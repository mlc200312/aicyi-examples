#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-7/P1-8/P1-9: 锁异常统一包装 + LockException 错误码语义 + DistributedLock SPI 受检异常收敛。"""
import sys

sys.path.insert(0, "/Users/liangchaomin/workspace/develop/aicyi-examples/.qoder-patch")
from patch_base import apply, ROOT  # noqa: E402


def write_full(rel_path, content):
    path = ROOT + "/" + rel_path
    with open(path, "r", encoding="utf-8") as f:
        original = f.read()
    if not original.endswith("\n"):
        content = content.rstrip("\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK   %s (full rewrite)" % rel_path)


# ---------------------------------------------------------------- BaseException
apply("aicyi-commons/aicyi-commons-lang/src/main/java/io/github/aicyi/commons/lang/exception/BaseException.java", [
    (
        """    public BaseException(IResultCode resultCode) {
        this(resultCode.getCode(), resultCode.getMessage());
    }
""",
        """    public BaseException(IResultCode resultCode) {
        this(resultCode.getCode(), resultCode.getMessage());
    }

    /**
     * 以错误码枚举 + 自定义消息构造：子类应优先使用本构造器而非直接传 code 整数，
     * 避免绕开枚举导致码位散落、无法在全局异常处理器侧统一归因
     *
     * @param resultCode 错误码枚举，不可为 null
     * @param message    自定义消息，覆盖枚举默认消息
     */
    public BaseException(IResultCode resultCode, String message) {
        this(resultCode.getCode(), message);
    }

    /**
     * @param resultCode 错误码枚举，不可为 null
     * @param message    自定义消息，覆盖枚举默认消息
     * @param cause      原始异常，保留根因堆栈
     */
    public BaseException(IResultCode resultCode, String message, Throwable cause) {
        this(resultCode.getCode(), message, cause);
    }
""",
    ),
])

# ---------------------------------------------------------------- LockException
write_full("aicyi-midware/aicyi-midware-redis/src/main/java/io/github/aicyi/midware/redis/lock/LockException.java", '''package io.github.aicyi.midware.redis.lock;

import io.github.aicyi.commons.lang.CommonResultCode;
import io.github.aicyi.commons.lang.IResultCode;
import io.github.aicyi.commons.lang.exception.BaseException;

/**
 * 分布式锁异常：屏蔽 Redisson 原生异常类型，使业务侧只需面向本类型与错误码编程。
 * <p>
 * 码位约定（经全局异常处理器统一返回 HTTP 200 + 业务码）：
 * <ul>
 *     <li>{@link CommonResultCode#SYSTEM_ERROR} 50001：锁基础设施故障（连接中断、脚本执行失败等）</li>
 *     <li>{@link CommonResultCode#BUSINESS_ERROR} 40002：调用方使用错误（如未持有锁即释放），
 *     归业务错误段避免被网关/监控误判为服务端故障</li>
 * </ul>
 *
 * @author Mr.Min
 * @date 2025/8/18
 **/
public class LockException extends BaseException {

    private static final long serialVersionUID = 1L;

    /**
     * 锁基础设施故障（系统级 50001）
     *
     * @param message 失败描述，应包含锁名以便定位资源
     */
    public LockException(String message) {
        super(CommonResultCode.SYSTEM_ERROR, message);
    }

    /**
     * 锁基础设施故障（系统级 50001）
     *
     * @param message 失败描述，应包含锁名以便定位资源
     * @param cause   中间件原生异常，保留根因堆栈但不对外暴露类型
     */
    public LockException(String message, Throwable cause) {
        super(CommonResultCode.SYSTEM_ERROR, message, cause);
    }

    /**
     * 指定错误码构造，用于区分「基础设施故障」与「调用方使用错误」
     *
     * @param resultCode 错误码枚举，不可为 null
     * @param message    失败描述
     */
    public LockException(IResultCode resultCode, String message) {
        super(resultCode, message);
    }

    /**
     * 指定错误码构造，用于区分「基础设施故障」与「调用方使用错误」
     *
     * @param resultCode 错误码枚举，不可为 null
     * @param message    失败描述
     * @param cause      中间件原生异常，保留根因堆栈但不对外暴露类型
     */
    public LockException(IResultCode resultCode, String message, Throwable cause) {
        super(resultCode, message, cause);
    }
}''')

# ---------------------------------------------------------------- DistributedLock SPI
write_full("aicyi-commons/aicyi-commons-core/src/main/java/io/github/aicyi/commons/core/lock/DistributedLock.java", '''package io.github.aicyi.commons.core.lock;


import java.time.Duration;
import java.util.concurrent.Callable;

/**
 * 分布式锁
 * <p>
 * 一个 DistributedLock 实例绑定一个唯一资源。
 * <p>
 * 语义：
 * - lock：阻塞直到获取成功
 * - tryLock：按条件尝试获取
 * - unlock：仅当前持有者可释放
 * <p>
 * <b>异常契约</b>：本 SPI 不声明任何受检异常，避免调用方逐处 try/catch，
 * 也避免把实现方的中断/连接语义泄露为接口契约。
 * <ul>
 *     <li>参数非法（{@code waitTime}/{@code leaseTime} 为 null 或为负）→ {@link IllegalArgumentException}</li>
 *     <li>等待期间线程被中断 → 实现须先复原中断标志（{@link Thread#interrupt()}）再抛出运行时异常，
 *     不得静默吞掉中断状态</li>
 *     <li>锁基础设施故障（连接中断、脚本执行失败等）→ 实现自身的锁运行时异常（如 Redis 实现的 LockException），
 *     不得直接抛出中间件原生异常</li>
 *     <li>非持有者调用 {@link #unlock()} → 运行时异常（业务错误码段），不静默成功</li>
 * </ul>
 */
public interface DistributedLock {

    /**
     * 锁名称（资源标识）
     *
     * @return 构造时传入的资源名，恒非 null
     */
    String name();

    /**
     * 阻塞获取锁（默认策略）
     * <p>
     * 默认由实现决定：
     * - 是否自动续租
     * - 默认租约时间
     * <p>
     * 阻塞期间线程被中断时不返回，由实现复原中断标志后抛出运行时异常
     */
    void lock();

    /**
     * 阻塞获取锁（指定租约时间）
     * <p>
     * 租约到期自动释放，实现不应对该锁自动续租；需要自动续租请使用 {@link #lock()}
     *
     * @param leaseTime 租约时间，不可为 null、不可为负；需要「实现默认租约 + 自动续租」语义请调用 {@link #lock()}
     */
    void lock(Duration leaseTime);

    /**
     * 立即尝试获取锁，不阻塞、不等待
     *
     * @return true 获取成功；false 锁已被占用
     */
    boolean tryLock();

    /**
     * 指定等待时间尝试获取锁；租约策略与 {@link #lock()} 一致（由实现决定是否自动续租）
     *
     * @param waitTime 最长等待时间，不可为 null、不可为负；{@link Duration#ZERO} 表示不等待
     * @return true 获取成功；false 等待超时仍未获取到
     */
    boolean tryLock(Duration waitTime);

    /**
     * 指定等待时间和租约时间尝试获取锁
     *
     * @param waitTime  最长等待时间，不可为 null、不可为负；{@link Duration#ZERO} 表示不等待
     * @param leaseTime 租约时间，不可为 null、不可为负；到期自动释放，实现不应自动续租
     * @return true 获取成功；false 等待超时仍未获取到
     */
    boolean tryLock(Duration waitTime, Duration leaseTime);

    /**
     * 释放锁
     * <p>
     * 仅当前持有者可释放；当前线程不是持有者时实现须抛出运行时异常（业务错误码段），
     * 不得静默成功，否则会误删其他持有者的锁
     * <p>
     * 租约已到期自动释放时，实现可选择静默返回（幂等释放）
     */
    void unlock();

    /**
     * 当前线程是否持有锁
     *
     * @return true 当前调用线程为持有者
     */
    boolean isHeldByCurrentThread();

    /**
     * 锁是否被占用（任意线程/节点）
     *
     * @return true 锁已被持有；结果仅为瞬时快照，不可作为加锁前置判断（存在竞态）
     */
    boolean isLocked();

    /**
     * 强制释放（管理员能力）：不校验持有者身份
     * <p>
     * 会破坏正在持锁节点的业务一致性，仅用于运维兜底清理残留锁
     *
     * @return true 锁此前存在且已被释放
     */
    boolean forceUnlock();

    // =========================
    // Template Methods
    // =========================

    /**
     * 在锁保护下执行任务：阻塞获取锁 -> 执行 -> 释放锁
     * <p>
     * 无论任务成功或抛出异常，锁均会被释放
     *
     * @param task 待执行任务，不可为 null；任务失败应以运行时异常表达
     */
    default void execute(Runnable task) {
        lock();
        try {
            task.run();
        } finally {
            unlock();
        }
    }

    /**
     * 在锁保护下执行任务并返回结果：阻塞获取锁 -> 执行 -> 释放锁
     *
     * @param task 待执行任务，不可为 null
     * @param <T>  返回值类型
     * @return 任务返回值
     */
    default <T> T execute(Callable<T> task) {
        lock();
        try {
            return task.call();
        } catch (RuntimeException | Error e) {
            throw e;
        } catch (Exception e) {
            // Callable 声明的受检异常在此收敛为非受检：SPI 不向业务侧传播受检异常。
            // 需要区分失败原因的任务应抛出 BaseException 子类，由全局异常处理器映射错误码
            throw new IllegalStateException("Task failed under lock: " + name(), e);
        } finally {
            unlock();
        }
    }

    /**
     * 尝试执行任务：在 waitTime 内获取到锁才执行，否则直接返回 false，不阻塞业务线程
     *
     * @param waitTime 最长等待时间，不可为 null、不可为负
     * @param task     待执行任务，不可为 null；任务失败应以运行时异常表达
     * @return true 获取锁并执行完成；false 未获取到锁（任务未执行）
     */
    default boolean tryExecute(Duration waitTime, Runnable task) {
        boolean locked = tryLock(waitTime);
        if (!locked) {
            return false;
        }

        try {
            task.run();
            return true;
        } finally {
            unlock();
        }
    }

    /**
     * 尝试执行任务并返回结果：在 waitTime 内获取到锁才执行，否则返回 fallback
     *
     * @param waitTime 最长等待时间，不可为 null、不可为负
     * @param task     待执行任务，不可为 null
     * @param fallback 未获取到锁时的降级返回值，可为 null
     * @param <T>      返回值类型
     * @return 任务返回值；未获取到锁时返回 fallback
     */
    default <T> T tryExecute(
            Duration waitTime,
            Callable<T> task,
            T fallback
    ) {
        boolean locked = tryLock(waitTime);
        if (!locked) {
            return fallback;
        }

        try {
            return task.call();
        } catch (RuntimeException | Error e) {
            throw e;
        } catch (Exception e) {
            // 收敛受检异常口径与 execute(Callable) 保持一致
            throw new IllegalStateException("Task failed under lock: " + name(), e);
        } finally {
            unlock();
        }
    }
}''')

# ---------------------------------------------------------------- DistributedLockManager SPI
write_full("aicyi-commons/aicyi-commons-core/src/main/java/io/github/aicyi/commons/core/lock/DistributedLockManager.java", '''package io.github.aicyi.commons.core.lock;

/**
 * 分布式锁管理器：{@link DistributedLock} 的获取入口，由容器装配为单例供业务注入。
 * <p>
 * 实现须为无状态，可被多线程并发调用。
 *
 * @author Mr.Min
 * @date 2026/5/26
 **/
public interface DistributedLockManager {

    /**
     * 获取绑定指定资源的锁对象。
     * <p>
     * 返回的实例仅绑定资源名，不代表已持有锁；同一 name 的多次调用可以返回不同实例，
     * 因此调用方<b>不得缓存实例来判断持有状态</b>，持有状态须以
     * {@link DistributedLock#isHeldByCurrentThread()} 为准。
     *
     * @param name 锁名称（资源标识），不可为 null/空白；命名空间由实现决定，
     *             业务应保证跨服务唯一（建议 {@code 业务域:资源类型:资源ID}）
     * @return 锁对象，恒非 null
     */
    DistributedLock getLock(String name);
}''')

# ---------------------------------------------------------------- DistributedCacheLock
apply("aicyi-commons/aicyi-commons-core/src/main/java/io/github/aicyi/commons/core/cache/DistributedCacheLock.java", [
    (
        """            return null;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return null;
        }""",
        """            return null;
        } catch (RuntimeException e) {
            // SPI 已收敛受检异常：等待被中断时实现会复原中断标志并抛运行时异常，
            // 此处按中断标志识别，维持与旧版 catch InterruptedException 一致的降级语义（视为未取到锁）
            if (Thread.currentThread().isInterrupted()) {
                return null;
            }
            throw e;
        }""",
    ),
])

# ---------------------------------------------------------------- RedissonDistributedLock
write_full("aicyi-midware/aicyi-midware-redis/src/main/java/io/github/aicyi/midware/redis/lock/RedissonDistributedLock.java", '''package io.github.aicyi.midware.redis.lock;

import io.github.aicyi.commons.core.lock.DistributedLock;
import io.github.aicyi.commons.lang.Assert;
import io.github.aicyi.commons.lang.CommonResultCode;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;

import java.time.Duration;
import java.util.concurrent.TimeUnit;

/**
 * 基于 Redisson 的分布式锁实现。
 * <p>
 * 对外只暴露 {@link DistributedLock} 契约与 {@link LockException}：所有 Redisson 原生异常
 * （RedisException / RedisTimeoutException 等）在此统一收敛，业务侧无需感知锁的存储实现。
 *
 * @author Mr.Min
 * @date 2025/8/18
 **/
public class RedissonDistributedLock implements DistributedLock {

    private final String name;
    private final RLock lock;

    public RedissonDistributedLock(String name, RedissonClient redissonClient) {
        this.name = name;
        this.lock = redissonClient.getLock(name);
    }

    @Override
    public String name() {
        return name;
    }

    /**
     * 阻塞获取锁
     * <p>
     * 使用 Redisson watchdog 自动续租
     */
    @Override
    public void lock() {
        try {
            lock.lockInterruptibly();
        } catch (InterruptedException e) {
            throw interrupted("acquire lock", e);
        } catch (Exception e) {
            throw new LockException("Failed to acquire lock: " + name, e);
        }
    }

    /**
     * 阻塞获取锁（固定租约）
     * <p>
     * 不启用 watchdog
     */
    @Override
    public void lock(Duration leaseTime) {

        Assert.notNull(leaseTime, "leaseTime");

        validateDuration(leaseTime, "leaseTime");

        try {
            lock.lockInterruptibly(leaseTime.toMillis(), TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            throw interrupted("acquire lock", e);
        } catch (Exception e) {
            throw new LockException("Failed to acquire lock: " + name, e);
        }
    }

    /**
     * 立即尝试获取
     */
    @Override
    public boolean tryLock() {
        try {
            return lock.tryLock();
        } catch (Exception e) {
            throw new LockException("Failed to acquire lock: " + name, e);
        }
    }

    /**
     * 等待指定时间尝试获取
     * <p>
     * 租约策略与 {@link #lock()} 一致（watchdog 自动续租）
     */
    @Override
    public boolean tryLock(Duration waitTime) {

        Assert.notNull(waitTime, "waitTime");

        validateDuration(waitTime, "waitTime");

        try {
            return lock.tryLock(waitTime.toMillis(), TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            throw interrupted("try lock", e);
        } catch (Exception e) {
            throw new LockException("Failed to acquire lock: " + name, e);
        }
    }

    /**
     * 指定等待时间 + 固定租约
     */
    @Override
    public boolean tryLock(Duration waitTime, Duration leaseTime) {

        Assert.notNull(waitTime, "waitTime");
        Assert.notNull(leaseTime, "leaseTime");

        validateDuration(waitTime, "waitTime");
        validateDuration(leaseTime, "leaseTime");

        try {
            return lock.tryLock(waitTime.toMillis(), leaseTime.toMillis(), TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            throw interrupted("try lock", e);
        } catch (Exception e) {
            throw new LockException("Failed to acquire lock: " + name, e);
        }
    }

    /**
     * 释放锁
     * <p>
     * 非持有者释放归为调用方使用错误（业务错误码段），与基础设施故障区分
     */
    @Override
    public void unlock() {
        try {
            lock.unlock();
        } catch (IllegalMonitorStateException e) {
            throw new LockException(CommonResultCode.BUSINESS_ERROR,
                    "Current thread does not hold lock: " + name, e);
        } catch (Exception e) {
            throw new LockException("Failed to release lock: " + name, e);
        }
    }

    /**
     * 当前线程是否持有锁
     */
    @Override
    public boolean isHeldByCurrentThread() {
        try {
            return lock.isHeldByCurrentThread();
        } catch (Exception e) {
            throw new LockException("Failed to check lock owner: " + name, e);
        }
    }

    /**
     * 锁是否被占用
     */
    @Override
    public boolean isLocked() {
        try {
            return lock.isLocked();
        } catch (Exception e) {
            throw new LockException("Failed to check lock state: " + name, e);
        }
    }

    /**
     * 管理员强制释放
     */
    @Override
    public boolean forceUnlock() {
        try {
            return lock.forceUnlock();
        } catch (Exception e) {
            throw new LockException("Failed to force unlock: " + name, e);
        }
    }

    /**
     * 中断收敛：SPI 不向调用方传播受检的 InterruptedException，
     * 但必须复原中断标志，否则上游线程池/优雅停机失去中断协作能力
     */
    private LockException interrupted(String action, InterruptedException e) {
        Thread.currentThread().interrupt();
        return new LockException("Interrupted while " + action + ": " + name, e);
    }

    private void validateDuration(Duration duration, String fieldName) {
        Assert.check(!duration.isNegative(), fieldName + " must not be negative");

        if (duration.isZero()) {
            return;
        }

        Assert.check(duration.toMillis() > 0, fieldName + " is too small");
    }
}''')

print("P1-7/P1-8/P1-9 done")
