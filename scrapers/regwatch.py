

import json, hashlib, time, sys, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scrapers.taiwan_cscra import TaiwanCSCRA
from scrapers.eu_eurlex import EUEurLex
from scrapers.cha_toxic_list import CHAToxicListScraper

from scrapers.us_cfr40 import USCFRTitle40
from scrapers.us_tsca_inventory import USTscaInventory
from scrapers.eu_inventory import EUEchaSelenium


SNAPSHOT = Path("outputs/snapshots.jsonl")
STATE = Path("outputs/latest_hash.json")
SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)

# Per-regulation snapshot directory (each slug has its own JSONL)
PER_SLUG_DIR = Path("outputs/by_slug")
PER_SLUG_DIR.mkdir(parents=True, exist_ok=True)

def iso_now():
    return datetime.now(timezone.utc).isoformat()

def taipei_now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()

def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def record_per_slug(entry: dict, slug: str):

    fetched_time = entry.get("fetched_time")
    date_prefix = ""
    if fetched_time:
        # 只取年月日
        date_digits = "".join([c for c in fetched_time if c.isdigit()])
        if len(date_digits) >= 8:
            date_prefix = f"{date_digits[:8]}_"
        else:
            date_prefix = f"{date_digits}_"
    path = PER_SLUG_DIR / f"{date_prefix}{slug}.json"
    
    # Create source dataset mapping
    source_dataset_mapping = {
        "tw_cscra_moenv": "tw_regulation",
        "tw_inventory": "tw_inventory",
        "eu_reach_eurlex": "eu_regulation",
        "us_cfr40": "us_regulation",
        "us_tsca_inventory": "us_inventory",
        "eu_echa_inventory": "eu_inventory",
        "eu_echa_selenium": "eu_inventory"
    }
    
    # Get the source dataset name
    source_dataset = source_dataset_mapping.get(slug, slug)
    
    # Create the main data structure with metadata
    fetched_time = taipei_now()
    
    # If the entry contains detailed per-section records, write as JSON object with array
    per_sections = entry.get("per_section_records")
    if isinstance(per_sections, list) and per_sections:
        records = []
        for rec in per_sections:
            if slug == "us_tsca_inventory":
                # For TSCA Inventory, preserve original field names (e.g., CASRN, ChemName)
                out = dict(rec)
                # Remove any existing fetched_time from individual records
                out.pop("fetched_time", None)
            elif slug == "eu_echa_inventory" or slug == "eu_echa_selenium":
                # For EU ECHA Inventory, preserve chemical substance field names
                out = dict(rec)
                # Remove any existing fetched_time from individual records
                out.pop("fetched_time", None)
            elif slug == "tw_inventory":
                # For Taiwan CHA toxic chemicals, use the enhanced format with chemical-specific fields
                out = dict(rec)
                # Remove any existing fetched_time from individual records
                out.pop("fetched_time", None)
            else:
                # Default format for other regulations (EU REACH, Taiwan CSCRA, US CFR)
                out = {
                    "part": rec.get("part", ""),
                    "section_citation": rec.get("section_citation", ""),
                    "section_heading": rec.get("section_heading", ""),
                    "text": rec.get("text", ""),
                    "length": rec.get("length", 0),
                }
            records.append(out)
        
        # Create final structure with metadata at top level
        final_data = {
            "source_dataset": source_dataset,
            "fetched_time": fetched_time,
            "records": records
        }
        
        # Write as JSON object
        with path.open("w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        return
    
    # Otherwise, write single record as JSON object with metadata
    entry_with_source = dict(entry)
    entry_with_source["source_dataset"] = source_dataset
    entry_with_source["fetched_time"] = fetched_time
    with path.open("w", encoding="utf-8") as f:
        json.dump(entry_with_source, f, ensure_ascii=False, indent=2)

# Override main with a simplified job set (EU REACH, TW CSCRA, US LCSA only)
def main():
    jobs = []

    jobs.append(TaiwanCSCRA(
        name="毒性及關注化學物質管理法",
        url="https://oaout.moenv.gov.tw/law/LawContent.aspx?id=FL015852#lawmenu",
        jurisdiction="TW", 
        slug="tw_cscra_moenv"
    ))

    jobs.append(CHAToxicListScraper(
        name="環境部化學物質管理署毒性及關注化學物質清單",
        url="https://www.cha.gov.tw/sp-toch-list-1.html",
        jurisdiction="TW",
        slug="tw_inventory"
    ))

    jobs.append(EUEurLex(
        name="REACH Regulation (EC) No 1907/2006",
        url="file://Consolidated TEXT_ 32006R1907 — EN — 01.09.2025.html",
        jurisdiction="EU",
        slug="eu_reach_eurlex"
    ))


    jobs.append(USCFRTitle40(
        name="CFR Title 40 - Protection of Environment",
        url="https://www.govinfo.gov/app/collection/cfr/2024/",
        jurisdiction="US",
        slug="us_cfr40"
    ))

    # TSCA Inventory checker 

    inv_csv = "https://www.epa.gov/tsca-inventory/how-access-tsca-inventory#Download%20the%20non-confidential%20TSCA%20Inventory"
    qry_csv = str(Path('inputs') / 'chemicals.csv')
    jobs.append(USTscaInventory(
        name="TSCA Inventory (Local CSV lookup)",
        jurisdiction="US",
        slug="us_tsca_inventory",
        inventory_csv=inv_csv,
        queries_csv=qry_csv,
        dump_all=True
    ))

    # EU ECHA EC Inventory checker using Selenium
    jobs.append(EUEchaSelenium(
        name="EU ECHA EC Inventory (Selenium)",
        jurisdiction="EU",
        slug="eu_echa_inventory",
        max_records=10100
    ))

    state = load_state()
    changed = []
    results = []

    for job in jobs:
        try:
            meta = job.fetch()
            entry = {
                "jurisdiction": job.jurisdiction,
                "regulation": job.name,
                "source_url": job.url,
                "detected_version_date": meta.get("version_date"),
                "detected_title": meta.get("title"),
                "detected_notes": meta.get("notes"),
                "fetched_time": taipei_now(),
                "slug": job.slug,
                "content_sha256": meta.get("sha256"),
                "law_code": meta.get("law_code"),
                "regulation_number": meta.get("regulation_number"),
                "category": meta.get("category"),
                "full_content": meta.get("full_content"),
                "structured_sections": meta.get("structured_sections"),
                "per_section_records": meta.get("per_section_records"),
                "content_length": meta.get("content_length", 0),
                "raw_excerpt": meta.get("excerpt")
            }
            record_per_slug(entry, job.slug)
            results.append(entry)

            prev_hash = state.get(job.slug, "")
            if prev_hash != entry["content_sha256"]:
                state[job.slug] = entry["content_sha256"]
                changed.append(entry)

            time.sleep(1.0)
        except Exception as e:
            err_entry = {
                "jurisdiction": job.jurisdiction,
                "regulation": job.name,
                "source_url": job.url,
                "error": str(e),
                "fetched_time": taipei_now(),
                "slug": job.slug
            }
            record_per_slug(err_entry, job.slug)
            continue

    save_state(state)

    if changed:
        lines = ["法規內容發生變更："]
        for c in changed:
            lines.append(f"- [{c['jurisdiction']}] {c['regulation']} | {c['source_url']} | 版本日期: {c.get('detected_version_date') or 'N/A'} | 時間: {c['fetched_time']}")
        msg = "\n".join(lines)
        print(msg)  # Output change notification to console

    print(json.dumps(
        {"run_finished_at": taipei_now(), "items": results, "changed_count": len(changed)},
        ensure_ascii=False, indent=2
    ))


if __name__ == "__main__":
    sys.exit(main())
