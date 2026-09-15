# Écrire le jeu : bible et fiches de scène

[English version](README.md)

Le script du jeu (`game/story/*.rpy`) n'est plus écrit à la main. Il est **produit à partir de ce dossier** par `tools/fiches.py`, en respectant le sous-ensemble commun Ren'Py / Godot.

```
contenu/
├── bible.yaml          personnages, lieux, variables, règles éditoriales
├── scenes/…/*.yaml     une fiche par scène (sous-dossiers libres : ch01/, ch02/…)
├── traductions/*.yaml  un fichier par traduction (en.yaml…), tenu à jour par traduire
├── production.md       (généré) images et vidéos à produire
├── graphe.html         (généré) graphe interactif des routes, à ouvrir dans un navigateur
└── graphe.md           (généré) graphe des routes (Mermaid)
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
5. **Génération.** `.venv/bin/python tools/fiches.py generer` écrit `game/story/*.rpy`, `game/galerie.json` et `game/navigation.json` (cartes et présence), puis fait relire le résultat par le compilateur Godot.
6. **Suivi.** `production` (images et vidéos à rendre) et `graphe` (routes). `graphe --ouvrir` ouvre `graphe.html` dans le navigateur : une carte par scène, un lien par choix, les routes de test et les avertissements de `verifier` ; un clic sur une scène montre son contenu et les valeurs possibles des variables à l'entrée.
7. **Médias provisoires.** `provisoires` crée une image (dans `game/images/provisoires/`) ou une vidéo pour chaque média qui manque, afin que le jeu reste jouable. Dès qu'une image définitive du même nom arrive dans `game/images/`, la provisoire est retirée ; une vidéo remplacée est reconnue à son contenu. `production` distingue définitif, provisoire et manquant.
8. **Traduction.** `traduire en` ajoute les nouvelles répliques et les nouveaux textes à `traductions/en.yaml`. Remplissez `texte`, puis lancez `generer`, qui écrit `game/tl/english/story/`. Voir [Traductions](#traductions).

## Tests générés

`generer` choisit un petit ensemble de routes complètes qui couvre toutes les fins et tous les choix, puis écrit :

- `tests/routes_attendues.json` : Godot rejoue chaque route et doit obtenir la même fin et le même état final des variables que l'explorateur Python ;
- `game/tests_routes.rpy` : Ren'Py rejoue les mêmes routes en cliquant les choix, puis ouvre la galerie après avoir débloqué toutes ses entrées.

Les deux moteurs rejouent les routes dans chaque langue du jeu, en cliquant les choix traduits. Ces tests suivent l'histoire automatiquement : il n'y a rien à mettre à jour à la main quand les fiches changent.

## Bible (`bible.yaml`)

| Champ | Contenu |
|---|---|
| `debut` | Id de la première scène. |
| `personnages.<id>` | `nom`, `age` (facultatif ; s'il est indiqué, au moins `age_minimum`, 18 par défaut), `couleur` (#rrggbb), `role`, `biographie`, `personnalite`, `desirs`, `contradictions`, `limites`, `secrets`, `traits` (liste, pour le contexte d'écriture), `images` (sprites), `avatar` (petit portrait affiché sur les cartes), `presence` (où il se trouve, voir [Navigation](#navigation--cartes-pièces-et-présence)), `jauges`, `competences` et `relations` (voir [Jauges, compétences et relations](#jauges-compétences-et-relations)). L'id (minuscules) sert dans les fiches : `lena: "…"`. |
| `lieux.<id>` | `nom` (affiché sur les cartes ; sinon l'id mis en forme), `description`, `decors` (images de fond : liste, ou dictionnaire créneau → image, voir [Temps](#temps--créneaux-jours-et-décors)), `icone` (image de la pièce, affichée en rond). |
| `cartes.<id>` | Cartes de navigation : `titre`, `affichage` (`carte` ou `pieces`), `image`, `parent`, `lieux` (voir [Navigation](#navigation--cartes-pièces-et-présence)). |
| `variables.<nom>` | `defaut` (nombre, booléen ou texte), `min` et `max` (nombres), `description`. |
| `temps` | `creneaux` (liste), `jours` (booléen), `semaine` (liste), `date` ou `epoques` (calendrier), `evenements`, `debut` ; voir [Temps](#temps--créneaux-jours-et-décors). |
| `renommages` | Noms disparus depuis une version publiée : `variables: {ancien: nouveau}`, `scenes: {ANCIEN: NOUVEAU}`. Voir [Anciennes sauvegardes](#anciennes-sauvegardes). |
| `regles_editoriales` | Liste de règles, reprises dans le contexte d'écriture. |
| `synopsis`, `mystere_central` | Facultatifs ; repris dans le contexte d'écriture. |
| `langues` | `source` : langue des fiches (`fr` par défaut). `traductions` : liste des codes de traduction (`en`, `es`, `de`, `it`, `pt`, `nl`, `pl`, `ru`, `ja`, `ko`, `zh`). |

## Fiche de scène

| Champ | Contenu |
|---|---|
| `id` | Majuscules, chiffres et _ (`CH02_SC08`). Donne le label (`ch02_sc08`) et le fichier (`chapitre_02.rpy`, d'après `CHxx` ou le champ `chapitre`). |
| `titre`, `lieu`, `moment`, `personnages`, `objectif_narratif`, `resume`, `notes` | Métadonnées. `resume` alimente le contexte des scènes suivantes. Avec un bloc `temps`, `moment` doit être un créneau (sinon avertissement). |
| `conditions` | Conditions d'entrée, vérifiées sur **toutes** les routes : liste d'expressions (`- relation_lena >= 4`) ou format compact (`relation_lena_min: 4`, `indice_photo: true`). |
| `contenu` | Liste d'éléments (ci-dessous). |
| `choix` | Liste d'options, ou `question` (une réplique) + `options`. Option : `libelle`, `destination`, et en option `si`, `effets`, `contenu`. |
| `suite` | Scène suivante sans choix. |
| `carte: ville` | Affiche une carte de navigation (bible, `cartes`) : le joueur choisit un lieu, qui joue sa scène. |
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
| Temps | `- temps: 1` (créneaux à passer), `- temps: matin` (jusqu'au prochain matin), `- temps: {jours: 3}`, `{mois: 3, creneau: matin}`, `{date: 2027-12-24}`, `{epoque: passe}` | `call temps_avancer`, `temps_sauter_jours`, `temps_sauter_mois`, `temps_epoque_<nom>`, ou la date posée directement |

**Effets :** un nombre **s'ajoute** à une variable numérique (`-2` retire 2) ; un booléen ou un texte **remplace** la valeur.

**Expressions** (`si`, `conditions`) : variables de la bible, nombres, textes, `True` / `False`, `+ - *`, comparaisons, `and`, `or`, `not`, `in`, `min`, `max`, `abs`. Pas de division ni de comparaisons enchaînées (`0 < x < 3`), dont le résultat diffère entre Python et Godot.

**Textes :** `[variable]` insère une valeur ; balises Ren'Py `{i}…{/i}`, `{b}…{/b}`.

## Navigation : cartes, pièces et présence

Une scène qui se termine par `carte: ville` affiche une carte : le joueur choisit un lieu, qui joue sa scène. Chaque scène visitée se termine à son tour par `carte: …`, ce qui rouvre la navigation depuis le lieu où l'on est, signalé « vous êtes ici » : dans un bâtiment, la rangée d'icônes des pièces réapparaît ainsi dans chaque pièce, par-dessus son décor. Elle reste d'ailleurs affichée, en plus discret et sans clic, pendant toute scène jouée dans une pièce d'un bâtiment (le champ `lieu` de la fiche dit où l'on est) : on voit à tout moment qui est dans quelle pièce (voir `contenu/scenes/ch02/`). Les cartes sont déclarées dans la bible :

```yaml
cartes:
  ville:                          # carte extérieure : une image, des lieux placés dessus
    titre: La ville
    image: carte_ville            # image de fond (provisoire créée par « provisoires »)
    lieux:
      - lieu: immeuble
        x: 50                     # position en pourcentage de l'image
        y: 36
        carte: immeuble           # ouvre la sous-carte des pièces
      - lieu: cafe
        x: 80
        y: 66
        scene: CH02_CAFE          # joue cette scène
        si: heure < 2             # lieu proposé sous condition (facultatif)
  immeuble:                       # intérieur : rangée d'icônes rondes des pièces en bas à gauche
    titre: L'immeuble
    affichage: pieces
    image: immeuble_coupe         # facultatif ; sinon la scène en cours reste visible
    parent: ville                 # bouton « ← La ville » (déduit si une seule carte l'ouvre)
    lieux:
      - lieu: hall
        scene: CH02_HALL
      - lieu: appartement_lena
        scene: CH02_LENA
        si: heure < 2
      - lieu: appartement_lena    # le même lieu peut mener à une autre scène selon l'état
        scene: CH02_SOIR
        si: heure >= 2
```

- **Lieux.** Chaque entrée cite un lieu de la bible (`lieux`), dont `nom` est le texte affiché (au survol, pour une icône de pièce) et `icone` l'image de la pièce, recadrée en rond. Elle joue une scène (`scene`) ou ouvre une sous-carte (`carte`). Depuis une carte, le joueur atteint aussi les lieux de ses sous-cartes et de sa carte parente. Un lieu dont le `si` est faux est **invisible** : une pièce interdite à certaines heures (la cave la nuit) ou tant qu'un droit manque (`si: cle_cave`) n'apparaît pas.
- **Niveaux.** Les sous-cartes s'emboîtent sans limite : France → ville → immeuble → appartement. Un fil d'Ariane (La France › Lyon › L'immeuble) en haut de chaque carte remonte de plusieurs niveaux d'un clic, en plus du bouton « ← carte parente ».
- **Déplacements.** `temps: 1` (créneaux) ou `temps: {jours: 1}` sur une entrée : le coût est payé quand le joueur clique le lieu, avant sa scène ou l'ouverture de sa sous-carte (voir [Temps](#temps--créneaux-jours-et-décors)). Les conditions des lieux d'une sous-carte s'évaluent après ce coût : une ville rejointe le soir peut n'avoir plus rien d'ouvert.
- **Raccourcis.** `raccourci: true` sur une entrée la propose depuis toutes les cartes (bouton en bas à droite, sauf sur sa propre carte) : « chez moi » depuis Paris sans remonter jusqu'à la France. Son `si` et son `temps` s'appliquent partout ; son nom ne doit pas être celui d'un lieu d'une autre carte.
- **Présence.** Un personnage a des règles `presence` : liste de `lieu` avec un `si` facultatif ; à chaque affichage de carte, la première règle vraie donne son lieu (aucune : absent). Le résultat est la variable **`lieu_<personnage>`** (par exemple `lieu_lena`), que les fiches peuvent tester : `si: lieu_lena == "cafe"`. Elle ne se modifie pas par `effets`.
- **Affichage.** Sur chaque lieu, le jeu montre les personnages présents : leur `avatar` (image, par exemple `lena avatar`, recadrée en rond et posée sur l'icône de la pièce), sinon leur nom dans leur couleur (un disque de leur couleur sur une icône). Un lieu qui ouvre une sous-carte montre les personnages de toutes ses pièces.
- **Vérifications.** `verifier` explore les cartes comme des menus : lieux jamais accessibles, carte sans aucun lieu accessible sur une route, noms de lieux en double sur une carte, coûts et raccourcis cohérents. Les tests des deux moteurs cliquent les lieux par leur nom (traduit).

## Jauges, compétences et relations

Un personnage, joueur compris, peut porter des **jauges** (humeur, confiance en soi…), des **compétences** (photographie, bricolage…) et des **relations** avec d'autres personnages. Même format, seule la présentation change dans le jeu :

```yaml
personnages:
  lena:
    jauges:
      stress:
        defaut: 0                 # obligatoire ; un nombre seul (stress: 0) suffit
        min: 0
        max: 5
        nom: Stress               # nom affiché (facultatif : la clé mise en forme)
        description: Monte quand on la pousse sur le passé.
    competences:
      photographie: 4
    relations:                    # clé : l'id de l'autre personnage ; une relation vaut pour les deux
      moi:
        defaut: 3
        min: 0
        max: 10
        description: Confiance de Léna envers le protagoniste.
        paliers: {0: distante, 4: voisine, 6: amie, 8: confidente}
      karim: {defaut: 5, max: 10, nom: Anciens collègues}
  moi:
    competences:
      observation: {defaut: 0, max: 5}
```

- **Variables.** Chaque entrée devient la variable `<personnage>_<nom>` (`lena_stress`, `moi_observation`, `lena_moi`, `lena_karim`), déclarée par `default` dans le script généré, sauvegardée, modifiable par `effets` (`effets: {lena_moi: 1}`) et testable dans `si` et `conditions` (`si: moi_observation >= 1`). Une variable globale de la bible ne peut pas porter ce nom.
- **Relations.** Une relation se déclare une seule fois, sur l'un des deux personnages, sous l'id de l'autre ; elle apparaît sur les fiches des deux. Sans `nom`, le jeu affiche le nom de l'autre personnage dans sa couleur. Une jauge ou une compétence ne peut pas porter l'id d'un personnage.
- **Paliers.** `paliers` associe des seuils à des noms : le plus haut seuil atteint donne le palier, affiché dans le jeu et rappelé dans le contexte d'écriture (`lena_moi : 5 (voisine)`). Les seuils restent dans les bornes `min` / `max`.
- **Écran « Personnages ».** `generer` écrit `game/personnages.json` : avatar, nom, jauges, compétences et relations (variable, bornes, paliers). Ren'Py l'affiche dans le menu de jeu (`game/personnages.rpy`, bouton « Personnages »), Godot aussi (`engine/ui/characters_page.gd`) : un onglet vertical par personnage (avatar rond et nom), et la fiche ouverte avec une barre par entrée, la valeur sur le maximum et le palier atteint. Seuls les personnages qui ont au moins une entrée y figurent.
- **Traductions.** Les noms des jauges, des compétences, des relations nommées et des paliers passent par `traduire`, comme les noms de lieux.
- **Vérifications.** `verifier` contrôle les noms, les bornes (`min` ≤ `max`, paliers dans les bornes, noms de paliers distincts), les relations (autre personnage existant, déclarée une seule fois) et signale sur les routes une jauge qui sort de ses bornes.

## Temps : créneaux, jours et décors

Le temps se déclare dans la bible ; sans ce bloc, le jeu n'a pas de notion de temps.

```yaml
temps:
  creneaux: [matin, midi, soir]     # au moins deux, dans l'ordre de la journée
  jours: true                       # compte les jours (jour 1, 2…) ; implicite avec « semaine » ou une date
  semaine: [lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche]   # facultatif ; implicite avec une date
  date: 2026-10-16                  # vrai calendrier : jour_mois, mois, annee, jour_semaine suivent les dates
  evenements:                       # booléens evenement_<nom>, vrais ce jour-là chaque année
    noel: {mois: 12, jour: 25}
    anniversaire_lena: {mois: 10, jour: 17}
  debut: {creneau: soir}            # facultatif : premier créneau (et jour, jour_semaine sans date ; epoque)

lieux:
  appartement_lena:
    decors: {matin: appartement_jour, midi: appartement_jour, soir: appartement_soir}
```

- **Variables produites** : `creneau` (rang, 0 pour le premier), `moment` (nom du créneau), `jour` (compteur depuis le début), `jour_semaine`, et avec une date `jour_mois`, `mois` (1 à 12), `annee`, `evenement_<nom>`. Les fiches les lisent (`si: moment == "soir"`, `si: jour_semaine == "samedi"`, `si: evenement_noel`, `si: mois == 12 and jour_mois >= 20`) mais ne les modifient pas par `effets`.
- **Avancer** : `- temps: 1` passe un créneau (2 pour deux), `- temps: matin` avance jusqu'au prochain matin ; après le dernier créneau, le jour suivant commence au premier. Les ellipses gardent le créneau sauf `creneau` indiqué : `- temps: {jours: 3}`, `- temps: {mois: 3, creneau: matin}` (même jour du mois, ou le dernier jour du mois d'arrivée : 31 janvier + 1 mois = 28 février), `- temps: {date: 2027-12-24}` (date connue d'avance, passée ou future). Le script généré contient les labels `temps_*` appelés par ces éléments ; le calendrier tient compte des années bissextiles.
- **Voyages dans le temps** : `epoques` remplace `date` par une date par époque ; `debut.epoque` (sinon la première) donne l'époque de départ. `- temps: {epoque: passe}` range la date courante dans l'époque quittée et reprend celle de l'époque rejointe, là où on l'avait laissée. Les variables sont communes à toutes les époques : un indice trouvé dans le passé se lit dans le présent, et `epoque` (`si: epoque == "passe"`) sert aux règles de présence, aux cartes et aux décors (`decors: {passe: chantier_1987, present: chantier_jour}`, clés créneau ou époque).

  ```yaml
  temps:
    creneaux: [matin, midi, soir]
    epoques: {present: 2026-10-16, passe: 2016-10-16}
    debut: {creneau: soir, epoque: present}
  ```
- **Décors par créneau** : un lieu dont `decors` est un dictionnaire créneau (ou époque) → image se pose avec `- decor: <id du lieu>` ; le jeu choisit l'image du créneau courant, ou la première déclarée. Les images restent des entrées de `production`.
- **Affichage** : pendant la partie, « Jour 2 · mardi · matin » ou, avec un calendrier, « vendredi 16 octobre 2026 · soir » en haut à droite, dans les deux moteurs (Ren'Py : écran `temps_permanent`, `game/temps.rpy` ; Godot : `engine/temps.gd`), caché sur les cartes. Les noms des créneaux, des jours et des mois passent par `traduire`.
- **Présence et lieux** : les règles `presence` et les `si` des cartes testent ces variables comme les autres (`si: moment != "soir"` pour une cave fermée le soir).
- **Vérifications** : créneaux distincts, dates valides, semaine de 7 noms avec un calendrier, événements possibles, au moins deux époques, `debut` valide, noms `creneau`, `moment`, `jour`, `jour_semaine`, `jour_mois`, `mois`, `annee`, `epoque` et préfixes `temps_`, `evenement_`, `epoque_` réservés, `moment` des fiches parmi les créneaux, décors par créneau déclarés, sauts cohérents avec la bible. L'explorateur de routes suit le temps, calendrier et époques compris, comme n'importe quelle variable.

## Anciennes sauvegardes

Une sauvegarde contient la position (label et rang dans le label, pile des `appel`) et les variables. Ajouter des personnages, des jauges, des scènes ou des variables ne casse rien : une variable nouvelle prend son `defaut` au chargement, dans les deux moteurs. Ce qui casse, c'est un nom qui disparaît : label supprimé ou renommé (la sauvegarde ne se charge plus), variable renommée (sa valeur repart au `defaut`). Une fois le jeu publié, déclarez ces renommages dans la bible plutôt que de les subir :

```yaml
renommages:
  variables:
    relation_lena: lena_moi       # la valeur sauvegardée sous relation_lena passe dans lena_moi
  scenes:
    CH01_SC03: CH01_SC03A         # une sauvegarde faite dans ch01_sc03 reprend dans ch01_sc03a
```

`generer` écrit `game/renommages.json`, lu par `game/sauvegardes.rpy` côté Ren'Py (`config.label_overrides` pour les scènes, un rappel après chargement pour les variables) et par le lecteur Godot (`engine/renommages.gd`, appliqué par l'interpréteur au chargement). Les renommages en chaîne (`a: b` puis `b: c`) se font dans l'ordre déclaré. `verifier` refuse un renommage dont l'ancien nom existe encore ou dont le nouveau nom n'existe pas. Ne modifiez pas l'intérieur d'une scène publiée avant un point de sauvegarde possible : ajoutez des scènes.

## Traductions

Chaque code de `langues.traductions` a son fichier `traductions/<code>.yaml`, créé et tenu à jour par `.venv/bin/python tools/fiches.py traduire <code>` :

```yaml
repliques:                      # répliques, par identifiant
  ch01_sc02_14e17bdd:
    qui: lena                   # qui parle (pour information)
    source: "Je ne pensais pas que tu viendrais."   # texte d'origine : ne pas modifier
    texte: "I didn't think you'd come."             # traduction ; vide = pas encore traduit
textes:                         # noms, choix et titres de galerie, par texte d'origine
  - source: "Lui faire confiance"
    texte: "Trust her"
```

- **Identifiants.** Chaque réplique reçoit un identifiant calculé d'après sa scène, son personnage et son texte. `generer` l'écrit dans le script (`lena "…" id ch01_sc02_14e17bdd`). Ajouter des répliques ailleurs ne le change pas.
- **Modifications.** Quand une fiche change, relancez `traduire` :
  - les nouvelles répliques et les nouveaux textes sont ajoutés avec un `texte` vide ;
  - si un texte d'origine a changé, sa traduction est gardée et marquée `a_revoir`, avec l'ancien original : vérifiez la traduction, puis supprimez la ligne `a_revoir` ;
  - les traductions qui ne correspondent plus à rien passent dans `obsoletes`.
- **Traductions manquantes :** ce n'est pas une erreur, le jeu affiche le texte d'origine. `verifier` les compte.
- **Traducteur ou IA.** `traduire en --paquet traduction.md` écrit un paquet : consignes, personnages, glossaire et entrées à traduire. Enregistrez la réponse dans un fichier et reprenez-la avec `traduire en --importer reponse.yaml`.
- **Fichiers produits.** `generer` écrit les répliques traduites dans `game/tl/<langue>/story/chapitre_XX.rpy` (blocs `translate` de Ren'Py), et les textes dans `textes.rpy` (`translate strings`). Ren'Py et Godot les lisent tous les deux.

## Pièges YAML

- Mettre **tous les textes entre guillemets** : une phrase contenant « : » casse le fichier sinon.
- `yes`, `no`, `on`, `off` sans guillemets deviennent des booléens.
- L'indentation se fait avec des espaces.

## Ce que vérifie `verifier`

- **Bible :** âge des personnages, quand il est indiqué, au moins `age_minimum` (18 par défaut), identifiants valides, variables typées, jauges, compétences et relations (nombres, bornes, paliers, relation déclarée une fois), temps (créneaux, début, noms réservés, décors par créneau), cartes cohérentes (lieux déclarés, positions, une destination par lieu, règles de présence).
- **Fiches :** champs connus, personnages, lieux et cartes déclarés, destinations existantes, expressions compatibles avec les deux moteurs, variables citées dans les textes.
- **Routes :** toutes les combinaisons de choix et de lieux sont jouées. L'outil signale :
  - les conditions d'entrée fausses, avec la route fautive ;
  - les variables hors bornes ;
  - les menus sans choix disponible et les cartes sans lieu accessible ;
  - les scènes jamais atteintes, les choix jamais proposés et les lieux jamais accessibles ;
  - l'absence de fin.
- **Traductions :** répliques et textes à traduire ou à revoir, `[variables]` et `{balises}` conservées, choix d'un même menu (et lieux d'une même carte) toujours distincts une fois traduits, entrées qui ne correspondent plus au script.
- **Script :** aucun `.rpy` écrit à la main ne redéfinit un label ou une variable produits par les fiches. Les fichiers écrits à la main ne sont jamais écrasés sans `--remplacer`.
