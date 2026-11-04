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
| `ai.list` | AI 站点清单（走 🤖 人工智能 组） | 想加 AI 站点时动 |
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
ruleset=🎥 NETFLIX,https://raw.githubusercontent.com/gjzbbs/xin/main/netflix.list
```

`ruleset=` 后面的策略组名必须是 ini 里已经定义过的（见 `custom_proxy_group=` 段），
否则生成的 YAML 会因为找不到策略组而报错。

---

## 四、优先级顺序（从上往下，先命中先生效）

```
局域网 / UnBan / custom-direct.list      → 🎯 全球直连
BanAD / BanProgramAD                     → 🛑 广告拦截 / 🍃 应用净化
custom-proxy.list                        → 🚀 节点选择      ← 自维护代理优先
应用分流（Netflix/YouTube/AI/微软/苹果…）  → 各自策略组
GEOIP,CN                                 → 🎯 全球直连
MATCH                                    → 🐟 漏网之鱼
```

所以：**`custom-proxy.list` 的优先级高于所有通用分流**——想强行让某个域名走代理，加进这个文件就行，
不用管它本来被 Netflix 还是 Microsoft 规则抓走。

---

## 五、已实测验证（爱快 192.168.11.1，mihomo v1.19.33）

用真实订阅链路 + 本 ini 请求转换后端，实测结果：

```
groups=32  rules=13499
- DOMAIN-SUFFIX,example.com,🎯 全球直连     ← custom-direct.list 生效
- DOMAIN-SUFFIX,example.org,🚀 节点选择     ← custom-proxy.list 生效
- DOMAIN-SUFFIX,facebook.com,📘 Meta        ← meta.list 生效
- GEOIP,CN,🎯 全球直连                       ← GEOIP 兜底生效
- MATCH,🐟 漏网之鱼                          ← 末尾兜底生效
```

关键点：转换请求**必须带 `insert=true`**，否则后端只返回 proxies、不返回 proxy-groups 和 rules。
ShellCrash 的 `starts/core_config.sh` 里已经硬编码了 `insert=true`，走菜单生成不需要你操心。

---

## 六、改完为什么有时不立刻生效

`sub.jwsc.eu.org` 是**多实例 + 带缓存**的转换后端。同一个 config URL 连发三次，
出现过前两次返回旧版本（32 组里的第 16 组还是旧名）、第三次才拿到新内容的情况。

所以：

1. 改完 GitHub 后等 1–2 分钟再让路由器生成；
2. 一次没生效不算改错，**重试一次**（ShellCrash 菜单 `7 更新配置文件`）；
3. 排查时给 config URL 加个查询串强制绕缓存，例如
   `...ShellClash_Custom.ini?v=2`（只影响你手动自测，不影响 ini 内容）。

> 用 `?v=` 自测时注意：某些后端实例会把带 query 的 URL 当成另一个缓存键，
> 所以自测结果和路由器实际结果可能短暂不一致，以路由器生成为准。
