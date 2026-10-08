# Autonomy: no gate, but checkpoints

`motion-design` stops five times for the user. `motion-studio` never does: the critic (`roles/critic.md`) and the
blocking scripts take their place.

## What replaces each gate

| Gate of motion-design | Here |
|---|---|
| 1. Script | the user's script is final: copied word for word, only the voice version is adapted (numbers in letters) |
| 2. Voice | always the user's ElevenLabs voice with the `eleven.py` defaults, one take, never regenerated; `minutage.py` interpolated words are checked against the waveform and listed in `LIVRAISON.md` |
| 3. Storyboard (choice of direction) | `STYLES.json` + `style-distance.py` (exit 0) choose three; per film: critic on styleframes and on the storyboard, `check-cues.py` (exit 0) |
| 4. Animation (pilot) | critic on the pilot, then on the contact sheet of the assembled film |
| 5. Music (by ear) | the background track is given; `check-sfx.py` (exit 0), loudness measured, critic on the render |

Thresholds: every critic criterion at 8/10 or more; 3 rounds at most per checkpoint, then go on and note the reserve.
Blocking scripts (`check-cues.py`, `check-sfx.py`, `style-distance.py`, lint, `check`, `validate`) have no round
limit: fix until they pass.

## When to stop and ask (the only cases)

- No script or no background sound in the call.
- `ELEVENLABS_API_KEY` missing, or ElevenLabs answers 401/403 on TTS (key or Text to Speech permission): say which.
  A 401/403 on the other two calls is not a stop: Speech to Text → `mots.py` (local Whisper, same output); Sound
  Effects → library sounds only. Both are noted in `LIVRAISON.md`.
- `numpy` or `ffmpeg` missing: stop and say which (no pip install from the agent).
- A media file unreadable by ffprobe: go on without it if others remain, stop if it was the only one.
- An action forbidden by `AGENTS.md` would be needed.
- Disk full, or a tool missing (`ffmpeg`, `node_modules` failing `npm ci`).

Never ask for a choice of style, a validation, or "should I continue": decide, write the decision in `STATE.json`
(`"decisions"`), go on.

## STATE.json (in the base folder)

```json
{
  "projet": "embody-reel",
  "frame": [1080, 1920],
  "base": {"preflight": true, "medias": true, "voix": true, "minutage": true, "styles": true},
  "films": [
    {"n": 1, "famille": "storyboard-marketing", "dir": "embody-reel-1-storyboard-marketing",
     "step": "animation", "sequences_done": ["01-accroche"], "rounds": {"storyboard": 1}},
    {"n": 2, "famille": "pop-up-papier", "dir": "embody-reel-2-pop-up-papier", "step": "todo"},
    {"n": 3, "famille": "cinema-lumiere", "dir": "embody-reel-3-cinema-lumiere", "step": "todo"}
  ],
  "decisions": ["frame 9:16: 7 of 9 media are portrait"],
  "reserves": []
}
```

`step` takes the values `todo`, `direction`, `frame`, `storyboard`, `animation`, `sons`, `mix`, `assemblage`, `rendu`,
`done`. Update it after every step, before starting the next.

## Resume after a session cut

Read `STATE.json`, never start over. For the film in progress: `python3 .claude/skills/motion-design/scripts/check-frames.py <film>`
and re-dispatch only the sequences MISSING or BROKEN; finished films (`done`) are not touched. A step half done is
redone from its start (every step is idempotent: files are rewritten).

## Degraded mode (no Agent tool)

When the session cannot dispatch sub-agents (the agent was launched as a sub-agent, e.g. through `@Dev`), build every
sequence yourself, one at a time, following `roles/builder.md`, and judge with `roles/critic.md` yourself, writing
`CRITIQUE.md` the same way. Say it once at the start and in `LIVRAISON.md`: it is slower and the critique is less
independent.

## Cost

Three complete films: several hours and a large token budget. ElevenLabs: exactly 1 voice take, 1 transcription, a few
sounds per film, each generated once. Never several outputs to choose from.
