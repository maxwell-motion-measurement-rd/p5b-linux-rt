// SPDX-License-Identifier: GPL-2.0
/* Experimental one-shot loader. Loading this module does not wake Core3. */
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of_address.h>
#include <linux/io.h>
#include <linux/ioport.h>
#include <linux/firmware.h>
#include <linux/firmware/xlnx-zynqmp.h>
#include <linux/cpu.h>
#include <linux/mutex.h>
#include <linux/slab.h>
#include <linux/sizes.h>
#include <asm/unaligned.h>
#include <asm/sysreg.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/delay.h>
#include <linux/jiffies.h>
#include <linux/capability.h>
#include <linux/kthread.h>
#include <linux/sched/signal.h>
#include "../protocol/amp_fault.h"
static bool fault_tests;
module_param(fault_tests,bool,0444);
#include "../protocol/amp_wire.c"
#include "../protocol/amp_slots.h"

struct core3 {
	void __iomem *private, *shared;
	const struct zynqmp_eemi_ops *ops;
	struct mutex lock;
	bool attempted;
	int last_result;
    struct miscdevice misc;
    atomic_t opened;
    u32 tx_generation, rx_generation;
    u64 tx_count, rx_count, bad_rx, timeouts, stale;
    u8 outgoing[AMP_FRAME_MAX], reply[AMP_FRAME_MAX];
    unsigned reply_len;
    bool reply_pending;
    bool raw_once,hold_next,ack_held,peer_seen;
    u32 held_generation,peer_sequence;
    int last_rx_error;
    u64 aborted;
    struct task_struct *hb_task;
    bool running,hb_lost,require_hello;
    unsigned long host_pause_until,last_hb_change;
    u64 host_hb,last_peer_hb,hb_lost_count,hb_restored_count,hb_detection_ns;
};

#include "ipc_linux.h"

static ssize_t status_show(struct device *dev, struct device_attribute *a, char *buf)
{
	struct core3 *c = dev_get_drvdata(dev);
	u8 s[104];
	u32 state = ~0U, requirements, usage;
	int ret;

	mutex_lock(&c->lock);
	ret = c->ops->get_node_status(NODE_APU_3, &state, &requirements, &usage);
	memcpy_fromio(s, c->shared, sizeof(s));
	ret = scnprintf(buf, PAGE_SIZE,
		"attempted=%u result=%d pm_query=%d pm_state=%u magic=%08x version=%u core=%u el=%u freq=%llu token=%llu heartbeat=%llu state=%u reason=%u host_freq=%llu initial_freq=%llu configured_freq=%llu esr=%llx elr=%llx far=%llx\n",
		c->attempted, c->last_result, ret, state,
		get_unaligned_le32(s), get_unaligned_le32(s + 4),
		get_unaligned_le32(s + 8), get_unaligned_le32(s + 12),
		get_unaligned_le64(s + 16), get_unaligned_le64(s + 24),
		get_unaligned_le64(s + 32), get_unaligned_le32(s + 40),
		get_unaligned_le32(s + 44), get_unaligned_le64(s + 48),
		get_unaligned_le64(s + 88), get_unaligned_le64(s + 96),
		get_unaligned_le64(s + 64), get_unaligned_le64(s + 72),
		get_unaligned_le64(s + 80));
	mutex_unlock(&c->lock);
	return ret;
}
static DEVICE_ATTR_RO(status);

static ssize_t start_store(struct device *dev, struct device_attribute *a,
			   const char *buf, size_t count)
{
	struct core3 *c = dev_get_drvdata(dev);
	const struct firmware *fw;
	u32 state, requirements, usage;
	u64 counter_freq;
	__le64 frequency_le;
	void *readback;
	int ret;

	if (!sysfs_streq(buf, "1"))
		return -EINVAL;
	mutex_lock(&c->lock);
	if (c->attempted) {
		ret = -EALREADY;
		goto out;
	}
	/* Do not overwrite RAM if firmware considers Core3 running or sleeping. */
	ret = c->ops->get_node_status(NODE_APU_3, &state, &requirements, &usage);
	if (ret)
		goto out;
	if (state != 0) { /* PM_PROC_STATE_FORCEDOFF in matching PMUFW */
		ret = -EBUSY;
		goto out;
	}
	counter_freq = read_sysreg(cntfrq_el0);
	if (counter_freq < 10 || counter_freq > U32_MAX) {
		ret = -EINVAL;
		goto out;
	}
	frequency_le = cpu_to_le64(counter_freq);
	ret = request_firmware(&fw, "p5-core3-comm.bin", dev);
	if (ret)
		goto out;
	if (!fw->size || fw->size > 0x10000) {
		ret = -EFBIG;
		goto release;
	}
	readback = kmalloc(fw->size, GFP_KERNEL);
	if (!readback) {
		ret = -ENOMEM;
		goto release;
	}
	/* Map is Normal-NC, matching the EL3 page tables, not Device memory. */
	memset_io(c->private, 0, 0x20000);
	memset_io(c->shared, 0, 4096);
    writel(0,c->shared+AMP_LINUX_TX+AMP_PUBLISH);
    writel(0,c->shared+AMP_CORE3_TX+AMP_ACK);
	memcpy_toio(c->shared + 48, &frequency_le, sizeof(frequency_le));
	iowrite32(0x46525132, c->shared + 56);
	memcpy_toio(c->private, fw->data, fw->size);
	mb();
	memcpy_fromio(readback, c->private, fw->size);
	ret = memcmp(readback, fw->data, fw->size) ? -EIO : 0;
	kfree(readback);
	if (ret)
		goto release;
	/* Keep module pinned even if wake ACK fails: hardware state is uncertain.
	 * There is deliberately no retry, force-reset, stop or unload-after-start.
	 */
	if (!try_module_get(THIS_MODULE)) {
		ret = -ENODEV;
		goto release;
	}
	c->attempted = true;
	mb();
	ret = c->ops->request_wakeup(NODE_APU_3, true, 0x60000000ULL,
				     ZYNQMP_PM_REQUEST_ACK_BLOCKING);
	if(!ret) WRITE_ONCE(c->running,true);
    dev_info(dev, "one-shot PMU wake result=%d; inspect status; no automatic retry\n", ret);
release:
	release_firmware(fw);
out:
	c->last_result = ret;
	mutex_unlock(&c->lock);
	return ret ? ret : count;
}
static DEVICE_ATTR_WO(start);

static struct attribute *attrs[] = { &dev_attr_status.attr, &dev_attr_start.attr, &dev_attr_stats.attr, &dev_attr_live.attr, NULL };
static const struct attribute_group group = { .attrs = attrs };

static void remove_group(void *dev)
{
	sysfs_remove_group(&((struct device *)dev)->kobj, &group);
}

static void __iomem *map_reserved(struct device *dev, int index, resource_size_t expected)
{
	struct device_node *node;
	struct resource r;
	int ret;

	node = of_parse_phandle(dev->of_node, "memory-region", index);
	if (!node)
		return ERR_PTR(-EINVAL);
	ret = of_address_to_resource(node, 0, &r);
	if (!of_property_read_bool(node, "no-map"))
		ret = -EINVAL;
	of_node_put(node);
	if (ret || r.start != expected || resource_size(&r) != SZ_2M)
		return ERR_PTR(-EINVAL);
	if (!devm_request_mem_region(dev, r.start, resource_size(&r), dev_name(dev)))
		return ERR_PTR(-EBUSY);
	return devm_ioremap_wc(dev, r.start, resource_size(&r)) ?: ERR_PTR(-ENOMEM);
}

static int core3_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct core3 *c;
	int ret;

	if (num_possible_cpus() != 3 || !cpu_possible(0) ||
	    !cpu_possible(1) || !cpu_possible(2))
		return -EINVAL;
	c = devm_kzalloc(dev, sizeof(*c), GFP_KERNEL);
	if (!c)
		return -ENOMEM;
	c->ops = zynqmp_pm_get_eemi_ops();
	if (!c->ops || !c->ops->get_node_status || !c->ops->request_wakeup)
		return -ENODEV;
	c->private = map_reserved(dev, 0, 0x60000000);
	if (IS_ERR(c->private))
		return PTR_ERR(c->private);
	c->shared = map_reserved(dev, 1, 0x60200000);
	if (IS_ERR(c->shared))
		return PTR_ERR(c->shared);
	mutex_init(&c->lock);
    ret=heartbeat_register(c,dev);
    if(ret) return ret;
    ret=ipc_misc_register(c,dev);
    if(ret) return ret;
	platform_set_drvdata(pdev, c);
	ret = sysfs_create_group(&dev->kobj, &group);
	if (ret)
		return ret;
	ret = devm_add_action_or_reset(dev, remove_group, dev);
	if (ret)
		return ret;
	dev_info(dev, "mapped reserved DDR; Core3 NOT started; explicit start required\n");
	return 0;
}

static const struct of_device_id matches[] = {
	{ .compatible = "p5,core3-heartbeat-experiment" }, {}
};
MODULE_DEVICE_TABLE(of, matches);
static struct platform_driver core3_driver = {
	.probe = core3_probe,
	.driver = { .name = "p5-core3-heartbeat", .of_match_table = matches,
		    .suppress_bind_attrs = true },
};
module_platform_driver(core3_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("P5 experimental one-shot PMU Core3 heartbeat loader");
MODULE_FIRMWARE("p5-core3-comm.bin");
