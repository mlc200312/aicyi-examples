#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RedisCache 重复代码消除：get(key, loader) 中"首次竞争锁加载"与"等待超时后再竞争锁加载"
两段 26 行逻辑完全相同（仅锁句柄变量名不同），抽取为私有方法 loadUnderLock。

行为等价性：两段原逻辑在所有路径上都是 return 或 throw，块内对 result 的重新赋值从不逃逸到
后续代码，故抽取为返回 T 的私有方法后语义逐条一致（双重检查、回源、回填、统计、finally 释放锁）。
"""
import sys

sys.path.insert(0, "/Users/liangchaomin/workspace/develop/aicyi-examples/.qoder-patch")
from patch_base import apply  # noqa: E402

CACHE = "aicyi-midware/aicyi-midware-redis/src/main/java/io/github/aicyi/midware/redis/cache/RedisCache.java"

FIRST_BLOCK = (
    "        CacheLockHandle lockHandle = lock.tryLock(lockKey, config.getLockTtl());\n"
    "\n"
    "        if (lockHandle != null) {\n"
    "            long start = System.nanoTime();\n"
    "\n"
    "            try {\n"
    "                result = lookup(key);\n"
    "\n"
    "                if (!result.isNullValue()) {\n"
    "                    return result.getData();\n"
    "                }\n"
    "\n"
    "                T loaded = loader.load(key);\n"
    "\n"
    "                put(key, loaded);\n"
    "\n"
    "                stats.recordLoadSuccess(System.nanoTime() - start);\n"
    "\n"
    "                return loaded;\n"
    "            } catch (Exception e) {\n"
    "                stats.recordLoadFailure(System.nanoTime() - start);\n"
    "                throw e;\n"
    "            } finally {\n"
    "                unlockQuietly(lockHandle);\n"
    "            }\n"
    "        }\n"
)

FALLBACK_BLOCK = (
    "        CacheLockHandle fallbackHandle = lock.tryLock(lockKey, config.getLockTtl());\n"
    "\n"
    "        if (fallbackHandle != null) {\n"
    "            long start = System.nanoTime();\n"
    "\n"
    "            try {\n"
    "                result = lookup(key);\n"
    "\n"
    "                if (!result.isNullValue()) {\n"
    "                    return result.getData();\n"
    "                }\n"
    "\n"
    "                T loaded = loader.load(key);\n"
    "\n"
    "                put(key, loaded);\n"
    "\n"
    "                stats.recordLoadSuccess(System.nanoTime() - start);\n"
    "\n"
    "                return loaded;\n"
    "            } catch (Exception e) {\n"
    "                stats.recordLoadFailure(System.nanoTime() - start);\n"
    "                throw e;\n"
    "            } finally {\n"
    "                unlockQuietly(fallbackHandle);\n"
    "            }\n"
    "        }\n"
)

LOAD_UNDER_LOCK = (
    "    /**\n"
    "     * 持锁加载：先双重检查缓存（等待/竞争锁期间持锁者可能已完成回填），未命中才回源并写入，\n"
    "     * 加载耗时计入统计；无论提前返回、加载成功还是抛异常，锁都在 finally 中释放。\n"
    "     *\n"
    "     * @param key        缓存逻辑 key\n"
    "     * @param lockHandle 已获取的锁句柄，不可为 null（判空由调用方负责）\n"
    "     * @param loader     回源加载器\n"
    "     * @return 缓存中已存在的值，或本次回源加载并回填的值\n"
    "     */\n"
    "    private T loadUnderLock(String key, CacheLockHandle lockHandle, CacheLoader<String, T> loader) {\n"
    "\n"
    "        long start = System.nanoTime();\n"
    "\n"
    "        try {\n"
    "            CacheWrapper<T> result = lookup(key);\n"
    "\n"
    "            if (!result.isNullValue()) {\n"
    "                return result.getData();\n"
    "            }\n"
    "\n"
    "            T loaded = loader.load(key);\n"
    "\n"
    "            put(key, loaded);\n"
    "\n"
    "            stats.recordLoadSuccess(System.nanoTime() - start);\n"
    "\n"
    "            return loaded;\n"
    "        } catch (Exception e) {\n"
    "            stats.recordLoadFailure(System.nanoTime() - start);\n"
    "            throw e;\n"
    "        } finally {\n"
    "            unlockQuietly(lockHandle);\n"
    "        }\n"
    "    }\n"
    "\n"
)

UNLOCK_QUIETLY_DOC = (
    "    /**\n"
    "     * 防御性释放锁：锁过期后的 unlock 失败（如 Redisson 租约过期）不得在 finally 中\n"
)

apply(CACHE,
      [
          # 1. 首次竞争锁：26 行 → 1 行委托
          (
              FIRST_BLOCK,
              "        CacheLockHandle lockHandle = lock.tryLock(lockKey, config.getLockTtl());\n"
              "\n"
              "        if (lockHandle != null) {\n"
              "            return loadUnderLock(key, lockHandle, loader);\n"
              "        }\n",
          ),
          # 2. 等待超时后的二次竞争：26 行 → 1 行委托
          (
              FALLBACK_BLOCK,
              "        CacheLockHandle fallbackHandle = lock.tryLock(lockKey, config.getLockTtl());\n"
              "\n"
              "        if (fallbackHandle != null) {\n"
              "            return loadUnderLock(key, fallbackHandle, loader);\n"
              "        }\n",
          ),
          # 3. 抽取的私有方法置于 unlockQuietly 之前，两个锁相关helper相邻
          (
              UNLOCK_QUIETLY_DOC,
              LOAD_UNDER_LOCK + UNLOCK_QUIETLY_DOC,
          ),
      ])

print("RedisCache duplicated fragment removed")
