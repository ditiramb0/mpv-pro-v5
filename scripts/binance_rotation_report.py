from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.binance_futures import scan_binance_futures_context
from app.binance_scanner import scan_binance_demo


async def build_report() -> dict:
    spot, futures = await asyncio.gather(
        scan_binance_demo(),
        scan_binance_futures_context(),
        return_exceptions=True,
    )
    if isinstance(spot, Exception):
        raise spot
    if isinstance(futures, Exception):
        futures = {"provider": "Binance USDⓈ-M Futures public market data", "results": [],
                   "errors": [{"symbol": "ALL", "error": str(futures)[:240]}]}
    return {"spot": spot, "futures": futures}


def main() -> int:
    report = asyncio.run(build_report())
    spot = report["spot"]
    futures = report["futures"]
    print(json.dumps(report, indent=2))
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("# MPV Pro V5 — Binance Rotation & Futures Context\n\n")
            summary.write(f"Generated: {spot['generated_at']}\n\n")
            summary.write("**Mode: read-only public Spot and Futures data. No account access or orders.**\n\n")
            summary.write("## Spot rotation scan\n\n")
            summary.write("| Symbol | Price (USDT) | 24h change | RSI (1h) | 1h volume / 20h avg | 1h | 4h | Signal | Score |\n")
            summary.write("|---|---:|---:|---:|---:|---|---|---|---:|\n")
            for item in spot["results"]:
                summary.write(
                    f"| {item['symbol']} | {item['price']:.8g} | {item['change_24h_percent']:+.3f}% "
                    f"| {item['rsi14_1h']:.2f} | {item['volume_vs_previous_20h_average']} | {item['signal_1h']} | {item['signal_4h']} "
                    f"| **{item['signal']}** | {item['rotation_score']:.3f} |\n"
                )
            if spot["errors"]:
                summary.write("\nSpot data errors:\n\n")
                for error in spot["errors"]:
                    summary.write(f"- {error['symbol']}: {error['error']}\n")
            summary.write("\n## Futures market context\n\n")
            summary.write("| Symbol | Mark price | Funding rate | Mark/index basis | 24h change | Open interest | Quote volume (USDT) |\n")
            summary.write("|---|---:|---:|---:|---:|---:|---:|\n")
            for item in futures.get("results", []):
                summary.write(
                    f"| {item['symbol']} | {item['mark_price']:.8g} | {item['last_funding_percent']:+.5f}% "
                    f"| {item['mark_index_basis_percent']:+.5f}% | {item['price_change_24h_percent']:+.3f}% "
                    f"| {item['open_interest_contracts']:.8g} | {item['quote_volume_24h_usdt']:.8g} |\n"
                )
            if futures.get("errors"):
                summary.write("\nFutures data errors:\n\n")
                for error in futures["errors"]:
                    summary.write(f"- {error['symbol']}: {error['error']}\n")
            summary.write("\n> Research only. Public data does not connect a demo account. No orders are placed and profitability is not implied.\n")
    return 0 if spot["results"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
