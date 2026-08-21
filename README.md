# 支付宝纳斯达克 QDII 基金限购监控

自动抓取纳斯达克相关 QDII 基金的**限购额度**和**近1年收益率**，生成小红书卡片图，通过飞书推送提醒。

## 功能

- 每天早上定时执行（cron 7:16 UTC+8），生成两张卡片图：
  - **被动型**（指数基金）— 18 只纳斯达克100指数基金
  - **主动型**（主动管理）— 19 只全球科技/成长 QDII 基金
- 卡片内容：基金名称、代码、近1年收益率、当日限购额度，按限额从大到小排序
- 限购额度变化自动检测，飞书推送时附带可复制的小红书文案
- 历史数据保留最近 30 天
- **节假日/周末自动跳过**（基于 `chinese_calendar`，含调休判断）
- **多源高可用**：主源 JSON 接口 + 备源 HTML 解析 + 历史快照兜底 + 主备交叉验证（详见下文"数据源架构"）

数据来源：[天天基金网](https://fund.eastmoney.com/)

## 工作流程

```
飞书收到提醒 → 点击按钮查看卡片图 → 保存到手机发小红书
```

## 架构

```
服务器 (Docker Compose)
├── monitor    cron 定时抓取数据 → 生成卡片 → 飞书通知
└── nginx      提供卡片图 HTTP 访问（飞书按钮链接指向这里）

GitHub Actions
└── push to main → SSH 自动部署到服务器
```

## 项目结构

```
main.py                            入口
fund_monitor/
├── cli.py                         命令行参数解析 & 流程编排（含数据源健康打印）
├── config.py                      配置加载（支持环境变量覆盖）
├── trading_day.py                 交易日判断（周末 + 中国法定节假日 + 调休）
│
├── fetch/                         【数据抓取层】
│   ├── __init__.py                对外暴露 fetch_all
│   ├── aggregator.py              多源编排 + 历史兜底 + 交叉验证（核心策略）
│   └── sources/
│       ├── base.py                统一记录格式 SourceRecord + 限额格式化工具
│       ├── eastmoney_jjjz.py      限购主源：JSON 接口 Fund_JJJZ_Data.aspx
│       ├── eastmoney_ranking.py   业绩主源：JSON 接口 rankhandler.aspx（近1年收益率）
│       └── eastmoney_html.py      备源：HTML 详情页（JJJZ/RANKING 失败时启用）
│
├── storage/                       【存储层】
│   └── history.py                 历史记录 & 额度变动检测（JSON 存储，保留30天）
│
└── output/                        【输出层】
    ├── image.py                   小红书卡片图生成（Pillow，1080px 宽）
    └── notifier.py                飞书 Webhook 卡片消息推送

config.json                        基金列表 & 配置
fonts/                             字体文件（STHeiti Medium，确保跨平台渲染一致）
Dockerfile                         容器镜像（Python 3.11 + cron + 中文字体）
docker-compose.yml                 服务编排（monitor + nginx）
data/                              历史数据（volume 挂载，不进 git）
docs/                              生成的卡片图（nginx 托管，不进 git）
```

## 数据源架构

为了规避"前端改版导致单点失效"的风险，抓取层采用"双 JSON 主源 + HTML 备源 + 历史兜底"的策略：

```
┌──────────────────────────────────────────────────────────────────┐
│  aggregator.aggregate(funds, history_latest)                     │
│                                                                   │
│  ┌──────────────┐ ┌──────────────┐  ← 两个 JSON 主源并行              │
│  │ JJJZ         │ │ RANKING      │     一次拉全市场快照                │
│  │ 限购 + 净值  │ │ 近1年收益率  │     正常路径只用这两个请求         │
│  └──────┬───────┘ └──────┬───────┘                                 │
│         │                │                                         │
│         └────┬───────────┘                                         │
│              ▼                                                     │
│        ┌─────────────┐                                             │
│        │ HTML 详情页  │  ← 任一主源失败 / 个别基金缺漏时启用        │
│        │ 限购 + 收益 │     单只一次请求，速度慢但字段全              │
│        └──────┬──────┘                                             │
│               ▼                                                    │
│        ┌─────────────┐                                             │
│        │ history.json │  ← 主备都失败的最后兜底                     │
│        │ 上次成功值   │     飞书消息附 ⚠️ 数据陈旧提示              │
│        └─────────────┘                                             │
│                                                                   │
│  ▶ JJJZ 与 HTML 同时成功时：比对申购状态/限额，不一致打 warning   │
│  ▶ 全部失败且无历史 → source=none，错误透传到飞书                 │
└──────────────────────────────────────────────────────────────────┘
```

**JJJZ 主源** `Fund_JJJZ_Data.aspx`：
- 一次拉全市场约 2.6 万只基金的"申购状态 + 日累计限定金额 + 最新净值"
- JSON 风格结构（带 `var reData=` 包裹），不依赖 HTML class

**RANKING 主源** `rankhandler.aspx`：
- 一次拉全市场约 2.4 万只开放式基金的"近1年/3年/5年/今年 等阶段收益率"
- 关键参数 `dx=0`（默认 1 会过滤暂停申购的基金，导致漏数据）

**HTML 备源** 详情页：
- 仅当 JJJZ 整体失败、RANKING 整体失败、或个别基金在快照中缺漏时启用
- 单只一次请求，慢但字段全，是双主源的最后一道补救

**历史兜底**：
- 上述全部失败时，从 `history.json` 当前 namespace 的 `latest` 中取上次值
- 飞书消息追加 ⚠️ 数据陈旧提示，避免推送出"未知/未知"

**交叉验证**：
- HTML 因被启用而与 JJJZ 同时成功时（比如个别基金缺漏），比对申购状态与限额
- 状态属"暂停/开放"时跳过限额比对（限额此时无意义，避免噪音）

每条结果会带上元字段：

| 字段 | 含义 |
|------|------|
| `source` | `jjjz` / `html` / `stale` / `none`（限购数据来源） |
| `confidence` | `high` / `medium` / `low` |
| `warnings` | 不一致或异常的诊断列表 |

正常路径下 37 只基金抓取**只有 2 个 HTTP 请求**（两次全市场 JSON）；只有降级路径才会触发 HTML 单只抓取。

CLI 每次运行末尾会打印数据源健康面板；如果有 stale/none/warnings，飞书消息也会附"数据源健康提醒"区块。

## 部署

### 前置条件

服务器上需要安装 `docker` 和 `docker compose`。

### GitHub Secrets

在仓库 Settings → Secrets → Actions 中添加：

| Secret | 说明 |
|--------|------|
| `SERVER_HOST` | 服务器 IP |
| `SERVER_USER` | SSH 用户名 |
| `SSH_PRIVATE_KEY` | SSH 私钥 |
| `FEISHU_WEBHOOK` | 飞书机器人 Webhook 地址 |

### 自动部署

Push 到 `main` 分支会通过 GitHub Actions 自动部署。首次部署会自动 clone 仓库、创建 `.env`、构建并启动容器。

### 手动验证

不想等次日 cron 时，可以在 GitHub Actions 里手动触发 **Manual Run (on server)** 工作流，它会 SSH 到服务器执行一次真实运行，带两个开关：

| 输入 | 默认 | 说明 |
|------|------|------|
| `dry_run` | false | 勾选则只在控制台输出，不推送飞书 |
| `no_history` | true | 默认不写入 `history.json`，避免测试污染历史数据 |

也可以直接在服务器上执行：

```bash
cd /root/qdii-quota-radar

# 手动执行一次（--force 忽略节假日检查）
docker compose run --rm monitor python main.py --force

# 查看定时任务日志
docker logs qdii-quota-radar
```

## 本地开发

```bash
pip install -r requirements.txt

# 控制台输出（不推飞书）
python main.py --dry-run

# 只查指定基金
python main.py --dry-run --fund-codes 008971 019173

# 不生成图片，只看数据
python main.py --dry-run --no-image

# 不记录历史（避免污染 history.json）
python main.py --dry-run --no-history
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--dry-run` | 不推送飞书（控制台打印） |
| `--no-image` | 不生成卡片图 |
| `--no-notify` | 不发送任何通知 |
| `--no-history` | 不记录历史数据 |
| `--force` | 强制运行（忽略节假日/周末检查） |
| `--fund-codes` | 只查询指定基金代码 |
| `--config` | 指定配置文件路径（默认 config.json） |

## 配置说明

`config.json` 字段：

| 字段 | 说明 |
|------|------|
| `passive_funds` | 被动型基金列表（指数基金） |
| `active_funds` | 主动型基金列表（主动管理 QDII） |
| `history_file` | 历史数据文件路径 |
| `feishu_webhook` | 飞书 Webhook（建议通过环境变量 `FEISHU_WEBHOOK` 注入） |
| `feishu_webhooks` | 额外的飞书 Webhook 列表（与 `feishu_webhook` 合并去重，支持同时推送多个机器人/群） |
| `image_base_url` | 图片访问基础 URL（建议通过环境变量 `IMAGE_BASE_URL` 注入） |

每只基金的 `display` 字段控制卡片上显示的简称。

## 更新日志

见 [CHANGELOG.md](CHANGELOG.md)
