#!/usr/bin/env python3
"""Offline tests of eleven.py: no key, no network (urlopen is mocked).

Run: python3 -m unittest .claude/skills/motion-design/scripts/test_eleven.py -v
"""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eleven  # noqa: E402

KEY = "sk_test_0123456789abcdef"

SCRIPT_MD = """# Script

## Version écran

Lundi, tu demandes une modif.

## Version voix (collée dans ElevenLabs)

Lundi, tu demandes une modif sur ton site.
Mercredi, le devis tombe : mille euros.

## Notes

Rien à lire ici.
"""


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def read(path, binary=False):
    with open(path, "rb" if binary else "r", **({} if binary else {"encoding": "utf-8"})) as fh:
        return fh.read()


def write(path, data):
    with open(path, "wb") as fh:
        fh.write(data)


def http_error(code, body=b"{}"):
    return urllib.error.HTTPError("https://api.elevenlabs.io/x", code, "err", {}, io.BytesIO(body))


class HelpersTest(unittest.TestCase):
    def test_voice_text_extracts_the_voice_section_only(self):
        text = eleven.voice_text(SCRIPT_MD)
        self.assertEqual(text, "Lundi, tu demandes une modif sur ton site.\nMercredi, le devis tombe : mille euros.")

    def test_voice_text_accepts_a_coller_heading_and_drops_code_fences(self):
        md = "## Version à coller\n\n```\nBonjour.\n```\n"
        self.assertEqual(eleven.voice_text(md), "Bonjour.")

    def test_voice_text_without_section_fails(self):
        with self.assertRaisesRegex(eleven.ElevenError, "Version voix"):
            eleven.voice_text("# Script\n\n## Version écran\n\nBonjour.\n")

    def test_voice_text_empty_section_fails(self):
        with self.assertRaisesRegex(eleven.ElevenError, "empty"):
            eleven.voice_text("## Version voix\n\n## Notes\n")

    def test_break_and_ssml_tags_are_refused_with_their_lines(self):
        with self.assertRaises(eleven.ElevenError) as ctx:
            eleven.check_tags('Bonjour. <break time="0.6s" />\nÇa va.\n<SPEAK>non</SPEAK>')
        msg = str(ctx.exception)
        self.assertIn("line 1", msg)
        self.assertIn("line 3", msg)
        self.assertNotIn("line 2", msg)

    def test_acting_tags_are_allowed(self):
        eleven.check_tags("[sighs] Vendredi... toujours rien.")

    def test_scribe_to_words_keeps_words_only(self):
        resp = {"words": [
            {"text": "Lundi,", "start": 0.12, "end": 0.5, "type": "word"},
            {"text": " ", "start": 0.5, "end": 0.52, "type": "spacing"},
            {"text": "(rires)", "start": 0.6, "end": 0.9, "type": "audio_event"},
            {"text": "tu", "start": 1.004, "end": 1.1, "type": "word"},
        ]}
        self.assertEqual(eleven.scribe_to_words(resp), [
            {"w": "Lundi,", "start": 0.12, "end": 0.5},
            {"w": "tu", "start": 1.0, "end": 1.1},
        ])

    def test_silences_over_threshold(self):
        words = [{"w": "a", "start": 0, "end": 1.0}, {"w": "b", "start": 1.2, "end": 2.0},
                 {"w": "c", "start": 2.6, "end": 3.0}]
        self.assertEqual(eleven.silences(words), [(2.0, 2.6)])

    def test_multipart_carries_fields_and_file(self):
        body, ctype = eleven.multipart({"model_id": "scribe_v2"}, "file", "voix.wav", b"RIFFDATA")
        boundary = ctype.split("boundary=")[1]
        self.assertTrue(ctype.startswith("multipart/form-data"))
        self.assertIn(b'name="model_id"\r\n\r\nscribe_v2', body)
        self.assertIn(b'filename="voix.wav"', body)
        self.assertIn(b"RIFFDATA", body)
        self.assertTrue(body.endswith(f"--{boundary}--\r\n".encode()))


@mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": KEY})
@mock.patch("eleven.time.sleep")
@mock.patch("eleven.urllib.request.urlopen")
class RequestTest(unittest.TestCase):
    def test_missing_key_stops_before_any_network_call(self, urlopen, sleep):
        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": ""}):
            with self.assertRaisesRegex(eleven.ElevenError, "ELEVENLABS_API_KEY"):
                eleven.request("/v1/sound-generation", json_body={"text": "x"})
        urlopen.assert_not_called()

    def test_sends_key_header_and_json(self, urlopen, sleep):
        urlopen.return_value = FakeResponse(b"ID3audio")
        self.assertEqual(eleven.request("/v1/sound-generation", json_body={"text": "x"}, query={"a": "b"}), b"ID3audio")
        req = urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://api.elevenlabs.io/v1/sound-generation?a=b")
        self.assertEqual(req.get_header("Xi-api-key"), KEY)
        self.assertEqual(json.loads(req.data), {"text": "x"})

    def test_401_names_the_permission_and_hides_the_key(self, urlopen, sleep):
        urlopen.side_effect = http_error(401, f'{{"detail": "bad key {KEY}"}}'.encode())
        with self.assertRaises(eleven.ElevenError) as ctx:
            eleven.request("/v1/text-to-speech/v", json_body={})
        msg = str(ctx.exception)
        self.assertIn("permission", msg)
        self.assertNotIn(KEY, msg)
        self.assertIn("***", msg)

    def test_retries_429_then_succeeds(self, urlopen, sleep):
        urlopen.side_effect = [http_error(429), http_error(503), FakeResponse(b"ok")]
        self.assertEqual(eleven.request("/v1/x", json_body={}), b"ok")
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_gives_up_after_three_retries(self, urlopen, sleep):
        urlopen.side_effect = [http_error(500) for _ in range(4)]
        with self.assertRaisesRegex(eleven.ElevenError, "HTTP 500"):
            eleven.request("/v1/x", json_body={})
        self.assertEqual(urlopen.call_count, 4)

    def test_400_is_not_retried(self, urlopen, sleep):
        urlopen.side_effect = http_error(400, b'{"detail": "bad voice"}')
        with self.assertRaisesRegex(eleven.ElevenError, "bad voice"):
            eleven.request("/v1/x", json_body={})
        self.assertEqual(urlopen.call_count, 1)

    def test_empty_body_is_an_error(self, urlopen, sleep):
        urlopen.return_value = FakeResponse(b"")
        with self.assertRaisesRegex(eleven.ElevenError, "empty"):
            eleven.request("/v1/x", json_body={})


@mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": KEY})
@mock.patch("eleven.time.sleep")
@mock.patch("eleven.urllib.request.urlopen")
class CommandsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = os.path.join(self.tmp.name, "film")
        os.makedirs(os.path.join(self.project, "assets", "audio"))
        with open(os.path.join(self.project, "SCRIPT.md"), "w", encoding="utf-8") as fh:
            fh.write(SCRIPT_MD)
        self.audio = os.path.join(self.project, "assets", "audio")

    def tearDown(self):
        self.tmp.cleanup()

    def test_tts_writes_the_take_and_its_settings(self, urlopen, sleep):
        urlopen.return_value = FakeResponse(b"ID3take")
        self.assertEqual(eleven.main(["tts", self.project, "--seed", "42"]), 0)
        self.assertEqual(read(os.path.join(self.audio, "voix.mp3"), binary=True), b"ID3take")
        req = urlopen.call_args[0][0]
        self.assertIn("/v1/text-to-speech/WeAAwKYcS06VmXw086yZ?output_format=mp3_44100_128", req.full_url)
        body = json.loads(req.data)
        self.assertEqual(body["model_id"], "eleven_v4")
        self.assertEqual(body["language_code"], "fr")
        self.assertEqual(body["seed"], 42)
        self.assertEqual(body["voice_settings"], {"stability": 0.45, "similarity_boost": 0.85})
        self.assertTrue(body["text"].startswith("Lundi, tu demandes une modif sur ton site."))
        meta_raw = read(os.path.join(self.audio, "voix.json"))
        self.assertNotIn(KEY, meta_raw)
        self.assertEqual(json.loads(meta_raw)["seed"], 42)

    def test_tts_refuses_to_overwrite_a_take(self, urlopen, sleep):
        write(os.path.join(self.audio, "voix.mp3"), b"old")
        self.assertEqual(eleven.main(["tts", self.project]), 1)
        urlopen.assert_not_called()
        self.assertEqual(read(os.path.join(self.audio, "voix.mp3"), binary=True), b"old")

    def test_tts_one_sentence_reuses_the_seed_of_the_take(self, urlopen, sleep):
        with open(os.path.join(self.audio, "voix.json"), "w", encoding="utf-8") as fh:
            json.dump({"seed": 777}, fh)
        urlopen.return_value = FakeResponse(b"ID3phrase")
        self.assertEqual(eleven.main(["tts", self.project, "--text", "Vendredi... toujours rien.",
                                      "--out", "phrase-03.mp3"]), 0)
        body = json.loads(urlopen.call_args[0][0].data)
        self.assertEqual(body["seed"], 777)
        self.assertEqual(body["text"], "Vendredi... toujours rien.")
        self.assertTrue(os.path.exists(os.path.join(self.audio, "phrase-03.mp3")))

    def test_tts_refuses_break_tags_before_any_call(self, urlopen, sleep):
        self.assertEqual(eleven.main(["tts", self.project, "--text", 'Stop. <break time="1s" />']), 1)
        urlopen.assert_not_called()

    @mock.patch("eleven.duration", return_value=3.456)
    def test_stt_writes_the_mots_format(self, duration, urlopen, sleep):
        wav = os.path.join(self.audio, "voix-montage.wav")
        write(wav, b"RIFFwav")
        urlopen.return_value = FakeResponse(json.dumps({"words": [
            {"text": "Lundi,", "start": 0.1, "end": 0.5, "type": "word"},
            {"text": " ", "start": 0.5, "end": 1.2, "type": "spacing"},
            {"text": "mercredi.", "start": 1.2, "end": 1.9, "type": "word"},
        ]}).encode())
        self.assertEqual(eleven.main(["stt", wav]), 0)
        out = json.loads(read(os.path.join(self.audio, "voix-montage-mots.json")))
        self.assertEqual(out, {"duration": 3.46, "words": [
            {"w": "Lundi,", "start": 0.1, "end": 0.5}, {"w": "mercredi.", "start": 1.2, "end": 1.9}]})
        data = urlopen.call_args[0][0].data
        self.assertIn(b"scribe_v2", data)
        self.assertIn(b'name="timestamps_granularity"\r\n\r\nword', data)

    @mock.patch("eleven.duration", return_value=1.0)
    def test_stt_without_any_word_fails_and_writes_nothing(self, duration, urlopen, sleep):
        wav = os.path.join(self.audio, "voix-montage.wav")
        write(wav, b"RIFFwav")
        urlopen.return_value = FakeResponse(b'{"words": []}')
        self.assertEqual(eleven.main(["stt", wav]), 1)
        self.assertFalse(os.path.exists(os.path.join(self.audio, "voix-montage-mots.json")))

    def test_stt_missing_audio_fails_before_any_call(self, urlopen, sleep):
        self.assertEqual(eleven.main(["stt", os.path.join(self.audio, "absent.wav")]), 1)
        urlopen.assert_not_called()

    def test_sfx_rejects_a_name_that_is_not_kebab_case(self, urlopen, sleep):
        self.assertEqual(eleven.main(["sfx", self.project, "Mon Son", "a chime"]), 1)
        urlopen.assert_not_called()

    def test_sfx_writes_the_sound_and_its_credit(self, urlopen, sleep):
        urlopen.return_value = FakeResponse(b"ID3chime")
        self.assertEqual(eleven.main(["sfx", self.project, "signature", "soft two-tone chime", "--duration", "1.5"]), 0)
        sfx_dir = os.path.join(self.audio, "sfx")
        self.assertEqual(read(os.path.join(sfx_dir, "signature.mp3"), binary=True), b"ID3chime")
        body = json.loads(urlopen.call_args[0][0].data)
        self.assertEqual(body["model_id"], "eleven_text_to_sound_v2")
        self.assertEqual(body["duration_seconds"], 1.5)
        credits = read(os.path.join(sfx_dir, "CREDITS.md"))
        self.assertIn("signature.mp3", credits)
        self.assertIn("soft two-tone chime", credits)

    def test_sfx_duration_out_of_range_fails_before_any_call(self, urlopen, sleep):
        self.assertEqual(eleven.main(["sfx", self.project, "long", "rain", "--duration", "45"]), 1)
        urlopen.assert_not_called()

    def test_sfx_says_when_it_overrides_a_library_sound(self, urlopen, sleep):
        urlopen.return_value = FakeResponse(b"ID3pop")
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(eleven.main(["sfx", self.project, "pop", "a soft pop"]), 0)
        self.assertIn("overrides", out.getvalue())


if __name__ == "__main__":
    unittest.main()
