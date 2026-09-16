#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-2 连带修正：RedisAutoConfiguration 类注释仍描述 redis 模块为 provided+optional，
patch_04 已将其收敛为 optional，注释须同步，否则会误导后续维护者按 provided 语义判断类路径来源。
"""
import sys

sys.path.insert(0, "/Users/liangchaomin/workspace/develop/aicyi-examples/.qoder-patch")
from patch_base import apply  # noqa: E402

apply("aicyi-midware/aicyi-midware-spring-boot-starter/src/main/java/io/github/aicyi/midware/starter/autoconfigure/RedisAutoConfiguration.java",
      [
          (
              " * 类级 @ConditionalOnClass 守卫：starter 中 redis 模块为 provided+optional，\n"
              " * 需同时覆盖 spring-data-redis 与 aicyi-midware-redis 两侧的类，\n"
              " * 业务未引入 redis 时整个配置类跳过加载，避免 NoClassDefFoundError\n",
              " * 类级 @ConditionalOnClass 守卫：starter 中 redis 模块为 optional（不向下游传递），\n"
              " * 需同时覆盖 spring-data-redis 与 aicyi-midware-redis 两侧的类，\n"
              " * 业务未引入 redis 时整个配置类跳过加载，避免 NoClassDefFoundError；\n"
              " * Redisson 相关装配另由嵌套 RedissonLockConfiguration 的 @ConditionalOnClass 二次隔离，\n"
              " * 因 aicyi-midware-redis 已将 redisson 标记 optional，仅需缓存/Token 的接入方类路径上可以没有它\n",
          ),
      ])

print("P1-2 comment sync done")
