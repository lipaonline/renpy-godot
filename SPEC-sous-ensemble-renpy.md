# Sous-ensemble commun Ren'Py / Godot — spécification v0.1

[English version](SPEC.md)

## 1. Principe

- **Ren'Py est la référence.** Tout script du sous-ensemble est un script Ren'Py valide. Il doit se dérouler de la même façon dans le lecteur Godot : mêmes répliques, mêmes choix, mêmes variables, même ordre.
- **Les scripts partagés vivent dans `game/story/`.** Ils sont générés à partir des fiches de `contenu/` par `tools/fiches.py` (voir `contenu/LISEZMOI.md`), qui ne produit que ce sous-ensemble : on ne les modifie pas à la main. Godot ne lit que ce dossier. Le code propre à Ren'Py (`gui.rpy`, `screens.rpy`, `options.rpy`, écrans de galerie, etc.) reste dans `game/`, en dehors de `story/`.
- **Tout ce qui sort du sous-ensemble est une erreur.** Le compilateur Godot la signale avec `fichier:ligne`. Il sert donc aussi de linter pour les scénaristes.

## 2. Organisation des fichiers

```
renpy-godot/
├── project.godot, main.tscn   projet Godot (le dossier est aussi un projet Ren'Py)
├── engine/
│   ├── rpy_parser.gd          compilateur .rpy → programme linéaire
│   ├── rpy_interpreter.gd     exécution, variables, historique, retour arrière, état sauvegardable
│   ├── route_explorer.gd      exploration de toutes les routes
│   ├── persistent_data.gd     texte déjà lu, labels atteints, préférences (« persistent »)
│   ├── save_slots.gd          emplacements de sauvegarde et vignettes
│   ├── gallery.gd, assets.gd  galerie, images et vidéos
│   ├── langues.gd             langues (game/langues.json) et traductions (game/tl/)
│   ├── vn_player.gd           lecteur : scène, avance rapide / automatique, sauvegardes, langue
│   └── ui/                    menus principal et de jeu, pages, menu rapide, textes de l'interface
├── contenu/                   bible et fiches de scène : source de vérité du texte
├── tests/                     run_tests.gd (Godot), test_fiches.py (chaîne d'écriture)
├── tools/                     fiches.py (fiches → .rpy), placeholders, vidéos, routes
└── game/                      dossier « game » de Ren'Py, partagé
    ├── story/*.rpy            script du sous-ensemble, généré depuis contenu/
    ├── gui.rpy, screens.rpy,  interface et options Ren'Py (générées par le launcher) ;
    │   options.rpy, gui/      Godot réutilise les images de gui/ pour garder le même aspect
    ├── testcases.rpy          tests automatiques Ren'Py, ignorés par Godot
    ├── galerie.json           entrées de la galerie, lues par les deux moteurs (section 5)
    ├── galerie.rpy            écran et visionneuses de la galerie côté Ren'Py
    ├── langues.json           langues du jeu, lues par les deux moteurs (section 6)
    ├── langues.rpy            réglages de langue côté Ren'Py
    ├── tl/<langue>/           traductions : répliques générées (story/), interface Ren'Py
    ├── images/                « lena sourire.png » = image « lena sourire »
    └── videos/                .webm pour Ren'Py + .ogv pour Godot
```

## 3. Instructions supportées

### Premier niveau (sans indentation)

| Instruction | Syntaxe | Remarques |
|---|---|---|
| Personnage | `define lena = Character(_("Léna"), color="#c8a2ff")` | Le nom est une chaîne, ou `_("…")` pour qu'il soit traduit. Arguments acceptés : `color` (ou `who_color`), `what_color`. |
| Constante | `define x = expression` | Recalculée à chaque chargement, comme dans Ren'Py. |
| Variable | `default x = expression` | Sauvegardée. Une variable ajoutée après coup est initialisée au chargement. |
| Image | `image lena triste = "images/autre_nom.png"` | Facultatif : les fichiers de `game/images/` sont déclarés automatiquement. |
| Label | `label nom:` | En fin de bloc, l'exécution continue sur le label suivant du même fichier. La fin d'un fichier vaut `return`. |

### Dans un label

| Instruction | Syntaxe | Remarques |
|---|---|---|
| Narration | `"Texte"` | Peut finir par `id identifiant`, comme une réplique. |
| Réplique | `lena "Texte"` ou `"Nom libre" "Texte"`, suivis au besoin de `id identifiant` | L'`id` relie la réplique à ses traductions (section 6) ; il doit être unique. |
| Décor | `scene rue_nuit [with dissolve]` | `scene` seul vide l'écran. Retire tous les personnages. |
| Personnage | `show lena sourire [at right] [with dissolve]` | Positions : `left`, `center`, `right`, `truecenter`. Sans `at`, garde la position précédente du même tag (par défaut `center`). |
| Masquer | `hide lena [with dissolve]` | |
| Transition | `with dissolve` | Transitions : `dissolve`, `fade`, `None`. |
| Menu | voir ci-dessous | Une réplique facultative avant les choix. Un choix peut avoir `if condition`. |
| Condition | `if` / `elif` / `else` | |
| Boucle | `while condition:` | Sans `break` ni `continue`. |
| Saut | `jump label`, `call label`, `return` | `return` sans valeur. |
| Affectation | `$ x = …`, `$ x += …`, `$ x -= …`, `$ x *= …` | |
| Vidéo | `$ renpy.movie_cutscene("videos/scene.webm")` | Voir la section 5. |
| Pause | `pause`, `pause 1.5`, `$ renpy.pause(1.5)` | `pause` seul attend un clic. |
| Audio | `play music "audio/theme.ogg" [fadein 1.0] [fadeout 1.0] [loop\|noloop]` | Canaux : `music`, `sound`, `audio`. |
| Arrêt audio | `stop music [fadeout 1.0]` | |
| Divers | `pass`, `window show\|hide\|auto`, `# commentaire` | `window` est ignoré par Godot. |

```renpy
menu:
    lena "Alors… tu restes un peu ?"

    "Lui faire confiance":
        $ relation_lena += 2
        jump ch01_sc03a

    "L'interroger sur la photo" if indice_photo:
        jump ch01_sc03b
```

Un choix dont la condition est fausse n'est pas affiché. Un menu sans aucun choix visible est sauté, comme dans Ren'Py.

### Texte

- `[variable]` insère la valeur d'une variable simple. `[[` produit un crochet littéral.
- Balises converties en BBCode Godot : `{b}`, `{i}`, `{u}`, `{s}`, `{color=#hex}`. Les autres (`{w}`, `{p}`, `{size}`, etc.) sont ignorées côté Godot.

## 4. Expressions

Elles sont traduites de Python vers la classe `Expression` de Godot.

- **Autorisé :** nombres, chaînes `"…"` ou `'…'`, `True`, `False`, `None`, listes `[…]`, `+ - *`, comparaisons, `and`, `or`, `not`, `in`, parenthèses, fonctions `min`, `max`, `abs`, `str`, `int`, `float`.
- **Interdit :** `/`, `//` et `%` (résultats différents entre Python et Godot), accès par point (`persistent.x`, `renpy.random…`), `is`, expression conditionnelle `a if c else b`, `lambda`, compréhensions.
- Toute variable utilisée doit être déclarée par `default` ou `define`, ou affectée par `$`.

## 5. Médias

- **Images :** `game/images/` (sous-dossiers acceptés), en PNG, JPG ou WebP. Le nom de fichier en minuscules donne le nom d'image ; les espaces séparent tag et attributs, comme dans Ren'Py.
- **Vidéos :** le script référence le `.webm`, que Ren'Py lit. Godot lit le `.ogv` (Ogg Theora) de même nom. `python3 tools/convertir_videos.py` génère les `.ogv` manquants ou périmés.
- **Audio :** privilégier le `.ogg` Vorbis, lu par les deux moteurs. Godot ne lit pas l'Opus.
- **Galerie :** `game/galerie.json`, généré depuis le champ `galerie` des fiches, liste les entrées ; Godot le lit dans `engine/gallery.gd`, Ren'Py dans `game/galerie.rpy`. Chaque entrée est débloquée dès que son label a été atteint une fois (`renpy.seen_label` côté Ren'Py). Elle montre soit des images une par une sur fond noir, soit une vidéo ; un clic passe à l'image suivante ou arrête la vidéo. Format :

```json
{"entrees": [
  {"titre": "La confiance de Léna", "label": "ch01_sc03a", "vignette": "lena rougit",
   "video": "videos/lena_scene_01.webm"},
  {"titre": "Le secret de Léna", "label": "ch01_sc03b", "vignette": "lena serieuse",
   "images": ["appartement_soir", "lena serieuse"]}
]}
```

Les tests vérifient que chaque label, image et vidéo cité existe.

## 6. Traductions

Le système de traduction de Ren'Py, restreint comme suit ; le lecteur Godot lit les mêmes fichiers.

- **Langues :** `game/langues.json`, généré depuis la bible (`langues`), liste la langue des fiches et les traductions : `{"source": {"code": "fr", "renpy": "french", "nom": "Français"}, "traductions": [{"code": "en", "renpy": "english", "nom": "English"}]}`. Ren'Py le lit dans `game/langues.rpy`, Godot dans `engine/langues.gd`.
- **Répliques traduites :** `game/tl/<langue>/**/*.rpy`, générés par `tools/fiches.py`. Un bloc `translate <langue> <id>:` contient exactement une réplique (narration ou personnage) : la traduction de la réplique qui porte `id <id>`.

```renpy
translate english ch01_sc02_14e17bdd:

    # lena "Je ne pensais pas que tu viendrais."
    lena "I didn't think you'd come."
```

- **Textes :** les blocs `translate <langue> strings:`, avec des paires `old "…"` / `new "…"`, traduisent les noms des personnages (déclarés avec `_()`), les choix des menus et les titres de la galerie.
- **Réservé à Ren'Py :** les blocs `translate <langue> python:` et `translate <langue> style:` ne concernent que l'interface Ren'Py ; Godot les ignore. Toute autre instruction dans `game/tl/<langue>/` est une erreur côté Godot.
- **Langue par défaut :** la langue des fiches est la langue par défaut de Ren'Py (`config.default_language`). Ses textes d'interface sont traduits dans `game/tl/<langue>/` (le français est fourni, repris des traductions de Ren'Py) ; en anglais, les textes d'interface de Ren'Py sont les originaux. Les textes de l'interface Godot sont dans `engine/ui/traductions_interface.gd`.
- **Choix de la langue :** Préférences → Langue, dans les deux moteurs. Au premier lancement, le jeu prend la langue du système si elle est disponible, sinon celle des fiches.
- Une réplique ou un texte sans traduction s'affiche dans la langue d'origine.

## 7. Hors sous-ensemble

Ces éléments restent réservés aux fichiers Ren'Py situés hors de `game/story/` :

- blocs `python:` et `init python:` ;
- `screen`, `call screen`, `transform` et ATL, `style`, `nvl`, `voice`, `queue`, `layeredimage`, `for` ;
- `translate` dans `game/story/` : les traductions vont dans `game/tl/<langue>/` (section 6) ;
- menus nommés, `set` ;
- attributs d'image dans les répliques (`lena sourire "…"`) : utilisez `show` avant la réplique ;
- `show … behind | zorder | onlayer | as` ;
- chaînes sur plusieurs lignes ;
- `renpy.*`, sauf `movie_cutscene` et `pause`, ainsi que `persistent`.

## 8. Différences connues du prototype Godot

- **Sauvegarde :** la position est enregistrée en « label + numéro d'instruction ». Modifier un label avant le point de sauvegarde peut décaler la reprise ; Ren'Py est plus tolérant.
- **Fonctions du lecteur Godot :** menu principal, menu de jeu, historique (250 répliques), retour arrière (128 interactions), avance rapide limitée au texte déjà lu, avance automatique, 5 pages de 6 emplacements avec vignette, sauvegarde rapide (F5 / F9), préférences et galerie.
- **Retour arrière :** il ne survit pas à un chargement (Ren'Py le conserve dans la sauvegarde). Il n'y a pas non plus d'avance après retour (rollforward).
- **Préférences absentes côté Godot :** « continuer l'avance rapide après un choix », accessibilité. La durée d'avance automatique est calculée plus simplement que dans Ren'Py.
- **Texte déjà lu :** une réplique est identifiée par son `id` quand elle en a un (le même dans toutes les langues), sinon par son label, son personnage et son texte. La corriger la fait redevenir « non lue », comme dans Ren'Py.
- **Galerie :** Ren'Py l'ajoute au menu principal (bouton « Gallery » dans `screens.rpy`, traduit comme le reste de l'interface).
- **Changement de langue en cours de partie :** Godot réaffiche aussitôt la réplique ou le menu en cours dans la nouvelle langue. Les répliques précédentes restent dans l'historique dans la langue où elles ont été affichées.
- **`with` seul :** dans Godot, les transitions ne s'appliquent que sur une ligne `scene`, `show` ou `hide`. Une ligne `with` isolée n'a pas d'effet visuel.
- **`show` :** le nom d'image doit exister tel quel. Godot ne résout pas les attributs partiels comme le fait Ren'Py.
- **`fade` :** Godot fait un fondu depuis le noir, alors que Ren'Py passe au noir puis revient.
- **Sprites :** affichés à leur taille native, réduits seulement s'ils sont plus hauts que l'écran.

## 9. Commandes

| Action | Commande |
|---|---|
| Jouer (Godot) | `godot --path .`, ou ouvrir `project.godot` dans l'éditeur puis F5 |
| Jouer dans une langue (Godot) | `godot --path . -- --langue=en` (pour cette session ; la préférence enregistrée ne change pas) |
| Lecture automatique | `godot --path . -- --choices=1,0` (rang parmi les choix affichés) |
| Parcours d'interface scripté | `godot --path . -- --actions=start,advance,menu:history,back,quit` (liste des actions dans `_run_action`, `engine/vn_player.gd`) |
| Tests Godot | `godot --headless --path . --script res://tests/run_tests.gd` |
| Rapport de routes | `godot --headless --path . --script res://tools/routes.gd` |
| Jouer (Ren'Py) | `$RENPY_SDK/renpy.sh .`, ou via le launcher |
| Lint Ren'Py | `$RENPY_SDK/renpy.sh . lint` |
| Tests Ren'Py | `$RENPY_SDK/renpy.sh . test --overwrite-screenshots` (captures dans `tests/screenshots/`) |
| Médias provisoires | `.venv/bin/python tools/fiches.py provisoires` |
| Fichier de traduction | `.venv/bin/python tools/fiches.py traduire en` |
| Vidéos pour Godot | `python3 tools/convertir_videos.py` |

**Côté Ren'Py (déjà fait) :** l'interface a été générée en 1920×1080 par la commande cachée du launcher, puis complétée par `gui_images` (normale et variante « small phone »). Le `script.rpy` modèle, qui redéfinissait `label start`, a été retiré. Pour régénérer :

```sh
SDK=$RENPY_SDK
$SDK/renpy.sh $SDK/launcher generate_gui "$PWD" --width 1920 --height 1080 --accent "#b48cff" --template $SDK/gui --start
RENPY_VARIANT="small phone" $SDK/renpy.sh . gui_images
$SDK/renpy.sh . gui_images
rm game/script.rpy
```

Dans un test Ren'Py, `advance` interrompt aussi une vidéo en cours, comme un clic du joueur. Le test `video_seule` vérifie donc la lecture du WebM sans clic simulé.

**Export :**

- Godot : ajouter `*.rpy, *.json` aux filtres « fichiers non-ressources » et exclure `*.webm`.
- Ren'Py : `*.ogv` et `*.import` sont exclus par `build.classify` (déjà en place dans `game/options.rpy`).
