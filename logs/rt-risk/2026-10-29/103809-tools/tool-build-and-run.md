# ARM64工具准备与测量条件

日期：2026-10-29，Asia/Shanghai。SSH入口本轮已恢复，无需修改密钥ACL或复制凭据。原Ubuntu GCC9.2.0和recipe-sysroot可用，未修改板子启动镜像或内核。

## 工具适配过程

先从kernel.org下载rt-tests1.10，源码XZ SHA256为3740ad97b164a1cd77d9ee32bba23a4a0b2495a76468bcf40ff60b55c2a3a709。静态链接numactl2.0.12构建cyclictest，板端运行在NUMA初始化时退出，返回1；未进入测量。保留失败工具和日志，不把工具初始化失败记为内核实时性能失败。

随后采用kernel.org官方older目录的rt-tests1.0，使用上游Makefile支持的NUMA=0构建，未修改上游测量代码。源码XZ SHA256：aea85fd8eda8c1d96e9d32a019bfd4a1d2e0d362971d97838996f49d1af2d470。

最终cyclictest摘要：131c6a2d9fff8950a48939e970a82ec819d5bca06e98371f5dd1d0333b9ace6c。动态依赖仅librt.so.1、libpthread.so.0、libc.so.6，加载器为/lib/ld-linux-aarch64.so.1。与原始RT用户空间匹配后，5秒自检返回0，取得5000样本，最小43μs、平均46μs、最大52μs，直方图无溢出。

附加负载工具rtload为本次独立编写的有限时长SCHED_OTHER负载程序，不作为延迟测量工具。源码在work/scripts/rtload.c，构建命令在rtload-build.sh；ARM64二进制摘要441fcb946f6a9e4b5ce53055d9c055abb7902db802244b616fa5416e7e61ac3d。CPU模式为整数运算，内存模式固定分配两个64MiB缓冲区，总计128MiB。两种模式各2秒预检正常退出，分别绑定CPU0、CPU2。

源码和构建日志保存在sources/及仓库work/scripts/；二进制在work/artifacts/rt-audit-tools/。经串口传输到/tmp/rt-audit-tools并核对摘要，临时关闭TTY回显以传输八进制编码字节，完成后已恢复TTY设置；没有安装到系统/bin、/lib或改变Shell。

## 测量参数

```text
cyclictest --laptop -a1 -t1 -p80 --policy=fifo -m -i1000 -D10m -q -h2000
```

单线程、CPU1、FIFO80、绝对周期CLOCK_MONOTONIC、1ms、mlockall、直方图上限2000μs，静默输出。--laptop在此用于跳过cpu_dma_latency写入，保持原始CPU休眠行为；不是为了调整为省电模式。未写isolcpus、频率、IRQ亲和性或RT预算。T00开始uptime为2769.68秒，wrapper PID1222，测量进程PID1223。

5秒自检是先行工具验证，T00是10分钟冒烟测量，不能把这些结果称为30分钟正式场景或产品业务验收。串口采样命令及其时间在poll日志中保留；它们也属于本次测量背景开销。
