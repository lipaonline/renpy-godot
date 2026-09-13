# Writing the game: story bible and scene sheets

[Version française](LISEZMOI.md)

The game script (`game/story/*.rpy`) is no longer written by hand. It is **produced from this folder** by `tools/fiches.py`, within the Ren'Py / Godot common subset.

The file format uses French keys (`titre` = title, `lieu` = location, `personnages` = characters…); each one is translated below.

```
contenu/
├── bible.yaml          characters, locations, variables, editorial rules
├── scenes/…/*.yaml     one sheet per scene (free subfolders: ch01/, ch02/…)
├── traductions/*.yaml  one file per translation (en.yaml…), updated by traduire
├── production.md       (generated) images and videos to produce
└── graphe.md           (generated) route graph
```

## Setup (once)

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Workflow

1. **Skeleton.** Create the sheet: `id`, `titre`, `lieu`, `personnages`, `objectif_narratif`, and how the scene ends (`choix`, `suite`, `fin` or `retour`). Link it from another scene.
2. **Context.** `.venv/bin/python tools/fiches.py contexte CH02_SC08 -o contexte.md` produces the pack to hand to a writer or an AI: sheets of the characters present, possible variable values on entry, summaries of what came before, objective, editorial rules, expected format.
3. **Writing.** Fill in `contenu` and `choix`.
4. **Check.** `.venv/bin/python tools/fiches.py verifier`.
5. **Generation.** `.venv/bin/python tools/fiches.py generer` writes `game/story/*.rpy` and `game/galerie.json`, then has the Godot compiler re-read the result.
6. **Tracking.** `production` (images and videos to render) and `graphe` (routes as Mermaid).
7. **Placeholder media.** `provisoires` creates an image (in `game/images/provisoires/`) or a video for every missing asset, so the game stays playable. As soon as a final image with the same name arrives in `game/images/`, the placeholder is removed; a replaced video is recognised by its content. `production` tells final, placeholder and missing apart.
8. **Translation.** `traduire en` (translate) adds the new lines and texts to `traductions/en.yaml`. Fill in `texte`, then run `generer`, which writes `game/tl/english/story/`. See [Translations](#translations).

## Generated tests

`generer` picks a small set of complete routes that covers every ending and every choice, then writes:

- `tests/routes_attendues.json`: Godot replays each route and must reach the same ending and the same final variable state as the Python explorer;
- `game/tests_routes.rpy`: Ren'Py replays the same routes by clicking the choices, then opens the gallery after unlocking all of its entries.

Both engines replay the routes in every language of the game, clicking the translated choices. These tests follow the story automatically: nothing needs updating by hand when the sheets change.

## Bible (`bible.yaml`)

| Field | Contents |
|---|---|
| `debut` (start) | Id of the first scene. |
| `personnages.<id>` (characters) | `nom` (name), **`age` (required, at least `age_minimum`, 18 by default)**, `couleur` (colour, #rrggbb), `role`, `biographie`, `personnalite`, `desirs` (desires), `contradictions`, `limites` (limits), `secrets`, `images` (sprites). The lowercase id is used in the sheets: `lena: "…"`. |
| `lieux.<id>` (locations) | `description`, `decors` (background images). |
| `variables.<name>` | `defaut` (default: number, boolean or text), `min` and `max` (numbers), `description`. |
| `regles_editoriales` | Editorial rules, repeated in the writing context. |
| `synopsis`, `mystere_central` | Optional; included in the writing context. |
| `langues` (languages) | `source`: language of the sheets (`fr` by default). `traductions`: list of translation codes (`en`, `es`, `de`, `it`, `pt`, `nl`, `pl`, `ru`, `ja`, `ko`, `zh`). |

## Scene sheet

| Field | Contents |
|---|---|
| `id` | Uppercase letters, digits and _ (`CH02_SC08`). Gives the label (`ch02_sc08`) and the file (`chapitre_02.rpy`, from `CHxx` or the `chapitre` field). |
| `titre` (title), `lieu` (location), `moment` (time), `personnages` (characters), `objectif_narratif` (narrative goal), `resume` (summary), `notes` | Metadata. `resume` feeds the context of the following scenes. |
| `conditions` | Entry conditions, checked on **every** route: a list of expressions (`- relation_lena >= 4`) or the compact form (`relation_lena_min: 4`, `indice_photo: true`). |
| `contenu` (content) | List of elements (below). |
| `choix` (choices) | A list of options, or `question` (a line) + `options`. Option: `libelle` (label), `destination`, and optionally `si` (if), `effets` (effects), `contenu`. |
| `suite` (next) | Next scene, without a choice. |
| `fin: true` (end) | End of the game (back to the main menu). |
| `retour: true` (return) | Scene called with `appel` (a memory, a reusable interlude): returns after the call. |
| `galerie` (gallery) | `titre`, `vignette` (thumbnail), and `images` (list) or `video`. The entry unlocks once the scene has been reached. |

## Content elements

| Element | Example | Produces |
|---|---|---|
| Narration | `- narration: "Il pleut."` | `"Il pleut."` |
| Line | `- lena: "Salut."` | `lena "Salut."` |
| Background | `- decor: rue_nuit` + `transition: fade` | `scene rue_nuit with fade` |
| Character | `- montrer: lena sourire` (show) + `position: right`, `transition: dissolve` | `show lena sourire at right with dissolve` |
| Hide | `- cacher: lena` | `hide lena` |
| Video | `- video: videos/scene.webm` | `$ renpy.movie_cutscene("videos/scene.webm")` |
| Pause | `- pause: 1.5` (empty: wait for a click) | `pause 1.5` |
| Audio | `- musique: audio/theme.ogg`, `- musique: stop`, `- son: audio/porte.ogg` (sound) | `play music …`, `stop music`, `play sound …` |
| Effects | `- effets: {relation_lena: 2, indice_photo: true}` | `$ relation_lena += 2`, `$ indice_photo = True` |
| Condition | `- si: indice_photo` + `alors: […]` (then), `sinon_si: [{si: …, alors: […]}]` (elif), `sinon: […]` (else) | `if / elif / else` |
| Call | `- appel: CH01_SOUVENIR` | `call ch01_souvenir` |

**Effects:** a number is **added** to a numeric variable (`-2` subtracts 2); a boolean or a text **replaces** the value.

**Expressions** (`si`, `conditions`): bible variables, numbers, texts, `True` / `False`, `+ - *`, comparisons, `and`, `or`, `not`, `in`, `min`, `max`, `abs`. No division and no chained comparisons (`0 < x < 3`), whose results differ between Python and Godot.

**Texts:** `[variable]` inserts a value; Ren'Py tags `{i}…{/i}`, `{b}…{/b}`.

## Translations

Each code listed in `langues.traductions` has its file `traductions/<code>.yaml`, created and updated by `.venv/bin/python tools/fiches.py traduire <code>`:

```yaml
repliques:                      # lines, by identifier
  ch01_sc02_14e17bdd:
    qui: lena                   # who speaks (for information)
    source: "Je ne pensais pas que tu viendrais."   # original text: do not edit
    texte: "I didn't think you'd come."             # translation; empty = not translated yet
textes:                         # names, choices and gallery titles, by original text
  - source: "Lui faire confiance"
    texte: "Trust her"
```

- **Identifiers.** Each line gets an identifier computed from its scene, its speaker and its text. `generer` writes it into the script (`lena "…" id ch01_sc02_14e17bdd`). Adding lines elsewhere does not change it.
- **Changes.** When a sheet changes, run `traduire` again:
  - new lines and texts are added with an empty `texte`;
  - if an original text changed, its translation is kept and marked `a_revoir` (to review), with the old original: check the translation, then delete the `a_revoir` line;
  - translations that no longer match anything move to `obsoletes`.
- **Missing translations** are not an error: the game shows the original text. `verifier` counts them.
- **Translator or AI.** `traduire en --paquet traduction.md` writes a pack: instructions, characters, glossary and entries to translate. Save the answer to a file and import it with `traduire en --importer reponse.yaml`.
- **Generated files.** `generer` writes the translated lines to `game/tl/<language>/story/chapitre_XX.rpy` (Ren'Py `translate` blocks), and the texts to `textes.rpy` (`translate strings`). Ren'Py and Godot both read them.

## YAML pitfalls

- Put **every text between quotes**: otherwise a sentence containing ": " breaks the file.
- Unquoted `yes`, `no`, `on`, `off` become booleans.
- Indent with spaces.

## What `verifier` checks

- **Bible:** an age for every character, at least `age_minimum` (18 by default), valid identifiers, typed variables.
- **Sheets:** known fields, declared characters and locations, existing destinations, expressions compatible with both engines, variables quoted in texts.
- **Routes:** every combination of choices is played. The tool reports:
  - entry conditions that are false, with the faulty route;
  - variables out of bounds;
  - menus with no available choice;
  - scenes never reached and choices never offered;
  - a story with no ending.
- **Translations:** lines and texts to translate or to review, `[variables]` and `{tags}` kept, choices of a menu still distinct once translated, entries that no longer match the script.
- **Script:** no hand-written `.rpy` redefines a label or a variable produced by the sheets. Hand-written files are never overwritten without `--remplacer` (replace).
