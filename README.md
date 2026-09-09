# Daily Free Token Digest

每天自动抓取 **kimi / GLM / DeepSeek / Qwen** 等主流 AI 模型的免费 token 资讯，通过邮件推送到你的邮箱。

## 功能

- 🕘 每天北京时间上午 9:00 自动运行
- 🔍 抓取多个 GitHub 仓库的免费 token 信息
- 📧 生成精美的 HTML 邮件发送到你的邮箱
- 🎯 关键词精准匹配 kimi、GLM、DeepSeek、Qwen

## 快速开始

### 1. 创建仓库

在 GitHub 上新建一个仓库，把此项目代码 push 进去。

### 2. 配置 Secrets

进入仓库 → **Settings** → 滚动到底部找到 **Secrets and variables** → **Actions** → **New repository secret**，添加三个密钥：

| Secret 名称 | 说明 | 获取方式 |
|---|---|---|
| `SMTP_USERNAME` | 发件邮箱 | 你的 QQ 邮箱地址 |
| `SMTP_PASSWORD` | 邮箱授权码 | QQ 邮箱设置 → 账户 → SMTP 服务 → 生成授权码 |
| `RECIPIENT_EMAIL` | 收件邮箱 | 可以和发件人相同 |

> ⚠️ **QQ 邮箱注意**：密码框填的是**授权码**，不是登录密码！需要先在 QQ 邮箱里开启 SMTP 服务并生成授权码。

> 📍 **找不到 Secrets 入口？** 确保你是在**仓库**的 Settings 里（不是 GitHub 账号设置），左侧侧边栏往下滚动，看到 **Secrets and variables** 分类，点进去就有 **Actions** 标签。

### 3. 启用 workflow

进入 **Actions** 标签页，找到 "Daily Free Token Digest" workflow，点击 **Enable workflow**。

### 4. 手动测试（可选）

workflow 页面 → 点击 **Run workflow** 按钮，立即测试一次。

## 自定义

- 修改 `.github/workflows/daily-free-token.yml` 中的 `cron` 表达式来调整运行时间
- 在 `fetch_free_tokens.py` 的 `TARGET_MODELS` 字典中添加/移除模型

## 数据源

- [mnfst/awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis) — 免费 LLM API 资源聚合 (7.5K+ stars)
- GitHub API 实时搜索

## License

MIT
