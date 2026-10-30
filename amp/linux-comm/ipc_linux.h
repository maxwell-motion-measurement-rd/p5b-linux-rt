/* Included after struct core3 in the experimental loader. */
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
    mutex_unlock(&c->lock);
    atomic_set(&c->opened,0);
    return 0;
}
static ssize_t ipc_read(struct file *file,char __user *buf,size_t count,loff_t *pos)
{
    struct core3 *c=file->private_data;
    int ret;
    mutex_lock(&c->lock);
    if(!c->reply_pending) ret=-EAGAIN;
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
       readl(c->shared+4)!=3 || readl(c->shared+40)!=1) {ret=-EHOSTDOWN;goto out;}
    if(c->reply_pending) {ret=-EBUSY;goto out;}
    if(copy_from_user(c->outgoing,buf,count)) {ret=-EFAULT;goto out;}
    ret=amp_decode(c->outgoing,count,&request);
    if(ret) {ret=-EINVAL;goto out;}
    deadline=jiffies+msecs_to_jiffies(100);
    /* Drain stale replies, which can otherwise block the peer's single slot. */
    generation=readl(c->shared+AMP_CORE3_TX+AMP_PUBLISH);
    if(generation!=c->rx_generation) {
        c->rx_generation=generation;
        writel(generation,c->shared+AMP_CORE3_TX+AMP_ACK);
        c->stale++;
    }
    while(readl(c->shared+AMP_LINUX_TX+AMP_ACK)!=c->tx_generation) {
        if(time_after_eq(jiffies,deadline)) {ret=-ETIMEDOUT;goto timeout;}
        usleep_range(50,100);
    }
    memcpy_toio(c->shared+AMP_LINUX_TX,c->outgoing,count);
    wmb();
    writel(++c->tx_generation,c->shared+AMP_LINUX_TX+AMP_PUBLISH);
    c->tx_count++;
    for(;;) {
        generation=readl(c->shared+AMP_CORE3_TX+AMP_PUBLISH);
        if(generation!=c->rx_generation) {
            rmb();
            memcpy_fromio(c->reply,c->shared+AMP_CORE3_TX,AMP_FRAME_MAX);
            rmb();
            c->rx_generation=generation;
            writel(generation,c->shared+AMP_CORE3_TX+AMP_ACK);
            c->rx_count++;
            n=get_unaligned_le16(c->reply+10);
            if(n>AMP_PAYLOAD_MAX || amp_decode(c->reply,AMP_HEADER_BYTES+n,&response)) {
                c->bad_rx++; ret=-EPROTO; goto out;
            }
            if(response.session!=request.session) {c->stale++;continue;}
            c->reply_len=AMP_HEADER_BYTES+n;
            c->reply_pending=true;
            ret=count;
            goto out;
        }
        if(time_after_eq(jiffies,deadline)) {ret=-ETIMEDOUT;goto timeout;}
        usleep_range(50,100);
    }
timeout:
    c->timeouts++;
out:
    mutex_unlock(&c->lock);
    return ret;
}
static const struct file_operations ipc_fops={
    .owner=THIS_MODULE,.open=ipc_open,.release=ipc_release,
    .read=ipc_read,.write=ipc_write,.llseek=no_llseek,
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
    ret=scnprintf(buf,PAGE_SIZE,"linux_tx=%llu linux_rx=%llu bad_rx=%llu timeouts=%llu stale=%llu core3_rx=%llu core3_tx=%llu core3_bad=%llu\n",
        c->tx_count,c->rx_count,c->bad_rx,c->timeouts,c->stale,
        readq(c->shared+AMP_C3_RX_COUNT),readq(c->shared+AMP_C3_TX_COUNT),
        readq(c->shared+AMP_C3_BAD_COUNT));
    mutex_unlock(&c->lock);
    return ret;
}
static DEVICE_ATTR_RO(stats);
