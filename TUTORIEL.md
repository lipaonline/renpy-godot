# Tutoriel : de la démo à votre jeu

[English version](TUTORIAL.md)

Ce tutoriel part du jeu de démo et vous amène jusqu'à votre propre jeu, joué par Ren'Py et par Godot. Comptez une heure.

## 1. Installer et jouer la démo

1. Installez Godot 4.7, le SDK Ren'Py 8.5, Python 3.10 ou plus, `ffmpeg` et `ffmpeg2theora`.
2. Dans le dossier du projet :

   ```sh
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. Jouez la démo dans les deux moteurs :

   ```sh
   godot --path .
   $RENPY_SDK/renpy.sh .          # $RENPY_SDK : dossier où vous avez décompressé le SDK
   ```

Essayez les deux fins : faites confiance à Léna, ou repartez sous la pluie. Regardez la photo dans la boîte aux lettres pour débloquer un choix de plus. Ouvrez la galerie depuis le menu principal, et passez en anglais dans Préférences → Langue.

## 2. Comprendre le circuit

```
contenu/bible.yaml            personnages, lieux, variables, langues
contenu/scenes/**/*.yaml      une fiche par scène
contenu/traductions/en.yaml   traduction anglaise
        │  tools/fiches.py verifier   → contrôle toutes les routes
        │  tools/fiches.py generer    → écrit :
        ▼
game/story/*.rpy              script commun, lu par Ren'Py ET par Godot
game/tl/english/story/*.rpy   traduction anglaise, lue elle aussi par les deux moteurs
game/galerie.json             galerie
tests/routes_attendues.json   routes à rejouer par Godot
game/tests_routes.rpy         routes à rejouer par Ren'Py
```

On n'écrit jamais `game/story/` à la main : on modifie les fiches, puis on régénère.

## 3. Modifier une réplique

Ouvrez [contenu/scenes/ch01/CH01_SC01.yaml](contenu/scenes/ch01/CH01_SC01.yaml) et changez la première narration :

```yaml
  - narration: "La pluie ne s'arrête pas. L'immeuble est plus petit que dans mes souvenirs."
```

Puis :

```sh
.venv/bin/python tools/fiches.py verifier
.venv/bin/python tools/fiches.py generer
```

Relancez le jeu dans les deux moteurs : la réplique a changé partout.

## 4. Ajouter une scène

Créez `contenu/scenes/ch01/CH01_SC06.yaml` :

```yaml
id: CH01_SC06
titre: Le lendemain
lieu: rue
moment: matin
personnages: [moi, lena]
objectif_narratif:
  - montrer_les_consequences_de_la_soiree
resume: Le lendemain matin, Léna attend le protagoniste devant l'immeuble.

contenu:
  - decor: rue_matin
    transition: fade
  - montrer: lena sourire
    position: center
  - si: relation_lena >= 5
    alors:
      - lena: "Je t'ai apporté un café. Et la suite de l'histoire."
    sinon:
      - lena: "Tu es encore là ? Je pensais que tu serais parti."

fin: true
```

Reliez-la : dans `CH01_SC04.yaml`, remplacez `fin: true` par `suite: CH01_SC06`.

Lancez `verifier`. L'outil joue toutes les combinaisons de choix et vous dit si une condition est fausse sur une route, si une scène n'est jamais atteinte ou si une variable n'existe pas. Le décor `rue_matin` n'existe pas encore : c'est l'étape suivante.

Pour voir toute l'histoire, lancez `.venv/bin/python tools/fiches.py graphe --ouvrir`. `contenu/graphe.html` s'ouvre dans le navigateur, avec une carte par scène et un lien par choix. Un clic sur une scène montre son contenu, les valeurs possibles des variables à l'entrée et ses avertissements ; le menu du haut surligne chaque route de test.

## 5. Images et vidéos

- **Nommage.** Une image se nomme comme dans Ren'Py : `game/images/lena sourire.png` définit l'image `lena sourire`. Le premier mot est le tag du personnage.
- **Médias provisoires.** `.venv/bin/python tools/fiches.py provisoires` crée une image provisoire pour chaque image qui manque, dans `game/images/provisoires/`. Il crée aussi une vidéo de remplacement pour chaque vidéo manquante. Le jeu reste jouable pendant que les rendus avancent.
- **Médias définitifs.** Déposez l'image définitive sous le même nom dans `game/images/`, puis relancez `provisoires` : la version provisoire est retirée.
- **Vidéos.** Le script cite le `.webm`, que lit Ren'Py. Godot lit le `.ogv` de même nom, que produit `python3 tools/convertir_videos.py`.
- **Suivi.** `production` écrit `contenu/production.md` : chaque image et chaque vidéo, où elle sert, et son état (définitive, provisoire ou manquante).

## 6. Personnages et variables

Dans [contenu/bible.yaml](contenu/bible.yaml) :

```yaml
personnages:
  sam:
    nom: Sam
    couleur: "#8fe3b0"
    age: 30                      # facultatif ; s'il est indiqué, minimum réglable par age_minimum (18 par défaut)
    biographie: Libraire du quartier.
    images: [sam neutre]

    competences:
      cuisine: {defaut: 2, max: 5}            # variable sam_cuisine
    relations:
      moi: {defaut: 0, max: 10, paliers: {0: inconnu, 4: ami}}   # variable sam_moi, sur les deux fiches

variables:
  argent: {defaut: 20, min: 0, description: Ce qu'il reste en poche.}
```

Dans les fiches, Sam parle avec `- sam: "…"`, et les effets modifient les variables : `effets: {sam_moi: 1, argent: -5}`. Un nombre s'ajoute, un booléen ou un texte remplace la valeur. Jauges, compétences et relations des personnages s'affichent dans l'écran « Personnages » du menu de jeu, avec le palier atteint (`ami` à partir de 4). Détails : [contenu/LISEZMOI.md](contenu/LISEZMOI.md#jauges-compétences-et-relations).

### Le temps : créneaux, calendrier, époques

Dans la bible, un bloc `temps` donne au jeu des créneaux (matin, midi, soir), un vrai calendrier à partir d'une date, des événements annuels et, pour les voyages dans le temps, des époques qui gardent chacune leur date :

```yaml
temps:
  creneaux: [matin, midi, soir]
  epoques: {present: 2026-10-16, passe: 2016-10-16}
  evenements: {anniversaire_lena: {mois: 10, jour: 17}}
  debut: {creneau: soir, epoque: present}
```

Dans les fiches, `- temps: 1` passe au créneau suivant, `- temps: {mois: 3, creneau: matin}` fait une ellipse, `- temps: {epoque: passe}` part dans le passé (et `present` en revient, là où on l'avait laissé). Les conditions lisent `moment`, `jour_semaine`, `mois`, `jour_mois`, `annee`, `epoque` et `evenement_anniversaire_lena` ; les variables de l'histoire sont communes aux époques, ce qu'on change dans le passé se voit dans le présent. Le jeu affiche « vendredi 16 octobre 2026 · soir » en haut à droite. Détails : [contenu/LISEZMOI.md](contenu/LISEZMOI.md#temps--créneaux-jours-et-décors).

### Cartes, pièces et présence des personnages

Le chapitre 2 de la démo est une journée en liberté : on se réveille dans l'appartement du père (chambre, cuisine, salon, salle de bain, en icônes rondes au bas de l'écran, visibles dans chaque pièce), l'immeuble (hall, cave fermée le soir, appartement de Léna), puis la carte de la ville ; deux personnages se déplacent selon l'heure. Tout se déclare dans la bible :

```yaml
lieux:
  cave:
    nom: La cave
    icone: icone_cave            # image de la pièce, affichée en icône ronde

cartes:
  maison:
    titre: La maison
    affichage: pieces            # icônes des pièces ; « carte » = image avec des lieux placés dessus (x, y en %)
    lieux:
      - lieu: salon
        scene: CH03_SALON
      - lieu: cave
        scene: CH03_CAVE
        si: heure < 2            # invisible la nuit : le lieu n'apparaît pas tant que la condition est fausse

personnages:
  sam:
    avatar: sam avatar           # petit portrait affiché sur les lieux où il se trouve
    presence:
      - lieu: salon
        si: heure == 0
      - lieu: cave               # sinon
```

Une scène affiche la carte en se terminant par `carte: maison` au lieu de `choix` ou `suite`. Chaque scène de pièce se termine ainsi : les icônes réapparaissent dans la pièce où l'on est (mise en évidence) et le joueur choisit la suivante ; pendant la scène elle-même, elles restent visibles en plus discret. À chaque affichage, le jeu recalcule où est chaque personnage (et `verifier` fait de même sur chaque route) ; le résultat est la variable `lieu_sam`, que vos fiches peuvent tester (`si: lieu_sam == "cave"`). `provisoires` crée les cartes, icônes et avatars manquants. Le détail est dans [contenu/LISEZMOI.md](contenu/LISEZMOI.md#navigation--cartes-pièces-et-présence).

## 7. Écrire avec un scénariste ou une IA

```sh
.venv/bin/python tools/fiches.py contexte CH01_SC06 -o contexte.md
```

`contexte.md` réunit tout ce qu'il faut pour écrire la scène :
- le synopsis et le mystère central ;
- les fiches des personnages présents ;
- les valeurs possibles des variables à l'entrée de la scène ;
- ce qui précède et les suites prévues ;
- les règles éditoriales et le format attendu.

Donnez-le à votre scénariste ou à une IA : la réponse attendue est la fiche YAML complète. Collez-la, puis relancez `verifier`.

## 8. Traduire le jeu

Les fiches sont écrites dans une langue, déclarée dans la bible, et chaque traduction a son fichier :

```yaml
langues:
  source: fr            # langue des fiches
  traductions: [en]     # traductions : en, es, de, it, pt…
```

1. `.venv/bin/python tools/fiches.py traduire en` crée ou met à jour `contenu/traductions/en.yaml`. On y trouve chaque réplique du script, chaque nom de personnage, choix et titre de galerie, avec son texte d'origine (`source`) et un `texte` vide à remplir.
2. Remplissez `texte`, puis lancez `generer` : les traductions sont écrites dans `game/tl/english/story/`, où Ren'Py et Godot les lisent.
3. En jeu, Préférences → Langue change de langue. Au premier lancement, le jeu prend la langue du système si elle est disponible.

Après une modification des fiches, relancez `traduire en` :
- les nouvelles répliques sont ajoutées ;
- une traduction dont le texte d'origine a changé est gardée et marquée `a_revoir`, avec l'ancien texte ;
- les traductions qui ne correspondent plus à rien passent dans `obsoletes`.

`verifier` compte ce qui reste à traduire ou à revoir, et contrôle que chaque traduction garde les `[variables]` et les `{balises}` de l'original.

Avec un traducteur ou une IA, `traduire en --paquet traduction.md` écrit un paquet : consignes, personnages, glossaire et entrées à traduire. Enregistrez la réponse dans un fichier, puis lancez `traduire en --importer reponse.yaml`.

Chaque réplique est reliée à ses traductions par un identifiant écrit dans le script (`lena "…" id ch01_sc02_14e17bdd`). Il est calculé d'après la scène, le personnage et le texte : ajouter des répliques ailleurs ne le change pas.

## 9. Tests

```sh
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
godot --headless --path . --script res://tests/run_tests.gd
$RENPY_SDK/renpy.sh . lint
$RENPY_SDK/renpy.sh . test --overwrite-screenshots
```

`generer` choisit quelques routes qui couvrent toutes les fins, tous les choix et tous les lieux des cartes. Godot doit y retrouver exactement l'état final calculé en Python ; Ren'Py rejoue les mêmes routes en cliquant les choix. Les deux le font dans chaque langue, en cliquant les choix traduits. Les tests suivent donc votre histoire sans que vous ayez à les écrire.

## 10. Partir de zéro pour votre jeu

1. **Copier.** Copiez ce dépôt dans un nouveau dossier, qui sera votre projet.
2. **Vider le contenu.** Supprimez les fiches de la démo (`contenu/scenes/`) et remplacez `contenu/bible.yaml` par la vôtre. Supprimez les médias de la démo dans `game/images/` et `game/videos/`, sauf `lena_scene_01.webm`, utilisé par le test Ren'Py `video_seule` de `game/testcases.rpy` (adaptez ce test si vous le retirez).
3. **Renommer.** Changez le nom du jeu :
   - `config/name` dans `project.godot` ;
   - `config.name`, `build.name` et `config.save_directory` dans `game/options.rpy`.
4. **Construire.** Écrivez vos fiches, puis lancez `verifier`, `provisoires` et `generer`.
5. **Langues.** Déclarez `langues` dans votre bible (supprimez `contenu/traductions/en.yaml` si vous n'avez pas de traduction anglaise). L'interface Ren'Py existe en français (`game/tl/french/`) et en anglais (textes d'origine de Ren'Py). Pour une autre langue :
   - extrayez ses textes d'interface avec `$RENPY_SDK/renpy.sh . translate <langue> --strings-only`, puis traduisez-les ;
   - supprimez le sous-dossier `story/` que cette commande ajoute, puis relancez `generer` ;
   - les textes de l'interface Godot sont dans `engine/ui/traductions_interface.gd`.
6. **Garder le jeu d'essai.** Conservez `tests/fixtures/demo/` : ce jeu d'essai figé sert aux tests du moteur Godot et ne dépend pas de votre histoire.

## 11. Exporter

- **Ren'Py.** Utilisez « Build Distributions » dans le launcher. Les fichiers propres à Godot et aux outils sont déjà exclus dans `game/options.rpy`.
- **Godot.** Dans « Projet → Exporter », ajoutez `*.rpy, *.json` aux filtres de fichiers non-ressources et excluez `*.webm`.

## Et ensuite

La [SPEC](SPEC-sous-ensemble-renpy.md) liste ce que le script commun accepte et les petites différences entre les deux moteurs. Le format complet des fiches est décrit dans [contenu/LISEZMOI.md](contenu/LISEZMOI.md).
