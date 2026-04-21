# stock-skills

[English](README.md) | [繁體中文](README_zh-TW.md) | [简体中文](README_zh-CN.md)

一套低估值股票筛选系统。使用 Yahoo Finance API（yfinance）跨越 60 个以上地区筛选低估值股票。以 [Claude Code](https://claude.ai/code) Skills 形式运作，只需用自然语言说出需求，系统即自动执行对应功能。

## 致谢

感谢 [okiku](https://qiita.com/okikusan-public) 发表了数篇精彩文章，介绍他如何运用 Claude Code 以 Agent Skills 设计 [stock-skills](https://github.com/okikusan-public/stock_skills)。

1. [Claude Code Skills × 投资分析系列 — 文章一览](https://qiita.com/okikusan-public/items/6707fa0c99dbcc3e493f)
2. [用 Claude Code Skills 自动化股票筛选 Vol.1【Python × yfinance × 氛围编程】](https://qiita.com/okikusan-public/items/61100a5b1aa8d752ae24)
3. [用 Claude Code Skills 打造「越用越聪明」的投资分析 AI Vol.2【Neo4j × 个人开发】](https://qiita.com/okikusan-public/items/405949f83e8a39a49566)
4. [Claude Code Skills × 投资分析 Vol.3 — 处方笺引擎・逆向信号检测・股票聚类](https://qiita.com/okikusan-public/items/1765d6afb8c548f019f1)
5. [用 Claude Code Skills 自动化股票筛选 Vol.4【多 AI 代理 × Agentic AI 模式】](https://qiita.com/okikusan-public/items/27d9b0f0177293db8b1a)

原始仓库 [stock_skills](https://github.com/okikusan-public/stock_skills) 是上述 Vol.1〜3 的成果。

由于原始仓库中存在大量日文字符，本仓库将大部分备注、注释、文档字符串翻译为英文，方便希望从这些优质分享中学习的用户。

## 前置需求

| 需求项目 | 版本 | 说明 |
|:---|:---|:---|
| Python | 3.13+ | 必要 |
| [uv](https://github.com/astral-sh/uv) | 最新版 | 包与虚拟环境管理工具 |
| Docker | 最新版 | 用于 Neo4j 与 TEI（可选） |
| Neo4j | 5.x (Community) | 知识图谱 — 通过 Docker Compose 启动 |
| Grok API 密钥（`XAI_API_KEY`） | — | X 情绪分析与主题检测（可选） |

**可选服务**（所有 Skills 均可在无这些服务的情况下正常运作，支持优雅降级）：
- **Neo4j** — 启用知识图谱搜索、上下文注入与跨会话记忆
- **TEI（文字嵌入推理）** — 启用跨历史分析的向量相似度搜索
- **Grok API** — 启用 X/网络情绪分析、趋势股检测与自动主题筛选

## 安装配置

```bash
uv sync
```

执行任何命令前，请先激活虚拟环境：

```bash
source .venv/bin/activate
```

### 可选：通过 Docker 启动 Neo4j 与 TEI

```bash
docker compose up -d
python3 scripts/init_graph.py --rebuild  # 初始化模式 + 导入既有数据
```

### 环境变量

```bash
# Grok API（X 情绪分析，可选）
export XAI_API_KEY=xai-xxxxxxxxxxxxx

# Neo4j 写入深度（off/summary/full，默认：full）
export NEO4J_MODE=full

# TEI 向量搜索端点（默认：http://localhost:8081）
export TEI_URL=http://localhost:8081

# 上下文新鲜度阈值（单位：小时）
export CONTEXT_FRESH_HOURS=24    # 在此时限内 → 从缓存回答
export CONTEXT_RECENT_HOURS=168  # 在此时限内 → 增量更新 / 超过此时限 → 完整重新抓取
```

所有环境变量均为可选。未设置时系统将使用默认值正常运作。

## Skills 功能说明

### `/screen-stocks` — 低估值股票筛选

使用 EquityQuery 从日本、美国、东南亚等地区搜索股票。支持 15 种预设策略与 60 个以上地区。

```bash
# 基本用法
/screen-stocks tw value           # 台湾价值股
/screen-stocks tw high-dividend   # 台湾高股息股
/screen-stocks tw growth-value    # 台湾成长价值股

# 预设策略列表（15 种）
# value / high-dividend / growth / growth-value / deep-value / quality / pullback / alpha / trending
# long-term / shareholder-return / high-growth / small-cap-growth / contrarian / momentum

# 主题筛选
/screen-stocks tw value --theme ai           # AI 相关低估值股
/screen-stocks tw growth-value --theme ev    # EV 相关成长价值股

# 逆向操作与动能策略
/screen-stocks tw contrarian                 # 超卖股票（三轴评分）
/screen-stocks tw momentum                   # 急涨股票（四轴动能评分）

# 其他选项
/screen-stocks tw value --sector Technology  # 指定行业筛选
/screen-stocks tw value --with-pullback      # 加入回调筛选器
```

### `/stock-report` — 个股报告

针对指定的股票代码生成财务分析报告，显示估值、低估度评分、**股东回报率**（股息 + 库藏股回购）及价值陷阱判断。

```bash
/stock-report 2330.TW    # 台积电
/stock-report 2308.TW    # 台达电
```

**输出内容包含：**
- 行业与板块分类
- 估值指标（市盈率、市净率、股息收益率、ROE、盈利增长率）
- 低估度评分（0–100 分）
- **股东回报**（股息收益率 + 库藏股回购收益率 = 总股东回报率）

### `/watchlist` — 自选股管理

添加、移除及列出关注中的股票。

```bash
/watchlist list
/watchlist add my-list 2330.TW 2308.TW
/watchlist show my-list
```

### `/stress-test` — 压力测试

投资组合的冲击敏感度、情景分析、相关性分析、VaR 及建议行动。提供 8 种预定义情景（三杀、科技股崩盘、日元升值等）。

```bash
/stress-test 2330.TW,2308.TW,3231.TW,2317.TW
/stress-test 3231.TW,2317.TW --scenario triple-meltdown
```

### `/market-research` — 深度研究

对个股、行业、市场及商业模式进行深度分析。通过 Grok API 获取最新新闻、X 平台情绪及行业动态。

```bash
/market-research stock 3231.TW           # 个股研究
/market-research industry semiconductors # 行业研究
/market-research market tw               # 市场概况
/market-research business 2317.TW        # 商业模式分析
```

### `/stock-portfolio` — 投资组合管理

记录买卖交易、查看损益、分析组合结构、执行健康检查、估算收益率、再平衡及模拟。支持多币种（换算为日元）。

```bash
/stock-portfolio snapshot   # 当前损益
/stock-portfolio buy 0050.TW 1000 85.75 TWD
/stock-portfolio sell 0050.TW 5 87.25 TWD
/stock-portfolio analyze    # HHI 集中度分析
/stock-portfolio health     # 健康检查（三级警示 + 交叉信号 + 价值陷阱 + 回报稳定度）
/stock-portfolio forecast   # 估算收益率（乐观/基准/悲观 + 新闻 + X 情绪）
/stock-portfolio rebalance  # 再平衡建议
/stock-portfolio simulate   # 复利模拟（三种情景 + 股息再投资 + 定投）
/stock-portfolio what-if    # 假设情景模拟
/stock-portfolio backtest   # 回测筛选结果
```

### `/investment-note` — 投资笔记

记录、查询及删除投资论点、疑虑与学习心得。

```bash
/investment-note save --symbol 7203.T --type thesis --content "EV 普及带动零件需求增长"
/investment-note list
/investment-note list --symbol AAPL
```

### `/graph-query` — 知识图谱搜索

以自然语言搜索过去的报告、筛选结果、交易记录及研究历程。

```bash
/graph-query "0050.TW 上次报告是什么？"
/graph-query "反复出现的候选股有哪些？"
/graph-query "NVDA 情绪趋势"
```

## 配置说明

所有配置文件位于 `config/` 目录。您可以自定义筛选行为、添加地区、调整阈值，以及设置券商配置，无需修改任何 Python 代码。

### `config/screening_presets.yaml` — 筛选策略

定义 16 种内置筛选预设策略，每个预设设置传递给 EquityQuery 的条件。

```yaml
presets:
  value:
    description: "传统价值投资（低市盈率、低市净率）"
    criteria:
      max_per: 15           # 最高市盈率
      max_pbr: 1.5          # 最高市净率
      min_dividend_yield: 0.02  # 最低股息收益率（2%）
      min_roe: 0.05         # 最低 ROE（5%）
```

**可用预设策略及其重点：**

| 预设名称 | 重点 |
|:---|:---|
| `value` | 低市盈率 + 低市净率 + 股息 |
| `high-dividend` | 股息收益率 ≥ 3% |
| `growth` | 高 ROE + 营收/盈利增长 |
| `growth-value` | 成长潜力 + 低估值 |
| `deep-value` | 极低市盈率（≤8）+ 极低市净率（≤0.5）|
| `quality` | 高 ROE（≥15%）+ 低估值 |
| `pullback` | 上升趋势中的短暂回调 |
| `alpha` | 低估值 + 变化质量 + 回调信号 |
| `trending` | X/SNS 热议股票（含基本面验证） |
| `shareholder-return` | 总股东回报率（股息 + 回购）≥ 5% |
| `high-growth` | 年营收增长 ≥ 20%，PSR ≤ 20 |
| `small-cap-growth` | 市值 ≤ 1000 亿 + 年营收增长 ≥ 20% |
| `contrarian` | 技术面超卖 + 基本面稳健 |
| `momentum` | 52 周涨幅 ≥ 20% + 突破信号 |
| `long-term` | 高 ROE + EPS 增长 + 大盘股稳定性 |
| `market-darling` | 可容忍高市盈率 + 高速 EPS/营收增长 |

如需添加自定义预设，在 `screening_presets.yaml` 中新增条目，并以 `/screen-stocks <地区> <自定义预设名>` 调用。

---

### `config/exchanges.yaml` — 地区与交易所

定义 11 个支持地区的股票交易所、货币、股票代码后缀，以及默认筛选阈值。

```yaml
regions:
  tw:
    region_name: "Taiwan"
    aliases: ["tw", "taiwan"]
    exchanges:
      - code: "TAI"   # 台湾证券交易所（TWSE）
      - code: "TWO"   # 台北交易所（TPEx）
    currency: "TWD"
    ticker_suffix: ".TW"
    thresholds:
      per_max: 15.0
      pbr_max: 2.0
      dividend_yield_min: 0.03
      roe_min: 0.08
      rf: 0.01          # 无风险利率（用于收益估算）
```

**支持地区：**

| 代码 | 地区 | 货币 | 交易所 |
|:---|:---|:---|:---|
| `jp` | 日本 | JPY | 东证、福冈、札幌 |
| `us` | 美国 | USD | NASDAQ、NYSE、AMEX、OTC |
| `sg` | 新加坡 | SGD | SGX |
| `th` | 泰国 | THB | SET |
| `my` | 马来西亚 | MYR | 马来西亚交易所 |
| `id` | 印度尼西亚 | IDR | IDX |
| `ph` | 菲律宾 | PHP | PSE |
| `hk` | 香港 | HKD | 港交所 |
| `kr` | 韩国 | KRW | KOSPI、KOSDAQ |
| `tw` | 台湾 | TWD | 证交所、柜买中心 |
| `cn` | 中国 | CNY | 上交所、深交所 |
| `asean` | *（组合）* | — | sg + th + my + id + ph |

如需调整特定地区的筛选阈值（例如收紧某市场的市盈率上限），请编辑对应地区的 `thresholds` 块。

---

### `config/themes.yaml` — 主题筛选

定义 `/screen-stocks` 中 `--theme` 选项对应的行业分类。

```yaml
themes:
  ai:
    description: "AI 与半导体"
    industries:
      - Semiconductors
      - Semiconductor Equipment & Materials
      - Software—Infrastructure
      - Electronic Components
```

**可用主题：**

| 主题代码 | 说明 |
|:---|:---|
| `ai` | AI 与半导体 |
| `ev` | 电动车与新世代汽车 |
| `cloud-saas` | 云计算与 SaaS |
| `cybersecurity` | 网络安全 |
| `biotech` | 生物技术与新药研发 |
| `renewable-energy` | 可再生能源 |
| `fintech` | 金融科技 |
| `defense` | 国防与航空航天 |
| `healthcare` | 医疗健康 |

如需添加自定义主题，新增一个 key 并填写 `description` 与 `industries` 列表。行业名称须与 yfinance 的行业分类一致。

---

### `config/thresholds.yaml` — 健康检查与筛选阈值

集中管理健康检查、技术指标及投资组合分析使用的数值阈值，修改后立即生效，无需改动代码。

```yaml
health:
  rsi_drop_threshold: 40    # RSI 低于此值 → 早期预警
  cross_lookback: 60         # 扫描金叉/死叉的天数
  small_cap_warn_pct: 0.25   # 小盘股比例 > 25% → 警告
  small_cap_crit_pct: 0.35   # 小盘股比例 > 35% → 危急

contrarian:
  prefilter_fifty_day_max: 0.05   # 排除 50 日均线涨幅 > 5% 的股票
  prefilter_52wk_high_min: -0.05  # 排除距 52 周高点 5% 以内的股票

technicals:
  pullback_min: -0.20    # 回调下限（距近期高点）
  pullback_max: -0.05    # 回调上限
  rsi_reversal_lo: 25.0  # RSI 反转区间下限

theme_balance:
  max_theme_weight: 0.20    # 单一主题最大持仓比例（20%）
  fng_caution_threshold: 80 # 恐贪指数 > 80 时，主题加仓发出警告
```

---

### `config/user_profile.yaml` — 券商与税务配置

将 `config/user_profile.yaml.example` 复制为 `config/user_profile.yaml` 并填入您的券商信息，用于交易模拟中的手续费计算。

```bash
cp config/user_profile.yaml.example config/user_profile.yaml
```

```yaml
broker:
  name: Rakuten Securities
  account_type: general   # general / specific-withholding / NISA

fees:
  us_stock:
    rate: 0.00495     # 0.495% 手续费率
    max_usd: 22       # 手续费上限
  jp_stock:
    rate: 0           # 零手续费方案

tax:
  capital_gains_rate: 0.20315  # 20.315%（所得税 + 住民税）
  realized_losses_ytd: 0       # 本年度已实现亏损（损益抵扣用，请手动更新）
```

---

## 系统架构

```
Skills (.claude/skills/*/SKILL.md → scripts/*.py)
  │
  ▼
Core (src/core/)
  screening/ ─ screener, indicators, filters, query_builder, alpha, technicals, momentum, contrarian
  portfolio/ ─ portfolio_manager, portfolio_simulation, concentration, rebalancer, simulator, backtest
  risk/      ─ correlation, shock_sensitivity, scenario_analysis, scenario_definitions, recommender
  research/  ─ researcher（yfinance + Grok API 集成）
  [root]     ─ common, models, ticker_utils, health_check, return_estimate, value_trap
  │
  ├─ Markets (src/markets/) ─ japan/us/asean
  ├─ Data (src/data/)
  │    yahoo_client.py ─ 24 小时 JSON 缓存
  │    grok_client.py ─ Grok API（X 情绪分析）
  │    graph_store.py ─ Neo4j 知识图谱（双重写入）
  │    history_store.py ─ 自动累积执行历史
  ├─ Output (src/output/) ─ Markdown 格式化器
  └─ Config (config/) ─ 预设策略（15 种）· 交易所定义（60 个地区）
```

详细信息请参阅 [CLAUDE.md](CLAUDE.md)。

## Neo4j 知识图谱（可选）

将 Skills 执行历史累积至 Neo4j，可跨历史分析、交易及研究进行全文搜索。

```bash
# 使用 Docker 启动 Neo4j
docker compose up -d

# 初始化模式 + 导入既有数据
python3 scripts/init_graph.py --rebuild
```

未连接 Neo4j 时，所有 Skills 仍可正常运作（优雅降级）。

## 测试

```bash
pytest tests/           # 全部 1573 个测试（< 6 秒）
pytest tests/core/ -v   # 核心模块
```

## 免责声明

本软件仅提供投资决策的参考信息，**不保证任何投资结果**。所有依据本软件输出所做的投资决策，均由用户自行承担风险。开发者对因使用本软件而产生的任何损失概不负责。

## 许可证

本软件不设许可限制，任何人均可自由使用、修改及再分发。
