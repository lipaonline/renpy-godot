## Tests Ren'Py propres au moteur (fichier réservé à Ren'Py, ignoré par Godot).
## Les tests de parcours et de galerie sont générés depuis les fiches dans
## game/tests_routes.rpy (tools/fiches.py generer).
##
##   renpy.sh <projet> test

testsuite global:
    teardown:
        exit


## Vidéo seule, sans clic simulé : vérifie que Ren'Py lit bien le WebM.
testcase video_seule:
    click "Start"
    pause 1.0
    run Jump("test_video_seule")
    pause 1.0
    screenshot "renpy_video_a.png"
    pause 1.5
    screenshot "renpy_video_b.png"
    # Retour au menu principal : chaque test démarre du même endroit.
    run MainMenu(confirm=False)
    pause 1.0


label test_video_seule:
    $ renpy.movie_cutscene("videos/lena_scene_01.webm")
    "Vidéo terminée."
    return
