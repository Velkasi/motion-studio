# Voice and sound effects with ElevenLabs (API)

The voice is the clock of the whole film: every reveal is cued on it. It is generated through the ElevenLabs API by
`scripts/eleven.py`, the only script of this repository allowed to send anything out (`AGENTS.md`, ElevenLabs
exception). Standard library only, nothing to install.

## The key

`ELEVENLABS_API_KEY`, a Windows user environment variable set by the user (System settings, "Edit the environment
variables for your account", or in their own PowerShell:
`[Environment]::SetEnvironmentVariable("ELEVENLABS_API_KEY", "<key>", "User")`), then the app restarted. Check it
without printing it: `test -n "$ELEVENLABS_API_KEY" && echo key ok`. Never ask for the key in the chat, never write it
in `.env` (the root `.env` stays empty) nor anywhere in the repository. The key needs three permissions: **Text to
Speech**, **Speech to Text**, **Sound Effects**. An HTTP 401 or 403 means a wrong key or a missing permission.

## Prepare the text (agent)

The validated script lives in `<project>/SCRIPT.md` in two forms: the **staged version** (the text with its staging:
the silent gag, the pivot on black, what the screen shows) and the **voice version** under a `## Version voix`
heading (or `## Version à coller`), which carries no staging at all: `eleven.py tts` reads that section, up to the
next heading, and nothing else. Rules for the voice version, with Eleven v4:

- **No pause tags**: v4 has none, and `eleven.py` refuses `<break>` and any SSML tag (it lists the lines). Pauses come
  from punctuation (full stops, commas, `...`) and line breaks, one sentence per line. Long silences (the silent gag,
  the pivot) are made at the montage, never in the text.
- **Few acting tags**, in square brackets (`[sighs]`, `[dry amusement]`, `[lower, slower]`): one or two per film.
  More makes the voice unstable.
- **Numbers in letters** for the voice ("mille euros", "deux point zéro"); the screen keeps "1 000 €", "2.0".
- **Words written as they are**: v4 does not understand phonetic spelling. Write "l'IA", not `/li.a/`.
- A sentence that ends on a past participle ("lancées") can be read as an imperative: turn it another way.

Example (the flagship film, `examples/ligne-du-temps-v8/`):

```
Lundi, tu demandes une modif sur ton site.
Mercredi, le devis tombe : mille euros.
Vendredi... toujours rien.
```

## Generate the voice (agent, the user validates by ear)

```bash
python3 .claude/skills/motion-design/scripts/eleven.py tts <project>
```

One take, the whole text in one call (the intonation carries from one sentence to the next). Defaults: voice
`WeAAwKYcS06VmXw086yZ`, model `eleven_v4`, `language_code` `fr` (set explicitly: left on automatic, a French accent
can drift, often to Canadian French), stability 0.45, similarity 0.85 (v4 takes no style nor speed), MP3 44.1 kHz
128 kb/s (192 kb/s needs the Creator plan: `--format mp3_44100_192`). Output: `<project>/assets/audio/voix.mp3` and `voix.json` (voice, model, settings, seed, date; never the
key). Options: `--voice`, `--model`, `--lang`, `--stability` (lower = more expressive, less stable), `--similarity`,
`--seed`, `--format`.

- **A new take** after a text fix: the same command with `--force` (otherwise it refuses to overwrite a take: each one
  costs credits).
- **One wrong word in a good take** (v4 once read "l'IA" as "Lydia"): regenerate that sentence alone, with the seed of
  the take (read from `voix.json`):
  `eleven.py tts <project> --text "Vendredi... toujours rien." --out phrase-03.mp3`, splice it in the silences around
  it at the montage, then redo the timings (`method.md` § 4), since every cue after it moves.

A paid ElevenLabs plan is required for commercial use of the audio.

**Fallback without the key** (or to try another voice by ear): the ElevenLabs web app, Text to Speech, Eleven v4,
same settings, language set explicitly; paste the voice version in one go, download the MP3 as
`<project>/assets/audio/voix.mp3`. Recording your own voice works the same way (quiet room, phone close to the mouth).

## Word timings (agent)

```bash
python3 .claude/skills/motion-design/scripts/eleven.py stt <project>/assets/audio/voix-montage.wav
```

Always on the EDITED voice (silences already cut), never on the raw take. Scribe v2, word timestamps, no audio event
tags. Writes `voix-montage-mots.json` (`{"duration", "words": [{"w", "start", "end"}]}`, the format of `mots.py`) and
prints the silences over 0.4 s; it rewrites the file at each run (rerun it after every montage change). Offline
fallback with the same output: `scripts/mots.py` (local Whisper). Then `onsets.py --transcript` as in `method.md` § 4.

## Sound effects (agent, the user validates by ear)

Generic sounds come from the library (`.claude/skills/media-use/audio/assets/sfx/`). The signature sound of the film
and any sound the library lacks are generated, one at a time, each validated before the next:

```bash
python3 .claude/skills/motion-design/scripts/eleven.py sfx <project> signature "soft two-tone notification chime, clean, modern UI" --duration 1.2
```

Writes `<project>/assets/audio/sfx/<name>.mp3` (kebab-case name; refuses to overwrite without `--force`) and a credit
line in `assets/audio/sfx/CREDITS.md`. `sfx-events.json` uses the sound by its name; a project sound wins over a
library sound of the same name (the command says so). Describe the sound precisely (material, attack, length, mood);
`--duration` 0.5 to 30 s (auto if omitted), `--influence` 0 to 1 (default 0.3: higher follows the text more strictly).

## After the voice

- **Montage, never regeneration, for the silences**: the silent gag (2 to 3 s), the pivot (about 1.5 s of silence),
  a breath before the end card and a tail of about 4 s. Cut only in the middle of a silence (`onsets.py --no-whisper`
  prints the cut points), 5 ms fades on every join (`build-audio.sh`, `CUTS`).
