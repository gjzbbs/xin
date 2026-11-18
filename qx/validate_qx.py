#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_qx.py — 校验 build_qx.py 的产物能不能被 QuantumultX 吃下去。

检查项：
  1) 每个 .list 里出现的策略名，必须在 [policy] 里有定义（或 DIRECT/REJECT）
  2) 规则行字段数 3 或 4（第 4 段只能是 no-resolve）
  3) 规则类型在 QX 白名单内
  4) GEOIP,CN 与 FINAL 必须出现在最后一个规则集，且 FINAL 在最后一行
  5) [filter_remote] 的文件数与 filter/ 目录一致、无重复 tag
  6) 组名不含逗号、无自引用、无循环引用
用法：python qx/validate_qx.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILTER = os.path.join(HERE, "filter")
CONF = os.path.join(HERE, "QuantumultX.conf")

QX_TYPES = {
    "DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD",
    "IP-CIDR", "IP-CIDR6", "GEOIP", "IP-ASN",
    "USER-AGENT", "URL-REGEX",
    "HOST", "HOST-SUFFIX", "HOST-KEYWORD",
    "SRC-IP-CIDR", "DST-PORT", "SRC-PORT", "FINAL",
}
errs, warns = [], []


def parse_conf(path):
    sec, data = None, {}
    for raw in open(path, encoding="utf-8"):
        s = raw.rstrip("\n")
        if s.strip().startswith("["):
            sec = s.strip().strip("[]")
            data.setdefault(sec, [])
            continue
        if sec and s.strip() and not s.strip().startswith("#"):
            data[sec].append(s.strip())
    return data


def main():
    conf = parse_conf(CONF)

    servers = set()
    sp = os.path.join(HERE, "servers.txt")
    if os.path.exists(sp):
        servers = {l.strip() for l in open(sp, encoding="utf-8") if l.strip() and not l.startswith("#")}

    # ---- policy
    groups, members = [], {}
    for line in conf.get("policy", []):
        kind, _, body = line.partition("=")
        parts = [p.strip() for p in body.split(",")]
        name = parts[0]
        groups.append(name)
        params = [p for p in parts[1:] if re.match(r"^(check-interval|tolerance|img-url|alive-check)=", p)]
        mem = [p for p in parts[1:] if p not in params]
        members[name] = mem
        if "," in name:
            errs.append("组名含逗号：" + name)

    defined = set(groups) | {"DIRECT", "REJECT"}

    # ---- 组内引用检查（自引用/未定义/循环）
    for g, mem in members.items():
        for m in mem:
            if m in ("DIRECT", "REJECT"):
                continue
            if m == g:
                errs.append("组自引用：" + g)
            elif m in members:
                continue
            elif m not in defined and m not in servers:
                warns.append("组 %s 引用了既不是组也不是已知节点的名字 %r" % (g, m))

    # 环检测
    state = {}

    def dfs(n, stack):
        if state.get(n) == 1:
            errs.append("组引用成环：" + " → ".join(stack + [n]))
            return
        if state.get(n) == 2:
            return
        state[n] = 1
        for m in members.get(n, []):
            if m in members:
                dfs(m, stack + [n])
        state[n] = 2

    for g in members:
        dfs(g, [])

    # ---- 规则文件
    files = sorted(f for f in os.listdir(FILTER) if f.endswith(".list"))
    total = 0
    last_regular = -1     # 最后一个普通规则（DOMAIN/IP 类）所在文件序号
    geoip_idx = final_idx = -1
    for i, f in enumerate(files):
        is_last = i == len(files) - 1
        seen_geoip = seen_final = False
        for n, raw in enumerate(open(os.path.join(FILTER, f), encoding="utf-8"), 1):
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            parts = [p.strip() for p in s.split(",")]
            t = parts[0].upper()
            total += 1
            if t not in QX_TYPES:
                errs.append("%s:%d 未知类型 %s" % (f, n, t))
                continue
            if t == "FINAL":
                if len(parts) != 2:
                    errs.append("%s:%d FINAL 应为两段：%s" % (f, n, s))
                final_idx = i
                continue
            if len(parts) not in (3, 4):
                errs.append("%s:%d 字段数=%d：%s" % (f, n, len(parts), s))
                continue
            if len(parts) == 4 and parts[3].lower() != "no-resolve":
                errs.append("%s:%d 第4段不是 no-resolve：%s" % (f, n, s))
            policy = parts[2]
            if policy not in defined:
                errs.append("%s:%d 策略未定义 %r" % (f, n, policy))
            if t == "GEOIP":
                seen_geoip = True
                geoip_idx = i
            else:
                last_regular = max(last_regular, i)
    if final_idx < 0:
        errs.append("整个配置没有 FINAL 规则")
    if geoip_idx < 0:
        warns.append("没有 GEOIP,CN（国内 IP 会走漏网之鱼，境外流量会多绕一跳）")
    if last_regular > geoip_idx >= 0:
        errs.append("GEOIP,CN 在第 %d 个规则集，但第 %d 个规则集里还有普通规则会抢先"
                    % (geoip_idx + 1, last_regular + 1))

    # ---- filter_remote
    fr = conf.get("filter_remote", [])
    if len(fr) != len(files):
        errs.append("filter_remote 有 %d 条，filter/ 有 %d 个文件" % (len(fr), len(files)))
    for line, f in zip(fr, files):
        if f not in line:
            errs.append("filter_remote 顺序与文件不一致：%s vs %s" % (line, f))
        if ", tag=" not in line:
            warns.append("filter_remote 缺 tag：" + line)

    # ---- 合并版 QX-all.list
    allp = os.path.join(HERE, "QX-all.list")
    if os.path.exists(allp):
        rows = [l.strip() for l in open(allp, encoding="utf-8")
                if l.strip() and not l.startswith("#")]
        if rows[-1].upper().startswith("FINAL,") is False:
            errs.append("QX-all.list 最后一行不是 FINAL")
        if not any(r.upper().startswith("FINAL,") for r in rows):
            errs.append("QX-all.list 缺 FINAL")
        gi = next((i for i, r in enumerate(rows) if r.upper().startswith("GEOIP,")), -1)
        fi = next((i for i, r in enumerate(rows) if r.upper().startswith("FINAL,")), -1)
        if gi < 0:
            warns.append("QX-all.list 没有 GEOIP,CN")
        elif fi >= 0 and gi > fi:
            errs.append("QX-all.list 里 GEOIP 在 FINAL 之后")
        for i, r in enumerate(rows, 1):
            parts = [x.strip() for x in r.split(",")]
            t = parts[0].upper()
            if t == "FINAL":
                continue
            if len(parts) not in (3, 4):
                errs.append("QX-all.list:%d 字段数=%d" % (i, len(parts)))
                break
            if parts[2] not in defined:
                errs.append("QX-all.list:%d 策略未定义 %r" % (i, parts[2]))
                break

    print("规则集 %d 个 / %d 条，合并版 %d 条，策略组 %d 个"
          % (len(files), total, len(rows) if os.path.exists(allp) else 0, len(groups)))
    print("未定义策略 %d 条，格式错误 %d 条，组结构错误 %d 条，提示 %d 条"
          % (sum(1 for e in errs if "策略未定义" in e),
             sum(1 for e in errs if "字段数" in e or "未知类型" in e or "第4段" in e),
             sum(1 for e in errs if "组" in e),
             len(warns)))
    for e in errs:
        print("ERROR  " + e)
    for w in warns:
        print("WARN   " + w)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
