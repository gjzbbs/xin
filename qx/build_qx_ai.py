#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_qx_ai.py — 生成「AI / 人工智能」的独立 QuantumultX 分流资源。

源是仓库根目录的 custom-ai.list（ShellCrash 用的 Clash 格式），
本脚本把它转成 QX 原生类型（DOMAIN→host、DOMAIN-SUFFIX→host-suffix、
DOMAIN-KEYWORD→host-keyword），并做三件母版没做的事：

1. 剔除会误伤的通用域名（www.google.com / accounts.google.com / notion.so …）
2. 把 Meta 系的 AI 域名让给 📘 Meta 组（museai.com 与 muse.ai 同源，
   用户最初的要求就是 muse 走 Meta，不能在这里被 AI 抢走）
3. 补一批母版缺的常用 AI 服务（claude.com / notebooklab / v0 / bolt.new …）

产物 qx/QX-ai.list 可直接加到 QX「设置 → 资源 → 分流」。

用法：
  python qx/build_qx_ai.py                 # 策略名 AI
  python qx/build_qx_ai.py --group 人工智能  # 改成别的组名
  python qx/build_qx_ai.py --with-wide     # 把剔除的宽泛域名也加回来
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "custom-ai.list")

# Clash 类型 → QX 原生类型
TYPE_MAP = {
    "DOMAIN": "host",
    "DOMAIN-SUFFIX": "host-suffix",
    "DOMAIN-KEYWORD": "host-keyword",
    "HOST": "host",
    "HOST-SUFFIX": "host-suffix",
    "HOST-KEYWORD": "host-keyword",
}

# 母版里这些域名放 AI 组会误伤：它们是 Google / Meta / Notion 的通用入口，
# 分到 AI 组等于把搜索、云盘、登录、笔记全推到 AI 线路上。
WIDE = {
    "www.google.com",
    "apis.google.com",
    "accounts.google.com",
    "fb.okta.com",
    "accountscenter.com",
    "metamask.com",
    "notion.so",
    "notion.site",
    "siliconflow.cn",      # 国内站，走代理反而更慢
}

# 让给 📘 Meta 组：与 muse.ai 同源，用户原始诉求就是 muse 走 Meta
TO_META = {
    "museai.com",
}

# 母版缺的常用 AI 服务
EXTRA = [
    "DOMAIN-SUFFIX,claude.com",
    "DOMAIN-SUFFIX,notebooklm.google.com",
    "DOMAIN-SUFFIX,labs.google",
    "DOMAIN-SUFFIX,v0.dev",
    "DOMAIN-SUFFIX,v0.app",
    "DOMAIN-SUFFIX,bolt.new",
    "DOMAIN-SUFFIX,lovable.dev",
    "DOMAIN-SUFFIX,civitai.com",
    "DOMAIN-SUFFIX,openart.ai",
    "DOMAIN-SUFFIX,krea.ai",
    "DOMAIN-SUFFIX,openai.azure.com",
]


def norm(t, v):
    """返回 (qx_type, value) 或 None"""
    t = t.strip().upper()
    if t not in TYPE_MAP:
        return None
    v = v.strip().rstrip(".").lower()
    if not v:
        return None
    if TYPE_MAP[t] in ("host", "host-suffix"):
        v = v.replace("*.", "").replace("http://", "").replace("https://", "").split("/")[0]
        if not v:
            return None
        try:
            v.encode("ascii")
        except UnicodeEncodeError:
            try:
                v = v.encode("idna").decode("ascii")
            except Exception:
                return None
    return TYPE_MAP[t], v


def load():
    lines = []
    if os.path.exists(SRC):
        for l in open(SRC, encoding="utf-8"):
            l = l.strip()
            if not l or l.startswith("#"):
                continue
            p = [x.strip() for x in l.split(",")]
            if len(p) >= 2:
                lines.append((p[0], p[1]))
    lines += [(x.split(",")[0], x.split(",")[1]) for x in EXTRA]
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="AI", help="规则落到哪个策略组（默认 AI）")
    ap.add_argument("--with-wide", action="store_true", help="保留会被误伤的宽泛域名")
    ap.add_argument("--out", default=None, help="输出文件名")
    args = ap.parse_args()
    g = args.group

    seen = set()
    rows, dropped, moved = [], [], []
    for t, v in load():
        r = norm(t, v)
        if not r:
            continue
        qt, val = r
        if val in TO_META:
            moved.append(val)
            continue
        if val in WIDE and not args.with_wide:
            dropped.append(val)
            continue
        key = (qt, val)
        if key in seen:
            continue
        seen.add(key)
        rows.append("%s,%s,%s" % (qt, val, g))

    out = args.out or os.path.join(HERE, "QX-ai.list")
    hdr = [
        "# gjzbbs/xin · AI / 人工智能 分流清单（QuantumultX 原生格式）",
        "# 共 %d 条，策略统一为 %s" % (len(rows), g),
        "# 源：custom-ai.list（Clash 格式）+ 补齐的常用 AI 服务，已转 QX 类型名",
        "#",
        "# 用法：QX → 设置 → 资源 → 分流 → + 粘贴下面这行",
        "#   https://raw.githubusercontent.com/gjzbbs/xin/main/qx/QX-ai.list",
        "# 前提：配置文件 [policy] 里要有一个叫 %s 的策略组" % g,
        "#",
        "# 注意：本文件不含 geoip 与 final。若要让它单独生效，" ,
        "#       在 [filter_remote] 里把它排在主分流资源之前（QX 1.0.30+ 可拖动顺序）。",
        "",
    ]
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(hdr + rows) + "\n")

    print("输出 %s：%d 条，策略=%s" % (os.path.basename(out), len(rows), g))
    if dropped:
        print("剔除宽泛域名 %d 个：%s" % (len(dropped), "、".join(sorted(dropped))))
    if moved:
        print("让给 Meta 组 %d 个：%s" % (len(moved), "、".join(sorted(moved))))
    return 0


if __name__ == "__main__":
    sys.exit(main())