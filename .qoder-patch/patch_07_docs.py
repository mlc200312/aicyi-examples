#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文档同步：
1) P1-1 redisson 改为 optional 属接入契约变更，必须在分布式锁章节明示「需自行声明依赖」；
2) metadata JSON 已把 aicyi.token.enabled 标注为缺省关，README「唯一缺省关的是 snowflake」
   的表述与之冲突（该表述在改动前即已不准确，TokenProperties.enabled 一直为 false），一并校正。
"""
import sys

sys.path.insert(0, "/Users/liangchaomin/workspace/develop/aicyi-examples/.qoder-patch")
from patch_base import apply  # noqa: E402

# ------------------------------------------------------------ redisson optional 接入契约
apply("docs/advanced.md", [
    (
        "> 启用前置：`aicyi.redis.enabled=true` 且容器中存在 `RedissonClient` Bean 时，\n"
        "> 自动装配 `DistributedLockManager`（`RedissonDistributedLockManager`）。Redisson 版本为 3.27.2（由 BOM 统一管理）。\n",
        "> 启用前置：`aicyi.redis.enabled=true` 且容器中存在 `RedissonClient` Bean 时，\n"
        "> 自动装配 `DistributedLockManager`（`RedissonDistributedLockManager`）。Redisson 版本为 3.27.2（由 BOM 统一管理）。\n"
        ">\n"
        "> **依赖声明要求**：`aicyi-midware-redis` 将 `org.redisson:redisson` 声明为 `optional`，\n"
        "> 因为 Redisson 仅被 `lock` 包与 `RedissonCacheLock` 使用，却会带入 netty、kryo、rxjava3、\n"
        "> byte-buddy 等 20+ 传递依赖 —— 仅需 `RedisCache` / `TokenService` / 雪花 ID 的接入方不应被迫引入。\n"
        "> 因此使用 `DistributedLockManager`、`RedissonCacheLock` 或自行构造 `RedissonClient` 的模块，\n"
        "> **必须在自己的 pom 中显式声明该依赖**（版本由 BOM 管理，不要写 `<version>`）：\n"
        ">\n"
        "> ```xml\n"
        "> <dependency>\n"
        ">     <groupId>org.redisson</groupId>\n"
        ">     <artifactId>redisson</artifactId>\n"
        "> </dependency>\n"
        "> ```\n"
        ">\n"
        "> 未声明时不会启动失败：`RedissonLockConfiguration` 由 `@ConditionalOnClass(RedissonClient.class)`\n"
        "> 守卫，类路径缺失即整体跳过装配，表现为 `DistributedLockManager` Bean 不存在。\n",
    ),
])

# ------------------------------------------------------------ README 开关表与口径约定
apply("docs/README.md", [
    (
        "| `aicyi.snowflake.enabled` | **关** | 分布式 Snowflake ID，需显式开启 |\n",
        "| `aicyi.snowflake.enabled` | **关** | 分布式 Snowflake ID，需显式开启 |\n"
        "| `aicyi.token.enabled` | **关** | 认证 Token 组件，需显式开启；开启后 `secret-key`/`issuer`/`subject`/`principal-type` 均为必填 |\n",
    ),
    (
        "> **唯一缺省关的是 `aicyi.snowflake.enabled`**：Snowflake 需 Redis 协调 WorkerId 租约，\n"
        "> 且多实例误用同一 workerId 会产生重复 ID，故要求显式开启。\n",
        "> **缺省关的只有 `aicyi.snowflake.enabled` 与 `aicyi.token.enabled`**：前者需 Redis 协调 WorkerId 租约，\n"
        "> 多实例误用同一 workerId 会产生重复 ID；后者一旦装配即要求密钥等必填项就位，\n"
        "> 故两者均要求显式开启，避免仅需缓存能力的服务被隐式拉起。\n",
    ),
])

print("docs sync done")
