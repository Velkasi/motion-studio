#!/usr/bin/env python3
"""Offline tests of the motion-studio scripts: no key, no network.

Run: python3 -m unittest .claude/skills/motion-studio/scripts/test_motion_studio.py -v
The EM-Body_reel_4 regression tests are skipped when that project is not on disk.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
EMB = os.path.join(ROOT, "EM-Body_reel_4")


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def w(text, start, end):
    return {"w": text, "start": start, "end": end}


class MinutageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load("minutage")

    def test_split_sentences_on_terminators_and_lines(self):
        self.assertEqual(self.m.split_sentences("Tu veux ? Oui… Avec EMBody, ça existe.\nFin"),
                         ["Tu veux ?", "Oui…", "Avec EMBody, ça existe.", "Fin"])

    def test_screen_words_attach_lone_punctuation(self):
        self.assertEqual(self.m.screen_words("à la salle ?"), ["à", "la", "salle ?"])
        self.assertEqual(self.m.screen_words("de 19 % et « oui »"), ["de", "19 %", "et", "« oui »"])

    def test_non_breaking_space_makes_one_screen_unit(self):
        self.assertEqual(self.m.split_sentences("En seulement 30 minutes."), ["En seulement 30 minutes."])
        self.assertEqual(self.m.screen_words("en 30 minutes."), ["en", "30 minutes."])
        stt = [w("en", 0.0, 0.2), w("30", 0.2, 0.5), w("minutes", 0.5, 0.9)]
        out = self.m.build(["en 30 minutes."], stt, [], 1.5)
        self.assertEqual([(x["w"], x["start"], x["end"]) for x in out["words"]],
                         [("en", 0.0, 0.2), ("30 minutes.", 0.2, 0.9)])

    def test_norm_drops_case_accents_punctuation(self):
        self.assertEqual(self.m.norm("Déjà-vu, É!"), "dejavue")

    def test_align_groups_fragments(self):
        self.assertEqual(self.m.align(["Avec", "EMBody,", "ça"], ["Avec", "M", "-Body,", "ça"]),
                         [(0, 0), (1, 2), (3, 3)])

    def test_number_in_digits_is_interpolated_on_the_spoken_word(self):
        stt = [w("en", 0.0, 0.2), w("seulement", 0.2, 0.6), w("trente", 0.6, 1.0), w("minutes", 1.0, 1.5)]
        out = self.m.build(["en seulement 30 minutes."], stt, [], 2.0)
        thirty = out["words"][2]
        self.assertEqual(thirty["w"], "30")
        self.assertEqual(thirty["cale"], "interpole")
        self.assertAlmostEqual(thirty["start"], 0.6, places=2)
        self.assertAlmostEqual(out["words"][3]["start"], 1.0, places=2)

    def test_skipped_word_is_interpolated_and_times_increase(self):
        stt = [w("un", 0.0, 0.3), w("trois", 0.8, 1.1)]
        out = self.m.build(["un deux trois"], stt, [], 2.0)
        starts = [x["start"] for x in out["words"]]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual(out["words"][1]["cale"], "interpole")
        self.assertIn("deux", out["unaligned"])

    def test_interpolated_word_starts_on_the_attack_not_in_the_silence(self):
        stt = [w("Bonjour", 0.0, 0.6), w("trente", 1.5, 1.8), w("minutes", 1.8, 2.2)]
        out = self.m.build(["Bonjour.", "30 minutes."], stt, [0.0, 1.5], 3.0)
        self.assertEqual(out["words"][1]["w"], "30")
        self.assertAlmostEqual(out["words"][1]["start"], 1.5, places=2)
        self.assertAlmostEqual(out["words"][2]["start"], 1.8, places=2)

    def test_word_added_by_the_voice_is_not_absorbed_and_is_reported(self):
        stt = [w("Très", 0.0, 0.3), w("vraiment", 0.3, 0.8), w("vite", 0.8, 1.1)]
        out = self.m.build(["Très vite."], stt, [], 1.5)
        self.assertAlmostEqual(out["words"][1]["start"], 0.8, places=2)
        self.assertIn("vraiment", out["extra"])

    def test_snap_on_phrase_attack(self):
        stt = [w("Bonjour", 0.30, 0.7), w("toi", 0.7, 1.0)]
        out = self.m.build(["Bonjour toi."], stt, [0.12], 1.5)
        self.assertEqual(out["words"][0]["start"], 0.12)
        self.assertEqual(out["words"][0]["cale"], "attaque")

    def test_schema(self):
        stt = [w("Un", 0.0, 0.3), w("deux", 0.3, 0.6), w("Trois", 1.5, 1.8)]
        out = self.m.build(["Un deux.", "Trois."], stt, [], 3.0)
        self.assertEqual(set(out) >= {"duration", "fps", "phrases", "words", "silences"}, True)
        self.assertEqual(out["phrases"][1]["words"], [2, 2])
        self.assertEqual(out["silences"][0], {"from": 0.6, "to": 1.5, "len": 0.9})
        self.assertEqual(out["silences"][-1]["to"], 3.0)

    def test_no_words_at_all_spreads_over_the_duration(self):
        out = self.m.build(["a b"], [], [], 2.0)
        self.assertEqual([x["cale"] for x in out["words"]], ["interpole", "interpole"])
        self.assertLess(out["words"][0]["start"], out["words"][1]["start"])

    @unittest.skipUnless(os.path.exists(os.path.join(EMB, "minutage.json")), "EM-Body_reel_4 absent")
    def test_regression_em_body_reel_4(self):
        import difflib
        ref = json.load(open(os.path.join(EMB, "minutage.json"), encoding="utf-8"))
        stt = json.load(open(os.path.join(EMB, "assets/audio/voix-montage-mots.json"), encoding="utf-8"))["words"]
        onsets = json.load(open(os.path.join(EMB, "onsets.json"), encoding="utf-8"))
        db = self.m.envelope_db(os.path.join(EMB, "assets/audio/voix-montage.wav"))
        out = self.m.build([p["text"] for p in ref["phrases"]], stt, [p["start"] for p in onsets["phrases"]],
                           onsets["duration"], db=db)
        a = [self.m.norm(x["w"]) for x in ref["words"]]
        b = [self.m.norm(x["w"]) for x in out["words"]]
        pairs = [(i, j) for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks()
                 for i, j in zip(range(blk.a, blk.a + blk.size), range(blk.b, blk.b + blk.size))]
        self.assertGreaterEqual(len(pairs), 0.95 * len(a))
        close = [1 for i, j in pairs if abs(ref["words"][i]["start"] - out["words"][j]["start"]) <= 1 / 30 + 0.001]
        self.assertGreaterEqual(len(close), 0.95 * len(pairs), f"{len(close)}/{len(pairs)} within one frame")


class StyleDistanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = load("style-distance")

    def style(self, famille, *values):
        return {"famille": famille, "concept": "c", "axes": dict(zip(self.s.AXIS_ORDER, values))}

    def trio(self):
        return {"styles": [
            self.style("storyboard-marketing", "typographique", "clair-plat", "mono-accent", "grotesque",
                       "travelling-continu", "ressort-net"),
            self.style("illustration-vectorielle", "vectoriel-plat", "clair-profond", "pastel", "ronde",
                       "panoramique-plan", "organique"),
            self.style("pop-up-papier", "papier-physique", "sombre-profond", "sature-pop", "display-condensee",
                       "plan-fixe-pop", "impact-rapide"),
        ]}

    def test_distant_trio_passes(self):
        self.assertEqual(self.s.check(self.trio()), [])

    def test_close_pair_fails(self):
        data = self.trio()
        b = data["styles"][1]["axes"]
        b.update(rendu="typographique", monde="clair-plat")   # 4 axes apart from style 0
        errors = self.s.check(data)
        self.assertTrue(any("storyboard-marketing" in e and "illustration-vectorielle" in e for e in errors), errors)

    def test_unknown_value_is_invalid(self):
        data = self.trio()
        data["styles"][0]["axes"]["palette"] = "arc-en-ciel"
        with self.assertRaises(ValueError):
            self.s.check(data)

    def test_duplicate_family_and_count_are_invalid(self):
        data = self.trio()
        data["styles"][2]["famille"] = "storyboard-marketing"
        with self.assertRaises(ValueError):
            self.s.check(data)
        with self.assertRaises(ValueError):
            self.s.check({"styles": self.trio()["styles"][:2]})

    def test_distance(self):
        st = self.trio()["styles"]
        self.assertEqual(self.s.distance(st[0], st[0]), 0)
        self.assertEqual(self.s.distance(st[0], st[1]), 6)


class StyleCatalogTest(unittest.TestCase):
    """patterns/STYLE-FAMILIES.md and style-distance.py speak the same vocabulary, and its example trios pass."""

    @classmethod
    def setUpClass(cls):
        import re
        cls.s = load("style-distance")
        with open(os.path.join(ROOT, "patterns", "STYLE-FAMILIES.md"), encoding="utf-8") as f:
            text = f.read()
        cls.families = {}
        for fam, body in re.findall(r"^### ([a-z0-9-]+) — .*?\n(.*?)(?=^### |^## |\Z)", text, re.M | re.S):
            axes = re.search(r"\*\*Axes\*\* : `([^`]+)`", body)
            cls.families[fam] = dict(kv.split("=") for kv in axes.group(1).split())
        cls.trios = [[x.strip() for x in row.split(",")]
                     for row in re.findall(r"^\| [A-Z] \| ([a-z0-9-]+(?:, [a-z0-9-]+){2}) \|", text, re.M)]

    def styles(self, names):
        return {"styles": [{"famille": n, "concept": "c", "axes": self.families[n]} for n in names]}

    def test_twelve_families_with_valid_axes(self):
        self.assertEqual(len(self.families), 12)
        for fam, axes in self.families.items():
            self.assertEqual(list(axes), self.s.AXIS_ORDER, fam)
            for axis, value in axes.items():
                self.assertIn(value, self.s.AXES[axis], f"{fam}: {axis}={value}")

    def test_example_trios_pass(self):
        self.assertEqual(len(self.trios), 3)
        for names in self.trios:
            self.assertEqual(self.s.check(self.styles(names)), [], names)


STORY = """# Storyboard

## Frame 1: L'accroche · 0.00 → 2.60

- duration: 2.60s

Word cues: Tu@0.05 veux@0.18 à@0.60 la@1.00 salle ?@1.50

## Frame 2 : Suite · 2.60 → 4.00

Word cues: Avec@0.00 EMBody,@0.40
"""


def minutage(words, fps=30):
    return {"fps": fps, "duration": 5.0, "words": [{"i": i, "w": t, "start": s} for i, (t, s) in enumerate(words)]}


class CheckCuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = load("check-cues")

    def ok_minutage(self):
        return minutage([("Tu", 0.05), ("veux", 0.18), ("à", 0.6), ("la", 1.0), ("salle ?", 1.5), ("Avec", 2.6),
                         ("EMBody,", 3.0)])

    def test_parse_both_header_forms_and_spaced_cues(self):
        frames = self.c.parse_storyboard(STORY)
        self.assertEqual([f[0] for f in frames], [1, 2])
        self.assertEqual(frames[1][1], 2.6)
        self.assertEqual(frames[0][2], [("Tu", 0.05), ("veux", 0.18), ("à", 0.6), ("la", 1.0), ("salle ?", 1.5)])

    def test_on_time_passes(self):
        self.assertEqual(self.c.check(STORY, self.ok_minutage()), [])

    def test_one_frame_late_fails(self):
        m = self.ok_minutage()
        m["words"][1]["start"] = 0.18 - 1 / 30
        errors = self.c.check(STORY, m)
        self.assertTrue(any("veux" in e and "retard" in e for e in errors), errors)

    def test_three_frames_early_fails(self):
        m = self.ok_minutage()
        m["words"][3]["start"] = 1.0 + 3 / 30
        errors = self.c.check(STORY, m)
        self.assertTrue(any("la" in e and "tôt" in e for e in errors), errors)

    def test_sparse_cues_far_apart_still_match(self):
        story = "## Frame 1 : A · 0.00 → 5.00\n\nWord cues: un@0.00 fin@4.00\n"
        words = [("un", 0.0)] + [(f"mot{k}", 0.5 + 0.4 * k) for k in range(8)] + [("fin", 4.0)]
        self.assertEqual(self.c.check(story, minutage(words)), [])

    def test_unknown_word_fails(self):
        m = self.ok_minutage()
        m["words"][6]["w"] = "Autre"
        errors = self.c.check(STORY, m)
        self.assertTrue(any("EMBody" in e for e in errors), errors)

    @unittest.skipUnless(os.path.exists(os.path.join(EMB, "STORYBOARD.md")), "EM-Body_reel_4 absent")
    def test_em_body_reel_4_runs(self):
        text = open(os.path.join(EMB, "STORYBOARD.md"), encoding="utf-8").read()
        m = json.load(open(os.path.join(EMB, "minutage.json"), encoding="utf-8"))
        self.assertGreater(sum(len(f[2]) for f in self.c.parse_storyboard(text)), 100)
        self.assertIsInstance(self.c.check(text, m), list)


class CheckSfxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = load("check-sfx")

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.lib = os.path.join(self.tmp, "lib")
        self.proj = os.path.join(self.tmp, "proj")
        os.makedirs(self.lib)
        os.makedirs(self.proj)
        for d, n in ((self.lib, "pop.mp3"), (self.lib, "whoosh.mp3"), (self.proj, "signature.mp3")):
            open(os.path.join(d, n), "wb").close()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_check(self, events, duration=10.0):
        return self.x.check(events, duration, [self.proj, self.lib])

    def test_two_uses_pass(self):
        self.assertEqual(self.run_check([["pop", 1, 0.2], ["pop", 2, 0.2], ["signature", 3, 0.5]]), [])

    def test_three_uses_fail_with_the_name(self):
        errors = self.run_check([["pop", 1, 0.2], ["pop", 2, 0.2], ["pop", 3, 0.2]])
        self.assertTrue(any("pop" in e and "3" in e for e in errors), errors)

    def test_missing_file_fails(self):
        errors = self.run_check([["boom", 1, 0.2]])
        self.assertTrue(any("boom" in e for e in errors), errors)

    def test_event_after_the_end_fails(self):
        errors = self.run_check([["whoosh", 12, 0.2]])
        self.assertTrue(any("whoosh" in e and "12" in e for e in errors), errors)

    def test_malformed_event_fails(self):
        errors = self.run_check([["pop", 1.0], "whoosh", ["whoosh", "x", 0.2]])
        self.assertEqual(len([e for e in errors if "format" in e]), 3, errors)

    def test_project_sound_wins(self):
        open(os.path.join(self.proj, "pop.mp3"), "wb").close()
        self.assertEqual(self.x.find(["pop"][0], [self.proj, self.lib]), os.path.join(self.proj, "pop.mp3"))

    @unittest.skipUnless(os.path.exists(os.path.join(EMB, "assets/audio/sfx-events.json")), "EM-Body_reel_4 absent")
    def test_em_body_reel_4_repeats_em_pulse(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "check-sfx.py"), EMB], capture_output=True, text=True,
                           encoding="utf-8")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("em-pulse", r.stdout + r.stderr)


@unittest.skipUnless(shutil.which("bash"), "bash absent")
class HfWrapperTest(unittest.TestCase):
    def run_hf(self, *args):
        # shutil.which: Git Bash, not the System32 WSL launcher that a bare "bash" can resolve to on Windows
        return subprocess.run([shutil.which("bash"), os.path.join(HERE, "hf.sh"), *args], capture_output=True, text=True,
                              encoding="utf-8", env={**os.environ, "HF_DRY_RUN": "1"})

    def test_forbidden_commands_are_refused(self):
        for cmd in ("publish", "feedback", "cloud", "lambda", "cloudrun", "auth", "upgrade", "skills"):
            r = self.run_hf(ROOT, cmd)
            self.assertNotEqual(r.returncode, 0, cmd)
            self.assertIn("AGENTS.md", r.stderr)

    def test_allowed_command_runs_local_cli_with_telemetry_off(self):
        r = self.run_hf(ROOT, "snapshot", "--at", "1.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("HYPERFRAMES_NO_TELEMETRY=1", r.stdout)
        self.assertIn("npx --no hyperframes snapshot --at 1.0", r.stdout)
        self.assertNotIn("@latest", r.stdout)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg absent")
class ComparatifTest(unittest.TestCase):
    def test_contact_sheet_size(self):
        tmp = tempfile.mkdtemp()
        try:
            films = []
            for k in range(3):
                f = os.path.join(tmp, f"f{k}.mp4")
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30:d=2",
                                "-pix_fmt", "yuv420p", f], check=True)
                films.append(f)
            out = os.path.join(tmp, "comparatif.jpg")
            subprocess.run([sys.executable, os.path.join(HERE, "comparatif.py"), *films, "--out", out,
                            "--height", "90"], check=True)
            size = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height", "-of", "csv=p=0", out], capture_output=True, text=True,
                                  check=True).stdout.strip()
            self.assertEqual(size, f"{6 * 160},{3 * 90}")
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
