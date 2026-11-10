# AI Radar · 个人 AI 行业情报工作台

一个免费部署、自动采集公开 RSS/Atom 信息的个人 AI 情报站。

## 已完成的 V1 功能

- 暗色自适应中文界面：总览、资讯流、收藏、信息源
- 关键词全文索引搜索（仅标题、摘要、来源、分类）
- 主题筛选、日期范围、时间排序、未读过滤
- 本地收藏、已读标记（浏览器 localStorage；不同设备**不同步**）
- 自动采集 RSS/Atom 文章的标题、摘要、发布时间、原文 URL，去重、限量、分类
- GitHub Actions 每 4 小时计划采集，支持手动触发
- 无数据库、无付费 API、无需购买域名；适合 Cloudflare Pages 静态网站

## 5 步免费部署（推荐 Cloudflare Pages）

**第一步：创建 GitHub 仓库。** 到 https://github.com/new 创建一个**公开**仓库，例如 `ai-radar`。公开仓库的标准 GitHub-hosted Actions 运行一般免费；请按你的账户和 GitHub 当前政策核实额度。可以通过 GitHub 网页 **Add file → Upload files** 上传本压缩包内的文件，但一定保留 `.github/workflows/collect.yml` 文件结构。更简单的方法是在本地解压后 `git add .` / `git commit` / `git push`。

**第二步：首次采集。** 进入 GitHub 仓库的 `Actions` → `Collect AI Feeds` → `Run workflow`。首次成功后，`site/data/articles.json` 会出现真实资讯。Action 每四小时检查一次更新。GitHub 的 schedule 可能延迟或在极端高负载下漏跑，不是严格实时服务。

**第三步：连接 Cloudflare Pages。** 在 https://dash.cloudflare.com 中打开 **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**，授权刚创建的 GitHub 仓库。注意应选择 Git 集成，不要选择 Direct Upload，否则后续不能在同一 Pages 项目改为 Git 集成。

**第四步：部署设置。** 选择 framework preset `None` / 无框架，`Build command` 留空，`Build output directory` 填 `site`。如果界面要求填写构建命令，可使用 `exit 0`。根目录使用仓库根目录。部署完成即得到一个 `https://你的项目.pages.dev` 免费子域名，不需购买域名。

**第五步：持续使用。** GitHub Actions 更新 `site/data/articles.json` 并提交到仓库后，Cloudflare Pages Git 集成会自动重新部署。注意没有运行 Actions 时，网站只会显示“等待首次采集”；这不是错误，也**不含虚构资讯**。

## 本地预览

直接打开 `site/index.html` 可能受 `file://` 文件访问限制，建议在项目根目录运行：

```bash
python -m http.server 8000 --directory site
```

然后访问 http://localhost:8000 。首次抓取真实 RSS 数据：

```bash
python -m pip install -r requirements.txt
python scripts/collect.py
```

## 数据结构和配置

- `site/index.html`, `site/styles.css`, `site/app.js`: 纯静态前端，无 Node.js 构建依赖
- `sources.json`: RSS/Atom 源清单；新增项包括 `name`, `url`, `website`, `category`, `description`
- `scripts/collect.py`: 后台采集程序，最多保留最新 1500 条，每个源每次取最多 35 条
- `site/data/articles.json`: 自动生成文章索引，格式 `{"updated_at":"...", "articles":[{"id","title","summary","url","source","category","published"}]}`
- `.github/workflows/collect.yml`: 定时采集并提交

## 限制和注意事项

1. **RSS 不保证覆盖全部行业信息。** 没有 RSS 的网站（例如部分厂商公告）未纳入。新增源前先验证地址是否能返回 RSS/Atom。
2. 本站仅索引公开文章的标题、简短摘要和链接，不抓全文；遵守源站使用条款和版权要求。
3. 初版分类是关键词规则，不是真正的 AI 语义分类；英语标题/摘要不会自动翻译为中文。
4. 收藏与已读状态存储在浏览器本地；清理站点数据会丢失。公开 GitHub 仓库和静态网页的数据对任何访问者可见，不适合存放私密笔记、密码、API Keys。
5. 免费服务受各平台政策、额度、滥用限制和 GitHub Actions 调度影响。静态网站默认没有账户系统和跨设备同步。
6. arXiv 更新量大，当前每轮每源限定抓取量；若需要全面论文索引，应单独设计查询、质量过滤和索引方案。
7. 开源发布与本地使用无需模型 API；后续中文 AI 摘要和模型评测模块可能发生模型成本。

## 下一步迭代路线

- V1.1：订阅源健康检查、手动源管理、热词趋势、更多国内一手信息源
- V2：LLM 中文摘要、事件聚类、优先级评分、每日简报
- V3：个人笔记、专题研究档案、跨设备同步（会引入用户系统与存储）
