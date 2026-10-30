#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <unistd.h>
#include "../protocol/amp_fault.h"
int main(void)
{
    struct amp_test_snapshot s;
    int fd=open("/dev/p5-core3",O_RDWR);
    if(fd<0) {perror("snapshot open");return 1;}
    if(ioctl(fd,AMP_IOC_SNAPSHOT,&s)) {perror("snapshot ioctl");close(fd);return 1;}
    close(fd);
    printf("{\"linux_tx\":%"PRIu64",\"linux_rx\":%"PRIu64",\"core3_rx\":%"PRIu64",\"core3_tx\":%"PRIu64
        ",\"bad_rx\":%"PRIu64",\"timeouts\":%"PRIu64",\"stale\":%"PRIu64",\"aborted\":%"PRIu64
        ",\"core3_bad\":%"PRIu64",\"peer_timeouts\":%"PRIu64",\"busy\":%"PRIu64",\"resets\":%"PRIu64
        ",\"heartbeat\":%"PRIu64",\"host_heartbeat\":%"PRIu64",\"host_lost\":%"PRIu64
        ",\"host_restored\":%"PRIu64",\"peer_lost\":%"PRIu64",\"peer_restored\":%"PRIu64
        ",\"boot_token\":%"PRIu64",\"service_epoch\":%"PRIu64",\"host_lost_active\":%u}\n",
        s.linux_tx,s.linux_rx,s.core3_rx,s.core3_tx,s.bad_rx,s.timeouts,s.stale,s.aborted,
        s.core3_bad,s.peer_timeouts,s.busy,s.resets,s.heartbeat,s.host_heartbeat,s.host_lost,
        s.host_restored,s.peer_lost,s.peer_restored,s.boot_token,s.service_epoch,s.host_lost_active);
    return 0;
}
