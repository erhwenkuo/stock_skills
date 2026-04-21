"""Scenario definitions and mappings for portfolio stress testing (KIK-365).

This module contains data-only definitions extracted from scenario_analysis.py:
- SCENARIOS: preset scenario definitions (8 scenarios)
- SCENARIO_ALIASES: natural language aliases for scenario lookup
- _TARGET_TO_SECTORS: scenario target to sector mapping
- _SUFFIX_TO_REGION: ticker suffix to region mapping
- _ETF_ASSET_CLASS: ETF ticker to asset class mapping
"""

from typing import Optional


# ---------------------------------------------------------------------------
# Preset scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS = {
    "triple_decline": {
        "name": "Triple Decline (equity/bond/yen)",
        "trigger": "Fiscal concerns and credit downgrade",
        "base_shock": -0.20,
        "effects": {
            "primary": [
                {"target": "Japan stocks", "impact": -0.12, "reason": "Foreign investor selling"},
                {"target": "JPY-denominated", "impact": -0.10, "reason": "Yen -15 yen"},
            ],
            "secondary": [
                {"target": "Growth stocks", "impact": -0.12, "reason": "Rising interest rates"},
                {"target": "Export companies", "impact": +0.06, "reason": "Yen weakness benefit"},
                {"target": "Domestic companies", "impact": -0.07, "reason": "Cost increase"},
                {"target": "Banks", "impact": +0.06, "reason": "Net interest margin improvement"},
                {"target": "Gold/safe assets", "impact": +0.03, "reason": "Some inflows from risk aversion"},
                {"target": "Long-term bonds", "impact": -0.10, "reason": "Bond price decline (one leg of triple decline)"},
            ],
            "currency": {"usd_jpy_change": +15, "impact_on_foreign": +0.097},
            "offset": ["Export companies yen weakness benefit", "Banks interest rate rise benefit"],
            "time_axis": "Immediate -> secondary effects in weeks -> intervention reversal risk",
        },
    },
    "yen_depreciation": {
        "name": "USD strength / Yen weakness",
        "trigger": "Widening US-Japan rate differential",
        "base_shock": -0.10,
        "effects": {
            "primary": [
                {"target": "US stocks (JPY)", "impact": +0.097, "reason": "FX gain"},
                {"target": "Japan export stocks", "impact": +0.06, "reason": "Yen weakness benefit"},
                {"target": "Japan domestic stocks", "impact": -0.07, "reason": "Cost increase"},
            ],
            "secondary": [
                {"target": "All foreign assets", "impact": -0.05, "reason": "Intervention -> sharp reversal risk (165->158)"},
                {"target": "Gold/safe assets", "impact": +0.03, "reason": "Gold price resilient even with strong USD"},
                {"target": "Long-term bonds", "impact": -0.03, "reason": "Bond price decline due to widening rate differential"},
            ],
            "currency": {"usd_jpy_change": +10, "impact_on_foreign": +0.065},
            "offset": ["Export companies benefit"],
            "time_axis": "Gradual: 155->165 (positive) -> 165->175 (caution) -> intervention (sharp reversal)",
        },
    },
    "us_recession": {
        "name": "US Recession",
        "trigger": "Confirmed economic recession",
        "base_shock": -0.25,
        "effects": {
            "primary": [
                {"target": "US stocks", "impact": -0.25, "reason": "Deteriorating corporate earnings"},
                {"target": "Cyclical stocks", "impact": -0.35, "reason": "Economically sensitive"},
            ],
            "secondary": [
                {"target": "Japan export stocks", "impact": -0.15, "reason": "Demand decline"},
                {"target": "ASEAN stocks", "impact": -0.10, "reason": "Capital outflows"},
                {"target": "Defensive stocks", "impact": -0.05, "reason": "Relatively resilient"},
                {"target": "Gold/safe assets", "impact": +0.08, "reason": "Safe asset demand (risk aversion)"},
                {"target": "Long-term bonds", "impact": +0.10, "reason": "Bond price rise on rate cut expectations"},
            ],
            "currency": {"usd_jpy_change": -10, "impact_on_foreign": -0.065},
            "offset": ["Defensive stocks", "Yen appreciation hedges foreign assets"],
            "time_axis": "Confirmed -> bottom in 6-12 months -> reversal on monetary easing",
        },
    },
    "boj_rate_hike": {
        "name": "BOJ Rate Hike Acceleration",
        "trigger": "Persistent inflation triggers additional rate hike",
        "base_shock": -0.15,
        "effects": {
            "primary": [
                {"target": "Growth stocks", "impact": -0.15, "reason": "Rising discount rate"},
                {"target": "Real Estate", "impact": -0.12, "reason": "Higher interest cost"},
                {"target": "Banks", "impact": +0.08, "reason": "Net interest margin expansion"},
            ],
            "secondary": [
                {"target": "High dividend stocks", "impact": -0.05, "reason": "Less attractive vs bonds"},
                {"target": "JPY-denominated foreign assets", "impact": -0.05, "reason": "Yen appreciation"},
                {"target": "Gold/safe assets", "impact": -0.02, "reason": "Rising opportunity cost from higher rates"},
                {"target": "Long-term bonds", "impact": -0.05, "reason": "Bond price decline from rising rates"},
            ],
            "currency": {"usd_jpy_change": -8, "impact_on_foreign": -0.052},
            "offset": ["Banks sector rise", "Import cost reduction from yen appreciation"],
            "time_axis": "Rate hike announcement -> immediate reaction -> priced in within 6 months",
        },
    },
    "us_china_conflict": {
        "name": "US-China Conflict Escalation",
        "trigger": "Tariff and sanction escalation",
        "base_shock": -0.15,
        "effects": {
            "primary": [
                {"target": "China-related stocks", "impact": -0.20, "reason": "Supply chain disruption"},
                {"target": "Semiconductors", "impact": -0.15, "reason": "Export restrictions"},
            ],
            "secondary": [
                {"target": "ASEAN stocks", "impact": +0.05, "reason": "Supply chain relocation destination"},
                {"target": "Defense-related", "impact": +0.08, "reason": "Geopolitical risk"},
                {"target": "Gold/safe assets", "impact": +0.08, "reason": "Safe asset demand from geopolitical risk"},
                {"target": "Long-term bonds", "impact": +0.03, "reason": "Flight to quality (government bond demand)"},
            ],
            "currency": {"usd_jpy_change": -3, "impact_on_foreign": -0.02},
            "offset": ["ASEAN production relocation benefit", "Defense-related rise"],
            "time_axis": "Announcement -> sharp drop within days -> capital shift to alternatives over months",
        },
    },
    "inflation_resurgence": {
        "name": "Inflation Resurgence",
        "trigger": "CPI re-acceleration",
        "base_shock": -0.15,
        "effects": {
            "primary": [
                {"target": "Growth stocks", "impact": -0.18, "reason": "Rate hike resumption fears"},
                {"target": "Long-term bonds", "impact": -0.10, "reason": "Rising interest rates"},
            ],
            "secondary": [
                {"target": "Energy stocks", "impact": +0.10, "reason": "Rising crude oil prices"},
                {"target": "Materials stocks", "impact": +0.05, "reason": "Rising commodity prices"},
                {"target": "Consumer-related", "impact": -0.08, "reason": "Declining purchasing power"},
                {"target": "Gold/safe assets", "impact": +0.08, "reason": "Inflation hedge demand"},
            ],
            "currency": {"usd_jpy_change": +5, "impact_on_foreign": +0.032},
            "offset": ["Commodity-related rise", "Inflation hedge assets"],
            "time_axis": "CPI release -> immediate reaction -> direction set in 3-6 months",
        },
    },
    "tech_crash": {
        "name": "Tech Crash",
        "trigger": "AI monetization disappointment, valuation correction, regulatory tightening",
        "base_shock": -0.30,
        "effects": {
            "primary": [
                {"target": "Tech stocks", "impact": -0.35, "reason": "NASDAQ -30%, valuation correction"},
                {"target": "Semiconductors", "impact": -0.40, "reason": "Excessive AI expectations correction"},
            ],
            "secondary": [
                {"target": "Non-tech stocks", "impact": -0.08, "reason": "Risk-off spillover"},
                {"target": "Defensive stocks", "impact": -0.03, "reason": "Relatively resilient due to flight to quality"},
                {"target": "Gold/safe assets", "impact": +0.06, "reason": "Safe asset demand"},
                {"target": "Long-term bonds", "impact": +0.05, "reason": "Government bond demand from flight to quality"},
            ],
            "currency": {"usd_jpy_change": -8, "impact_on_foreign": -0.052},
            "offset": ["Defensive stock resilience", "Capital flight to gold/bonds", "Foreign asset compression from yen appreciation"],
            "time_axis": "Crash -> sharp drop in days -> secondary spread over weeks -> bottom search over months",
        },
    },
    "yen_appreciation": {
        "name": "Yen Appreciation / USD Weakness",
        "trigger": "Fed rate cut acceleration + BOJ additional rate hike",
        "base_shock": -0.10,
        "effects": {
            "primary": [
                {"target": "All foreign assets", "impact": -0.13, "reason": "USD/JPY -20 yen (153->133)"},
                {"target": "Japan export stocks", "impact": -0.12, "reason": "Yen appreciation headwind"},
            ],
            "secondary": [
                {"target": "Japan domestic stocks", "impact": +0.04, "reason": "Import cost reduction"},
                {"target": "Gold/safe assets", "impact": +0.05, "reason": "Gold price rise from USD weakness"},
                {"target": "Long-term bonds", "impact": +0.03, "reason": "Bond demand in rate cut environment"},
            ],
            "currency": {"usd_jpy_change": -20, "impact_on_foreign": -0.131},
            "offset": ["Domestic companies import cost reduction", "Japan domestic consumption improvement"],
            "time_axis": "Fed rate cut decision -> rapid yen appreciation in days -> new equilibrium over months",
        },
    },
}

# ---------------------------------------------------------------------------
# Scenario name aliases (natural language support)
# ---------------------------------------------------------------------------

SCENARIO_ALIASES = {
    # triple_decline
    "トリプル安": "triple_decline",
    "triple": "triple_decline",
    "株安・円安・債券安": "triple_decline",
    # yen_depreciation
    "ドル高": "yen_depreciation",
    "ドル高円安": "yen_depreciation",
    "円安": "yen_depreciation",
    "yen": "yen_depreciation",
    "為替ショック": "yen_depreciation",
    # us_recession
    "リセッション": "us_recession",
    "recession": "us_recession",
    "景気後退": "us_recession",
    "米国リセッション": "us_recession",
    # boj_rate_hike
    "利上げ": "boj_rate_hike",
    "日銀": "boj_rate_hike",
    "日銀利上げ": "boj_rate_hike",
    "金利上昇": "boj_rate_hike",
    "boj": "boj_rate_hike",
    # us_china_conflict
    "米中": "us_china_conflict",
    "米中対立": "us_china_conflict",
    "china": "us_china_conflict",
    "地政学リスク": "us_china_conflict",
    "貿易戦争": "us_china_conflict",
    # inflation_resurgence
    "インフレ": "inflation_resurgence",
    "インフレ再燃": "inflation_resurgence",
    "inflation": "inflation_resurgence",
    "物価上昇": "inflation_resurgence",
    # tech_crash
    "テック暴落": "tech_crash",
    "tech暴落": "tech_crash",
    "ai暴落": "tech_crash",
    "ナスダック暴落": "tech_crash",
    "tech": "tech_crash",
    "テクノロジー暴落": "tech_crash",
    # yen_appreciation
    "円高ドル安": "yen_appreciation",
    "円高": "yen_appreciation",
    "ドル安": "yen_appreciation",
}

# ---------------------------------------------------------------------------
# Sector / currency mapping
# ---------------------------------------------------------------------------

# Scenario target to sector name mapping
TARGET_TO_SECTORS = {
    "Japan stocks": None,  # all sectors
    "US stocks": None,
    "Growth stocks": ["Technology", "Communication Services"],
    "Export companies": ["Industrials", "Consumer Cyclical", "Technology"],
    "Japan export stocks": ["Industrials", "Consumer Cyclical", "Technology"],
    "Domestic companies": ["Consumer Defensive", "Utilities", "Real Estate"],
    "Japan domestic stocks": ["Consumer Defensive", "Utilities", "Real Estate"],
    "Banks": ["Financial Services"],
    "Real Estate": ["Real Estate"],
    "High dividend stocks": None,  # cross-sector
    "Cyclical stocks": ["Consumer Cyclical", "Industrials", "Basic Materials"],
    "Defensive stocks": ["Consumer Defensive", "Healthcare", "Utilities"],
    "ASEAN stocks": None,  # region
    "China-related stocks": None,  # region
    "Semiconductors": ["Technology"],
    "Defense-related": ["Industrials"],
    "Energy stocks": ["Energy"],
    "Materials stocks": ["Basic Materials"],
    "Consumer-related": ["Consumer Cyclical", "Consumer Defensive"],
    "Long-term bonds": None,  # non-equity
    "JPY-denominated": None,
    "JPY-denominated foreign assets": None,
    "US stocks (JPY)": None,
    "All foreign assets": None,
    "Tech stocks": ["Technology", "Communication Services"],
    "Non-tech stocks": None,  # all sectors except tech (determined by caller)
    "Gold/safe assets": None,  # non-equity
}

# Ticker suffix -> region label
SUFFIX_TO_REGION = {
    ".T": "Japan",
    ".SI": "Singapore",
    ".BK": "Thailand",
    ".KL": "Malaysia",
    ".JK": "Indonesia",
    ".PS": "Philippines",
}

# ETF -> asset class mapping (ticker-based)
ETF_ASSET_CLASS = {
    # Gold/safe assets
    "GLDM": "Gold/safe assets",
    "GLD": "Gold/safe assets",
    "IAU": "Gold/safe assets",
    "SGOL": "Gold/safe assets",
    # Long-term bonds
    "TLT": "Long-term bonds",
    "IEF": "Long-term bonds",
    "BND": "Long-term bonds",
    "AGG": "Long-term bonds",
    "VGLT": "Long-term bonds",
    # Equity income
    "JEPI": "Equity income",
    "JEPQ": "Equity income",
    "SCHD": "Equity income",
    "VYM": "Equity income",
    "HDV": "Equity income",
    "SPYD": "Equity income",
}
