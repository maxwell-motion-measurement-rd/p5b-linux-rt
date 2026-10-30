#ifndef P5_AMP_FAULT_H
#define P5_AMP_FAULT_H
#include "amp_wire.h"
#ifdef __KERNEL__
#include <linux/ioctl.h>
#elif !defined(AMP_BARE_METAL)
#include <sys/ioctl.h>
#endif
#define AMP_TEST_BAD_REPLY 0x70U
#define AMP_TEST_PAUSE 0x71U
#define AMP_TEST_RESET 0x72U
#define AMP_TEST_TX_SEQUENCE 0x73U
#define AMP_TEST_HEARTBEAT_PAUSE 0x74U
#define AMP_HOST_HEARTBEAT 216U
#define AMP_PEER_HB_LOST 232U
#define AMP_PEER_HB_RESTORED 240U
#define AMP_PEER_HB_DETECTION_TICKS 248U
#define AMP_C3_LAST_ERROR 152U
#define AMP_SERVICE_EPOCH 160U
#define AMP_C3_TIMEOUTS 168U
#define AMP_C3_BUSY 176U
#define AMP_C3_WAIT_START 184U
#define AMP_C3_TIMEOUT_AT 192U
#define AMP_C3_RESETS 200U
enum amp_fault_kind { F_MAGIC=1,F_VERSION,F_HEADER,F_LENGTH,F_CRC,F_DUPLICATE,F_SESSION,F_EPOCH };
enum amp_reject_reason { R_LENGTH=1,R_MAGIC,R_VERSION,R_HEADER,R_CRC,R_SESSION,R_EPOCH,R_SEQUENCE,R_TYPE,R_DATA,R_HEARTBEAT };
struct amp_test_snapshot {
    uint64_t linux_tx,linux_rx,bad_rx,timeouts,stale,aborted;
    uint64_t core3_rx,core3_tx,core3_bad,service_epoch,peer_timeouts,busy;
    uint64_t wait_start,timeout_at,resets,heartbeat,freq,boot_token;
    uint64_t host_heartbeat,host_lost,host_restored,peer_lost,peer_restored;
    uint64_t host_detection_ns,peer_detection_ticks;
    uint32_t core3_error;
    int32_t last_rx_error;
    uint32_t rx_publish,rx_ack,rx_crc;
    uint32_t host_lost_active,require_hello;
};
#define AMP_IOC_RAW_ONCE _IO('A',0x41)
#define AMP_IOC_HOLD_ACK _IO('A',0x42)
#define AMP_IOC_RELEASE_ACK _IO('A',0x43)
#define AMP_IOC_REBASE_PEER _IO('A',0x44)
#define AMP_IOC_SNAPSHOT _IOR('A',0x45,struct amp_test_snapshot)
#define AMP_IOC_PAUSE_HOST_HB _IOW('A',0x46,uint32_t)
#endif
