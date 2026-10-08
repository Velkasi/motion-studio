# Role: builder (one sequence of one film)

The orchestrator dispatches one `general-purpose` sub-agent per sequence, in the background. The prompt is the
**dispatch template of `.claude/skills/motion-design/SKILL.md`** (section « Dispatch template »), word for word, with
absolute paths, plus the lines below. The builder never sees the conversation, the other films or the other sequences:
its packet, `frame.md` and this contract are its whole world.

## Lines to change in the template

- `canvas: <W>x<H>, 30 fps` — the frame of this film (`meta.json`), not always 1920x1080. For 1080x1920 the subtitle
  band of the house rules moves to y 1500 to 1640 (50 to 56 px, 28 characters at most per chunk) unless `frame.md`
  gives another band; everything else keeps equal side margins of at least 60 px.
- `world: <dark|light>` — from `frame.md`.

## Lines to add under « House rules of this repository »

```
- Family of this film: <famille> (patterns/STYLE-FAMILIES.md, absolute path: <ROOT>/patterns/STYLE-FAMILIES.md).
  Read only its section. Its technique, signatures and bans are binding; when they differ from a generic house rule
  on the look (palette, typography, camera language), the family wins; the BLOCKING rules always win.
- Word cues are minutage.json times: each word appears on its cue (0 to 2 frames early), never late. Do not move a
  cue; if a step cannot fit, shorten the step.
- Media: use only the files of assets/img/ and assets/video/ named in your packet, treated as the family says
  (cut out, framed, annotated, printed, drawn over...). A photo is never left static full frame: it arrives, moves or
  is transformed. Video: a <video> with an id, muted, no crossorigin, timed by the framework attributes (data-start,
  data-duration, data-media-start) and never by .play(); no ancestor carrying data-start
  (<ROOT>/.claude/skills/hyperframes-core/references/variables-and-media.md).
- Fonts: only the files of assets/fonts/ named in frame.md.
- No sound in your file: the orchestrator mixes all sounds.
```

## What the builder returns

Its last action is writing `<film>/compositions/frames/<frame_id>.html` (a single `<template>…</template>`), then one
short answer: the frame id, the key images it checked, anything it could not do. A fix request arrives by SendMessage
with the critic's findings verbatim: fix those, nothing else, rewrite the same file.
