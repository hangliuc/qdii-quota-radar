# 支付宝纳斯达克 QDII 基金限购监控

自动抓取纳斯达克相关 QDII 基金的**限购额度**和**近1年收益率**，生成小红书卡片图，通过飞书推送提醒。

## 功能

- 每天早上定时执行（cron 7:16 UTC+8），生成两张卡片图：
  - **被动型**（指数基金）— 18 只纳斯达克100指数基金
  - **主动型**（主动管理）— 19 只全球科技/成长 QDII 基金
- 卡片内容：基金名称、代码、近1年收益率、当日限购额度，按限额从大到小排序
- 限购额度变化自动检测，飞书推送时附带可复制的小红书文案
- 历史数据保留最近 30 天

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
main.py                     入口
fund_monitor/
├── cli.py                  命令行参数解析 & 流程编排
├── config.py               配置加载（支持环境变量覆盖）
├── scraper.py              天天基金网数据抓取（限购状态 + 近1年收益率）
├── history.py              历史记录 & 额度变动检测（JSON 存储，保留30天）
├── image.py                小红书卡片图生成（Pillow，1080px 宽）
└── notifier.py             飞书 Webhook 卡片消息推送
config.json                 基金列表 & 配置
fonts/                      字体文件（STHeiti Medium，确保跨平台渲染一致）
Dockerfile                  容器镜像（Python 3.11 + cron + 中文字体）
docker-compose.yml          服务编排（monitor + nginx）
data/                       历史数据（volume 挂载，不进 git）
docs/                       生成的卡片图（nginx 托管，不进 git）
```

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

```bash
# SSH 到服务器，手动执行一次
docker compose run --rm monitor python main.py

# 查看定时任务日志
docker logs fund-monitor
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
| `image_base_url` | 图片访问基础 URL（建议通过环境变量 `IMAGE_BASE_URL` 注入） |

每只基金的 `display` 字段控制卡片上显示的简称。

## 更新日志

见 [CHANGELOG.md](CHANGELOG.md)
