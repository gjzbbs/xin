#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_qx.py — 把 ShellClash_Custom.ini（Clash/mihomo 版分流规格）转换成
              QuantumultX 可直接导入的 .conf + 分策略规则集。

单一真源：ShellClash_Custom.ini 里的 ruleset= / custom_proxy_group=。
改了 ini 或任一 .list 之后，重跑本脚本 + push，QX 端「更新资源」即生效。

用法：
    python qx/build_qx.py                # 默认：跳过超大的 ChinaDomain（用 geoip,cn 兜底）
    python qx/build_qx.py --with-china-domain   # 全量还原（规则多，QX 会慢）
    python qx/build_qx.py --remote       # 自维护 .list 也从 GitHub 拉（而不是读本地）
    python qx/build_qx.py --servers qx/servers.txt

产物：
    qx/filter/NN-<slug>.list   QX 原生规则（每行已带策略名），按 ini 顺序编号
    qx/QuantumultX.conf        完整配置骨架（policy / filter_remote / server 占位）
    qx/servers.txt             节点名清单（策略组按正则从这里筛）
    qx/build_report.txt        本次构建统计
"""

import argparse
import hashlib
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
INI_PATH = os.path.join(REPO, "ShellClash_Custom.ini")
OUT_DIR = HERE
FILTER_DIR = os.path.join(HERE, "filter")
CACHE_DIR = os.path.join(HERE, ".cache")

RAW_BASE = "https://raw.githubusercontent.com/gjzbbs/xin/main/qx/filter"
SELF_REPO = "raw.githubusercontent.com/gjzbbs/xin/main/"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"

# QX 支持的规则类型（其余跳过并计数）
QX_TYPES = {
    "DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD",
    "IP-CIDR", "IP-CIDR6", "GEOIP", "IP-ASN",
    "USER-AGENT", "URL-REGEX",
    "HOST", "HOST-SUFFIX", "HOST-KEYWORD",
    "SRC-IP-CIDR", "DST-PORT", "SRC-PORT",
}

SLUGS = {
    "🎯 全球直连": "direct",
    "🛑 广告拦截": "adblock",
    "🍃 应用净化": "appclean",
    "🚀 节点选择": "proxy",
    "📘 Meta": "meta",
    "♻️ 自动选择": "auto",
    "📺 省流节点": "saver",
    "📢 谷歌FCM": "fcm",
    "🎥 NETFLIX": "netflix",
    "🎥 DisneyP": "disney",
    "🎥 YouTube": "youtube",
    "📺 哔哩海外": "bilibili",
    "🤖 人工智能": "ai",
    "Ⓜ️ 微软服务": "microsoft",
    "🍎 苹果服务": "apple",
    "📲 电报消息": "telegram",
    "🎮 外服游戏": "game",
    "📺 巴哈姆特": "bahamut",
    "🌍 国外媒体": "proxymedia",
    "🌏 国内媒体": "chinamedia",
    "🎶 网易音乐": "netease",
    "🐟 漏网之鱼": "final",
}

# 默认跳过的超大规则集（用 geoip,cn + domain-suffix,cn 兜底，手机端更省电）
SKIP_UNLESS_FULL = ("ChinaIp.list", "ChinaIpV6.list")


# ---------------------------------------------------------------- fetch
def _cache_path(key):
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, h + ".txt")


def fetch(url, use_cache=True):
    """下载文本，raw 失败依次走镜像；结果缓存 12 小时。"""
    cp = _cache_path(url)
    if use_cache and os.path.exists(cp) and time.time() - os.path.getmtime(cp) < 12 * 3600:
        return open(cp, encoding="utf-8", errors="replace").read()

    candidates = [url]
    p = url.split("raw.githubusercontent.com/", 1)[-1]
    candidates += [
        "https://ghproxy.net/https://raw.githubusercontent.com/" + p,
        "https://gh-proxy.net/https://raw.githubusercontent.com/" + p,
        "https://cdn.statically.io/gh/" + p,
    ]
    last = None
    for u in candidates:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            txt = data.decode("utf-8", "replace")
            if txt.lstrip().startswith("<!DOCTYPE") or "<html" in txt[:400].lower():
                last = "html-not-a-list: " + u
                continue
            os.makedirs(CACHE_DIR, exist_ok=True)
            open(cp, "w", encoding="utf-8").write(txt)
            return txt
        except Exception as e:  # noqa: BLE001
            last = "%s: %s" % (u, e)
    raise RuntimeError("下载失败 %s (%s)" % (url, last))


# ---------------------------------------------------------------- ini
def parse_ini(path):
    rulesets, groups = [], []
    for raw in open(path, encoding="utf-8"):
        s = raw.strip()
        if not s or s[0] in ";#[" or "=" not in s:
            continue
        k, _, v = s.partition("=")
        if k == "ruleset":
            policy, _, spec = v.partition(",")
            rulesets.append((policy.strip(), spec.strip()))
        elif k == "custom_proxy_group":
            parts = v.split("`")
            if len(parts) >= 2:
                groups.append((parts[0].strip(), parts[1].strip(), [x.strip() for x in parts[2:]]))
    return rulesets, groups


def load_servers(path):
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def resolve_source(spec, remote):
    """ruleset 的 spec → ('text', 内容, 显示名)"""
    if spec.startswith("http"):
        if not remote and SELF_REPO in spec:
            name = spec.split("/main/", 1)[1].split("?")[0]
            local = os.path.join(REPO, name)
            if os.path.exists(local):
                return open(local, encoding="utf-8").read(), name + " (本地)"
        return fetch(spec), spec.split("?")[0]
    raise RuntimeError("无法识别的 ruleset: " + spec)


# ---------------------------------------------------------------- rules
def to_qx(line, policy, skipped):
    r = line.strip()
    if r.startswith("- "):
        r = r[2:].strip()
    r = r.strip().strip("'\"").strip()
    if not r or r.startswith("#") or r.startswith(";") or r.startswith("payload:"):
        return None
    parts = [p.strip() for p in r.split(",")]
    if len(parts) < 2:
        return None
    t = parts[0].upper()
    value = parts[1]
    extra = parts[2:]
    if t not in QX_TYPES:
        skipped[t] = skipped.get(t, 0) + 1
        return None
    no_resolve = any(x.lower() == "no-resolve" for x in extra)
    # 原文件里若已带策略（纯文本 QX 格式），丢弃，用规则集策略覆盖
    out = "%s,%s,%s" % (t, value, policy)
    if no_resolve:
        out += ",no-resolve"
    return out


def build_segments(rulesets):
    segs = []
    for policy, spec in rulesets:
        if segs and segs[-1][0] == policy:
            segs[-1][1].append(spec)
        else:
            segs.append((policy, [spec]))
    return segs


def slugify(policy, used):
    base = SLUGS.get(policy)
    if not base:
        base = re.sub(r"[^a-z0-9]+", "-", policy.lower()).strip("-") or hashlib.md5(policy.encode()).hexdigest()[:6]
    name = base
    i = 2
    while name in used:
        name = "%s-%d" % (base, i)
        i += 1
    used.add(name)
    return name


# ---------------------------------------------------------------- policy
def build_policies(groups, servers):
    """把 ini 的策略组翻成 QX [policy] 段。

    ini 的 url-test 组形如： (正则)`http://测速url`300,,50
      - 测速 URL 与 "300,,50"（interval,tolerance）是 subconverter 的参数，
        QX 组不收这些，测速地址统一走 [general] server_check_url；
        这里只从中取出 interval / tolerance。
      - QX 组内不支持正则，只能列节点名或引用其它组，所以正则在这里离线求值。
    """
    leaf, noded = [], []

    def parse_members(ms):
        url, interval, tol, raw = None, 300, 50, []
        for m in ms:
            if not m:
                continue
            if re.fullmatch(r"\d+(,\d*)*", m):          # 300,,50
                nums = [x for x in m.split(",") if x.strip().isdigit()]
                if nums:
                    interval = int(nums[0])
                if len(nums) >= 2:
                    tol = int(nums[-1])
                continue
            if re.match(r"^(https?|tcp|quic)://", m):     # 测速 URL
                url = m
                continue
            if m.startswith("[]"):
                raw.append(m[2:].strip())
            elif m == ".*":
                raw.extend(servers)
            elif m.startswith("(") and m.endswith(")"):
                try:
                    rx = re.compile(m)
                except re.error:
                    continue
                raw.extend([s for s in servers if rx.search(s)])
            elif m in ("DIRECT", "REJECT"):
                raw.append(m)
            else:
                raw.append(m)
        seen, uniq = set(), []
        for x in raw:
            if x and x not in seen:
                seen.add(x)
                uniq.append(x)
        return uniq, interval, tol, url

    for name, gtype, ms in groups:
        mem, interval, tol, url = parse_members(ms)
        mem = [x for x in mem if x != name]           # 去自引用
        entry = (name, gtype, mem, interval, tol, url)
        if any(x not in servers and x not in ("DIRECT", "REJECT") for x in mem):
            noded.append(entry)
        else:
            leaf.append(entry)

    lines, notes = [], []
    for name, gtype, mem, interval, tol, url in leaf + noded:
        if not mem:
            mem = ["DIRECT"] if name == "🚀 手动切换" else ["🚀 手动切换"]
            notes.append("%s 在订阅里没有匹配节点，兜底到 %s（可在 QX 里手动选具体节点）" % (name, mem[0]))
        body = ", ".join(mem)
        if gtype == "url-test":
            lines.append("url-latency-benchmark=%s, %s, check-interval=%d, tolerance=%d"
                         % (name, body, interval, tol))
            if url:
                notes.append("%s 原测速地址 %s 在 QX 无法按组指定，改用全局 server_check_url" % (name, url))
        else:
            lines.append("static=%s, %s" % (name, body))
    return lines, notes



# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-china-domain", action="store_true", help="包含 ChinaIp/ChinaIpV6（数千条 IP 规则，QX 会略慢）")
    ap.add_argument("--remote", action="store_true", help="自维护 list 也走网络")
    ap.add_argument("--servers", default=os.path.join(HERE, "servers.txt"))
    ap.add_argument("--no-cn-suffix", action="store_true", help="不额外加 DOMAIN-SUFFIX,cn 兜底")
    args = ap.parse_args()

    rulesets, groups = parse_ini(INI_PATH)
    servers = load_servers(args.servers)
    os.makedirs(FILTER_DIR, exist_ok=True)

    segs = build_segments(rulesets)
    failed = []
    used, manifest, report = set(), [], []
    total_rules = 0
    skipped_all = {}

    for idx, (policy, specs) in enumerate(segs, 1):
        slug = slugify(policy, used)
        fname = "%02d-%s.list" % (idx, slug)
        lines, srcs, dropped = [], [], {}
        for spec in specs:
            if spec.startswith("[]"):
                body = spec[2:]
                key = body.replace(",", "|").lower()
                if key == "geoip|cn":
                    # .cn 域名直接命中，比等 DNS 解析出国内 IP 再走 GEOIP 更快更准
                    if not args.no_cn_suffix:
                        lines.append("DOMAIN-SUFFIX,cn,%s" % policy)
                    lines.append("GEOIP,CN,%s" % policy)
                    srcs.append("内置 GEOIP,CN")
                    continue
                if key == "final":
                    lines.append("FINAL,%s" % policy)
                    srcs.append("内置 FINAL")
                    continue
                continue
            if (not args.with_china_domain) and any(s in spec for s in SKIP_UNLESS_FULL):
                srcs.append(spec.split("/")[-1].split("?")[0] + " (按 --with-china-domain 跳过)")
                continue
            try:
                text, shown = resolve_source(spec, args.remote)
            except Exception as e:  # 单源失败不废掉整次构建
                failed.append("%s <- %s" % (spec, e))
                srcs.append(spec.split("/")[-1].split("?")[0] + " (下载失败，已跳过)")
                continue
            srcs.append(shown)
            for raw in text.splitlines():
                q = to_qx(raw, policy, dropped)
                if q:
                    lines.append(q)
        # 去重保序
        seen, uniq = set(), []
        for x in lines:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        lines = uniq

        header = [
            "# 策略：%s" % policy,
            "# 来源：%s" % "; ".join(srcs),
            "# 条数：%d（去重后；不支持的类型已丢弃：%s）" % (len(lines), dropped or "无"),
            "# 由 qx/build_qx.py 生成，勿手改（改 ShellClash_Custom.ini 或对应 .list 后重跑）",
            "",
        ]
        open(os.path.join(FILTER_DIR, fname), "w", encoding="utf-8", newline="\n").write(
            "\n".join(header + lines) + "\n"
        )
        total_rules += len(lines)
        manifest.append((fname, policy, len(lines)))
        report.append("%s  %-14s %6d 条  <- %s" % (fname, policy, len(lines), "; ".join(srcs)))
        for k, v in dropped.items():
            skipped_all[k] = skipped_all.get(k, 0) + v

    # ---------------- policy 段
    pol, notes = build_policies(groups, servers)

    # ---------------- conf
    fr = "\n".join(
        "%s/%s, tag=%02d %s, force-remote-filter=true" % (RAW_BASE, f, i, p)
        for i, (f, p, _n) in enumerate(manifest, 1)
    )
    conf = """# ==========================================================
# QuantumultX 配置 —— gjzbbs/xin 分流规格（ShellCrash_Custom.ini 的 QX 版）
# 由 qx/build_qx.py 生成；规则条数 {total}
#
# 用法：QX → 设置 → 配置文件 → 导入本文件，或把下面各段拷进你自己的配置。
# 规则在 GitHub 上改（改 .list 后重跑 build_qx.py），QX 端「更新全部资源」即生效。
# ==========================================================

[general]
network_check_url=http://www.gstatic.com/generate_204
server_check_url=http://www.gstatic.com/generate_204
# 下面这条可选：这些域名不走代理判断，省电
# dns_exclusion_list=*.qq.com, *.tencent.com, *.wechat.com

[dns]
server=223.5.5.5
server=119.29.29.29

[policy]
{policy}

[server_local]
# 单节点可以直接写这里（QX 语法），例如：
# vless=我的节点, example.com, 443, method=none, password=UUID, obfs=wss, obfs-host=example.com, obfs-uri=/path, tls=true, fast-open=false, udp-relay=false, tag=我的节点

[server_remote]
# 你自己的订阅放这里（一行一个），节点名必须能和上面策略组里的名字对上：
# https://你的订阅地址, tag=自建, enabled=true

[filter_remote]
# 顺序 = 匹配优先级，不要调换文件名序号
{filter_remote}

[filter_local]
# 注意：QX 的本地规则【优先于】上面所有远程规则集。
# 所以 GEOIP,CN 与 FINAL 放在最后一个远程文件里（99 final 段），不要写到这里，
# 否则国内 IP 会抢在所有应用分流之前直接直连。

[rewrite_local]
# 需要改写规则时加在这里（对应 Clash 的 rules / 脚本）

[task_local]
# 定时任务

[mitm]
# hostname = %APPEND% example.com
""".format(total=total_rules, policy="\n".join(pol), filter_remote=fr)
    open(os.path.join(HERE, "QuantumultX.conf"), "w", encoding="utf-8", newline="\n").write(conf)

    # ---------------- report
    rep = [
        "生成时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "规则总数：%d" % total_rules,
        "策略组数：%d（QX policy 行）" % len(pol),
        "远程规则集：%d 个" % len(manifest),
        "丢弃的不支持类型：%s" % (skipped_all or "无"),
        "下载失败的源：%s" % (failed or "无"),
        "",
        "== 规则集 ==",
    ] + report + ["", "== 策略组提示 =="] + (notes or ["无"])
    open(os.path.join(HERE, "build_report.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    sys.exit(main())
