# Fichier généré par tools/fiches.py depuis contenu/ : ne pas modifier à la main.
# Tests de parcours Ren'Py : renpy.sh <projet> test


testcase route_01:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Monter directement")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Lui faire confiance")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_01_1.png"
    run Function(tests_viser, "La salle de bain")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "La chambre")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "La cuisine")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "Le salon")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Le café de la gare")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_01_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    screenshot "renpy_en.png"
    run Function(tests_viser, "Go straight up")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Trust her")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The bathroom")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The bedroom")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The kitchen")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The living room")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The station café")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_02:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Regarder la boîte aux lettres")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "L'interroger sur la photo")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_02_1.png"
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_02_2.png"
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'appartement de mon père")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "La salle de bain")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "La cave")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_02_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Check the letterbox")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Ask her about the photo")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "My father's flat")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The bathroom")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The cellar")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_03:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Regarder la boîte aux lettres")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "L'interroger sur la photo")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_03_1.png"
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_03_2.png"
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_03_3.png"
    run Function(tests_viser, "Le café de la gare")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'appartement de mon père")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "La salle de bain")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Le chantier")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_03_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Check the letterbox")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Ask her about the photo")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The station café")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "My father's flat")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The bathroom")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The construction site")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_04:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Monter directement")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Lui faire confiance")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_04_1.png"
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_04_2.png"
    run Function(tests_viser, "La cave")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'appartement de mon père")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "La salle de bain")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "La chambre")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "La cuisine")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "Le salon")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_04_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Go straight up")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Trust her")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The cellar")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "My father's flat")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The bathroom")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The bedroom")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The kitchen")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The living room")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_05:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Regarder la boîte aux lettres")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Lui faire confiance")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_05_1.png"
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_05_2.png"
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_05_3.png"
    run Function(tests_viser, "Le chantier")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'appartement de mon père")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "La salle de bain")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Le café de la gare")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_05_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Check the letterbox")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Trust her")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The construction site")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "My father's flat")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The bathroom")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The station café")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_06:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch01_sc05", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch01_sc05"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Monter directement")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Repartir sous la pluie")
    pause 0.5
    pause until not screen "choice"
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch01_sc05"), "fin attendue non atteinte : ch01_sc05"


testcase route_06_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch01_sc05", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch01_sc05"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Go straight up")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Leave in the rain")
    pause 0.5
    pause until not screen "choice"
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch01_sc05"), "fin attendue non atteinte : ch01_sc05"


testcase route_07:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Monter directement")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Lui faire confiance")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_07_1.png"
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_07_2.png"
    run Function(tests_viser, "Le hall")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Le café de la gare")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_07_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Go straight up")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Trust her")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The lobby")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The station café")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_08:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Monter directement")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Lui faire confiance")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_08_1.png"
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_08_2.png"
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_08_3.png"
    run Function(tests_viser, "← La France")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_08_4.png"
    run Function(tests_viser, "Cannes")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_08_5.png"
    run Function(tests_viser, "La plage")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← La France")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_08_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Go straight up")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Trust her")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← France")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Cannes")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The beach")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← France")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_09:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Monter directement")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Lui faire confiance")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_09_1.png"
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_09_2.png"
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_09_3.png"
    run Function(tests_viser, "← La France")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_09_4.png"
    run Function(tests_viser, "Paris")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_09_5.png"
    run Function(tests_viser, "Les archives")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← La France")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_09_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Go straight up")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Trust her")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "← France")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Paris")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The archives")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← France")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_10:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Regarder la boîte aux lettres")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Lui faire confiance")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_10_1.png"
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_10_2.png"
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'appartement de mon père")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "La salle de bain")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_10_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Check the letterbox")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Trust her")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "My father's flat")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The bathroom")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_11:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Monter directement")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Lui faire confiance")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_11_1.png"
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_11_2.png"
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Le café de la gare")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_11_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Go straight up")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Trust her")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The station café")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_12:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Monter directement")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Lui faire confiance")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    screenshot "renpy_carte_12_1.png"
    run Function(tests_viser, "← L'immeuble")
    pause 0.5
    pause 1.0
    screenshot "renpy_carte_12_2.png"
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Le chantier")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "L'immeuble")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "L'appartement de Léna")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase route_12_en:
    $ _test.timeout = 120.0
    $ _test.transition_timeout = 0.05
    $ renpy.game.persistent._seen_ever.pop("ch02_epilogue", None)
    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64("ch02_epilogue"), None)
    pause until screen "main_menu"
    run Language("english")
    pause 0.5
    run Start()
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Go straight up")
    pause 0.5
    pause until not screen "choice"
    advance until screen "choice"
    pause 0.5
    run Function(tests_viser, "Trust her")
    pause 0.5
    pause until not screen "choice"
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "← Lyon")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "The construction site")
    pause 0.5
    advance until screen "carte"
    pause 1.0
    run Function(tests_viser, "The building")
    pause 0.5
    pause 1.0
    run Function(tests_viser, "Léna's flat")
    pause 0.5
    advance until screen "main_menu"
    $ assert renpy.seen_label("ch02_epilogue"), "fin attendue non atteinte : ch02_epilogue"


testcase galerie:
    $ _test.timeout = 30.0
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    pause 0.5
    run Jump("ch01_sc03a")
    pause 0.5
    run Jump("ch01_sc03b")
    pause 0.5
    run MainMenu(confirm=False)
    pause 1.0
    run ShowMenu("galerie")
    pause 1.0
    screenshot "renpy_galerie.png"
    $ assert len(galerie_entrees) == 2, galerie_entrees
    $ assert all(renpy.seen_label(e["label"]) for e in galerie_entrees), galerie_entrees
    run Return()
    pause 1.0


testcase personnages:
    $ _test.timeout = 30.0
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "say"
    pause 0.5
    run ShowMenu("personnages")
    pause 1.0
    screenshot "renpy_personnages.png"
    $ assert [f['id'] for f in personnages_fiches] == ['moi', 'lena', 'karim'], personnages_fiches
    $ assert moi_observation == 0, moi_observation
    $ assert lena_photographie == 4, lena_photographie
    $ assert lena_moi == 3, lena_moi
    $ assert lena_karim == 5, lena_karim
    $ assert karim_chantier == 5, karim_chantier
    run Function(tests_onglet, "personnages", "personnages_onglet", "lena")
    pause 0.5
    screenshot "renpy_personnages_2.png"
    run MainMenu(confirm=False)
    pause 1.0


testcase temps:
    $ _test.timeout = 30.0
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "say"
    pause 0.5
    screenshot "renpy_temps.png"
    $ assert moment == "soir", moment
    $ assert temps_texte() == "vendredi 16 octobre 2026 · soir", temps_texte()
    run MainMenu(confirm=False)
    pause 1.0


testcase renommages:
    $ _test.timeout = 30.0
    pause until screen "main_menu"
    run Language("french")
    pause 0.5
    run Start()
    advance until screen "say"
    pause 0.5
    $ setattr(store, "relation_lena", 70 + 1)
    advance
    advance until screen "say"
    pause 0.5
    run FileSave("test_renommages", confirm=False)
    pause 0.5
    run FileLoad("test_renommages", confirm=False)
    pause 1.0
    $ assert lena_moi == 70 + 1, lena_moi
    $ assert not hasattr(store, "relation_lena"), "relation_lena"
    run MainMenu(confirm=False)
    pause 1.0
