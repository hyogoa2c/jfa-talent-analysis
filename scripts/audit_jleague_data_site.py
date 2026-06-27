from __future__ import annotations

import argparse
from pathlib import Path

from jfa_talent_analysis.sources.jleague_data_site import DEFAULT_PAGES, write_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit J.League Data Site pages before building collectors."
    )
    parser.add_argument(
        "--page",
        action="append",
        dest="pages",
        help="Page ID to audit, e.g. SFIX03. Can be repeated.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/source_audit/jleague_data_site_audit.json"),
        help="Output JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pages = args.pages or list(DEFAULT_PAGES)
    write_audit(args.output, pages)
    print(f"Wrote audit report for {len(pages)} pages to {args.output}")


if __name__ == "__main__":
    main()
