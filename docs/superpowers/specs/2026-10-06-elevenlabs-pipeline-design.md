# ElevenLabs dans le pipeline motion-design — design

Date : 2026-10-06. Statut : validé en conversation, en relecture.

## Objectif

Rendre l'API ElevenLabs le chemin **par défaut de tout projet** `motion-design` pour trois tâches aujourd'hui manuelles
ou locales : générer la voix (TTS), obtenir les timings au mot (STT) et générer les sons manquants (SFX). Le reste de la
méthode ne change pas.

## Décisions

- **Les 5 gates restent** (script, voix, storyboard, animation, musique et sons). Seul le travail manuel passe par l'API.
- **Voix** : 1 prise par génération, `eleven_v4`, voix `WeAAwKYcS06VmXw086yZ`, `language_code=fr`, stabilité 0,45,
  similarité 0,85 (surchargeables). L'utilisateur valide la prise à l'écoute.
- **Timings** : Scribe v2 (`scribe_v2`, horodatage au mot) ; `mots.py` (Whisper local) reste en secours hors ligne.
- **Sons** : mixte. Bibliothèque locale (`media-use/audio/assets/sfx/`) pour le générique ; ElevenLabs
  (`eleven_text_to_sound_v2`) pour le son signature et ce qui manque. Musique : inchangée (CC0 fournie, jamais générée).
- **Approche** : un script Python en bibliothèque standard (`urllib`), sans pip ni npm.
- **Clé** : uniquement dans la variable d'environnement utilisateur `ELEVENLABS_API_KEY`. Jamais dans `.env` (qui reste
  vide), jamais dans le dépôt, jamais affichée. Permissions requises : Text to Speech, Speech to Text, Sound Effects.

## Composant : `.claude/skills/motion-design/scripts/eleven.py`

Trois sous-commandes, encodage UTF-8 forcé comme les autres scripts.

| Commande | Entrée | Sortie |
|---|---|---|
| `tts <projet> [--voice] [--model] [--lang] [--stability] [--similarity] [--seed] [--text TEXTE \| --text-file F] [--out NOM] [--force]` | section voix de `<projet>/SCRIPT.md` (ou texte fourni) | `<projet>/assets/audio/voix.mp3` (mp3 44,1 kHz 128 kb/s ; 192 kb/s exige le forfait Creator) + `voix.json` (voix, modèle, réglages, seed, date, sans la clé) |
| `stt <audio> [--lang fr]` | voix montée (`voix-montage.wav`) | `<audio>-mots.json` au format de `mots.py` (`{"duration", "words": [{"w","start","end"}]}`) + liste des silences > 0,4 s |
| `sfx <projet> <nom> "description" [--duration S] [--influence X] [--force]` | description | `<projet>/assets/audio/sfx/<nom>.mp3` + ligne dans `assets/audio/sfx/CREDITS.md` |

Règles :

- **Section voix** : premier titre `## Version voix…` ou `## Version à coller…` de `SCRIPT.md`, jusqu'au titre suivant.
  Absente : arrêt avec message. Contient `<break` ou une balise SSML : arrêt et liste des lignes (v4 n'a pas de balise
  de pause ; les silences se font au montage).
- **Régénérer une phrase** : `tts <projet> --text "…" --out phrase-07.mp3`, avec la seed de `voix.json` par défaut.
- **STT** : `timestamps_granularity=word`, `tag_audio_events=false` ; seuls les éléments `type == "word"` sont gardés ;
  durée lue par `ffprobe`.
- **Écriture** : `tts` et `sfx` n'écrasent jamais sans `--force` (une prise ou un son coûtent des crédits) ; `stt`
  réécrit ses timings comme `mots.py` (on le relance après chaque montage). Fichier écrit seulement après une réponse
  200 non vide.
- **Erreurs** : clé absente, arrêt avant tout appel réseau. 401/403 : « clé invalide ou permission manquante
  (TTS / STT / SFX) ». 429 et 5xx : 3 nouvelles tentatives à attente croissante. Aucun message ne contient la clé.
- **Réseau** : uniquement `https://api.elevenlabs.io`.

## Modifications des fichiers existants

| Fichier | Changement |
|---|---|
| `motion-design/templates/build-audio.sh`, `templates/build-music-options.py` | `sfx_file(name)` cherche d'abord `<projet>/assets/audio/sfx/`, puis `SFX_DIR` |
| `motion-design/scripts/new-project.sh` | crée `assets/audio/sfx/` |
| `motion-design/SKILL.md` | étape 2 : `eleven.py tts` puis `eleven.py stt` ; étape 5 : `eleven.py sfx` ; préflight : vérifier `ELEVENLABS_API_KEY` |
| `motion-design/references/voice-elevenlabs.md` | réécrit autour de l'API ; l'app web en secours |
| `motion-design/references/method.md` § 4 | `stt` d'abord, `mots.py` en secours |
| `AGENTS.md` | exception écrite : la clé dans `ELEVENLABS_API_KEY` seulement ; trois appels sortants autorisés, via `eleven.py` seulement ; tout le reste inchangé |
| `README.md`, `THIRD_PARTY_NOTICES.md` | prérequis de la clé ; skills ElevenLabs (MIT) installés dans `.agents/skills/` |
| skills `setup-api-key`, `update-skills-from-changelog` | retirés (dossier, lien `.claude/skills/`, entrée `skills-lock.json`) : le premier écrit la clé dans `.env`, le second ouvre des PR chez ElevenLabs |

Les projets existants gardent leurs copies de `build-audio.sh` ; ils ne profitent des sons générés que si on y reporte
la recherche dans `assets/audio/sfx/` (à la demande).

## Tests

1. `scripts/test_eleven.py` (`unittest`, hors ligne, HTTP simulé) : extraction de la section, refus de `<break>`,
   conversion Scribe vers le format de `mots.py`, arrêt sans clé, refus d'écraser, message 401 sans la clé.
2. Test réel, avec accord préalable : une phrase en TTS, le STT de cette phrase, un son d'1 s, dans le dossier
   temporaire de la session. Confirme les trois permissions de la clé.
3. Non-régression : la recherche de sons modifiée, appliquée à une copie de `premier-film` dans le dossier temporaire,
   donne le même mix qu'avant (comparaison des fichiers).
