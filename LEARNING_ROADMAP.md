# hltv-crawler 项目学习路线图

> 面向零基础到入门级开发者，帮助快速上手本项目
> 从爬虫入门到独立开发爬虫工具的全路径

## 总览

| 学习阶段 | 预估时间 | 目标 |
|----------|----------|------|
| 基础预备 | 2-3 天 | 掌握爬虫所需的前置知识 |
| 项目核心 | 2-3 天 | 理解爬虫各模块的职责与实现 |
| 进阶拓展 | 2-3 天 | 能独立修改和扩展爬虫功能 |
| **合计** | **约 6-9 天** | 具备独立开发爬虫项目的能力 |

---

## 第一阶段：基础预备（2-3 天）

### 1. Python 基础（1-1.5 天）

| 知识点 | 重要性 | 说明 |
|--------|--------|------|
| 变量、数据类型、控制流 | ★★★★★ | 最基础语法 |
| 函数定义与参数 | ★★★★★ | 项目中大量使用函数 |
| 面向对象基础（类） | ★★★★☆ | 项目中的 `HltvOrchestrator`、`Database` 等类 |
| 异常处理 `try/except` | ★★★★★ | 爬虫和解析环节大量使用 |
| 文件 I/O（`pathlib.Path`） | ★★★★★ | 项目中统一使用 `pathlib` 处理路径 |
| 日期时间处理（`datetime`） | ★★★☆☆ | 筛选比赛日期时用到 |
| 上下文管理器 `with` | ★★★☆☆ | 数据库连接、HTTP 客户端使用 |

**推荐资源：**
- [Python 官方教程（中文）](https://docs.python.org/zh-cn/3/tutorial/) — 前 8 章足够
- 《Python 编程从入门到实践》前 10 章

### 2. HTTP 与网络基础（0.5 天）

| 知识点 | 重要性 | 说明 |
|--------|--------|------|
| HTTP 请求方法（GET/POST） | ★★★★★ | 爬虫的核心交互方式 |
| 请求头（Headers）、Cookie | ★★★★★ | 伪装浏览器必须掌握 |
| 状态码（200/301/403/404/500） | ★★★★★ | 调试爬虫的基础 |
| HTML DOM 结构 | ★★★★★ | 知道 `<div>`、`<table>`、`<span>`、class/id |
| Cloudflare 反爬机制 | ★★★☆☆ | JS 挑战、指纹检测、速率限制 |

### 3. 数据库基础（0.5 天）

| 知识点 | 重要性 | 说明 |
|--------|--------|------|
| 关系型数据库概念 | ★★★★★ | 表、行、列、主键、外键 |
| SQL 基础（SELECT/INSERT/UPDATE） | ★★★★★ | 日常增删改查 |
| SQL JOIN | ★★★★☆ | 多表联合查询 |
| SQLite 特点 | ★★★☆☆ | 轻量级、零配置、文件型数据库 |

**推荐资源：**
- [SQLite Tutorial](https://www.sqlitetutorial.net/) — 前三章
- 项目中的 `storage/schema.py` 是很好的学习样本

---

## 第二阶段：项目核心（2-3 天）

### 1. 项目全景理解（0.5 天）

按以下顺序阅读关键文件：

1. **`README.md`**（10 分钟）— 项目功能、安装方式
2. **`AGENTS.md`**（10 分钟）— 项目状态、后续方向
3. **`crawl.py`**（20 分钟）— 入口文件，从 CLI 参数到流水线编排

**理解要点：**

爬虫流水线是一条线性管道：

```
events 页 → events 表
ranking 页 → teams 表 + players 表
results 页（多翻页）→ matches 表
match detail 页 → maps 表 + player_match_stats 表
```

### 2. HTTP 客户端 — scraper/http_client.py（0.5 天）

| 核心机制 | 说明 |
|----------|------|
| `curl_cffi` 浏览器指纹模拟 | Cloudflare 绕过核心技术 |
| 磁盘缓存（24h TTL） | 避免重复下载，节约带宽 |
| 请求限速（2s 间隔） | 尊重目标服务器 |
| 自动重试（最多 3 次） | 网络波动容错 |

**关键学习要点：**
- `requests.Session`-like 模式管理连接
- 缓存键的设计（URL 的 MD5 哈希）
- 限速器的实现原理（`time.sleep` + 上次请求时间记录）
- 重试退避策略

### 3. 解析器 — parser/parsers.py（1 天）

| 页面 | 解析内容 | 技术要点 |
|------|----------|----------|
| /events | 赛事名称、ID、日期 | `BeautifulSoup` 选择器、去重 |
| /results | 比赛列表、翻页 | 多行列解析、分数提取 |
| /matches/{id} | 地图详情、选手数据 | mapholder 解析、列序精确提取 |
| /ranking/teams | 战队排名、选手阵容 | 嵌套表格解析、关联提取 |

**关键学习要点：**
- `BeautifulSoup` 实战：`find()`、`find_all()`、`select()`
- 正则表达式用于 URL 和文本提取
- 容错处理：`try/except` + 默认值
- 数据清洗：字符串转数值、去空白

### 4. 编排器 — scraper/orchestrator.py（0.5 天）

| 功能 | 说明 |
|------|------|
| 流水线编排 | 5 个步骤的顺序执行 |
| 断点续爬 | `progress.json` 持久化爬取进度 |
| 事件/时间过滤 | 只爬取指定范围的比赛 |
| 翻页控制 | 自动遍历多个结果页 |

**关键学习要点：**
- 流水线设计模式：每个步骤独立可复用
- 进度持久化：JSON 文件记录已爬 ID
- 错误隔离：单个 match 失败不影响整体

### 5. 存储层 — storage/（0.5 天）

| 文件 | 核心内容 |
|------|----------|
| `storage/schema.py` | 6 张表的建表 SQL + Schema 迁移 |
| `storage/database.py` | SQLite 连接管理 + CRUD 操作 |

**6 张核心表：**

| 表 | 核心字段 | 说明 |
|----|----------|------|
| events | event_id, event_name, start_date, end_date | 赛事信息 |
| teams | team_id, team_name, world_rank | 战队排名 |
| players | player_id, player_name, team_id | 选手信息 |
| matches | match_id, team1_id, team2_id, score, winner | 比赛结果 |
| maps | map_name, team1_rounds, team2_rounds, CT/T 分侧 | 地图数据 |
| player_match_stats | rating, adr, kast, kills, deaths | 选手统计数据 |

---

## 第三阶段：进阶拓展（2-3 天）

### 1. 断点续爬实现原理（0.5 天）

- `progress.json` 的数据结构
- 已爬 match ID 的去重逻辑
- 失败 ID 的跳过机制
- 翻页 offset 恢复

**练习：** 手动修改 `progress.json` 模拟中断恢复场景

### 2. 反爬虫对抗（0.5 天）

- Cloudflare 五秒盾的原理
- TLS 指纹模拟（JA3 指纹）
- `curl_cffi` vs `requests` vs `selenium` vs `playwright`
- 请求频率控制与 IP 轮换

### 3. 数据库设计思维（0.5 天）

- 学习第三范式
- 项目中 6 张表的设计优劣分析
- **练习：** 如果要新增"武器使用统计"数据，应如何设计表结构

### 4. 生产化（0.5 天）

- GitHub Actions CI：自动运行测试
- `pre-commit`：代码格式自动检查
- `pyproject.toml`：项目元数据管理
- **思考：** 如果每天自动爬取一次新比赛，应该怎么做？（增量爬取）

### 5. CLI 工具设计（0.5 天）

- `argparse` 参数设计模式
- 友好提示 vs 详细调试模式（`--verbose`）
- `entry_points` 注册命令（`hltv-crawler` 命令）
- **练习：** 增加 `--output` 参数支持导出为 JSON

---

## 学习建议

### 按角色定制

| 你的背景 | 建议路径 |
|----------|----------|
| Python 新手，想学爬虫 | 从第一阶段开始，逐阶段推进 |
| 有 Python 基础，没做过爬虫 | 快速过第一阶段，重点学 `http_client.py` + `parsers.py` |
| 做过爬虫，想学架构设计 | 重点学 `orchestrator.py` 的流水线编排 + 断点续爬 |
| 后端/全栈开发者 | 快速浏览，重点看 `storage/database.py` 的 DAO 模式 |

### 推荐学习顺序

> `README.md` → `AGENTS.md` → `crawl.py` → `scraper/config.py` → `scraper/http_client.py` → `parser/parsers.py` → `scraper/orchestrator.py` → `storage/schema.py` → `storage/database.py` → `tests/`

### 外部资源

| 领域 | 资源 |
|------|------|
| Python | [Python 官方文档](https://docs.python.org/zh-cn/3/) |
| SQL | [SQLite Tutorial](https://www.sqlitetutorial.net/) |
| 爬虫 | [BeautifulSoup 文档](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) |
| curl_cffi | [curl_cffi GitHub](https://github.com/yifeikong/curl_cffi) |
| 反爬虫 | [curl_cffi 指纹模拟说明](https://github.com/yifeikong/curl_cffi?tab=readme-ov-file#features) |
| 自动化 | [GitHub Actions 文档](https://docs.github.com/zh/actions) |
| 测试 | [pytest 文档](https://docs.pytest.org/en/stable/) |
