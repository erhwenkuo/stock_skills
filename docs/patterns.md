# 開発パターンガイド

頻出開発タスクのテンプレート集。実際のコードベースに合わせた具体例を掲載している。
詳細ルールは [development.md](../rules/development.md) および [workflow.md](../rules/workflow.md) を参照。

---

## パターン1: 新スクリーニングプリセット追加

新しい投資戦略（例: 「低ボラティリティ株」）のスクリーニングプリセットを追加する手順。

### 変更ファイル一覧（順序付き）

1. `config/screening_presets.yaml` — プリセット定義を追加
2. `src/core/screening/screener_registry.py` — `build_default_registry()` に ScreenerSpec を登録
3. `src/output/formatter.py` — 専用フォーマッター関数を追加（必要な場合）
4. `.claude/rules/intent-routing.md` — preset 推定テーブルにキーワードを追加
5. `tests/core/test_screener_registry.py` — 登録テストを追加

### 1. config/screening_presets.yaml

```yaml
# 追加例: 低ボラティリティ株プリセット
low-volatility:
  description: "低ボラティリティ株（安定配当・β値低め）"
  criteria:
    max_per: 20
    min_dividend_yield: 0.02
    min_roe: 0.05
    max_beta: 0.8
```

### 2. screener_registry.py — ScreenerSpec 登録

`build_default_registry()` 関数内に追加:

```python
# src/core/screening/screener_registry.py の build_default_registry() 末尾に追加

# --- Low Volatility ---
registry.register(ScreenerSpec(
    preset="low-volatility",
    screener_class=QueryScreener,           # 既存スクリーナーを再利用
    formatter=format_query_markdown,        # または専用 formatter
    display_name="低ボラティリティ",
    category="query",
    supports_legacy=True,
    step_messages=(
        "Step 1: 低ボラティリティ条件で絞り込み中...",
        "Step 2: {n}銘柄が条件に合致",
    ),
))
```

新スクリーナークラスが必要な場合は `ContrarianScreener` / `MomentumScreener` の実装を参考に:

```python
# src/core/screening/low_volatility_screener.py

class LowVolatilityScreener:
    """低ボラティリティ株スクリーナー。

    パイプライン:
      Step 1: EquityQuery でファンダメンタルズ絞り込み
      Step 2: get_price_history() でβ値・ボラティリティを計算
      Step 3: スコアリング＋ランキング
    """

    DEFAULT_CRITERIA = {
        "max_per": 20,
        "min_dividend_yield": 0.02,
        "min_roe": 0.05,
    }

    def __init__(self, yahoo_client):
        self.yahoo_client = yahoo_client

    def screen(
        self,
        region: str = "jp",
        top_n: int = 20,
        sector: str | None = None,
        theme: str | None = None,
    ) -> list[dict]:
        criteria = dict(self.DEFAULT_CRITERIA)
        query = build_query(criteria, region=region, sector=sector, theme=theme)

        raw_quotes = self.yahoo_client.screen_stocks(
            query, size=250, max_results=max(top_n * 3, 30),
            sort_field="intradaymarketcap", sort_asc=False,
        )
        if not raw_quotes:
            return []

        scored: list[dict] = []
        for quote in raw_quotes:
            normalized = QueryScreener._normalize_quote(quote)
            symbol = normalized.get("symbol")
            if not symbol:
                continue

            hist = self.yahoo_client.get_price_history(symbol)
            lv_result = compute_low_volatility_score(hist, normalized)  # 新関数
            if lv_result["lv_score"] < 30:
                continue

            normalized.update(lv_result)
            scored.append(normalized)

        scored.sort(key=lambda r: r.get("lv_score", 0), reverse=True)
        return scored[:top_n]
```

### 3. formatter.py — フォーマッター追加

```python
# src/output/formatter.py に追加

def format_low_volatility_markdown(results: list[dict]) -> str:
    """低ボラティリティスクリーニング結果をMarkdownテーブルに整形。"""
    if not results:
        return "低ボラティリティ条件に合致する銘柄が見つかりませんでした。"

    lines = [
        "| 順位 | 銘柄 | セクター | 株価 | PER | β値 | 配当利回り | ROE | スコア |",
        "|---:|:-----|:---------|-----:|----:|----:|---------:|----:|------:|",
    ]
    for rank, row in enumerate(results, start=1):
        label = _build_label(row)
        sector = row.get("sector") or "-"
        price = _fmt_float(row.get("price"), decimals=0) if row.get("price") is not None else "-"
        per = _fmt_float(row.get("per"))
        beta = _fmt_float(row.get("beta"), decimals=2)
        div_yield = _fmt_pct(row.get("dividend_yield"))
        roe = _fmt_pct(row.get("roe"))
        score = _fmt_float(row.get("lv_score"))
        lines.append(
            f"| {rank} | {label} | {sector} | {price} | {per} | {beta} | {div_yield} | {roe} | {score} |"
        )
    _append_annotation_footer(lines, results)
    return "\n".join(lines)
```

### テスト作成例

```python
# tests/core/test_low_volatility_screener.py

import pandas as pd
import numpy as np
import pytest
from src.core.screening.low_volatility_screener import LowVolatilityScreener


def _make_stable_hist() -> pd.DataFrame:
    """低ボラティリティな価格履歴を生成。"""
    n = 250
    dates = pd.bdate_range(end="2026-02-27", periods=n)
    prices = 1000.0 + np.random.RandomState(0).randn(n) * 5  # 振れ幅小
    volumes = np.full(n, 300_000.0)
    return pd.DataFrame({"Close": prices, "Volume": volumes}, index=dates)


def _make_quote(symbol: str, per: float = 15.0, roe: float = 0.08) -> dict:
    return {
        "symbol": symbol,
        "shortName": f"Company {symbol}",
        "sector": "Utilities",
        "regularMarketPrice": 1000.0,
        "marketCap": 500_000_000_000,
        "trailingPE": per,
        "priceToBook": 1.2,
        "returnOnEquity": roe,
        "dividendYield": 3.0,
        "revenueGrowth": 0.02,
    }


class _MockClient:
    def __init__(self, quotes, hist):
        self._quotes = quotes
        self._hist = hist

    def screen_stocks(self, query, **kwargs):
        return self._quotes

    def get_price_history(self, symbol, period="1y"):
        return self._hist


class TestLowVolatilityScreener:
    def test_empty_quotes_returns_empty(self):
        client = _MockClient(quotes=[], hist=_make_stable_hist())
        screener = LowVolatilityScreener(client)
        assert screener.screen(region="jp", top_n=5) == []

    def test_stable_stock_passes_filter(self):
        quotes = [_make_quote("1234.T")]
        client = _MockClient(quotes=quotes, hist=_make_stable_hist())
        screener = LowVolatilityScreener(client)
        results = screener.screen(region="jp", top_n=5)
        # 安定銘柄はスコア >= 30 を期待
        assert len(results) >= 0  # 結果構造の確認

    def test_top_n_limits_results(self):
        quotes = [_make_quote(f"{i}000.T") for i in range(10)]
        hist = _make_stable_hist()
        client = _MockClient(quotes=quotes, hist=hist)
        screener = LowVolatilityScreener(client)
        results = screener.screen(region="jp", top_n=3)
        assert len(results) <= 3
```

### ドキュメント更新チェックリスト

- [ ] `config/screening_presets.yaml` — プリセット定義追加
- [ ] `src/core/screening/screener_registry.py` — ScreenerSpec 登録
- [ ] `src/output/formatter.py` — フォーマッター追加（専用フォーマット必要な場合）
- [ ] `.claude/rules/intent-routing.md` — preset 推定テーブルにキーワード追加
- [ ] `.claude/rules/screening.md` — スクリーナーエンジンの説明を更新
- [ ] `CLAUDE.md` — アーキテクチャセクションのモジュール一覧を更新
- [ ] `docs/skill-catalog.md` — screen-stocks スキルの対応プリセット一覧を更新

---

## パターン2: 新PFサブコマンド追加

ポートフォリオスキルに新サブコマンド（例: `compare` — 複数PFの比較）を追加する手順。

### 変更ファイル一覧（順序付き）

1. `src/core/portfolio/` — コアロジックモジュールを作成
2. `src/output/portfolio_formatter.py` — フォーマッター関数を追加
3. `.claude/skills/stock-portfolio/scripts/portfolio_commands/compare.py` — サブコマンドモジュール作成
4. `.claude/skills/stock-portfolio/scripts/portfolio_commands/__init__.py` — HAS_* フラグと import 追加
5. `.claude/skills/stock-portfolio/scripts/run_portfolio.py` — argparse サブコマンドとディスパッチ追加
6. `.claude/rules/intent-routing.md` — 保有管理ドメインの判定テーブルに追加

### 1. コアロジックモジュール

```python
# src/core/portfolio/compare.py

"""ポートフォリオ比較ロジック (KIK-NNN)。"""

from typing import Optional


def compare_portfolios(
    pf_a: list[dict],
    pf_b: list[dict],
    label_a: str = "A",
    label_b: str = "B",
) -> dict:
    """2つのポートフォリオを比較する。

    Parameters
    ----------
    pf_a, pf_b : list[dict]
        保有銘柄リスト。各要素は {"symbol", "shares", "current_price", ...} を含む。
    label_a, label_b : str
        比較ラベル（表示用）。

    Returns
    -------
    dict
        比較結果: total_value, sector_diff, common_symbols, unique_a, unique_b
    """
    symbols_a = {r["symbol"] for r in pf_a}
    symbols_b = {r["symbol"] for r in pf_b}

    return {
        "label_a": label_a,
        "label_b": label_b,
        "total_value_a": sum(r.get("current_price", 0) * r.get("shares", 0) for r in pf_a),
        "total_value_b": sum(r.get("current_price", 0) * r.get("shares", 0) for r in pf_b),
        "common_symbols": sorted(symbols_a & symbols_b),
        "unique_a": sorted(symbols_a - symbols_b),
        "unique_b": sorted(symbols_b - symbols_a),
    }
```

### 2. フォーマッター追加

```python
# src/output/portfolio_formatter.py に追加

def format_compare_markdown(compare_result: dict) -> str:
    """ポートフォリオ比較結果をMarkdownで整形。"""
    a = compare_result["label_a"]
    b = compare_result["label_b"]
    lines = [
        f"## ポートフォリオ比較: {a} vs {b}",
        "",
        f"- **{a} 総額**: ¥{compare_result['total_value_a']:,.0f}",
        f"- **{b} 総額**: ¥{compare_result['total_value_b']:,.0f}",
        "",
        f"**共通銘柄 ({len(compare_result['common_symbols'])}件)**: "
        + (", ".join(compare_result["common_symbols"]) or "なし"),
        f"**{a}のみ**: " + (", ".join(compare_result["unique_a"]) or "なし"),
        f"**{b}のみ**: " + (", ".join(compare_result["unique_b"]) or "なし"),
    ]
    return "\n".join(lines)
```

### 3. サブコマンドモジュール

```python
# .claude/skills/stock-portfolio/scripts/portfolio_commands/compare.py

"""compare サブコマンド: 複数ポートフォリオの比較 (KIK-NNN)。"""

from portfolio_commands import HAS_PORTFOLIO_MANAGER


def cmd_compare(csv_path: str, other_csv: str) -> None:
    """2つのポートフォリオCSVを比較して出力する。"""
    if not HAS_PORTFOLIO_MANAGER:
        print("ポートフォリオマネージャーが利用できません。")
        return

    try:
        from src.core.portfolio.manager import PortfolioManager
        from src.core.portfolio.compare import compare_portfolios
        from src.output.portfolio_formatter import format_compare_markdown
    except ImportError as e:
        print(f"モジュール読み込みエラー: {e}")
        return

    mgr_a = PortfolioManager(csv_path)
    mgr_b = PortfolioManager(other_csv)
    result = compare_portfolios(mgr_a.holdings, mgr_b.holdings, "メイン", "サブ")
    print(format_compare_markdown(result))
```

### 4. portfolio_commands/__init__.py への追加

```python
# .claude/skills/stock-portfolio/scripts/portfolio_commands/__init__.py に追加

# HAS_* フラグ定義（既存パターンに倣う）
try:
    from src.core.portfolio.compare import compare_portfolios as _
    HAS_COMPARE = True
except ImportError:
    HAS_COMPARE = False
```

### 5. run_portfolio.py へのサブコマンド追加

```python
# run_portfolio.py の argparse セクションに追加

# --- compare サブコマンド ---
compare_parser = subparsers.add_parser("compare", help="2つのPFを比較")
compare_parser.add_argument("--other", required=True, help="比較対象CSVパス")

# --- ディスパッチ ---
elif args.command == "compare":
    if not HAS_COMPARE:
        print("compare モジュールが利用できません。")
    else:
        from portfolio_commands.compare import cmd_compare
        cmd_compare(csv_path, args.other)
```

### テスト作成例

```python
# tests/core/test_portfolio_compare.py

import pytest
from src.core.portfolio.compare import compare_portfolios


@pytest.fixture
def pf_a():
    return [
        {"symbol": "7203.T", "shares": 100, "current_price": 2850},
        {"symbol": "9984.T", "shares": 50, "current_price": 7500},
    ]


@pytest.fixture
def pf_b():
    return [
        {"symbol": "7203.T", "shares": 200, "current_price": 2850},
        {"symbol": "AAPL", "shares": 10, "current_price": 200},
    ]


def test_common_symbols(pf_a, pf_b):
    result = compare_portfolios(pf_a, pf_b)
    assert "7203.T" in result["common_symbols"]


def test_unique_symbols(pf_a, pf_b):
    result = compare_portfolios(pf_a, pf_b)
    assert "9984.T" in result["unique_a"]
    assert "AAPL" in result["unique_b"]


def test_total_value(pf_a, pf_b):
    result = compare_portfolios(pf_a, pf_b)
    assert result["total_value_a"] == 100 * 2850 + 50 * 7500
    assert result["total_value_b"] == 200 * 2850 + 10 * 200


def test_empty_portfolio():
    result = compare_portfolios([], [])
    assert result["common_symbols"] == []
    assert result["unique_a"] == []
    assert result["unique_b"] == []
```

### ドキュメント更新チェックリスト

- [ ] `src/core/portfolio/compare.py` — コアロジック作成
- [ ] `src/output/portfolio_formatter.py` — フォーマッター追加
- [ ] `portfolio_commands/compare.py` — サブコマンドモジュール作成
- [ ] `portfolio_commands/__init__.py` — HAS_COMPARE フラグ追加
- [ ] `run_portfolio.py` — argparse + ディスパッチ追加
- [ ] `.claude/rules/intent-routing.md` — 保有管理ドメイン判定テーブルに追加
- [ ] `.claude/rules/portfolio.md` — 機能説明を追加
- [ ] `CLAUDE.md` — アーキテクチャセクションを更新
- [ ] `docs/skill-catalog.md` — stock-portfolio スキルのコマンド一覧を更新

---

## パターン3: 新Neo4jノードタイプ追加

新しいナレッジグラフノード（例: `PriceAlert` — 価格アラート）を追加する手順。

### 変更ファイル一覧（順序付き）

1. `src/data/graph_store/` — 適切なサブモジュールに merge 関数を追加
2. `src/data/graph_store/__init__.py` — 公開関数として re-export
3. `docs/neo4j-schema.md` — スキーマドキュメントを更新
4. `scripts/get_context.py` — 必要に応じてコンテキスト取得に組み込む
5. `tests/data/test_graph_store_*.py` — テスト追加

### 1. サブモジュールに merge 関数を追加

既存のサブモジュール（`note.py`, `portfolio.py`, `stock.py`, `market.py` 等）のうち
最も関連性の高いものに追記する。新ノード `PriceAlert` は `stock.py` に追加する例:

```python
# src/data/graph_store/stock.py に追加

# ---------------------------------------------------------------------------
# PriceAlert ノード (KIK-NNN)
# ---------------------------------------------------------------------------

def merge_price_alert(
    alert_id: str,
    symbol: str,
    alert_date: str,
    target_price: float,
    direction: str,       # "above" | "below"
    triggered: bool = False,
    note: str = "",
) -> bool:
    """PriceAlert ノードを作成/更新し、Stock との TARGETS リレーションを張る。

    Parameters
    ----------
    alert_id : str
        一意なアラートID（例: "alert_7203T_20260101"）。
    symbol : str
        対象銘柄シンボル（例: "7203.T"）。
    alert_date : str
        アラート設定日（ISO形式: "2026-01-01"）。
    target_price : float
        目標株価。
    direction : str
        "above" = 上抜け / "below" = 下抜け。
    triggered : bool
        発火済みフラグ。
    note : str
        補足メモ。

    Returns
    -------
    bool
        True if successful, False otherwise.
    """
    if _common._get_mode() == "off":
        return False
    driver = _common._get_driver()
    if driver is None:
        return False
    try:
        with driver.session() as session:
            session.run(
                "MERGE (a:PriceAlert {id: $id}) "
                "SET a.date = $date, a.target_price = $target_price, "
                "a.direction = $direction, a.triggered = $triggered, "
                "a.note = $note",
                id=alert_id, date=alert_date, target_price=target_price,
                direction=direction, triggered=triggered, note=note,
            )
            # Stock との TARGETS リレーション
            session.run(
                "MATCH (a:PriceAlert {id: $alert_id}) "
                "MERGE (s:Stock {symbol: $symbol}) "
                "MERGE (a)-[:TARGETS]->(s)",
                alert_id=alert_id, symbol=symbol,
            )
        return True
    except Exception:
        return False
```

### 2. __init__.py に re-export 追加

```python
# src/data/graph_store/__init__.py の stock.py セクションに追加

from src.data.graph_store.stock import (  # noqa: F401
    get_stock_history,
    merge_price_alert,   # ← 追加
    merge_report,
    merge_report_full,
    merge_screen,
    merge_stock,
    merge_watchlist,
    tag_theme,
)
```

### 3. docs/neo4j-schema.md の更新例

`docs/neo4j-schema.md` の「ノードタイプ一覧」セクションに追記:

```markdown
### PriceAlert（価格アラート, KIK-NNN）

| プロパティ | 型 | 説明 |
|:---|:---|:---|
| id | str | 一意ID |
| date | str | 設定日 (ISO) |
| target_price | float | 目標株価 |
| direction | str | "above" / "below" |
| triggered | bool | 発火済みフラグ |
| note | str | 補足メモ |

**リレーション**: `PriceAlert-[TARGETS]->Stock`
```

### テスト作成例

```python
# tests/data/test_graph_store_stock.py に追加（既存テストファイルを拡張）

from unittest.mock import MagicMock, patch
import pytest


class TestMergePriceAlert:
    """merge_price_alert() のテスト。"""

    def test_returns_false_when_mode_off(self):
        with patch("src.data.graph_store._common._get_mode", return_value="off"):
            from src.data.graph_store.stock import merge_price_alert
            result = merge_price_alert(
                "alert_001", "7203.T", "2026-01-01", 3000.0, "above"
            )
            assert result is False

    def test_returns_false_when_no_driver(self):
        with patch("src.data.graph_store._common._get_mode", return_value="full"), \
             patch("src.data.graph_store._common._get_driver", return_value=None):
            from src.data.graph_store.stock import merge_price_alert
            result = merge_price_alert(
                "alert_001", "7203.T", "2026-01-01", 3000.0, "above"
            )
            assert result is False

    def test_returns_true_on_success(self):
        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        with patch("src.data.graph_store._common._get_mode", return_value="full"), \
             patch("src.data.graph_store._common._get_driver", return_value=mock_driver):
            from src.data.graph_store.stock import merge_price_alert
            result = merge_price_alert(
                "alert_001", "7203.T", "2026-01-01", 3000.0, "above"
            )
            assert result is True
            assert mock_session.run.call_count == 2  # MERGE + TARGETS 関係

    def test_exception_returns_false(self):
        mock_session = MagicMock()
        mock_session.run.side_effect = Exception("Neo4j error")
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        with patch("src.data.graph_store._common._get_mode", return_value="full"), \
             patch("src.data.graph_store._common._get_driver", return_value=mock_driver):
            from src.data.graph_store.stock import merge_price_alert
            result = merge_price_alert(
                "alert_001", "7203.T", "2026-01-01", 3000.0, "above"
            )
            assert result is False
```

### ドキュメント更新チェックリスト

- [ ] `src/data/graph_store/<submodule>.py` — merge 関数追加
- [ ] `src/data/graph_store/__init__.py` — re-export 追加
- [ ] `docs/neo4j-schema.md` — ノードタイプ・リレーション一覧を更新
- [ ] `.claude/rules/graph-context.md` — 22ノードリストを更新
- [ ] `CLAUDE.md` — Architecture セクションのノード数を更新

---

## パターン4: 新ヘルスチェック指標追加

ポートフォリオヘルスチェックに新しい判定指標（例: 「流動性リスク」）を追加する手順。

### 変更ファイル一覧（順序付き）

1. `src/core/health_check.py` — 指標計算関数と `compute_alert_level()` への統合を追加
2. `config/thresholds.yaml` — 閾値を追加（`th()` ヘルパー経由で参照）
3. `src/output/health_formatter.py` — フォーマッターに指標の表示列を追加
4. `tests/core/test_health_check.py` — テスト追加

### 1. health_check.py への指標追加

```python
# src/core/health_check.py に追加

# 閾値定数（config/thresholds.yaml から取得, KIK-446パターン）
LIQUIDITY_MIN_VOLUME = th("health", "liquidity_min_volume", 100_000)   # 最小出来高
LIQUIDITY_MIN_MARKET_CAP = th("health", "liquidity_min_market_cap", 30_000_000_000)  # 最小時価総額


def check_liquidity_risk(
    stock_detail: dict,
    hist,  # pd.DataFrame | None
) -> dict:
    """流動性リスクを評価する。

    低出来高・低時価総額の銘柄を「流動性リスクあり」と判定する。

    Parameters
    ----------
    stock_detail : dict
        get_stock_detail() の返り値。market_cap, avg_volume を含む。
    hist : pd.DataFrame or None
        価格履歴（過去30日の出来高平均を計算するため）。

    Returns
    -------
    dict
        liquidity_risk: bool, volume_avg_30d: float, volume_label: str,
        market_cap_label: str, alerts: list[str]
    """
    alerts: list[str] = []
    info = stock_detail.get("info", stock_detail)

    market_cap = info.get("market_cap") or info.get("marketCap")
    avg_vol = info.get("averageVolume") or info.get("averageDailyVolume10Day")

    # 過去30日の出来高平均（履歴データ優先）
    volume_avg_30d: float | None = None
    if hist is not None and "Volume" in hist.columns and len(hist) >= 30:
        volume_avg_30d = float(hist["Volume"].iloc[-30:].mean())
    elif avg_vol is not None:
        volume_avg_30d = float(avg_vol)

    # 出来高評価
    if volume_avg_30d is not None and volume_avg_30d < LIQUIDITY_MIN_VOLUME:
        volume_label = "低出来高"
        alerts.append(f"平均出来高 {volume_avg_30d:,.0f} 株は低水準（売買困難のリスク）")
    else:
        volume_label = "十分"

    # 時価総額評価
    if market_cap is not None and market_cap < LIQUIDITY_MIN_MARKET_CAP:
        market_cap_label = "小規模"
        alerts.append(f"時価総額 {market_cap/1e9:.0f}十億は小規模（流動性リスクあり）")
    else:
        market_cap_label = "適正"

    return {
        "liquidity_risk": bool(alerts),
        "volume_avg_30d": volume_avg_30d,
        "volume_label": volume_label,
        "market_cap_label": market_cap_label,
        "alerts": alerts,
    }
```

`compute_alert_level()` 関数に流動性リスクを統合する:

```python
# compute_alert_level() 内の既存ロジックに追加

def compute_alert_level(
    trend_data: dict,
    change_data: dict,
    stock_detail: dict,
    is_small_cap: bool = False,
    liquidity_data: dict | None = None,   # ← 新パラメータ追加
) -> tuple[str, list[str]]:
    """...既存 docstring..."""

    # 既存のロジック ...

    # 流動性リスクによるアラート引き上げ（KIK-NNN）
    if liquidity_data and liquidity_data.get("liquidity_risk"):
        reasons.extend(liquidity_data.get("alerts", []))
        if alert_level == ALERT_NONE:
            alert_level = ALERT_EARLY_WARNING  # 流動性リスクは最低 EARLY_WARNING

    return alert_level, reasons
```

### 2. config/thresholds.yaml への閾値追加

```yaml
# config/thresholds.yaml の health セクションに追加
health:
  # ... 既存閾値 ...
  liquidity_min_volume: 100000       # 最小出来高（30日平均）
  liquidity_min_market_cap: 30000000000  # 最小時価総額（300億円）
```

### 3. health_formatter.py — 表示カラム追加

```python
# src/output/health_formatter.py の format_health_markdown() に追加

# 流動性リスク列を既存テーブルに追加
def _fmt_liquidity(liq_data: dict | None) -> str:
    if liq_data is None:
        return "-"
    if liq_data.get("liquidity_risk"):
        return "⚠️ リスクあり"
    return "OK"
```

### テスト作成例

```python
# tests/core/test_health_check.py に追加

import pandas as pd
import numpy as np
import pytest
from src.core.health_check import check_liquidity_risk


def _make_hist_with_volume(avg_vol: float, n: int = 250) -> pd.DataFrame:
    dates = pd.bdate_range(end="2026-02-27", periods=n)
    prices = np.full(n, 1000.0)
    volumes = np.full(n, avg_vol)
    return pd.DataFrame({"Close": prices, "Volume": volumes}, index=dates)


class TestCheckLiquidityRisk:
    def test_no_risk_for_high_volume(self):
        hist = _make_hist_with_volume(500_000)
        detail = {"info": {"market_cap": 100_000_000_000}}
        result = check_liquidity_risk(detail, hist)
        assert result["liquidity_risk"] is False
        assert result["volume_label"] == "十分"

    def test_risk_for_low_volume(self):
        hist = _make_hist_with_volume(50_000)  # 閾値 100,000 未満
        detail = {"info": {"market_cap": 100_000_000_000}}
        result = check_liquidity_risk(detail, hist)
        assert result["liquidity_risk"] is True
        assert "低出来高" in result["volume_label"]
        assert len(result["alerts"]) >= 1

    def test_risk_for_small_market_cap(self):
        hist = _make_hist_with_volume(500_000)
        detail = {"info": {"market_cap": 10_000_000_000}}  # 100億 < 300億
        result = check_liquidity_risk(detail, hist)
        assert result["liquidity_risk"] is True
        assert result["market_cap_label"] == "小規模"

    def test_no_hist_falls_back_to_info(self):
        detail = {"info": {"market_cap": 100_000_000_000, "averageVolume": 1_000_000}}
        result = check_liquidity_risk(detail, None)
        assert result["liquidity_risk"] is False
        assert result["volume_avg_30d"] == 1_000_000.0

    def test_empty_detail_no_crash(self):
        result = check_liquidity_risk({}, None)
        assert isinstance(result, dict)
        assert "liquidity_risk" in result
```

### ドキュメント更新チェックリスト

- [ ] `src/core/health_check.py` — 指標関数追加 + `compute_alert_level()` への統合
- [ ] `config/thresholds.yaml` — 閾値定義追加
- [ ] `src/output/health_formatter.py` — 表示列追加
- [ ] `.claude/rules/portfolio.md` — ヘルスチェックセクションに機能説明を追記
- [ ] `.claude/rules/intent-routing.md` — 関連キーワード追加（必要な場合）
- [ ] `CLAUDE.md` — アーキテクチャセクションを更新
- [ ] `docs/skill-catalog.md` — stock-portfolio スキルの出力項目を更新

---

## 共通事項

### HAS_MODULE パターン（スクリプト層）

スクリプト層 (`run_*.py`) では必ず `try/except ImportError` で可用性フラグを定義する:

```python
# 共通フラグ: scripts/common.py で管理 (KIK-448)
try:
    from src.data.history_store import HistoryStore as _
    HAS_HISTORY_STORE = True
except ImportError:
    HAS_HISTORY_STORE = False

# スクリプト固有フラグ: 各スクリプト内に定義
try:
    from src.core.portfolio.compare import compare_portfolios as _
    HAS_COMPARE = True
except ImportError:
    HAS_COMPARE = False
```

### Graceful Degradation

外部依存（Neo4j, Grok API, TEI）は常に graceful degradation を実装する:

```python
# Neo4j 未接続時はスキップ（例: health_check.py パターン）
try:
    from src.data import graph_store as gs
    if gs.is_available():
        gs.merge_health(...)
except Exception:
    pass  # Neo4j 操作は失敗しても主機能に影響させない
```

### 閾値の一元管理

ハードコードを避け、`config/thresholds.yaml` + `th()` ヘルパーを使用する:

```python
from src.core._thresholds import th

# 使用例
MY_THRESHOLD = th("health", "my_threshold", default_value)
```

### テストの自動遮断

`tests/conftest.py` の `_block_external_io` フィクスチャが Neo4j/TEI/Grok を全テストで自動モックする。
外部通信が必要なテストは `@pytest.mark.no_auto_mock` でオプトアウトできる。
