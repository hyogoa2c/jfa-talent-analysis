"""Collect pre-2014 J.League appearance records from the static Shift_JIS archive.

Source: https://data.j-league.or.jp/SS/jpn/team/index.html ("過去の試合記録"), covering
1999-2013 season x team x competition-stage pages. See
docs/source_audit_pre2014_appearances.md for page-format details and known anomalies, and
docs/research_plan_phase1.md §12 for how this backfill track fits the Phase 1 plan.

Fetching is strictly sequential (no parallelism) with a configurable sleep between requests,
per the politeness constraints noted in the audit doc (this site has caused a rate-limit
incident before). Raw HTML for every fetched page is cached to --output-dir/html_cache/ so a
re-run skips already-fetched pages entirely -- both to be polite to the source and to make
interrupted runs resumable. Output is one CSV per season year:
appearance_records_pre2014_<year>.csv.

Identity resolution to SFIX03 player IDs and competition_label classification (league vs.
cup) are explicitly OUT OF SCOPE here -- this script only produces raw parsed rows.
"""

from __future__ import annotations

import argparse
import csv
import time
from collections import defaultdict
from pathlib import Path

from jfa_talent_analysis.sources.pre2014_appearances import (
    ENCODING,
    AppearanceRecord,
    IndexLink,
    fetch_index_html,
    fetch_page_html,
    parse_appearance_page,
    parse_index,
    write_appearance_records_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect pre-2014 (1999-2013) J.League appearance records."
    )
    parser.add_argument("--start-year", type=int, default=1999)
    parser.add_argument("--end-year", type=int, default=2013)
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Delay in seconds between live page fetches (not applied to cache hits).",
    )
    parser.add_argument(
        "--limit-pages",
        type=int,
        default=None,
        help="Cap the total number of pages processed this run, for smoke tests.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/interim/pre2014"),
        help="Directory for per-year CSVs, the HTML cache, and the failure log.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir: Path = args.output_dir
    cache_dir = output_dir / "html_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    index_html = load_index_html(cache_dir, sleep_seconds=args.sleep)
    links = [
        link
        for link in parse_index(index_html)
        if args.start_year <= link.year <= args.end_year
    ]
    links.sort(key=lambda link: (link.year, link.filename))

    if args.limit_pages is not None:
        links = links[: args.limit_pages]

    print(
        f"years={args.start_year}-{args.end_year} pages_to_process={len(links)}",
        flush=True,
    )

    records_by_year: dict[int, list[AppearanceRecord]] = defaultdict(list)
    failures: list[tuple[str, str]] = []
    fetched = 0
    cached = 0

    for index, link in enumerate(links, start=1):
        html, was_cached = load_page_html(link, cache_dir)
        if html is None:
            failures.append((link.filename, "fetch failed after retries"))
            continue
        if was_cached:
            cached += 1
        else:
            fetched += 1
            if args.sleep > 0:
                time.sleep(args.sleep)

        try:
            page_records = parse_appearance_page(
                html, season_year=link.year, source_url=link.url
            )
        except ValueError as exc:
            failures.append((link.filename, str(exc)))
            continue

        if not page_records:
            failures.append((link.filename, "parsed zero player rows"))
        records_by_year[link.year].extend(page_records)

        if index % 20 == 0 or index == len(links):
            print(
                f"[{index}/{len(links)}] fetched={fetched} cached={cached} "
                f"failed={len(failures)}",
                flush=True,
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    for year in sorted(records_by_year):
        out_path = output_dir / f"appearance_records_pre2014_{year}.csv"
        write_appearance_records_csv(out_path, records_by_year[year])
        print(f"wrote {len(records_by_year[year])} rows to {out_path}", flush=True)

    if failures:
        write_failures_csv(output_dir / "collection_failures.csv", failures)
        print(f"{len(failures)} page(s) failed or produced zero rows -- see "
              f"{output_dir / 'collection_failures.csv'}", flush=True)

    print(f"done fetched={fetched} cached={cached} failed={len(failures)}", flush=True)


def load_index_html(cache_dir: Path, *, sleep_seconds: float) -> str:
    cache_path = cache_dir / "index.html"
    if cache_path.exists():
        return cache_path.read_bytes().decode(ENCODING)
    html = fetch_index_html()
    cache_path.write_bytes(html.encode(ENCODING))
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    return html


def load_page_html(link: IndexLink, cache_dir: Path) -> tuple[str | None, bool]:
    cache_path = cache_dir / link.filename
    if cache_path.exists():
        return cache_path.read_bytes().decode(ENCODING), True
    try:
        html = fetch_page_html(link.url)
    except Exception:
        return None, False
    cache_path.write_bytes(html.encode(ENCODING))
    return html, False


def write_failures_csv(path: Path, failures: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["filename", "reason"])
        writer.writerows(failures)


if __name__ == "__main__":
    main()
