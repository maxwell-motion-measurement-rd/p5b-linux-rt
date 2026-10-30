#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static volatile sig_atomic_t stop;
static volatile uint64_t sink;
static void finish(int sig) { (void)sig; stop = 1; }
static double seconds(void) { struct timespec t; if(clock_gettime(CLOCK_MONOTONIC,&t)) exit(3); return t.tv_sec+t.tv_nsec/1e9; }
int main(int argc,char **argv) {
    if(argc!=4 || (strcmp(argv[1],"cpu") && strcmp(argv[1],"mem"))) { fprintf(stderr,"usage: rtload cpu|mem cpu-number seconds\n"); return 2; }
    char *end; long cpu=strtol(argv[2],&end,10); if(*end || cpu<0 || cpu>2) return 2;
    long duration=strtol(argv[3],&end,10); if(*end || duration<1 || duration>14400) return 2;
    cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu,&set);
    if(sched_setaffinity(0,sizeof(set),&set)) { perror("affinity"); return 1; }
    if(sched_getscheduler(0)!=SCHED_OTHER) { fprintf(stderr,"requires SCHED_OTHER\n"); return 1; }
    signal(SIGTERM,finish); signal(SIGINT,finish);
    const size_t size=128u*1024u*1024u;
    unsigned char *a=NULL,*b=NULL;
    if(!strcmp(argv[1],"mem")) { a=malloc(size); b=malloc(size); if(!a||!b) { perror("malloc"); return 1; } memset(a,0x5a,size); memset(b,0xa5,size); }
    double start=seconds(); uint64_t iterations=0,x=1;
    while(!stop && seconds()-start<duration) {
        if(a) { memset(a,(unsigned char)iterations,size); memcpy(b,a,size); if(memcmp(a,b,size)) { fprintf(stderr,"MEMORY_VERIFY_FAILED\n"); return 1; } sink+=b[iterations%size]; unsigned char *tmp=a;a=b;b=tmp; }
        else { for(int i=0;i<100000;i++) x=x*6364136223846793005ULL+1; sink=x; }
        iterations++;
    }
    printf("mode=%s cpu=%ld policy=SCHED_OTHER seconds=%.3f iterations=%"PRIu64" sink=%"PRIu64" stopped=%d bytes_allocated=%zu\n",argv[1],cpu,duration?seconds()-start:0,iterations,sink,stop,a?size*2:0);
    free(a);free(b);return 0;
}
