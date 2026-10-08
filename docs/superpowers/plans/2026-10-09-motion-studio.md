# Motion Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un agent `Motion` (bandeau d'agents) qui, à partir d'un script, d'un fond WAV, de photos et de vidéos, produit seul trois films de motion design rendus, contrôlés et radicalement différents.

**Architecture:** Un agent utilisateur mince (`~/.claude/agents/motion-studio.md`) qui charge le skill de projet `.claude/skills/motion-studio/` : déroulé autonome, rôles `builder` et `critic` confiés à des sous-agents `general-purpose`, quatre scripts de contrôle déterministes et un catalogue de familles de styles. La production d'un film réutilise la méthode et les outils de `motion-design` sans ses gates humaines.

**Tech Stack:** Python 3 (bibliothèque standard + numpy déjà présent), ffmpeg/ffprobe, HyperFrames 0.8.82 épinglé, ElevenLabs via `eleven.py` uniquement.

**Spec:** `docs/superpowers/specs/2026-10-09-motion-studio-design.md`

## Global Constraints

- Tout `AGENTS.md` s'applique : `npx hyperframes` local uniquement, commandes interdites, `.env` vide à la racine, rien ne quitte la machine sauf `eleven.py` (TTS, STT, SFX), pas de pip, `--local-only`, musique fournie jamais générée.
- Chaque projet vit à la racine du dépôt (`<projet>/`, `<projet>-<n>-<famille>/`), jamais plus bas.
- Scripts Python : bibliothèque standard + numpy, sortie UTF-8 forcée, tests `unittest` lancés par `python3 -m unittest`.
- `minutage.json` garde le schéma d'EM-Body_reel_4 : `duration`, `fps`, `audio`, `source`, `regle`, `phrases[{i,text,start,end,words:[first,last]}]`, `words[{i,w,start,end,phrase,cale}]`, `silences[{from,to,len}]`.
- Repères du storyboard au format existant : `Word cues: mot@<temps local>` sous `## Frame <n> : <titre> · <in> → <out>`.
- Règle des repères : début du mot moins 2 images ≤ repère ≤ début du mot (jamais après).
- Règle des sons : un même son au plus 2 fois par film.
- Distance des styles : chaque paire diffère sur au moins 5 des 6 axes.

## Review Focus

- Script avec des chiffres (« 30 ») et voix lue en lettres (« trente ») : le mot est interpolé sur l'intervalle libre, pas d'erreur.
- La voix ajoute ou saute un mot : les mots non alignés sont interpolés et listés, le minutage reste croissant.
- Fragments de transcription (« M » + « -Body » → « EMBody ») : un seul mot écran couvrant les deux.
- Repères contenant une espace (« salle ?@3.15 », « 19 %@3.71 ») : lus comme un seul repère.
- Son nommé absent de la bibliothèque et du projet : `check-sfx.py` échoue avec le nom.

---

## File Structure

| Fichier | Rôle |
|---|---|
| `.claude/skills/motion-studio/scripts/minutage.py` | minutage générique mot à mot |
| `.claude/skills/motion-studio/scripts/style-distance.py` | contrôle de distance des 3 styles |
| `.claude/skills/motion-studio/scripts/check-cues.py` | repères du storyboard contre le minutage |
| `.claude/skills/motion-studio/scripts/check-sfx.py` | règle des 2 occurrences, fichiers, bornes |
| `.claude/skills/motion-studio/scripts/comparatif.py` | planche des 3 films |
| `.claude/skills/motion-studio/scripts/test_motion_studio.py` | tests des cinq scripts |
| `patterns/STYLE-FAMILIES.md` | catalogue des 12 familles |
| `.claude/skills/motion-studio/SKILL.md` | déroulé autonome |
| `.claude/skills/motion-studio/roles/builder.md`, `roles/critic.md` | contrats des sous-agents |
| `.claude/skills/motion-studio/references/autonomy.md` | seuils, reprise, mode dégradé |
| `~/.claude/agents/motion-studio.md` | agent visible `Motion` |
| `AGENTS.md`, `README.md` | point d'entrée mentionné |

### Task 1: minutage.py

**Files:** Create `scripts/minutage.py`; Test `scripts/test_motion_studio.py` (classe `MinutageTest`).

**Interfaces:** Produces `split_sentences(text) -> list[str]`, `screen_words(sentence) -> list[str]`, `norm(s) -> str`, `align(screen: list[str], stt: list[str]) -> list[tuple[int,int]|None]`, `build(sentences, stt_words, phrase_starts, duration, fps=30, db=None) -> dict`, CLI `--text --words --onsets --audio --out [--fps]`.

- [ ] Step 1: tests — fragments (`["Avec","EMBody,","ça"]` vs `["Avec","M","-Body,","ça"]` → `(1,2)`), chiffre interpolé (`30` vs `trente`, temps = intervalle de `trente`, `cale == "interpole"`), mot sauté, ponctuation isolée rattachée (`"la salle ?"` → `["la","salle ?"]`), découpe de phrases, régression EM-Body_reel_4 (≥ 95 % des mots appariés à une image près).
- [ ] Step 2: `python3 -m unittest .claude/skills/motion-studio/scripts/test_motion_studio.py -v` → FAIL (module absent).
- [ ] Step 3: implémenter (alignement caractère par caractère `difflib.SequenceMatcher`, interpolation proportionnelle au nombre de lettres, calage attaque / creux repris de `EM-Body_reel_4/build-minutage.py`).
- [ ] Step 4: tests → PASS.

### Task 2: style-distance.py

**Interfaces:** `AXES: dict[str, set[str]]`, `distance(a, b) -> int`, `check(data, minimum=5) -> list[str]` (erreurs), CLI `<STYLES.json>` (exit 0 ok, 1 trop proches, 2 fichier invalide).

- [ ] tests : trio valide passe ; paire à 4 axes échoue ; valeur hors liste et famille dupliquée → invalide ; ≠ 3 styles → invalide.
- [ ] implémenter, tests → PASS.

### Task 3: check-cues.py

**Interfaces:** `parse_storyboard(text) -> list[(frame, start, [(word, local_t)])]`, `check(storyboard_text, minutage, fps=30) -> list[str]`, CLI `<film_dir>`.

- [ ] tests : repère à l'heure passe ; repère 1 image après → « en retard » ; 3 images avant → « trop tôt » ; repère `salle ?@3.15` lu entier ; mot inconnu → erreur ; en-têtes `## Frame 1: …` et `## Frame 1 : …`.
- [ ] implémenter, tests → PASS ; lancer sur `EM-Body_reel_4` et noter le résultat.

### Task 4: check-sfx.py

**Interfaces:** `check(events, duration, sfx_dirs, maximum=2) -> list[str]`, CLI `<film_dir> [--max 2]`.

- [ ] tests : 2 occurrences passent, 3 échouent avec le nom ; fichier absent → erreur ; événement après la fin → erreur ; un son du projet masque la bibliothèque. `EM-Body_reel_4` doit échouer (em-pulse).
- [ ] implémenter, tests → PASS.

### Task 5: comparatif.py

**Interfaces:** CLI `<film1> <film2> <film3> --out <jpg> [--height 360]` ; 6 instants (10, 25, 40, 55, 70, 90 % de la plus courte durée), une ligne par film.

- [ ] test : 3 vidéos `testsrc` de 2 s générées par ffmpeg dans un dossier temporaire, la planche existe et mesure 6 × largeur sur 3 × hauteur.
- [ ] implémenter, test → PASS.

### Task 6: patterns/STYLE-FAMILIES.md

12 familles (storyboard marketing, illustration vectorielle, pop-up papier, collage éditorial, isométrique 3D, typographie suisse, doodle, néon tech, infographie data, stickers stop-motion, cinéma lumière, cartoon personnage). Pour chacune : quand elle sert, ligne d'axes au vocabulaire exact de `style-distance.py`, technique HyperFrames, traitement des photos et vidéos, signatures, interdits, polices (fontsource OFL), une séquence exemple. Plus les axes, la méthode de choix d'un trio et 3 trios d'exemple vérifiés par `style-distance.py`.

- [ ] écrire ; extraire les lignes d'axes et vérifier que les 3 trios d'exemple passent le script.

### Task 7: skill motion-studio

`SKILL.md` (préflight, base, voix et minutage, choix des styles, production d'un film × 3, livraison, reprise), `roles/builder.md` (modèle de dispatch de `motion-design` + cadre variable + traitement des médias + isolement), `roles/critic.md` (notes /10, seuil 8, sortie `CRITIQUE.md`), `references/autonomy.md` (`STATE.json`, points de contrôle, mode dégradé, blocages).

- [ ] écrire ; chaque commande citée existe (`grep` des chemins de scripts).

### Task 8: agent et points d'entrée

`~/.claude/agents/motion-studio.md` (`name: Motion`, outils `Read, Write, Edit, Bash, Glob, Grep, Agent`), mention dans `AGENTS.md` et `README.md`, spec mise à jour (format des repères, mix par `build-music-options.py`, `comparatif.py`).

- [ ] écrire ; frontmatter valide (YAML lisible) ; tous les tests du skill passent.

### Task 9: revue finale

- [ ] relecture de l'ensemble par un sous-agent `Reviewer` (scripts + skill + agent) ; corriger ce qui est confirmé.
