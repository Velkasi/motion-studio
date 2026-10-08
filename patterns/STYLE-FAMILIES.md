---
titre: Familles de styles — trois films vraiment différents pour un même script
date: 2026-10-09
usage: skill motion-studio, étape « choix des trois styles » ; contrôle par .claude/skills/motion-studio/scripts/style-distance.py
---

# Familles de styles

`STORYBOARD-CRAFT.md` dit comment écrire un film d'agence ; `PATTERNS.md` dit quoi montrer. Ce fichier dit **à quoi
le film ressemble** : douze familles visuelles, chacune avec sa technique, sa façon de traiter les photos et les vidéos
fournies, ses signatures et ses interdits. Le skill `motion-studio` en choisit trois par script, assez éloignées pour
donner **trois films différents**, pas trois habillages d'une même chorégraphie (le défaut d'EM-Body_reel_4).

## 1. Ce qui ne change jamais, quelle que soit la famille

- La voix et `minutage.json` : chaque animation tombe sur son mot (0 à 2 images avant), jamais après.
- Les 10 lois de `STORYBOARD-CRAFT.md` et sa grille de 15 points. Une famille **adapte** une loi (dit comment elle la
  tient), elle ne la supprime pas : une famille à « plan fixe » garde une dérive lente de la caméra ou du décor ; une
  famille à « coupes franches » les pose sur des mots et les compte (Loi 6), le reste chaîne par objets.
- Les règles maison de `motion-design` : sous-titres lisibles au mot, une chose à regarder à la fois, marges égales,
  zéro décor sans sens, interfaces réelles, fin avec un bouton et un curseur qui clique.
- Les médias fournis apparaissent dans les trois films, traités selon la famille. Jamais une photo posée telle quelle
  en plein cadre sans geste : elle arrive, elle est découpée, cadrée, annotée, transformée.

## 2. Les 6 axes

Chaque famille a une valeur par axe. Deux films sont « différents » s'ils diffèrent sur **au moins 5 axes sur 6**.
Vocabulaire fermé, le même que `style-distance.py` :

| Axe | Ce qu'il mesure | Valeurs |
|---|---|---|
| `rendu` | la matière de l'image | vectoriel-plat, papier-physique, photo-composite, 3d-simulee, typographique, trace-main, lumiere |
| `monde` | le sol et la profondeur | clair-plat, clair-profond, sombre-plat, sombre-profond |
| `palette` | la logique de couleur | mono-accent, duo, pastel, sature-pop, naturelle, nuit-neon |
| `typo` | la voix de la typographie | grotesque, serif-editorial, display-condensee, manuscrite, mono, ronde |
| `camera` | le langage de caméra | travelling-continu, coupes-franches, plan-fixe-pop, zooms-profondeur, panoramique-plan |
| `mouvement` | la sensation du geste | ressort-net, glisse-douce, image-par-image, impact-rapide, organique |

## 3. Les douze familles

Polices : toutes en licence SIL OFL, récupérées comme dans `new-project.sh`
(`https://cdn.jsdelivr.net/fontsource/fonts/<id>@latest/latin-<poids>-normal.woff2` vers `<film>/assets/fonts/`).
« Image-par-image » se fait en GSAP avec `ease: "steps(n)"` ou des positions tenues 2 images (`8 i/s` simulés), jamais
avec une animation CSS.

### storyboard-marketing — Storyboard marketing

- **Axes** : `rendu=typographique monde=clair-plat palette=mono-accent typo=grotesque camera=travelling-continu mouvement=ressort-net`
- **Quand** : une offre, un produit, un service avec une promesse claire ; un public pro ; un script à bénéfices.
- **Technique** : un monde blanc cassé où la caméra voyage d'une station à l'autre (Loi 1), kinetic type mot à mot,
  cartes d'interface réelles, curseur qui clique, chiffres qui roulent, objet-pont entre chaque séquence. Ressorts
  courts (`back.out(1.2)` au plus), `expo.out` sur les arrivées.
- **Médias** : photos en cartes arrondies à ombre douce, recadrées sur le sujet de la phrase, annotées (cercle, flèche
  tracée, étiquette) ; vidéos en vignettes vivantes dans une interface, ou plein cadre quelques secondes puis réduites
  en carte.
- **Signatures** : un mot clé en boîte de l'accent ; un trait sous le mot fort ; une ligne-guide qui relie les stations.
- **Interdits** : dégradés, néon, illustrations, plus d'un accent, mots géants.
- **Polices** : `inter` ou `instrument-sans` (400–700).
- **Exemple de séquence** : « 4 séances » — la carte photo glisse à gauche, le chiffre 4 roule de 0 à 4 dans une pastille
  accent, quatre points se cochent au mot « séances », la caméra file vers la station suivante.

### illustration-vectorielle — Illustration vectorielle

- **Axes** : `rendu=vectoriel-plat monde=clair-profond palette=pastel typo=ronde camera=panoramique-plan mouvement=organique`
- **Quand** : un sujet humain, du bien-être, de l'éducation, un service grand public, un ton chaleureux.
- **Technique** : décor en SVG dessiné dans la page (formes simples, 3 plans de parallaxe), personnages en SVG avec
  membres sur pivots, panoramique latéral continu d'une scène à l'autre, transitions par objets qui se transforment
  (interpolation de `d` entre deux chemins au même nombre de points, ou échelle + masque).
  Mouvements organiques : `sine.inOut`, légers dépassements, respiration des formes.
- **Médias** : photos détourées et posées dans une fenêtre ou un cadre dessiné, avec un liseré épais ; ou passées en
  aplats (filtre `grayscale` + `mix-blend-mode: multiply` sur un aplat pastel) ; vidéos dans un écran de téléphone ou
  une bulle dessinée.
- **Signatures** : formes molles qui respirent ; soleil, plante, ou objet dessiné qui revient d'une scène à l'autre.
- **Interdits** : interfaces austères plein cadre, néon, noir pur, coupes franches.
- **Polices** : `nunito` ou `fredoka` (titres), `nunito` (sous-titres).
- **Exemple** : « sans douleur » — le personnage s'étire sur un tapis, un cœur dessiné bat doucement, la caméra glisse
  vers la droite où le mot arrive porté par une forme ronde.

### pop-up-papier — Pop-up et papier

- **Axes** : `rendu=papier-physique monde=clair-profond palette=sature-pop typo=display-condensee camera=plan-fixe-pop mouvement=impact-rapide`
- **Quand** : un ton ludique, un lancement grand public, un événement, un script court et rythmé.
- **Technique** : un livre ou une scène en carton : éléments qui se déplient (`rotationX` de -90 à 0 avec
  `transformOrigin: bottom`, `perspective` sur le parent), couches de papier avec ombre portée nette décalée, texture
  de grain en SVG `feTurbulence`. Caméra presque fixe qui dérive lentement ; les changements viennent des pages qui se
  tournent ou se plient (objet-pont = la page).
- **Médias** : photos imprimées sur carton, découpées avec un bord blanc irrégulier (clip-path `polygon` fixe, jamais
  interpolé), qui se dressent ; vidéos dans une fenêtre découpée dans la page.
- **Signatures** : le pli qui se lève sur le mot ; une languette tirée qui fait bouger un élément ; le titre en lettres
  découpées qui tombent et rebondissent une fois.
- **Interdits** : flou de caméra excessif, néon, verre, plus de trois couleurs saturées.
- **Polices** : `anton` ou `bebas-neue`.
- **Exemple** : « Avec EMBody, ça existe » — la page se tourne, un comptoir de clinique se déplie, le logo se dresse en
  carton au mot « EMBody ».

### collage-editorial — Collage éditorial

- **Axes** : `rendu=photo-composite monde=clair-plat palette=duo typo=serif-editorial camera=coupes-franches mouvement=image-par-image`
- **Quand** : mode, beauté, culture, lifestyle ; beaucoup de photos fournies ; un ton magazine.
- **Technique** : composition de magazine : photos détourées en noir et blanc, un aplat de couleur duo, gros titres
  serif, éléments déchirés, rubans adhésifs, gribouillis tracés. Coupes franches posées sur des mots (quota de la
  Loi 6 relevé et compté), mouvement en image-par-image (`steps(4)`), petites rotations.
- **Médias** : la matière principale : détourer (`media-use` remove-background en local si besoin), coller, empiler ;
  vidéos en vignettes décalées, accélérées, saccadées.
- **Signatures** : une main ou un ciseau qui entre ; la photo qui se déchire pour révéler la suivante ; un mot souligné à
  la main.
- **Interdits** : interfaces logicielles plein cadre, travelling 3D, néon.
- **Polices** : `playfair-display` ou `dm-serif-display`, `inter` pour les petits textes.
- **Exemple** : « une silhouette plus dessinée » — la photo avant se déchire en diagonale, la photo après apparaît
  dessous, un contour tracé à la main suit la silhouette mot par mot.

### isometrique-3d — Isométrique 3D

- **Axes** : `rendu=3d-simulee monde=sombre-profond palette=duo typo=mono camera=panoramique-plan mouvement=glisse-douce`
- **Quand** : technologie, processus, logistique, une explication en étapes, un produit à démonter.
- **Technique** : plateau isométrique en CSS 3D (`rotateX(55deg) rotateZ(45deg)` sur le plateau, éléments extrudés par
  couches), caméra qui glisse d'un îlot à l'autre, éléments qui montent du sol. Pas de Three.js sauf objet unique.
- **Médias** : photos sur des panneaux posés sur le plateau, vidéos sur des écrans isométriques.
- **Signatures** : la tuile qui monte du sol au mot ; un flux de petits cubes qui relie les îlots.
- **Interdits** : texte en perspective illisible (les sous-titres restent à plat), plus de deux couleurs vives.
- **Polices** : `jetbrains-mono` et `space-grotesk`.
- **Exemple** : « des milliers de contractions » — un îlot muscle s'élève, des centaines de cubes pulsent en vagues.

### typographie-suisse — Typographie suisse

- **Axes** : `rendu=typographique monde=clair-plat palette=duo typo=grotesque camera=coupes-franches mouvement=impact-rapide`
- **Quand** : manifeste, annonce forte, script court et tranché, marque sobre.
- **Technique** : grille stricte, texte immense en blocs alignés, rouge et noir sur blanc, changements de grille sur les
  mots, masques rectangulaires qui révèlent, coupes franches comptées.
- **Médias** : photos en blocs rectangulaires de la grille, contrastées, en noir et blanc avec l'accent en aplat.
- **Signatures** : la grille qui se recompose au mot ; un carré rouge qui traverse.
- **Interdits** : ombres, arrondis, illustrations, flou décoratif.
- **Polices** : `archivo` (800) ou `inter` (800).
- **Exemple** : « Résultat : » — tout le cadre bascule dans une nouvelle grille, le mot occupe la colonne gauche.

### doodle-tableau — Doodle, tableau blanc

- **Axes** : `rendu=trace-main monde=clair-plat palette=mono-accent typo=manuscrite camera=panoramique-plan mouvement=image-par-image`
- **Quand** : explication, pédagogie, un concept à rendre simple, un ton humble.
- **Technique** : traits SVG tracés en direct (`stroke-dashoffset`), papier blanc ou quadrillé, la caméra glisse sur une
  grande feuille, croquis qui tremblent légèrement (2 variantes de tracé en alternance, `steps`).
- **Médias** : photos collées sur la feuille avec un trait de contour dessiné autour ; vidéos dans un cadre crayonné.
- **Signatures** : la flèche dessinée qui relie deux idées ; le mot clé entouré à la main.
- **Interdits** : dégradés, ombres réalistes, interfaces austères.
- **Polices** : `caveat` ou `patrick-hand`, `kalam`.
- **Exemple** : « sans chirurgie » — un scalpel dessiné se fait barrer d'un trait rouge au mot.

### neon-tech — Néon et tech

- **Axes** : `rendu=lumiere monde=sombre-profond palette=nuit-neon typo=mono camera=zooms-profondeur mouvement=glisse-douce`
- **Quand** : technologie, appareil, performance, nuit, énergie.
- **Technique** : fond nuit, lignes lumineuses (SVG + `filter: drop-shadow`), particules finies, HUD sobre, zooms dans la
  profondeur d'une couche à l'autre, éléments qui s'allument.
- **Médias** : photos en duotone froid avec un balayage lumineux qui les révèle ; vidéos assombries, cadre HUD.
- **Signatures** : le balayage de scan ; un tracé lumineux qui suit un contour.
- **Interdits** : plus de deux teintes néon, glow sur les sous-titres, `backdrop-filter`, flou géant.
- **Polices** : `jetbrains-mono`, `space-grotesk`.
- **Exemple** : « 30 minutes » — un anneau lumineux se remplit pendant que le chiffre roule.

### infographie-data — Infographie data

- **Axes** : `rendu=vectoriel-plat monde=sombre-plat palette=duo typo=grotesque camera=zooms-profondeur mouvement=ressort-net`
- **Quand** : un script qui contient des chiffres, des comparaisons, des pourcentages, des étapes.
- **Technique** : graphiques qui se construisent (barres, anneaux, courbes tracées), chiffres qui roulent, zooms sur une
  donnée puis recul vers la vue d'ensemble, légendes courtes.
- **Médias** : photos en vignettes rondes rattachées à un point de donnée ; vidéos en fond assombri derrière un chiffre.
- **Signatures** : le chiffre qui roule et se pose ; la barre qui pousse l'élément suivant.
- **Interdits** : graphiques sans valeur réelle, compteurs qui ne disent rien, 3D décorative.
- **Polices** : `inter` (400–800), chiffres tabulaires.
- **Exemple** : « -19 % de graisse, +16 % de muscle » — deux barres se répondent, la seconde pousse la première.

### stickers-stop-motion — Stickers et stop-motion

- **Axes** : `rendu=papier-physique monde=clair-plat palette=sature-pop typo=ronde camera=plan-fixe-pop mouvement=image-par-image`
- **Quand** : réseaux sociaux, public jeune, ton drôle, produit du quotidien.
- **Technique** : stickers à bord blanc épais qui se collent (échelle 1.3 → 1 en 2 images), légère rotation, animation en
  image-par-image, fond uni coloré qui change par séquence, caméra fixe qui « tressaute » d'un cran sur les mots forts.
- **Médias** : photos détourées en stickers ; vidéos dans un sticker-écran.
- **Signatures** : le sticker qui se décolle par un coin ; une pile qui grandit.
- **Interdits** : flou de profondeur, travelling, typographie sérieuse.
- **Polices** : `fredoka`, `baloo-2`.
- **Exemple** : « tu reprends ta journée » — trois stickers (café, sac, clés) se collent sur les trois mots.

### cinema-lumiere — Cinéma et lumière

- **Axes** : `rendu=photo-composite monde=sombre-profond palette=naturelle typo=serif-editorial camera=zooms-profondeur mouvement=glisse-douce`
- **Quand** : luxe, soin, émotion, hospitalité ; de belles vidéos fournies.
- **Technique** : les vidéos et photos plein cadre en mouvement lent (Ken Burns travaillé, `hyperframes-keyframes`),
  bandes cinéma, lumière qui balaie, grain fin, typographie serif posée avec élégance, fondus de lumière plutôt que de
  noir.
- **Médias** : la matière principale, étalonnée de façon cohérente (`media-use` grade en local), recadrée au sujet de
  chaque phrase.
- **Signatures** : la poussée lente vers le visage ; la lumière qui révèle le mot.
- **Interdits** : interfaces plein cadre, stickers, couleurs saturées, coupes nerveuses.
- **Polices** : `cormorant-garamond` ou `playfair-display`, `inter` (300) pour les sous-titres.
- **Exemple** : « une silhouette plus dessinée » — lente poussée sur la vidéo, un trait de lumière suit la courbe.

### cartoon-personnage — Cartoon personnage

- **Axes** : `rendu=vectoriel-plat monde=clair-profond palette=sature-pop typo=ronde camera=coupes-franches mouvement=organique`
- **Quand** : une histoire avec un héros, une situation du quotidien, un ton humoristique.
- **Technique** : un personnage récurrent en SVG (squash and stretch, anticipation, clignement), décors simples,
  coupes franches de plan de dessin animé sur les mots, réactions exagérées.
- **Médias** : photos dans le monde du personnage (une affiche au mur, un écran qu'il regarde) ; vidéos sur un téléphone
  qu'il tient.
- **Signatures** : le personnage qui réagit au mot ; un objet qui le suit d'une scène à l'autre.
- **Interdits** : réalisme, néon, interfaces austères, plus d'un personnage principal.
- **Polices** : `baloo-2`, `nunito`.
- **Exemple** : « sans passer ta vie à la salle » — le personnage soulève un haltère, s'écroule, un chrono géant éclate.

## 4. Choisir le trio pour un script

1. **Lire** le script (ton, cible, sujet, chiffres, présence d'un pivot) et `MEDIAS.md` (combien de photos et de
   vidéos, de quoi, de quelle qualité).
2. **Classer** les douze familles par adéquation (la ligne « Quand ») : écarter celles qui trahissent le sujet (pas de
   cartoon pour un soin médical sérieux sans raison, pas de néon pour une boulangerie).
3. **Prendre la meilleure**, puis la meilleure parmi celles à 5 axes ou plus d'elle, puis la meilleure à 5 axes ou plus
   des deux premières.
4. **Écrire** `<projet>/STYLES.json` (famille, concept en une phrase propre à ce script, axes copiés de ce fichier) et
   lancer `style-distance.py` ; s'il échoue, remplacer la famille la plus proche et recommencer.
5. Varier aussi ce qui n'est pas dans les axes : la métaphore centrale (Loi 7), l'objet-pont, la façon de montrer le
   produit et la fin. Deux films ne partagent jamais une métaphore.

## 5. Trios d'exemple (vérifiés par `style-distance.py`)

| Trio | Familles | Pour |
|---|---|---|
| A | storyboard-marketing, illustration-vectorielle, pop-up-papier | service grand public, ton positif |
| B | cinema-lumiere, doodle-tableau, infographie-data | soin, explication, chiffres |
| C | neon-tech, collage-editorial, cartoon-personnage | appareil, lifestyle, ton drôle |
