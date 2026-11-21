#!/usr/bin/env python3
"""Deterministic, position-specific evidence packets and readings for Atelier API v1.

The chart is always recomputed from four canonical Mothers. Historical records are selected by exact
figure/house scope; court selections deliberately do not borrow house rulings. No model is used here.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
from typing import Any

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import deep_read as D  # noqa: E402
from engine import ground as G  # noqa: E402

SCHEMA = "atelier.position_reading/1"
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII",
         "XIII", "XIV", "XV", "XVI"]
COURT_ROLES = {13: "witness_right", 14: "witness_left", 15: "judge", 16: "reconciler"}
HOUSES = yaml.safe_load((ROOT / "kb/houses.yaml").read_text())
HOUSE_NAMES = HOUSES.get("houses", {})
TOPICS: dict[str, int] = {str(k): int(v) for k, v in HOUSES["question_to_house"].items()}
LITERAL_NAME_GLOSSES = {
    "Via": "way", "Populus": "people or group", "Albus": "white", "Conjunctio": "joining",
    "Carcer": "enclosure or prison", "Puella": "girl", "Puer": "boy", "Caput Draconis": "dragon's head",
    "Cauda Draconis": "dragon's tail", "Fortuna Major": "greater fortune", "Fortuna Minor": "lesser fortune",
    "Rubeus": "red", "Acquisitio": "acquisition", "Amissio": "loss", "Tristitia": "sadness",
    "Laetitia": "joy",
}
TOPIC_LABELS = {
    "marriage": "marriage or partnership", "love_partner": "love or partnership",
    "wealth_money": "personal money and resources", "job_livelihood": "work and livelihood",
    "career_rank": "career and standing", "children": "children", "pregnancy": "pregnancy",
    "health": "health", "illness": "illness", "death": "death", "property_land": "property and land",
    "inheritance": "inheritance", "travel_journey": "travel", "studies": "study",
    "servants_workers": "workers and service", "lawsuit": "a lawsuit or contract",
    "enemies_obstruction": "obstacles or hidden enemies", "imprisonment_absent": "absence or confinement",
    "lost_things": "a lost item", "news_message": "news or a message", "friends": "friends and hopes",
    "animals": "animals", "accept_job": "accepting a job", "moving_house": "moving house",
}
# Conservative phrase matching. This suggests a key; it never confirms one on the reader's behalf.
TRIGGERS = {
    "marriage": ("marriage", "partner", "relationship", "spouse", "trust"),
    "love_partner": ("love", "romance", "dating"),
    "wealth_money": ("saving", "savings", "money", "wealth", "finance", "financial", "budget"),
    "job_livelihood": ("job", "work", "employment", "livelihood"),
    "career_rank": ("career", "promotion", "rank"),
    "property_land": ("moving house", "move house", "home", "property", "land", "house move"),
    "children": ("child", "children"), "pregnancy": ("pregnant", "pregnancy"),
    "health": ("health",), "illness": ("illness", "sick"), "travel_journey": ("travel", "journey", "trip"),
    "studies": ("study", "school", "education", "exam"), "inheritance": ("inheritance", "inherit"),
    "lawsuit": ("lawsuit", "court case", "legal dispute"), "friends": ("friend", "friendship"),
}


class InputError(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def validate_mothers(mothers: Any) -> list[str]:
    if not isinstance(mothers, list) or len(mothers) != 4:
        raise InputError("mothers", "must be an ordered list of exactly four canonical figure names")
    names = set(D.FIG)
    for i, name in enumerate(mothers):
        if not isinstance(name, str) or name not in names:
            raise InputError(f"mothers[{i}]", f"unknown canonical figure name: {name!r}")
    return list(mothers)


def _revisions() -> dict[str, str]:
    paths = [ROOT / "kb/voices.jsonl", ROOT / "kb/figures.yaml", ROOT / "kb/houses.yaml"]
    dataset = hashlib.sha256(b"".join(p.read_bytes() for p in paths)).hexdigest()
    engine_files = [ROOT / "engine/deep_read.py", pathlib.Path(__file__)]
    engine = hashlib.sha256(b"".join(p.read_bytes() for p in engine_files)).hexdigest()
    return {"engine_revision": engine[:16], "dataset_revision": dataset[:16]}


def chart(mothers: Any) -> dict:
    names = validate_mothers(mothers)
    computed = D.build(names)
    positions = []
    for i, pattern in enumerate(computed["houses"]):
        number = i + 1
        figure = D.fig(pattern)
        if number <= 12:
            role = "house"
            label = ((HOUSE_NAMES.get(number) or HOUSE_NAMES.get(str(number)) or {}).get("english")
                     or f"House {ROMAN[i]}")
        else:
            role = COURT_ROLES[number]
            label = {13: "Right witness", 14: "Left witness", 15: "Judge", 16: "Reconciler / Sentence"}[number]
        positions.append({"id": number, "label": label, "role": role,
                          "figure": figure, "pattern": list(pattern)})
    return {"mothers": names, "positions": positions, "judge": D.fig(computed["judge"]),
            "reconciler": D.fig(computed["sentence"]), "patterns": [p["pattern"] for p in positions]}


def route_question(question: str | None = None, confirmed_topic: str | None = None) -> dict:
    """Route conservatively. The chosen tile and topic focus are independent inputs/outputs."""
    if confirmed_topic is not None:
        if not isinstance(confirmed_topic, str) or confirmed_topic not in TOPICS:
            raise InputError("confirmed_topic", "unknown topic key")
        return {"state": "confirmed", "topic": confirmed_topic, "focus_house": TOPICS[confirmed_topic],
                "label": TOPIC_LABELS.get(confirmed_topic, confirmed_topic.replace("_", " ")),
                "candidates": []}
    if not question or not question.strip():
        return {"state": "general", "topic": None, "focus_house": None,
                "label": "general reading", "candidates": []}
    q = re.sub(r"\s+", " ", question.lower()).strip()
    found: list[str] = []
    for topic, phrases in TRIGGERS.items():
        for phrase in phrases:
            if phrase not in q:
                continue
            # Do not let a negated topic ('not a marriage question') win over the actual concern.
            before = q[max(0, q.find(phrase) - 32):q.find(phrase)]
            if re.search(r"\b(?:not|no|isn't|wasn't)\b[^.;!?]*$", before):
                continue
            found.append(topic)
            break
    found = list(dict.fromkeys(found))
    candidates = [{"topic": t, "label": TOPIC_LABELS.get(t, t.replace("_", " ")),
                   "focus_house": TOPICS.get(t)} for t in found]
    if not candidates:
        return {"state": "general", "topic": None, "focus_house": None,
                "label": "general reading", "candidates": [],
                "notice": "I could not confidently map that wording to a supported topic; choose a topic or continue generally."}
    if len(candidates) == 1:
        c = candidates[0]
        return {"state": "suggested", "topic": None, "focus_house": None,
                "label": "general reading", "suggestion": c, "candidates": candidates,
                "notice": "Suggested from your wording; confirm or change the focus."}
    return {"state": "needs_confirmation", "topic": None, "focus_house": None,
            "label": "choose a focus", "candidates": candidates,
            "notice": "More than one supported focus may fit. Choose one, or continue with a general reading."}


def _allowed(row: dict, rights_profile: str) -> bool:
    if row.get("disposition") == "never" or row.get("licence") != "A":
        return False
    if rights_profile == "public" and (row.get("cite_only") or row.get("disposition") != "full"):
        return False
    return rights_profile in ("research", "public")


def _evidence(row: dict, *, rights_profile: str, scope: str) -> dict:
    cite_only = bool(row.get("cite_only") or row.get("disposition") != "full")
    return {"id": row["id"], "scope": scope, "authority": row.get("authority"),
            "work": row.get("work"), "through": row.get("through"), "locator": row.get("locator"),
            "language": row.get("language"), "disposition": row.get("disposition"),
            "permissions": {"licence_bucket": row.get("licence"), "cite_only": cite_only,
                            "quote_allowed": not cite_only and rights_profile == "research" and bool(row.get("quote"))},
            "text": row.get("quote") if not cite_only and rights_profile == "research" else None,
            "gloss": None if cite_only else row.get("gloss")}


def _unresolved_comparisons(rows: list[dict], rights_profile: str) -> list[dict]:
    """Expose differing source passages as unresolved views, never infer conflict from polarity alone."""
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        if _allowed(row, rights_profile):
            family = row.get("family")
            if family in ("figure_attribute", "attribution_conflict") and row.get("attribute"):
                fig = str(row.get("figure") or "").replace("_", " ")
                group = f"figure_attribute:{fig}:{row['attribute']}"
            else:
                group = str(row.get("key") or row["id"])
            grouped.setdefault(group, []).append(row)
    comparisons = []
    for key, candidates in grouped.items():
        visible = []
        seen = set()
        for row in candidates:
            text = None if row.get("cite_only") or row.get("disposition") != "full" else (row.get("quote") or row.get("gloss"))
            authority = row.get("authority") or "Unknown authority"
            if text and (authority, text) not in seen:
                visible.append({"evidence_id": row["id"], "authority": authority, "text": text})
                seen.add((authority, text))
        if len({v["authority"] for v in visible}) > 1 and len({v["text"] for v in visible}) > 1:
            comparisons.append({"key": key, "status": "unresolved_comparison",
                                "note": "The available source passages differ; this is not an adjudicated disagreement.",
                                "source_views": visible})
    return comparisons


def _selected_evidence(book: G.VoiceBook, figure: str, position: int, rights_profile: str) -> tuple[list[dict], list[dict]]:
    records: list[dict] = []
    gaps: list[dict] = []
    if position <= 12:
        rows = book.key(f"figure_in_house:{figure}:{position}", reliable_only=False)
        usable = [r for r in rows if _allowed(r, rights_profile)]
        if usable:
            records.extend(_evidence(r, rights_profile=rights_profile, scope="selected_position") for r in usable)
        else:
            gaps.append({"position": position, "figure": figure,
                         "reason": "no permitted exact figure-in-house record is available"})
    else:
        # Court records are not house rulings. Hartmann's judge/cofigure rows additionally require an exact
        # cofigure and question-number condition; absent a reviewed mapping, withhold them rather than guess.
        gaps.append({"position": position, "figure": figure,
                     "reason": "no position-specific court ruling is established for this role and condition"})
    return records, gaps


def build_packet(mothers: Any, selected_position: Any, *, topic: str | None = None,
                 question: str | None = None, locale: str = "en", rights_profile: str = "research") -> dict:
    if isinstance(selected_position, bool) or not isinstance(selected_position, int) or not 1 <= selected_position <= 16:
        raise InputError("selected_position", "must be an integer from 1 through 16")
    if not isinstance(locale, str) or not locale.strip():
        raise InputError("locale", "must be a non-empty locale tag")
    locale = locale.strip()
    if rights_profile not in ("research", "public"):
        raise InputError("rights_profile", "unsupported server rights profile")
    if question is not None and (not isinstance(question, str) or len(question) > 2000):
        raise InputError("question", "must be text no longer than 2000 characters")
    if topic is not None and not isinstance(topic, str):
        raise InputError("confirmed_topic", "must be a supported topic key")
    board = chart(mothers)
    intent = route_question(question, topic)
    book = G.VoiceBook()
    # Full-chart audit is an internal fail-closed gate. The packet below is narrower than this reading.
    full_reading = G.assemble({"houses": {i + 1: p["figure"] for i, p in enumerate(board["positions"][:12])},
                               # ground.py's legacy names reverse Atelier's screen sides: its XIII is called left.
                               "witness_left": board["positions"][12]["figure"],
                               "witness_right": board["positions"][13]["figure"],
                               "judge": board["judge"], "reconciler": board["reconciler"]},
                              intent.get("topic"), book)
    audit = G.validate(full_reading, book)
    if not audit.get("ok"):
        raise RuntimeError("source audit failed; verified reading withheld")
    selected = board["positions"][selected_position - 1]
    figure = selected["figure"]
    evidence, gaps = _selected_evidence(book, figure, selected_position, rights_profile)
    comparison_rows = []
    if selected_position <= 12:
        comparison_rows.extend(book.key(f"figure_in_house:{figure}:{selected_position}", reliable_only=False))
    related_position = None
    if intent.get("focus_house") and intent["focus_house"] != selected_position:
        related = board["positions"][intent["focus_house"] - 1]
        related_rows = book.key(f"figure_in_house:{related['figure']}:{intent['focus_house']}", reliable_only=False)
        comparison_rows.extend(related_rows)
        related_position = {"id": related["id"], "figure": related["figure"], "role": "related_position",
                            "evidence_ids": []}
        for row in related_rows:
            if _allowed(row, rights_profile):
                evidence.append(_evidence(row, rights_profile=rights_profile, scope="related_position"))
                related_position["evidence_ids"].append(row["id"])
        if not related_position["evidence_ids"]:
            gaps.append({"position": related["id"], "figure": related["figure"],
                         "reason": "no permitted exact record for the question focus; related position only"})
    # General figure facts are kept separate from positional rulings.
    definition_rows = []
    for attr in ("quality", "element", "planet", "motion", "gender"):
        definition_rows.extend(r for r in book.key(f"figure_attribute:{figure}:{attr}", reliable_only=False)
                              if _allowed(r, rights_profile))
    naming_figures = ("Puer", "Puella") if figure in ("Puer", "Puella") else (figure,)
    for naming_figure in naming_figures:
        definition_rows.extend(r for r in book.key(f"naming:{naming_figure}", reliable_only=False)
                               if _allowed(r, rights_profile))
    # The KB records explicit planetary attribution conflicts under a separate family/key; retain both
    # named authorities rather than silently preferring the general attribute row.
    for row in book.rows:
        if (row.get("family") == "attribution_conflict"
                and str(row.get("figure") or "").replace("_", " ") == figure
                and row.get("attribute") == "planet" and _allowed(row, rights_profile)):
            definition_rows.append(row)
    for row in definition_rows:
        evidence.append(_evidence(row, rights_profile=rights_profile, scope="general_figure"))
    comparison_rows.extend(definition_rows)
    unresolved_comparisons = _unresolved_comparisons(comparison_rows, rights_profile)
    # De-duplicate IDs while keeping a record's distinct scopes visible.
    dedup: dict[str, dict] = {}
    for item in evidence:
        old = dedup.get(item["id"])
        if old:
            if old["scope"] != item["scope"]:
                old["scope"] = "multiple_scopes"
        else:
            dedup[item["id"]] = item
    evidence = list(dedup.values())
    definition_ids = [e["id"] for e in evidence if e["scope"] in ("general_figure", "multiple_scopes")]
    position_ids = [e["id"] for e in evidence if e["scope"] in ("selected_position", "multiple_scopes")]
    sections = [{"key": "figure_alone", "kind": "calculation", "text":
                 f"{figure} is the canonical name for the pattern {selected['pattern']} in this chart convention.",
                 "evidence_ids": []},
                {"key": "literal_name_gloss", "kind": "editorial_gloss",
                 "text": f"The literal name gloss is ‘{LITERAL_NAME_GLOSSES.get(figure, 'not available')}’; this is not a source quotation or a divinatory verdict.",
                 "evidence_ids": []}]
    if definition_ids:
        attrs = []
        for e in evidence:
            if e["id"] in definition_ids:
                v = book.lookup(e["id"])
                if v and v.get("attribute") and v.get("value") is not None:
                    attrs.append(f"{v['attribute']}: {v['value']}")
        sections.append({"key": "general_definition", "kind": "attributed_claim",
                         "text": f"The available figure notes record {', '.join(dict.fromkeys(attrs))}.",
                         "evidence_ids": definition_ids})
    else:
        sections.append({"key": "general_definition", "kind": "editorial_gloss",
                         "text": "No permitted general attribute record is available for this figure.", "evidence_ids": []})
    if position_ids:
        sections.append({"key": "in_this_position", "kind": "attributed_claim",
                         "text": f"The evidence packet contains exact source record(s) for {figure} at position {selected_position} ({selected['label']}).",
                         "evidence_ids": position_ids})
    else:
        sections.append({"key": "in_this_position", "kind": "editorial_gloss",
                         "text": f"No permitted exact ruling for {figure} at position {selected_position} ({selected['label']}) is available.",
                         "evidence_ids": []})
    if intent.get("state") == "confirmed":
        if selected_position <= 12:
            quality = D.FIG.get(figure, {}).get("quality") or "unrecorded"
            if selected_position == 7 and figure == "Conjunctio" and intent["topic"] == "marriage":
                application = ("In this partnership focus, Conjunctio's literal joining image invites you to ask where both people already agree, and where either may be assuming agreement without saying so. The chart cannot tell us what your partner privately thinks.")
            elif selected_position == 7 and figure == "Conjunctio" and intent["topic"] == "wealth_money":
                application = ("Your focus is personal resources in house II; this tile is VII, not the focus house, and remains the position of agreement with another party. Conjunctio's joining image can prompt a clear conversation about contributions, expectations and terms; it does not show that combining savings is financially safe.")
            elif intent["focus_house"] == selected_position:
                application = (f"You chose {intent['label']} as the focus. In {selected['label']}, consider what the figure's recorded {quality} quality invites you to check or clarify about that concern. This is a reflective prompt, not a prediction or proof.")
            else:
                application = (f"You chose {intent['label']} (focus house {intent['focus_house']}); this tile is {selected['label']}, not the focus house. Keep the positions distinct. Consider how its recorded {quality} quality might be relevant, without treating it as an answer about the focus house.")
        else:
            application = (f"You chose {intent['label']}; this tile is the {selected['label']} court role, which summarizes chart structure rather than acting as that topic's house. It cannot be substituted for a position-specific ruling.")
        sections.append({"key": "for_your_question", "kind": "tentative_application", "text": application,
                         "evidence_ids": []})
    else:
        sections.append({"key": "for_your_question", "kind": "tentative_application",
                         "text": "No topic has been confirmed. Continue with this general reading or choose a focus; the chart will not be recast.",
                         "evidence_ids": []})
    if intent.get("state") == "needs_confirmation":
        sections.append({"key": "clarification", "kind": "editorial_gloss", "text": intent["notice"], "evidence_ids": []})
    pattern_convention = None
    if figure in ("Puer", "Puella"):
        canonical = {"Puer": list(D.FIG["Puer"]["pattern"]), "Puella": list(D.FIG["Puella"]["pattern"])}
        alternate = {"Puer": canonical["Puella"], "Puella": canonical["Puer"]}
        naming_ids = [f"naming:{name}:calatarama" for name in ("Puer", "Puella") if book.lookup(f"naming:{name}:calatarama")]
        pattern_convention = {"status": "documented_naming_conflict",
                              "canonical_convention": {"name": "Britannica plate / Golden Dawn", "patterns": canonical},
                              "alternate_convention": {"name": "Digital Ambler binary table / Skinner line", "patterns": alternate},
                              "note": "This reading uses the canonical pattern labels; the alternate convention swaps only the Puer and Puella names, not the arithmetic. Verify the tradition you follow.",
                              "evidence_ids": naming_ids}
        sections.append({"key": "pattern_convention", "kind": "editorial_gloss",
                         "text": pattern_convention["note"], "evidence_ids": naming_ids})
    return {"schema": SCHEMA, "status": intent["state"], "mode_used": "grounded", "position": selected,
            "intent": intent, "related_position": related_position, "pattern_convention": pattern_convention,
            "sections": sections,
            "evidence": evidence, "gaps": gaps, "disagreements": unresolved_comparisons,
            "limits": ["This is a symbolic reading, not evidence about another person's private thoughts or a guaranteed outcome.",
                       "Only English evidence and editorial text are currently supported."],
            "locale": locale, "available_locale": "en",
            "fallback_reason": None if re.fullmatch(r"en(?:-[A-Za-z0-9]{2,8})*", locale, re.I)
            else "requested locale is not supported; returned English",
            "audit_status": {"ok": True, "claims": audit["claims"], "cited_voice_ids": audit["cited"]},
            "revisions": _revisions(), "model_called": False}


def render_position(mothers: Any, selected_position: Any, *, topic: str | None = None,
                    question: str | None = None, locale: str = "en", rights_profile: str = "research") -> dict:
    """Public service function. A question can suggest but never silently confirm a topic."""
    packet = build_packet(mothers, selected_position, topic=topic, question=question,
                          locale=locale, rights_profile=rights_profile)
    if packet["intent"]["state"] == "suggested":
        # The position reading remains usable while the client confirms the optional topic suggestion.
        packet["sections"][-1]["text"] = "A topic was suggested but not confirmed. Confirm or change the focus, or continue generally. The chart will not be recast."
    return packet
