from __future__ import annotations

import asyncio
import json
import os

from app.binance_scanner import scan_binance_demo


def main() -> int:
    report = asyncio.run(scan_binance_demo())
    print(json.dumps(report, indent=2))
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("# MPV Pro V5 — Binance Rotation Scan\n\n")
            summary.write(f"Generated: {report['generated_at']}\n\n")
            summary.write("**Mode: read-only public Spot data. No account access or orders.**\n\n")
            summary.write("| Symbol | Price (USDT) | 24h change | RSI (1h) | 1h | 4h | Signal | Score |\n")
            summary.write("|---|---:|---:|---:|---|---|---|---:|\n")
            for item in report["results"]:
                summary.write(
                    f"| {item['symbol']} | {item['price']:.8g} | {item['change_24h_percent']:+.3f}% "
                    f"| {item['rsi14_1h']:.2f} | {item['signal_1h']} | {item['signal_4h']} "
                    f"| **{item['signal']}** | {item['rotation_score']:.3f} |\n"
                )
            if report["errors"]:
                summary.write("\n## Symbols with data errors\n\n")
                for error in report["errors"]:
                    summary.write(f"- {error['symbol']}: {error['error']}\n")
            summary.write("\n> Research only. This is not a validated profitable strategy or a demo-account order connection.\n")
    return 0 if report["results"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
