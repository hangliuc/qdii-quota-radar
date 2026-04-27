# 支付宝纳斯达克 QDII 基金监控

每天自动抓取支付宝中纳斯达克相关 QDII 基金的**限购额度、近1年收益率**，生成小红书卡片图，推送到飞书。

## 架构

```
服务器 (Docker)
├── monitor 容器：cron 每天 8:40 执行抓取 + 生图 + 飞书通知
└── nginx 容器：提供图片 HTTP 访问（飞书按钮链接）

GitHub Actions
└── push to main → 自动 SSH 部署到服务器
```

## 部署

### 1. 配置 GitHub Secrets

| Secret | 说明 |
|--------|------|
| `SERVER_HOST` | 服务器 IP |
| `SERVER_USER` | SSH 用户名 |
| `SSH_PRIVATE_KEY` | SSH 私钥 |

### 2. 服务器环境变量

在服务器 `/root/alipay-nasdaq-fund-monitor/` 下创建 `.env`：

```bash
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
IMAGE_BASE_URL=http://你的服务器IP:8900
```

### 3. 首次部署

push 代码到 main 分支会自动部署。也可以手动：

```bash
ssh root@你的服务器
cd /root/alipay-nasdaq-fund-monitor
docker compose up -d
```

### 4. 手动测试

```bash
# 在服务器上
docker exec fund-monitor python main.py --dry-run
```

## 本地开发

```bash
pip install -r requirements.txt
python main.py --dry-run
```

## 项目结构

```
main.py                     入口
fund_monitor/
  ├── cli.py                流程编排
  ├── config.py             配置加载
  ├── scraper.py            天天基金数据抓取
  ├── history.py            历史记录 & 变动检测
  ├── image.py              小红书卡片图生成
  └── notifier.py           飞书通知
config.json                 基金列表 & 配置
Dockerfile                  容器镜像
docker-compose.yml          编排（monitor + nginx）
docs/                       生成的卡片图（nginx 托管）
data/                       历史数据
```
