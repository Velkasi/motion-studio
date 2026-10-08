# ElevenLabs Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ElevenLabs (TTS, STT, SFX) the default path of every `motion-design` project through one stdlib script.

**Architecture:** `scripts/eleven.py` holds the three API calls (pure helpers + one `request()` that is the only network
code). The rest of the method is untouched: `stt` writes the exact `mots.py` format, generated sounds land in
`<project>/assets/audio/sfx/` and the two mix templates look there before the media-use library. Docs and `AGENTS.md`
are rewritten around it.

**Tech Stack:** Python 3 standard library (`urllib`, `json`, `argparse`, `unittest`), ffprobe, bash.

**Spec:** `docs/superpowers/specs/2026-10-06-elevenlabs-pipeline-design.md`

## Global Constraints

- No pip, no npm: standard library only. Only `https://api.elevenlabs.io` is contacted.
- Key: `ELEVENLABS_API_KEY` environment variable only; never read from a file, never printed, never written.
- Defaults: voice `WeAAwKYcS06VmXw086yZ`, model `eleven_v4`, `language_code=fr`, stability 0.45, similarity 0.85,
  output `mp3_44100_128`; STT `scribe_v2`; SFX `eleven_text_to_sound_v2`.
- `tts` and `sfx` never overwrite without `--force`; `stt` rewrites its timings like `mots.py`.
- 401/403 → "invalid key or missing permission"; 429/5xx/network → 3 retries with growing wait.
- Root `.env` stays empty; no commit unless the user asks.

## Review Focus

- The key appears in an API error body → the message must show `***`, never the key.
- The API answers 200 with an empty body → nothing written, clear error.
- `SCRIPT.md` voice section wrapped in a code fence (```) → fences dropped, not read aloud.
- A generated sound named like a library sound (`pop`) → the project sound wins, and `sfx` says it overrides.
- `stt` on audio where Scribe recognizes no word → error, no empty timings file.

---

### Task 1: `eleven.py` helpers and network layer

**Files:**
- Create: `.claude/skills/motion-design/scripts/eleven.py`
- Test: `.claude/skills/motion-design/scripts/test_eleven.py`

**Interfaces:**
- Produces: `ElevenError(Exception)`; `api_key() -> str`; `voice_text(markdown: str) -> str`; `check_tags(text: str) -> None`;
  `scribe_to_words(resp: dict) -> list[dict]`; `silences(words, threshold=0.4) -> list[tuple]`;
  `multipart(fields: dict, file_field: str, filename: str, content: bytes) -> (bytes, str)`;
  `request(path, *, json_body=None, form=None, query=None, retries=3) -> bytes`; `write_bytes(path, data, force) -> None`.

- [ ] **Step 1: Write the failing tests** (helpers, key, retries, 401, empty body, overwrite) in `test_eleven.py`
  (see final file in Task 2, classes `HelpersTest` and `RequestTest`).
- [ ] **Step 2: Run** `python3 -m unittest .claude/skills/motion-design/scripts/test_eleven.py -v` → FAIL (no module).
- [ ] **Step 3: Implement** the helpers and `request()` in `eleven.py` (final file in Task 2).
- [ ] **Step 4: Run** the tests → PASS.

### Task 2: `tts`, `stt`, `sfx` commands

**Files:**
- Modify: `.claude/skills/motion-design/scripts/eleven.py`
- Test: `.claude/skills/motion-design/scripts/test_eleven.py`

**Interfaces:**
- Consumes: Task 1 helpers.
- Produces: CLI `eleven.py tts|stt|sfx` (arguments of the spec); `<project>/assets/audio/voix.mp3` + `voix.json`;
  `<audio>-mots.json`; `<project>/assets/audio/sfx/<name>.mp3` + `CREDITS.md` line.

- [ ] **Step 1: Write the failing tests** `CommandsTest`: tts writes file + meta without key and sends `eleven_v4`,
  voice id in URL, `language_code=fr`; tts refuses overwrite with no network call; tts reuses the seed of `voix.json`
  for `--text`; stt writes the `mots.py` format and fails on zero words; sfx rejects a non kebab-case name, writes
  sound + credits, notes a library override.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `cmd_tts`, `cmd_stt`, `cmd_sfx`, `main()`.
- [ ] **Step 4: Run** → PASS.

Final `eleven.py` and `test_eleven.py`: written in full during execution in these two tasks, matching the interfaces
above (the code is the deliverable; this plan is executed inline by the same session that wrote the spec).

### Task 3: generated sounds found by the mix templates

**Files:**
- Modify: `.claude/skills/motion-design/templates/build-audio.sh` (function `sfx_file`, comment of `SFX_DIR`)
- Modify: `.claude/skills/motion-design/templates/build-music-options.py` (function `sfx_file`)
- Modify: `.claude/skills/motion-design/scripts/new-project.sh` (`mkdir` of `assets/audio/sfx`)

New `sfx_file` in `build-audio.sh` (cwd is the project folder):

```python
def sfx_file(name):
    # a sound generated for this film (eleven.py sfx) wins over the shared library
    for folder in ("assets/audio/sfx", env["SFX_DIR"]):
        for ext in (".wav", ".mp3"):
            path = os.path.join(folder, name + ext)
            if os.path.exists(path):
                return path
    sys.exit(f"build-audio: sound effect '{name}' not found in assets/audio/sfx/ nor {env['SFX_DIR']} (.wav or .mp3)")
```

New `sfx_file` in `build-music-options.py`:

```python
def sfx_file(name):
    # a sound generated for this film (eleven.py sfx) wins over the shared library
    for folder in (os.path.join(HERE, "assets", "audio", "sfx"), SFX_DIR):
        for ext in (".wav", ".mp3"):
            f = os.path.join(folder, name + ext)
            if os.path.exists(f):
                return f
    sys.exit(f"build-music-options: sound effect '{name}' not found in assets/audio/sfx/ nor {SFX_DIR} (.wav or .mp3)")
```

- [ ] **Step 1: Non-regression baseline**: copy `premier-film` to the scratchpad (its `sfx_file` equals the template's),
  run `MUSIC= bash build-audio.sh` there, keep `md5sum assets/audio/mix.wav`.
- [ ] **Step 2: Apply** the new `sfx_file` to the templates and to the scratch copy; rerun; same md5 expected.
- [ ] **Step 3: Override check**: in the scratch copy, put a 0.3 s sine as `assets/audio/sfx/pop.wav`; rerun; the mix
  md5 must differ (the project sound is used).
- [ ] **Step 4: new-project.sh**: `mkdir -p "$DST"/assets/{audio/sfx,fonts,icons,img,music}`; run it on a scratch
  path and check the folder exists.

### Task 4: method docs and guardrails

**Files:**
- Modify: `.claude/skills/motion-design/SKILL.md` (preflight, step 2, step 5, references table, scripts row)
- Rewrite: `.claude/skills/motion-design/references/voice-elevenlabs.md`
- Modify: `.claude/skills/motion-design/references/method.md` (§ 3 voice paragraph line 77, § 4 timings)
- Modify: `AGENTS.md` (the "Nothing leaves the machine" rule → ElevenLabs exception)
- Modify: `README.md` (prerequisites, voice section, "Aucune clé d'API" line), `THIRD_PARTY_NOTICES.md` (skills MIT)

- [ ] **Step 1**: edit each file (rule rewritten in place, never two versions side by side).
- [ ] **Step 2**: `grep -rn "web app\|no API key\|never ask for an ElevenLabs key" AGENTS.md .claude/skills/motion-design`
  prints only the fallback mentions.

### Task 5: remove the two unsafe ElevenLabs skills

- [ ] **Step 1**: `npx skills remove setup-api-key update-skills-from-changelog` if the CLI supports it (check
  `skills-lock.json` afterwards); otherwise delete `.agents/skills/<name>`, the `.claude/skills/<name>` link and the
  `skills-lock.json` entries by hand.
- [ ] **Step 2**: `ls .claude/skills .agents/skills` and `skills-lock.json` no longer list them.

### Task 6: real test (with the user's key, a few credits)

- [ ] **Step 1**: scratch project with a `SCRIPT.md` holding one sentence; `eleven.py tts <scratch>`; ffprobe the MP3.
- [ ] **Step 2**: `eleven.py stt <scratch>/assets/audio/voix.mp3`; the words match the sentence.
- [ ] **Step 3**: `eleven.py sfx <scratch> test-chime "soft two-tone notification chime" --duration 1`; ffprobe it.
- [ ] **Step 4**: report the three permissions as confirmed (or which one failed, with the message).
