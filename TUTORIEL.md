# Tutoriel : de la démo à votre jeu

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

Essayez les deux fins : faites confiance à Léna, ou repartez sous la pluie. Regardez la photo dans la boîte aux lettres pour débloquer un choix de plus. Ouvrez la galerie depuis le menu principal.

## 2. Comprendre le circuit

```
contenu/bible.yaml            personnages, lieux, variables
contenu/scenes/**/*.yaml      une fiche par scène
        │  tools/fiches.py verifier   → contrôle toutes les routes
        │  tools/fiches.py generer    → écrit :
        ▼
game/story/*.rpy              script commun, lu par Ren'Py ET par Godot
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
    age: 30                      # obligatoire ; minimum réglable par age_minimum (18 par défaut)
    biographie: Libraire du quartier.
    images: [sam neutre]

variables:
  amitie_sam: {defaut: 0, min: 0, max: 10, description: Amitié de Sam.}
```

Dans les fiches, Sam parle avec `- sam: "…"`, et les effets modifient ses variables : `effets: {amitie_sam: 1}`. Un nombre s'ajoute, un booléen ou un texte remplace la valeur.

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

## 8. Tests

```sh
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
godot --headless --path . --script res://tests/run_tests.gd
$RENPY_SDK/renpy.sh . lint
$RENPY_SDK/renpy.sh . test --overwrite-screenshots
```

`generer` choisit quelques routes qui couvrent toutes les fins et tous les choix. Godot doit y retrouver exactement l'état final calculé en Python ; Ren'Py rejoue les mêmes routes en cliquant les choix. Les tests suivent donc votre histoire sans que vous ayez à les écrire.

## 9. Partir de zéro pour votre jeu

1. **Copier.** Copiez ce dépôt dans un nouveau dossier, qui sera votre projet.
2. **Vider le contenu.** Supprimez les fiches de la démo (`contenu/scenes/ch01/`) et remplacez `contenu/bible.yaml` par la vôtre. Supprimez les médias de la démo dans `game/images/` et `game/videos/`, sauf `lena_scene_01.webm`, utilisé par le test Ren'Py `video_seule` de `game/testcases.rpy` (adaptez ce test si vous le retirez).
3. **Renommer.** Changez le nom du jeu :
   - `config/name` dans `project.godot` ;
   - `config.name`, `build.name` et `config.save_directory` dans `game/options.rpy`.
4. **Construire.** Écrivez vos fiches, puis lancez `verifier`, `provisoires` et `generer`.
5. **Garder le jeu d'essai.** Conservez `tests/fixtures/demo/` : ce jeu d'essai figé sert aux tests du moteur Godot et ne dépend pas de votre histoire.

## 10. Exporter

- **Ren'Py.** Utilisez « Build Distributions » dans le launcher. Les fichiers propres à Godot et aux outils sont déjà exclus dans `game/options.rpy`.
- **Godot.** Dans « Projet → Exporter », ajoutez `*.rpy, *.json` aux filtres de fichiers non-ressources et excluez `*.webm`.

## Et ensuite

La [SPEC](SPEC-sous-ensemble-renpy.md) liste ce que le script commun accepte et les petites différences entre les deux moteurs. Le format complet des fiches est décrit dans [contenu/LISEZMOI.md](contenu/LISEZMOI.md).
