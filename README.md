# xin

在线自定义规格库（ShellCrash / mihomo·clash.meta 用）。

**核心用法：所有改动都在这个 GitHub 网页上做，路由器侧只指向一次，以后不用再动路由器。**

---

## 一、目录说明

| 文件 | 作用 | 你要不要动 |
|---|---|---|
| `ShellClash_Custom.ini` | 规则母版（ruleset + 策略组 + 开关） | 增删分流段落时才动 |
| `custom-proxy.list` | 自维护「强制走代理」域名清单 | **日常主要改这个** |
| `custom-direct.list` | 自维护「强制走直连」域名清单 | **日常主要改这个** |
| `custom-ai.list` | AI 站点清单（走 🤖 人工智能 组） | 想加 AI 站点时动 |
| `meta.list` | Meta 系站点清单（Facebook / Instagram / WhatsApp / Threads，走 📘 Meta 组） | 想加 Meta 系域名时动 |
| `ShellClash_Full_Block.ini` | 旧母版，保留备查 | 不动 |

---

## 二、部署到 ShellCrash（只做一次）

ShellCrash 的规则来源是 `configs/servers.list` 里 `^5` 开头的行，由 `rule_link` 序号选择。

1. 进 ShellCrash 菜单 → `配置文件管理` → `在线生成配置文件`
2. 选 `4 选取在线配置规则模版`
3. 菜单最后一列的 `(推荐)` 之类后缀会被忽略，你要选的是**你自己新增的那一条**：
   先把本文件仓的 ini 地址加进去，方法是编辑路由上的
   `/etc/mnt/plugins/configs/shellcrash/configs/servers.list`，追加一行：

   ```
   520 gjzbbs在线自定义规格 https://raw.githubusercontent.com/gjzbbs/xin/main/ShellClash_Custom.ini
   ```

   > 爱快插件版真身路径以 `/etc/mnt/plugins/configs/shellcrash/configs/servers.list` 为准；
   > `/tmp/iktmp/plugins/shellcrash/bin/configs` 是指向该持久区的软链（inode 相同），两边改都等效，
   > 但重启后软链由 ipk 重建，直接改持久区更稳。

4. 回到菜单 `4 选取在线配置规则模版`，选中 `520`，`rule_link` 会写成 20（序号，不是 520）
5. 返回上级 → `1 在线生成配置文件` → 确认后生成

**关于网络**：这个 ini 是**转换服务器**（`sub.jwsc.eu.org` 等）去下载的，不是路由器下载。
所以路由器本身连不上 GitHub 完全不影响，`raw.githubusercontent.com` 直接写就行。

只有一种情况需要换镜像——你在电脑浏览器里手动拼转换链接自测时。实测可用的三个：

```
https://testingcf.jsdelivr.net/gh/gjzbbs/xin@main/ShellClash_Custom.ini
https://gcore.jsdelivr.net/gh/gjzbbs/xin@main/ShellClash_Custom.ini
https://fastly.jsdelivr.net/gh/gjzbbs/xin@main/ShellClash_Custom.ini
```

ini 里引用的所有 `*.list` 同样由转换服务器下载，路由器不需要能连 GitHub。

---

## 三、日常怎么改（这就是你要的「在线自定义规格」）

直接在 GitHub 网页上编辑、保存、Commit 即可。改完在路由器上执行一次「更新订阅 / 重新生成配置」就生效。

### 加一个「一定走代理」的域名

编辑 `custom-proxy.list`，加一行：

```
DOMAIN-SUFFIX,example.org
```

支持的写法：

```
DOMAIN,www.example.com          精确域名
DOMAIN-SUFFIX,example.com       含所有子域
DOMAIN-KEYWORD,keyword          含关键字的域名
IP-CIDR,1.2.3.0/24              网段
```

### 加一个「一定走直连」的域名

编辑 `custom-direct.list`，写法同上。

### 想让某个域名走特定策略组

改 `ShellClash_Custom.ini`，新增一条 ruleset 指到你自己的清单，例如：

```ini
ruleset=🎥 NETFLIX,https://raw.githubusercontent.com/gjzbbs/xin/main/netflix.list?v=1
```

（`?v=1` 必须有，改内容时递增，原因见第六节。）

`ruleset=` 后面的策略组名必须与 `custom_proxy_group=` 里定义的名字**逐字一致**
（emoji、空格、全角都不能差）。名字对不上时 subconverter 不会报错，
而是**静默把整条 ruleset 连同它的规则全部丢弃**——表现就是「组在、但组内规则数为 0」，
域名全落到别的组（常见是落进 🌍 国外媒体 或 🐟 漏网之鱼）。

**还有一条**：新建策略组时不要和已有组共用同一个 emoji 前缀。
例如已经有了 `🤖 人工智能`，再建 `🤖 Mate` 会被 subconverter 判为同前缀冲突而整组丢弃；
换掉 emoji（这里是 `📘 Meta`）就正常。

### ⚠️ 顺序决定成败

Clash 规则是**从上往下第一条命中即停**。自维护的清单要放在通用清单**之前**，否则抢不过。

具体到本仓库：`meta.list` 那条 ruleset 必须写在 `ACL4SSR/Clash/ProxyLite.list` 之前。
放在后面时，`facebook.com` 会先被 ProxyLite 匹配走（落到 🚀 节点选择），
`📘 Meta` 组永远是 0 条规则——**格式全对也没用，就是位置问题**。

---

## 四、优先级顺序（从上往下，先命中先生效）

```
局域网 / UnBan / custom-direct.list      → 🎯 全球直连
BanAD / BanProgramAD                     → 🛑 广告拦截 / 🍃 应用净化
custom-proxy.list                        → 🚀 节点选择      ← 自维护代理优先
meta.list                                → 📘 Meta          ← 必须早于 ProxyLite
应用分流（Netflix/YouTube/AI/微软/苹果…）  → 各自策略组
ProxyLite / ChinaDomain / GEOIP,CN       → 🚀 节点选择 / 🎯 全球直连
MATCH                                    → 🐟 漏网之鱼
```

所以：**`custom-proxy.list` 的优先级高于所有通用分流**——想强行让某个域名走代理，加进这个文件就行，
不用管它本来被 Netflix 还是 Microsoft 规则抓走。

---

## 五、已实测验证（爱快 192.168.11.1，mihomo v1.19.33）

用真实订阅链路（3 条源）+ 本 ini 请求转换后端，连测 3 次结果完全一致：

```
groups=33  rules=14055
- DOMAIN-SUFFIX,chatgpt.com,🤖 人工智能      ← custom-ai.list 生效（组内 79 条）
- DOMAIN-SUFFIX,claude.ai,🤖 人工智能
- DOMAIN-SUFFIX,gemini.google.com,🤖 人工智能
- DOMAIN-SUFFIX,facebook.com,📘 Meta        ← meta.list 生效（组内 556 条）
- DOMAIN-SUFFIX,instagram.com,📘 Meta
- DOMAIN-SUFFIX,whatsapp.com,📘 Meta
- DOMAIN-SUFFIX,threads.net,📘 Meta
- DOMAIN-SUFFIX,example.com,🎯 全球直连     ← custom-direct.list 生效
- DOMAIN-SUFFIX,example.org,🚀 节点选择     ← custom-proxy.list 生效
- GEOIP,CN,🎯 全球直连                       ← GEOIP 兜底生效
- MATCH,🐟 漏网之鱼                          ← 末尾兜底生效
```

`📘 Meta` 组的候选顺序：`🚀 节点选择 / ♻️ 自动选择 / 🏠 家宽节点 / 🇺🇲 美国节点 / 🇭🇰 香港节点 / 🇸🇬 新加坡节点 / 🚀 手动切换`
—— 想让它默认走住宅线路，在面板里选「🏠 家宽节点」即可（该组是 url-test，只收节点名含 `home` 或 `家宽/住宅` 的节点）。

各策略组实际承载规则数（`grep -oE ',[^,]+$' | sort | uniq -c`）：

```
🍃 应用净化 997    🎯 全球直连 727   🛑 广告拦截 588   📘 Meta 556
🎮 外服游戏 548    🌍 国外媒体 353   🚀 节点选择 347   🤖 人工智能 79
Ⓜ️ 微软服务 79     🎥 NETFLIX 55     Ⓜ️ 苹果服务 19
```

关键点：转换请求**必须带 `insert=true`**，否则后端只返回 proxies、不返回 proxy-groups 和 rules。
ShellCrash 的 `starts/core_config.sh` 里已经硬编码了 `insert=true`，走菜单生成不需要你操心。

---

## 六、⚠️⚠️ 改完 `.list` 必须递增 `?v=`（最容易踩的坑）

**subconverter 会按 `.list` 的文件 URL 缓存文件内容本身**，不是只缓存 ini。

所以：你改了 `custom-proxy.list` 的内容、甚至删光了重写，只要 ini 里那条 ruleset 的
URL 一个字没变，转换服务器拿到的还是**旧版本**——表现就是「我明明加了规则，路由器上一条都没有」。

本仓库的 ini 里，四条自维护清单都已经带上了版本号：

```ini
ruleset=🎯 全球直连,https://raw.githubusercontent.com/gjzbbs/xin/main/custom-direct.list?v=1
ruleset=🚀 节点选择,https://raw.githubusercontent.com/gjzbbs/xin/main/custom-proxy.list?v=1
ruleset=📘 Meta,https://raw.githubusercontent.com/gjzbbs/xin/main/meta.list?v=1
ruleset=🤖 人工智能,https://raw.githubusercontent.com/gjzbbs/xin/main/custom-ai.list?v=1
```

**操作纪律：每次改完任何一个 `.list` 的内容，回到 `ShellClash_Custom.ini` 把对应那行的
`?v=1` 改成 `?v=2`、`?v=3`……（任意新串都行，只要和上次不同），两个文件一起 Commit。**

只改 `.list` 不改 `?v=` = 改动不生效，这是实测确认过的，不是猜测。

> 为什么加 `?v=` 不影响 Clash：转换服务器是先把 `.list` 下载下来、解析成规则再写进最终 YAML，
> 最终配置里只剩 `DOMAIN-SUFFIX,xxx,组名`，查询串不会进 Clash 配置。

---

## 七、改完为什么有时不立刻生效

`sub.jwsc.eu.org` 是**多实例 + 带缓存**的转换后端。连测多次出现过前两次返回旧版本、
第三次才拿到新内容的情况（缓存过期有延迟）。

所以：

1. 改完 GitHub 后等 1–2 分钟再让路由器生成；
2. 一次没生效不算改错，**重试一次**（ShellCrash 菜单 `7 更新配置文件`）；
3. 确认是缓存还是真的写错：连测 3 次，3 次都一样才算定论。

> 自测时不要给 ini 的 config URL 加 `?v=`。某些后端实例会把带 query 的 URL 当成另一个
> 缓存键，结果和路由器实际生成的不一致。要清缓存就清 `.list` 的 `?v=`，别动 ini 的。
