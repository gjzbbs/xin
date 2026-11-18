#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_qx_sngxpro.py — 把本仓库的分流规则改写成「少年歌行PRO 小白配置」的组名。

为什么要这一步：用户现有的 QX 配置（quantumult_20261118221214.conf）只有 19 个组，
命名是 Bing / 延迟最低 / 全球加速 / 黑白名单 / 网飞影视 …，与本仓库 ini 里的
🚀 节点选择 / 📘 Meta / 🎯 全球直连 完全不同。规则里的策略名在目标配置里不存在时
QX 会直接忽略该条规则，所以必须先做名字映射。

产物：
  qx/QX-sngxpro-meta.list  只含 📘 Meta 那 556 条（"muse 规则"本体），策略统一为 --meta-group
  qx/QX-sngxpro-all.list   全套 5137 条，末尾自带 geoip,cn,direct + final,黑白名单

用法：
  python qx/build_qx_sngxpro.py                 # 默认把 Meta 映射到「全球加速」
  python qx/build_qx_sngxpro.py --meta-group Meta   # 你若新加了 Meta 组，映射到它
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "QX-all.list")

# 本仓库 33 组 → 用户现有配置里的组
MAP = {
    "🎯 全球直连": "direct",
    "🛑 广告拦截": "reject",
    "🍃 应用净化": "reject",
    "🚀 节点选择": "全球加速",
    "♻️ 自动选择": "延迟最低",
    "📺 省流节点": "延迟最低",
    "📢 谷歌FCM": "全球加速",
    "🎥 NETFLIX": "网飞影视",
    "🎥 DisneyP": "网飞影视",
    "🎥 YouTube": "国际媒体",
    "📺 哔哩海外": "港台番剧",
    "🤖 人工智能": "全球加速",
    "Ⓜ️ 微软服务": "Bing",
    "🍎 苹果服务": "苹果服务",
    "📲 电报消息": "电报代理",
    "🎮 外服游戏": "IPLC",
    "📺 巴哈姆特": "港台番剧",
    "🌍 国外媒体": "国际媒体",
    "🌏 国内媒体": "direct",
    "🎶 网易音乐": "direct",
    "🐟 漏网之鱼": "黑白名单",
    # 📘 Meta 由 --meta-group 决定
}

# 用户配置里真实存在的策略（含 QX 内置 direct/reject/proxy）
HIS = {
    "Bing", "延迟最低", "TikTok", "新加坡", "美国", "日本", "韩国", "香港", "台湾",
    "特殊", "IPLC", "苹果服务", "全球加速", "港台番剧", "国际媒体", "声田音乐",
    "网飞影视", "电报代理", "黑白名单", "direct", "reject", "proxy",
}


def map_line(line, meta_group):
    p = [x.strip() for x in line.split(",")]
    if p[0].upper() == "FINAL":
        p[1] = MAP.get(p[1], p[1])
    else:
        p[2] = meta_group if p[2] == "📘 Meta" else MAP.get(p[2], p[2])
    return ",".join(p), p[-1] if p[0].upper() == "FINAL" else p[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta-group", default="全球加速",
                    help="📘 Meta 那套规则落到你现有的哪个组（默认 全球加速）")
    args = ap.parse_args()
    mg = args.meta_group
    if mg not in HIS:
        print("警告：%r 不在你现有配置的策略里，规则会被 QX 忽略。" % mg)
        print("      现有可用：%s" % "、".join(sorted(HIS - {"direct", "reject", "proxy"})))

    rows = [l.strip() for l in open(SRC, encoding="utf-8")
            if l.strip() and not l.startswith("#")]
    if not rows:
        sys.exit("QX-all.list 为空，先跑 python qx/build_qx.py")

    # ---- 全套
    out, bad = [], set()
    for r in rows:
        line, pol = map_line(r, mg)
        out.append(line)
        if pol not in HIS:
            bad.add(pol)
    hdr = [
        "# gjzbbs/xin 全量分流 · 少年歌行PRO 组名版",
        "# %d 条，文件内顺序 = 匹配优先级；末尾自带 geoip,cn,direct 与 final,黑白名单" % len(out),
        "# 用法：加到 QX「设置 → 资源 → 分流」，并把配置文件 [filter_local] 里的",
        "#       geoip, cn, direct 与 final, 黑白名单 两条删掉（本文件已含）",
        "",
    ]
    open(os.path.join(HERE, "QX-sngxpro-all.list"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(hdr + out) + "\n")

    # ---- 只有 Meta / muse（源里策略是 📘 Meta 的行）
    meta = []
    for r in rows:
        p = [x.strip() for x in r.split(",")]
        if len(p) >= 3 and p[2] == "📘 Meta":
            p[2] = mg
            meta.append(",".join(p))
    mhdr = [
        "# gjzbbs/xin · 📘 Meta 系（Facebook / Instagram / WhatsApp / Threads / muse.ai 等）",
        "# %d 条，策略统一为 %s" % (len(meta), mg),
        "# 用法：加到 QX「设置 → 资源 → 分流」，然后把它拖到「本地规则」上面一行",
        "#       （QX 1.0.30+ 支持调整本地/远程加载顺序；否则本地 final 会先截断，本资源不生效）",
        "",
    ]
    open(os.path.join(HERE, "QX-sngxpro-meta.list"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(mhdr + meta) + "\n")

    print("全部 %d 条 → qx/QX-sngxpro-all.list" % len(out))
    print("Meta  %d 条 → qx/QX-sngxpro-meta.list（策略=%s）" % (len(meta), mg))
    if bad:
        print("未映射到现有策略的名字：%s" % "、".join(sorted(bad)))
        return 1
    print("策略映射校验：全部命中你现有 19 个组，0 个未定义")
    return 0


if __name__ == "__main__":
    sys.exit(main())
