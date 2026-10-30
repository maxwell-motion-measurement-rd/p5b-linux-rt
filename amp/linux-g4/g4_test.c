#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include "../protocol/amp_fault.h"
static int fd=-1,peer_seen;
static uint32_t seq,peer_seq;
static uint64_t session,previous_session,epoch,hello_max_ns;
static uint8_t tx[AMP_FRAME_MAX],rx[AMP_FRAME_MAX];
static unsigned cases;
static const char *stage="init";
static unsigned iteration;
static uint64_t now_ns(void) {struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000ULL+t.tv_nsec;}
static void fail(const char *why,int line) {fprintf(stderr,"G4_FAIL stage=%s iteration=%u line=%d assertion=%s errno=%d\n",stage,iteration,line,why,errno);exit(1);}
#define CHECK(x) do {if(!(x))fail(#x,__LINE__);} while(0)
static void nap(unsigned ms) {struct timespec t={ms/1000,(long)(ms%1000)*1000000};while(nanosleep(&t,&t)&&errno==EINTR){} }
static void open_dev(void) {CHECK(fd<0);fd=open("/dev/p5-core3",O_RDWR);CHECK(fd>=0);}
static struct amp_test_snapshot snapshot(void) {struct amp_test_snapshot s;CHECK(ioctl(fd,AMP_IOC_SNAPSHOT,&s)==0);return s;}
static int make(unsigned type,const uint8_t *p,unsigned n,uint32_t correlation)
{
    struct amp_view v={0};v.type=type;v.seq=++seq;v.session=session;v.epoch=type==AMP_HELLO?0:epoch;
    v.payload=p;v.payload_len=n;v.correlation=correlation;
    return amp_encode(tx,sizeof(tx),&v);
}
static struct amp_view receive(void)
{
    struct amp_view v;ssize_t n=read(fd,rx,sizeof(rx));
    CHECK(n>=40 && amp_decode(rx,(size_t)n,&v)==0);
    CHECK(v.session==session && (!epoch || v.epoch==epoch));
    CHECK(!peer_seen || v.seq==peer_seq+1U);peer_seq=v.seq;peer_seen=1;return v;
}
static struct amp_view good(unsigned type,const uint8_t *p,unsigned n,uint32_t corr)
{
    int bytes=make(type,p,n,corr);CHECK(bytes>=40);CHECK(write(fd,tx,bytes)==bytes);return receive();
}
static void echoes(unsigned count)
{
    unsigned i,j;uint8_t p[256];uint64_t next=now_ns();
    for(i=0;i<count;i++) {
        struct amp_view v;struct timespec wake;uint32_t request=seq+1U;
        for(j=0;j<sizeof(p);j++)p[j]=(uint8_t)(i+j*3);
        v=good(AMP_ECHO_REQ,p,sizeof(p),0);
        CHECK(v.type==AMP_ECHO_RESP && v.correlation==request && v.payload_len==sizeof(p) && !memcmp(v.payload,p,sizeof(p)));
        next+=10000000ULL;
        if(now_ns()<next) {wake.tv_sec=next/1000000000ULL;wake.tv_nsec=next%1000000000ULL;CHECK(!clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&wake,0));}
        else next=now_ns();
    }
}
static void heal(unsigned count)
{
    struct amp_view v;struct amp_test_snapshot s;uint64_t begin=now_ns(),elapsed;
    previous_session=session;session=begin;if(session<=previous_session)session=previous_session+1;
    seq=0;epoch=0;peer_seen=0;
    v=good(AMP_HELLO,0,0,0);CHECK(v.type==AMP_READY && v.correlation==seq && !v.payload_len && v.epoch);
    epoch=v.epoch;s=snapshot();CHECK(s.service_epoch==epoch);
    elapsed=now_ns()-begin;CHECK(elapsed<2000000000ULL);if(elapsed>hello_max_ns)hello_max_ns=elapsed;
    echoes(count);
}
static void report(const char *name,unsigned kind,int error,uint64_t elapsed,uint64_t detail,unsigned recovered)
{
    cases++;printf("{\"case\":\"%s\",\"kind\":%u,\"iteration\":%u,\"passed\":true,\"errno\":%d,\"elapsed_ns\":%" PRIu64 ",\"detail\":%" PRIu64 ",\"recovered_echoes\":%u}\n",name,kind,iteration,error,elapsed,detail,recovered);fflush(stdout);
}
static void put(uint8_t *p,uint64_t value,unsigned n) {unsigned i;for(i=0;i<n;i++)p[i]=(uint8_t)(value>>(8*i));}
static void recalc_crc(int bytes) {uint8_t b[AMP_FRAME_MAX];memcpy(b,tx,36);memcpy(b+36,tx+40,bytes-40);put(tx+36,amp_crc32(b,bytes-4),4);}
static void corrupt(unsigned kind,int bytes)
{
    if(kind==F_MAGIC)tx[0]^=1;
    if(kind==F_VERSION)tx[4]=2;
    if(kind==F_HEADER)tx[8]=39;
    if(kind==F_LENGTH){tx[10]=1;tx[11]=1;}
    if(kind==F_DUPLICATE)put(tx+12,seq-1U,4);
    if(kind==F_SESSION)put(tx+16,previous_session?previous_session:session^1,8);
    if(kind==F_EPOCH)put(tx+24,epoch^1,8);
    recalc_crc(bytes);if(kind==F_CRC)tx[36]^=1;
}
static void negative_cases(void)
{
    static const unsigned reason[]={0,R_MAGIC,R_VERSION,R_HEADER,R_LENGTH,R_CRC,R_SEQUENCE,R_SESSION,R_EPOCH};
    unsigned kind;
    for(kind=1;kind<=8;kind++) for(iteration=0;iteration<10;iteration++) {
        struct amp_test_snapshot before,after;uint64_t begin,elapsed;int bytes,error;ssize_t rc;uint8_t p[4]={1,2,3,4};
        stage="linux_to_core3_fault";before=snapshot();bytes=make(AMP_ECHO_REQ,p,4,0);corrupt(kind,bytes);
        CHECK(!ioctl(fd,AMP_IOC_RAW_ONCE));begin=now_ns();rc=write(fd,tx,bytes);error=errno;elapsed=now_ns()-begin;
        CHECK(rc<0 && error==ETIMEDOUT && elapsed>=50000000ULL && elapsed<1000000000ULL);
        after=snapshot();CHECK(after.core3_bad==before.core3_bad+1 && after.core3_error==reason[kind] && after.timeouts==before.timeouts+1);
        heal(1);report(stage,kind,error,elapsed,after.core3_error,1);
        stage="core3_to_linux_fault";before=snapshot();put(p,kind,4);bytes=make(AMP_TEST_BAD_REPLY,p,4,0);
        begin=now_ns();rc=write(fd,tx,bytes);error=errno;elapsed=now_ns()-begin;
        CHECK(rc<0 && error==(kind==F_SESSION?ETIMEDOUT:EPROTO));
        after=snapshot();CHECK(after.last_rx_error==-(int32_t)reason[kind]);
        if(kind==F_SESSION) CHECK(after.stale==before.stale+1 && after.timeouts==before.timeouts+1);
        else CHECK(after.bad_rx==before.bad_rx+1);
        heal(1);report(stage,kind,error,elapsed,(uint64_t)reason[kind],1);
    }
}
static void wrap_cases(void)
{
    for(iteration=0;iteration<10;iteration++) {
        struct amp_view v;uint8_t p[4];unsigned j;uint32_t expected[]={0xffffffffU,0,1};
        stage="linux_sequence_wrap";previous_session=session;session=now_ns();CHECK(session>previous_session);seq=0xfffffffdU;epoch=0;peer_seen=0;
        v=good(AMP_HELLO,0,0,0);CHECK(v.type==AMP_READY && v.correlation==0xfffffffeU);
        epoch=v.epoch;
        for(j=0;j<3;j++){v=good(AMP_ECHO_REQ,0,0,0);CHECK(seq==expected[j] && v.type==AMP_ECHO_RESP && v.correlation==seq);}
        report(stage,0,0,0,seq,3);
        stage="core3_sequence_wrap";CHECK(!ioctl(fd,AMP_IOC_REBASE_PEER));peer_seen=0;put(p,0xfffffffdU,4);
        v=good(AMP_TEST_TX_SEQUENCE,p,4,0);CHECK(v.type==AMP_READY && v.seq==0xfffffffeU);
        for(j=0;j<3;j++){v=good(AMP_ECHO_REQ,0,0,0);CHECK(v.type==AMP_ECHO_RESP && v.seq==expected[j]);}
        heal(1);report(stage,0,0,0,1,3);
    }
}
static void backpressure_cases(void)
{
    for(iteration=0;iteration<10;iteration++) {
        struct amp_test_snapshot held,blocked;struct amp_view v;uint64_t begin,elapsed;int bytes,error;
        stage="backpressure";CHECK(!ioctl(fd,AMP_IOC_HOLD_ACK));v=good(AMP_ECHO_REQ,(const uint8_t *)"first",5,0);CHECK(v.type==AMP_ECHO_RESP);
        held=snapshot();CHECK(held.rx_publish!=held.rx_ack);bytes=make(AMP_ECHO_REQ,(const uint8_t *)"second",6,0);
        begin=now_ns();CHECK(write(fd,tx,bytes)<0);error=errno;elapsed=now_ns()-begin;CHECK(error==ETIMEDOUT);
        blocked=snapshot();CHECK(blocked.rx_publish==held.rx_publish && blocked.rx_crc==held.rx_crc && blocked.busy>=held.busy+1);
        CHECK(!ioctl(fd,AMP_IOC_RELEASE_ACK));heal(1);report(stage,0,error,elapsed,blocked.busy,1);
    }
}
static void pause_cases(void)
{
    for(iteration=0;iteration<10;iteration++) {
        struct amp_view v;struct amp_test_snapshot before,after;uint8_t p[4];uint64_t begin,elapsed,peer_ns;int bytes,error;
        stage="core3_comm_pause";put(p,1000,4);v=good(AMP_TEST_PAUSE,p,4,0);CHECK(v.type==AMP_READY);
        bytes=make(AMP_ECHO_REQ,p,4,0);begin=now_ns();CHECK(write(fd,tx,bytes)<0);error=errno;elapsed=now_ns()-begin;CHECK(error==ETIMEDOUT);
        nap(1050);heal(1);report(stage,0,error,elapsed,1000,1);
        stage="linux_consumer_pause";before=snapshot();v=good(AMP_ARM_REVERSE,p,4,0);CHECK(v.type==AMP_ECHO_REQ);
        nap(1000);after=snapshot();CHECK(after.peer_timeouts==before.peer_timeouts+1 && after.timeout_at>=after.wait_start);
        peer_ns=(after.timeout_at-after.wait_start)*1000000000ULL/after.freq;
        CHECK(peer_ns>=100000000ULL && peer_ns<200000000ULL);
        heal(1);report(stage,0,0,peer_ns,after.peer_timeouts,1);
    }
}
static uint64_t live_tx(void)
{
    unsigned long long value,aborted;FILE *f=fopen("/sys/bus/platform/devices/core3-heartbeat/live","r");
    CHECK(f && fscanf(f,"tx=%llu aborted=%llu",&value,&aborted)==2);CHECK(!fclose(f));return value;
}
static void restart_cases(void)
{
    for(iteration=0;iteration<10;iteration++) {
        int pipefd[2],status;pid_t child;char ready;uint64_t begin;
        int inflight=iteration>=5;struct amp_test_snapshot before=snapshot(),after;
        stage=inflight?"app_killed_waiting_reply":"app_killed_before_send";
        CHECK(!close(fd));fd=-1;CHECK(!pipe(pipefd));child=fork();CHECK(child>=0);
        if(!child) {
            uint8_t p[4];struct amp_view v;int bytes;
            close(pipefd[0]);open_dev();heal(0);
            if(inflight) {put(p,1000,4);v=good(AMP_TEST_PAUSE,p,4,0);CHECK(v.type==AMP_READY);}
            CHECK(write(pipefd[1],"R",1)==1);close(pipefd[1]);
            if(inflight) {bytes=make(AMP_ECHO_REQ,(const uint8_t *)"pending",7,0);(void)write(fd,tx,bytes);_exit(4);}
            for(;;)pause();
        }
        close(pipefd[1]);CHECK(read(pipefd[0],&ready,1)==1);close(pipefd[0]);begin=now_ns();
        if(inflight) {
            while(live_tx()<before.linux_tx+3) {
                CHECK(now_ns()-begin<2000000000ULL);CHECK(waitpid(child,&status,WNOHANG)==0);nap(1);
            }
        }
        CHECK(!kill(child,SIGKILL));CHECK(waitpid(child,&status,0)==child);
        CHECK(WIFSIGNALED(status) && WTERMSIG(status)==SIGKILL);
        if(inflight)nap(1050);
        open_dev();after=snapshot();
        CHECK(after.aborted==before.aborted+(unsigned)inflight);
        CHECK(after.linux_tx==before.linux_tx+(inflight?3:1));
        heal(100);report(stage,0,SIGKILL,now_ns()-begin,after.aborted,100);
    }
}
static void reset_cases(void)
{
    for(iteration=0;iteration<10;iteration++) {
        struct amp_test_snapshot before=snapshot(),after;uint64_t begin=now_ns(),old_epoch=epoch;
        int bytes,error;
        stage="communication_service_reset";
        bytes=make(AMP_TEST_RESET,0,0,0);CHECK(write(fd,tx,bytes)<0);error=errno;CHECK(error==ETIMEDOUT);
        after=snapshot();CHECK(after.resets==before.resets+1 && after.service_epoch==old_epoch+1 && after.boot_token==before.boot_token);
        /* Replay the old HELLO: reset must not erase the session high-water mark. */
        bytes=make(AMP_HELLO,0,0,0);CHECK(write(fd,tx,bytes)<0 && errno==ETIMEDOUT);
        after=snapshot();CHECK(after.core3_error==R_SESSION);
        heal(0);CHECK(epoch==old_epoch+1);
        bytes=make(AMP_ECHO_REQ,(const uint8_t *)"old epoch",9,0);put(tx+24,old_epoch,8);recalc_crc(bytes);
        CHECK(!ioctl(fd,AMP_IOC_RAW_ONCE));CHECK(write(fd,tx,bytes)<0 && errno==ETIMEDOUT);
        after=snapshot();CHECK(after.core3_error==R_EPOCH);
        heal(100);after=snapshot();CHECK(after.boot_token==before.boot_token && after.heartbeat>before.heartbeat);
        report(stage,0,error,now_ns()-begin,after.service_epoch,100);
    }
}
static void heartbeat_cases(void)
{
    for(iteration=0;iteration<10;iteration++) {
        struct amp_test_snapshot before=snapshot(),after;struct amp_view v;
        uint32_t ms=1200;uint8_t p[4];uint64_t begin=now_ns(),detection_ns;int bytes;
        stage="core3_heartbeat_pause";put(p,ms,4);v=good(AMP_TEST_HEARTBEAT_PAUSE,p,4,0);CHECK(v.type==AMP_READY);
        do {nap(5);after=snapshot();CHECK(now_ns()-begin<2000000000ULL);} while(after.host_lost==before.host_lost);
        CHECK(after.host_lost==before.host_lost+1 && after.host_restored==before.host_restored && after.host_lost_active);
        detection_ns=after.host_detection_ns;CHECK(detection_ns>=1000000000ULL && detection_ns<1400000000ULL);
        bytes=make(AMP_ECHO_REQ,p,4,0);CHECK(write(fd,tx,bytes)<0 && errno==ENOLINK);
        do {nap(5);after=snapshot();CHECK(now_ns()-begin<2000000000ULL);} while(after.host_restored==before.host_restored || after.host_lost_active);
        bytes=make(AMP_ECHO_REQ,p,4,0);CHECK(write(fd,tx,bytes)<0 && errno==ENOTCONN);
        heal(1);report(stage,0,ENOLINK,detection_ns,after.host_restored,1);
        stage="linux_heartbeat_pause";before=snapshot();begin=now_ns();CHECK(!ioctl(fd,AMP_IOC_PAUSE_HOST_HB,&ms));
        do {nap(5);after=snapshot();CHECK(now_ns()-begin<2000000000ULL);} while(after.peer_lost==before.peer_lost);
        CHECK(after.peer_lost==before.peer_lost+1 && after.peer_restored==before.peer_restored);
        detection_ns=after.peer_detection_ticks*1000000000ULL/after.freq;
        CHECK(detection_ns>=1000000000ULL && detection_ns<1400000000ULL);
        bytes=make(AMP_ECHO_REQ,p,4,0);CHECK(write(fd,tx,bytes)<0 && errno==ETIMEDOUT);
        after=snapshot();CHECK(after.core3_error==R_HEARTBEAT);
        do {nap(5);after=snapshot();CHECK(now_ns()-begin<2000000000ULL);} while(after.peer_restored==before.peer_restored);
        heal(1);report(stage,0,ETIMEDOUT,detection_ns,after.peer_restored,1);
    }
}
int main(int argc,char **argv)
{
    struct amp_test_snapshot before,after;
    if(argc!=2)return 2;
    setvbuf(stdout,0,_IOLBF,0);open_dev();
    if(!strcmp(argv[1],"gate")) {
        errno=0;CHECK(ioctl(fd,AMP_IOC_RAW_ONCE)<0 && errno==EPERM);
        puts("G4_DEFAULT_FAULT_GATE=passed");close(fd);return 0;
    }
    if(strcmp(argv[1],"run"))return 2;
    before=snapshot();heal(1);
    negative_cases();wrap_cases();backpressure_cases();pause_cases();restart_cases();reset_cases();heartbeat_cases();
    after=snapshot();CHECK(cases==250);
    CHECK(after.timeouts-before.timeouts==150 && after.bad_rx-before.bad_rx==70);
    CHECK(after.core3_bad-before.core3_bad==110 && after.peer_timeouts-before.peer_timeouts==10);
    CHECK(after.aborted-before.aborted==5 && after.resets-before.resets==10);
    CHECK(after.host_lost-before.host_lost==10 && after.host_restored-before.host_restored==10);
    CHECK(after.peer_lost-before.peer_lost==10 && after.peer_restored-before.peer_restored==10);
    CHECK(after.linux_tx==after.core3_rx && after.linux_rx==after.core3_tx);
    printf("{\"G4_SUMMARY\":\"passed\",\"cases\":%u,\"expected_kernel_timeouts\":150,\"expected_bad_rx\":70,\"expected_core3_rejections\":110,\"expected_peer_timeouts\":10,\"heartbeat_losses_each_direction\":10,\"aborted_waiting_writes\":5,\"service_resets\":10,\"max_handshake_ns\":%" PRIu64 ",\"linux_tx\":%" PRIu64 ",\"linux_rx\":%" PRIu64 ",\"stale_dropped\":%" PRIu64 "}\n",cases,hello_max_ns,after.linux_tx,after.linux_rx,after.stale-before.stale);
    close(fd);return 0;
}
