# 支付宝纳斯达克 QDII 基金监控

每天自动抓取支付宝中纳斯达克相关 QDII 基金（被动型 & 主动型）的**限购额度、收益率、手续费**等信息，推送到飞书群。

数据源：天天基金网（东方财富）

## 监控范围

覆盖 18 家基金公司的纳斯达克 QDII 场外基金（仅统计 C 类份额，A/C 限额相同，C 类无申购费更适合短期持有）：

大成 · 广发 · 国泰 · 华安 · 易方达 · 华夏 · 南方 · 天弘 · 景顺长城 · 嘉实 · 博时 · 招商 · 华泰柏瑞 · 摩根 · 汇添富 · 建信 · 宝盈 · 万家

## 快速开始

```bash
pip install -r requirements.txt

# 输出到控制台
python main.py --dry-run

# 推送到飞书
python main.py

# 只查指定基金
python main.py --fund-codes 008971 019172
```

## 配置

编辑 `config.json`：
- `feishu_webhook` — 飞书机器人 webhook 地址
- `funds` — 要监控的基金列表，可自由增减

## GitHub Actions 定时运行

1. Fork 仓库
2. Settings → Secrets → 添加 `FEISHU_WEBHOOK`
3. 默认每天北京时间 9:00 自动运行，也可手动触发

## 文件说明

```
main.py          入口
fund_scraper.py  从天天基金网抓取限购信息
notifier.py      飞书推送 & 报告格式化
history.py       历史记录 & 变动检测
config.json      基金列表 & webhook 配置
```
