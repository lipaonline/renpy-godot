# Écrire le jeu : bible et fiches de scène

[English version](README.md)

Le script du jeu (`game/story/*.rpy`) n'est plus écrit à la main. Il est **produit à partir de ce dossier** par `tools/fiches.py`, en respectant le sous-ensemble commun Ren'Py / Godot.

```
contenu/
├── bible.yaml          personnages, lieux, variables, règles éditoriales
├── scenes/…/*.yaml     une fiche par scène (sous-dossiers libres : ch01/, ch02/…)
├── production.md       (généré) images et vidéos à produire
└── graphe.md           (généré) graphe des routes
```

## Mise en route (une fois)

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Boucle de travail

1. **Squelette.** Créer la fiche : `id`, `titre`, `lieu`, `personnages`, `objectif_narratif`, et la fin de scène (`choix`, `suite`, `fin` ou `retour`). La relier depuis une autre scène.
2. **Contexte.** `.venv/bin/python tools/fiches.py contexte CH02_SC08 -o contexte.md` produit le paquet à donner au scénariste ou à l'IA : fiches des personnages présents, état possible des variables à l'entrée, résumés de ce qui précède, objectif, règles éditoriales, format attendu.
3. **Écriture.** Compléter `contenu` et `choix`.
4. **Contrôle.** `.venv/bin/python tools/fiches.py verifier`.
5. **Génération.** `.venv/bin/python tools/fiches.py generer` écrit `game/story/*.rpy` et `game/galerie.json`, puis fait relire le résultat par le compilateur Godot.
6. **Suivi.** `production` (images et vidéos à rendre) et `graphe` (routes en Mermaid).
7. **Médias provisoires.** `provisoires` crée une image (dans `game/images/provisoires/`) ou une vidéo pour chaque média qui manque, afin que le jeu reste jouable. Dès qu'une image définitive du même nom arrive dans `game/images/`, la provisoire est retirée ; une vidéo remplacée est reconnue à son contenu. `production` distingue définitif, provisoire et manquant.

## Tests générés

`generer` choisit un petit ensemble de routes complètes qui couvre toutes les fins et tous les choix, puis écrit :

- `tests/routes_attendues.json` : Godot rejoue chaque route et doit obtenir la même fin et le même état final des variables que l'explorateur Python ;
- `game/tests_routes.rpy` : Ren'Py rejoue les mêmes routes en cliquant les choix, puis ouvre la galerie après avoir débloqué toutes ses entrées.

Ces tests suivent l'histoire automatiquement : il n'y a rien à mettre à jour à la main quand les fiches changent.

## Bible (`bible.yaml`)

| Champ | Contenu |
|---|---|
| `debut` | Id de la première scène. |
| `personnages.<id>` | `nom`, **`age` (obligatoire, au moins `age_minimum`, 18 par défaut)**, `couleur` (#rrggbb), `role`, `biographie`, `personnalite`, `desirs`, `contradictions`, `limites`, `secrets`, `images` (sprites). L'id (minuscules) sert dans les fiches : `lena: "…"`. |
| `lieux.<id>` | `description`, `decors` (images de fond). |
| `variables.<nom>` | `defaut` (nombre, booléen ou texte), `min` et `max` (nombres), `description`. |
| `regles_editoriales` | Liste de règles, reprises dans le contexte d'écriture. |
| `synopsis`, `mystere_central` | Facultatifs ; repris dans le contexte d'écriture. |

## Fiche de scène

| Champ | Contenu |
|---|---|
| `id` | Majuscules, chiffres et _ (`CH02_SC08`). Donne le label (`ch02_sc08`) et le fichier (`chapitre_02.rpy`, d'après `CHxx` ou le champ `chapitre`). |
| `titre`, `lieu`, `moment`, `personnages`, `objectif_narratif`, `resume`, `notes` | Métadonnées. `resume` alimente le contexte des scènes suivantes. |
| `conditions` | Conditions d'entrée, vérifiées sur **toutes** les routes : liste d'expressions (`- relation_lena >= 4`) ou format compact (`relation_lena_min: 4`, `indice_photo: true`). |
| `contenu` | Liste d'éléments (ci-dessous). |
| `choix` | Liste d'options, ou `question` (une réplique) + `options`. Option : `libelle`, `destination`, et en option `si`, `effets`, `contenu`. |
| `suite` | Scène suivante sans choix. |
| `fin: true` | Fin de partie (retour au menu principal). |
| `retour: true` | Scène appelée par `appel` (souvenir, interlude réutilisable) : revient après l'appel. |
| `galerie` | `titre`, `vignette`, et `images` (liste) ou `video`. L'entrée se débloque quand la scène a été atteinte. |

## Éléments du contenu

| Élément | Exemple | Produit |
|---|---|---|
| Narration | `- narration: "Il pleut."` | `"Il pleut."` |
| Réplique | `- lena: "Salut."` | `lena "Salut."` |
| Décor | `- decor: rue_nuit` + `transition: fade` | `scene rue_nuit with fade` |
| Personnage | `- montrer: lena sourire` + `position: right`, `transition: dissolve` | `show lena sourire at right with dissolve` |
| Retirer | `- cacher: lena` | `hide lena` |
| Vidéo | `- video: videos/scene.webm` | `$ renpy.movie_cutscene("videos/scene.webm")` |
| Pause | `- pause: 1.5` (vide : attendre un clic) | `pause 1.5` |
| Audio | `- musique: audio/theme.ogg`, `- musique: stop`, `- son: audio/porte.ogg` | `play music …`, `stop music`, `play sound …` |
| Effets | `- effets: {relation_lena: 2, indice_photo: true}` | `$ relation_lena += 2`, `$ indice_photo = True` |
| Condition | `- si: indice_photo` + `alors: […]`, `sinon_si: [{si: …, alors: […]}]`, `sinon: […]` | `if / elif / else` |
| Appel | `- appel: CH01_SOUVENIR` | `call ch01_souvenir` |

**Effets :** un nombre **s'ajoute** à une variable numérique (`-2` retire 2) ; un booléen ou un texte **remplace** la valeur.

**Expressions** (`si`, `conditions`) : variables de la bible, nombres, textes, `True` / `False`, `+ - *`, comparaisons, `and`, `or`, `not`, `in`, `min`, `max`, `abs`. Pas de division ni de comparaisons enchaînées (`0 < x < 3`), dont le résultat diffère entre Python et Godot.

**Textes :** `[variable]` insère une valeur ; balises Ren'Py `{i}…{/i}`, `{b}…{/b}`.

## Pièges YAML

- Mettre **tous les textes entre guillemets** : une phrase contenant « : » casse le fichier sinon.
- `yes`, `no`, `on`, `off` sans guillemets deviennent des booléens.
- L'indentation se fait avec des espaces.

## Ce que vérifie `verifier`

- **Bible :** âge indiqué pour chaque personnage, au moins `age_minimum` (18 par défaut), identifiants valides, variables typées.
- **Fiches :** champs connus, personnages et lieux déclarés, destinations existantes, expressions compatibles avec les deux moteurs, variables citées dans les textes.
- **Routes :** toutes les combinaisons de choix sont jouées. L'outil signale :
  - les conditions d'entrée fausses, avec la route fautive ;
  - les variables hors bornes ;
  - les menus sans choix disponible ;
  - les scènes jamais atteintes et les choix jamais proposés ;
  - l'absence de fin.
- **Script :** aucun `.rpy` écrit à la main ne redéfinit un label ou une variable produits par les fiches. Les fichiers écrits à la main ne sont jamais écrasés sans `--remplacer`.
