#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-3 代码改造：移除 RedisCache 的 public getTemplate()/buildKey()，
Token 体系对 Redis 原生结构（ZSet / pipeline / Lua 脚本）的访问收敛到包内门面 RedisIndexedOperator。

门面接口与实现类置于 io.github.aicyi.midware.redis.token 包内并声明为 package-private：
唯一消费方 RedisTokenServiceImpl 就在该包内，因此无需 public 即可完成协作，
接入方既无法 import、也无法注入（未注册 Bean），彻底满足"禁止 public 对外暴露"。
"""
import os
import sys

sys.path.insert(0, "/Users/liangchaomin/workspace/develop/aicyi-examples/.qoder-patch")
from patch_base import ROOT, apply  # noqa: E402

TOKEN = "aicyi-midware/aicyi-midware-redis/src/main/java/io/github/aicyi/midware/redis/token"
CACHE = "aicyi-midware/aicyi-midware-redis/src/main/java/io/github/aicyi/midware/redis/cache"


def create(rel_path, content):
    path = ROOT + "/" + rel_path
    if os.path.exists(path):
        print("FAIL %s already exists" % rel_path)
        sys.exit(1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK   %s (new file)" % rel_path)


# ============================================================
# 1. 新增门面接口 RedisIndexedOperator（package-private）
# ============================================================
create(TOKEN + "/RedisIndexedOperator.java", '''package io.github.aicyi.midware.redis.token;

import org.springframework.data.redis.core.script.RedisScript;

import java.util.Collection;
import java.util.List;
import java.util.Set;

/**
 * Token 体系的 Redis 索引操作门面（<b>包内协作专用，非对外 API</b>）
 *
 * <p>
 * 收敛 {@link RedisTokenServiceImpl} 对 Redis 原生结构的全部访问：主体索引 ZSet 读写、
 * 会话 key 批量存活探测（pipeline）、索引写入/裁剪 Lua 脚本、索引 key 删除。
 * </p>
 *
 * <p>
 * 刻意不提供 {@code StringRedisTemplate} / {@code RedisConnection} 的获取途径，也不开放任意命令执行：
 * 调用方只能使用下列方法，无法借道 Token 服务绕过缓存语义直接操作 Redis。
 * </p>
 *
 * <p>
 * 可见性为包级私有，仅 {@code io.github.aicyi.midware.redis.token} 包内可用；未注册为 Spring Bean，
 * 接入方无法注入，不属于脚手架对外契约，后续版本可不兼容变更或移除。
 * </p>
 *
 * @author Mr.Min
 */
interface RedisIndexedOperator {

    /**
     * 按会话缓存命名空间拼接完整 key（{@code globalPrefix:cacheName:key}）
     * <p>规则与 {@code RedisCache} 的键规则一致，两者不一致会使会话写入与存活探测落在不同 key 上
     *
     * @param key 缓存逻辑 key，不可为 null
     * @return 完整 Redis key
     */
    String cacheKey(String key);

    /**
     * 读取 ZSet 全部成员（score 升序）
     *
     * @param key ZSet 完整 key，不可为 null；本方法不叠加任何前缀
     * @return 成员集合；key 不存在时返回空集合，不返回 null
     */
    Set<String> zRangeAll(String key);

    /**
     * 移除 ZSet 成员
     *
     * @param key     ZSet 完整 key，不可为 null；本方法不叠加任何前缀
     * @param members 待移除成员，为 null 或空时不发起 Redis 调用
     * @return 实际移除的成员数量
     */
    long zRemove(String key, Collection<String> members);

    /**
     * pipeline 批量 EXISTS：单次往返完成多 key 存活判定，避免逐个 RTT
     *
     * @param keys 完整 key 集合（由 {@link #cacheKey(String)} 生成，本方法不叠加前缀）；为 null 或空时返回空列表
     * @return 与入参顺序一一对应的存活标记，元素不为 null
     */
    List<Boolean> existsPipelined(Collection<String> keys);

    /**
     * 执行 Lua 脚本
     *
     * @param script 脚本定义，不可为 null
     * @param keys   KEYS 列表（完整 key，本方法不叠加前缀），不可为 null
     * @param args   ARGV 列表，按模板既有的 String 序列化器写入
     * @param <T>    脚本返回值类型
     * @return 脚本执行结果
     */
    <T> T executeScript(RedisScript<T> script, List<String> keys, Object... args);

    /**
     * 删除单个 key
     *
     * @param key 完整 key，不可为 null；本方法不叠加任何前缀
     * @return key 存在且被删除时返回 true
     */
    boolean delete(String key);
}
''')

# ============================================================
# 2. 新增实现类 DefaultRedisIndexedOperator（package-private final）
# ============================================================
create(TOKEN + "/DefaultRedisIndexedOperator.java", '''package io.github.aicyi.midware.redis.token;

import io.github.aicyi.commons.core.cache.CacheConfig;
import io.github.aicyi.commons.lang.Assert;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * {@link RedisIndexedOperator} 默认实现（<b>包内协作专用，非对外 API</b>）
 *
 * <p>
 * 包装 {@code StringRedisTemplate}，仅开放 Token 索引所需的最小操作集；模板以 private final 持有且
 * <b>不提供 getter</b>，调用方无法取得模板实例，也就无法执行门面之外的任意 Redis 命令。
 * </p>
 *
 * <p>
 * 所有方法均<b>不改变原有 Redis 语义</b>：命令、参数序列化器、pipeline 往返次数与改造前逐条一致。
 * </p>
 *
 * @author Mr.Min
 */
final class DefaultRedisIndexedOperator implements RedisIndexedOperator {

    /**
     * 底层模板，仅本类可见
     */
    private final StringRedisTemplate template;

    /**
     * 会话缓存配置，仅用于按 {@code globalPrefix:cacheName:key} 拼接会话 key；
     * 必须与会话缓存（{@code RedisCache}）使用同一份配置，否则键空间割裂
     */
    private final CacheConfig config;

    DefaultRedisIndexedOperator(StringRedisTemplate template, CacheConfig config) {
        this.template = Assert.notNull(template, "redisTemplate");
        this.config = Assert.notNull(config, "cacheConfig");
    }

    /**
     * 与 {@code RedisCache} 的键规则保持一致：空段跳过、冒号连接
     */
    @Override
    public String cacheKey(String key) {

        Assert.notNull(key, "cache key");

        return Stream.of(
                        config.getGlobalPrefix(),
                        config.getCacheName(),
                        key
                )
                .filter(s -> s != null && !s.isEmpty())
                .collect(Collectors.joining(":"));
    }

    @Override
    public Set<String> zRangeAll(String key) {

        Assert.notNull(key, "key");

        Set<String> members = template.opsForZSet().range(key, 0, -1);

        // 归一 null 为空集合：调用方无需重复判空，且不会把"key 不存在"与"空索引"区分对待
        return members == null ? Collections.emptySet() : members;
    }

    @Override
    public long zRemove(String key, Collection<String> members) {

        Assert.notNull(key, "key");

        if (members == null || members.isEmpty()) {
            return 0L;
        }

        Long removed = template.opsForZSet().remove(key, members.toArray());

        return removed == null ? 0L : removed;
    }

    @Override
    public List<Boolean> existsPipelined(Collection<String> keys) {

        if (keys == null || keys.isEmpty()) {
            return Collections.emptyList();
        }

        List<String> keyList = new ArrayList<>(keys);

        List<Object> pipelined = template.executePipelined((RedisCallback<Object>) connection -> {
            for (String key : keyList) {
                connection.keyCommands().exists(key.getBytes(StandardCharsets.UTF_8));
            }
            return null;
        });

        // 管道结果在事务/管道模式下可能为 null，此处统一收敛为 boolean，调用方可直接下标取值
        List<Boolean> result = new ArrayList<>(pipelined.size());

        for (Object item : pipelined) {
            result.add(Boolean.TRUE.equals(item));
        }

        return result;
    }

    @Override
    public <T> T executeScript(RedisScript<T> script, List<String> keys, Object... args) {

        Assert.notNull(script, "script");
        Assert.notNull(keys, "keys");

        return template.execute(script, keys, args);
    }

    @Override
    public boolean delete(String key) {

        Assert.notNull(key, "key");

        return Boolean.TRUE.equals(template.delete(key));
    }
}
''')

# ============================================================
# 3. RedisCache：移除 public getTemplate()，buildKey 收窄为 private
# ============================================================
apply(CACHE + "/RedisCache.java",
      [
          (
              "    /**\n"
              "     * 暴露底层模板，<b>仅限框架内部协作使用</b>（如 token 体系需直接操作 ZSet 等原生结构）。\n"
              "     * <p>\n"
              "     * <b>业务代码禁止调用</b>：绕过缓存语义直接操作 Redis 会破坏 TTL 策略、统计计数与防击穿保护。\n"
              "     * 后续版本可能收窄可见性，接入方不应依赖此方法。\n"
              "     */\n"
              "    public StringRedisTemplate getTemplate() {\n"
              "        return template;\n"
              "    }\n"
              "\n"
              "    /**\n"
              "     * 构造完整 Redis key（globalPrefix:cacheName:key），<b>仅限框架内部协作使用</b>。\n"
              "     * <p>\n"
              "     * token 体系等需对多个 key 做 pipeline/批量原生操作时使用。\n"
              "     * <b>业务代码禁止调用</b>：请走 {@link Cache} 接口语义方法，不应依赖内部 key 拼接规则。\n"
              "     * 后续版本可能收窄可见性，接入方不应依赖此方法。\n"
              "     */\n"
              "    public String buildKey(String key) {\n",
              "    /**\n"
              "     * 构造完整 Redis key（globalPrefix:cacheName:key），缓存内部键规则的唯一出处，<b>不对外暴露</b>。\n"
              "     * <p>\n"
              "     * 框架内部协作（token 体系的 ZSet / pipeline / 脚本操作）改由包内门面\n"
              "     * {@code io.github.aicyi.midware.redis.token.RedisIndexedOperator} 承担，业务只能走 {@link Cache}\n"
              "     * 接口语义方法，无法取得底层模板，也就无法绕过 TTL 策略、统计计数与防击穿保护直接操作 Redis。\n"
              "     * <p>\n"
              "     * 键规则变更时必须同步 {@code DefaultRedisIndexedOperator#cacheKey}，\n"
              "     * 否则会话写入与批量存活探测会落在不同 key 上（幽灵成员回收失效）。\n"
              "     */\n"
              "    private String buildKey(String key) {\n",
          ),
      ])

# ============================================================
# 4. RedisTokenServiceImpl：依赖门面，删除 getTemplate/buildKey 调用
# ============================================================
apply(TOKEN + "/RedisTokenServiceImpl.java",
      [
          # 4.1 imports：移除 RedisCallback / StandardCharsets（管道细节下沉到门面实现）
          (
              "import org.springframework.dao.DataAccessException;\n"
              "import org.springframework.data.redis.core.RedisCallback;\n"
              "import org.springframework.data.redis.core.StringRedisTemplate;\n"
              "import org.springframework.data.redis.core.script.DefaultRedisScript;\n"
              "\n"
              "import java.nio.charset.StandardCharsets;\n"
              "import java.time.Duration;\n",
              "import org.springframework.dao.DataAccessException;\n"
              "import org.springframework.data.redis.core.StringRedisTemplate;\n"
              "import org.springframework.data.redis.core.script.DefaultRedisScript;\n"
              "\n"
              "import java.time.Duration;\n",
          ),
          # 4.2 类注释：补充封装边界
          (
              " *     <li>主体索引：{@code {keyPrefix}:principal:{principalId}}（ZSet，score 为签发时刻）</li>\n"
              " * </ul>\n",
              " *     <li>主体索引：{@code {keyPrefix}:principal:{principalId}}（ZSet，score 为签发时刻）</li>\n"
              " * </ul>\n"
              " *\n"
              " * <p>\n"
              " * 封装边界：对 Redis 原生结构（ZSet / pipeline / Lua 脚本）的访问统一收敛到包内门面\n"
              " * {@code RedisIndexedOperator}，本类不再持有 {@code StringRedisTemplate}，\n"
              " * 业务与子类均无法借道 Token 服务绕过缓存语义直接操作 Redis。\n"
              " * </p>\n",
          ),
          # 4.3 字段：模板替换为门面
          (
              "    /**\n"
              "     * redis 操作\n"
              "     */\n"
              "    protected final StringRedisTemplate redisTemplate;\n",
              "    /**\n"
              "     * Redis 索引操作门面：仅开放 ZSet / pipeline / 脚本 / key 生成的最小能力，\n"
              "     * 不持有也不暴露 {@code StringRedisTemplate}（包内类型，子类与业务均不可见）\n"
              "     */\n"
              "    private final RedisIndexedOperator indexedOperator;\n",
          ),
          # 4.4 移除两个基于 RedisCache 的构造器（依赖已删除的 getTemplate()，且两仓库均无调用方）
          (
              "    public RedisTokenServiceImpl(RedisCache<TokenSession<P>> tokenCache, long refreshTtl, TimeUnit refreshTimeUnit) {\n"
              "        this(tokenCache, AuthenticationConfig.DEFAULT_KEY_PREFIX, refreshTtl, refreshTimeUnit);\n"
              "    }\n"
              "\n"
              "    /**\n"
              "     * @param tokenCache 外部构建的会话缓存；其 globalPrefix 应与 keyPrefix 保持一致，否则会话与索引键空间割裂\n"
              "     * @param keyPrefix  Token 键空间前缀\n"
              "     */\n"
              "    public RedisTokenServiceImpl(RedisCache<TokenSession<P>> tokenCache, String keyPrefix, long refreshTtl, TimeUnit refreshTimeUnit) {\n"
              "        super(refreshTtl, refreshTimeUnit);\n"
              "        Assert.notNull(tokenCache, \"tokenCache\");\n"
              "        this.keyPrefix = Assert.notBlank(keyPrefix, \"keyPrefix\");\n"
              "        this.tokenCache = tokenCache;\n"
              "        this.redisTemplate = tokenCache.getTemplate();\n"
              "    }\n"
              "\n"
              "    public RedisTokenServiceImpl(StringRedisTemplate redisTemplate, Class<? extends P> principalType, long refreshTtl, TimeUnit refreshTimeUnit) {\n",
              "    public RedisTokenServiceImpl(StringRedisTemplate redisTemplate, Class<? extends P> principalType, long refreshTtl, TimeUnit refreshTimeUnit) {\n",
          ),
          # 4.5 主构造器：会话缓存与门面共用同一份 CacheConfig
          (
              "    public RedisTokenServiceImpl(StringRedisTemplate redisTemplate, Class<? extends P> principalType, long refreshTtl, TimeUnit refreshTimeUnit, String keyPrefix) {\n",
              "    /**\n"
              "     * @param redisTemplate Redis 模板，仅用于内部构建会话缓存与索引操作门面，<b>不作为字段持有</b>\n"
              "     * @param principalType Principal 类型，决定会话编解码\n"
              "     * @param keyPrefix     Token 键空间前缀\n"
              "     */\n"
              "    public RedisTokenServiceImpl(StringRedisTemplate redisTemplate, Class<? extends P> principalType, long refreshTtl, TimeUnit refreshTimeUnit, String keyPrefix) {\n",
          ),
          (
              "        this.tokenCache = new RedisCache<>(\n"
              "                redisTemplate,\n"
              "                cacheConfig,\n"
              "                new CacheWrapperCodec<>(TokenInfo.class, principalType)\n"
              "        );\n"
              "        this.redisTemplate = redisTemplate;\n"
              "    }\n",
              "        this.tokenCache = new RedisCache<>(\n"
              "                redisTemplate,\n"
              "                cacheConfig,\n"
              "                new CacheWrapperCodec<>(TokenInfo.class, principalType)\n"
              "        );\n"
              "        // 门面与会话缓存共用同一份 CacheConfig，cacheKey 与 RedisCache 的键规则天然一致\n"
              "        this.indexedOperator = new DefaultRedisIndexedOperator(redisTemplate, cacheConfig);\n"
              "    }\n",
          ),
          # 4.6 writeIndex：脚本执行走门面
          (
              "        List<String> removed = redisTemplate.execute(\n"
              "                WRITE_INDEX_SCRIPT,\n",
              "        List<String> removed = indexedOperator.executeScript(\n"
              "                WRITE_INDEX_SCRIPT,\n",
          ),
          # 4.7 getTokens：ZSet 读取走门面
          (
              "        Set<String> members = redisTemplate.opsForZSet().range(principalId, 0, -1);\n"
              "\n"
              "        if (members == null || members.isEmpty()) {\n"
              "            return Collections.emptySet();\n"
              "        }\n",
              "        Set<String> members = indexedOperator.zRangeAll(principalId);\n"
              "\n"
              "        if (members.isEmpty()) {\n"
              "            return Collections.emptySet();\n"
              "        }\n",
          ),
          # 4.8 retainAliveMembers：key 拼接 + pipeline 走门面
          (
              "        for (String member : candidates) {\n"
              "            sessionKeys.add(tokenCache.buildKey(getTokenId(tokenOf(member))));\n"
              "        }\n"
              "\n"
              "        // pipeline 批量 EXISTS：单次往返完成存活判定，避免逐个 RTT\n"
              "        List<Object> existsResult = redisTemplate.executePipelined((RedisCallback<Object>) connection -> {\n"
              "            for (String sessionKey : sessionKeys) {\n"
              "                connection.keyCommands().exists(sessionKey.getBytes(StandardCharsets.UTF_8));\n"
              "            }\n"
              "            return null;\n"
              "        });\n",
              "        for (String member : candidates) {\n"
              "            sessionKeys.add(indexedOperator.cacheKey(getTokenId(tokenOf(member))));\n"
              "        }\n"
              "\n"
              "        // pipeline 批量 EXISTS：单次往返完成存活判定，避免逐个 RTT\n"
              "        List<Boolean> existsResult = indexedOperator.existsPipelined(sessionKeys);\n",
          ),
          (
              "            if (Boolean.TRUE.equals(existsResult.get(i))) {\n",
              "            if (existsResult.get(i)) {\n",
          ),
          (
              "        if (!stale.isEmpty()) {\n"
              "            redisTemplate.opsForZSet().remove(principalId, stale.toArray());\n"
              "        }\n",
              "        if (!stale.isEmpty()) {\n"
              "            indexedOperator.zRemove(principalId, stale);\n"
              "        }\n",
          ),
          # 4.9 revokeAll：ZSet 读取走门面
          (
              "        // 直接按索引成员失效会话，不经 getTokens 的存活过滤（回收路径本身要处理已失效成员）\n"
              "        Set<String> members = redisTemplate.opsForZSet().range(principalId, 0, -1);\n"
              "\n"
              "        if (members != null) {\n"
              "            for (String member : members) {\n"
              "                tokenCache.evict(getTokenId(tokenOf(member)));\n"
              "            }\n"
              "        }\n",
              "        // 直接按索引成员失效会话，不经 getTokens 的存活过滤（回收路径本身要处理已失效成员）\n"
              "        for (String member : indexedOperator.zRangeAll(principalId)) {\n"
              "            tokenCache.evict(getTokenId(tokenOf(member)));\n"
              "        }\n",
          ),
          # 4.10 revokePrincipal / revokePrincipalAll
          (
              "    protected void revokePrincipal(P principal, String token) {\n"
              "\n"
              "        redisTemplate.opsForZSet().remove(getPrincipalId(principal), indexMember(principal, token));\n"
              "    }\n"
              "\n"
              "    protected void revokePrincipalAll(P principal) {\n"
              "\n"
              "        redisTemplate.delete(getPrincipalId(principal));\n"
              "    }\n",
              "    protected void revokePrincipal(P principal, String token) {\n"
              "\n"
              "        indexedOperator.zRemove(getPrincipalId(principal), Collections.singletonList(indexMember(principal, token)));\n"
              "    }\n"
              "\n"
              "    protected void revokePrincipalAll(P principal) {\n"
              "\n"
              "        indexedOperator.delete(getPrincipalId(principal));\n"
              "    }\n",
          ),
      ])

# ============================================================
# 5. token/package-info：补充封装边界说明
# ============================================================
apply(TOKEN + "/package-info.java",
      [
          (
              " * 与 {@link io.github.aicyi.midware.redis.token.ClaimFilteredPrincipalSerializer}（claim 字段白名单）。\n",
              " * 与 {@link io.github.aicyi.midware.redis.token.ClaimFilteredPrincipalSerializer}（claim 字段白名单）。\n"
              " * <p>\n"
              " * 封装边界：Token 存储对 Redis 原生结构（ZSet / pipeline / Lua 脚本）的访问统一收敛到包内门面\n"
              " * {@code RedisIndexedOperator}（package-private，未注册 Bean），本包不持有也不对外暴露\n"
              " * {@code StringRedisTemplate}；{@code RedisCache} 亦不开放底层模板与键拼接方法，\n"
              " * 业务无法绕过缓存语义直接操作 Redis。\n",
          ),
      ])

print("P1-3 facade refactor done")
