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
├── graphe.html         (generated) interactive route graph, to open in a browser
└── graphe.md           (generated) route graph (Mermaid)
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
5. **Generation.** `.venv/bin/python tools/fiches.py generer` writes `game/story/*.rpy`, `game/galerie.json` and `game/navigation.json` (maps and character presence), then has the Godot compiler re-read the result.
6. **Tracking.** `production` (images and videos to render) and `graphe` (routes). `graphe --ouvrir` opens `graphe.html` in the browser: one card per scene, one link per choice, the test routes and the warnings of `verifier`; click a scene to read its content and the possible variable values on entry.
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
| `personnages.<id>` (characters) | `nom` (name), `age` (optional; when given, at least `age_minimum`, 18 by default), `couleur` (colour, #rrggbb), `role`, `biographie`, `personnalite`, `desirs` (desires), `contradictions`, `limites` (limits), `secrets`, `traits` (list, for the writing context), `images` (sprites), `avatar` (small portrait shown on the maps), `presence` (where the character is, see [Navigation](#navigation-maps-rooms-and-character-presence)), `jauges` (gauges), `competences` (skills) and `relations` (see [Gauges, skills and relationships](#gauges-skills-and-relationships)). The lowercase id is used in the sheets: `lena: "…"`. |
| `lieux.<id>` (locations) | `nom` (name shown on the maps; the id otherwise), `description`, `decors` (background images: a list, or a dictionary slot → image, see [Time](#time-slots-days-and-backgrounds)), `icone` (image of the room, shown as a round icon). |
| `cartes.<id>` (maps) | Navigation maps: `titre` (title), `affichage` (layout: `carte` or `pieces`), `image`, `parent`, `lieux` (see [Navigation](#navigation-maps-rooms-and-character-presence)). |
| `variables.<name>` | `defaut` (default: number, boolean or text), `min` and `max` (numbers), `description`. |
| `temps` (time) | `creneaux` (slots), `jours` (days, boolean), `semaine` (week), `date` or `epoques` (calendar, eras), `evenements` (events), `debut` (start); see [Time](#time-slots-days-and-backgrounds). |
| `renommages` (renames) | Names gone since a published version: `variables: {old: new}`, `scenes: {OLD: NEW}`. See [Old saves](#old-saves). |
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
| `carte: ville` (map) | Shows a navigation map (bible, `cartes`): the player picks a location, which plays its scene. |
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
| Time | `- temps: 1` (slots to skip), `- temps: matin` (until the next morning), `- temps: {jours: 3}`, `{mois: 3, creneau: matin}`, `{date: 2027-12-24}`, `{epoque: passe}` | `call temps_avancer`, `temps_sauter_jours`, `temps_sauter_mois`, `temps_epoque_<name>`, or the date set directly |

**Effects:** a number is **added** to a numeric variable (`-2` subtracts 2); a boolean or a text **replaces** the value.

**Expressions** (`si`, `conditions`): bible variables, numbers, texts, `True` / `False`, `+ - *`, comparisons, `and`, `or`, `not`, `in`, `min`, `max`, `abs`. No division and no chained comparisons (`0 < x < 3`), whose results differ between Python and Godot.

**Texts:** `[variable]` inserts a value; Ren'Py tags `{i}…{/i}`, `{b}…{/b}`.

## Navigation: maps, rooms and character presence

A scene that ends with `carte: ville` shows a map: the player picks a location, which plays its scene. Each visited scene ends with `carte: …` in turn, which reopens the navigation from the location the player is in, marked "you are here": inside a building, the row of room icons thus reappears in every room, over its background. It also stays on screen, dimmed and without clicks, during any scene played in a room of a building (the sheet's `lieu` field says where the player is): you always see who is in which room (see `contenu/scenes/ch02/`). Maps are declared in the bible:

```yaml
cartes:
  ville:                          # outdoor map: an image with locations placed on it
    titre: La ville
    image: carte_ville            # background image (placeholder created by "provisoires")
    lieux:
      - lieu: immeuble
        x: 50                     # position, in percent of the image
        y: 36
        carte: immeuble           # opens the sub-map of the rooms
      - lieu: cafe
        x: 80
        y: 66
        scene: CH02_CAFE          # plays this scene
        si: heure < 2             # location offered under a condition (optional)
  immeuble:                       # indoors: a row of round room icons at the bottom left
    titre: L'immeuble
    affichage: pieces
    image: immeuble_coupe         # optional; otherwise the current scene stays visible
    parent: ville                 # "← La ville" button (inferred when a single map opens it)
    lieux:
      - lieu: hall
        scene: CH02_HALL
      - lieu: appartement_lena
        scene: CH02_LENA
        si: heure < 2
      - lieu: appartement_lena    # the same location may lead to another scene depending on the state
        scene: CH02_SOIR
        si: heure >= 2
```

- **Locations.** Each entry names a location of the bible (`lieux`), whose `nom` is the text shown (on hover, for a room icon) and `icone` the image of the room, cropped to a circle. It plays a scene (`scene`) or opens a sub-map (`carte`). From a map, the player also reaches the locations of its sub-maps and of its parent map. A location whose `si` is false is **invisible**: a room forbidden at some hours (the cellar at night) or until a right is obtained (`si: cle_cave`) does not appear.
- **Levels.** Sub-maps nest without limit: France → city → building → flat. A breadcrumb (La France › Lyon › L'immeuble) at the top of every map climbs several levels in one click, on top of the "← parent map" button.
- **Travel.** `temps: 1` (slots) or `temps: {jours: 1}` on an entry: the cost is paid when the player clicks the location, before its scene or the opening of its sub-map (see [Time](#time-slots-days-and-backgrounds)). Conditions of the locations of a sub-map are evaluated after that cost: a city reached in the evening may have nothing open any more.
- **Shortcuts.** `raccourci: true` on an entry offers it from every map (button at the bottom right, except on its own map): "home" from Paris without climbing back to France. Its `si` and `temps` apply everywhere; its name must not be that of a location of another map.
- **Presence.** A character has `presence` rules: a list of `lieu` with an optional `si`; every time a map is shown, the first true rule gives its location (none: absent). The result is the variable **`lieu_<character>`** (for example `lieu_lena`), which the sheets can test: `si: lieu_lena == "cafe"`. It cannot be changed by `effets`.
- **Display.** On every location, the game shows the characters present: their `avatar` (an image, for example `lena avatar`, cropped to a circle and laid on the room icon), otherwise their name in their colour (a disc in their colour on an icon). A location that opens a sub-map shows the characters of all its rooms.
- **Checks.** `verifier` explores maps like menus: locations never reachable, a map with no reachable location on a route, duplicate location names on a map. The tests of both engines click locations by their (translated) name.

## Gauges, skills and relationships

Any character, the player included, can carry **gauges** (`jauges`: mood, confidence…), **skills** (`competences`: photography, DIY…) and **relationships** (`relations`) with other characters. Same format, only the in-game presentation differs:

```yaml
personnages:
  lena:
    jauges:
      stress:
        defaut: 0                 # required; a bare number (stress: 0) is enough
        min: 0
        max: 5
        nom: Stress               # displayed name (optional: the key, capitalised)
        description: Rises when pushed about the past.
    competences:
      photographie: 4
    relations:                    # key: the other character's id; one relationship serves both
      moi:
        defaut: 3
        min: 0
        max: 10
        description: Léna's trust in the protagonist.
        paliers: {0: distante, 4: voisine, 6: amie, 8: confidente}
      karim: {defaut: 5, max: 10, nom: Anciens collègues}
  moi:
    competences:
      observation: {defaut: 0, max: 5}
```

- **Variables.** Each entry becomes the variable `<character>_<name>` (`lena_stress`, `moi_observation`, `lena_moi`, `lena_karim`), declared with `default` in the generated script, saved, changed by `effets` (`effets: {lena_moi: 1}`) and tested in `si` and `conditions` (`si: moi_observation >= 1`). A global variable of the bible cannot take such a name.
- **Relationships.** A relationship is declared once, on either character, under the other character's id; it appears on both sheets. Without `nom`, the game shows the other character's name in their colour. A gauge or a skill cannot take a character's id as its name.
- **Thresholds.** `paliers` maps thresholds to names: the highest threshold reached gives the level, shown in the game and recalled in the writing context (`lena_moi : 5 (voisine)`). Thresholds stay within `min` / `max`.
- **"Characters" screen.** `generer` writes `game/personnages.json`: avatar, name, gauges, skills and relationships (variable, bounds, thresholds). Ren'Py shows it in the game menu (`game/personnages.rpy`, "Characters" button), and so does Godot (`engine/ui/characters_page.gd`): one vertical tab per character (round avatar and name), and the open sheet with one bar per entry, the value over the maximum and the level reached. Only characters with at least one entry appear.
- **Translations.** Names of gauges, skills, named relationships and levels go through `traduire`, like location names.
- **Checks.** `verifier` validates names, bounds (`min` ≤ `max`, thresholds within bounds, distinct level names), relationships (existing other character, declared once) and reports a gauge going out of bounds on a route.

## Time: slots, days and backgrounds

Time is declared in the bible; without this block the game has no notion of time.

```yaml
temps:
  creneaux: [matin, midi, soir]     # at least two, in the order of the day
  jours: true                       # counts days (day 1, 2…); implied by « semaine » or a date
  semaine: [lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche]   # optional; implied by a date
  date: 2026-10-16                  # real calendar: jour_mois, mois, annee, jour_semaine follow the dates
  evenements:                       # booleans evenement_<name>, true on that day every year
    noel: {mois: 12, jour: 25}
    anniversaire_lena: {mois: 10, jour: 17}
  debut: {creneau: soir}            # optional: first slot (and jour, jour_semaine without a date; epoque)

lieux:
  appartement_lena:
    decors: {matin: appartement_jour, midi: appartement_jour, soir: appartement_soir}
```

- **Generated variables**: `creneau` (rank, 0 for the first slot), `moment` (slot name), `jour` (day counter since the start), `jour_semaine` (weekday), and with a date `jour_mois` (day of month), `mois` (1 to 12), `annee` (year), `evenement_<name>`. Sheets read them (`si: moment == "soir"`, `si: jour_semaine == "samedi"`, `si: evenement_noel`, `si: mois == 12 and jour_mois >= 20`) but cannot change them through `effets`.
- **Moving on**: `- temps: 1` moves one slot forward (2 for two), `- temps: matin` moves to the next morning; after the last slot, the next day starts at the first one. Ellipses keep the slot unless `creneau` is given: `- temps: {jours: 3}`, `- temps: {mois: 3, creneau: matin}` (same day of month, or the last day of the target month: 31 January + 1 month = 28 February), `- temps: {date: 2027-12-24}` (a date known in advance, past or future). The generated script holds the `temps_*` labels called by these elements; the calendar handles leap years.
- **Time travel**: `epoques` replaces `date` with one date per era; `debut.epoque` (else the first) is the starting era. `- temps: {epoque: passe}` stores the current date in the era being left and resumes the date of the era being joined, where it was left. Variables are shared across eras: a clue found in the past is readable in the present, and `epoque` (`si: epoque == "passe"`) serves presence rules, maps and backgrounds (`decors: {passe: chantier_1987, present: chantier_jour}`, keys are slots or eras).

  ```yaml
  temps:
    creneaux: [matin, midi, soir]
    epoques: {present: 2026-10-16, passe: 2016-10-16}
    debut: {creneau: soir, epoque: present}
  ```
- **Backgrounds per slot**: a location whose `decors` is a dictionary slot (or era) → image is set with `- decor: <location id>`; the game picks the image of the current slot, or the first one declared. The images remain entries of `production`.
- **Display**: during a game, "Day 2 · Tuesday · morning" or, with a calendar, "Friday 16 October 2026 · evening" at the top right, in both engines (Ren'Py: screen `temps_permanent`, `game/temps.rpy`; Godot: `engine/temps.gd`), hidden on the maps. Slot, weekday and month names go through `traduire`.
- **Presence and locations**: `presence` rules and the `si` of maps test these variables like any other (`si: moment != "soir"` for a cellar closed in the evening).
- **Checks**: distinct slots, valid dates, a 7-name week with a calendar, possible events, at least two eras, valid `debut`, reserved names `creneau`, `moment`, `jour`, `jour_semaine`, `jour_mois`, `mois`, `annee`, `epoque` and prefixes `temps_`, `evenement_`, `epoque_`, the `moment` of a sheet among the slots, declared backgrounds per slot, jumps consistent with the bible. The route explorer follows time, calendar and eras included, like any other variable.

## Old saves

A save holds the position (label and rank inside it, the `appel` stack) and the variables. Adding characters, gauges, scenes or variables breaks nothing: a new variable takes its `defaut` when the save is loaded, in both engines. What breaks is a name that disappears: a deleted or renamed label (the save no longer loads), a renamed variable (its value goes back to `defaut`). Once the game is published, declare those renames in the bible instead of suffering them:

```yaml
renommages:
  variables:
    relation_lena: lena_moi       # the value saved under relation_lena moves to lena_moi
  scenes:
    CH01_SC03: CH01_SC03A         # a save made inside ch01_sc03 resumes in ch01_sc03a
```

`generer` writes `game/renommages.json`, read by `game/sauvegardes.rpy` on the Ren'Py side (`config.label_overrides` for scenes, an after-load callback for variables) and by the Godot player (`engine/renommages.gd`, applied by the interpreter when a state is loaded). Chained renames (`a: b` then `b: c`) apply in the declared order. `verifier` rejects a rename whose old name still exists or whose new name does not. Do not edit the inside of a published scene before a possible save point: add scenes instead.

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

- **Bible:** character ages, when given, at least `age_minimum` (18 by default), valid identifiers, typed variables, gauges, skills and relationships (numbers, bounds, thresholds, relationship declared once), time (slots, start, reserved names, backgrounds per slot), consistent maps (declared locations, positions, one destination per location, presence rules).
- **Sheets:** known fields, declared characters, locations and maps, existing destinations, expressions compatible with both engines, variables quoted in texts.
- **Routes:** every combination of choices and locations is played. The tool reports:
  - entry conditions that are false, with the faulty route;
  - variables out of bounds;
  - menus with no available choice and maps with no reachable location;
  - scenes never reached, choices never offered and locations never reachable;
  - a story with no ending.
- **Translations:** lines and texts to translate or to review, `[variables]` and `{tags}` kept, choices of a menu (and locations of a map) still distinct once translated, entries that no longer match the script.
- **Script:** no hand-written `.rpy` redefines a label or a variable produced by the sheets. Hand-written files are never overwritten without `--remplacer` (replace).
