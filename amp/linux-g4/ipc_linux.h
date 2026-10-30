/* Included after struct core3 in the experimental loader. */
static int heartbeat_thread(void *data)
{
    struct core3 *c=data;
    bool observing=false;
    while(!kthread_should_stop()) {
        if(READ_ONCE(c->running) && readl(c->shared)==0x504d4143 && readl(c->shared+4)==4) {
            unsigned long now=jiffies,pause=READ_ONCE(c->host_pause_until);
            u64 hb;
            if(!pause || time_after_eq(now,pause)) writeq(++c->host_hb,c->shared+AMP_HOST_HEARTBEAT);
            hb=readq(c->shared+32);
            if(!observing || hb!=c->last_peer_hb) {
                observing=true;c->last_peer_hb=hb;c->last_hb_change=now;
                if(READ_ONCE(c->hb_lost)) {
                    WRITE_ONCE(c->hb_lost,false);smp_wmb();c->hb_restored_count++;
                }
            } else if(!READ_ONCE(c->hb_lost) && time_after_eq(now,c->last_hb_change+HZ)) {
                c->hb_detection_ns=(u64)jiffies_to_msecs(now-c->last_hb_change)*1000000ULL;
                WRITE_ONCE(c->hb_lost,true);WRITE_ONCE(c->require_hello,true);smp_wmb();c->hb_lost_count++;
            }
        }
        msleep(100);
    }
    return 0;
}
static void heartbeat_stop(void *data)
{
    struct core3 *c=data;
    WRITE_ONCE(c->running,false);kthread_stop(c->hb_task);
}
static int heartbeat_register(struct core3 *c,struct device *dev)
{
    c->hb_task=kthread_run(heartbeat_thread,c,"p5-amp-hb");
    if(IS_ERR(c->hb_task)) return PTR_ERR(c->hb_task);
    return devm_add_action_or_reset(dev,heartbeat_stop,c);
}
static int ipc_open(struct inode *inode, struct file *file)
{
    struct core3 *c=container_of(file->private_data,struct core3,misc);
    if(atomic_cmpxchg(&c->opened,0,1)) return -EBUSY;
    file->private_data=c;
    return nonseekable_open(inode,file);
}
static int ipc_release(struct inode *inode, struct file *file)
{
    struct core3 *c=file->private_data;
    mutex_lock(&c->lock);
    c->reply_pending=false;
    c->raw_once=false;c->hold_next=false;
    WRITE_ONCE(c->require_hello,true);
    mutex_unlock(&c->lock);
    atomic_set(&c->opened,0);
    return 0;
}
static ssize_t ipc_read(struct file *file,char __user *buf,size_t count,loff_t *pos)
{
    struct core3 *c=file->private_data;
    int ret;
    mutex_lock(&c->lock);
    if(c->reply_pending && READ_ONCE(c->require_hello)) {c->reply_pending=false;ret=-ENOTCONN;}
    else if(!c->reply_pending) ret=-EAGAIN;
    else if(count<c->reply_len) ret=-EMSGSIZE;
    else if(copy_to_user(buf,c->reply,c->reply_len)) ret=-EFAULT;
    else { ret=c->reply_len; c->reply_pending=false; }
    mutex_unlock(&c->lock);
    return ret;
}
static ssize_t ipc_write(struct file *file,const char __user *buf,size_t count,loff_t *pos)
{
    struct core3 *c=file->private_data;
    struct amp_view request,response;
    unsigned long deadline;
    u32 generation;
    unsigned n;
    int ret;
    if(count<AMP_HEADER_BYTES || count>AMP_FRAME_MAX) return -EMSGSIZE;
    mutex_lock(&c->lock);
    if(!c->attempted || readl(c->shared)!=0x504d4143 ||
       readl(c->shared+4)!=4 || readl(c->shared+40)!=1) {ret=-EHOSTDOWN;goto out;}
    if(c->reply_pending) {ret=-EBUSY;goto out;}
    if(READ_ONCE(c->hb_lost)) {ret=-ENOLINK;goto out;}
    if(copy_from_user(c->outgoing,buf,count)) {ret=-EFAULT;goto out;}
    if(c->raw_once && fault_tests) {
        memset(&request,0,sizeof(request));
        request.type=get_unaligned_le16(c->outgoing+6);
        request.session=get_unaligned_le64(c->outgoing+16);
        request.epoch=get_unaligned_le64(c->outgoing+24);
        c->raw_once=false;
    } else {
        ret=amp_decode(c->outgoing,count,&request);
        if(ret) {ret=-EINVAL;goto out;}
    }
    if(request.type>=AMP_TEST_BAD_REPLY && !fault_tests) {ret=-EPERM;goto out;}
    if(READ_ONCE(c->require_hello) && request.type!=AMP_HELLO) {ret=-ENOTCONN;goto out;}
    if(request.type==AMP_HELLO) c->peer_seen=false;
    deadline=jiffies+msecs_to_jiffies(100);
    /* Drain stale replies, which can otherwise block the peer's single slot. */
    generation=readl(c->shared+AMP_CORE3_TX+AMP_PUBLISH);
    if(generation!=c->rx_generation) {
        c->rx_generation=generation;
        writel(generation,c->shared+AMP_CORE3_TX+AMP_ACK);
        c->rx_count++;
        c->stale++;
    }
    while(readl(c->shared+AMP_LINUX_TX+AMP_ACK)!=c->tx_generation) {
        if(fatal_signal_pending(current)) {c->aborted++;ret=-EINTR;goto out;}
        if(time_after_eq(jiffies,deadline)) {ret=-ETIMEDOUT;goto timeout;}
        usleep_range(50,100);
    }
    memcpy_toio(c->shared+AMP_LINUX_TX,c->outgoing,count);
    wmb();
    writel(++c->tx_generation,c->shared+AMP_LINUX_TX+AMP_PUBLISH);
    c->tx_count++;
    for(;;) {
        if(fatal_signal_pending(current)) {c->aborted++;ret=-EINTR;goto out;}
        if(time_after_eq(jiffies,deadline)) {ret=-ETIMEDOUT;goto timeout;}
        generation=readl(c->shared+AMP_CORE3_TX+AMP_PUBLISH);
        if(generation!=c->rx_generation) {
            rmb();
            memcpy_fromio(c->reply,c->shared+AMP_CORE3_TX,AMP_FRAME_MAX);
            rmb();
            c->rx_generation=generation;
            if(c->hold_next) {c->ack_held=true;c->held_generation=generation;c->hold_next=false;}
            else writel(generation,c->shared+AMP_CORE3_TX+AMP_ACK);
            c->rx_count++;
            n=get_unaligned_le16(c->reply+10);
            c->last_rx_error=n>AMP_PAYLOAD_MAX?-R_LENGTH:amp_decode(c->reply,AMP_HEADER_BYTES+n,&response);
            if(c->last_rx_error) {
                WRITE_ONCE(c->require_hello,true);c->bad_rx++; ret=-EPROTO; goto out;
            }
            if(response.session!=request.session) {c->last_rx_error=-R_SESSION;c->stale++;continue;}
            if(response.epoch!=readq(c->shared+AMP_SERVICE_EPOCH)) {
                WRITE_ONCE(c->require_hello,true);c->last_rx_error=-R_EPOCH;c->bad_rx++;ret=-EPROTO;goto out;
            }
            if(c->peer_seen && response.seq!=c->peer_sequence+1U) {
                WRITE_ONCE(c->require_hello,true);c->last_rx_error=-R_SEQUENCE;c->bad_rx++;ret=-EPROTO;goto out;
            }
            c->peer_sequence=response.seq;c->peer_seen=true;
            if(request.type==AMP_HELLO) WRITE_ONCE(c->require_hello,false);
            c->reply_len=AMP_HEADER_BYTES+n;
            c->reply_pending=true;
            ret=count;
            goto out;
        }
        if(time_after_eq(jiffies,deadline)) {ret=-ETIMEDOUT;goto timeout;}
        usleep_range(50,100);
    }
timeout:
    WRITE_ONCE(c->require_hello,true);
    c->timeouts++;
out:
    mutex_unlock(&c->lock);
    return ret;
}
static long ipc_ioctl(struct file *file,unsigned int command,unsigned long arg)
{
    struct core3 *c=file->private_data;
    struct amp_test_snapshot s;
    u8 raw[AMP_FRAME_MAX];
    long ret=0;
    if(command!=AMP_IOC_SNAPSHOT && (!fault_tests || !capable(CAP_SYS_RAWIO))) return -EPERM;
    mutex_lock(&c->lock);
    switch(command) {
    case AMP_IOC_RAW_ONCE:
        if(c->reply_pending) ret=-EBUSY; else c->raw_once=true;
        break;
    case AMP_IOC_HOLD_ACK:
        if(c->hold_next || c->ack_held || c->reply_pending) ret=-EBUSY;else c->hold_next=true;
        break;
    case AMP_IOC_RELEASE_ACK:
        if(c->ack_held) {
            writel(c->held_generation,c->shared+AMP_CORE3_TX+AMP_ACK);
            c->ack_held=false;
        }
        c->hold_next=false;
        break;
    case AMP_IOC_REBASE_PEER:
        c->peer_seen=false;
        break;
    case AMP_IOC_PAUSE_HOST_HB: {
        u32 ms;
        if(copy_from_user(&ms,(void __user *)arg,sizeof(ms))) {ret=-EFAULT;break;}
        if(!ms || ms>1200) {ret=-EINVAL;break;}
        WRITE_ONCE(c->host_pause_until,jiffies+msecs_to_jiffies(ms));
        break;
    }
    case AMP_IOC_SNAPSHOT:
        memset(&s,0,sizeof(s));
        s.linux_tx=c->tx_count;s.linux_rx=c->rx_count;s.bad_rx=c->bad_rx;
        s.timeouts=c->timeouts;s.stale=c->stale;s.aborted=c->aborted;
        s.core3_rx=readq(c->shared+AMP_C3_RX_COUNT);s.core3_tx=readq(c->shared+AMP_C3_TX_COUNT);
        s.core3_bad=readq(c->shared+AMP_C3_BAD_COUNT);s.service_epoch=readq(c->shared+AMP_SERVICE_EPOCH);
        s.peer_timeouts=readq(c->shared+AMP_C3_TIMEOUTS);s.busy=readq(c->shared+AMP_C3_BUSY);
        s.wait_start=readq(c->shared+AMP_C3_WAIT_START);s.timeout_at=readq(c->shared+AMP_C3_TIMEOUT_AT);
        s.resets=readq(c->shared+AMP_C3_RESETS);s.heartbeat=readq(c->shared+32);s.freq=readq(c->shared+16);
        s.boot_token=readq(c->shared+24);
        s.host_heartbeat=READ_ONCE(c->host_hb);s.host_lost=READ_ONCE(c->hb_lost_count);
        s.host_restored=READ_ONCE(c->hb_restored_count);
        smp_rmb();s.host_lost_active=READ_ONCE(c->hb_lost);s.require_hello=READ_ONCE(c->require_hello);
        s.peer_lost=readq(c->shared+AMP_PEER_HB_LOST);s.peer_restored=readq(c->shared+AMP_PEER_HB_RESTORED);
        s.host_detection_ns=READ_ONCE(c->hb_detection_ns);s.peer_detection_ticks=readq(c->shared+AMP_PEER_HB_DETECTION_TICKS);
        s.core3_error=readl(c->shared+AMP_C3_LAST_ERROR);s.last_rx_error=c->last_rx_error;
        s.rx_publish=readl(c->shared+AMP_CORE3_TX+AMP_PUBLISH);s.rx_ack=readl(c->shared+AMP_CORE3_TX+AMP_ACK);
        memcpy_fromio(raw,c->shared+AMP_CORE3_TX,sizeof(raw));s.rx_crc=amp_crc32(raw,sizeof(raw));
        if(copy_to_user((void __user *)arg,&s,sizeof(s))) ret=-EFAULT;
        break;
    default:ret=-ENOTTY;
    }
    mutex_unlock(&c->lock);
    return ret;
}
static const struct file_operations ipc_fops={
    .owner=THIS_MODULE,.open=ipc_open,.release=ipc_release,
    .read=ipc_read,.write=ipc_write,.llseek=no_llseek,.unlocked_ioctl=ipc_ioctl,
};
static void ipc_misc_remove(void *data) { misc_deregister(data); }
static int ipc_misc_register(struct core3 *c,struct device *dev)
{
    int ret;
    atomic_set(&c->opened,0);
    c->misc.minor=MISC_DYNAMIC_MINOR; c->misc.name="p5-core3";
    c->misc.fops=&ipc_fops; c->misc.parent=dev; c->misc.mode=0600;
    ret=misc_register(&c->misc);
    if(ret) return ret;
    return devm_add_action_or_reset(dev,ipc_misc_remove,&c->misc);
}
static ssize_t stats_show(struct device *dev,struct device_attribute *a,char *buf)
{
    struct core3 *c=dev_get_drvdata(dev);
    ssize_t ret;
    mutex_lock(&c->lock);
    ret=scnprintf(buf,PAGE_SIZE,"linux_tx=%llu linux_rx=%llu bad_rx=%llu timeouts=%llu stale=%llu core3_rx=%llu core3_tx=%llu core3_bad=%llu service_epoch=%llu peer_timeouts=%llu busy=%llu resets=%llu aborted=%llu last_core_error=%u last_rx_error=%d fault_tests=%u\n",
        c->tx_count,c->rx_count,c->bad_rx,c->timeouts,c->stale,
        readq(c->shared+AMP_C3_RX_COUNT),readq(c->shared+AMP_C3_TX_COUNT),
        readq(c->shared+AMP_C3_BAD_COUNT),readq(c->shared+AMP_SERVICE_EPOCH),
        readq(c->shared+AMP_C3_TIMEOUTS),readq(c->shared+AMP_C3_BUSY),
        readq(c->shared+AMP_C3_RESETS),c->aborted,readl(c->shared+AMP_C3_LAST_ERROR),c->last_rx_error,fault_tests);
    mutex_unlock(&c->lock);
    return ret;
}
static DEVICE_ATTR_RO(stats);
static ssize_t live_show(struct device *dev,struct device_attribute *a,char *buf)
{
    struct core3 *c=dev_get_drvdata(dev);
    /* Read-only progress used by parent to kill its child while write waits. */
    return scnprintf(buf,PAGE_SIZE,"tx=%llu aborted=%llu\n",READ_ONCE(c->tx_count),READ_ONCE(c->aborted));
}
static DEVICE_ATTR_RO(live);
