# Known pitfalls (and their fix)

Found while making the example films with this exact stack (HyperFrames 0.8.82, HeyGen skills at commit 93ab289), up to
the flagship film `examples/ligne-du-temps-v8/`. The guardrails of `AGENTS.md` (pinned local CLI, telemetry variables
on every `npx hyperframes` command) come first. The items marked BLOCKING are the ones the dispatch template of
`SKILL.md` hands to every worker.

## Timing

- **Whisper alone drifts by a few hundred ms.** The motion reveals words 0 to 2 frames before they are spoken, so a
  late cue is visible. Always take the cues from `onsets.py` (energy onsets), run on the final voice montage.
- **The agent's arithmetic on durations is not reliable** (a documented case announced 299 s and delivered 578 s).
  One source of truth: frame durations in `STORYBOARD.md`, `TOTAL` in `assemble.sh` and `build-audio.sh`. Compute the
  sum with a script, never in your head.
- **A voice cut on a word** clicks or swallows a syllable. Cut only in the middle of a silence (`cut point` printed by
  `onsets.py --no-whisper`), with 5 ms fades on every join (`build-audio.sh` does it). Every cue after a cut moves by the
  silence inserted before it: re-run `onsets.py` on the montage.
- **Same template for 10 s** reads as slow even with content changing inside. Never the same layout for more than 3 s:
  change the framing, the text position and the object, bring elements back as reminders but never in the same frame.
- **Enough shots, not enough events.** A film can cut every 2 s and still feel static: the version before
  `examples/C-le-devis-v7a/` had 4.6 shots per 10 s (in the norm) but a fixed camera 95 % of the time and 31 % of its
  tenths of a second almost still. Write an event every 0.5 to 1 s and a camera track in every shot
  (`patterns/STORYBOARD-CRAFT.md`, laws 1 and 2).

## Frames (workers)

- **BLOCKING. A frame is not masked before its start.** Anything visible by default in its CSS shows during the
  previous frames (transitions overlap them). Every element that is not on screen at t=0 of its frame starts with
  `opacity: 0` in CSS, and every `fromTo` that starts after t=0 has `immediateRender: false`.
- **BLOCKING. Tween transforms only** (`x`, `y`, `scale`, `rotation`, `opacity`, `filter`): never `top`, `left`,
  `width`, `height` (a width that changes is the `scaleX` of a separate background), and never `letterSpacing`:
  frame-by-frame capture rounds it to device pixels and the text shakes (the lint blocks it). For a word whose letters
  tighten: split it into inline-block letters and tween their `x`. On a counting number keep only scale and blur.
- **BLOCKING. No `backdrop-filter`** (frosted glass): use solid colors instead (a card at 97 % opacity).
- **BLOCKING. Every id starts with a letter** and carries the prefix of its frame (`p04-...`): an id that starts with a
  digit breaks CSS selectors, and two frames that use the same id collide once assembled in one page.
- **BLOCKING. Only `.clip` children of the frame root render.** A shared world built by script must be mounted inside a
  `.clip` layer that lasts the whole frame (`<div id="p03-bed" class="clip" data-start="0" data-duration="D">`, then
  build the stage inside it): a stage appended straight to `#root` renders as an empty frame in the engine while the
  same file looks fine in a standalone browser.
- **A `mix-blend-mode` layer inside a group whose opacity is tweened paints flat.** Between 0 and 1 exclusive, Chrome
  isolates the group and the blended layer has nothing to blend with (a dusk overlay turned the illustrations into an
  opaque colour only during the fade). Keep the group at opacity 1 and fade the blended layers themselves. Check a
  fade at a time strictly inside it, never only at its ends.
- **Background on `#root` is not dependable**: at assembly the frame root is clip-gated, a dark frame can land on the
  black host page. The ground is its own full-duration `class="clip"` layer.
- **BLOCKING. Packet over 48 KB** makes `frame-packets.mjs` fail. A blueprint weighs 5 to 29 KB, a rule 5 to 10 KB:
  1 or 2 rules per frame. Every rule id written anywhere in the frame block (for example "(→ cursor-click-ripple)") is
  inlined too, so never write the name of another rule in the block.
- **BLOCKING. An inner `<template id>` placed beside the frame root** (a reusable fragment the frame clones with
  `getElementById(...).content`): the engine only embeds the root element, the lookup returns null and the whole frame
  stays black (two frames of `examples/C-le-devis-v7a/`). The lint does not see it; `npx hyperframes validate` prints
  "Cannot read properties of null (reading 'content')". The inner template lives INSIDE the root.
- **BLOCKING. `style.visibility = "visible"` in a frame**: a child forced visible no longer inherits the hidden state of its
  frame, so it shows over the whole film (frame 09 of the same film covered 0 to 33 s). Always `"inherit"`.
- **Session cuts kill workers mid-write** (two in one afternoon on the same film). Ask each worker to write a complete
  first version early, then refine it; before resuming, `check-frames.py` and re-dispatch only what is MISSING or
  BROKEN (`variants.md` § Resume): 9 frames out of 10 were kept.
- **Two workers, one seam, two images**: without a written handoff, each worker imagines the camera and the objects at
  the seam and the cut jumps. The storyboard writes `handoff_out` of frame N and copies it word for word into
  `handoff_in` of frame N+1 (camera state, blur, world state, objects, light, text); check it with the script of
  `method.md` § 6, then on the render, image by image (§ 12). **BLOCKING**: no element is born or dies in the 2 images
  around a seam, and the seam falls at the top of the blur of a move.
- **Two frames, one decor, two drawings**: when several frames show the same place (a timeline, a quote, a column),
  each worker redraws it a little differently and the seam jumps. The decor is built by ONE function written once in
  `reference/<world>.html` and copied verbatim into each frame; check it with a diff (`method.md` § 8).
- **The camera is one proxy object**, written by ONE `onUpdate` that places the whole world. Never
  `getBoundingClientRect` inside `onUpdate` (it forces a layout at every image and slows the render): measure widths
  once at init.
- **GSAP ease names are one power higher than they read**: `power1` is quadratic, `power2` cubic, `power3` quartic,
  `power4` quintic (`power3.out` = 1 - (1 - t)^4). Compute every mid-gesture handoff value with the real GSAP curve.
  A seam cut in the middle of an `expo.inOut` lands on its peak speed (half the move in one image) and reads as a jump
  unless the blur is strong; `power2.inOut` has the same midpoint (50 %) and a third of the peak speed (reel EM-Body 2).
- **Parallel workers share the session scratchpad**: one overwrote another's harness and rebuilt a sibling frame. Give
  each worker its own subfolder (`scratchpad/p<nn>/`) in the dispatch context.
- **Infinite loops** (`repeat: -1`, an endless yoyo, CSS animations, `Math.random`) break the seek-based render. Finite
  tweens (a living hold repeats `Math.ceil(D / period)` times), randomness derived from the index.
- **The core worker contract forbids narration text on screen** because HeyGen's default pipeline burns captions. This
  method disables captions and shows the sentence itself, word by word: the dispatch template says so explicitly.
- **CSS `transform` on an element that GSAP moves** is silently overwritten (the centering jumps). Center with margins
  or `xPercent` / `yPercent`.
- **BLOCKING. GSAP does not interpolate a `clip-path: polygon()` with many points** (a torn edge, a crumpled sheet): it swaps
  the long string at the end of the tween instead of morphing it. Compute the polygon yourself: tween a proxy value
  from 0 to 1 and, in its setter, interpolate every point between the two shapes and write `el.style.clipPath` at each
  frame (the same number of points in both shapes), or avoid it: `circle()`, `ellipse()` and `inset()` interpolate
  well.
- **BLOCKING. No giant blurred 3D layer**: a blurred plane of several thousand pixels (a floor, a wall) seen in
  perspective is too heavy for the frame-by-frame render. Draw the floor on a canvas, hide any quad whose corner comes too close
  to the camera, no blurred object over 1800 px wide, and a push through an object (zoom-through) hands over to a flat
  2D copy before it passes ×4.
- **A camera pull-back that lasts too long** keeps the enlarged object over the phrase band while its words are being
  written: the first words land under the object. End the pull-back before the first word cue of the phrase, or keep
  the phrase on a layer above the camera that never scales.

## Assembly and transitions

- **The injector knows 5 CSS transitions** (crossfade, blur-crossfade, push-slide, zoom-through, squeeze) plus the cut.
  HeyGen's shader transitions need their whole engine: for the 2 or 3 key moments, use the orchestrator layer (light
  flash, iris) instead.
- **A frame extended under a transition must extend its internal clips too**, otherwise the iris opens on black (the
  frame root lives longer, its clips do not).
- **Two worlds of ground = grey crossfades.** The root is dark, so a crossfade between two light frames passes through
  grey. The paper bed of `assemble.sh` lies under the whole light world.
- **A hard cut must never land on an empty frame.** If the incoming frame fades its content in from opacity 0 at t=0,
  its first frame is just the dark ground and reads as a black flash at the cut (`contact-sheets.sh` flags it as a
  one-frame black). The incoming frame is visible from its first frame (start at opacity 0.7, not 0).
- **The iris ring must be visible at once.** Tween its radius over the whole iris but its opacity 0 to 1 in 0.08 s,
  otherwise the first quarter of the iris is a plain black disc.
- **A silent pivot needs the music out of the way.** When the pivot is a silence (a lone caret in the dark), duck the
  music by about 85 % for that second in `build-audio.sh` (volume expression with `clip()`), then let it come back
  with the light.
- **`index.html` is rebuilt from scratch** by the assembler: never edit it by hand, put every orchestrator change in
  `assemble.sh`.
- **A frame marked `animated` without its HTML file** stops the assembler. `assemble.sh` marks a frame animated only
  when its file exists, so a pilot or a partial build assembles.

## Sound

- **A tension music that sits too low makes the start feel flat.** On the flagship film the tension track (its sparse
  intro) was 10 dB under the élan track: the first seconds felt soft. Take the tension from a full section of its track
  and keep it 2 to 3 dB under the élan at most, measured in LUFS (`music.md`).
- **The music must not crush the voice at the pivot.** It is the moment where a build peaks, and where it most often
  covers the voice. Measure it: 8 dB or more between the voice and the music in the 1.5 s before the pivot, the bass
  (under 150 Hz) near silence between the pivot and the flash. `build-music-options.py` prints both (`music.md`).
- **`alimiter` has a make-up gain on by default** (`level`): after `loudnorm`, it pushes the peaks back near 0 dBFS
  and the film ends above -1.5 dBTP. Use `alimiter=limit=0.79:level=disabled`, and measure with
  `ffmpeg -i mix.wav -af ebur128=peak=true -f null -`.

## Checks

- **Always check the real render**, not only the preview: `contact-sheets.sh` (black segments + 4 images/s sheets).
  A black segment is almost always a clip that ends too early or a frame whose ground is on `#root`.
- **A file rewritten under an open player freezes**: close the QuickTime (or any player) window before replacing a
  delivered MP4 with a new render.
- **A stray element** whose origin is unclear: hide the frames one by one in `index.html` (temporarily) until it
  disappears, then fix that frame.
- **Precise feedback** makes precise fixes: moment, symptom, expected ("at 4 s, the blur passes in front of the text
  instead of behind").

## Look

- No linear motion: curves (`power3.out`, `expo.out`), never bounce or elastic.
- Each entry animates 2 or 3 properties together (position, opacity, scale); 3 to 6 frames of offset between
  elements that enter together; exits faster than entries.
- No gratuitous 3D or effect: the agent tends to add some. "Better no movement than a bad movement."
- Music: a library track can open on a quiet build that drains the first seconds. Start on a stronger, clean section
  (`MUSIC_START`), keep a short fade-in and a 3 s fade-out, volume 0.10 to 0.15 under the voice.

## Landing page

- No browser autoplays a video with sound: the top-of-page video is muted and must read without sound. Offer a silent
  loop of 8 to 18 s (MP4 H.264, 3 to 4 MB, no audio track, with a poster image) plus the full version with the voice,
  opened on click.
- **A textured direction weighs a lot.** Wood grain, film grain and paper textures change at every pixel and every
  frame: the desk variant rendered at 69 MB for 43 s, three times the flat one (21 MB). Never put a render on a site as
  is: re-encode it for the web (`landing-integration.md`; the flat film weighs 5.6 MB at `-crf 24`), and check the
  grain did not turn to mush (lower the `-crf` a little if it did).

## Real footage inside frames (learned on Hydromassage_reel_2, 9:16)

- **A `<video>` created in a frame's script plays only in frame 1.** The render probe finds it in the DOM but reads
  its `data-start` as FILM time and ignores `data-playback-rate`: a frame that starts later renders it black. Cut and
  retime each stretch with ffmpeg into its own file (`setpts`, `minterpolate=fps=30` for slow motion, `-frames:v` for
  an exact length), then set `data-start` to the film time, `data-hf-media-start-basis="global"`,
  `data-media-start="0"`, rate 1. A still of the exact last image takes over where the clip ends.
- **`filter: url(#svg-filter)` on an HTML element is ignored by the renderer** (a directional blur rendered sharp, so a
  whip seam showed both images). Use CSS `blur()` for camera blur; SVG filters inside an `<svg>` (a `<g filter>`) do
  render.
- **The last image of a frame is one frame before its boundary** (2.667 for a seam at 2.70 at 30 fps): a move that must
  peak on the seam ends 1 frame early, or the next frame opens on a jump.
- **A `<video>` written in a frame's HTML is refused by the assembler** (`assemble-index.mjs`: media must sit at the
  root of `index.html`), and a root video cannot follow the frame's camera (push, blur, an object resting on it). When
  the footage must move with the frame, extract it as an image sequence cropped to the plate's cover framing
  (`ffmpeg -ss A -t D -vf crop=W:H:X:0 c%02d.jpg`), write the `<img>` tags statically in the frame and show one per
  frame from `render()` (index = floor(local time × source fps)). Learned on Hydromassage_reel (the closing lid).
- **An image a frame creates by script can be blank on that frame's first image in `snapshot`** (not in the real
  render). Preload every still used after 0 s with hidden static `<img>` in frame 1, and judge a seam on the draft
  render, never on a snapshot alone.
- **A handoff that stops mid-move must give the whole move**: start, target, curve and progress (« cam(1750, 60, 1) →
  cam(1750, -110, 3), power2.in over 0.45 s, 0.39 s done »). Workers never see the neighbouring frame: without the
  target, the next frame guesses and the seam jumps.
- **`hyperframes check` flags a button label as `text_occluded`** when a large fill circle (the press fill) overlaps
  it, even with the label on top (`z-index`). Look at the snapshot: if the label reads, it is a false positive. Never
  stack two copies of the label for a colour change (`content_overlap`): keep one label whose colour contrasts with
  both fills.

## Learned on EM-Body_reel_3 (9:16, world written once in reference/<world>.html)

- **`hyperframes check` counts a full-frame overlay as an opaque occluder** as soon as one gradient stop reaches
  alpha 0.6 (a vignette at `.62` raised `text_occluded` on every headline of the film). Keep overlay stops under 0.6,
  and put `data-layout-allow-occlusion` on the TEXT when the cover is intended (the flag is read on the text element,
  not on the layer that covers it).
- **A Playwright `page.evaluate()` whose expression returns a GSAP timeline hangs, then crashes the tab** ("Target
  crashed"): `tl.seek(t)` returns the timeline. Wrap it: `void window.__timelines[id].seek(t, false)`.
- **Never measure text at init to size a stroke** (`offsetWidth` before the web fonts load gives the fallback width):
  wrap the underlined words in an inline-block span and give the stroke `width: 100%` in CSS.
- **A shared world kit pays off on a 9:16 reel**: one `reference/<world>.html` (CSS block + JS kit + state object
  `st` + one `scApply` in `onUpdate`), rendered to PNG by its own `demo()` states, gave the styleframes for free and
  five parallel workers whose decor stayed byte for byte identical (checked with a block hash after the build).
