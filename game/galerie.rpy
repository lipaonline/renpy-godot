## Galerie Ren'Py : lit game/galerie.json, le même fichier que le lecteur Godot.
## Fichier réservé à Ren'Py (hors de game/story/, donc ignoré par Godot).
##
## Mêmes règles que engine/gallery.gd : une entrée est débloquée dès que son label
## a été atteint une fois (renpy.seen_label) ; elle montre ses images une par une
## sur fond noir, ou sa vidéo. Les entrées invalides sont ignorées et signalées.

init python:
    import builtins
    import json

    def galerie_charger():
        with renpy.open_file("galerie.json", "utf-8") as fichier:
            donnees = json.load(fichier)
        # Dans le store Ren'Py, dict et list désignent les versions « révertables » :
        # json renvoie les types Python d'origine, d'où builtins.
        if not isinstance(donnees, builtins.dict) or not isinstance(donnees.get("entrees"), builtins.list):
            print('galerie.json : format attendu {"entrees": [ ... ]}')
            return []
        entrees = []
        for numero, entree in enumerate(donnees["entrees"], 1):
            ou = "galerie.json, entrée {}".format(numero)
            if not isinstance(entree, builtins.dict):
                print("{} : objet attendu".format(ou))
                continue
            label = entree.get("label", "")
            images = entree.get("images", [])
            video = entree.get("video", "")
            if not renpy.has_label(label):
                print("{} : label inconnu « {} »".format(ou, label))
                continue
            if not images and not video:
                print("{} : il faut « images » ou « video »".format(ou))
                continue
            entrees.append({
                "titre": entree.get("titre", label),
                "label": label,
                "vignette": entree.get("vignette", images[0] if images else ""),
                "images": images,
                "video": video,
            })
        return entrees

    def galerie_ouvrir(entree):
        if entree["video"]:
            renpy.call_in_new_context("galerie_video", entree["video"])
        else:
            renpy.call_in_new_context("galerie_images", entree["images"])

define galerie_entrees = galerie_charger()


screen galerie():

    tag menu

    use game_menu(_("Galerie")):

        vpgrid:
            cols 3
            spacing 30

            for entree in galerie_entrees:
                $ debloquee = renpy.seen_label(entree["label"])
                $ titre = entree["titre"] if debloquee else "???"

                button:
                    xysize (430, 310)
                    background Frame("gui/button/slot_idle_background.png", gui.slot_button_borders)
                    hover_background Frame("gui/button/slot_hover_background.png", gui.slot_button_borders)
                    sensitive debloquee
                    action Function(galerie_ouvrir, entree)

                    vbox:
                        align (0.5, 0.5)
                        spacing 6

                        fixed:
                            xysize (400, 225)
                            if debloquee:
                                add Transform(entree["vignette"], fit="contain", xysize=(400, 225)) align (0.5, 0.5)
                            else:
                                text _("Verrouillé") align (0.5, 0.5) color gui.insensitive_color

                        text titre:
                            substitute False
                            xalign 0.5
                            size 24
                            color (gui.idle_small_color if debloquee else gui.insensitive_color)


## Visionneuses, lancées dans un nouveau contexte comme la galerie native de Ren'Py.
## Le menu rapide et le menu de jeu sont désactivés le temps de la visite.

label galerie_video(chemin):
    $ galerie_avant = (quick_menu, _game_menu_screen)
    $ quick_menu = False
    $ _game_menu_screen = None
    $ renpy.movie_cutscene(chemin)
    $ quick_menu, _game_menu_screen = galerie_avant
    return


label galerie_images(noms):
    $ galerie_avant = (quick_menu, _game_menu_screen)
    $ quick_menu = False
    $ _game_menu_screen = None
    window hide
    python:
        for nom in noms:
            renpy.scene()
            renpy.show("black")
            renpy.show(nom, at_list=[truecenter])
            renpy.pause()
    $ quick_menu, _game_menu_screen = galerie_avant
    return
