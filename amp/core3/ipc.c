/* G3 single-slot transport; all pointers below map reserved Normal-NC DDR. */
#include "../protocol/amp_wire.h"
#include "../protocol/amp_slots.h"
static volatile uint8_t *const shared=(volatile uint8_t *)0x60200000UL;
static uint8_t incoming[AMP_FRAME_MAX], outgoing[AMP_FRAME_MAX];
static uint8_t original[AMP_PAYLOAD_MAX], challenge[AMP_PAYLOAD_MAX];
static uint64_t session, epoch, received, sent, bad;
static uint32_t rx_generation, tx_generation, wire_tx, wire_rx, origin_seq, reverse_seq;
static unsigned queued, waiting, mode, saved_len;
static size_t outgoing_len;
static inline void barrier(void) {
#ifdef AMP_HOST_TEST
    __asm__ volatile("" ::: "memory");
#else
    __asm__ volatile("dmb ish" ::: "memory");
#endif
}
static uint32_t read32(unsigned off) { return *(volatile uint32_t *)(shared+off); }
static void write32(unsigned off,uint32_t x) { *(volatile uint32_t *)(shared+off)=x; }
static void count(unsigned off,uint64_t x) { *(volatile uint64_t *)(shared+off)=x; }
static void reject(void) { count(AMP_C3_BAD_COUNT,++bad); }
static void flush(void)
{
    unsigned i;
    if(!queued || read32(AMP_CORE3_TX+AMP_ACK)!=tx_generation) return;
    barrier();
    for(i=0;i<outgoing_len;i++) shared[AMP_CORE3_TX+i]=outgoing[i];
    barrier();
    write32(AMP_CORE3_TX+AMP_PUBLISH,++tx_generation);
    barrier();
    count(AMP_C3_TX_COUNT,++sent);
    queued=0;
}
static void queue(uint16_t type,uint32_t correlation,const uint8_t *p,unsigned n)
{
    struct amp_view v={0};
    v.type=type; v.seq=++wire_tx; v.correlation=correlation;
    v.session=session; v.epoch=epoch; v.payload_len=(uint16_t)n; v.payload=p;
    outgoing_len=(size_t)amp_encode(outgoing,sizeof(outgoing),&v);
    queued=1;
    flush();
}
void amp_ipc_init(void)
{
    epoch=*(volatile uint64_t *)(shared+24);
    write32(AMP_LINUX_TX+AMP_ACK,0); /* consumer-owned */
    write32(AMP_CORE3_TX+AMP_PUBLISH,0); /* producer-owned */
    count(AMP_C3_RX_COUNT,0); count(AMP_C3_TX_COUNT,0); count(AMP_C3_BAD_COUNT,0);
    barrier();
}
void amp_ipc_poll(void)
{
    uint32_t generation;
    unsigned i,n;
    struct amp_view v;
    flush();
    if(queued) return; /* keep private output until peer acknowledges old slot */
    generation=read32(AMP_LINUX_TX+AMP_PUBLISH);
    if(generation==rx_generation) return;
    barrier();
    for(i=0;i<sizeof(incoming);i++) incoming[i]=shared[AMP_LINUX_TX+i];
    barrier();
    rx_generation=generation;
    write32(AMP_LINUX_TX+AMP_ACK,generation);
    barrier();
    count(AMP_C3_RX_COUNT,++received);
    n=(unsigned)incoming[10]|((unsigned)incoming[11]<<8);
    if(n>AMP_PAYLOAD_MAX || amp_decode(incoming,AMP_HEADER_BYTES+n,&v)!=AMP_OK) {reject();return;}
    if(v.type==AMP_HELLO) {
        if(!v.session || v.epoch || v.payload_len) {reject();return;}
        session=v.session; wire_rx=v.seq; waiting=0;
        queue(AMP_READY,v.seq,0,0);
        return;
    }
    if(!session || v.session!=session || v.epoch!=epoch || v.seq!=wire_rx+1U) {reject();return;}
    wire_rx=v.seq;
    if(waiting) {
        if(v.type!=AMP_ECHO_RESP || v.correlation!=reverse_seq || v.payload_len!=saved_len) {reject();return;}
        for(i=0;i<saved_len;i++) if(v.payload[i]!=challenge[i]) {reject();return;}
        waiting=0;
        queue(mode==AMP_CROSSED?AMP_ECHO_RESP:AMP_READY,origin_seq,
              mode==AMP_CROSSED?original:0,mode==AMP_CROSSED?saved_len:0);
    } else if(v.type==AMP_ECHO_REQ) {
        queue(AMP_ECHO_RESP,v.seq,v.payload,v.payload_len);
    } else if(v.type==AMP_ARM_REVERSE || v.type==AMP_CROSSED) {
        mode=v.type; saved_len=v.payload_len; origin_seq=v.seq;
        for(i=0;i<saved_len;i++) original[i]=v.payload[i];
        reverse_seq=wire_tx+1U;
        for(i=0;i<saved_len;i++) challenge[i]=(uint8_t)(i^reverse_seq^0xa5U);
        waiting=1;
        queue(AMP_ECHO_REQ,origin_seq,challenge,saved_len);
    } else reject();
}
