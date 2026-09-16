#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-6: SPI 分层治理 —— 移除实现模块中对外暴露的空标记接口 RedisTokenService。

RedisTokenService<P> 仅声明 `extends TokenService<String, P>` 且无任何自有方法，
属实现模块对外 public 暴露的冗余类型；父类 AbstractTokenService<P> 已 implements
TokenService<String, P>，故实现类去掉该 implements 子句后契约完全不变。
"""
import sys

sys.path.insert(0, "/Users/liangchaomin/workspace/develop/aicyi-examples/.qoder-patch")
from patch_base import apply  # noqa: E402

apply("aicyi-midware/aicyi-midware-redis/src/main/java/io/github/aicyi/midware/redis/token/RedisTokenServiceImpl.java",
      [
          (
              "public class RedisTokenServiceImpl<P> extends AbstractTokenService<P> implements RedisTokenService<P> {",
              "public class RedisTokenServiceImpl<P> extends AbstractTokenService<P> {",
          ),
      ])

print("P1-6 impl clause done")
