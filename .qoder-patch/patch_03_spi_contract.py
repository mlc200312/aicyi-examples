#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0-2/P1-10/P1-11: SPI JavaDoc 契约补全（含 40101/40102 异常契约）+ WorkerIdLease 不可变与凭证脱敏。"""
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


CORE = "aicyi-commons/aicyi-commons-core/src/main/java/io/github/aicyi/commons/core/"

# ---------------------------------------------------------------- TokenService
write_full(CORE + "token/TokenService.java", '''package io.github.aicyi.commons.core.token;


import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * Token 服务接口：签发、校验、解析、续期与吊销的统一契约。
 * <p>
 * <b>错误码与异常契约</b>（不声明受检异常；实现须遵守同一码位，前端据此区分处理）：
 * <ul>
 *     <li>Token 已过期 / 会话不存在 → {@code TokenExpiredException}（40102），前端据此触发刷新</li>
 *     <li>Token 无效 / 验签失败 / 解析失败 → {@code TokenInvalidException}（40101）</li>
 *     <li>未携带凭证等身份缺失 → {@code UnauthorizedException}（40101）</li>
 *     <li>存储层基础设施故障（如 Redis 连接中断）→ 原样向上抛出（如 {@code DataAccessException}），
 *     <b>不得</b>降级为「Token 无效」，否则存储抖动会导致全量在线用户被误判登出</li>
 * </ul>
 * 上述 Token 异常均由全局异常处理器映射为 HTTP 200 + 业务错误码，业务层不得自行转换为 HTTP 401/403。
 *
 * @param <T> Token 载体类型（如 String / TokenPair）
 * @param <P> Principal 主体类型
 * @author Mr.Min
 * @date 2025/8/12
 **/
public interface TokenService<T, P> {

    /**
     * 创建 Token 对象
     *
     * @param request Token 创建请求，不可为 null；其 {@code principal} 亦不可为 null。
     *                未指定 ttl/timeUnit 时由实现回退默认有效期
     * @return Token，恒非 null
     */
    T create(TokenCreateRequest<P> request);

    /**
     * 校验 Token 是否有效。
     * <p>
     * 本方法是唯一<b>不抛 Token 异常</b>的读取入口：过期与无效一律收敛为 false，
     * 便于网关/拦截器做布尔判定。需要区分「过期」与「无效」时请改用 {@link #parsePrincipal(String)}
     *
     * @param token Token，null/空白视为无效
     * @return true-有效；false-已过期、无效或解析失败
     */
    boolean isValid(String token);

    /**
     * 解析 Token 主体信息
     *
     * @param token Token，不可为 null/空白
     * @return 主体信息，恒非 null（签发时已校验 principal 非空）
     * @throws io.github.aicyi.commons.lang.exception.TokenExpiredException Token 已过期或会话不存在（40102）
     * @throws io.github.aicyi.commons.lang.exception.TokenInvalidException Token 无效、验签或解析失败（40101）
     */
    P parsePrincipal(String token);

    /**
     * 解析 Token 属性。
     * <p>
     * 返回弱类型 Map 仅为承载签发时写入的自由属性；属性集固定且需强类型约束的场景，
     * 业务应在 Principal 上建模而非依赖本方法
     *
     * @param token Token，不可为 null/空白
     * @return Token 属性，无属性时返回空 Map（恒非 null）；调用方不得修改返回内容
     * @throws io.github.aicyi.commons.lang.exception.TokenExpiredException Token 已过期或会话不存在（40102）
     * @throws io.github.aicyi.commons.lang.exception.TokenInvalidException Token 无效、验签或解析失败（40101）
     */
    Map<String, Object> parseAttributes(String token);

    /**
     * 获取指定 Token 属性。
     * <p>
     * 返回值按泛型 {@code <V>} 无检查强转，类型不符时 {@code ClassCastException} 发生在<b>调用方赋值处</b>；
     * 调用方须自行保证 {@code attributeName} 对应的值类型与 {@code <V>} 一致
     *
     * @param token         Token，不可为 null/空白
     * @param attributeName 属性名称，不可为 null
     * @param <V>           属性值类型
     * @return 属性值；属性不存在或无属性集时返回 null
     * @throws io.github.aicyi.commons.lang.exception.TokenExpiredException Token 已过期或会话不存在（40102）
     * @throws io.github.aicyi.commons.lang.exception.TokenInvalidException Token 无效、验签或解析失败（40101）
     */
    <V> V getAttribute(String token, String attributeName);

    /**
     * 刷新 Token：先签发新 Token 再吊销旧 Token，新 Token 签发失败时旧 Token 仍可用。
     *
     * @param token 原 Token，不可为 null/空白
     * @return 新 Token，恒非 null；与入参不同值
     * @throws io.github.aicyi.commons.lang.exception.TokenExpiredException 原 Token 已过期或会话不存在（40102），
     *                                                                       此时须重新登录而非重试刷新
     * @throws io.github.aicyi.commons.lang.exception.TokenInvalidException 原 Token 无效、验签或解析失败（40101）
     */
    T refresh(String token);

    /**
     * 获取 Token 剩余有效期
     *
     * @param token Token，不可为 null/空白
     * @param unit  时间单位，不可为 null；不足一个单位时向零截断
     * @return 剩余有效时间，按 {@code unit} 折算，恒为正数
     * @throws io.github.aicyi.commons.lang.exception.TokenExpiredException Token 已过期或不存在（40102）
     */
    long getRemainingTtl(String token, TimeUnit unit);

    /**
     * 获取主体所有有效 Token。
     * <p>
     * 实现应过滤并回收已失效的残留索引，不得返回过期 Token
     *
     * @param principal 主体信息，不可为 null
     * @return Token 集合，无有效 Token 时返回空集合（恒非 null）
     */
    Set<String> getTokens(P principal);

    /**
     * 撤销 Token（幂等）
     *
     * @param token Token；为 null 或已失效时静默返回，不抛异常
     */
    void revoke(String token);

    /**
     * 撤销主体所有 Token（踢下线，幂等）
     *
     * @param principal 主体信息，不可为 null；无有效 Token 时静默返回
     */
    void revokeAll(P principal);
}''')

# ---------------------------------------------------------------- Cache
write_full(CORE + "cache/Cache.java", '''package io.github.aicyi.commons.core.cache;

import java.time.Duration;
import java.util.Collection;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 缓存接口：面向业务的读写契约，屏蔽底层存储与序列化细节。
 * <p>
 * <b>异常契约</b>：不声明受检异常。存储层基础设施故障（连接中断、超时等）由实现原样向上抛出，
 * 调用方须自行决定降级策略；本接口不承诺「故障时静默返回 null」，
 * 因为静默降级会让缓存故障伪装成数据不存在，引发错误的业务判定。
 * <p>
 * <b>空值语义</b>：{@code get} 返回 null 表示「无业务值」，可能是 key 不存在，
 * 也可能是实现按配置缓存了空值占位（防穿透），二者对调用方等价。
 *
 * @param <K> 缓存键类型
 * @param <V> 缓存值类型
 * @author Mr.Min
 * @date 2026/5/22
 **/
public interface Cache<K, V> {

    /**
     * 读取缓存
     *
     * @param key 缓存键，不可为 null
     * @return 缓存值；未命中或命中空值占位时返回 null
     */
    V get(K key);

    /**
     * 缓存未命中时通过 loader 加载并回填缓存（含防击穿锁保护）
     *
     * @param key    缓存键，不可为 null
     * @param loader 回源加载器，不可为 null；返回 null 时按空值策略处理
     * @return 缓存值或加载值；加载结果为 null 时返回 null
     */
    V get(K key, CacheLoader<K, V> loader);

    /**
     * 批量读取
     *
     * @param keys 缓存键集合，不可为 null；空集合返回空 Map
     * @return key -> 值 的映射，仅包含命中的 key（未命中 key 不出现在结果中）；恒非 null
     */
    Map<K, V> getAll(Collection<K> keys);

    /**
     * 批量读取，缺失 key 通过 loader 批量加载并回填缓存。
     * 注意：批量回填不走防击穿锁，高频缺失场景请用单 key {@link #get(Object, CacheLoader)}
     *
     * @param keys   缓存键集合，不可为 null；空集合返回空 Map
     * @param loader 回源加载器，不可为 null
     * @return key -> 值 的映射；loader 未返回的 key 不出现在结果中；恒非 null
     */
    Map<K, V> getAll(Collection<K> keys, CacheLoader<K, V> loader);

    /**
     * 剩余过期时间（推荐入口）
     *
     * @param key 缓存键，不可为 null
     * @return null 表示 key 不存在；负值表示永久有效；其余为剩余时间
     */
    default Duration getExpire(K key) {
        Long millis = getExpire(key, TimeUnit.MILLISECONDS);
        return millis == null ? null : Duration.ofMillis(millis);
    }

    /**
     * 剩余过期时间
     *
     * @param key      缓存键，不可为 null
     * @param timeUnit 折算单位，不可为 null
     * @return null 表示 key 不存在；-1 表示永久有效；其余为按 timeUnit 折算的剩余时间
     */
    Long getExpire(K key, TimeUnit timeUnit);

    /**
     * 写入缓存，TTL 取配置的默认值
     *
     * @param key   缓存键，不可为 null
     * @param value 缓存值；为 null 时按配置的空值策略写入占位或直接忽略
     */
    void put(K key, V value);

    /**
     * 写入缓存并指定 TTL
     *
     * @param key   缓存键，不可为 null
     * @param value 缓存值；为 null 时按配置的空值策略处理
     * @param ttl   存活时间，null 表示永久有效（覆盖配置的默认 TTL）；不可为负
     */
    void put(K key, V value, Duration ttl);

    /**
     * 批量写入，TTL 取配置的默认值
     *
     * @param values key -> 值 映射，不可为 null；空 Map 为无操作
     */
    void putAll(Map<K, V> values);

    /**
     * 批量写入并指定 TTL
     *
     * @param values key -> 值 映射，不可为 null；空 Map 为无操作
     * @param ttl    存活时间，null 表示永久有效（覆盖配置的默认 TTL）；不可为负
     */
    void putAll(Map<K, V> values, Duration ttl);

    /**
     * 删除缓存
     *
     * @param key 缓存键，不可为 null
     * @return 是否实际删除了 key；key 不存在时返回 false
     */
    boolean evict(K key);

    /**
     * 批量删除
     *
     * @param keys 缓存键集合，不可为 null；空集合返回 0
     * @return 实际删除的 key 数量
     */
    long evictBatch(Collection<K> keys);

    /**
     * key 是否存在
     * <p>
     * 注意：启用缓存空值时，空值占位 key 也返回 true（exists 不代表有业务值）
     *
     * @param key 缓存键，不可为 null
     * @return true 表示存在（含空值占位）
     */
    boolean exists(K key);

    /**
     * 清空本缓存全部 key
     * <p>
     * 实现必须按 globalPrefix:cacheName 前缀限定范围，不得影响其他缓存
     */
    void clear();

    /**
     * 读取统计快照（命中/未命中/回源耗时等）
     *
     * @return 统计快照，恒非 null；外部修改不影响缓存内部计数器
     */
    CacheStats stats();
}''')

# ---------------------------------------------------------------- CacheConfig
write_full(CORE + "cache/CacheConfig.java", '''package io.github.aicyi.commons.core.cache;

import java.time.Duration;

/**
 * 缓存配置接口（面向分布式缓存的「身份 + 策略」契约：
 * globalPrefix/cacheName 为键空间身份，其余为通用策略属性；不含存储/序列化细节）
 * <p>
 * 实现须为不可变值对象（构造后各 getter 返回值恒定）：缓存实例长期持有本配置，
 * 运行期可变会导致键空间与 TTL 策略漂移。
 *
 * @author Mr.Min
 * @date 11:10
 **/
public interface CacheConfig {

    /**
     * 全局键空间前缀，用于多应用/多环境共享同一存储时相互隔离
     *
     * @return 前缀；null 或空串表示不加前缀（键退化为 cacheName:key）
     */
    String getGlobalPrefix();

    /**
     * 缓存名，与 globalPrefix 共同构成键空间身份
     *
     * @return 缓存名，恒非空白；{@code clear()} 的前缀扫描范围由此界定
     */
    String getCacheName();

    /**
     * 默认存活时间，{@code put(K, V)} 等未显式传 ttl 的写入使用本值
     *
     * @return 默认 TTL，恒非 null 且为正
     */
    Duration getTtl();

    /**
     * 是否缓存空值（防穿透）
     *
     * @return true 时回源结果为 null 也写入占位，此时 {@code Cache#exists} 对占位 key 返回 true
     */
    boolean isCacheNull();

    /**
     * 是否对 TTL 施加随机抖动（防雪崩）
     * <p>
     * <b>安全凭证类缓存必须关闭</b>：抖动会使实际 TTL 超出对外声明的有效期
     *
     * @return true 时实际 TTL = 配置 TTL 上浮 0 ~ {@link #getJitterPercent()}%
     */
    boolean isTtlJitter();

    /**
     * TTL 抖动上浮比例
     *
     * @return 百分比整数，取值 [0, 100]；{@link #isTtlJitter()} 为 false 时本值不生效
     */
    int getJitterPercent();

    /**
     * 防击穿锁的租约时间
     *
     * @return 锁 TTL，恒非 null 且为正；须显著大于单次回源耗时，否则锁提前失效会退化为并发回源
     */
    Duration getLockTtl();

    /**
     * 未取到防击穿锁时的最长等待时间
     *
     * @return 等待超时，恒非 null；为 {@link Duration#ZERO} 时表示不等待，直接回源或返回 null
     */
    Duration getWaitTimeout();
}''')

# ---------------------------------------------------------------- CacheLock
write_full(CORE + "cache/CacheLock.java", '''package io.github.aicyi.commons.core.cache;

import java.time.Duration;

/**
 * 缓存防击穿锁：零等待、短租约、允许获取失败的尽力锁。
 * <p>
 * 与 {@link io.github.aicyi.commons.core.lock.DistributedLock} 的区别见本包 package-info：
 * 业务互斥请使用 DistributedLock，本接口仅服务于缓存回填的并发收敛。
 *
 * @author Mr.Min
 * @date 2026/5/22
 **/
public interface CacheLock {

    /**
     * 尝试获取锁，不阻塞、不等待
     *
     * @param key 锁 key，不可为 null；命名空间由调用方负责（如置于缓存前缀内，使 clear() 可覆盖）
     * @param ttl 锁租约时间，不可为 null 且须为正，到期自动释放
     * @return 锁句柄（携带凭证，可在任意线程释放），获取失败返回 null；调用方须自行处理 null 分支
     */
    CacheLockHandle tryLock(String key, Duration ttl);
}''')

# ---------------------------------------------------------------- WorkerIdAllocator
write_full(CORE + "id/WorkerIdAllocator.java", '''package io.github.aicyi.commons.core.id;


/**
 * WorkerId 分配器接口：为雪花算法节点分配互不冲突的 workerId，并维护其租约。
 * <p>
 * 实现须保证：同一时刻同一 workerId 至多被一个存活节点持有（互斥），
 * 且 {@link #renew} / {@link #release} 以租约凭证为准（防误删他人租约）。
 *
 * @author Mr.Min
 * @date 2026/5/21
 **/
public interface WorkerIdAllocator {

    /**
     * 申请 workerId，成功后调用方即独占该 workerId 直至租约到期或主动释放
     *
     * @return 租约对象，恒非 null；调用方须持有并在关闭时释放
     * @throws IllegalStateException 可用 workerId 已耗尽（存活节点数超过 workerId 位宽容量）；
     *                               调用方应视为启动失败，不得退化为随机 workerId（会产生重复 ID）
     */
    WorkerIdLease allocate();

    /**
     * 续约：延长租约 TTL
     *
     * @param lease {@link #allocate()} 返回的租约，不可为 null
     * @return true 续约成功；false 表示租约已丢失（TTL 过期被回收，或已被其他节点抢占），
     *         调用方<b>必须</b>立即停止发号并重新申请，否则将与其他节点产生重复 ID
     */
    boolean renew(WorkerIdLease lease);

    /**
     * 主动释放：租约凭证不匹配时静默失败，不抛异常（防误删他人租约）
     *
     * @param lease {@link #allocate()} 返回的租约，不可为 null
     * @return true 释放成功；false 表示租约已不属于本调用方，无需重试
     */
    boolean release(WorkerIdLease lease);
}''')

# ---------------------------------------------------------------- IdGenerator
write_full(CORE + "id/IdGenerator.java", '''package io.github.aicyi.commons.core.id;

/**
 * ID 生成器接口定义。
 * <p>
 * 实现须为线程安全，可被多线程并发调用。
 *
 * @author Mr.Min
 * @date 17:57
 **/
public interface IdGenerator {

    /**
     * 生成 ID。
     * <p>
     * 单节点内单调递增；跨节点仅保证全局唯一，<b>不保证全局有序</b>，
     * 调用方不得据此推断创建先后。
     * <p>
     * 返回值为 64 位有符号整数，序列化到前端时会超出 JavaScript 安全整数范围（2^53-1），
     * Web 层须按字符串输出。
     *
     * @return 全局唯一的 long 型 ID，恒为正数
     * @throws IllegalStateException 发号前置条件不满足（如 workerId 租约未就绪或已丢失）；
     *                               实现应 fail-closed 拒绝发号，不得退化为可能重复的 ID
     */
    long nextId();
}''')

# ---------------------------------------------------------------- WorkerIdLease
write_full(CORE + "id/WorkerIdLease.java", '''package io.github.aicyi.commons.core.id;

import io.github.aicyi.commons.lang.model.BaseBean;

/**
 * workerId 租约对象：持有 workerId、租约凭证与 TTL。
 * <p>
 * <b>不可变</b>：token 是续约/释放的 fencing 凭证，一旦可被外部改写，
 * 基于「凭证一致才操作」的 CAS 语义即失效，可能出现误删他人租约、双节点共用 workerId 而发出重复 ID。
 * 因此本类不提供无参构造与 setter。
 *
 * @author Mr.Min
 * @date 2026/5/21
 **/
public class WorkerIdLease extends BaseBean {

    /**
     * WorkerId
     */
    private final int workerId;

    /**
     * fencing token：续约/释放的持有凭证
     */
    private final String token;

    /**
     * TTL（秒）
     */
    private final long ttlSeconds;

    public WorkerIdLease(int workerId, String token, long ttlSeconds) {
        this.workerId = workerId;
        this.token = token;
        this.ttlSeconds = ttlSeconds;
    }

    public int getWorkerId() {
        return workerId;
    }

    public String getToken() {
        return token;
    }

    public long getTtlSeconds() {
        return ttlSeconds;
    }

    /**
     * 覆写 {@link BaseBean} 的反射 toString 做凭证脱敏：token 一旦落日志，
     * 任何具备日志读取权限的人都可伪造续约/释放，等同于窃取 workerId
     */
    @Override
    public String toString() {
        return "WorkerIdLease{workerId=" + workerId + ", ttlSeconds=" + ttlSeconds + ", token=***}";
    }
}''')

# ---------------------------------------------------------------- RedisWorkerIdAllocator 日志脱敏
apply("aicyi-midware/aicyi-midware-redis/src/main/java/io/github/aicyi/midware/redis/id/RedisWorkerIdAllocator.java", [
    (
        '''            if (Boolean.TRUE.equals(success)) {
                logger.info("Allocated workerId={}, token={}", workerId, token);
                return new WorkerIdLease(workerId, token, ttlSeconds);
            }''',
        '''            if (Boolean.TRUE.equals(success)) {
                // 不打印 fencing token：token 落日志等同于泄露租约持有凭证，可被伪造续约/释放
                logger.info("Allocated workerId={}, ttlSeconds={}", workerId, ttlSeconds);
                return new WorkerIdLease(workerId, token, ttlSeconds);
            }''',
    ),
])

print("P0-2/P1-10/P1-11 done")
