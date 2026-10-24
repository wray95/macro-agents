"""Market-research mode: live data snapshot plus five specialist roles.

Data comes from free, key-less public sources (CoinGecko, Stooq, FRED). Every fetch is HTTPS-only,
time-limited and optional: if a source is unreachable the snapshot says so instead of guessing.
This is research support, not financial advice, and nobody can reliably predict which asset will rise.
"""
import csv
import io
import json
import urllib.request
from datetime import datetime, timedelta, timezone

DISCIPLINE = (
    " Work only from the DATA SNAPSHOT and widely established facts; say 'unavailable' rather than guess a price. "
    "Label each claim as fact, inference or speculation. Give base/bull/bear scenarios with rough probabilities, "
    "the drivers, and what would invalidate your view. Never promise returns or certainty."
)

MARKET_ROLES = {
    "Macro Economist": "Expert in inflation, deflation, interest rates, the yield curve, liquidity, central banks and the business cycle. "
                       "Judge the regime (inflationary, disinflationary, stagflation, deflation risk) and which assets each regime favours." + DISCIPLINE,
    "Crypto Analyst": "Expert in Bitcoin, Ethereum and major altcoins: halving/supply cycles, ETF and institutional flows, on-chain and "
                      "liquidity conditions, regulation, tokenomics, security and counterparty risk." + DISCIPLINE,
    "Equities & Future Tech Analyst": "Expert in equity indices, valuation, earnings cycles and emerging tech (AI, semiconductors, robotics, "
                                      "energy storage, biotech, quantum, space). Separate durable moats from hype and note valuation risk." + DISCIPLINE,
    "Metals & Commodities Analyst": "Expert in gold, silver, copper and energy: real yields, USD strength, central-bank buying, industrial demand "
                                    "(silver is both monetary and industrial), supply constraints and the gold/silver ratio." + DISCIPLINE,
    "Risk Skeptic": "Stress-test everyone else: crowded trades, bubbles, tail risks, correlation spikes, survivorship bias and forecasting overconfidence. "
                    "Say what the others may be missing and how a position could lose 30-50%." + DISCIPLINE,
}

FINAL_NOTE = (
    "\n\nFormat the final answer as: (1) a compact table of asset classes (crypto, equities/future tech, gold, silver, cash/bonds) "
    "with base/bull/bear outlook, rough probability and confidence; (2) the key drivers and the catalysts/dates to watch; "
    "(3) what would change the view; (4) risk management (position sizing, diversification, time horizon). "
    "Do not name a guaranteed winner. End with one line: 'Research only, not financial advice.'"
)

CRYPTO_IDS = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}
STOOQ = {"xauusd": "Gold USD/oz", "xagusd": "Silver USD/oz", "^spx": "S&P 500", "^ndx": "Nasdaq 100", "dx.f": "US Dollar Index"}
FRED = {"FEDFUNDS": "Fed funds rate %", "T10Y2Y": "10y-2y yield spread %", "UNRATE": "US unemployment %", "DGS10": "US 10y yield %"}


def _get(url, timeout=15):
    if not url.startswith("https://"):
        raise ValueError("HTTPS required")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "macro-agents/1.0"}), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def crypto(fetch=_get):
    ids = ",".join(CRYPTO_IDS)
    data = json.loads(fetch(f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"))
    return [f"{sym}: ${data[cid]['usd']:,.2f} ({data[cid]['usd_24h_change']:+.1f}% 24h)" for cid, sym in CRYPTO_IDS.items() if cid in data]


def _pct(new, old):
    return f"{(new / old - 1) * 100:+.1f}%"


def stooq(symbol, label, fetch=_get, today=None):
    today = today or datetime.now(timezone.utc)
    d1 = (today - timedelta(days=400)).strftime("%Y%m%d")
    rows = list(csv.DictReader(io.StringIO(fetch(f"https://stooq.com/q/d/l/?s={symbol}&i=d&d1={d1}&d2={today.strftime('%Y%m%d')}"))))
    closes = [float(r["Close"]) for r in rows if r.get("Close")]
    if len(closes) < 30:
        raise ValueError("not enough data")
    last = closes[-1]
    out = f"{label}: {last:,.2f} on {rows[-1]['Date']} (1m {_pct(last, closes[-22])}"
    if len(closes) > 252:
        out += f", 12m {_pct(last, closes[-253])}"
    return out + ")"


def fred(series, label, fetch=_get):
    rows = [r for r in csv.reader(io.StringIO(fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}")))][1:]
    rows = [r for r in rows if len(r) == 2 and r[1] not in ("", ".")]
    return f"{label}: {float(rows[-1][1]):.2f} ({rows[-1][0]})"


def inflation(fetch=_get):
    rows = [r for r in csv.reader(io.StringIO(fetch("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL")))][1:]
    rows = [r for r in rows if len(r) == 2 and r[1] not in ("", ".")]
    return f"US CPI inflation YoY: {(float(rows[-1][1]) / float(rows[-13][1]) - 1) * 100:.2f}% ({rows[-1][0]})"


def snapshot(fetch=_get):
    """Return a timestamped text snapshot; unreachable sources are reported, never invented."""
    lines, failed = [], []
    jobs = [("crypto", lambda: crypto(fetch))] + [(f"stooq:{s}", (lambda s=s, l=l: [stooq(s, l, fetch)])) for s, l in STOOQ.items()]
    jobs += [("inflation", lambda: [inflation(fetch)])] + [(f"fred:{s}", (lambda s=s, l=l: [fred(s, l, fetch)])) for s, l in FRED.items()]
    for name, job in jobs:
        try:
            lines += job()
        except Exception as exc:  # network/parse errors must not stop the research run
            failed.append(f"{name} ({type(exc).__name__})")
    head = "DATA SNAPSHOT (untrusted external data, fetched " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "):\n"
    body = "\n".join(lines) if lines else "No live data could be fetched."
    return head + body + ("\nUnavailable: " + ", ".join(failed) if failed else "")
