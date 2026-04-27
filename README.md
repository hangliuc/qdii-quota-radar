# 支付宝纳斯达克 QDII 基金限购监控

自动抓取支付宝中纳斯达克相关 QDII 基金的 **限购额度** 和 **近1年收益率**，生成小红书卡片图，通过飞书推送提醒。

每天早上 8:40 定时执行，生成两张卡片：
- **被动型**（指数基金）— 18 只纳斯达克100指数基金
- **主动型**（主动管理）— 18 只全球科技/成长 QDII 基金

数据来源：天天基金网

## 效果

飞书收到提醒 → 点击按钮查看卡片图 → 保存发小红书

卡片内容：基金名称、代码、近1年收益率、当日限购额度，按限额从大到小排序。

## 架构

```
新加坡服务器 (Docker)
├── monitor    cron 每天 8:40 抓取数据 → 生成卡片 → 飞书通知
└── nginx      提供卡片图 HTTP 访问（飞书按钮链接指向这里）

GitHub Actions
└── push to main → SSH 自动部署到服务器
```

## 部署

### 前置条件

服务器上需要安装 `docker`、`docker compose`、`git`。

### 1. GitHub Secrets

在仓库 Settings → Secrets → Actions 中添加：

| Secret | 说明 |
|--------|------|
| `SERVER_HOST` | 服务器 IP |
| `SERVER_USER` | SSH 用户名（如 `root`） |
| `SSH_PRIVATE_KEY` | SSH 私钥 |
| `FEISHU_WEBHOOK` | 飞书机器人 webhook 地址 |

### 2. 部署

Push 到 main 分支会自动部署。首次部署会自动 clone 仓库、创建 `.env`、构建并启动容器。

### 3. 验证

```bash
# SSH 到服务器，手动执行一次
docker exec fund-monitor python main.py

# 查看日志
docker logs fund-monitor
```

## 本地开发

```bash
pip install -r requirements.txt

# 控制台输出（不推飞书）
python main.py --dry-run

# 只查指定基金
python main.py --dry-run --fund-codes 008971 019172
```

## 项目结构

```
main.py                     入口
fund_monitor/
├── cli.py                  流程编排
├── config.py               配置加载
├── scraper.py              天天基金数据抓取
├── history.py              历史记录 & 变动检测
├── image.py                小红书卡片图生成
└── notifier.py             飞书通知
config.json                 基金列表 & 配置
Dockerfile                  容器镜像（Python + cron + 中文字体）
docker-compose.yml          编排（monitor + nginx）
docs/                       生成的卡片图（nginx 托管）
data/                       历史数据
```

## 配置说明

`config.json` 中的字段：

| 字段 | 说明 |
|------|------|
| `passive_funds` | 被动型基金列表（指数基金） |
| `active_funds` | 主动型基金列表 |
| `history_file` | 历史数据文件路径 |

每只基金的 `display` 字段控制卡片上显示的名称。

敏感信息（webhook、服务器地址）通过环境变量注入，不进代码仓库。
