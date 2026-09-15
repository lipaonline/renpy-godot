## Outils des tests Ren'Py générés (game/tests_routes.rpy, tools/fiches.py) : au lieu de cliquer
## un bouton par sa position (la souris simulée de Ren'Py 8.5 tombe à côté quand la fenêtre est
## mise à l'échelle), les tests donnent le focus au bouton par son texte, puis envoient
## l'événement « button_select » (Entrée) : le bouton s'active par la voie normale des événements.
## Fichier réservé à Ren'Py (hors de game/story/, donc ignoré par Godot).

init python:

    def tests_viser(texte):
        """Donne le focus au bouton dont le texte (alt) est exactement celui-ci."""
        cible = texte.casefold()
        candidats = [f for f in renpy.display.focus.focus_list
                     if f.x is not None and f.widget._tts_all(False).casefold().strip() == cible]
        if not candidats:
            visibles = sorted({f.widget._tts_all(False) for f in renpy.display.focus.focus_list if f.x is not None})
            raise Exception("tests : bouton « {} » introuvable parmi {}".format(texte, visibles))
        f = candidats[0]
        renpy.display.focus.set_focused(f.widget, f.arg, f.screen)
        # Comme la touche Entrée : l'événement « button_select » active le bouton qui a le focus,
        # par la voie normale des événements, ce qui termine le menu ou joue l'action du lieu.
        renpy.queue_event("button_select")

    def tests_onglet(ecran, variable, valeur):
        """Change une variable d'un écran affiché (onglet des fiches de personnages)."""
        renpy.get_screen(ecran).scope[variable] = valeur
        renpy.restart_interaction()
