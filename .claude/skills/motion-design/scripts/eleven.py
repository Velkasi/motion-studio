#!/usr/bin/env python3
"""ElevenLabs calls of the motion-design method: the voice (TTS), the word timings (STT), the sound effects (SFX).

The only script of this repository that sends anything out, and only to https://api.elevenlabs.io (see the ElevenLabs
exception in AGENTS.md). Standard library only. The key comes from the ELEVENLABS_API_KEY environment variable, never
from a file; it is never printed nor written.

  python3 eleven.py tts <project> [--voice ID] [--model eleven_v4] [--lang fr] [--stability 0.45] [--similarity 0.85]
                                  [--seed N] [--text TEXT | --text-file F] [--out voix.mp3] [--format mp3_44100_128]
                                  [--force]
      Reads the "## Version voix" (or "## Version à coller") section of <project>/SCRIPT.md, writes one take to
      <project>/assets/audio/voix.mp3 and its settings to voix.json. One sentence again, same seed:
      --text "..." --out phrase-07.mp3.
  python3 eleven.py stt <audio> [--lang fr]
      Scribe v2 word timestamps -> <audio>-mots.json, the format of mots.py ({"duration", "words": [{"w","start","end"}]}).
  python3 eleven.py sfx <project> <name> "description" [--duration S] [--influence 0.3] [--force]
      -> <project>/assets/audio/sfx/<name>.mp3, used by its name in sfx-events.json (it wins over the media-use library).
"""
import argparse
import datetime
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

API = "https://api.elevenlabs.io"
DEFAULT_VOICE = "WeAAwKYcS06VmXw086yZ"
DEFAULT_MODEL = "eleven_v4"
STT_MODEL = "scribe_v2"
SFX_MODEL = "eleven_text_to_sound_v2"
HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY_SFX = os.path.normpath(os.path.join(HERE, "..", "..", "media-use", "audio", "assets", "sfx"))

VOICE_HEADING = re.compile(r"^##\s+Version\s+(voix|à coller)", re.IGNORECASE)
ANY_HEADING = re.compile(r"^#{1,2}\s")
# Eleven v4 has no pause tag and no SSML: these would be read aloud or ignored. Acting tags in [brackets] are fine.
SSML_TAG = re.compile(r"<\s*/?\s*(break|speak|prosody|phoneme|say-as|emphasis|sub|lang)\b", re.IGNORECASE)
NAME = re.compile(r"[a-z0-9][a-z0-9-]*")


class ElevenError(Exception):
    pass


def api_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise ElevenError("ELEVENLABS_API_KEY is not set (a Windows user environment variable, then restart the app; "
                          "see references/voice-elevenlabs.md). Nothing was sent.")
    return key


def voice_text(markdown):
    """The text the voice reads: the "## Version voix" / "## Version à coller" section of SCRIPT.md, fences dropped."""
    section = None
    for line in markdown.splitlines():
        if section is None:
            if VOICE_HEADING.match(line):
                section = []
            continue
        if ANY_HEADING.match(line):
            break
        if not line.strip().startswith("```"):
            section.append(line)
    if section is None:
        raise ElevenError("SCRIPT.md has no '## Version voix' or '## Version à coller' section (the text to read)")
    text = "\n".join(section).strip()
    if not text:
        raise ElevenError("the voice section of SCRIPT.md is empty")
    return text


def check_tags(text):
    bad = [f"  line {i}: {line.strip()}" for i, line in enumerate(text.splitlines(), 1) if SSML_TAG.search(line)]
    if bad:
        raise ElevenError("Eleven v4 has no pause or SSML tag (<break>, <speak>...): make the silences at the montage "
                          "and use punctuation, '...' and line breaks. Lines to fix in the voice text:\n" + "\n".join(bad))


def scribe_to_words(resp):
    return [{"w": w["text"].strip(), "start": round(float(w["start"]), 2), "end": round(float(w["end"]), 2)}
            for w in resp.get("words", []) if w.get("type", "word") == "word" and w.get("text", "").strip()]


def silences(words, threshold=0.4):
    return [(a["end"], b["start"]) for a, b in zip(words, words[1:]) if b["start"] - a["end"] > threshold]


def multipart(fields, file_field, filename, content):
    boundary = uuid.uuid4().hex
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8")
             for k, v in fields.items()]
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
                 f"Content-Type: application/octet-stream\r\n\r\n".encode("utf-8") + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def request(path, *, json_body=None, form=None, query=None, retries=3):
    """POST to the ElevenLabs API and return the response body. form = (bytes, content type) from multipart()."""
    key = api_key()
    url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
    if form is not None:
        data, ctype = form
    else:
        data, ctype = json.dumps(json_body).encode("utf-8"), "application/json"
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, method="POST", headers={"xi-api-key": key, "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = resp.read()
            if not body:
                raise ElevenError(f"empty answer from {path}: nothing written")
            return body
        except urllib.error.HTTPError as e:
            detail = e.read()[:400].decode("utf-8", "replace").replace(key, "***")
            e.close()
            if e.code in (401, 403):
                raise ElevenError(f"HTTP {e.code} on {path}: refused: invalid key, missing permission on the key "
                                  f"(Text to Speech / Speech to Text / Sound Effects) or a plan limit. {detail}")
            if (e.code == 429 or e.code >= 500) and attempt < retries:
                time.sleep(2 * 2 ** attempt)
                continue
            raise ElevenError(f"HTTP {e.code} on {path}: {detail}")
        except urllib.error.URLError as e:
            if attempt < retries:
                time.sleep(2 * 2 ** attempt)
                continue
            raise ElevenError(f"network error on {path}: {e.reason}")


def write_bytes(path, data, force):
    if os.path.exists(path) and not force:
        raise ElevenError(f"{path} already exists (a take or a sound costs credits): pass --force to replace it")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def project_dir(path):
    if not os.path.isdir(path):
        raise ElevenError(f"project folder {path} not found")
    return path


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def cmd_tts(a):
    audio_dir = os.path.join(project_dir(a.project), "assets", "audio")
    if a.text is not None:
        text = a.text.strip()
    elif a.text_file:
        text = read_text(a.text_file).strip()
    else:
        script = os.path.join(a.project, "SCRIPT.md")
        if not os.path.exists(script):
            raise ElevenError(f"{script} not found (or pass --text / --text-file)")
        text = voice_text(read_text(script))
    if not text:
        raise ElevenError("no text to read")
    check_tags(text)
    out = os.path.join(audio_dir, a.out)
    if os.path.exists(out) and not a.force:
        raise ElevenError(f"{out} already exists (a take costs credits): pass --force to replace it")
    seed = a.seed
    take_meta = os.path.join(audio_dir, "voix.json")
    if seed is None and os.path.exists(take_meta):
        seed = json.loads(read_text(take_meta)).get("seed")
    if seed is None:
        seed = random.randint(1, 4294967295)
    settings = {"stability": a.stability, "similarity_boost": a.similarity}
    body = {"text": text, "model_id": a.model, "language_code": a.lang, "seed": seed, "voice_settings": settings}
    print(f"tts: {len(text)} characters, voice {a.voice}, {a.model}, {a.lang}, seed {seed} ...")
    audio = request(f"/v1/text-to-speech/{a.voice}", json_body=body, query={"output_format": a.format})
    write_bytes(out, audio, a.force)
    meta = {"voice_id": a.voice, "model_id": a.model, "language_code": a.lang, "voice_settings": settings,
            "seed": seed, "output_format": a.format, "characters": len(text), "date": now()}
    with open(os.path.splitext(out)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print(f"tts: {out} ({len(audio) // 1024} KB), settings in {os.path.splitext(out)[0]}.json")


def cmd_stt(a):
    if not os.path.isfile(a.audio):
        raise ElevenError(f"audio {a.audio} not found")
    with open(a.audio, "rb") as fh:
        content = fh.read()
    fields = {"model_id": STT_MODEL, "language_code": a.lang, "timestamps_granularity": "word",
              "tag_audio_events": "false"}
    print(f"stt: {os.path.basename(a.audio)} ({len(content) // 1024} KB) -> {STT_MODEL} ...")
    resp = json.loads(request("/v1/speech-to-text", form=multipart(fields, "file", os.path.basename(a.audio), content)))
    words = scribe_to_words(resp)
    if not words:
        raise ElevenError("Scribe recognized no word in this audio: nothing written")
    dur = duration(a.audio)
    out = os.path.splitext(a.audio)[0] + "-mots.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"duration": round(dur, 2), "words": words}, fh, ensure_ascii=False, indent=1)
    print(f"{len(words)} mots, {dur:.2f} s -> {out}")
    # silences over 0.4 s: each one must become a shot with its own action in the storyboard
    print("silences > 0,4 s : " + ", ".join(f"{s:.2f} à {e:.2f}" for s, e in silences(words)))


def cmd_sfx(a):
    if not NAME.fullmatch(a.name):
        raise ElevenError(f"use a kebab-case name (a-z, 0-9, -) for the sound, not '{a.name}'")
    if a.duration is not None and not 0.5 <= a.duration <= 30:
        raise ElevenError("--duration must be between 0.5 and 30 seconds")
    if not 0 <= a.influence <= 1:
        raise ElevenError("--influence must be between 0 and 1")
    sfx_dir = os.path.join(project_dir(a.project), "assets", "audio", "sfx")
    out = os.path.join(sfx_dir, a.name + ".mp3")
    if os.path.exists(out) and not a.force:
        raise ElevenError(f"{out} already exists (a sound costs credits): pass --force to replace it")
    body = {"text": a.description, "model_id": SFX_MODEL, "prompt_influence": a.influence}
    if a.duration is not None:
        body["duration_seconds"] = a.duration
    print(f"sfx: '{a.description}' ({a.duration or 'auto'} s) ...")
    audio = request("/v1/sound-generation", json_body=body, query={"output_format": "mp3_44100_128"})
    write_bytes(out, audio, a.force)
    credits = os.path.join(sfx_dir, "CREDITS.md")
    new = not os.path.exists(credits)
    with open(credits, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# Sons générés pour ce film (ElevenLabs Sound Effects)\n\n")
        fh.write(f"- `{a.name}.mp3`: {SFX_MODEL}, {now()}, {a.duration or 'auto'} s, influence {a.influence}: "
                 f"« {a.description} »\n")
    print(f"sfx: {out}")
    if any(os.path.exists(os.path.join(LIBRARY_SFX, a.name + ext)) for ext in (".wav", ".mp3")):
        print(f"sfx: '{a.name}' overrides the library sound of the same name for this film")


def parser():
    p = argparse.ArgumentParser(prog="eleven.py", description="ElevenLabs voice, word timings and sound effects.")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tts", help="one take of the voice")
    t.add_argument("project")
    t.add_argument("--voice", default=DEFAULT_VOICE)
    t.add_argument("--model", default=DEFAULT_MODEL)
    t.add_argument("--lang", default="fr")
    t.add_argument("--stability", type=float, default=0.45)
    t.add_argument("--similarity", type=float, default=0.85)
    t.add_argument("--seed", type=int)
    src = t.add_mutually_exclusive_group()
    src.add_argument("--text")
    src.add_argument("--text-file")
    t.add_argument("--out", default="voix.mp3")
    t.add_argument("--format", default="mp3_44100_128")
    t.add_argument("--force", action="store_true")
    s = sub.add_parser("stt", help="word timings of a voice (mots.py format)")
    s.add_argument("audio")
    s.add_argument("--lang", default="fr")
    f = sub.add_parser("sfx", help="one sound effect for this film")
    f.add_argument("project")
    f.add_argument("name")
    f.add_argument("description")
    f.add_argument("--duration", type=float)
    f.add_argument("--influence", type=float, default=0.3)
    f.add_argument("--force", action="store_true")
    return p


def main(argv=None):
    a = parser().parse_args(argv)
    try:
        {"tts": cmd_tts, "stt": cmd_stt, "sfx": cmd_sfx}[a.cmd](a)
    except ElevenError as e:
        print(f"eleven: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    sys.exit(main())
