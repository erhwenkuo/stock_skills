"""Portfolio commands: buy and sell -- Record stock purchases and sales."""

import sys
from datetime import date
from typing import Optional

from portfolio_commands import (
    HAS_GRAPH_STORE,
    HAS_HISTORY,
    HAS_PORTFOLIO_FORMATTER,
    HAS_PORTFOLIO_MANAGER,
    _fallback_load_csv,
    _fallback_save_csv,
    _fmt_conf_price,
    _save_trade_market_context,
    add_position,
    format_trade_result,
    load_portfolio,
    save_trade,
    sell_position,
    sync_portfolio,
)


def cmd_buy(
    csv_path: str,
    symbol: str,
    shares: int,
    price: float,
    currency: str = "JPY",
    purchase_date: Optional[str] = None,
    memo: str = "",
    yes: bool = False,
) -> None:
    """Add a purchase record to the portfolio CSV."""
    if purchase_date is None:
        purchase_date = date.today().isoformat()

    # KIK-444: Confirmation step (preview only when --yes is not specified)
    if not yes:
        total = shares * price if price else None
        lines = ["## Purchase Confirmation", "",
                 "The following purchase record will be added:", ""]
        lines.append(f"  Symbol:         {symbol}")
        lines.append(f"  Shares:         {shares:,}")
        if price:
            lines.append(f"  Purchase Price: {_fmt_conf_price(price, currency)}")
        lines.append(f"  Purchase Date:  {purchase_date}")
        if total:
            lines.append(f"  Total Cost:     {_fmt_conf_price(total, currency)}")
        if memo:
            lines.append(f"  Memo:           {memo}")
        lines.append("")
        lines.append("Proceed with recording? Re-run with `--yes` to confirm.")
        print("\n".join(lines))
        return

    if HAS_PORTFOLIO_MANAGER:
        result = add_position(csv_path, symbol, shares, price, currency, purchase_date, memo)
        if HAS_PORTFOLIO_FORMATTER:
            print(format_trade_result({
                "symbol": symbol,
                "shares": shares,
                "price": price,
                "currency": currency,
                "total_shares": result.get("shares"),
                "avg_cost": result.get("cost_price"),
                "memo": memo,
            }, "buy"))
            if HAS_HISTORY:
                try:
                    save_trade(symbol, "buy", shares, price, currency, purchase_date, memo)
                except Exception as e:
                    print(f"Warning: Failed to save history: {e}", file=sys.stderr)
                _save_trade_market_context()
            return
    else:
        holdings = _fallback_load_csv(csv_path)
        # Check if symbol already exists -- merge shares
        existing = [h for h in holdings if h["symbol"] == symbol]
        if existing:
            old = existing[0]
            # Weighted average cost
            old_total = old["cost_price"] * old["shares"]
            new_total = price * shares
            combined_shares = old["shares"] + shares
            old["cost_price"] = (old_total + new_total) / combined_shares
            old["shares"] = combined_shares
            old["purchase_date"] = purchase_date
            if memo:
                old["memo"] = memo
        else:
            holdings.append({
                "symbol": symbol,
                "shares": shares,
                "cost_price": price,
                "cost_currency": currency,
                "purchase_date": purchase_date,
                "memo": memo,
            })
        _fallback_save_csv(csv_path, holdings)

    print(f"Purchase recorded: {symbol} {shares} shares @ {price} {currency}")
    print(f"  Purchase Date: {purchase_date}")
    if memo:
        print(f"  Memo: {memo}")

    if HAS_HISTORY:
        try:
            save_trade(symbol, "buy", shares, price, currency, purchase_date, memo)
        except Exception as e:
            print(f"Warning: Failed to save history: {e}", file=sys.stderr)
        _save_trade_market_context()

    # KIK-414: Sync portfolio to Neo4j
    if HAS_GRAPH_STORE:
        try:
            _holdings = load_portfolio(csv_path) if HAS_PORTFOLIO_MANAGER else _fallback_load_csv(csv_path)
            sync_portfolio(_holdings)
        except Exception:
            pass


def cmd_sell(
    csv_path: str,
    symbol: str,
    shares: int,
    sell_price: float | None = None,
    sell_date: str | None = None,
    yes: bool = False,
) -> None:
    """Record a sale (reduce shares for a symbol). KIK-441: sell_price/sell_date added. KIK-444: yes flag added."""
    # KIK-444: Confirmation step (preview only when --yes is not specified)
    if not yes:
        lines = ["## Sale Confirmation", "",
                 "The following sale record will be added:", ""]
        lines.append(f"  Symbol:       {symbol}")
        lines.append(f"  Shares:       {shares:,}")
        cost_price = None
        currency = "JPY"
        try:
            holdings = _fallback_load_csv(csv_path)
            matching = [h for h in holdings if h.get("symbol") == symbol]
            if matching:
                cost_price = matching[0].get("cost_price")
                currency = matching[0].get("cost_currency", "JPY")
        except Exception:
            pass
        if cost_price is not None:
            lines.append(f"  Cost Price:   {_fmt_conf_price(cost_price, currency)}")
        if sell_price:
            lines.append(f"  Sale Price:   {_fmt_conf_price(sell_price, currency)}")
            if cost_price:  # Skip intentionally when cost_price=0.0 (avoid division by zero)
                pnl = (sell_price - cost_price) * shares
                pnl_rate = (sell_price - cost_price) / cost_price
                sign = "+" if pnl >= 0 else ""
                lines.append(
                    f"  Est. Realized P&L: {sign}{_fmt_conf_price(pnl, currency)}"
                    f" ({sign}{pnl_rate * 100:.2f}%)"
                )
        lines.append(f"  Sale Date:    {sell_date or date.today().isoformat()}")
        lines.append("")
        lines.append("Proceed with recording? Re-run with `--yes` to confirm.")
        print("\n".join(lines))
        return

    if HAS_PORTFOLIO_MANAGER:
        try:
            result = sell_position(csv_path, symbol, shares,
                                   sell_price=sell_price, sell_date=sell_date)
            remaining = result.get("shares", 0)
            cost_price = result.get("cost_price")
            realized_pnl = result.get("realized_pnl")
            pnl_rate = result.get("pnl_rate")
            hold_days = result.get("hold_days")
            currency = result.get("cost_currency", "JPY")
            trade_date = sell_date or date.today().isoformat()

            if HAS_PORTFOLIO_FORMATTER:
                print(format_trade_result({
                    "symbol": symbol,
                    "shares": shares,
                    "price": sell_price,
                    "currency": currency,
                    "total_shares": remaining,
                    "avg_cost": None,
                    "cost_price": cost_price,
                    "sell_price": sell_price,
                    "realized_pnl": realized_pnl,
                    "pnl_rate": pnl_rate,
                    "hold_days": hold_days,
                }, "sell"))
            else:
                if remaining == 0:
                    print(f"Sale complete: {symbol} {shares} shares (all shares sold -- removed from portfolio)")
                else:
                    print(f"Sale recorded: {symbol} {shares} shares ({remaining} shares remaining)")

            if HAS_HISTORY:
                try:
                    save_trade(
                        symbol, "sell", shares,
                        price=cost_price or 0.0,
                        currency=currency,
                        date_str=trade_date,
                        sell_price=sell_price,
                        realized_pnl=realized_pnl,
                        pnl_rate=pnl_rate,
                        hold_days=hold_days,
                        cost_price=cost_price,
                    )
                except Exception as e:
                    print(f"Warning: Failed to save history: {e}", file=sys.stderr)
                _save_trade_market_context()
            return
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    holdings = _fallback_load_csv(csv_path)
    existing = [h for h in holdings if h["symbol"] == symbol]
    if not existing:
        print(f"Error: {symbol} does not exist in portfolio.")
        sys.exit(1)

    h = existing[0]
    if shares > h["shares"]:
        print(f"Error: Sale quantity ({shares}) exceeds held shares ({h['shares']}).")
        sys.exit(1)

    h["shares"] -= shares
    if h["shares"] == 0:
        holdings = [x for x in holdings if x["symbol"] != symbol]
        print(f"Sale complete: {symbol} {shares} shares (all shares sold -- removed from portfolio)")
    else:
        print(f"Sale recorded: {symbol} {shares} shares ({h['shares']} shares remaining)")

    _fallback_save_csv(csv_path, holdings)

    trade_date = sell_date or date.today().isoformat()
    if HAS_HISTORY:
        try:
            save_trade(symbol, "sell", shares, 0.0, "", trade_date,
                       sell_price=sell_price)
        except Exception as e:
            print(f"Warning: Failed to save history: {e}", file=sys.stderr)
        _save_trade_market_context()

    # KIK-414: Sync portfolio to Neo4j
    if HAS_GRAPH_STORE:
        try:
            _holdings = load_portfolio(csv_path) if HAS_PORTFOLIO_MANAGER else _fallback_load_csv(csv_path)
            sync_portfolio(_holdings)
        except Exception:
            pass
