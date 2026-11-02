# ArknightsPRTS

GsCore 的明日方舟资料查询 **AI 工具插件**：让机器人通过 [PRTS.wiki](https://prts.wiki) 查询干员、敌人和公开招募数据。

> 这个插件没有用户命令，也不绑定游戏账号。它只注册 AI 工具；开启 GsCore AI Core 后，用户直接用自然语言提问即可。

## 功能

- **干员详情**：技能、天赋、属性、精英化材料、模组、档案、语音、稀有度、职业、分支等。
- **敌人详情**：属性、等级、种族、攻击方式、伤害类型、技能等。
- **干员筛选**：按关键词、职业、分支、稀有度、位置、性别、标签、势力、出身地、种族等多维筛选。
- **敌人筛选**：按关键词、级别、种族等筛选。
- **公开招募计算**：根据词条计算可能出现的干员，或推荐能出高星的最佳词条组合。
- **AI 知识库注册**：把「机器人具备明日方舟查询能力」注册进 AI 认知库，方便模型在用户提问时召回。

## 环境要求

- Python >= 3.11
- GsCore 上游 `0.11.x`（主目标），或 `AthenaHibou/gsuid_core` 的 `main`（基于 `0.10.7` + 定制补丁）
- **必须开启 GsCore AI Core 并配置可用模型**，否则插件不会产生任何用户可见效果
- 需要能访问 `https://prts.wiki`

依赖：`httpx`、`beautifulsoup4`、`lxml`。

## 安装

### 方式一：core 安装插件（收录到插件列表后）

```text
安装插件ArknightsPRTS
```

### 方式二：手动 clone

```bash
cd gsuid_core/gsuid_core/plugins
git clone https://github.com/AthenaHibou/ArknightsPRTS
```

然后重启 Core。

## 使用

不需要记命令，直接对机器人说：

- 「银灰的数据」
- 「查一下阿米娅（医疗）」
- 「医疗干员有哪些」
- 「六星近卫推荐」
- 「这个公招词条能出什么：资深干员, 术师, 群攻」
- 「公招怎么选词条能出高星」

AI 会调用以下工具：

| 工具 | 说明 |
|---|---|
| `ak_operator_info(name, sections="")` | 单个干员详情；`sections` 可限定章节，如 `天赋,技能` |
| `ak_enemy_info(name, sections="")` | 单个敌人详情 |
| `ak_operator_search(...)` | 干员多维筛选 / 模糊搜索 |
| `ak_enemy_search(...)` | 敌人多维筛选 / 模糊搜索 |
| `ak_recruit(terms, mode="normal")` | 公招计算；`mode="suggest"` 返回推荐组合 |

## 配置

在 Web 控制台「插件配置」中修改：

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `enable` | `true` | 插件总开关 |
| `enable_operator` | `true` | 干员详情 / 干员筛选 |
| `enable_enemy` | `true` | 敌人详情 / 敌人筛选 |
| `enable_recruit` | `true` | 公开招募计算 |
| `default_limit` | `30` | 列表类查询默认返回条数上限（最大 200） |

## 数据源与致谢

- 数据来自 [PRTS.wiki](https://prts.wiki)，本项目与 PRTS.wiki、鹰角网络均无隶属关系。
- 抓取与解析逻辑移植自 [Doctah-MCP](https://github.com/TonybotNi/Doctah-MCP)（MIT License，Copyright (c) 2024 Mudrobot）。原项目的版权声明与许可文本保留在本仓库的 [LICENSE](LICENSE) 和 [NOTICE](NOTICE) 中。
- 请遵守 PRTS.wiki 的使用条款，不要高频抓取；本插件已使用进程内共享的 HTTP 客户端和较长的超时。

## 兼容性

- **主目标**：上游 `Genshin-bots/gsuid_core` 的 `master`，当前为 `0.11.2`。
- **Fork 目标**：`AthenaHibou/gsuid_core` 的 `main`，基于 `0.10.7` + 定制补丁；AI Core 行为可能与上游不同。
- 代码按上游 `0.11.2` 的 API 编写；导入与关键符号已做过静态对照，实际运行仍取决于 AI Core 配置和模型状态。
- 使用了 `ai_tools` 的 `covers` / `aliases` / `context_tags` 元数据；旧核心缺少这些参数时可能不影响加载，但 AI 召回效果会下降。
- 纯 AI 工具插件：AI Core 关闭时不会注册工具，也不会产生用户可见功能。

## License

MIT License。见 [LICENSE](LICENSE)；第三方来源说明见 [NOTICE](NOTICE)。
