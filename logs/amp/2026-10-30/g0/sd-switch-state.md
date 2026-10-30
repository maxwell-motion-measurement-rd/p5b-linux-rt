# SD 换卡前关机状态

用户已选择读卡器换卡。串口 COM3 已执行 sync、打印 __AMP_SYNC_COMPLETE__，随后执行 poweroff。服务停止、TERM/KILL、swap 停用均有日志，最后输出为 Unmounting local filesystems...。

首次监听 40 秒及追加监听 45 秒均未观察到 Power down／System halted。随后通过串口 BREAK+w 请求阻塞任务信息，无输出。没有强制复位、没有覆盖启动文件，不能据此宣称关机完成。

用户随后确认“板子已经断电”。已记录为用户报告断电，不能补写为已观察到正常关机完成。接下来通过读卡器识别卡并先备份实际内容。关机末段静默的具体原因仍未确定。

原 rootfs 的 /etc/init.d/umountfs 会执行 umount -f -a -r 并丢弃输出，之后 /etc/init.d/halt 执行 halt -d -f -p；因此最后一行本身不能证明卡在某一具体系统调用。

证据：board-shutdown-before-sd.txt、board-shutdown-wait.txt、shutdown-blocked-tasks.txt。
