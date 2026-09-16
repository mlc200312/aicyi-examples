#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0-1: WorkerId 生命周期自我中断与关闭竞态修复。"""
import sys

sys.path.insert(0, "/Users/liangchaomin/workspace/develop/aicyi-examples/.qoder-patch")
from patch_base import apply  # noqa: E402

HB = "aicyi-midware/aicyi-midware-redis/src/main/java/io/github/aicyi/midware/redis/id/WorkerIdHeartbeat.java"
MGR = "aicyi-midware/aicyi-midware-redis/src/main/java/io/github/aicyi/midware/redis/id/WorkerIdManager.java"

apply(HB, [
    (
        """    /**
     * 懒初始化（构造期 lease 尚未赋值）：显式构造而非 Executors 工厂方法（阿里手册），
     * 守护线程避免异常路径未 stop 时阻塞 JVM 退出
     */
    private ScheduledExecutorService scheduler;
""",
        """    /**
     * 懒初始化（构造期 lease 尚未赋值）：显式构造而非 Executors 工厂方法（阿里手册），
     * 守护线程避免异常路径未 stop 时阻塞 JVM 退出。
     * volatile：scheduler() 内由管理线程写入，cancelTask() 内可能由心跳线程读取
     */
    private volatile ScheduledExecutorService scheduler;
""",
    ),
    (
        """    private ScheduledFuture<?> future;
""",
        """    /**
     * 心跳任务句柄；volatile 保证 start()（管理线程）与停止路径（可能是心跳线程自身）之间的可见性
     */
    private volatile ScheduledFuture<?> future;

    /**
     * 停止标记：先于 future/scheduler 置位，使心跳任务在句柄尚未回填时也能自行终止，
     * 避免「首次续约即失败 -> 停止路径读到 null 句柄 -> 周期任务永不取消」的线程泄漏
     */
    private volatile boolean stopped;
""",
    ),
    (
        """        future = scheduler().scheduleAtFixedRate(() -> {
            try {
                boolean ok = allocator.renew(lease);

                if (!ok) {
                    logger.error("WorkerId renew failed, lease lost. workerId={}", lease.getWorkerId());

                    onLeaseLost.run();
""",
        """        future = scheduler().scheduleAtFixedRate(() -> {
            if (stopped) {
                return;
            }

            try {
                boolean ok = allocator.renew(lease);

                if (!ok) {
                    logger.error("WorkerId renew failed, lease lost. workerId={}", lease.getWorkerId());

                    // 先置停止标记再回调：本实例自此不再续约，恢复由 WorkerIdManager 重建新心跳承担
                    stopped = true;

                    onLeaseLost.run();
""",
    ),
    (
        """    public void stop() {
        if (future != null) {
            future.cancel(true);
        }

        if (scheduler != null) {
            scheduler.shutdownNow();
        }

        try {
            allocator.release(lease);
        } catch (Exception e) {
            logger.warn("release failed", e);
        }
    }

    /**
     * lease 已经丢了，不能 release（防误删）
     */
    private void stopWithoutRelease() {
        if (future != null) {
            future.cancel(true);
        }

        if (scheduler != null) {
            scheduler.shutdownNow();
        }
    }
}""",
        """    public void stop() {
        cancelTask();

        try {
            allocator.release(lease);
        } catch (Exception e) {
            logger.warn("release failed", e);
        }
    }

    /**
     * lease 已经丢了，不能 release（防误删）
     */
    private void stopWithoutRelease() {
        cancelTask();
    }

    /**
     * 取消周期任务并关闭线程池。
     * <p>使用 cancel(false) + shutdown() 而非 cancel(true) + shutdownNow()：
     * 本方法可能由心跳任务自身在租约丢失的恢复路径上调用，中断当前线程会把中断标志带入随后
     * WorkerIdAllocator#allocate 的 Redis 调用，使自动恢复必然失败；
     * shutdown() 对周期任务的默认策略即为不再执行后续周期，无需中断正在执行的任务
     */
    private void cancelTask() {
        stopped = true;

        ScheduledFuture<?> task = future;
        if (task != null) {
            task.cancel(false);
        }

        ScheduledExecutorService executor = scheduler;
        if (executor != null) {
            executor.shutdown();
        }
    }
}""",
    ),
])

apply(MGR, [
    (
        """    /**
     * lease 是否仍有效
     */
    private volatile boolean leaseValid = false;
""",
        """    /**
     * lease 是否仍有效
     */
    private volatile boolean leaseValid = false;

    /**
     * 停止标记：stop() 置位、start() 清零。
     * 心跳线程的自动恢复必须先检查该标记，否则容器关闭后仍会重新申请租约并新建心跳线程，
     * 造成 Redis workerId key 与线程双重泄漏（key 直到 TTL 才释放，期间挤占其他节点的名额）
     */
    private volatile boolean stopped = false;
""",
    ),
    (
        """        leaseValid = false;

        if (autoRecover) {
            try {
                start();
                logger.info("WorkerId recovered, new workerId={}", lease.getWorkerId());
            } catch (Exception e) {
                logger.error("WorkerId auto recover failed", e);
            }
        }
    }
""",
        """        leaseValid = false;

        if (stopped) {
            logger.info("WorkerIdManager already stopped, skip auto recover");
            return;
        }

        if (autoRecover) {
            recover();
        }
    }

    /**
     * 租约丢失后的自动恢复，由心跳线程回调。
     * <p>旧心跳已自行置停止标记并在回调返回后终止，此处只解除引用：若在恢复路径上对旧心跳执行
     * 带中断的取消，会中断当前正在执行恢复的线程，中断标志随即带入
     * {@link WorkerIdAllocator#allocate} 的 Redis 调用，使恢复必然失败。
     * <p>单次恢复：失败后不再重试，此时 leaseValid=false，发号器 fail-closed 拒绝发号，
     * 需人工介入或重启（由 SmartLifecycle#start 重新申请）
     */
    private synchronized void recover() {
        // 取得锁后二次判定：stop() 可能已在等待队列中先行完成，此时不得重新申请租约
        if (stopped) {
            logger.info("WorkerIdManager stopped during recover, skip");
            return;
        }

        heartbeat = null;

        try {
            acquire();
            logger.info("WorkerId recovered, new workerId={}", lease.getWorkerId());
        } catch (Exception e) {
            logger.error("WorkerId auto recover failed, id generation stays disabled until restart", e);
        }
    }
""",
    ),
    (
        """    /**
     * 幂等启动：重复调用会先停止旧心跳再重新申请租约
     */
    @Override
    public synchronized void start() {

        if (heartbeat != null) {
            // 租约丢失场景下 release 会被服务端以 token 不匹配拒绝，无害
            heartbeat.stop();
            heartbeat = null;
        }

        leaseValid = false;

        lease = allocator.allocate();

        heartbeat = new WorkerIdHeartbeat(
                allocator,
                lease,
                heartbeatSeconds,
                this::markLeaseLost
        );

        heartbeat.start();

        leaseValid = true;
        running = true;

        logger.info("WorkerIdManager started workerId={}", lease.getWorkerId());
    }

    @Override
    public synchronized void stop() {
        leaseValid = false;
""",
        """    /**
     * 幂等启动：重复调用会先停止旧心跳（并释放其租约）再重新申请租约
     */
    @Override
    public synchronized void start() {

        stopped = false;

        if (heartbeat != null) {
            heartbeat.stop();
            heartbeat = null;
        }

        acquire();
    }

    /**
     * 申请租约并启动心跳；调用方必须持有本对象监视器
     */
    private void acquire() {

        leaseValid = false;

        lease = allocator.allocate();

        heartbeat = new WorkerIdHeartbeat(
                allocator,
                lease,
                heartbeatSeconds,
                this::markLeaseLost
        );

        heartbeat.start();

        leaseValid = true;
        running = true;

        logger.info("WorkerIdManager started workerId={}", lease.getWorkerId());
    }

    @Override
    public synchronized void stop() {
        // 先置停止标记：与心跳线程的 recover() 互斥，杜绝容器关闭后被自动恢复重新拉起
        stopped = true;
        leaseValid = false;
""",
    ),
])

print("P0-1 done")
