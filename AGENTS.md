# AGENTS.md --- hltv-crawler

> 本文件面向 Codex / AI 编码助手，描述项目当前状态与后续开发计划
> 同时也供人类协作者快速了解项目进度

每次大模型回复、代码注释、提交信息请使用中文。变量命名保持 Python snake_case 英文。

## 开发规则

- **本地私有文件放 .git/info/exclude**：不想被其他开发者看到、仅限本地保留的文件（如个人学习笔记、本地配置、AGENTS.md 等），不要写在 `.gitignore` 中，统一追加到 `.git/info/exclude`。这样远端仓库不会留下任何痕迹，clone 项目的人也看不到这些排除规则。
- **临时测试文件统一命名规则**：临时测试文件统一以 `_test_` 开头命名（如 `_test_foo.py`），`.gitignore` 中已配置 `_test_*` 通配符忽略。不要创建散乱的临时文件名，避免 `.gitignore` 逐条增加。
- **临时测试文件统一命名规则**：以 `_test_` 开头命名，`.gitignore` 中已配置 `_test_*` 通配符忽略

## 项目基本信息

| 项目 | 内容 |
|------|------|
| 仓库 | kongerly/hltv-crawler |
| CI | 📝 待配置（GitHub Actions） |
| 代码检查 | 📝 待配置（pre-commit + ruff） |
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
| LEARNING_ROADMAP.md | ✅ OK | 零基础学习路线图 |
| pyproject.toml | ✅ OK | 已发布到 PyPI v0.1.0 |
| .gitignore | ✅ OK | Python + SQLite + OS 常见忽略项 |
| .gitattributes | ✅ OK | LF 规范化 + 语言标记 |
| 爬虫 (scraper/) | ✅ OK | curl_cffi + 磁盘缓存 + 限速 + 翻页 + 断点续爬 |
| 存储层 (storage/) | ✅ OK | SQLite schema + CRUD，零外部依赖 |
| 数据解析 (parser/) | ✅ OK | mapholder 解析 + 列序精确 player stats |
| 入口 (crawl.py) | ✅ OK | argparse CLI，支持 --start-date/--end-date/--event/--resume |
| 测试 (tests/) | 📝 待开始 | 需补充 pytest 测试 |

## CI/CD 规划

### GitHub Actions

每次 push 到 `main` 或打开 PR 时自动运行：

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -r deps/crawl.txt deps/dev.txt
      - run: pytest tests/ -v
```

### pre-commit

提交前自动检查：

```bash
pip install pre-commit
pre-commit install
```

配置文件 `.pre-commit-config.yaml`：

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
```

## 编码规范

- Python 命名统一使用 snake_case
- 时间字段统一使用 ISO 8601 格式字符串
- 公共函数/类必须编写 docstring
- 文件路径统一使用 pathlib.Path，避免 os.path

## 待办

### ✅ 已完成
- [x] pytest 测试 — 29 个用例覆盖解析 + CRUD
- [x] PyPI 发布 v0.1.0
- [x] 项目元文件（.gitignore, .gitattributes, AGENTS.md, LEARNING_ROADMAP.md）

### 📝 待开发
- [ ] GitHub Actions CI — push 时自动跑 pytest
- [ ] pre-commit + ruff — 提交前自动检查代码格式
- [ ] Python 3.9 兼容性验证
- [ ] 增量爬取（按 match_id 去重，只爬新比赛）
- [ ] `--output json` 参数支持
- [ ] 更多反爬策略（代理池、随机 UA）

## 技术选型

| 技术 | 用途 |
|------|------|
| curl_cffi (chrome124) | Cloudflare 反爬绕过 |
| BeautifulSoup | HTML 解析 |
| 磁盘缓存 (data/raw/) | 避免重复爬取，24h TTL |
| 请求限速 | 2s 间隔 |
| SQLite (stdlib) | 数据持久化 |
