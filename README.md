# 支付宝纳斯达克 QDII 基金监控

每天自动抓取支付宝中纳斯达克相关 QDII 基金（被动型 & 主动型）的**限购额度、近1年收益率**等信息，生成小红书卡片图，推送到飞书。

数据源：天天基金网（东方财富）

## 监控范围

覆盖 18 家基金公司的纳斯达克 QDII 场外基金（仅统计 C 类份额，A/C 限额相同，C 类无申购费更适合短期持有）：

大成 · 广发 · 国泰 · 华安 · 易方达 · 华夏 · 南方 · 天弘 · 景顺长城 · 嘉实 · 博时 · 招商 · 华泰柏瑞 · 摩根 · 汇添富 · 建信 · 宝盈 · 万家

## 快速开始

```bash
pip install -r requirements.txt

# 输出到控制台（不推飞书）
python main.py --dry-run

# 正常运行（推飞书 + 生成图片）
python main.py

# 只查指定基金
python main.py --fund-codes 008971 019172
```

## 配置

编辑 `config.json`：
- `feishu_webhook` — 飞书机器人 webhook 地址
- `funds` — 要监控的基金列表
- `github_repo` — GitHub 仓库路径（用于生成图片链接）

## GitHub Actions

每天北京时间 12:00 自动运行，也可手动触发。

1. Fork 仓库
2. Settings → Secrets → 添加 `FEISHU_WEBHOOK`

## 项目结构

```
main.py                     入口
fund_monitor/
  ├── __init__.py
  ├── cli.py                命令行解析 & 流程编排
  ├── config.py             配置加载
  ├── scraper.py            天天基金数据抓取
  ├── history.py            历史记录 & 变动检测
  ├── image.py              小红书卡片图生成
  └── notifier.py           飞书通知
config.json                 基金列表 & 配置
data/                       历史数据
output/                     生成的卡片图
```
