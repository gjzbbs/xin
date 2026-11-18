# QuantumultX 版分流（由 ShellClash_Custom.ini 生成）

这套东西把本仓库在 Clash / ShellCrash 上用的分流规格，原样搬到 iOS **QuantumultX**。
规则**唯一真源仍是仓库根目录的 `ShellClash_Custom.ini` + 各 `.list`**，改动只需在 GitHub 上做（或改 `.list` 后 push），QX 端「更新全部资源」即生效。

- 共 **5133 条规则 / 33 个策略组 / 25 个远程规则集**
- `📘 Meta` 组（Facebook / Instagram / WhatsApp / Threads，含 **muse.ai**）原样保留，候选：🚀 节点选择、♻️ 自动选择、🏠 家宽节点、🇯🇵 日本节点、🇺🇲 美国节点、🇭🇰 香港节点、🇸🇬 新加坡节点、🚀 手动切换
- 规则顺序与 Clash 一致：`📘 Meta` 段在 ACL4SSR ProxyLite 之前，所以 facebook 不会被 ProxyLite 抢走

---

## 一、怎么用

### 0. 只加一条「分流资源」（QX 设置 → 资源 → 分流）

```
https://raw.githubusercontent.com/gjzbbs/xin/main/qx/QX-all.list
```

5133 条规则全在这一个文件里，**文件内顺序就是匹配优先级**（等于 ini 里 `ruleset=` 的先后），等价于下面 25 个分文件。tag 随便写（如 `xin`）。

唯一的前提：你 QX 配置的 `[policy]` 段里要有同名策略组，否则规则里的 `📘 Meta` / `🚀 节点选择` 这些名字解析不到，规则会被忽略。
把 [QX-policy.txt](QX-policy.txt) 整段拷进配置文件的 `[policy]` 位置即可（33 行，只含组不含量节点，节点仍来自你的订阅）。

**别**再把 `GEOIP,CN` / `FINAL` 塞进 `[filter_local]` —— 这个文件末尾自带，QX 本地规则优先于远程资源，放本地会抢在所有分流之前。

如果你 QX 里已经有一套自己的组（名字不叫 `📘 Meta` 这些），不想动配置，就统一压成一个组名重新生成：

```bash
python qx/build_qx.py --force-policy "你现有的组名"
# 生成的 QX-all.list 里每条规则的策略都换成那个组名，policy 段可删
```

### 0b. 想分批更新 / 排错：用 25 个分文件

按下表顺序逐个加到 QX 的「资源 → 分流」（**顺序不能乱，它就是优先级**）：见文末清单，地址前缀是
`https://raw.githubusercontent.com/gjzbbs/xin/main/qx/filter/`。

### 0c. 直接导入整份配置（不想手动拼）



### 附：整份配置导入

```
https://raw.githubusercontent.com/gjzbbs/xin/main/qx/QuantumultX.conf
```

QX → 设置 → 配置文件 → 点右上角「+」→ 填上面地址 → 下载 → 切到该配置。
然后把 `[server_remote]` 换成你自己的订阅（见第二节）。

> 导入会**覆盖**当前配置。已有自己的配置就先用方式 B。

### 附：只拷两段进现有配置

只需把这两段拷进你的 QX 配置文件：

1. `[policy]` —— 整个段一起拷（33 行）
2. `[filter_remote]` —— 整个段一起拷（25 行，顺序不要变）

`[filter_local]` **不要**放 `GEOIP,CN` 和 `FINAL`（原因见第四节）。

---

## 二、节点名必须对上

QX 的策略组里只能写**节点名**或**其它组名**，不支持正则（Clash 的 `(港|HK)` 那种）。所以地区组是脚本按 `qx/servers.txt` 在本地算好写死的：

```
qx/servers.txt   ← 一行一个节点名
```

- 换成别的机场 / 改了节点名之后：改 `servers.txt` → 重跑 `python qx/build_qx.py` → push
- 名字对不上时，该组会退化成只有一个 `🚀 手动切换`（不会报错，但自动选国就没意义了）

订阅本身写在 QX 的 `[server_remote]`：

```
[server_remote]
https://你的订阅地址, tag=自建, enabled=true
```

（本仓库里这份配置只放占位，不写真实订阅地址。）

---

## 三、改规则 → 生效

```bash
# 1) 改 ShellClash_Custom.ini 或任意 .list（GitHub 网页上改也行）
# 2) 重新生成
python qx/build_qx.py
# 3) 自检（应为 0 错误）
python qx/validate_qx.py
# 4) push
git add qx && git commit -m "qx: 重建 QuantumultX 规则" && git push
```

QX 里：**设置 → 资源 → 规则 → 全部更新**（或下拉刷新主界面）。
推送后如果 QX 拿到的还是旧规则，是 `raw.githubusercontent.com` 的分支缓存——重跑（`06` 之后的文件名不变时内容会变）或者把 QX 的资源地址加 `?v=N` 破缓存。

---

## 四、QX 与 Clash 不一样的地方（都已在脚本里处理，但要知道）

| 差异 | Clash | QuantumultX | 本仓库的处理 |
|---|---|---|---|
| 组内筛节点 | 支持正则 | **只认节点名/组名** | 脚本离线跑正则，把结果写成节点名 |
| 组内测速地址 | 每组可指定 | 只有全局 `server_check_url` | 组级 URL 丢弃，统一用 global |
| 规则自带策略 | `payload:` 里纯规则 | 每行必须 `TYPE,VALUE,POLICY` | 转换时统一拼上策略名 |
| 本地规则优先级 | — | **`[filter_local]` 优先于所有远程规则集** | `GEOIP,CN`、`FINAL` 放在最后一个远程文件里，绝不放本地 |
| 顺序 | rule-providers 按 rules 顺序 | `[filter_remote]` 按配置里的顺序 | 生成 25 个文件，文件名前缀 `01`~`25` 就是匹配优先级 |
| 规则集格式 | yaml payload | 纯文本 | 生成 `qx/filter/*.list` |

另外：

- **`ChinaIp.list` / `ChinaIpV6.list` 默认不导入**（7460+ 条 IP-CIDR，iOS 上会很慢），改用 `GEOIP,CN` 兜底。要全量加 `--with-china-domain`。
- 额外加了一条 `DOMAIN-SUFFIX,cn → 🎯 全球直连`（`.cn` 域名不用等 DNS 解析出国内 IP，直接直连）。不想要就加 `--no-cn-suffix`。
- 订阅里没有香港 / 台湾节点，`🇭🇰 香港节点`、`🇨🇳 台湾节点`、`👍 高级节点`、`📺 省流节点`、`🎮 游戏节点`、`🎥 流媒体解锁` 这 6 组在 QX 里成员是 `🚀 手动切换`（兜底），有对应节点后重跑即可恢复。

---

## 五、文件清单

| 文件 | 作用 |
|---|---|
| `qx/build_qx.py` | 转换器：ini + .list → QX 配置与规则集 |
| `qx/validate_qx.py` | 产物自检：策略名已定义 / 字段数 / GEOIP 与 FINAL 位置 / 组引用环 |
| `qx/servers.txt` | 节点名清单，地区组按它筛 |
| `qx/QuantumultX.conf` | 生成的完整配置（订阅为占位） |
| `qx/filter/01-…25-*.list` | 生成的 QX 规则集，序号 = 优先级 |
| `qx/build_report.txt` | 本次构建统计（条数、来源、兜底提示） |

生成的规则集：

```
01-direct  🎯 全球直连     70     LAN / 未批处理域名 / custom-direct
02-adblock 🛑 广告拦截    588     BanAD
03-appclean 🍃 应用净化  1010     BanProgramAD
04-proxy   🚀 节点选择      1     custom-proxy（占位，排在 Meta 之前）
05-meta    📘 Meta        556     Meta 系（含 muse.ai）
06-auto    ♻️ 自动选择      5     custom-auto
07-saver   📺 省流节点      1     custom-saver
08-fcm     📢 谷歌FCM      44     GoogleFCM
09-direct2 🎯 全球直连     29     GoogleCN
10-netflix 🎥 NETFLIX     499     ACL4SSR + LM-Firefly
11-disney  🎥 DisneyP      20
12-youtube 🎥 YouTube      14
13-bili    📺 哔哩海外     21     BilibiliHMT（港澳台）
14-ai      🤖 人工智能    104     custom-ai
15-ms      Ⓜ️ 微软服务     79
16-apple   🍎 苹果服务     29
17-tg      📲 电报         13
18-game    🎮 外服游戏    547     LM-Firefly Game
19-bahamut 📺 巴哈姆特      5
20-pmedia  🌍 国外媒体    354     ProxyMedia
21-cmedia  🌏 国内媒体     38     ChinaMedia
22-netease 🎶 网易音乐     37
23-proxy2  🚀 节点选择    421     ACL4SSR ProxyLite
24-direct3 🎯 全球直连    726+    ChinaDomain + Download + DOMAIN-SUFFIX,cn + GEOIP,CN
25-final   🐟 漏网之鱼      1     FINAL
```

---

## 六、验证

```bash
python qx/validate_qx.py
# 规则集 25 个，规则 5133 条，策略组 33 个
# 未定义策略 0 条，格式错误 0 条，组结构错误 0 条，提示 0 条
```

QX 里验证分流：打开日志（QX 主界面 → 底部「日志」）看某条连接命中的规则集 tag，例如访问 `muse.ai` 应命中 `05 📘 Meta`。

---

## 七、按「少年歌行PRO」小白配置的组名重新映射

`qx/build_qx_sngxpro.py` 把同一套规则改写成那套配置的组名（`Bing` / `延迟最低` / `全球加速` / `黑白名单` / `网飞影视` / `国际媒体` / `港台番剧` / `电报代理` / `IPLC` / `苹果服务` / 地区组），**目标配置的 `[policy]` 不用改一个字**。

```bash
python qx/build_qx_sngxpro.py                     # 📘 Meta 落到「全球加速」
python qx/build_qx_sngxpro.py --meta-group Meta   # 你若新加了 Meta 组，落到它
```

产物：

| 文件 | 条数 | 用法 |
|---|---|---|
| `qx/QX-sngxpro-meta.list` | 556 | 只要 muse / Meta 那套。加资源后**拖到「本地规则」上面一行**，配置文件不用改 |
| `qx/QX-sngxpro-all.list` | 5133 | 整套分流，末尾自带 `geoip, cn, direct` 与 `final, 黑白名单`；用这个要**删掉** `[filter_local]` 里对应的两条 |

映射关系（本仓库 33 组 → 那套配置的组）：

```
🎯 全球直连 → direct            🛑 广告拦截 / 🍃 应用净化 → reject
🚀 节点选择 → 全球加速           📘 Meta → 全球加速（或 --meta-group 指定）
♻️ 自动选择 / 📺 省流节点 → 延迟最低   📢 谷歌FCM / 🤖 人工智能 → 全球加速
🎥 NETFLIX / 🎥 DisneyP → 网飞影视     🎥 YouTube / 🌍 国外媒体 → 国际媒体
📺 哔哩海外 / 📺 巴哈姆特 → 港台番剧   Ⓜ️ 微软服务 → Bing
🍎 苹果服务 → 苹果服务           📲 电报消息 → 电报代理
🎮 外服游戏 → IPLC              🌏 国内媒体 / 🎶 网易音乐 → direct
🐟 漏网之鱼 → 黑白名单
```

**为什么必须拖顺序 / 删本地两条**：QX 的匹配顺序是 `[filter_local] > [filter_remote] > final`。那套配置的 `[filter_local]` 末尾有 `geoip, cn, direct` 和 `final, 黑白名单`，`final` 会把远程资源全部截断，除非把远程资源排到本地规则之前（QX 1.0.30+ 支持调整加载顺序），或者把这两条挪进远程资源末尾。
