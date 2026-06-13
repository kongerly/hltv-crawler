# AGENTS.md --- hltv-crawler

> 本文件面向 Codex / AI 编码助手，描述项目当前状态与后续开发计划
> 同时也供人类协作者快速了解项目进度

每次大模型回复、代码注释、提交信息请使用中文。变量命名保持 Python snake_case 英文。

## 开发规则

- **本地私有文件放 .git/info/exclude**：不想被其他开发者看到、仅限本地保留的文件统一追加到 `.git/info/exclude`
- **临时测试文件统一命名规则**：以 `_test_` 开头命名，`.gitignore` 中已配置 `_test_*` 通配符忽略

## 项目基本信息

| 项目 | 内容 |
|------|------|
| 仓库 | kongerly/hltv-crawler |
| PyPI | https://pypi.org/project/hltv-crawler/ |
| 目标 | HLTV CS2 比赛数据爬虫 —— 采集、解析、存储到 SQLite |
| Python 版本 | 3.10+（开发环境 3.13.4） |
| 虚拟环境 | .venv |
| 数据库 | SQLite（Python 标准库） |

## 项目状态一览

| 模块 | 状态 | 说明 |
|------|------|------|
| README | ✅ OK | 含安装、使用、API 示例 |
| AGENTS.md | ✅ OK | 当前文件 |
| pyproject.toml | ✅ OK | 已发布到 PyPI v0.1.0 |
| .gitignore | ✅ OK | Python + SQLite + OS 常见忽略项 |
| .gitattributes | ✅ OK | LF 规范化 + 语言标记 |
| 爬虫 (scraper/) | ✅ OK | curl_cffi + 磁盘缓存 + 限速 + 翻页 + 断点续爬 |
| 存储层 (storage/) | ✅ OK | SQLite schema + CRUD，零外部依赖 |
| 数据解析 (parser/) | ✅ OK | mapholder 解析 + 列序精确 player stats |
| 入口 (crawl.py) | ✅ OK | argparse CLI，支持 --start-date/--end-date/--event/--resume |
| 测试 (tests/) | 📝 待开始 | 需补充 pytest 测试 |

## 编码规范

- Python 命名统一使用 snake_case
- 时间字段统一使用 ISO 8601 格式字符串
- 公共函数/类必须编写 docstring
- 文件路径统一使用 pathlib.Path，避免 os.path

## 待办

- [ ] 补充 pytest 测试（解析逻辑 + 核心流程）
- [ ] GitHub Actions CI 配置
- [ ] pre-commit + ruff 代码检查
- [ ] 支持 Python 3.9 兼容

## 技术选型

| 技术 | 用途 |
|------|------|
| curl_cffi (chrome124) | Cloudflare 反爬绕过 |
| BeautifulSoup | HTML 解析 |
| 磁盘缓存 (data/raw/) | 避免重复爬取，24h TTL |
| 请求限速 | 2s 间隔 |
| SQLite (stdlib) | 数据持久化 |
