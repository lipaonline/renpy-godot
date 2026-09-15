# Tutorial: from the demo to your own game

[Version française](TUTORIEL.md)

This tutorial starts from the demo game and takes you to your own game, played by Ren'Py and by Godot. Allow about an hour.

The demo game is written in French and translated into English. The tool commands and the scene-sheet keys are in French; their meaning is given as we go (`verifier` = check, `generer` = generate, `provisoires` = placeholders, `traduire` = translate…).

## 1. Install and play the demo

1. Install Godot 4.7, the Ren'Py 8.5 SDK, Python 3.10 or later, `ffmpeg` and `ffmpeg2theora`.
2. In the project folder:

   ```sh
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. Play the demo in both engines:

   ```sh
   godot --path .
   $RENPY_SDK/renpy.sh .          # $RENPY_SDK: the folder where you unpacked the SDK
   ```

Try both endings: trust Léna, or leave in the rain. Look at the photo in the letterbox to unlock one more choice. Open the gallery from the main menu, and switch to English in Preferences → Language.

## 2. Understand the pipeline

```
contenu/bible.yaml            characters, locations, variables, languages
contenu/scenes/**/*.yaml      one sheet per scene
contenu/traductions/en.yaml   English translation
        │  tools/fiches.py verifier   → checks every route
        │  tools/fiches.py generer    → writes:
        ▼
game/story/*.rpy              shared script, read by Ren'Py AND by Godot
game/tl/english/story/*.rpy   English translation, also read by both engines
game/galerie.json             gallery
tests/routes_attendues.json   routes for Godot to replay
game/tests_routes.rpy         routes for Ren'Py to replay
```

You never write `game/story/` by hand: edit the sheets, then regenerate.

## 3. Change a line

Open [contenu/scenes/ch01/CH01_SC01.yaml](contenu/scenes/ch01/CH01_SC01.yaml) and change the first narration:

```yaml
  - narration: "The rain won't stop. The building looks smaller than I remember."
```

Then:

```sh
.venv/bin/python tools/fiches.py verifier
.venv/bin/python tools/fiches.py generer
```

Relaunch the game in both engines: the line has changed everywhere.

## 4. Add a scene

Create `contenu/scenes/ch01/CH01_SC06.yaml`:

```yaml
id: CH01_SC06
titre: The next morning
lieu: rue
moment: matin
personnages: [moi, lena]
objectif_narratif:
  - show_the_consequences_of_the_evening
resume: The next morning, Léna is waiting outside the building.

contenu:
  - decor: rue_matin
    transition: fade
  - montrer: lena sourire
    position: center
  - si: relation_lena >= 5
    alors:
      - lena: "I brought you a coffee. And the rest of the story."
    sinon:
      - lena: "You're still here? I thought you'd be gone."

fin: true
```

`titre` is the title, `lieu` the location, `personnages` the characters, `montrer` shows a character, `si` / `alors` / `sinon` mean if / then / else, and `fin: true` ends the game.

Link it: in `CH01_SC04.yaml`, replace `fin: true` with `suite: CH01_SC06`.

Run `verifier`. The tool plays every combination of choices and tells you if a condition is false on a route, if a scene is never reached or if a variable does not exist. The `rue_matin` background does not exist yet: that is the next step.

To see the whole story, run `.venv/bin/python tools/fiches.py graphe --ouvrir`. `contenu/graphe.html` opens in the browser, with one card per scene and one link per choice. Click a scene to read its content, the possible variable values on entry and its warnings; the menu at the top highlights each test route.

## 5. Images and videos

- **Naming.** Images are named as in Ren'Py: `game/images/lena sourire.png` defines the image `lena sourire`. The first word is the character's tag.
- **Placeholder media.** `.venv/bin/python tools/fiches.py provisoires` creates a placeholder image in `game/images/provisoires/` for every missing image. It also creates a stand-in video for every missing video. The game stays playable while the renders progress.
- **Final media.** Drop the final image under the same name in `game/images/`, then run `provisoires` again: the placeholder is removed.
- **Videos.** The script references the `.webm`, which Ren'Py plays. Godot plays the `.ogv` with the same name, produced by `python3 tools/convertir_videos.py`.
- **Tracking.** `production` writes `contenu/production.md`: every image and video, where it is used, and its state (final, placeholder or missing).

## 6. Characters and variables

In [contenu/bible.yaml](contenu/bible.yaml):

```yaml
personnages:
  sam:
    nom: Sam
    couleur: "#8fe3b0"
    age: 30                      # optional; when given, the minimum is set by age_minimum (18 by default)
    biographie: The neighbourhood bookseller.
    images: [sam neutre]

    competences:
      cuisine: {defaut: 2, max: 5}            # variable sam_cuisine
    relations:
      moi: {defaut: 0, max: 10, paliers: {0: inconnu, 4: ami}}   # variable sam_moi, on both sheets

variables:
  argent: {defaut: 20, min: 0, description: Money left in your pocket.}
```

In the sheets, Sam speaks with `- sam: "…"`, and effects change the variables: `effets: {sam_moi: 1, argent: -5}`. A number is added, a boolean or a text replaces the value. Gauges, skills and relationships of the characters appear on the "Characters" screen of the game menu, with the level reached (`ami` from 4). Details: [contenu/README.md](contenu/README.md#gauges-skills-and-relationships).

### Time: slots, calendar, eras

In the bible, a `temps` block gives the game slots (morning, noon, evening), a real calendar from a start date, yearly events and, for time travel, eras that each keep their own date:

```yaml
temps:
  creneaux: [matin, midi, soir]
  epoques: {present: 2026-10-16, passe: 2016-10-16}
  evenements: {anniversaire_lena: {mois: 10, jour: 17}}
  debut: {creneau: soir, epoque: present}
```

In the sheets, `- temps: 1` moves to the next slot, `- temps: {mois: 3, creneau: matin}` makes an ellipsis, `- temps: {epoque: passe}` travels to the past (and `present` comes back, where it was left). Conditions read `moment`, `jour_semaine`, `mois`, `jour_mois`, `annee`, `epoque` and `evenement_anniversaire_lena`; story variables are shared across eras, so what changes in the past shows in the present. The game shows "vendredi 16 octobre 2026 · soir" at the top right. Details: [contenu/README.md](contenu/README.md#time-slots-days-and-backgrounds).

### Maps, rooms and character presence

Chapter 2 of the demo is a free-roaming day: you wake up in your father's flat (bedroom, kitchen, living room, bathroom, as round icons at the bottom of the screen, visible in every room), then the building (lobby, a cellar closed in the evening, Léna's flat), then the town map; two characters move around with the time of day. Everything is declared in the bible:

```yaml
lieux:
  cave:
    nom: La cave
    icone: icone_cave            # image of the room, shown as a round icon

cartes:
  maison:
    titre: La maison
    affichage: pieces            # room icons; "carte" = an image with locations placed on it (x, y in %)
    lieux:
      - lieu: salon
        scene: CH03_SALON
      - lieu: cave
        scene: CH03_CAVE
        si: heure < 2            # invisible at night: the room does not appear while the condition is false

personnages:
  sam:
    avatar: sam avatar           # small portrait shown on the locations where he is
    presence:
      - lieu: salon
        si: heure == 0
      - lieu: cave               # otherwise
```

A scene shows the map by ending with `carte: maison` instead of `choix` or `suite`. Every room scene ends that way: the icons reappear in the room the player is in (highlighted) and the player picks the next room; during the scene itself they stay visible, dimmed. Each time a map is shown, the game recomputes where every character is (and `verifier` does the same on every route); the result is the variable `lieu_sam`, which your sheets can test (`si: lieu_sam == "cave"`). `provisoires` creates the missing maps, icons and avatars. Details in [contenu/README.md](contenu/README.md#navigation-maps-rooms-and-character-presence).

## 7. Write with a writer or an AI

```sh
.venv/bin/python tools/fiches.py contexte CH01_SC06 -o contexte.md
```

`contexte.md` gathers everything needed to write the scene:
- the synopsis and the central mystery;
- the sheets of the characters present;
- the possible variable values on entry to the scene;
- what comes before and the planned follow-ups;
- the editorial rules and the expected format.

Give it to your writer or to an AI: the expected answer is the complete YAML sheet. Paste it, then run `verifier` again.

## 8. Translate the game

The sheets are written in one language, declared in the bible, and each translation has its own file:

```yaml
langues:
  source: fr            # language of the sheets
  traductions: [en]     # translations: en, es, de, it, pt…
```

1. `.venv/bin/python tools/fiches.py traduire en` creates or updates `contenu/traductions/en.yaml`. It lists every line of the script, every character name, choice and gallery title, with its original text (`source`) and an empty `texte` to fill in.
2. Fill in `texte`, then run `generer`: the translations are written to `game/tl/english/story/`, where Ren'Py and Godot both read them.
3. In the game, Preferences → Language switches language. On first launch, the game picks the system language if it is available.

After changing a sheet, run `traduire en` again:
- new lines are added;
- a translation whose original text changed is kept and marked `a_revoir` (to review), with the old text;
- translations that no longer match anything move to `obsoletes`.

`verifier` counts what is left to translate or to review, and checks that each translation keeps the `[variables]` and `{tags}` of the original.

With a translator or an AI, `traduire en --paquet traduction.md` writes a pack: instructions, characters, glossary and entries to translate. Save the answer to a file, then run `traduire en --importer reponse.yaml`.

Each line is linked to its translations by an identifier written into the script (`lena "…" id ch01_sc02_14e17bdd`). It is computed from the scene, the speaker and the text, so adding lines elsewhere does not change it.

## 9. Tests

```sh
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
godot --headless --path . --script res://tests/run_tests.gd
$RENPY_SDK/renpy.sh . lint
$RENPY_SDK/renpy.sh . test --overwrite-screenshots
```

`generer` picks a few routes that cover every ending, every choice and every map location. Godot must reach exactly the final state computed in Python; Ren'Py replays the same routes by clicking the choices. Both do so in every language, clicking the translated choices. The tests therefore follow your story without you having to write them.

## 10. Start your own game from scratch

1. **Copy.** Copy this repository into a new folder, which becomes your project.
2. **Clear the content.** Delete the demo sheets (`contenu/scenes/`) and replace `contenu/bible.yaml` with your own. Delete the demo media in `game/images/` and `game/videos/`, except `lena_scene_01.webm`, used by the Ren'Py test `video_seule` in `game/testcases.rpy` (adapt that test if you remove it).
3. **Rename.** Change the game's name:
   - `config/name` in `project.godot`;
   - `config.name`, `build.name` and `config.save_directory` in `game/options.rpy`.
4. **Build.** Write your sheets, then run `verifier`, `provisoires` and `generer`.
5. **Languages.** Declare `langues` in your bible (delete `contenu/traductions/en.yaml` if you have no English translation). The Ren'Py interface exists in French (`game/tl/french/`) and in English (Ren'Py's own texts). For another language:
   - extract its interface texts with `$RENPY_SDK/renpy.sh . translate <language> --strings-only` and translate them;
   - delete the `story/` subfolder this command adds, then run `generer` again;
   - the Godot interface texts are in `engine/ui/traductions_interface.gd`.
6. **Keep the fixture.** Keep `tests/fixtures/demo/`: this frozen test game is used by the Godot engine tests and does not depend on your story.

## 11. Export

- **Ren'Py.** Use "Build Distributions" in the launcher. Files specific to Godot and to the tools are already excluded in `game/options.rpy`.
- **Godot.** In "Project → Export", add `*.rpy, *.json` to the non-resource file filters and exclude `*.webm`.

## Going further

The [spec](SPEC.md) lists what the shared script accepts and the small differences between the two engines. The full scene-sheet format is described in [contenu/README.md](contenu/README.md).
