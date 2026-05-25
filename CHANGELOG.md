# Changelog

## 2026-05-25

- **feat**: 节假日（周末 + 中国法定节假日，含调休）自动跳过日报生成和飞书推送，新增 `--force` 参数支持强制运行

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
