#include "amp_wire.h"
static uint32_t crc_step(uint32_t c, uint8_t b)
{
    unsigned i;
    c ^= b;
    for (i=0;i<8;i++) c=(c>>1)^((0U-(c&1U))&0xedb88320U);
    return c;
}
uint32_t amp_crc32(const uint8_t *p, size_t n)
{
    uint32_t c=0xffffffffU;
    while(n--) c=crc_step(c,*p++);
    return c^0xffffffffU;
}
static uint32_t frame_crc(const uint8_t *p, size_t n)
{
    uint32_t c=0xffffffffU;
    size_t i;
    for(i=0;i<n;i++) if(i<36 || i>=40) c=crc_step(c,p[i]);
    return c^0xffffffffU;
}
static uint64_t get(const uint8_t *p, unsigned n)
{
    uint64_t x=0;
    unsigned i;
    for(i=0;i<n;i++) x|=(uint64_t)p[i]<<(8*i);
    return x;
}
static void put(uint8_t *p, uint64_t x, unsigned n)
{
    unsigned i;
    for(i=0;i<n;i++) p[i]=(uint8_t)(x>>(8*i));
}
int amp_encode(uint8_t *p, size_t cap, const struct amp_view *v)
{
    unsigned i;
    size_t n;
    if(!p || !v || v->payload_len>AMP_PAYLOAD_MAX ||
       (v->payload_len && !v->payload)) return AMP_BAD_LENGTH;
    n=AMP_HEADER_BYTES+v->payload_len;
    if(cap<n) return AMP_BAD_LENGTH;
    put(p,AMP_MAGIC,4); put(p+4,AMP_WIRE_VERSION,2); put(p+6,v->type,2);
    put(p+8,AMP_HEADER_BYTES,2); put(p+10,v->payload_len,2); put(p+12,v->seq,4);
    put(p+16,v->session,8); put(p+24,v->epoch,8); put(p+32,v->correlation,4);
    put(p+36,0,4);
    for(i=0;i<v->payload_len;i++) p[40+i]=v->payload[i];
    put(p+36,frame_crc(p,n),4);
    return (int)n;
}
int amp_decode(const uint8_t *p, size_t n, struct amp_view *v)
{
    size_t payload_len;
    if(!p || !v || n<AMP_HEADER_BYTES || n>AMP_FRAME_MAX) return AMP_BAD_LENGTH;
    if(get(p,4)!=AMP_MAGIC) return AMP_BAD_MAGIC;
    if(get(p+4,2)!=AMP_WIRE_VERSION) return AMP_BAD_VERSION;
    if(get(p+8,2)!=AMP_HEADER_BYTES) return AMP_BAD_HEADER;
    payload_len=get(p+10,2);
    if(payload_len>AMP_PAYLOAD_MAX || n!=AMP_HEADER_BYTES+payload_len) return AMP_BAD_LENGTH;
    if(get(p+36,4)!=frame_crc(p,n)) return AMP_BAD_CRC;
    v->type=(uint16_t)get(p+6,2); v->payload_len=(uint16_t)payload_len;
    v->seq=(uint32_t)get(p+12,4); v->session=get(p+16,8); v->epoch=get(p+24,8);
    v->correlation=(uint32_t)get(p+32,4); v->payload=p+40;
    return AMP_OK;
}
