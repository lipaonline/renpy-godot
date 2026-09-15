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
│   ├── characters.gd          fiches des personnages (game/personnages.json)
│   ├── renommages.gd          renommages appliqués aux anciennes sauvegardes (game/renommages.json)
│   ├── temps.gd               modèle de temps et son affichage (game/temps.json)
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
    ├── tests_outils.rpy       outils des tests Ren'Py générés : boutons activés par leur texte (focus + Entrée), pas par la position de la souris
    ├── galerie.json           entrées de la galerie, lues par les deux moteurs (section 5)
    ├── galerie.rpy            écran et visionneuses de la galerie côté Ren'Py
    ├── personnages.json       fiches des personnages : jauges, compétences, relations, lu par les deux moteurs (section 5c)
    ├── personnages.rpy        écran « Personnages » du menu de jeu côté Ren'Py
    ├── renommages.json        variables et labels renommés depuis une version publiée, lu par les deux moteurs (section 8)
    ├── sauvegardes.rpy        côté Ren'Py des renommages : label_overrides et rappel après chargement
    ├── temps.json             modèle de temps (créneaux, jours, semaine), lu par les deux moteurs (section 5d)
    ├── temps.rpy              écran Ren'Py affichant le jour et le créneau
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
| Carte | `$ naviguer("ville")`, `$ naviguer("immeuble", "hall")` | Affiche la carte de navigation (section 5b) : le joueur choisit un lieu, qui saute à sa scène. Le second argument, facultatif, est le lieu où l'on est, mis en évidence sur la carte. |
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

### 5b. Navigation : cartes, pièces et présence des personnages

`game/navigation.json`, généré depuis la bible (`cartes`, `presence`), décrit les cartes de navigation. Godot le lit dans `engine/navigation.gd`, Ren'Py dans `game/navigation.rpy`, qui définit aussi la fonction `naviguer()` et l'écran `carte`. `$ naviguer("ville")` (fiche : `carte: ville`) fait la même chose dans les deux moteurs :

1. le lieu de chaque personnage est recalculé : la première règle `presence` dont la condition est vraie donne le lieu, rangé dans la variable `lieu_<personnage>` (déclarée par `default lieu_lena = ""` dans le script généré), que les scènes peuvent tester ;
2. la carte attend que le joueur choisisse un lieu, qui saute à son label. Un lieu peut aussi ouvrir une sous-carte (les pièces d'un bâtiment), affichée sur place, avec un bouton « ← carte parente ».

Deux affichages : `"affichage": "carte"` est une image plein écran avec les lieux placés dessus (`x`, `y` en pourcentage) ; `"pieces"` est une rangée d'icônes rondes des pièces en bas à gauche de l'écran, par-dessus la scène en cours ou l'image de la carte (le nom de la pièce apparaît au survol ; une icône ronde de la carte parente fait sortir du bâtiment). Dans les deux cas, chaque lieu montre les personnages qui s'y trouvent (leur image `avatar`, sinon leur nom dans leur couleur) ; un lieu qui ouvre une sous-carte montre les personnages de toutes ses pièces ; le lieu donné en second argument de `naviguer` est mis en évidence (« vous êtes ici »). Un lieu dont le `si` est faux n'est pas affiché. Pendant toute scène dont le label se joue dans une pièce d'une carte `pieces` (`"scenes"` : label → lieu), la rangée reste affichée sans clic, au-dessus de la boîte de dialogue (Ren'Py : écran permanent `pieces_permanentes` ; Godot : même nœud en mode permanent). Les conditions (`si`) utilisent le sous-ensemble d'expressions (section 4). Format :

```json
{"cartes": {
   "ville": {"titre": "La ville", "affichage": "carte", "image": "carte_ville", "parent": "",
             "lieux": [{"lieu": "immeuble", "nom": "L'immeuble", "icone": "", "x": 50, "y": 36,
                        "label": "", "carte": "immeuble", "si": ""},
                       {"lieu": "cafe", "nom": "Le café", "icone": "", "x": 80, "y": 66,
                        "label": "ch02_cafe", "carte": "", "si": "moment != \"soir\"", "temps": {"creneaux": 1}, "raccourci": false}]},
   "immeuble": {"titre": "L'immeuble", "affichage": "pieces", "image": "", "parent": "ville",
                "lieux": [{"lieu": "hall", "nom": "Le hall", "icone": "icone_hall", "x": 50, "y": 50,
                           "label": "ch02_hall", "carte": "", "si": "heure < 2"}]}},
 "raccourcis": [{"lieu": "appartement_pere", "nom": "L'appartement de mon père", "carte": "appartement", "label": "",
                 "si": "moment != \"soir\"", "temps": null, "raccourci": true, "carte_origine": "immeuble"}],
 "scenes": {"ch02_hall": "hall", "ch02_cafe": "cafe"},
 "personnages": {
   "lena": {"nom": "Léna", "couleur": "#c8a2ff", "avatar": "lena avatar", "variable": "lieu_lena",
            "presence": [{"lieu": "appartement_lena", "si": "heure == 0"}, {"lieu": "cafe", "si": ""}]}}}
```

Les sous-cartes s'emboîtent sans limite ; chaque carte affiche un fil d'Ariane de ses cartes parentes (cliquable, sans coût). Le `temps` d'une entrée ({creneaux: n} ou {jours: n}) est payé au clic, en exécutant tout de suite les labels du temps générés (Ren'Py : `renpy.call_in_new_context` ; Godot : `Interpreter.apply_costs`), si bien que les conditions de la sous-carte ouverte s'évaluent après le voyage ; les explorateurs de routes font de même. `raccourcis` liste les entrées marquées `raccourci`, proposées sur toute carte qui ne porte pas déjà le lieu. Une carte sans aucun lieu accessible est sautée, comme un menu sans choix visible (`verifier` le signale). Titres, noms de lieux et noms de personnages sont traduits comme les autres textes (`translate strings`). La carte est une interaction comme un menu : le retour arrière et les sauvegardes fonctionnent dessus ; une sauvegarde rouvre la carte demandée, pas la sous-carte qui était ouverte.

### 5c. Fiches des personnages : jauges, compétences et relations

`game/personnages.json`, produit depuis la bible (`jauges`, `competences`, `relations` de chaque personnage), décrit l'écran « Personnages » du menu de jeu. Godot le lit dans `engine/characters.gd` et l'affiche dans `engine/ui/characters_page.gd`, Ren'Py dans `game/personnages.rpy` (écran `personnages`, bouton « Personnages » du menu de jeu). Chaque jauge ou compétence lit une variable du jeu, `<personnage>_<nom>`, déclarée par `default` dans le script généré et traitée comme toute variable (sauvegardes, retour arrière, `$ x += 1`, conditions). Format :

```json
{"personnages": {
   "lena": {"nom": "Léna", "couleur": "#c8a2ff", "avatar": "lena avatar",
            "jauges": [{"variable": "lena_relation", "nom": "Relation", "min": 0, "max": 10,
                        "paliers": [{"des": 0, "nom": "distante"}, {"des": 6, "nom": "amie"}]}],
            "competences": [{"variable": "lena_photographie", "nom": "Photographie", "min": 0, "max": 5,
                             "paliers": []}],
            "relations": [{"variable": "lena_karim", "avec": "karim", "nom": "Karim", "couleur": "#f2b45c",
                           "min": 0, "max": 10, "paliers": [{"des": 4, "nom": "collègues"}]}]}}}
```

Une relation est une variable partagée par deux personnages : elle figure sur les deux fiches, `avec` nommant l'autre personnage, dont le nom et la couleur servent à l'affichage sauf si la relation a son propre nom. Les deux moteurs dessinent la même chose : une colonne d'onglets à gauche, un par personnage (avatar rond ou disque à la couleur du personnage, et le nom, qui prend cette couleur une fois l'onglet ouvert), puis la fiche du personnage ouvert : avatar et nom, et une ligne par jauge, compétence et relation avec une barre de `min` à `max`, la valeur sur le maximum et le nom du plus haut palier (`paliers`) atteint (aucun sous le premier seuil). Les noms des jauges, des compétences, des relations et des paliers sont traduits comme les autres textes (`translate strings`). L'écran n'existe qu'en cours de partie, puisqu'il lit les variables du jeu. Les tests vérifient que chaque variable citée est un `default` numérique du script.

### 5d. Temps : créneaux et jours

`game/temps.json`, produit depuis la bible (`temps`), décrit le modèle de temps : `{"creneaux": ["matin", "midi", "soir"], "jours": true, "semaine": [...], "date": true, "mois": [...], "epoques": ["present", "passe"]}`. L'état tient dans des variables ordinaires du script généré, déclarées par `default` : sauvegardes, retour arrière et conditions n'ont rien de particulier. Ce sont `creneau` (rang), `moment` (nom du créneau), `jour`, `jour_semaine` et `jour_semaine_rang`, et avec un calendrier `jour_mois`, `mois`, `annee`, `evenement_<nom>`, `epoque`, plus des variables internes `temps_*` et `epoque_<époque>_*`. Seuls des labels générés les modifient, tous écrits dans le sous-ensemble (ni division ni modulo : la longueur des mois vient d'une chaîne de `if`, les années bissextiles d'un compteur remis à zéro tous les quatre ans, 2100, 2200 et 2300 exceptées) : `temps_avancer` (créneau suivant, puis `temps_jour_suivant` après le dernier), `temps_jour_suivant` (compteur de jours, semaine, calendrier), `temps_calculer_noms` (noms du créneau et du jour, événements), `temps_calculer_mois`, `temps_sauter_jours` et `temps_sauter_mois` (boucles sur `temps_saut`, par un `jump` vers le même label), et un `temps_epoque_<époque>` par époque (la date courante est rangée dans `epoque_<époque>_*`, celle de l'époque rejointe reprise). Les fiches y accèdent par l'élément `temps` : `call temps_avancer` répété, gardé par `if moment != "…"` pour un créneau nommé ; `$ temps_saut = n` puis un appel pour les sauts de jours et de mois ; des affectations directes (`$ annee = …`, `$ jour = …`, puis `call temps_calculer_noms`) pour une date connue d'avance ; `call temps_epoque_<époque>`. Un lieu à décors par créneau ou époque se compile en une chaîne `if moment == "…"` / `if epoque == "…"` avec la première image en repli. Pendant la partie, les deux moteurs affichent « Jour 2 · mardi · matin » ou « vendredi 16 octobre 2026 · soir » en haut à droite (Ren'Py : écran `temps_permanent` de `game/temps.rpy` ; Godot : `engine/temps.gd` et un libellé du lecteur), caché pendant une carte ; les noms des créneaux, des jours et des mois sont traduits comme les autres textes. Les tests Godot comparent des sauts de 800 jours et de 3 mois du calendrier généré au calendrier de Godot, et vérifient qu'une époque reprend là où on l'a laissée.

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
- `renpy.*` sauf `movie_cutscene` et `pause`, ainsi que `persistent` ; la seule autre fonction permise après `$` est `naviguer("carte")`.

## 8. Différences connues du prototype Godot

- **Sauvegarde :** la position est enregistrée en « label + numéro d'instruction ». Modifier un label avant le point de sauvegarde peut décaler la reprise ; Ren'Py est plus tolérant. Une variable ajoutée plus tard prend son `default` au chargement dans les deux moteurs. Les noms disparus passent par `game/renommages.json` (bible : `renommages`) : Godot recopie la valeur sauvegardée dans la nouvelle variable et résout les labels renommés (position et pile d'appels) au chargement d'un état ; Ren'Py utilise `config.label_overrides` et un rappel après chargement (`game/sauvegardes.rpy`). Les chaînes de renommages sont aplaties par `generer`.
- **Fonctions du lecteur Godot :** menu principal, menu de jeu, historique (250 répliques), retour arrière (128 interactions), avance rapide limitée au texte déjà lu, avance automatique, 5 pages de 6 emplacements avec vignette, sauvegarde rapide (F5 / F9), préférences et galerie.
- **Retour arrière :** il ne survit pas à un chargement (Ren'Py le conserve dans la sauvegarde). Il n'y a pas non plus d'avance après retour (rollforward).
- **Préférences absentes côté Godot :** « continuer l'avance rapide après un choix », accessibilité. La durée d'avance automatique est calculée plus simplement que dans Ren'Py.
- **Texte déjà lu :** une réplique est identifiée par son `id` quand elle en a un (le même dans toutes les langues), sinon par son label, son personnage et son texte. La corriger la fait redevenir « non lue », comme dans Ren'Py.
- **Galerie :** Ren'Py l'ajoute au menu principal (bouton « Gallery » dans `screens.rpy`, traduit comme le reste de l'interface).
- **Cartes de navigation :** l'écran Ren'Py s'appelle `carte` (`navigation` est l'écran du menu principal de Ren'Py). Les deux moteurs partagent la disposition (positions en pourcentage, icônes rondes des pièces en bas à gauche) ; polices et mise à l'échelle des images peuvent différer légèrement. Ren'Py recadre les icônes avec `gui/navigation_rond.png`, Godot avec un polygone texturé.
- **Changement de langue en cours de partie :** Godot réaffiche aussitôt la réplique, le menu ou la carte en cours dans la nouvelle langue. Les répliques précédentes restent dans l'historique dans la langue où elles ont été affichées.
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
| Parcours d'interface scripté | `godot --path . -- --actions=start,advance,menu:characters,character:lena,back,quit` (liste des actions dans `_run_action`, `engine/vn_player.gd`) |
| Tests Godot | `godot --headless --path . --script res://tests/run_tests.gd` |
| Rapport de routes | `godot --headless --path . --script res://tools/routes.gd` |
| Jouer (Ren'Py) | `$RENPY_SDK/renpy.sh .`, ou via le launcher |
| Lint Ren'Py | `$RENPY_SDK/renpy.sh . lint` |
| Tests Ren'Py | `$RENPY_SDK/renpy.sh . test --overwrite-screenshots` (captures dans `tests/screenshots/` ; une seule suite à la fois, et un lancement bloqué se termine par `kill -9`, le binaire ignore un kill simple) |
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
