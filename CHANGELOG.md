# Changelog

## 2026-08-21

- **refactor**: 项目改名为 `qdii-quota-radar`，统一 GitHub 仓库名、本地目录、容器名与日志名
  - 原本三处名字不一致（本地 `fund-limit-monitor`、仓库 `qdii-fund-monitor`、remote 仍指向更早的 `alipay-nasdaq-fund-monitor`），本次全部对齐
  - `limit` 在金融语境歧义大（限购/规模上限/风控限额），改用 `quota` 明确指向"申购额度"
  - 容器名 `fund-monitor` → `qdii-quota-radar`，`fund-images` → `qdii-quota-radar-nginx`
  - `deploy.yml` 新增一次性迁移逻辑：停旧容器 → 整体 `mv` 旧目录 → 纠正 remote，保留 `data/history.json` 与 `.env`
  - Python 包名 `fund_monitor` 保持不变
- **feat**: 新增 `manual-run.yml` 手动工作流，可按需在服务器上触发一次真实运行（`dry_run` / `no_history` 开关），用于部署后立即验证抓取与飞书推送，不必等到次日 cron

## 2026-06-02

- **feat**: 新增第二个 JSON 主源 `eastmoney_ranking`（`rankhandler.aspx`），为近1年收益率提供独立链路
  - 抓取层升级为"双 JSON 主源 + HTML 备源"模式：JJJZ 给限购、RANKING 给业绩，HTML 仅在主源失败/缺漏时启用
  - 正常路径下 37 只基金的抓取从"1 + 37 次 HTTP 请求"压缩到"2 次全市场 JSON 请求"，速度快一个数量级
  - 收益率字段从 HTML 正则升级为 JSON 索引，前端改版不再影响该字段
- **feat**: 数据源高可用改造 —— 引入主备双源 + 历史兜底 + 交叉验证
  - 主源：天天基金 JSON 接口 `Fund_JJJZ_Data.aspx`（一次拉全市场快照，结构稳定）
  - 备源：原有 HTML 详情页解析（前端改版时降级使用）
  - 兜底：主备都失败时自动回退到 `history.json` 上次快照，飞书加 ⚠️ 标记
  - 交叉验证：主备同时成功时比对申购状态与限额，不一致打 warning（不阻塞）
  - 每条结果新增 `source`/`confidence`/`warnings` 字段；CLI 新增数据源健康面板；飞书新增"数据源健康提醒"区块
- **refactor**: 重新整理目录结构为三层（`fetch/` 抓取、`storage/` 存储、`output/` 输出）+ 入口（cli/config/trading_day），原 scraper.py 外观入口移除，由 `fund_monitor.fetch.fetch_all` 接管

## 2026-05-26

- **feat**: 飞书支持多 webhook 推送，新增 `feishu_webhooks` 配置数组（与 env 注入的 `FEISHU_WEBHOOK` 合并去重）
- **style**: 卡片水印从"纳指心理按摩师"改为"HRuning"

## 2026-05-25

- **feat**: 节假日（周末 + 中国法定节假日，含调休）自动跳过日报生成和飞书推送，新增 `--force` 参数支持强制运行
- **style**: 卡片限额列省略单位"元"，只显示数字（"万"保留作为数量级）

## 2026-05-01

- **feat**: 主动型基金添加富国全球科技互联网(QDII)C (022184)
- **fix**: 使用 macOS STHeiti Medium 字体打包进 Docker，统一本地与服务器渲染效果
- **chore**: docs/*.png 加入 .gitignore，生成图片不再提交到仓库

## 2026-04-29

- **feat**: 额度变化推送飞书时附带可复制的小红书文案
- **fix**: Docker 改用思源黑体 Medium，字体效果接近 macOS
- **fix**: 图片文件名加随机后缀，防止飞书/浏览器缓存旧图

## 2026-04-28

- **fix**: 恢复卡片字体大小和间距到 4.26 版本样式

## 2026-04-27

- **feat**: Docker 部署 + GitHub Actions 自动发布到服务器
- **fix**: emoji 改为纯文字圆点，解决服务器字体不支持 emoji 渲染为方框
- **fix**: 移除 config 中的 webhook 敏感信息，deploy 自动写入 .env
- **chore**: 清理冗余文件，润色 README

## 2026-04-26

- **feat**: 项目初始化，支付宝纳斯达克 QDII 基金限购监控
- **feat**: 添加小红书卡片图生成模块（Pillow）
- **feat**: 卡片新增近1年收益率列，飞书改为发布提醒
- **feat**: 新增主动型基金卡片，被动/主动分开生成
- **refactor**: 重构为 fund_monitor 包结构
- **refactor**: 只保留 C 类份额，状态简化为开放/暂停，按额度排序
- **fix**: 基金名称改用 config 中的 display 字段
- **fix**: 卡片显示基金代码，修复万元限额解析
