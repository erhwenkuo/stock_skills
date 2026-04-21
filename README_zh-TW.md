# stock-skills

一套低估值股票篩選系統。使用 Yahoo Finance API（yfinance）跨越 60 個以上地區篩選低估值股票。以 [Claude Code](https://claude.ai/code) Skills 形式運作，只需用自然語言說出需求，系統即自動執行對應功能。

## 前置需求

| 需求項目 | 版本 | 說明 |
|:---|:---|:---|
| Python | 3.13+ | 必要 |
| [uv](https://github.com/astral-sh/uv) | 最新版 | 套件與虛擬環境管理工具 |
| Docker | 最新版 | 用於 Neo4j 與 TEI（選用） |
| Neo4j | 5.x (Community) | 知識圖譜 — 透過 Docker Compose 啟動 |
| Grok API 金鑰（`XAI_API_KEY`） | — | X 情緒分析與主題偵測（選用） |

**選用服務**（所有 Skills 均可在無這些服務的情況下正常運作，支援優雅降級）：
- **Neo4j** — 啟用知識圖譜搜尋、上下文注入與跨工作階段記憶
- **TEI（文字嵌入推論）** — 啟用跨歷史分析的向量相似度搜尋
- **Grok API** — 啟用 X/網路情緒分析、趨勢股偵測與自動主題篩選

## 安裝設定

```bash
uv sync
```

執行任何指令前，請先啟動虛擬環境：

```bash
source .venv/bin/activate
```

### 選用：透過 Docker 啟動 Neo4j 與 TEI

```bash
docker compose up -d
python3 scripts/init_graph.py --rebuild  # 初始化結構描述 + 匯入既有資料
```

### 環境變數

```bash
# Grok API（X 情緒分析，選用）
export XAI_API_KEY=xai-xxxxxxxxxxxxx

# Neo4j 寫入深度（off/summary/full，預設：full）
export NEO4J_MODE=full

# TEI 向量搜尋端點（預設：http://localhost:8081）
export TEI_URL=http://localhost:8081

# 上下文新鮮度閾值（單位：小時）
export CONTEXT_FRESH_HOURS=24    # 在此時限內 → 從快取回答
export CONTEXT_RECENT_HOURS=168  # 在此時限內 → 增量更新 / 超過此時限 → 完整重新抓取
```

所有環境變數皆為選用。未設定時系統將使用預設值正常運作。

## Skills 功能說明

### `/screen-stocks` — 低估值股票篩選

使用 EquityQuery 從日本、美國、東南亞等地區搜尋股票。支援 15 種預設策略與 60 個以上地區。

```bash
# 基本用法
/screen-stocks tw value           # 台灣價值股
/screen-stocks tw high-dividend   # 台灣高股息股
/screen-stocks tw growth-value    # 台灣長價值股

# 預設策略列表（15 種）
# value / high-dividend / growth / growth-value / deep-value / quality / pullback / alpha / trending
# long-term / shareholder-return / high-growth / small-cap-growth / contrarian / momentum

# 主題篩選
/screen-stocks tw value --theme ai           # AI 相關低估值股
/screen-stocks tw growth-value --theme ev    # EV 相關成長價值股

# 逆向操作與動能策略
/screen-stocks tw contrarian                 # 超賣股票（三軸評分）
/screen-stocks tw momentum                   # 急漲股票（四軸動能評分）

# 其他選項
/screen-stocks tw value --sector Technology  # 指定產業篩選
/screen-stocks tw value --with-pullback      # 加入回調篩選器
```

### `/stock-report` — 個股報告

針對指定的股票代號產生財務分析報告，顯示估值、低估度評分、**股東回報率**（股息 + 庫藏股回購）及價值陷阱判斷。

```bash
/stock-report 2330.TW    # 台積電
/stock-report 2308.TW    # 台達電
```

**輸出內容包含：**
- 產業與行業分類
- 估值指標（本益比、股價淨值比、股息殖利率、ROE、獲利成長率）
- 低估度評分（0–100 分）
- **股東回報**（股息殖利率 + 庫藏股回購殖利率 = 總股東回報率）

### `/watchlist` — 自選股管理

新增、移除及列出關注中的股票。

```bash
/watchlist list
/watchlist add my-list 2330.TW 2308.TW
/watchlist show my-list
```

### `/stress-test` — 壓力測試

投資組合的衝擊敏感度、情境分析、相關性分析、VaR 及建議行動。提供 8 種預定義情境（三殺、科技股崩盤、日圓升值等）。

```bash
/stress-test 2330.TW,2308.TW,3231.TW,2317.TW
/stress-test 3231.TW,2317.TW --scenario triple-meltdown
```

### `/market-research` — 深度研究

對個股、產業、市場及商業模式進行深度分析。透過 Grok API 取得最新新聞、X 平台情緒及產業動態。

```bash
/market-research stock 3231.TW           # 個股研究
/market-research industry semiconductors # 產業研究
/market-research market tw               # 市場概況
/market-research business 2317.TW        # 商業模式分析
```

### `/stock-portfolio` — 投資組合管理

記錄買賣交易、查看損益、分析組合結構、執行健康檢查、估算殖利率、再平衡及模擬。支援多幣別（換算為日圓）。

```bash
/stock-portfolio snapshot   # 目前損益
/stock-portfolio buy 0050.TW 1000 85.75 TWD
/stock-portfolio sell 0050.TW 5 87.25 TWD
/stock-portfolio analyze    # HHI 集中度分析
/stock-portfolio health     # 健康檢查（三級警示 + 交叉訊號 + 價值陷阱 + 回報穩定度）
/stock-portfolio forecast   # 估算殖利率（樂觀/基本/悲觀 + 新聞 + X 情緒）
/stock-portfolio rebalance  # 再平衡建議
/stock-portfolio simulate   # 複利模擬（三種情境 + 股息再投資 + 定期定額）
/stock-portfolio what-if    # 假設情境模擬
/stock-portfolio backtest   # 回測篩選結果
```

### `/investment-note` — 投資筆記

記錄、查詢及刪除投資論點、疑慮與學習心得。

```bash
/investment-note save --symbol 7203.T --type thesis --content "EV 普及帶動零件需求成長"
/investment-note list
/investment-note list --symbol AAPL
```

### `/graph-query` — 知識圖譜搜尋

以自然語言搜尋過去的報告、篩選結果、交易記錄及研究歷程。

```bash
/graph-query "0050.TW 上次報告是什麼？"
/graph-query "反覆出現的候選股有哪些？"
/graph-query "NVDA 情緒趨勢"
```

## 系統架構

```
Skills (.claude/skills/*/SKILL.md → scripts/*.py)
  │
  ▼
Core (src/core/)
  screening/ ─ screener, indicators, filters, query_builder, alpha, technicals, momentum, contrarian
  portfolio/ ─ portfolio_manager, portfolio_simulation, concentration, rebalancer, simulator, backtest
  risk/      ─ correlation, shock_sensitivity, scenario_analysis, scenario_definitions, recommender
  research/  ─ researcher（yfinance + Grok API 整合）
  [root]     ─ common, models, ticker_utils, health_check, return_estimate, value_trap
  │
  ├─ Markets (src/markets/) ─ japan/us/asean
  ├─ Data (src/data/)
  │    yahoo_client.py ─ 24 小時 JSON 快取
  │    grok_client.py ─ Grok API（X 情緒分析）
  │    graph_store.py ─ Neo4j 知識圖譜（雙重寫入）
  │    history_store.py ─ 自動累積執行歷史
  ├─ Output (src/output/) ─ Markdown 格式化器
  └─ Config (config/) ─ 預設策略（15 種）· 交易所定義（60 個地區）
```

詳細資訊請參閱 [CLAUDE.md](CLAUDE.md)。

## Neo4j 知識圖譜（選用）

將 Skills 執行歷史累積至 Neo4j，可跨歷史分析、交易及研究進行全文搜尋。

```bash
# 使用 Docker 啟動 Neo4j
docker compose up -d

# 初始化結構描述 + 匯入既有資料
python3 scripts/init_graph.py --rebuild
```

未連接 Neo4j 時，所有 Skills 仍可正常運作（優雅降級）。

## 測試

```bash
pytest tests/           # 全部 1573 個測試（< 6 秒）
pytest tests/core/ -v   # 核心模組
```

## 免責聲明

本軟體僅提供投資決策的參考資訊，**不保證任何投資結果**。所有依據本軟體輸出所做的投資決策，均由使用者自行承擔風險。開發者對因使用本軟體而產生的任何損失概不負責。

## 授權

本軟體不設授權限制，任何人均可自由使用、修改及再散布。
