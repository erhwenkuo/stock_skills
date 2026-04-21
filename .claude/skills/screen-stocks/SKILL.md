---
name: screen-stocks
description: "Undervalued stock screening. EquityQuery-based screening without a predefined stock list. Searches for undervalued stocks across 60+ regions including Japan, US, ASEAN, Hong Kong, Korea, and Taiwan using P/E, P/B, dividend yield, ROE, and more."
argument-hint: "[region] [preset] [--sector SECTOR]  e.g.: japan value, us high-dividend, asean quality, hk value --sector Technology"
allowed-tools: Bash(python3 *)
---

# Undervalued Stock Screening Skill

Parse $ARGUMENTS to determine region, preset, and sector, then run the following command.

## Execution Command

```bash
python3 /Users/kikuchihiroyuki/stock-skills/.claude/skills/screen-stocks/scripts/run_screen.py --region <region> --preset <preset> [--sector <sector>] [--theme <theme>] [--top <N>] [--mode <query|legacy>]
```

## Natural Language Routing

For natural language → skill selection, see [.claude/rules/intent-routing.md](../../rules/intent-routing.md).

## Available Region Codes (yfinance EquityQuery)

Major regions: jp, us, sg, th, my, id, ph, hk, kr, tw, cn, gb, de, fr, in, au, br, ca, etc. (~60 regions)

## Available Exchange Codes

| Exchange | Code |
|:------|:------|
| Tokyo Stock Exchange | JPX |
| NASDAQ | NMS |
| NYSE | NYQ |
| Singapore Exchange | SES |
| Stock Exchange of Thailand | SET |
| Bursa Malaysia | KLS |
| Indonesia Stock Exchange | JKT |
| Philippine Stock Exchange | PHS |
| Hong Kong Stock Exchange | HKG |
| Korea Stock Exchange | KSC/KOE |
| Taiwan Stock Exchange | TAI |

## Theme Screening (KIK-439)

Use `--theme <theme>` in combination with any preset to narrow screening to a specific theme.
`trending`/`pullback`/`alpha` presets do not support `--theme`.

| Theme Key | Description | Target Industries (excerpt) |
|:---------|:-----|:-----------------------|
| `ai` | AI & Semiconductors | Semiconductors, Software—Infrastructure, Electronic Components |
| `ev` | EV & Next-Gen Vehicles | Auto Manufacturers, Electrical Equipment & Parts |
| `cloud-saas` | Cloud & SaaS | Software—Application, Software—Infrastructure |
| `cybersecurity` | Cybersecurity | Software—Infrastructure (security-focused) |
| `biotech` | Biotech & Drug Development | Biotechnology, Drug Manufacturers |
| `renewable-energy` | Renewable Energy | Solar, Utilities—Renewable |
| `fintech` | Fintech | Software—Application (finance-focused), Capital Markets |
| `defense` | Defense & Aerospace | Aerospace & Defense |
| `healthcare` | Healthcare & Medical Devices | Medical Devices, Health Information Services |

Theme definitions are managed in `config/themes.yaml`.

## Trend Theme Auto-Detection (KIK-440)

Use `--auto-theme` to automatically detect trending themes via the Grok API (X/Web search) and run screening for each theme sequentially.

### Pipeline

1. Grok API detects 3–5 trending themes from X/Web (with confidence scores)
2. Cross-reference with keys in `themes.yaml`; only supported themes are executed (unsupported themes show a skip notice)
3. Run the specified preset screening for each theme

### Constraints

- `--auto-theme` and `--theme` are mutually exclusive
- Cannot be combined with `trending`/`pullback`/`alpha` presets
- `XAI_API_KEY` required (exits with error if not set)

### Difference from `trending` Preset

| | `--preset trending` | `--auto-theme` |
|:---|:---|:---|
| Detection target | Trending **individual stocks** on X | Trending **themes / sectors** |
| Granularity | Stock-level | Theme-level |
| Screening | Fundamental evaluation | Any preset within each theme |

### Execution Examples

```bash
# Screen for undervalued stocks in Japanese trending themes
python3 .../run_screen.py --region japan --preset value --auto-theme

# High-growth stocks in US trending themes
python3 .../run_screen.py --region us --preset high-growth --auto-theme

# Global trending themes with default preset
python3 .../run_screen.py --preset value --auto-theme
```

## Screening Modes

- `--mode query` (default): **EquityQuery mode**. Uses yfinance's EquityQuery API to search for qualifying stocks directly without a predefined list. Works across all regions. Fast.
- `--mode legacy`: **Stock list mode**. Uses the legacy ValueScreener. Fetches and evaluates stocks from a predefined list (Nikkei 225, S&P 500, etc.) one by one. Japan/US/ASEAN only.
- `--with-pullback`: **Add pullback filter**. Applies technical pullback detection on top of any preset (value, high-dividend, etc.). No need to combine with `--preset pullback` (pullback preset takes priority). Output uses the same column format as Pullback mode.

## Presets

- `value`: Traditional value investing (low P/E, low P/B, ROE ≥ 5%)
- `high-dividend`: High-dividend stocks (dividend yield ≥ 3%)
- `growth`: Pure growth stocks (high ROE ≥ 15%, revenue growth ≥ 10%; no P/E constraint; selected by growth strength regardless of valuation)
- `growth-value`: Growth-value blend (growth potential + undervaluation)
- `deep-value`: Deep value (very low P/E and P/B)
- `quality`: Quality value (ROE ≥ 15% + undervaluation; stricter ROE threshold than `value` at 5% → 15%; limited to highly profitable undervalued stocks)
- `pullback`: Pullback entry (temporary correction during an uptrend; 3-stage pipeline: EquityQuery → technical → SR; takes longer to run)
- `alpha`: Alpha signal (3-axis integration: undervaluation + change quality + pullback; 4-stage pipeline: EquityQuery → change quality → pullback detection → 2-axis scoring; takes longer to run)
- `trending`: X-trending stocks (discover trending stocks on X via Grok API → evaluate fundamentals via Yahoo Finance; `--theme` filtering available; `XAI_API_KEY` required)
- `long-term`: Long-term investment suitability (ROE ≥ 15%, EPS growth ≥ 10%, dividend ≥ 2%, P/E ≤ 25, P/B ≤ 3, market cap ≥ ¥100B; searches for stable growth stocks suitable for long-term holding)
- `shareholder-return`: Shareholder return focus (ranked by total return rate: dividend yield + buyback yield; with stability assessment: ✅Stable/📈Increasing/⚠️Temporary/📉Declining)
- `high-growth`: High-growth stocks (profit-agnostic; revenue growth ≥ 20%, recent quarterly revenue growth ≥ 10%, PSR ≤ 20, gross margin ≥ 20%; includes unprofitable growth companies; uses PSR instead of P/E to prevent bubble selection) (KIK-432)
- `small-cap-growth`: Small-cap high-growth (market cap ≤ ¥100B; revenue growth ≥ 20%, PSR ≤ 15, gross margin ≥ 20%; targets 10x candidates undiscovered by institutions; auto-adjusts market cap threshold by region; Risk ★★★★) (KIK-437)
- `contrarian`: Contrarian candidates (technically oversold × valuationally cheap × fundamentally sound; 3-axis 100-point scoring; detects "market overreaction," the opposite of value traps) (KIK-504)
- `momentum`: Momentum surge stocks (4-axis scoring: RSI/MACD/momentum rate/volume surge; detects stocks in uptrends; `--submode` selects stable acceleration vs. surge) (KIK-506)

### Momentum Screening Details (KIK-506)

#### 3-Stage Momentum Classification

| Classification | Condition | Description |
|:---|:---|:---|
| 🟢 Accelerating | Score 40–69 | Steady upward momentum; high continuity with no overheating |
| 🟡 Surging | Score 70–89 | Rapid price rise; high short-term attention but watch for correction |
| 🔴 Overheated | Score 90–100 | Overheated state; high return potential but elevated correction risk |

#### `--submode` Parameter

Use `--submode` to filter by classification.

| Value | Shows | Recommended Use Case |
|:---|:---|:---|
| `stable` (default) | 🟢 Accelerating only | When you want stable uptrend stocks |
| `surge` | 🟡 Surging + 🔴 Overheated | When you also want short-term surge stocks |

#### 4-Axis Scoring

| Axis | Max | Condition |
|:---|:---|:---|
| RSI strength | 25 | RSI ≥ 60 |
| MACD cross | 25 | MACD > signal line (bullish cross) |
| Momentum rate | 25 | 20-day price change rate exceeds threshold |
| Volume surge | 25 | 5-day avg volume / 20-day avg volume ≥ 1.3 |

Total score ≥ 40 qualifies as a momentum stock.

## Output

Display results in Markdown table format. EquityQuery mode adds a Sector column.

### EquityQuery Mode Columns
Rank / Symbol / Sector / Price / P/E / P/B / Div Yield / ROE / Score

### Legacy Mode Columns
Rank / Symbol / Price / P/E / P/B / Div Yield / ROE / Score

### Pullback Mode Columns
Rank / Symbol / Price / P/E / Pullback% / RSI / Volume Ratio / SMA50 / SMA200 / Score

### Alpha Mode Columns
Rank / Symbol / Price / P/E / P/B / Underval / Change / Total / Pullback / α / Accel / FCF / ROE Trend

### Growth Mode Columns
Rank / Symbol / Sector / Price / P/E / P/B / EPS Growth / Revenue Growth / ROE

### Trending Mode Columns
Rank / Symbol / Trending Reason / Price / P/E / P/B / Div Yield / ROE / Score / Judgment

### Contrarian Mode Columns
Rank / Symbol / Price / P/E / P/B / RSI / SMA200 Dev / Tech / Val / Fund / Total / Judgment

### Momentum Mode Columns
Rank / Symbol / Price / P/E / RSI / MACD / Momentum Rate / Volume Ratio / Momentum Score / Total Score / Classification

### Shareholder Return Mode Columns
Rank / Symbol / Price / Div Yield / Buyback Yield / Total Return / Stability / ROE / P/E

## Execution Examples

```bash
# Japanese undervalued stocks (default)
python3 .../run_screen.py --region japan --preset value

# US high-dividend technology stocks
python3 .../run_screen.py --region us --preset high-dividend --sector Technology

# Hong Kong value stocks
python3 .../run_screen.py --region hk --preset value

# ASEAN growth-value stocks (runs sg, th, my, id, ph sequentially)
python3 .../run_screen.py --region asean --preset growth-value

# Legacy mode US screening
python3 .../run_screen.py --region us --preset value --mode legacy

# Japanese pullback candidates
python3 .../run_screen.py --region japan --preset pullback

# Japanese alpha signals (undervaluation + change + pullback)
python3 .../run_screen.py --region japan --preset alpha

# US alpha signals
python3 .../run_screen.py --region us --preset alpha

# Japanese undervalued stocks + pullback filter
python3 .../run_screen.py --region japan --preset value --with-pullback

# US high-dividend stocks + pullback filter
python3 .../run_screen.py --region us --preset high-dividend --with-pullback

# Trending Japanese stocks on X (Twitter)
python3 .../run_screen.py --region japan --preset trending

# Trending AI-related US stocks on X
python3 .../run_screen.py --region us --preset trending --theme "AI"

# Trending semiconductor-related stocks on X
python3 .../run_screen.py --region japan --preset trending --theme "semiconductors"

# Japanese long-term investment candidates
python3 .../run_screen.py --region japan --preset long-term

# US long-term investment candidates
python3 .../run_screen.py --region us --preset long-term

# Japanese pure growth stocks (no valuation constraint)
python3 .../run_screen.py --region japan --preset growth

# US pure growth stocks
python3 .../run_screen.py --region us --preset growth

# Japanese high-return stocks
python3 .../run_screen.py --region japan --preset shareholder-return

# US high-return stocks
python3 .../run_screen.py --region us --preset shareholder-return

# US high-growth stocks (profit-agnostic, PSR-based)
python3 .../run_screen.py --region us --preset high-growth

# Japanese high-growth stocks
python3 .../run_screen.py --region japan --preset high-growth

# AI-related undervalued stocks (US)
python3 .../run_screen.py --region us --preset value --theme ai

# Semiconductor high-growth stocks (US)
python3 .../run_screen.py --region us --preset high-growth --theme ai

# Defense-related stocks (US, undervalued)
python3 .../run_screen.py --region us --preset value --theme defense

# EV-related growth stocks (US)
python3 .../run_screen.py --region us --preset growth --theme ev

# Biotech high-growth stocks
python3 .../run_screen.py --region us --preset high-growth --theme biotech

# Japanese small-cap high-growth stocks (market cap ≤ ¥100B)
python3 .../run_screen.py --region japan --preset small-cap-growth

# US small-cap high-growth stocks (auto-adjusted to ≤ $1B)
python3 .../run_screen.py --region us --preset small-cap-growth

# AI-related small-cap growth stocks
python3 .../run_screen.py --region us --preset small-cap-growth --theme ai

# Japanese contrarian candidates (oversold × fundamentally sound)
python3 .../run_screen.py --region japan --preset contrarian

# US contrarian candidates
python3 .../run_screen.py --region us --preset contrarian

# Technology sector contrarian candidates
python3 .../run_screen.py --region japan --preset contrarian --sector Technology

# Japanese momentum stocks (stable acceleration only, default)
python3 .claude/skills/screen-stocks/scripts/run_screen.py --preset momentum --region japan --top 10

# US momentum screening including surge stocks
python3 .claude/skills/screen-stocks/scripts/run_screen.py --preset momentum --region us --top 5 --submode surge

# Technology sector momentum stocks
python3 .../run_screen.py --region japan --preset momentum --sector Technology
```

## Annotation Features (KIK-418/419)

Screening results are automatically annotated with markers based on investment notes and trade history.

### Marker Legend

| Marker | Meaning | Trigger |
|:---:|:---|:---|
| ⚠️ | Has concern note | Investment note type=concern |
| 📝 | Has lesson note | Investment note type=lesson |
| 👀 | On watch | Investment note type=observation + keywords like "pass", "waiting" |

### Auto-Exclusion of Sold Stocks

Stocks sold within the last 90 days are automatically excluded from screening results. The exclusion count is shown in a message.

### Data Sources

1. Neo4j knowledge graph (preferred)
2. JSON files (fallback when Neo4j is not connected)

## Knowledge Integration Rules (KIK-466)

When `get_context.py` output contains the following, integrate with screening results:

- **Recurring stocks (SURFACED 3+ times)**: "Top 3 consecutive screenings → consistently rated undervalued; detailed report recommended"
- **Held stocks**: If screening results include held stocks, "Currently held: consider as additional investment material"
- **Concern notes**: If a result stock has a concern note, append "⚠️ Has concern note"
- **Sold stocks**: If a previously sold stock reappears at the top, "Previously sold → consider re-entry"
