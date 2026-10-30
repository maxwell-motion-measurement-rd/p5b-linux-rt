/* G3 single-slot transport; all pointers below map reserved Normal-NC DDR. */
#include "../protocol/amp_wire.h"
#include "../protocol/amp_slots.h"
#include "../protocol/amp_fault.h"
static volatile uint8_t *const shared=(volatile uint8_t *)0x60200000UL;
static uint8_t incoming[AMP_FRAME_MAX], outgoing[AMP_FRAME_MAX];
static uint8_t original[AMP_PAYLOAD_MAX], challenge[AMP_PAYLOAD_MAX];
static uint64_t session, epoch, received, sent, bad,highest_session,old_session;
static uint32_t rx_generation, tx_generation, wire_tx, wire_rx, origin_seq, reverse_seq;
static unsigned queued, waiting, mode, saved_len;
static size_t outgoing_len;
static uint64_t pause_until,wait_deadline,timeouts,busy,resets;
static unsigned corrupt_once,busy_recorded;
static uint64_t heartbeat_pause_until,last_host_hb,last_host_change,host_lost,host_restored;
static unsigned host_hb_seen,host_hb_lost;
#ifdef AMP_HOST_TEST
uint64_t amp_test_ticks;
#endif
static uint64_t ticks(void) {
#ifdef AMP_HOST_TEST
    return amp_test_ticks;
#else
    uint64_t t; __asm__ volatile("isb; mrs %0,cntpct_el0":"=r"(t)); return t;
#endif
}
static uint64_t frequency(void) {return *(volatile uint64_t *)(shared+16);}
int amp_heartbeat_allowed(void) {return ticks()>=heartbeat_pause_until;}
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
static void reject(unsigned reason) {
    count(AMP_C3_BAD_COUNT,++bad); write32(AMP_C3_LAST_ERROR,reason);
    count(256+reason*8,*(volatile uint64_t *)(shared+256+reason*8)+1);
    barrier();
}
static void flush(void)
{
    unsigned i;
    if(!queued) return;
    if(read32(AMP_CORE3_TX+AMP_ACK)!=tx_generation) {
        if(!busy_recorded) {count(AMP_C3_BUSY,++busy);busy_recorded=1;}
        return;
    }
    barrier();
    for(i=0;i<outgoing_len;i++) shared[AMP_CORE3_TX+i]=outgoing[i];
    barrier();
    write32(AMP_CORE3_TX+AMP_PUBLISH,++tx_generation);
    barrier();
    count(AMP_C3_TX_COUNT,++sent);
    queued=0;
    busy_recorded=0;
}
static void wire_put(uint8_t *p,uint64_t x,unsigned n) {unsigned i;for(i=0;i<n;i++)p[i]=(uint8_t)(x>>(8*i));}
static void corrupt_frame(unsigned kind)
{
    uint8_t scratch[AMP_HEADER_BYTES+AMP_PAYLOAD_MAX];
    unsigned i,n=(unsigned)outgoing_len-40;
    if(kind==F_MAGIC) outgoing[0]^=1;
    else if(kind==F_VERSION) outgoing[4]=2;
    else if(kind==F_HEADER) outgoing[8]=39;
    else if(kind==F_LENGTH) {outgoing[10]=1;outgoing[11]=1;}
    else if(kind==F_CRC) outgoing[36]^=1;
    else {
        if(kind==F_DUPLICATE) wire_put(outgoing+12,wire_tx-1U,4);
        if(kind==F_SESSION) wire_put(outgoing+16,old_session?old_session:session^1,8);
        if(kind==F_EPOCH) outgoing[24]^=1;
        for(i=0;i<36;i++)scratch[i]=outgoing[i];
        for(i=0;i<n;i++)scratch[36+i]=outgoing[40+i];
        wire_put(outgoing+36,amp_crc32(scratch,36+n),4);
    }
}
static void queue(uint16_t type,uint32_t correlation,const uint8_t *p,unsigned n)
{
    struct amp_view v={0};
    v.type=type; v.seq=++wire_tx; v.correlation=correlation;
    v.session=session; v.epoch=epoch; v.payload_len=(uint16_t)n; v.payload=p;
    outgoing_len=(size_t)amp_encode(outgoing,sizeof(outgoing),&v);
    if(corrupt_once) {corrupt_frame(corrupt_once);corrupt_once=0;}
    queued=1;
    flush();
}
void amp_ipc_init(void)
{
    epoch=*(volatile uint64_t *)(shared+24);
    host_hb_seen=1;last_host_change=ticks();
    write32(AMP_LINUX_TX+AMP_ACK,0); /* consumer-owned */
    write32(AMP_CORE3_TX+AMP_PUBLISH,0); /* producer-owned */
    count(AMP_C3_RX_COUNT,0); count(AMP_C3_TX_COUNT,0); count(AMP_C3_BAD_COUNT,0);
    count(AMP_SERVICE_EPOCH,epoch);count(AMP_C3_TIMEOUTS,0);count(AMP_C3_BUSY,0);
    count(AMP_C3_RESETS,0);write32(AMP_C3_LAST_ERROR,0);
    count(AMP_PEER_HB_LOST,0);count(AMP_PEER_HB_RESTORED,0);
    barrier();
}
void amp_ipc_poll(void)
{
    uint32_t generation;
    unsigned i,n;
    struct amp_view v;
    uint64_t now=ticks();
    uint64_t host_hb=*(volatile uint64_t *)(shared+AMP_HOST_HEARTBEAT);
    if(host_hb && (!host_hb_seen || host_hb!=last_host_hb)) {
        host_hb_seen=1;last_host_hb=host_hb;last_host_change=now;
        if(host_hb_lost) {host_hb_lost=0;count(AMP_PEER_HB_RESTORED,++host_restored);}
    } else if(host_hb_seen && !host_hb_lost && now-last_host_change>=frequency()) {
        host_hb_lost=1;
        count(AMP_PEER_HB_DETECTION_TICKS,now-last_host_change);
        session=0;waiting=0;queued=0;
        barrier();count(AMP_PEER_HB_LOST,++host_lost);
    }
    if(waiting && now>=wait_deadline) {
        uint8_t error[4]={1,0,0,0};
        waiting=0;count(AMP_C3_TIMEOUTS,++timeouts);count(AMP_C3_TIMEOUT_AT,now);
        queue(AMP_ERROR,origin_seq,error,4);
    }
    if(now<pause_until) return;
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
    if(n>AMP_PAYLOAD_MAX) {reject(R_LENGTH);return;}
    {
        int decode=amp_decode(incoming,AMP_HEADER_BYTES+n,&v);
        if(decode) {reject((unsigned)-decode);return;}
    }
    if(v.type==AMP_HELLO) {
        if(host_hb_lost) {reject(R_HEARTBEAT);return;}
        if(!v.session || v.session<=highest_session || v.epoch || v.payload_len) {reject(R_SESSION);return;}
        old_session=highest_session;highest_session=v.session;
        session=v.session; wire_rx=v.seq; waiting=0;
        queue(AMP_READY,v.seq,0,0);
        return;
    }
    if(host_hb_lost) {reject(R_HEARTBEAT);return;}
    if(!session || v.session!=session) {reject(R_SESSION);return;}
    if(v.epoch!=epoch) {reject(R_EPOCH);return;}
    if(v.seq!=wire_rx+1U) {reject(R_SEQUENCE);return;}
    wire_rx=v.seq;
    if(waiting) {
        if(v.type!=AMP_ECHO_RESP || v.correlation!=reverse_seq || v.payload_len!=saved_len) {reject(R_DATA);return;}
        for(i=0;i<saved_len;i++) if(v.payload[i]!=challenge[i]) {reject(R_DATA);return;}
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
        count(AMP_C3_WAIT_START,now);wait_deadline=now+frequency()/10;
        queue(AMP_ECHO_REQ,origin_seq,challenge,saved_len);
    } else if(v.type==AMP_TEST_BAD_REPLY && v.payload_len==4 && v.payload[0]>=1 && v.payload[0]<=8) {
        corrupt_once=v.payload[0];queue(AMP_ECHO_RESP,v.seq,v.payload,4);
    } else if(v.type==AMP_TEST_PAUSE && v.payload_len==4) {
        unsigned ms=(unsigned)v.payload[0]|((unsigned)v.payload[1]<<8);
        if(!ms || ms>1000) {reject(R_DATA);return;}
        queue(AMP_READY,v.seq,0,0);pause_until=now+frequency()*ms/1000;
    } else if(v.type==AMP_TEST_RESET && !v.payload_len) {
        epoch++;if(!epoch)epoch=1;count(AMP_SERVICE_EPOCH,epoch);count(AMP_C3_RESETS,++resets);
        session=0;wire_rx=0;waiting=0;queued=0;
        barrier();
        /* Deliberately abandon this transaction; new HELLO is mandatory. */
    } else if(v.type==AMP_TEST_TX_SEQUENCE && v.payload_len==4) {
        wire_tx=(uint32_t)v.payload[0]|((uint32_t)v.payload[1]<<8)|((uint32_t)v.payload[2]<<16)|((uint32_t)v.payload[3]<<24);
        queue(AMP_READY,v.seq,0,0);
    } else if(v.type==AMP_TEST_HEARTBEAT_PAUSE && v.payload_len==4) {
        unsigned ms=(unsigned)v.payload[0]|((unsigned)v.payload[1]<<8);
        if(!ms || ms>1200) {reject(R_DATA);return;}
        queue(AMP_READY,v.seq,0,0);heartbeat_pause_until=now+frequency()*ms/1000;
    } else reject(R_TYPE);
}
