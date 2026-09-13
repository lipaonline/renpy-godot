# Sous-ensemble commun Ren'Py / Godot — spécification v0.1

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
│   ├── vn_player.gd           lecteur : scène, avance rapide / automatique, sauvegardes
│   └── ui/                    menus principal et de jeu, pages, menu rapide
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
    ├── images/                « lena sourire.png » = image « lena sourire »
    └── videos/                .webm pour Ren'Py + .ogv pour Godot
```

## 3. Instructions supportées

### Premier niveau (sans indentation)

| Instruction | Syntaxe | Remarques |
|---|---|---|
| Personnage | `define lena = Character("Léna", color="#c8a2ff")` | Arguments acceptés : `color` (ou `who_color`), `what_color`. |
| Constante | `define x = expression` | Recalculée à chaque chargement, comme dans Ren'Py. |
| Variable | `default x = expression` | Sauvegardée. Une variable ajoutée après coup est initialisée au chargement. |
| Image | `image lena triste = "images/autre_nom.png"` | Facultatif : les fichiers de `game/images/` sont déclarés automatiquement. |
| Label | `label nom:` | En fin de bloc, l'exécution continue sur le label suivant du même fichier. La fin d'un fichier vaut `return`. |

### Dans un label

| Instruction | Syntaxe | Remarques |
|---|---|---|
| Narration | `"Texte"` | |
| Réplique | `lena "Texte"` ou `"Nom libre" "Texte"` | |
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
        jump lena_confiance

    "L'interroger sur la photo" if indice_photo:
        jump lena_interrogatoire
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
- **Galerie :** `game/galerie.json` liste les entrées ; Godot le lit dans `engine/gallery.gd`, Ren'Py dans `game/galerie.rpy`. Chaque entrée est débloquée dès que son label a été atteint une fois (`renpy.seen_label` côté Ren'Py). Elle montre soit des images une par une sur fond noir, soit une vidéo ; un clic passe à l'image suivante ou arrête la vidéo. Format :

```json
{"entrees": [
  {"titre": "La confiance de Léna", "label": "lena_confiance", "vignette": "lena rougit",
   "video": "videos/lena_scene_01.webm"},
  {"titre": "Le secret de Léna", "label": "lena_interrogatoire", "vignette": "lena serieuse",
   "images": ["appartement_soir", "lena serieuse"]}
]}
```

Les tests vérifient que chaque label, image et vidéo cité existe.

## 6. Hors sous-ensemble

Ces éléments restent réservés aux fichiers Ren'Py situés hors de `game/story/` :

- blocs `python:` et `init python:` ;
- `screen`, `call screen`, `transform` et ATL, `style`, `nvl`, `voice`, `queue`, `layeredimage`, `translate`, `for` ;
- menus nommés, `set` ;
- attributs d'image dans les répliques (`lena sourire "…"`) : utilisez `show` avant la réplique ;
- `show … behind | zorder | onlayer | as` ;
- chaînes sur plusieurs lignes ;
- `renpy.*`, sauf `movie_cutscene` et `pause`, ainsi que `persistent`.

## 7. Différences connues du prototype Godot

- **Sauvegarde :** la position est enregistrée en « label + numéro d'instruction ». Modifier un label avant le point de sauvegarde peut décaler la reprise ; Ren'Py est plus tolérant.
- **Fonctions du lecteur Godot :** menu principal, menu de jeu, historique (250 répliques), retour arrière (128 interactions), avance rapide limitée au texte déjà lu, avance automatique, 5 pages de 6 emplacements avec vignette, sauvegarde rapide (F5 / F9), préférences et galerie.
- **Retour arrière :** il ne survit pas à un chargement (Ren'Py le conserve dans la sauvegarde). Il n'y a pas non plus d'avance après retour (rollforward).
- **Préférences absentes côté Godot :** « continuer l'avance rapide après un choix », langue, accessibilité. La durée d'avance automatique est calculée plus simplement que dans Ren'Py.
- **Texte déjà lu :** une réplique est identifiée par son label, son personnage et son texte. La corriger la fait redevenir « non lue », comme dans Ren'Py.
- **Galerie :** Ren'Py l'ajoute au menu principal (bouton « Galerie » dans `screens.rpy`) ; son interface reste en anglais pour les autres boutons, faute de traduction du jeu.
- **`with` seul :** dans Godot, les transitions ne s'appliquent que sur une ligne `scene`, `show` ou `hide`. Une ligne `with` isolée n'a pas d'effet visuel.
- **`show` :** le nom d'image doit exister tel quel. Godot ne résout pas les attributs partiels comme le fait Ren'Py.
- **`fade` :** Godot fait un fondu depuis le noir, alors que Ren'Py passe au noir puis revient.
- **Sprites :** affichés à leur taille native, réduits seulement s'ils sont plus hauts que l'écran.

## 8. Commandes

| Action | Commande |
|---|---|
| Jouer (Godot) | `godot --path .`, ou ouvrir `project.godot` dans l'éditeur puis F5 |
| Lecture automatique | `godot --path . -- --choices=1,0` (rang parmi les choix affichés) |
| Parcours d'interface scripté | `godot --path . -- --actions=start,advance,menu:history,back,quit` (liste des actions dans `_run_action`, `engine/vn_player.gd`) |
| Tests Godot | `godot --headless --path . --script res://tests/run_tests.gd` |
| Rapport de routes | `godot --headless --path . --script res://tools/routes.gd` |
| Jouer (Ren'Py) | `~/dev/renpy-8.5.3-sdk/renpy.sh .`, ou via le launcher |
| Lint Ren'Py | `~/dev/renpy-8.5.3-sdk/renpy.sh . lint` |
| Tests Ren'Py | `~/dev/renpy-8.5.3-sdk/renpy.sh . test --overwrite-screenshots` (captures dans `tests/screenshots/`) |
| Médias provisoires | `python3 tools/generer_placeholders.py` |
| Vidéos pour Godot | `python3 tools/convertir_videos.py` |

**Côté Ren'Py (déjà fait) :** l'interface a été générée en 1920×1080 par la commande cachée du launcher, puis complétée par `gui_images` (normale et variante « small phone »). Le `script.rpy` modèle, qui redéfinissait `label start`, a été retiré. Pour régénérer :

```sh
SDK=~/dev/renpy-8.5.3-sdk
$SDK/renpy.sh $SDK/launcher generate_gui "$PWD" --width 1920 --height 1080 --accent "#b48cff" --template $SDK/gui --start
RENPY_VARIANT="small phone" $SDK/renpy.sh . gui_images
$SDK/renpy.sh . gui_images
trash game/script.rpy
```

Dans un test Ren'Py, `advance` interrompt aussi une vidéo en cours, comme un clic du joueur. Le test `video_seule` vérifie donc la lecture du WebM sans clic simulé.

**Export :**

- Godot : ajouter `*.rpy, *.json` aux filtres « fichiers non-ressources » et exclure `*.webm`.
- Ren'Py : exclure `*.ogv` et `*.import` avec `build.classify`.
