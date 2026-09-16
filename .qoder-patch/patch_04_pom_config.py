#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-1/P1-2/P1-3/P1-4/P1-5/P1-12: POM 依赖治理、配置开关语义、CacheLock 自动装配、Duration 单位。"""
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


# ============================================================ P1-1 redisson optional
apply("aicyi-midware/aicyi-midware-redis/pom.xml", [
    (
        """        <dependency>
            <groupId>org.redisson</groupId>
            <artifactId>redisson</artifactId>
        </dependency>
""",
        """        <!-- Redisson 仅被 lock 包与 RedissonCacheLock 共 3 个类使用，声明 optional 避免强制传递给
             仅需 RedisCache / TokenService / 雪花 ID 的接入方：Redisson 会带入 netty、kryo、rxjava3、
             jboss-marshalling、byte-buddy 等 20+ 传递依赖。
             需要 DistributedLockManager / RedissonCacheLock 的模块必须自行显式声明本依赖；
             自动配置侧已由 RedisAutoConfiguration.RedissonLockConfiguration 的 @ConditionalOnClass 守卫 -->
        <dependency>
            <groupId>org.redisson</groupId>
            <artifactId>redisson</artifactId>
            <optional>true</optional>
        </dependency>
""",
    ),
])

# ============================================================ P1-2 starter scope 语义
apply("aicyi-midware/aicyi-midware-spring-boot-starter/pom.xml", [
    (
        """        <dependency>
            <groupId>io.github.aicyi.midware</groupId>
            <artifactId>aicyi-midware-rabbitmq</artifactId>
            <scope>provided</scope>
            <optional>true</optional>
        </dependency>

        <dependency>
            <groupId>io.github.aicyi.midware</groupId>
            <artifactId>aicyi-midware-redis</artifactId>
            <scope>provided</scope>
            <optional>true</optional>
        </dependency>

        <dependency>
            <groupId>io.github.aicyi.midware</groupId>
            <artifactId>aicyi-midware-db-mybatisplus</artifactId>
            <scope>provided</scope>
            <optional>true</optional>
        </dependency>
""",
        """        <!-- 可选中间件模块统一用 optional 表达「接入方按需显式引入」，不使用 provided：
             provided 的语义是「运行期由容器提供」（如 servlet-api），用在此处会让依赖意图失真，
             且一旦被误删 optional 即变成对下游不可见的运行期缺类风险。
             两者对下游同样不传递，故本调整不改变现有接入方的依赖解析结果 -->
        <dependency>
            <groupId>io.github.aicyi.midware</groupId>
            <artifactId>aicyi-midware-rabbitmq</artifactId>
            <optional>true</optional>
        </dependency>

        <dependency>
            <groupId>io.github.aicyi.midware</groupId>
            <artifactId>aicyi-midware-redis</artifactId>
            <optional>true</optional>
        </dependency>

        <dependency>
            <groupId>io.github.aicyi.midware</groupId>
            <artifactId>aicyi-midware-db-mybatisplus</artifactId>
            <optional>true</optional>
        </dependency>

        <!-- RedisAutoConfiguration 的 RedissonLockConfiguration 编译期引用 RedissonClient；
             redis 模块已将 redisson 标记 optional，不再传递，故此处必须显式声明 -->
        <dependency>
            <groupId>org.redisson</groupId>
            <artifactId>redisson</artifactId>
            <optional>true</optional>
        </dependency>
""",
    ),
])

apply("aicyi-midware/aicyi-midware-message/aicyi-midware-message-spring-boot-starter/pom.xml", [
    (
        """        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter</artifactId>
            <scope>provided</scope>
        </dependency>
""",
        """        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter</artifactId>
            <scope>provided</scope>
        </dependency>

        <!-- TemplateAutoConfiguration 编译期引用 RedissonClient 与 RedissonCacheLock；
             aicyi-midware-redis 已将 redisson 标记 optional，不再经 message-db 传递，故此处显式声明 -->
        <dependency>
            <groupId>org.redisson</groupId>
            <artifactId>redisson</artifactId>
            <scope>provided</scope>
            <optional>true</optional>
        </dependency>
""",
    ),
])

# ============================================================ P1-4 CacheLock 自动装配
apply("aicyi-midware/aicyi-midware-spring-boot-starter/src/main/java/io/github/aicyi/midware/starter/autoconfigure/RedisAutoConfiguration.java",
      [
          (
              """import io.github.aicyi.midware.redis.template.EnhancedRedisTemplateFactory;
import io.github.aicyi.commons.core.lock.DistributedLockManager;
import io.github.aicyi.midware.redis.lock.RedissonDistributedLockManager;
""",
              """import io.github.aicyi.commons.core.cache.CacheLock;
import io.github.aicyi.midware.redis.cache.RedisCacheLock;
import io.github.aicyi.midware.redis.template.EnhancedRedisTemplateFactory;
import io.github.aicyi.commons.core.lock.DistributedLockManager;
import io.github.aicyi.midware.redis.lock.RedissonDistributedLockManager;
""",
          ),
          (
              """    @Bean
    @ConditionalOnMissingBean
    public EnhancedRedisTemplateFactory enhancedRedisTemplateFactory(RedisConnectionFactory redisConnectionFactory) {
        return new EnhancedRedisTemplateFactory(redisConnectionFactory);
    }
""",
              """    @Bean
    @ConditionalOnMissingBean
    public EnhancedRedisTemplateFactory enhancedRedisTemplateFactory(RedisConnectionFactory redisConnectionFactory) {
        return new EnhancedRedisTemplateFactory(redisConnectionFactory);
    }

    /**
     * 缓存防击穿锁：默认选用自包含的 {@link RedisCacheLock}（仅依赖 StringRedisTemplate），
     * 不要求接入方引入 Redisson。业务可自定义 {@link CacheLock} Bean 整体覆盖
     * （如需与业务互斥锁共用 Redisson 实现，可注册 {@code RedissonCacheLock}）
     */
    @Bean
    @ConditionalOnMissingBean(CacheLock.class)
    public CacheLock cacheLock(EnhancedRedisTemplateFactory redisTemplateFactory) {
        return new RedisCacheLock(redisTemplateFactory.getStringRedisTemplate());
    }
""",
          ),
      ])

# ============================================================ P1-3 配置开关语义 + 校验
apply("aicyi-midware/aicyi-midware-spring-boot-starter/src/main/java/io/github/aicyi/midware/starter/properties/SnowflakeProperties.java",
      [
          (
              """    /**
     * 是否启用
     */
    private boolean enabled = true;
""",
              """    /**
     * 是否启用：默认关闭，须显式配置 {@code aicyi.snowflake.enabled=true} 才装配。
     * <p>
     * 默认值必须与 SnowflakeAutoConfiguration 上的 {@code @ConditionalOnProperty(havingValue = "true")}
     * （未设 matchIfMissing，即缺省不装配）保持一致：雪花 ID 会在 Redis 中占用 workerId 名额
     * 并常驻心跳线程，仅需缓存/Token 能力的服务不应被隐式拉起
     */
    private boolean enabled = false;
""",
          ),
          (
              """    /**
     * workerId lease TTL
     */
    private long ttlSeconds = 60;

    /**
     * heartbeat 间隔；未显式配置时按 ttlSeconds / 3 计算（见 getHeartbeatSeconds）
     */
    private Long heartbeatSeconds;
""",
              """    /**
     * workerId lease TTL（秒）：须严格大于 heartbeatSeconds，否则租约会在下次续约前到期，
     * 导致 workerId 被其他节点抢占并发出重复 ID（启动期校验，见 SnowflakeAutoConfiguration）
     */
    private long ttlSeconds = 60;

    /**
     * heartbeat 间隔（秒）；未显式配置时按 ttlSeconds / 3 计算（见 getHeartbeatSeconds）
     */
    private Long heartbeatSeconds;
""",
          ),
          (
              """    /**
     * datacenterId
     */
    private int datacenterId = 0;
""",
              """    /**
     * datacenterId：底层 SnowflakeIdGenerator 固定 5 位（取值 0~31），超限将产生位溢出导致 ID 重复
     */
    private int datacenterId = 0;
""",
          ),
      ])

apply("aicyi-midware/aicyi-midware-spring-boot-starter/src/main/java/io/github/aicyi/midware/starter/autoconfigure/SnowflakeAutoConfiguration.java",
      [
          (
              """    /**
     * 配置契约校验（fail-fast）：底层发号器固定 5 位 workerId，超限配置会导致运行期发号异常；
     * serviceName 为空或使用默认值时多服务共享 workerId 命名空间
     */
    private void validateProperties(SnowflakeProperties properties) {

        if (properties.getWorkerIdBits() != SnowflakeProperties.FIXED_WORKER_ID_BITS) {
            throw new IllegalStateException(
                    "aicyi.snowflake.worker-id-bits only supports " + SnowflakeProperties.FIXED_WORKER_ID_BITS
                            + " (SnowflakeIdGenerator uses a fixed 5-bit workerId), but was set to " + properties.getWorkerIdBits());
        }

        String serviceName = properties.getServiceName();
        if (serviceName == null || serviceName.trim().isEmpty()) {
            throw new IllegalStateException("aicyi.snowflake.service-name must not be blank");
        }

        if (SnowflakeProperties.DEFAULT_SERVICE_NAME.equals(serviceName)) {
            logger.warn("aicyi.snowflake.service-name uses default value '{}', multiple services sharing the same Redis "
                    + "will compete for the same workerId namespace. Please configure it explicitly", serviceName);
        }
    }
""",
              """    /**
     * 配置契约校验（fail-fast）：底层发号器固定 5 位 workerId，超限配置会导致运行期发号异常；
     * serviceName 为空或使用默认值时多服务共享 workerId 命名空间；
     * 续约周期与租约 TTL 的关系错误会让 workerId 在运行期被其他节点抢占，进而发出重复 ID，
     * 故一并前置到启动期拦截，不留到线上暴露
     */
    private void validateProperties(SnowflakeProperties properties) {

        if (properties.getWorkerIdBits() != SnowflakeProperties.FIXED_WORKER_ID_BITS) {
            throw new IllegalStateException(
                    "aicyi.snowflake.worker-id-bits only supports " + SnowflakeProperties.FIXED_WORKER_ID_BITS
                            + " (SnowflakeIdGenerator uses a fixed 5-bit workerId), but was set to " + properties.getWorkerIdBits());
        }

        if (properties.getDatacenterId() < 0 || properties.getDatacenterId() > MAX_DATACENTER_ID) {
            throw new IllegalStateException(
                    "aicyi.snowflake.datacenter-id must be in [0, " + MAX_DATACENTER_ID + "] (5-bit), but was set to "
                            + properties.getDatacenterId());
        }

        if (properties.getTtlSeconds() <= 0) {
            throw new IllegalStateException("aicyi.snowflake.ttl-seconds must be positive, but was set to "
                    + properties.getTtlSeconds());
        }

        if (properties.getHeartbeatSeconds() <= 0) {
            throw new IllegalStateException("aicyi.snowflake.heartbeat-seconds must be positive, but was set to "
                    + properties.getHeartbeatSeconds());
        }

        // 续约必须早于租约到期，否则 lease 会在两次心跳之间被 Redis 回收并被其他节点抢占
        if (properties.getHeartbeatSeconds() >= properties.getTtlSeconds()) {
            throw new IllegalStateException("aicyi.snowflake.heartbeat-seconds (" + properties.getHeartbeatSeconds()
                    + ") must be less than aicyi.snowflake.ttl-seconds (" + properties.getTtlSeconds()
                    + "), otherwise the lease expires before it can be renewed");
        }

        String serviceName = properties.getServiceName();
        if (serviceName == null || serviceName.trim().isEmpty()) {
            throw new IllegalStateException("aicyi.snowflake.service-name must not be blank");
        }

        if (SnowflakeProperties.DEFAULT_SERVICE_NAME.equals(serviceName)) {
            logger.warn("aicyi.snowflake.service-name uses default value '{}', multiple services sharing the same Redis "
                    + "will compete for the same workerId namespace. Please configure it explicitly", serviceName);
        }
    }
""",
          ),
          (
              """    private final Logger logger = LoggerFactory.getLogger(getClass());
""",
              """    /**
     * datacenterId 上限：底层 SnowflakeIdGenerator 固定 5 位 datacenterId
     */
    private static final int MAX_DATACENTER_ID = 31;

    private final Logger logger = LoggerFactory.getLogger(getClass());
""",
          ),
      ])

# ============================================================ P1-12 Duration 单位
apply("aicyi-midware/aicyi-midware-spring-boot-starter/src/main/java/io/github/aicyi/midware/starter/properties/TokenProperties.java",
      [
          (
              """import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;
""",
              """import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.convert.DurationUnit;

import java.time.Duration;
import java.time.temporal.ChronoUnit;
""",
          ),
          (
              """    /**
     * RefreshToken 有效期
     */
    private Duration refreshTokenTtl = Duration.ofDays(7);

    /**
     * AccessToken 有效期
     */
    private Duration accessTokenTtl = Duration.ofHours(2);
""",
              """    /**
     * RefreshToken 有效期，默认 7 天。
     * <p>
     * <b>单位必须显式声明</b>：Spring Boot 对 {@link Duration} 类型的裸数字默认按<b>毫秒</b>绑定，
     * 而 {@code aicyi.token.*-ttl} 的既有配置与文档均以秒为单位（如 {@code access-token-ttl: 86400} 意为 1 天）。
     * 缺少 {@code @DurationUnit} 会让 86400 被解析为 86.4 秒，AccessToken 上线即近乎立即过期
     */
    @DurationUnit(ChronoUnit.SECONDS)
    private Duration refreshTokenTtl = Duration.ofDays(7);

    /**
     * AccessToken 有效期，默认 2 小时；单位约定同 {@link #refreshTokenTtl}（裸数字按秒解析）
     */
    @DurationUnit(ChronoUnit.SECONDS)
    private Duration accessTokenTtl = Duration.ofHours(2);
""",
          ),
      ])

# ============================================================ P1-5 metadata JSON
write_full("aicyi-midware/aicyi-midware-spring-boot-starter/src/main/resources/META-INF/additional-spring-configuration-metadata.json",
           '''{
  "properties": [
    {
      "name": "aicyi.mq.rabbitmq.enabled",
      "type": "java.lang.Boolean",
      "defaultValue": true,
      "description": "是否装配 RabbitMQ 相关组件；缺省视为 true（引入模块即生效），置 false 可在保留依赖的前提下关闭装配。"
    },
    {
      "name": "aicyi.redis.enabled",
      "type": "java.lang.Boolean",
      "defaultValue": true,
      "description": "是否装配 Redis 组件（EnhancedRedisTemplateFactory、CacheLock、DistributedLockManager）；缺省视为 true，置 false 可在保留依赖的前提下关闭装配。"
    },
    {
      "name": "aicyi.mybatis-plus.enabled",
      "type": "java.lang.Boolean",
      "defaultValue": true,
      "description": "是否装配 MyBatis-Plus 增强组件；缺省视为 true，置 false 可在保留依赖的前提下关闭装配。"
    },
    {
      "name": "aicyi.snowflake.enabled",
      "type": "java.lang.Boolean",
      "defaultValue": false,
      "description": "是否装配 Redis 协调的雪花 ID 组件。默认关闭：开启后会在 Redis 占用 workerId 名额并常驻心跳线程，仅需缓存或 Token 能力的服务不应启用。"
    },
    {
      "name": "aicyi.token.enabled",
      "type": "java.lang.Boolean",
      "defaultValue": false,
      "description": "是否装配认证 Token 组件（AuthenticationConfig、AuthenticationTokenService）。默认关闭：开启后 secret-key、issuer、subject、principal-type 均为必填，缺失即启动失败。"
    }
  ]
}''')

print("P1-1/2/3/4/5/12 done")
