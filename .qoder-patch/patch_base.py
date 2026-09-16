#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确文本替换补丁执行器：每条替换必须命中且唯一，否则整体失败不留半成品。"""
import sys

ROOT = "/Users/liangchaomin/workspace/develop/aicyi"


def apply(rel_path, replacements):
    path = ROOT + "/" + rel_path
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for idx, (old, new) in enumerate(replacements):
        count = content.count(old)
        if count != 1:
            print("FAIL %s #%d matched %d times" % (rel_path, idx, count))
            sys.exit(1)
        content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK   %s (%d edits)" % (rel_path, len(replacements)))


if __name__ == "__main__":
    print("patch_base ready")
