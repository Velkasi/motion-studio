#!/usr/bin/env python3
"""Single word-timing file of a voice film: every on-screen word with its exact start and end on the voice.

Generic replacement of the hand-written build-minutage.py of each project (EM-Body_reel_4):
1. aligns the on-screen words of the script on the recognized words (eleven.py stt or mots.py), letter by letter, so
   the fragments group by themselves ("M" + "-Body" -> "EMBody", "19" + "%" -> "19 %");
2. a word the voice says differently ("30" read "trente") or skips gets its times interpolated over the free interval
   between its aligned neighbours ("cale": "interpole") and is listed on stderr;
3. a word snaps onto a phrase attack of onsets.py when one sits just before it (-0.05 to +0.4 s), otherwise onto the
   energy dip that precedes it (-140 / +40 ms around the transcription): the animation lands on the word, never after.

Usage:
  python3 minutage.py --text <screen text .txt/.md> --words <voix-montage-mots.json> --onsets <onsets.json> \
      --audio <voix-montage.wav> --out <minutage.json> [--fps 30]
The screen text is the script as it must appear on screen (numbers in digits are fine): one sentence per line or
sentences ended by . ! ? or …; lines starting with # and empty lines are ignored. Words joined by a non-breaking
space (U+00A0) make one screen unit with one start and one end. Re-cut the text and re-run at will.
Output: the schema of EM-Body_reel_4/minutage.json (duration, fps, audio, source, regle, phrases, words, silences).
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import unicodedata

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

SR, HOP = 16000, 80          # energy envelope: 5 ms steps
SILENCE = 0.4                # gaps longer than this are listed as silences


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if c.isalnum() and not unicodedata.combining(c))


def split_sentences(text):
    out = []
    for line in text.replace("\r", "").split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip(" \t")   # a non-breaking space stays: it binds one screen unit
        if not line or line.startswith("#"):
            continue
        out += [s for s in re.split(r"(?<=[.!?…])\s+(?=\S)", line) if s]
    return out


def screen_words(sentence):
    """Words as shown on screen: a token without any letter or digit sticks to its neighbour (« salle ? », « 19 % »);
    words joined by a non-breaking space stay one unit (« 30 minutes »)."""
    words, prefix = [], ""
    for tok in re.split(r"[ \t\n]+", sentence.strip(" \t\n")):
        if not any(c.isalnum() for c in tok):
            if words and not prefix and tok not in ("«", "(", "[", "“"):
                words[-1] += " " + tok
            else:
                prefix += tok + " "
            continue
        words.append(prefix + tok)
        prefix = ""
    if prefix and words:
        words[-1] += " " + prefix.strip()
    return words


def align(screen, stt):
    """For each screen word, (first, last) index of the recognized words that carry its letters, or None."""
    a, a_own, b, b_own = [], [], [], []
    for j, word in enumerate(screen):
        for c in norm(word):
            a.append(c)
            a_own.append(j)
    for i, word in enumerate(stt):
        for c in norm(word):
            b.append(c)
            b_own.append(i)
    hits = [[] for _ in screen]
    sm = difflib.SequenceMatcher(None, "".join(a), "".join(b), autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            hits[a_own[blk.a + k]].append(b_own[blk.b + k])
    stt_len = [len(norm(word)) for word in stt]
    out = []
    for j, word in enumerate(screen):
        n = len(norm(word))
        if not n or 2 * len(hits[j]) < n:
            out.append(None)
            continue
        # a recognized word lending this screen word only a stray letter (« vraiment » added by the voice before
        # « vite ») is left out of its span, unless no recognized word carries half of its own letters here
        per = {i: hits[j].count(i) for i in set(hits[j])}
        keep = [i for i, c in per.items() if 2 * c >= stt_len[i]] or list(per)
        out.append((min(keep), max(keep)))
    return out


def extra_words(spans, stt):
    """Recognized words that no screen word covers and no interpolated screen word stands for: said by the voice,
    absent from the text."""
    extra, prev_last, pending_interp = [], -1, False
    for sp in spans + [(len(stt), len(stt))]:
        if sp is None:
            pending_interp = True
            continue
        if not pending_interp:
            extra += [stt[i] for i in range(prev_last + 1, sp[0])]
        prev_last, pending_interp = max(prev_last, sp[1]), False
    return extra


def envelope_db(path):
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    n = len(x) // HOP
    env = np.sqrt((x[: n * HOP].reshape(n, HOP) ** 2).mean(1) + 1e-12)
    env = np.convolve(env, np.ones(3) / 3, mode="same")
    return 20 * np.log10(env)


def refine(db, t, lo):
    """Energy dip closest before (or just after) t, never before lo (end of the previous word - 20 ms)."""
    a = max(0, int(round(max(lo, t - 0.14) * SR / HOP)))
    b = min(len(db), int(round((t + 0.04) * SR / HOP)))
    if b - a < 2:
        return t
    k = a + int(min(range(b - a), key=lambda i: db[a + i]))
    return round(k * HOP / SR, 3)


def raw_times(flat_words, spans, stt, duration, phrase_starts=(), sentence_first=()):
    """(start, end) per screen word: from the transcription, or interpolated over the free interval. A run of
    interpolated words that opens a sentence starts on the first phrase attack inside that interval, not in the
    silence before it."""
    times = [None if sp is None else (stt[sp[0]]["start"], stt[sp[1]]["end"]) for sp in spans]
    j = 0
    while j < len(times):
        if times[j] is not None:
            j += 1
            continue
        k = j
        while k < len(times) and times[k] is None:
            k += 1
        left = times[j - 1][1] if j > 0 else 0.0
        right = times[k][0] if k < len(times) else duration
        right = max(right, left)
        if j in sentence_first:
            attack = [p for p in sorted(phrase_starts) if left < p < right]
            if attack:
                left = attack[0]
        weights = [max(len(norm(flat_words[i])), 1) for i in range(j, k)]
        total, acc = sum(weights), 0
        for i, wgt in zip(range(j, k), weights):
            s = left + (right - left) * acc / total
            acc += wgt
            times[i] = (s, left + (right - left) * acc / total)
        j = k
    return times


def build(sentences, stt_words, phrase_starts, duration, fps=30, db=None):
    flat = [(si, word) for si, s in enumerate(sentences) for word in screen_words(s)]
    stt = [x for x in stt_words if norm(x["w"])]
    spans = align([word for _, word in flat], [x["w"] for x in stt])
    first = {i for i, (si, _) in enumerate(flat) if i == 0 or flat[i - 1][0] != si}
    times = raw_times([word for _, word in flat], spans, stt, duration, phrase_starts, first)
    starts = sorted(phrase_starts)

    words, prev_end = [], 0.0
    for idx, ((si, text), (s, e), sp) in enumerate(zip(flat, times, spans)):
        if sp is None:
            how = "interpole"
        else:
            snap = [p for p in starts if -0.05 <= s - p <= 0.4 and p >= prev_end - 0.02]
            if snap:
                s, how = snap[0], "attaque"
            elif db is not None:
                s, how = refine(db, s, prev_end - 0.02), "creux"
            else:
                how = "transcription"
        s = max(s, prev_end - 0.02, 0.0)
        words.append({"i": idx, "w": text, "start": round(s, 3), "end": round(max(e, s + 0.08), 3), "phrase": si,
                      "cale": how})
        prev_end = words[-1]["end"]

    phrases = []
    for si, text in enumerate(sentences):
        ids = [x["i"] for x in words if x["phrase"] == si]
        if ids:
            phrases.append({"i": si, "text": text, "start": words[ids[0]]["start"], "end": words[ids[-1]]["end"],
                            "words": [ids[0], ids[-1]]})
    silences = [{"from": a["end"], "to": b["start"], "len": round(b["start"] - a["end"], 3)}
                for a, b in zip(words, words[1:]) if b["start"] - a["end"] > SILENCE]
    if words and duration - words[-1]["end"] > 0:
        silences.append({"from": words[-1]["end"], "to": duration, "len": round(duration - words[-1]["end"], 3)})
    return {"duration": duration, "fps": fps,
            "source": "mots horodatés de la voix montée, alignés lettre à lettre sur le texte écran ; mots calés sur "
                      "l'attaque de leur phrase (onsets.py) ou sur le creux d'énergie qui les précède",
            "regle": "chaque animation démarre au début du mot (0 à 2 images avant), jamais après",
            "phrases": phrases, "words": words, "silences": silences,
            "unaligned": [x["w"] for x in words if x["cale"] == "interpole"],
            "extra": [x["w"] for x in extra_words(spans, stt)]}


def main():
    ap = argparse.ArgumentParser(description="Single word-timing file (minutage.json) of a voice film.")
    ap.add_argument("--text", required=True, help="screen text of the script")
    ap.add_argument("--words", required=True, help="word timings of the edited voice (eleven.py stt / mots.py)")
    ap.add_argument("--onsets", required=True, help="onsets.json of onsets.py on the edited voice")
    ap.add_argument("--audio", required=True, help="edited voice (voix-montage.wav)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()

    sentences = split_sentences(open(a.text, encoding="utf-8").read())
    if not sentences:
        sys.exit(f"minutage: no sentence in {a.text}")
    stt = json.load(open(a.words, encoding="utf-8"))["words"]
    on = json.load(open(a.onsets, encoding="utf-8"))
    duration = on.get("duration") or json.load(open(a.words, encoding="utf-8")).get("duration")
    out = build(sentences, stt, [p["start"] for p in on.get("phrases", [])], duration, a.fps, envelope_db(a.audio))
    out["audio"] = os.path.relpath(a.audio, os.path.dirname(os.path.abspath(a.out))).replace("\\", "/")
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for p in out["phrases"]:
        print(f"{p['start']:6.2f}-{p['end']:6.2f}  " + " ".join(
            f"{out['words'][k]['w']}@{out['words'][k]['start']:.2f}" for k in range(p["words"][0], p["words"][1] + 1)))
    print("silences:", ", ".join(f"{s['from']:.2f}-{s['to']:.2f}" for s in out["silences"]))
    if out["extra"]:
        print(f"minutage: {len(out['extra'])} mot(s) dit(s) par la voix mais absent(s) du texte : "
              + ", ".join(out["extra"]), file=sys.stderr)
    if out["unaligned"]:
        print(f"minutage: {len(out['unaligned'])} mot(s) interpolé(s), à vérifier à l'écoute : "
              + ", ".join(out["unaligned"]), file=sys.stderr)
    print(f"written: {a.out} ({len(out['words'])} words)")


if __name__ == "__main__":
    main()
