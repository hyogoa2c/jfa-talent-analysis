from __future__ import annotations

import argparse
import csv
import time
from collections import defaultdict
from pathlib import Path

from jfa_talent_analysis.club_history_extraction import parse_club_history
from jfa_talent_analysis.coach_network import (
    is_gap_placeholder,
    normalize_institution_name,
    years_overlap,
)
from jfa_talent_analysis.sources.wikipedia import fetch_wikipedia_extract

EDGE_COLUMNS = [
    "edge_type",  # mentored_by / trained_at / moved_between
    "coach_name",  # the coach this edge is ABOUT (the "student"/mover)
    "related_coach",  # mentor for mentored_by; blank otherwise
    "institution",  # normalized researched institution the edge runs through
    "from_year",
    "to_year",
    "evidence",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the coach-lineage graph from data already collected: parse "
            "each coach's own playing career out of their (verified) cached "
            "Wikipedia article, match stints against the 86 researched "
            "institutions, and where the stint years overlap another researched "
            "coach's tenure there, emit a mentored_by edge — 'coach A was "
            "developed under coach B.' Alumni links without usable years become "
            "weaker trained_at edges; coaches holding tenures at 2+ researched "
            "institutions become moved_between edges. Mentor matching is bounded "
            "by tenure-table era coverage (mostly 2000+, with pre-2000 reigns "
            "only where batches recorded true start years), so missing edges "
            "mean 'not covered', not 'no relationship'."
        )
    )
    parser.add_argument(
        "--attributes",
        type=Path,
        default=Path("data/interim/coach_network/coach_attributes.csv"),
    )
    parser.add_argument(
        "--extracts",
        type=Path,
        default=Path("data/interim/coach_network/coach_wikipedia_extracts.csv"),
    )
    parser.add_argument(
        "--tenures",
        type=Path,
        default=Path("data/interim/coach_network/coach_tenures_canonical.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/coach_network/coach_lineage_edges.csv"),
    )
    parser.add_argument("--sleep", type=float, default=1.0)
    return parser.parse_args()


def load_verified_extracts(
    attributes_path: Path, extracts_path: Path, sleep: float
) -> dict[str, str]:
    """Extract text per coach, but ONLY when we know it's the right person:
    the cached title must equal the corrected title from the attribute
    research; for the handful where the cache holds a wrong page but the
    correct title is known, fetch the correct page now."""
    csv.field_size_limit(10_000_000)
    with extracts_path.open(encoding="utf-8-sig", newline="") as file:
        cache = {row["coach_name"]: row for row in csv.DictReader(file)}
    with attributes_path.open(encoding="utf-8-sig", newline="") as file:
        attributes = list(csv.DictReader(file))

    verified: dict[str, str] = {}
    refetched = 0
    for row in attributes:
        corrected = row["corrected_wikipedia_title"]
        if not corrected:
            continue
        cached = cache.get(row["coach_name"])
        if cached and cached["wikipedia_title"] == corrected:
            verified[row["coach_name"]] = cached["full_extract"]
        else:
            extract = fetch_wikipedia_extract(corrected)
            time.sleep(sleep)
            refetched += 1
            if extract:
                verified[row["coach_name"]] = extract
    print(f"verified extracts: {len(verified)} coaches ({refetched} refetched by corrected title)")
    return verified


def main() -> None:
    args = parse_args()

    with args.tenures.open(encoding="utf-8-sig", newline="") as file:
        tenure_rows = [
            row
            for row in csv.DictReader(file)
            if not is_gap_placeholder(row["coach_name"], row["role_type"])
        ]
    researched = {row["normalized_institution"] for row in tenure_rows}
    tenures_by_institution: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in tenure_rows:
        tenures_by_institution[row["normalized_institution"]].append(row)

    extracts = load_verified_extracts(args.attributes, args.extracts, args.sleep)

    edges: list[dict[str, str]] = []

    # mentored_by / trained_at: from each coach's own playing stints
    for coach_name, extract in extracts.items():
        for stint in parse_club_history(extract):
            normalized = normalize_institution_name(stint.institution)
            if normalized not in researched:
                continue
            stint_from, stint_to = stint.from_year, stint.to_year
            mentors = []
            if stint_from is not None or stint_to is not None:
                for tenure in tenures_by_institution[normalized]:
                    if tenure["coach_name"] == coach_name:
                        continue
                    tenure_from = int(tenure["from_year"]) if tenure["from_year"] else None
                    tenure_to = int(tenure["to_year"]) if tenure["to_year"] else None
                    # a yearless tenure bound pair would overlap everything;
                    # require the tenure itself to carry at least one bound
                    if tenure_from is None and tenure_to is None:
                        continue
                    if years_overlap(stint_from, stint_to, tenure_from, tenure_to):
                        mentors.append(tenure)
            if mentors:
                for tenure in mentors:
                    edges.append(
                        {
                            "edge_type": "mentored_by",
                            "coach_name": coach_name,
                            "related_coach": tenure["coach_name"],
                            "institution": normalized,
                            "from_year": str(stint_from or ""),
                            "to_year": str(stint_to or ""),
                            "evidence": (
                                f"played at {normalized} {stint_from}-{stint_to}; "
                                f"{tenure['coach_name']} was {tenure['role_type']} "
                                f"{tenure['from_year']}-{tenure['to_year']}"
                            ),
                        }
                    )
            else:
                edges.append(
                    {
                        "edge_type": "trained_at",
                        "coach_name": coach_name,
                        "related_coach": "",
                        "institution": normalized,
                        "from_year": str(stint_from or ""),
                        "to_year": str(stint_to or ""),
                        "evidence": f"played at {normalized} (no researched tenure overlaps)",
                    }
                )

    # moved_between: same coach holding tenures at 2+ researched institutions
    institutions_by_coach: dict[str, set[str]] = defaultdict(set)
    for row in tenure_rows:
        institutions_by_coach[row["coach_name"]].add(row["normalized_institution"])
    for coach_name, institutions in sorted(institutions_by_coach.items()):
        if len(institutions) < 2:
            continue
        ordered = sorted(institutions)
        for a, b in zip(ordered, ordered[1:], strict=False):
            edges.append(
                {
                    "edge_type": "moved_between",
                    "coach_name": coach_name,
                    "related_coach": "",
                    "institution": f"{a}|{b}",
                    "from_year": "",
                    "to_year": "",
                    "evidence": f"held researched tenures at {len(institutions)} institutions",
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=EDGE_COLUMNS)
        writer.writeheader()
        writer.writerows(edges)

    from collections import Counter

    by_type = Counter(edge["edge_type"] for edge in edges)
    print(f"edges written: {len(edges)}  {dict(by_type)}")
    mentors = Counter(
        edge["related_coach"] for edge in edges if edge["edge_type"] == "mentored_by"
    )
    print("top mentors (most researched coaches developed under them):")
    for name, count in mentors.most_common(10):
        print(f"  {count:2d}  {name}")
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
