"""Fetch SK hynix consolidated annual accounts from Open DART and calculate ratios.

Run:
  DART_API_KEY=... python src/analyze_sk_hynix.py --start-year 2022 --end-year 2025

Outputs are written to output/. Amounts returned by DART are KRW.
"""
from __future__ import annotations
import argparse, os, re
from pathlib import Path
from typing import Iterable
import pandas as pd
import requests
from dotenv import load_dotenv

CORP_CODE = "00164779"  # SK hynix Inc.
API_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"

# DART account labels can differ slightly by filing; first matching label is selected.
ACCOUNT_PATTERNS = {
    "revenue": [r"^매출액$", r"^수익\(매출액\)$", r"^수익$"],
    "gross_profit": [r"^매출총이익$"],
    "operating_profit": [r"^영업이익\(손실\)$", r"^영업이익$"],
    "net_income": [r"^당기순이익\(손실\)$", r"^당기순이익$"],
    "total_assets": [r"^자산총계$"],
    "current_assets": [r"^유동자산$"],
    "cash": [r"^현금및현금성자산$"],
    "receivables": [r"^매출채권$", r"^매출채권 및 기타채권$"],
    "inventory": [r"^재고자산$"],
    "total_liabilities": [r"^부채총계$"],
    "current_liabilities": [r"^유동부채$"],
    "total_equity": [r"^자본총계$"],
    "interest_bearing_debt": [r"^단기차입금$", r"^장기차입금$", r"^사채$"],
    "interest_expense": [r"^이자비용$", r"^금융비용$"],
    "cfo": [r"^영업활동으로 인한 현금흐름$"],
    "investing_cf": [r"^투자활동으로 인한 현금흐름$"],
    "financing_cf": [r"^재무활동으로 인한 현금흐름$"],
    "capex": [r"^유형자산의 취득$", r"^유형자산 취득$", r"^무형자산의 취득$", r"^무형자산 취득$"],
}


def to_number(value: str) -> float:
    text = str(value).replace(",", "").strip()
    if text in {"", "-", "nan", "None"}: return float("nan")
    return float(text.replace("(", "-").replace(")", ""))


def fetch_year(api_key: str, year: int) -> list[dict]:
    params = {"crtfc_key": api_key, "corp_code": CORP_CODE, "bsns_year": year,
              "reprt_code": "11011", "fs_div": "CFS"}
    r = requests.get(API_URL, params=params, timeout=30)
    r.raise_for_status(); payload = r.json()
    if payload.get("status") != "000":
        raise RuntimeError(f"{year}: DART {payload.get('status')} - {payload.get('message')}")
    return payload["list"]


def value_for(rows: Iterable[dict], patterns: list[str], sum_matches=False) -> float:
    values=[]
    for row in rows:
        name = row.get("account_nm", "")
        if any(re.search(p, name) for p in patterns):
            values.append(to_number(row.get("thstrm_amount")))
    if not values: return float("nan")
    return sum(values) if sum_matches else values[0]


def collect(api_key: str, years: Iterable[int]) -> pd.DataFrame:
    records=[]
    for year in years:
        rows = fetch_year(api_key, year)
        record={"year":year}
        for key, patterns in ACCOUNT_PATTERNS.items():
            record[key] = value_for(rows, patterns, sum_matches=key in {"interest_bearing_debt", "capex"})
        # Cash-flow investing outflows are conventionally negative. CAPEX is stored as a positive use.
        record["capex"] = abs(record["capex"]) if pd.notna(record["capex"]) else record["capex"]
        records.append(record)
    return pd.DataFrame(records).sort_values("year").reset_index(drop=True)


def pct(n, d): return n / d * 100 if pd.notna(n) and pd.notna(d) and d != 0 else float("nan")
def ratio(n, d): return n / d if pd.notna(n) and pd.notna(d) and d != 0 else float("nan")

def add_ratios(df: pd.DataFrame) -> pd.DataFrame:
    out=df.copy()
    out["revenue_growth_pct"] = out["revenue"].pct_change() * 100
    out["gross_margin_pct"] = [pct(a,b) for a,b in zip(out.gross_profit,out.revenue)]
    out["operating_margin_pct"] = [pct(a,b) for a,b in zip(out.operating_profit,out.revenue)]
    out["net_margin_pct"] = [pct(a,b) for a,b in zip(out.net_income,out.revenue)]
    out["current_ratio_pct"] = [pct(a,b) for a,b in zip(out.current_assets,out.current_liabilities)]
    out["debt_to_equity_pct"] = [pct(a,b) for a,b in zip(out.total_liabilities,out.total_equity)]
    out["equity_ratio_pct"] = [pct(a,b) for a,b in zip(out.total_equity,out.total_assets)]
    out["net_debt"] = out.interest_bearing_debt - out.cash
    out["fcf"] = out.cfo - out.capex
    out["cfo_to_net_income"] = [ratio(a,b) for a,b in zip(out.cfo,out.net_income)]
    out["interest_coverage_x"] = [ratio(a,b) for a,b in zip(out.operating_profit,out.interest_expense)]
    out["avg_assets"]=(out.total_assets + out.total_assets.shift(1))/2
    out["avg_equity"]=(out.total_equity + out.total_equity.shift(1))/2
    out["roa_pct"]=[pct(a,b) for a,b in zip(out.net_income,out.avg_assets)]
    out["roe_pct"]=[pct(a,b) for a,b in zip(out.net_income,out.avg_equity)]
    out["asset_turnover_x"]=[ratio(a,b) for a,b in zip(out.revenue,out.avg_assets)]
    return out

def markdown_summary(df: pd.DataFrame) -> str:
    show=["year","revenue","operating_profit","net_income","cfo","fcf","revenue_growth_pct","operating_margin_pct","net_margin_pct","current_ratio_pct","debt_to_equity_pct","roe_pct"]
    view=df[[c for c in show if c in df]].copy()
    for c in ["revenue","operating_profit","net_income","cfo","fcf"]:
        if c in view: view[c]=(view[c]/1e12).round(2) # KRW tn
    return "# SK hynix: DART consolidated annual analysis\n\nAmounts are KRW trillion; percentages are %.\n\n" + view.round(2).to_markdown(index=False)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--start-year",type=int,default=2022); p.add_argument("--end-year",type=int,default=2025)
    args=p.parse_args(); load_dotenv(ROOT/".env"); key=os.getenv("DART_API_KEY")
    if not key: raise SystemExit("DART_API_KEY is missing. Copy .env.example to .env and enter your Open DART key.")
    OUT.mkdir(exist_ok=True); raw=collect(key,range(args.start_year,args.end_year+1)); result=add_ratios(raw)
    result.to_csv(OUT/"sk_hynix_dart_financials_and_ratios.csv",index=False,encoding="utf-8-sig")
    (OUT/"sk_hynix_analysis.md").write_text(markdown_summary(result),encoding="utf-8")
    print("Created output/sk_hynix_dart_financials_and_ratios.csv and output/sk_hynix_analysis.md")
if __name__ == "__main__": main()
