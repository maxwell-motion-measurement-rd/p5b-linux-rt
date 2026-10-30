#ifndef P5_AMP_WIRE_H
#define P5_AMP_WIRE_H
#ifdef __KERNEL__
#include <linux/types.h>
#else
#include <stdint.h>
#include <stddef.h>
#endif
#define AMP_MAGIC 0x32504d41U /* little-endian "AMP2"; separate from heartbeat */
#define AMP_WIRE_VERSION 1U
#define AMP_HEADER_BYTES 40U
#define AMP_PAYLOAD_MAX 256U
#define AMP_FRAME_MAX (AMP_HEADER_BYTES + AMP_PAYLOAD_MAX)
enum amp_type { AMP_HELLO=1, AMP_READY=2, AMP_ECHO_REQ=3, AMP_ECHO_RESP=4, AMP_ERROR=5,
    AMP_ARM_REVERSE=6, AMP_CROSSED=7 };
enum amp_wire_error { AMP_OK=0, AMP_BAD_LENGTH=-1, AMP_BAD_MAGIC=-2,
    AMP_BAD_VERSION=-3, AMP_BAD_HEADER=-4, AMP_BAD_CRC=-5 };
struct amp_view {
    uint16_t type, payload_len;
    uint32_t seq, correlation;
    uint64_t session, epoch;
    const uint8_t *payload; /* references the caller's stable private snapshot */
};
uint32_t amp_crc32(const uint8_t *data, size_t len);
int amp_encode(uint8_t *out, size_t cap, const struct amp_view *v);
int amp_decode(const uint8_t *in, size_t len, struct amp_view *v);
#endif
