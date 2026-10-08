# Motion Studio : un agent autonome, trois films très différents — design

Date : 2026-10-09. Statut : validé en conversation, en relecture.

## Objectif

Un agent qu'on appelle depuis le bandeau d'agents de l'app Claude, à qui on donne **un script, un fond sonore WAV, des
photos et des vidéos**, et qui livre seul, sans aucune question, **trois films de motion design rendus et contrôlés,
radicalement différents** (pas trois habillages d'une même chorégraphie, comme EM-Body_reel_4). L'utilisateur choisit
ensuite celui qu'il préfère.

Il reprend le prompt habituel de l'utilisateur : dossier créé, voix ElevenLabs, moment exact de chaque mot dans un seul
fichier de minutage (chaque animation tombe sur un mot, jamais après), sons générés pour le film (un même son au plus
2 fois), fond sonore fourni, motion design travaillé selon `patterns/STORYBOARD-CRAFT.md`.

## Décisions

- **Autonome de bout en bout.** Aucune gate humaine. L'agent ne s'arrête que s'il est bloqué (clé ElevenLabs absente,
  fichier illisible, script vide). Le rôle de l'utilisateur aux gates de `motion-design` est tenu par un critique
  interne (rôle `critic`).
- **Trois variantes produites à la suite**, chacune avec son propre concept, monde, technique de rendu, palette,
  typographie, caméra, découpage et sons générés. Seule la base audio est partagée : même voix, même `minutage.json`,
  même fond WAV.
- **Styles choisis par l'agent selon le script et les médias**, dans un catalogue de familles, avec un contrôle de
  distance chiffré entre les trois.
- **Une team, un seul agent visible.** `Motion` (niveau utilisateur, donc dans le bandeau avec Dev, Coder, Reviewer,
  Docs) est l'orchestrateur. Les spécialistes sont des rôles (fichiers `roles/*.md`) qu'il confie à des sous-agents
  `general-purpose`, comme le fait déjà le modèle de dispatch de `motion-design`. Le bandeau reste propre.
- **Moteur : HyperFrames uniquement** (épinglé, audité, déterministe). Pas de Remotion, pas de Manim.
- **Musique : celle fournie, jamais générée.** Une seule piste par film, ducking sous la voix, -16 LUFS.
- **Périmètre v1 : le film à voix off.** Les formats calés sur le beat sans voix vus sur prompt-motion.com (sting,
  morphing d'interface, logo reveal, explainer) sont une phase 2 ; le catalogue de styles en garde les techniques.
- **Garde-fous** : tout `AGENTS.md` s'applique (CLI local épinglé, commandes interdites, `.env` vide, rien ne quitte la
  machine sauf `eleven.py`, `--local-only`, pas de pip).

## L'appel

Depuis le bandeau : choisir **Motion**, puis par exemple :

> Script : `C:\…\script.md`. Fond : `C:\…\fond.wav`. Médias : `C:\…\photos\`, `C:\…\rushes\`.

Ou le script collé dans le message. Optionnel : nom du projet, cadre (`9:16`, `16:9`, `1:1`), langue, voix, CTA et
URL. Sans cadre précisé : l'orientation majoritaire des médias fournis (vertical → 1080x1920, sinon 1920x1080).

`Motion` travaille toujours dans le dossier du dépôt (chemins absolus), quel que soit le
dossier de la session. Il doit être l'agent principal de la session : lancé comme sous-agent (par `@Dev`), il n'a pas
l'outil Agent et passe en mode dégradé (il construit les séquences lui-même, une par une, et le signale).

## Déroulé

État persistant dans `<projet>/STATE.json` (étape atteinte par film) : après une coupure de session, l'agent reprend à
l'étape suivante au lieu de tout refaire.

### 0. Préflight et base

1. `test -f .env || cp .env.example .env`, `test -d node_modules || npm ci`, clé présente sans l'afficher.
2. Projet de base `<projet>/` (kebab-case, à la racine) : `inputs/` (script, WAV, médias copiés tels quels),
   `assets/audio/`, `STATE.json`. Ce dossier n'est pas un projet HyperFrames ; il porte ce qui est commun.
3. **Inventaire des médias** : pour chaque photo et vidéo, dimensions, durée, orientation, et une description courte
   de ce qu'elle montre (lecture de l'image ; pour une vidéo, 3 images extraites par ffmpeg). Écrit
   `<projet>/MEDIAS.md`.

### 1. Voix et minutage (commun aux trois films)

1. Texte voix depuis le script (règles de `references/voice-elevenlabs.md` : pas de balise de pause, nombres en
   lettres, ponctuation pour respirer), puis `eleven.py tts`.
2. Pas de montage manuel : silences de début et de fin coupés, voix gardée telle quelle (`voix-montage.wav`).
3. `eleven.py stt` (Scribe v2 ; repli automatique sur `mots.py` si la clé n'a pas la permission Speech to Text), puis
   `onsets.py`, puis **`minutage.py`** (nouveau, voir Composants) → `<projet>/minutage.json`, la seule source de temps.

### 2. Choix des trois styles

1. Lire le script (ton, cible, sujet, pivot), `MEDIAS.md` et `patterns/STYLE-FAMILIES.md`.
2. Retenir 3 familles qui servent ce script et ces médias, et écrire `<projet>/STYLES.json` : pour chacune, la famille,
   le concept en une phrase, et sa valeur sur les 6 axes.
3. **`style-distance.py`** : chaque paire doit différer sur au moins 5 axes sur 6. En dessous, remplacer la famille la
   plus proche et recommencer (3 essais, puis garder le meilleur trio et le noter).

### 3. Production d'un film (répétée pour les films 1, 2 puis 3)

Dossier `<projet>-<n>-<famille>/` à la racine, créé par `new-project.sh` (dimensions du cadre choisi), audio,
`minutage.json` et médias copiés depuis la base. Puis la méthode de `motion-design` étapes 3 à 7, sans gate humaine :

1. **Direction** : une seule direction (celle de la famille), 3 styleframes, `render-styleframes.py`. Critique
   (styleframes) ; sous le seuil, corriger.
2. **`frame.md`** et, si le monde est complexe, `reference/<monde>.html`.
3. **`STORYBOARD.md`** selon `patterns/STORYBOARD-CRAFT.md`, chaque repère écrit comme `« mot »#<index>` du
   `minutage.json`. `check-cues.py` (bloquant), puis critique (grille de 15 points).
4. **Animation** : paquets, pilote (séquence 1, snapshot, critique), puis une séquence par sous-agent `builder` en
   parallèle. Les builders d'un film ne reçoivent que les fichiers de ce film : jamais ceux d'un autre film.
5. **Sons** : `sfx-events.json` calé sur l'image ; bibliothèque locale pour le générique, `eleven.py sfx` pour la
   signature et ce qui manque. `check-sfx.py` (bloquant). Les sons générés pour un film ne sont pas réutilisés par
   les autres.
6. **Mix** : voix + fond WAV (ducking sidechain sous la voix, démarrage choisi par `analyze-music.py` pour poser une
   montée sur le pivot quand la piste en a une) + sons ; `loudnorm` -16 LUFS, -1,5 dBTP.
7. **Assemblage, contrôles, rendu** : `assemble.sh`, `check`, `validate`, snapshots sur les mots clés et chaque
   raccord, critique, rendu brouillon puis `high`, contrôle réel (`contact-sheets.sh`, noirs, `freezedetect`,
   LUFS, durée = voix, flux vidéo et audio). Critique finale.

### 4. Livraison

`<projet>/LIVRAISON.md` : les 3 MP4 (chemin, famille, concept, durée), une planche comparative
`<projet>/comparatif.jpg` (les 3 films au même instant, 6 instants), les notes du critique, les réserves (critères
restés sous le seuil), et les points à vérifier par l'utilisateur (allégations chiffrées, marques citées, droits des
médias). L'agent annonce la fin avec ce résumé.

## Composants

### Agent visible : `~/.claude/agents/motion-studio.md`

Frontmatter : `name: Motion`, description en français qui dit quand l'appeler et qu'il faut le lancer depuis le
bandeau, outils `Read, Write, Edit, Bash, Glob, Grep, Agent`. Corps court : se placer dans le dépôt, lire `AGENTS.md`
puis le skill `motion-studio`, et le suivre. Toute la méthode vit dans le dépôt (versionnée), l'agent n'en est que
l'entrée.

### Skill : `.claude/skills/motion-studio/`

- `SKILL.md` : le déroulé ci-dessus, les commandes, les seuils, les règles de reprise.
- `roles/builder.md` : contrat du sous-agent qui construit une séquence (reprend le modèle de dispatch de
  `motion-design` et ses règles BLOQUANTES, plus : repères en `#index` du minutage, traitement des médias selon la
  famille).
- `roles/critic.md` : contrat du sous-agent critique. Entrées : l'étape, les fichiers ou images à juger, la famille.
  Sortie : `<film>/CRITIQUE.md` (append) avec une note sur 10 par critère, verdict PASSE / À REFAIRE, et les
  corrections précises. Critères : grille de STORYBOARD-CRAFT § 5, règles maison et grille de contrôle de
  `motion-design`, signatures et interdits de la famille, lisibilité, sons. Seuil : 8/10 par critère ; 3 tours de
  correction au plus par point de contrôle, puis on continue et la réserve est notée.
- `references/autonomy.md` : points de contrôle, seuils, mode dégradé, reprise via `STATE.json`, ce qui bloque.

### Catalogue : `patterns/STYLE-FAMILIES.md`

Une douzaine de familles. Pour chacune : ce que c'est, quand elle sert un script, sa valeur sur les 6 axes, sa
technique HyperFrames (couches, caméra, primitives GSAP, blocs du registre utiles), comment elle traite les photos et
les vidéos fournies, ses signatures, ses interdits, un exemple de séquence. Familles de départ : storyboard marketing
(kinetic type + interfaces), illustration vectorielle, pop-up et papier, collage photo éditorial, isométrique 3D,
typographie suisse, doodle / tableau blanc, néon et tech, infographie data, stickers et stop-motion, cinéma et lumière,
cartoon personnage.

Les 6 axes, en valeurs fermées pour être comparables par script :

| Axe | Valeurs |
|---|---|
| `rendu` | vectoriel-plat, papier-physique, photo-composite, 3d-simulee, typographique, trace-main, lumiere |
| `monde` | clair-plat, clair-profond, sombre-plat, sombre-profond |
| `palette` | mono-accent, duo, pastel, sature-pop, naturelle, nuit-neon |
| `typo` | grotesque, serif-editorial, display-condensee, manuscrite, mono, ronde |
| `camera` | travelling-continu, coupes-franches, plan-fixe-pop, zooms-profondeur, panoramique-plan |
| `mouvement` | ressort-net, glisse-douce, image-par-image, impact-rapide, organique |

### Scripts (`.claude/skills/motion-studio/scripts/`, Python bibliothèque standard + numpy déjà utilisé)

- **`minutage.py`** : remplace les `build-minutage.py` écrits à la main. Entrées : script, mots horodatés (format de
  `mots.py` / `eleven.py stt`), `onsets.json`, voix montée. Aligne les mots du script sur les mots reconnus
  (normalisation : casse, ponctuation, accents, nombres ; alignement par séquence), regroupe les fragments (« M » +
  « -Body » → « EMBody », « 19 » + « % » → « 19 % »), cale le premier mot de chaque phrase sur l'attaque réelle et les
  mots intérieurs sur le creux d'énergie qui les précède (fenêtre -140 / +40 ms). Écrit `minutage.json` au schéma
  actuel d'EM-Body_reel_4 (`duration`, `fps`, `phrases`, `words`, `silences`). Signale les mots non alignés.
- **`style-distance.py`** : lit `STYLES.json`, imprime la matrice des distances, code de sortie non nul si une paire
  diffère sur moins de 5 axes.
- **`check-cues.py`** : chaque repère `#index` de `STORYBOARD.md` existe dans `minutage.json` et son temps écrit est
  entre le début du mot moins 2 images et le début du mot (jamais après).
- **`check-sfx.py`** : dans `sfx-events.json`, aucun son plus de 2 fois, chaque fichier existe, aucun événement hors
  de la durée du film.
- **`comparatif.sh`** : planche des 3 rendus au même instant (ffmpeg).

## Tests

- `minutage.py` : sur les données réelles d'EM-Body_reel_4 (script, `voix-montage-mots.json`, `onsets.json`,
  `voix-montage.wav`), le `minutage.json` produit retrouve celui du dépôt à une image près pour au moins 95 % des
  mots ; cas unitaires pour les fragments, les nombres et les mots non alignés.
- `style-distance.py`, `check-cues.py`, `check-sfx.py` : cas passants et cas qui échouent, sur de petits fichiers de
  test.
- Essai complet : un script court (15 à 20 s) avec 3 photos, une vidéo et un WAV ; l'utilisateur juge les trois films.

## Hors périmètre v1

Formats sans voix calés sur le beat ; plusieurs options de musique par film ; révisions après livraison (on reprend
alors le film choisi avec la méthode `motion-design` et ses gates) ; diffusion.

## Coûts

Trois films complets : de l'ordre de 3 fois le temps et les tokens d'un film `motion-design` (plusieurs heures au
total). Les appels ElevenLabs : 1 voix, 1 transcription, quelques sons par film.

## Amendements pendant l'implémentation (2026-10-09)

- **Repères** : le format existant est gardé (`Word cues: mot@<temps local>` sous `## Frame <n> : … · <in> → <out>`),
  lu par `frame-packets.mjs` ; `check-cues.py` apparie les repères aux mots de `minutage.json` dans l'ordre. Pas de
  syntaxe `#index`.
- **Voix** : toujours la voix de l'utilisateur avec les réglages par défaut d'`eleven.py`, **une seule prise**, jamais
  régénérée, ni en entier ni par phrase. Le ton passe uniquement par le texte (ponctuation, quelques balises de jeu).
  Les sons générés : une génération par son, sans essai à choisir.
- **Outils = mesures** : `minutage.py` mesure quand chaque mot est dit, rien d'autre. Le choix des mots animés, des
  regroupements, du découpage, du rythme et du style reste à l'agent, film par film ; il peut recouper le texte
  (espace insécable = une unité écran) et relancer, ou corriger `minutage.json` à l'oreille, en notant la décision.
- **Mix** : `build-music-options.py` du projet avec une seule option (le fond fourni, ducking sous la voix, -16 LUFS) ;
  les sons du pivot sont dans `sfx-events.json` pour que la règle des 2 occurrences les couvre.
- **Planche comparative** : `comparatif.py` (Python, comme les autres scripts) au lieu de `comparatif.sh`.
- **Rôles** : `builder` et `critic` sont des contrats (`roles/*.md`) confiés à des sous-agents `general-purpose`.
