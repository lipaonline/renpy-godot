# Fichier généré par tools/fiches.py depuis contenu/ : ne pas modifier à la main.
# Tests de parcours Ren'Py : renpy.sh <projet> test


testcase route_01:
    $ _test.timeout = 30.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch01_sc04", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch01_sc04"), None)
    click "Start"
    advance until screen "choice"
    click "Monter directement"
    advance until screen "choice"
    click "Lui faire confiance"
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch01_sc04"), "fin attendue non atteinte : ch01_sc04"


testcase route_02:
    $ _test.timeout = 30.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch01_sc05", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch01_sc05"), None)
    click "Start"
    advance until screen "choice"
    click "Regarder la boîte aux lettres"
    advance until screen "choice"
    click "Repartir sous la pluie"
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch01_sc05"), "fin attendue non atteinte : ch01_sc05"


testcase route_03:
    $ _test.timeout = 30.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch01_sc04", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch01_sc04"), None)
    click "Start"
    advance until screen "choice"
    click "Regarder la boîte aux lettres"
    advance until screen "choice"
    click "L'interroger sur la photo"
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch01_sc04"), "fin attendue non atteinte : ch01_sc04"


testcase galerie:
    $ _test.timeout = 30.0
    click "Start"
    pause 0.5
    run Jump("ch01_sc03a")
    pause 0.5
    run Jump("ch01_sc03b")
    pause 0.5
    run MainMenu(confirm=False)
    pause 1.0
    click "Galerie"
    pause 1.0
    screenshot "renpy_galerie.png"
    $ assert len(galerie_entrees) == 2, galerie_entrees
    $ assert all(renpy.seen_label(e["label"]) for e in galerie_entrees), galerie_entrees
