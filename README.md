# Daily Free Token Digest

每天自动整理 **Kimi / GLM / DeepSeek / Qwen** 等主流模型的免费 API 入口，按模型分类去重后通过邮件推送。

## 功能

- 每天北京时间 09:00 自动运行，也支持手动触发
- 聚合三个 GitHub 信息源
- 按模型关键词解析平台和模型表格
- 对平台入口按 URL 去重，并保留来源标注
- 在仓库中保存每日快照，用于识别新增和移除入口
- 邮件中用 **NEW** 标记新增入口；无变化时明确说明“上游今天没有变化”

## 信息源

- [mnfst/awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis)
- [jtig37/free-llm-api-resources](https://github.com/jtig37/free-llm-api-resources)
- [CYBIRD-D/FREE-LLM-API-Provider](https://github.com/CYBIRD-D/FREE-LLM-API-Provider)

这些仓库本身是维护频率有限的人工整理清单，所以地址不会每天大量变化。多来源聚合的价值在于互为补充、减少单一来源漏项，并通过每日快照让你清楚看到哪些入口是今天新增的。

## 配置 Secrets

依次进入仓库的 **Settings → Secrets and variables → Actions**，添加三个 repository secrets：

| Secret 名称 | 说明 |
|---|---|
| `SMTP_USERNAME` | 发件邮箱 |
| `SMTP_PASSWORD` | SMTP 授权码，不是邮箱登录密码 |
| `RECIPIENT_EMAIL` | 收件邮箱，可以和发件邮箱相同 |

## 运行

进入 GitHub 仓库的 **Actions → Daily Free Token Digest**，点击 **Run workflow** 即可手动测试；定时任务会在北京时间每天 09:00 运行。

首次运行会建立多来源基线。之后每封邮件会在顶部说明“新增/移除数量”，并为新增入口添加 **NEW** 标记。

## 自定义模型

编辑 `fetch_free_tokens.py` 中的 `TARGET_MODELS`，在对应模型的关键词列表中补充别名即可，例如模型的新英文名、中文品牌名或常见项目名。

## 维护说明

- `data/digest_history.json` 会随每日运行自动提交，用于对比变化。
- `email_body.html` 只是运行产物，不提交到仓库。
- 抓取顺序为 GitHub API 优先，失败后回退到 `raw.githubusercontent.com`，避免单一域名故障影响邮件发送。

## License

MIT
