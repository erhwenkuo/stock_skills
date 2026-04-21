# stock-skills

[English](README.md) | [繁體中文](README_zh-TW.md) | [简体中文](README_zh-CN.md)

一套低估值股票篩選系統。使用 Yahoo Finance API（yfinance）跨越 60 個以上地區篩選低估值股票。以 [Claude Code](https://claude.ai/code) Skills 形式運作，只需用自然語言說出需求，系統即自動執行對應功能。

## 致謝

感謝 [okiku](https://qiita.com/okikusan-public) 發表了三篇精彩文章，介紹他如何運用 Claude Code 以 Agent Skills 設計 [stock-skills](https://github.com/okikusan-public/stock_skills)。

1. [Claude Code Skills × 投資分析系列 — 文章一覽](https://qiita.com/okikusan-public/items/6707fa0c99dbcc3e493f)
2. [用 Claude Code Skills 自動化股票篩選 Vol.1【Python × yfinance × 氛圍編程】](https://qiita.com/okikusan-public/items/61100a5b1aa8d752ae24)
3. [用 Claude Code Skills 打造「越用越聰明」的投資分析 AI Vol.2【Neo4j × 個人開發】](https://qiita.com/okikusan-public/items/405949f83e8a39a49566)
4. [Claude Code Skills × 投資分析 Vol.3 — 處方箋引擎・逆向訊號偵測・股票聚類](https://qiita.com/okikusan-public/items/1765d6afb8c548f019f1)
5. [用 Claude Code Skills 自動化股票篩選 Vol.4【多 AI 代理 × Agentic AI 模式】](https://qiita.com/okikusan-public/items/27d9b0f0177293db8b1a)

原始儲存庫 [stock_skills](https://github.com/okikusan-public/stock_skills) 是上述 Vol.1〜3 的成果。

由於原始儲存庫中存在大量日文字符，本儲存庫將大部分備註、注釋、文件字串翻譯為英文，方便希望從這些優質分享中學習的使用者。

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

## 設定說明

所有設定檔位於 `config/` 目錄。您可以自訂篩選行為、新增地區、調整閾值，以及設定券商設定檔，無需修改任何 Python 程式碼。

### `config/screening_presets.yaml` — 篩選策略

定義 16 種內建篩選預設策略，每個預設設定傳遞給 EquityQuery 的條件。

```yaml
presets:
  value:
    description: "傳統價值投資（低本益比、低股價淨值比）"
    criteria:
      max_per: 15           # 最高本益比
      max_pbr: 1.5          # 最高股價淨值比
      min_dividend_yield: 0.02  # 最低股息殖利率（2%）
      min_roe: 0.05         # 最低 ROE（5%）
```

**可用預設策略及其重點：**

| 預設名稱 | 重點 |
|:---|:---|
| `value` | 低本益比 + 低股價淨值比 + 股息 |
| `high-dividend` | 股息殖利率 ≥ 3% |
| `growth` | 高 ROE + 營收/獲利成長 |
| `growth-value` | 成長潛力 + 低估值 |
| `deep-value` | 極低本益比（≤8）+ 極低股價淨值比（≤0.5）|
| `quality` | 高 ROE（≥15%）+ 低估值 |
| `pullback` | 上升趨勢中的短暫回調 |
| `alpha` | 低估值 + 變化品質 + 回調訊號 |
| `trending` | X/SNS 熱議股票（含基本面驗證） |
| `shareholder-return` | 總股東回報率（股息 + 庫藏股）≥ 5% |
| `high-growth` | 年營收成長 ≥ 20%，PSR ≤ 20 |
| `small-cap-growth` | 市值 ≤ 1000 億 + 年營收成長 ≥ 20% |
| `contrarian` | 技術面超賣 + 基本面穩健 |
| `momentum` | 52 週漲幅 ≥ 20% + 突破訊號 |
| `long-term` | 高 ROE + EPS 成長 + 大型股穩定性 |
| `market-darling` | 可容忍高本益比 + 高速 EPS/營收成長 |

如需新增自訂預設，在 `screening_presets.yaml` 加入新條目，並以 `/screen-stocks <地區> <自訂預設名>` 呼叫。

---

### `config/exchanges.yaml` — 地區與交易所

定義 11 個支援地區的股票交易所、幣別、股票代號後綴，以及預設篩選閾值。

```yaml
regions:
  tw:
    region_name: "Taiwan"
    aliases: ["tw", "taiwan"]
    exchanges:
      - code: "TAI"   # 台灣證券交易所（TWSE）
      - code: "TWO"   # 台北交易所（TPEx）
    currency: "TWD"
    ticker_suffix: ".TW"
    thresholds:
      per_max: 15.0
      pbr_max: 2.0
      dividend_yield_min: 0.03
      roe_min: 0.08
      rf: 0.01          # 無風險利率（用於報酬估算）
```

**支援地區：**

| 代碼 | 地區 | 幣別 | 交易所 |
|:---|:---|:---|:---|
| `jp` | 日本 | JPY | 東證、福岡、札幌 |
| `us` | 美國 | USD | NASDAQ、NYSE、AMEX、OTC |
| `sg` | 新加坡 | SGD | SGX |
| `th` | 泰國 | THB | SET |
| `my` | 馬來西亞 | MYR | 馬來西亞交易所 |
| `id` | 印尼 | IDR | IDX |
| `ph` | 菲律賓 | PHP | PSE |
| `hk` | 香港 | HKD | 港交所 |
| `kr` | 韓國 | KRW | KOSPI、KOSDAQ |
| `tw` | 台灣 | TWD | 證交所、櫃買中心 |
| `cn` | 中國 | CNY | 上交所、深交所 |
| `asean` | *（群組）* | — | sg + th + my + id + ph |

如需調整特定地區的篩選閾值（例如收緊某市場的本益比上限），請編輯對應地區的 `thresholds` 區塊。

---

### `config/themes.yaml` — 主題篩選

定義 `/screen-stocks` 中 `--theme` 選項對應的產業分類。

```yaml
themes:
  ai:
    description: "AI 與半導體"
    industries:
      - Semiconductors
      - Semiconductor Equipment & Materials
      - Software—Infrastructure
      - Electronic Components
```

**可用主題：**

| 主題代碼 | 說明 |
|:---|:---|
| `ai` | AI 與半導體 |
| `ev` | 電動車與新世代汽車 |
| `cloud-saas` | 雲端與 SaaS |
| `cybersecurity` | 資安 |
| `biotech` | 生技與新藥開發 |
| `renewable-energy` | 再生能源 |
| `fintech` | 金融科技 |
| `defense` | 國防與航太 |
| `healthcare` | 醫療保健 |

如需新增自訂主題，加入新的 key 並填寫 `description` 與 `industries` 清單。產業名稱須與 yfinance 的產業分類一致。

---

### `config/thresholds.yaml` — 健康檢查與篩選閾值

集中管理健康檢查、技術指標及投資組合分析使用的數值閾值，修改後立即生效，無需改動程式碼。

```yaml
health:
  rsi_drop_threshold: 40    # RSI 低於此值 → 早期預警
  cross_lookback: 60         # 掃描黃金/死亡交叉的天數
  small_cap_warn_pct: 0.25   # 小型股比例 > 25% → 警告
  small_cap_crit_pct: 0.35   # 小型股比例 > 35% → 危急

contrarian:
  prefilter_fifty_day_max: 0.05   # 排除 50 日均線漲幅 > 5% 的股票
  prefilter_52wk_high_min: -0.05  # 排除距 52 週高點 5% 以內的股票

technicals:
  pullback_min: -0.20    # 回調下限（距近期高點）
  pullback_max: -0.05    # 回調上限
  rsi_reversal_lo: 25.0  # RSI 反轉區間下限

theme_balance:
  max_theme_weight: 0.20    # 單一主題最大持倉比例（20%）
  fng_caution_threshold: 80 # 恐貪指數 > 80 時，加碼主題買入發出警告
```

---

### `config/user_profile.yaml` — 券商與稅務設定

將 `config/user_profile.yaml.example` 複製為 `config/user_profile.yaml` 並填入您的券商資訊，用於交易模擬中的手續費計算。

```bash
cp config/user_profile.yaml.example config/user_profile.yaml
```

```yaml
broker:
  name: Rakuten Securities
  account_type: general   # general / specific-withholding / NISA

fees:
  us_stock:
    rate: 0.00495     # 0.495% 手續費率
    max_usd: 22       # 手續費上限
  jp_stock:
    rate: 0           # 零手續費方案

tax:
  capital_gains_rate: 0.20315  # 20.315%（所得稅 + 住民稅）
  realized_losses_ytd: 0       # 本年度已實現虧損（損益沖抵用，請手動更新）
```

---

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
