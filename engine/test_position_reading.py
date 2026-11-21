#!/usr/bin/env python3
"""Tests for the deterministic Atelier position-reading contract. Run: python3 engine/test_position_reading.py"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import position_reading as PR  # noqa: E402
from engine import ground as G  # noqa: E402

FIXTURE = json.loads((ROOT / "data/fixtures/atelier_position_v1.json").read_text())
POLICY_FIXTURE = json.loads((ROOT / "data/fixtures/atelier_evidence_policy_v1.json").read_text())
MOTHERS = FIXTURE["mothers"]


class PositionReadingTests(unittest.TestCase):
    def test_fixture_has_same_all_sixteen_positions_as_python_reference(self):
        board = PR.chart(MOTHERS)
        self.assertEqual([p["figure"] for p in board["positions"]], FIXTURE["expected_figures"])
        self.assertEqual([p["pattern"] for p in board["positions"]], FIXTURE["expected_patterns"])
        self.assertEqual(board["judge"], FIXTURE["expected"]["judge"])
        self.assertEqual(board["reconciler"], FIXTURE["expected"]["reconciler"])
        self.assertEqual(board["positions"][12]["role"], "witness_right")
        self.assertEqual(board["positions"][13]["role"], "witness_left")

    def test_same_fixture_in_both_javascript_engines(self):
        script = r'''const fs=require('fs'); const fixture=JSON.parse(fs.readFileSync(process.argv[1]));
for (const path of ['app/engine.js','web/engine.js']) {
 const E=require('./'+path); const c=E.cast(fixture.mothers);
 if (JSON.stringify(c.names)!==JSON.stringify(fixture.expected_figures)) throw Error(path+' figure mismatch');
 if (JSON.stringify(c.houses)!==JSON.stringify(fixture.expected_patterns)) throw Error(path+' pattern mismatch');
 for (const [name,pattern] of Object.entries({Puer:[1,2,1,1],Puella:[1,1,2,1]})) {
  const one=E.cast([name,name,name,name]);
  if (JSON.stringify(one.mothers[0])!==JSON.stringify(pattern) || one.names[0]!==name) throw Error(path+' '+name+' canonical mapping mismatch');
 }
}'''
        subprocess.run(["node", "-e", script, str(ROOT / "data/fixtures/atelier_position_v1.json")],
                       cwd=ROOT, check=True, capture_output=True, text=True)

    def test_explicit_figures_canonical_puer_puella_convention_matches_shield(self):
        expected = {"Puer": [1, 2, 1, 1], "Puella": [1, 1, 2, 1]}
        self.assertEqual({n: PR.D.FIG[n]["pattern"] for n in expected}, expected)
        self.assertEqual({n: __import__("tools.shield", fromlist=["FIGURES"]).FIGURES[n] for n in expected}, expected)
        self.assertEqual(PR.D.fig(expected["Puer"]), "Puer")
        self.assertEqual(PR.D.fig(expected["Puella"]), "Puella")
        reading = PR.render_position(["Puer"] * 4, 1)
        conventions = reading["pattern_convention"]
        self.assertEqual(conventions["canonical_convention"]["patterns"], expected)
        self.assertEqual(conventions["alternate_convention"]["patterns"],
                         {"Puer": expected["Puella"], "Puella": expected["Puer"]})
        self.assertTrue(set(conventions["evidence_ids"]) <= {e["id"] for e in reading["evidence"]})

    def test_reversed_mother_order_is_a_different_input_and_board(self):
        original = PR.chart(MOTHERS)
        reversed_board = PR.chart(list(reversed(MOTHERS)))
        self.assertNotEqual(original["mothers"], reversed_board["mothers"])
        self.assertNotEqual(original["patterns"], reversed_board["patterns"])

    def test_exact_house_ruling_and_honest_gap_do_not_leak_as_selected_position(self):
        vii = PR.render_position(MOTHERS, 7, topic="marriage")
        v = next(e for e in vii["evidence"] if e["id"] == FIXTURE["expected"]["figure_in_house_7_voice"])
        self.assertEqual(v["scope"], "selected_position")
        self.assertEqual(v["locator"], FIXTURE["expected"]["figure_in_house_7_locator"])
        judge = PR.render_position(MOTHERS, 15, topic="marriage")
        self.assertEqual(judge["position"]["role"], "judge")
        self.assertIn("no position-specific court ruling", judge["gaps"][0]["reason"])
        self.assertFalse(any(e["scope"] == "selected_position" and e["id"] == v["id"] for e in judge["evidence"]))
        # A topically relevant VII passage may be present, but is explicitly not a Judge ruling.
        related = [e for e in judge["evidence"] if e["id"] == v["id"]]
        self.assertTrue(not related or related[0]["scope"] == "related_position")

    def test_carcer_in_first_is_gap_despite_general_definition(self):
        reading = PR.render_position(MOTHERS, 1)
        self.assertTrue(any(g["position"] == 1 and g["figure"] == "Carcer" for g in reading["gaps"]))
        self.assertTrue(any(e["scope"] == "general_figure" for e in reading["evidence"]))
        self.assertFalse(any(e["scope"] == "selected_position" for e in reading["evidence"]))

    def test_topic_changes_without_recasting_or_moving_selected_tile(self):
        marriage = PR.render_position(MOTHERS, 7, topic="marriage")
        wealth = PR.render_position(MOTHERS, 7, topic="wealth_money")
        self.assertEqual(marriage["position"], wealth["position"])
        self.assertEqual(marriage["intent"]["focus_house"], 7)
        self.assertEqual(wealth["intent"]["focus_house"], 2)
        self.assertIsNone(marriage["related_position"])
        self.assertEqual(wealth["related_position"]["id"], 2)
        marriage_text = next(s["text"] for s in marriage["sections"] if s["key"] == "for_your_question")
        wealth_text = next(s["text"] for s in wealth["sections"] if s["key"] == "for_your_question")
        self.assertIn("assuming agreement", marriage_text)
        self.assertIn("not the focus house", wealth_text)
        self.assertIn("not show that combining savings is financially safe", wealth_text)
        judge = PR.render_position(MOTHERS, 15, topic="marriage")
        judge_text = next(s["text"] for s in judge["sections"] if s["key"] == "for_your_question")
        self.assertIn("Judge", judge_text)
        self.assertNotIn("assuming agreement", judge_text)

    def test_question_routing_suggests_asks_and_does_not_override_explicit_focus(self):
        not_marriage = PR.route_question("not a marriage question; I am asking about our savings")
        self.assertEqual(not_marriage["state"], "suggested")
        self.assertIsNone(not_marriage["topic"])
        self.assertEqual(not_marriage["suggestion"]["topic"], "wealth_money")
        mixed = PR.route_question("Should I accept the job or move house?")
        self.assertEqual(mixed["state"], "needs_confirmation")
        self.assertGreaterEqual(len(mixed["candidates"]), 2)
        unknown = PR.route_question("Will the moonstone sing at dawn?")
        self.assertEqual(unknown["state"], "general")
        self.assertEqual(PR.route_question(None)["state"], "general")
        explicit = PR.route_question("Should I marry?", "wealth_money")
        self.assertEqual(explicit["topic"], "wealth_money")
        self.assertEqual(explicit["focus_house"], 2)

    def test_ambiguity_keeps_general_reading_available(self):
        reading = PR.render_position(MOTHERS, 7, question="Should I accept the job or move house?")
        self.assertEqual(reading["status"], "needs_confirmation")
        self.assertIsNone(reading["intent"]["focus_house"])
        self.assertTrue(any(s["key"] == "for_your_question" for s in reading["sections"]))

    def test_cite_only_text_is_filtered_and_differing_passages_stay_unresolved(self):
        book = G.VoiceBook()
        cite_only = book.lookup(POLICY_FIXTURE["cite_only_voice_id"])
        self.assertTrue(cite_only["cite_only"])
        reference = PR._evidence(cite_only, rights_profile="research", scope="selected_position")
        self.assertIsNone(reference["text"])
        self.assertIsNone(reference["gloss"])
        self.assertFalse(reference["permissions"]["quote_allowed"])
        self.assertFalse(PR._allowed(cite_only, "public"))
        case = POLICY_FIXTURE["comparison_case"]
        comparison = PR._unresolved_comparisons(case["records"], "research")
        self.assertEqual(comparison[0]["status"], case["expected_status"])
        self.assertEqual({v["authority"] for v in comparison[0]["source_views"]},
                         set(case["expected_authorities"]))
        self.assertIn("not an adjudicated disagreement", comparison[0]["note"])
        puer = PR.render_position(["Puer"] * 4, 1)
        actual = [d for d in puer["disagreements"] if d["key"] == "figure_attribute:Puer:planet"]
        self.assertTrue(actual)
        self.assertIn("Puer = Venus", " ".join(v["text"] for v in actual[0]["source_views"]))
        self.assertIn("Puer = Mars", " ".join(v["text"] for v in actual[0]["source_views"]))

    def test_locale_fallback_and_rights_filter(self):
        fallback = PR.render_position(MOTHERS, 7, topic="marriage", locale="fr")
        self.assertEqual(fallback["available_locale"], "en")
        self.assertIn("not supported", fallback["fallback_reason"])
        self.assertIsNone(PR.render_position(MOTHERS, 7, locale="en-GB")["fallback_reason"])
        self.assertIn("not supported", PR.render_position(MOTHERS, 7, locale="enochian")["fallback_reason"])
        public = PR.render_position(MOTHERS, 7, topic="marriage", rights_profile="public")
        self.assertTrue(all(not e["permissions"]["cite_only"] for e in public["evidence"]))
        self.assertTrue(all(e["permissions"]["quote_allowed"] is False for e in public["evidence"]))

    def test_invalid_inputs_name_the_field(self):
        for mothers, pos, field in [(["Via"], 1, "mothers"), (["not a figure"] * 4, 1, "mothers[0]"),
                                   (MOTHERS, 0, "selected_position"), (MOTHERS, 17, "selected_position"),
                                   (MOTHERS, True, "selected_position")]:
            with self.subTest(field=field, pos=pos), self.assertRaises(PR.InputError) as cm:
                PR.render_position(mothers, pos)
            self.assertEqual(cm.exception.field, field)
        with self.assertRaises(PR.InputError):
            PR.render_position(MOTHERS, 1, topic="invented_topic")

    def test_captured_examples_validate_against_versioned_json_schema(self):
        import jsonschema
        schema = json.loads((ROOT / "types/atelier-position-v1.schema.json").read_text())
        captured = json.loads((ROOT / "docs/atelier_position_v1_responses.json").read_text())
        for item in captured:
            with self.subTest(example=item["name"]):
                jsonschema.validate(item["response"], schema)

    def test_source_audit_smoke_and_known_folio_records(self):
        from app import server
        cast = server.chart(MOTHERS)
        board = {"houses": {int(k): v for k, v in cast["houses"].items()}, **cast["court"]}
        book = G.VoiceBook()
        self.assertEqual(cast["houses"]["7"], cast["judge"])
        for topic, expected_house in (("marriage", 7), ("wealth_money", 2),
                                      ("Should I discuss trust with my partner?", None)):
            reading = G.assemble(board, topic, book)
            self.assertTrue(G.validate(reading, book)["ok"])
            self.assertEqual(reading["quesited_house"], expected_house)
        for voice_id, locator in ((FIXTURE["expected"]["figure_in_house_7_voice"], FIXTURE["expected"]["figure_in_house_7_locator"]),
                                  (FIXTURE["expected"]["figure_in_house_2_voice"], FIXTURE["expected"]["figure_in_house_2_locator"])):
            self.assertEqual(book.lookup(voice_id)["locator"], locator)


if __name__ == "__main__":
    unittest.main(verbosity=2)
