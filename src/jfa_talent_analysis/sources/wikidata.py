from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request

from jfa_talent_analysis.sources.retry import request_with_retry

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "jfa-talent-analysis/0.1 Wikidata source audit"
KATAKANA_START = "\u30a0"
KATAKANA_END = "\u30ff"

SUMMARY_COLUMNS = [
    "wikidata_person_count",
    "wikidata_person_ids",
    "wikidata_team_count",
    "wikidata_countries",
    "wikidata_foreign_team_count",
    "wikidata_foreign_teams",
]

AUDIT_COLUMNS = [
    "audit_status",
    "manual_review_reason",
]


@dataclass(frozen=True)
class WikidataTeamStint:
    person_uri: str
    person_label: str
    team_label: str
    country_label: str
    start: str
    end: str


def name_label_variants(name_ja: str, name_en: str) -> list[tuple[str, str]]:
    variants: list[tuple[str, str]] = []
    if name_ja:
        normalized = " ".join(name_ja.split())
        variants.append((normalized, "ja"))
        no_space = normalized.replace(" ", "")
        if no_space != normalized:
            variants.append((no_space, "ja"))
    if name_en:
        normalized_en = " ".join(name_en.split())
        variants.append((normalized_en, "en"))
        title_en = normalized_en.title()
        if title_en != normalized_en:
            variants.append((title_en, "en"))
    return list(dict.fromkeys(variants))


def build_player_team_query(name_ja: str, name_en: str) -> str:
    values = "\n".join(
        f'    "{escape_sparql_string(label)}"@{language}'
        for label, language in name_label_variants(name_ja, name_en)
    )
    return f"""
SELECT ?person ?personLabel ?team ?teamLabel ?country ?countryLabel ?start ?end WHERE {{
  VALUES ?targetLabel {{
{values}
  }}
  ?person rdfs:label ?targetLabel.
  OPTIONAL {{
    ?person p:P54 ?teamStatement.
    ?teamStatement ps:P54 ?team.
    OPTIONAL {{ ?teamStatement pq:P580 ?start. }}
    OPTIONAL {{ ?teamStatement pq:P582 ?end. }}
    OPTIONAL {{ ?team wdt:P17 ?country. }}
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en". }}
}}
ORDER BY ?person ?start ?teamLabel
""".strip()


def fetch_player_team_stints(name_ja: str, name_en: str, timeout: int = 30) -> list[WikidataTeamStint]:
    query = build_player_team_query(name_ja, name_en)
    payload = urlencode({"query": query, "format": "json"}).encode()
    request = Request(
        SPARQL_ENDPOINT,
        data=payload,
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        },
    )
    _, _, content = request_with_retry(request, timeout=timeout)
    return parse_player_team_stints(json.loads(content))


def parse_player_team_stints(data: dict) -> list[WikidataTeamStint]:
    rows: list[WikidataTeamStint] = []
    for binding in data.get("results", {}).get("bindings", []):
        rows.append(
            WikidataTeamStint(
                person_uri=binding.get("person", {}).get("value", ""),
                person_label=binding.get("personLabel", {}).get("value", ""),
                team_label=binding.get("teamLabel", {}).get("value", ""),
                country_label=binding.get("countryLabel", {}).get("value", ""),
                start=binding.get("start", {}).get("value", ""),
                end=binding.get("end", {}).get("value", ""),
            )
        )
    return rows


def summarize_stints(stints: list[WikidataTeamStint]) -> dict[str, str]:
    person_uris = sorted({stint.person_uri for stint in stints if stint.person_uri})
    foreign_teams = sorted(
        {
            f"{stint.team_label} ({stint.country_label})"
            for stint in stints
            if stint.team_label and stint.country_label and stint.country_label != "日本"
        }
    )
    teams = sorted({stint.team_label for stint in stints if stint.team_label})
    countries = sorted({stint.country_label for stint in stints if stint.country_label})
    return {
        "wikidata_person_count": str(len(person_uris)),
        "wikidata_person_ids": "|".join(uri.rsplit("/", 1)[-1] for uri in person_uris),
        "wikidata_team_count": str(len(teams)),
        "wikidata_countries": "|".join(countries),
        "wikidata_foreign_team_count": str(len(foreign_teams)),
        "wikidata_foreign_teams": "|".join(foreign_teams),
    }


def classify_wikidata_audit(name_ja: str, summary: dict[str, str]) -> dict[str, str]:
    person_count = int(summary.get("wikidata_person_count", "0") or "0")
    foreign_team_count = int(summary.get("wikidata_foreign_team_count", "0") or "0")

    if person_count == 0:
        return {
            "audit_status": "needs_manual_review",
            "manual_review_reason": review_reason("no_wikidata_person_match", name_ja),
        }
    if person_count > 1:
        return {
            "audit_status": "needs_manual_review",
            "manual_review_reason": review_reason("multiple_wikidata_person_matches", name_ja),
        }
    if foreign_team_count > 0:
        return {
            "audit_status": "candidate_foreign_stint",
            "manual_review_reason": "",
        }
    if contains_katakana(name_ja):
        return {
            "audit_status": "needs_manual_review",
            "manual_review_reason": "katakana_name_without_wikidata_foreign_club_hint",
        }
    return {
        "audit_status": "no_wikidata_foreign_stint",
        "manual_review_reason": "",
    }


def review_reason(base_reason: str, name_ja: str) -> str:
    if contains_katakana(name_ja):
        return f"{base_reason}|katakana_name"
    return base_reason


def contains_katakana(value: str) -> bool:
    return any(KATAKANA_START <= char <= KATAKANA_END for char in value)


def escape_sparql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
