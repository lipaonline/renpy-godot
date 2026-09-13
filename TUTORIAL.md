# Tutorial: from the demo to your own game

[Version française](TUTORIEL.md)

This tutorial starts from the demo game and takes you to your own game, played by Ren'Py and by Godot. Allow about an hour.

The demo game, the tool commands and the scene-sheet keys are in French; their meaning is given as we go (`verifier` = check, `generer` = generate, `provisoires` = placeholders…).

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

Try both endings: trust Léna, or leave in the rain. Look at the photo in the letterbox to unlock one more choice. Open the gallery from the main menu.

## 2. Understand the pipeline

```
contenu/bible.yaml            characters, locations, variables
contenu/scenes/**/*.yaml      one sheet per scene
        │  tools/fiches.py verifier   → checks every route
        │  tools/fiches.py generer    → writes:
        ▼
game/story/*.rpy              shared script, read by Ren'Py AND by Godot
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
    age: 30                      # required; the minimum is set by age_minimum (18 by default)
    biographie: The neighbourhood bookseller.
    images: [sam neutre]

variables:
  amitie_sam: {defaut: 0, min: 0, max: 10, description: Sam's friendship.}
```

In the sheets, Sam speaks with `- sam: "…"`, and effects change his variables: `effets: {amitie_sam: 1}`. A number is added, a boolean or a text replaces the value.

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

## 8. Tests

```sh
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
godot --headless --path . --script res://tests/run_tests.gd
$RENPY_SDK/renpy.sh . lint
$RENPY_SDK/renpy.sh . test --overwrite-screenshots
```

`generer` picks a few routes that cover every ending and every choice. Godot must reach exactly the final state computed in Python; Ren'Py replays the same routes by clicking the choices. The tests therefore follow your story without you having to write them.

## 9. Start your own game from scratch

1. **Copy.** Copy this repository into a new folder, which becomes your project.
2. **Clear the content.** Delete the demo sheets (`contenu/scenes/ch01/`) and replace `contenu/bible.yaml` with your own. Delete the demo media in `game/images/` and `game/videos/`, except `lena_scene_01.webm`, used by the Ren'Py test `video_seule` in `game/testcases.rpy` (adapt that test if you remove it).
3. **Rename.** Change the game's name:
   - `config/name` in `project.godot`;
   - `config.name`, `build.name` and `config.save_directory` in `game/options.rpy`.
4. **Build.** Write your sheets, then run `verifier`, `provisoires` and `generer`.
5. **Keep the fixture.** Keep `tests/fixtures/demo/`: this frozen test game is used by the Godot engine tests and does not depend on your story.

## 10. Export

- **Ren'Py.** Use "Build Distributions" in the launcher. Files specific to Godot and to the tools are already excluded in `game/options.rpy`.
- **Godot.** In "Project → Export", add `*.rpy, *.json` to the non-resource file filters and exclude `*.webm`.

## Going further

The [spec](SPEC.md) lists what the shared script accepts and the small differences between the two engines. The full scene-sheet format is described in [contenu/README.md](contenu/README.md).
