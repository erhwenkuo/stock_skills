---
name: plan-execute
description: プランモード — Orchestrator がワークフロー設計・実行・自律ループ・レビューを統括する。「プランモードで」と言われたときに起動。
user_invocable: true
---

# Plan-Execute スキル v2 (KIK-609)

Orchestrator が中心となり、7名のエージェント体制でワークフロー設計→実行→自律ループ→レビューを行う。

## トリガー

「プランモードで」「プランで」「プラン立てて」「プランモードで実行」等の発言。

## エージェント構成（7名）

| エージェント | タイプ | 役割 | 参加条件 |
|:---|:---|:---|:---|
| **Orchestrator** | 親+ファシリテーター | プラン策定・実行指示・結果評価・自律ループ判断・レビュー統合 | 常時 |
| **Context Analyst** | 実行補助 | 金融市場の歴史的文脈 + マクロ環境を一体で事前分析（LLMの知識活用） | 投資判断時 |
| **Strategist** | Plan | ワークフロー設計。Growth/Value/Macro/Contrarian の4視点で選択肢を設計 | 常時 |
| **Lesson Checker** | Plan | 過去のlesson（制約条件）がワークフローに反映されているかチェック | 常時 |
| **Devil's Advocate** | Plan | 盲点・バイアス・見落とし・逆張り視点を指摘 | 常時 |
| **Quantitative Reviewer** | Review | 定量チェック + Gate Keeper機能（数値整合性・税コスト・通貨配分・単元株・制約充足・全ステップ実行確認） | 常時 |
| **Qualitative + Risk Reviewer** | Review | 定性チェック（テーゼ整合・conviction尊重・カタリスト）+ リスク（地政学・マクロ・市場過熱・PF構造・銘柄固有） | 常時 |

## 動作フロー

### Phase 1: Pre-Plan

1. `python3 scripts/get_context.py "<ユーザー入力>"` でグラフコンテキストを取得
2. `python3 scripts/extract_constraints.py "<ユーザー入力>"` でlesson制約を取得（投資判断の可能性がある場合）
3. `config/user_profile.yaml` からユーザー前提設定を参照（ファイルがない場合はデフォルト値）
4. 投資判断を伴う場合 → **Context Analyst** に金融市場の歴史的文脈を取得させる

#### Context Analyst の観点

| カテゴリ | 例 |
|:---|:---|
| 市場サイクル | 「2022年FRB利上げでグロース-30%」「利上げ停止後12ヶ月で+15%」 |
| テーマの歴史 | 「AIテーマは2023年開始、2024年バブル懸念、2025年実需で再評価」 |
| バブルパターン | 「ITバブル(2000年)のPER100超 vs 現在のAI半導体PER100超」 |
| 地政学の前例 | 「2018年米中貿易戦争でAMZN-20%」「2022年ロシアウクライナでエネルギー急騰」 |
| F&Gの歴史 | 「F&G80超が1ヶ月持続後の調整は平均-8%、回復45日」 |
| 金利サイクル | 「利上げ停止→最初の利下げまでの期間、株式は歴史的に好調」 |

### Phase 2: Plan（3名並列）

Strategist + Lesson Checker + Devil's Advocate を並列起動。

#### Strategist の4視点

Strategist は以下の4視点でワークフローを設計する（独立エージェントではなく1名で4視点を内包）:

- **Growth視点**: EPS成長率、テーマの初動、Forward PER
- **Value視点**: PER/PBR、割安度スコア、配当利回り
- **Macro視点**: 金利サイクル、F&G、セクターローテーション
- **Contrarian視点**: コンセンサスに流されていないか、見落としはないか

Orchestrator は3名の結果を統合し、Lesson Checker が FAIL の場合はワークフローを修正（最大2回）。

### Phase 3: Execute

プランに従ってスキル/スクリプトを順次実行する。

### Phase 4: 結果評価 + 自律ループ

Orchestrator が実行結果を評価し、必要に応じて追加実行・プラン修正を自律的に行う。

| 評価結果 | アクション |
|:---|:---|
| 問題なし | Phase 5（Review）へ進む |
| 情報不足を検出 | 追加スクリプトをピンポイント実行 → Phase 4に戻る |
| 新事実が判明（決算日等） | プランを修正 → Phase 3に戻る |
| アクション候補を検出 | what-if を自動実行して数値付き提案を生成 → Phase 4に戻る |

#### 自律ループの具体例

**例1: 決算日判明**
Phase 3で health 実行 → Phase 4で「NFLX決算が今日と判明」
→ Orchestrator: 「NFLX利確をプランから除外」→ Phase 3に戻り修正プランで再実行

**例2: 含み益集中検出**
Phase 3で health 実行 → Phase 4で「AMZN含み益68%集中を検出」
→ Orchestrator: what-if --remove "AMZN:5" と "AMZN:7" を自動実行 → 比較表生成 → Phase 5へ

**例3: テーマギャップ検出**
Phase 3で health 実行 → Phase 4で「AIテーマのみ、他テーマ0%」
→ Orchestrator: テーマ別候補スクリーニングを追加実行 → Phase 5へ

#### 自律ループの制限
- 最大2回まで追加実行/プラン修正
- 3回目は打ち切りしてPhase 5へ進む

### Phase 5: Review（2名並列）

Quantitative Reviewer + Qualitative/Risk Reviewer を並列起動。

#### Quantitative Reviewer のチェックリスト（Gate Keeper機能含む）

| チェック | 判定 |
|:---|:---|
| Orchestratorの全ステップが実行されたか | PASS/FAIL |
| 問題検出時にアクション提案があるか | PASS/FAIL |
| 提案に株数・金額・税コストが含まれているか | PASS/FAIL |
| 単元株が正しいか（日本株100株単位、SGX100株単位等） | PASS/FAIL |
| 通貨配分60%上限を超えていないか | PASS/FAIL |
| user_profileの前提が参照されているか | PASS/FAIL |
| 数値の整合性（what-if資金収支、HHI変化等） | PASS/FAIL |
| 税コスト計算が正確か（購入時為替レート考慮） | PASS/FAIL |

#### Qualitative + Risk Reviewer の観点

**定性チェック:**
- テーゼとの整合性（利確理由がテーゼ崩壊に基づいているか、テクニカルだけか）
- lesson/conviction尊重（ユーザーが確信を持って購入した銘柄を数値だけで否定していないか）
- カタリスト検証（決算日、材料、テーマ動向を確認しているか）
- テーマの妥当性（推奨テーマが市場環境と整合しているか）

**リスクチェック:**
- 地政学リスク（米中対立、台湾有事、中東情勢、制裁 → PF銘柄のサプライチェーン影響）
- マクロリスク（金利、為替、インフレ、リセッション確率）
- 市場リスク（F&G過熱、VIX急騰、決算シーズン）
- PF構造リスク（通貨集中、セクター集中、テーマ集中、含み益集中）
- 銘柄固有リスク（流動性、規制、カントリーリスク）

#### レビューFAIL時の対応
- FAIL → Orchestrator が不足分を特定し、**不足分のみ**再実行（全やり直しではない）
- 例: Quantitative FAIL（税コスト未反映）、Qualitative PASS → 税コスト計算のみ追加 → Quantitative のみ再レビュー

### Phase 6: 最終まとめ

全 PASS → Orchestrator が最終レポートをユーザーに提示。

### リトライルール

| フェーズ | 最大回数 | 超過時 |
|:---|:---|:---|
| Phase 2 Lesson Checker FAIL | 2回 | WARN付きで続行 |
| Phase 4 自律ループ | 2回 | Phase 5に進む |
| Phase 5 レビューFAIL | 2回 | WARN付きで出力 |

3回目のFAILは打ち切り: 「⚠️ 以下の点が未解決ですが結果を提示します」

## 問題検出→自動提案トリガー（Phase 4で適用）

| 検出内容 | 自動提案内容 |
|:---|:---|
| 含み益が1銘柄にPF含み益の50%超集中 | 部分利確の具体案（株数・売却代金・税コスト試算） |
| RSI 70超 + デッドクロス同時発生 | 利確検討の具体案（何株売るか、税引後手取りはいくらか） |
| 株主還元率が3年以上連続減少 | 売却の具体案（全売却 or 入替先候補をスクリーニング） |
| ヘルスチェックでEXIT判定 | 売却 + 同セクター/テーマで代替候補3銘柄をスクリーニング |
| テーマギャップ | テーマ別の候補銘柄上位3を提示（最低投資額付き） |
| F&G 80超 + 新規買い増し提案 | 「市場過熱中」の警告を付与。キャッシュ温存との比較を提示 |

## 提案時の制約

- 単元株バリデーション: 日本株は100株単位、SGXは100株単位で提案
- 通貨配分チェック: USD 60%上限。入替先がUSD建ての場合は警告
- user_profile.yaml: 手数料・税コストを自動計算（ファイルがない場合はデフォルト値）
- F&G 80超: 新規買い増しには「市場過熱中」警告を付与

## エスカレーション判定基準

以下のいずれかに該当する場合、Context Analyst を召集し、Plan Phase で3名並列を実行:
- ユーザーの意図が売買・入替・リバランス・調整を含む
- extract_constraints.py が action_type として swap_proposal / new_buy / sell / rebalance / adjust を返す
- プラン内に what-if / adjust / rebalance コマンドが含まれる
- Phase 4の自律ループでアクション提案が生成された場合

情報照会のみ（snapshot, analyze, health 等）の場合は Context Analyst 不要、Plan Phase も軽量版（Strategist のみ）で実行可能。

## 利用可能なスキル/スクリプト一覧

| スキル | スクリプト | 用途 |
|:---|:---|:---|
| screen-stocks | run_screen.py | スクリーニング |
| stock-report | generate_report.py | 個別銘柄レポート |
| stock-portfolio | run_portfolio.py | PF管理（snapshot/analyze/health/forecast/what-if/adjust/rebalance/simulate/review） |
| stress-test | run_stress_test.py | ストレステスト |
| market-research | run_research.py | 市場・業界・銘柄リサーチ |
| watchlist | manage_watchlist.py | ウォッチリスト |
| investment-note | manage_note.py | 投資メモ |
| graph-query | run_graph_query.py | ナレッジグラフ検索 |
| — | market_dashboard.py | 市況ダッシュボード |
| — | get_context.py | グラフコンテキスト取得 |
| — | extract_constraints.py | lesson制約抽出 |
