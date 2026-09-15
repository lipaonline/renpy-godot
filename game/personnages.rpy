## Écran « Personnages » du menu de jeu : lit game/personnages.json (produit par tools/fiches.py
## depuis les blocs « jauges », « competences » et « relations » de la bible), le même fichier que le lecteur
## Godot (engine/ui/characters_page.gd). Fichier réservé à Ren'Py (hors de game/story/).
##
## Un onglet vertical par personnage (avatar et nom) ; la fiche ouverte montre l'avatar, le nom dans sa
## couleur, puis ses jauges, ses compétences et ses relations (nom de l'autre personnage dans sa
## couleur) : une barre, la valeur sur le maximum, et le nom du plus haut palier atteint
## (« paliers » de la bible). Les valeurs sont les variables du jeu (<personnage>_<nom>) :
## l'écran n'existe donc qu'en cours de partie.

init python:
    import builtins
    import json

    def personnages_charger():
        try:
            with renpy.open_file("personnages.json", "utf-8") as fichier:
                donnees = json.load(fichier)
        except Exception as exc:
            print("personnages.json illisible ({}) : aucune fiche".format(exc))
            return []
        # Dans le store Ren'Py, dict et list désignent les versions « révertables » :
        # json renvoie les types Python d'origine, d'où builtins.
        if not isinstance(donnees, builtins.dict) or not isinstance(donnees.get("personnages"), builtins.dict):
            print('personnages.json : format attendu {"personnages": {...}}')
            return []
        fiches = []
        for pid, perso in donnees["personnages"].items():
            ou = "personnages.json, personnage « {} »".format(pid)
            if not isinstance(perso, builtins.dict):
                print("{} : objet attendu".format(ou))
                continue
            fiche = {"id": pid, "nom": perso.get("nom", pid), "couleur": perso.get("couleur") or "",
                     "avatar": perso.get("avatar") or "", "jauges": [], "competences": [], "relations": []}
            for champ in ("jauges", "competences", "relations"):
                for numero, jauge in enumerate(perso.get(champ) or [], 1):
                    la = "{}, {} {}".format(ou, champ, numero)
                    if not isinstance(jauge, builtins.dict) or not jauge.get("variable"):
                        print("{} : objet avec « variable » attendu".format(la))
                        continue
                    paliers = [(p.get("des", 0), p.get("nom", "")) for p in jauge.get("paliers") or []
                               if isinstance(p, builtins.dict)]
                    fiche[champ].append({"variable": jauge["variable"], "nom": jauge.get("nom", jauge["variable"]),
                                         "couleur": jauge.get("couleur") or "",
                                         "min": jauge.get("min", 0), "max": jauge.get("max", 0),
                                         "paliers": sorted(paliers, key=lambda p: p[0])})
            fiches.append(fiche)
        return fiches

    def personnages_valeur(jauge):
        """Valeur actuelle de la variable de la jauge (0 si elle manque au script)."""
        valeur = getattr(store, jauge["variable"], 0)
        return valeur if isinstance(valeur, (int, float)) else 0

    def personnages_palier(jauge, valeur):
        """Nom du plus haut palier atteint, ou une chaîne vide (mêmes règles que Godot)."""
        nom = ""
        for seuil, candidat in jauge["paliers"]:
            if valeur >= seuil:
                nom = candidat
        return nom

define personnages_fiches = personnages_charger()


screen personnages():

    tag menu

    # Onglet ouvert : identifiant du personnage (le premier au départ).
    default personnages_onglet = personnages_fiches[0]["id"] if personnages_fiches else ""

    use game_menu(_("Characters")):

        if not personnages_fiches:
            text _("No character sheet in game/personnages.json.")

        hbox:
            spacing 40

            ## Onglets verticaux : un par personnage (avatar et nom), sans limite de largeur.
            viewport:
                xsize 360
                yfill True
                mousewheel True
                scrollbars ("vertical" if len(personnages_fiches) > 8 else None)

                vbox:
                    spacing 8

                    for fiche in personnages_fiches:
                        $ actif = fiche["id"] == personnages_onglet
                        button:
                            xfill True
                            ysize 76
                            padding (12, 8, 12, 8)
                            # Fonds plats, comme les onglets du lecteur Godot : ouvert surligné, les autres transparents.
                            background None
                            hover_background "#b48cff1f"
                            selected_background "#b48cff40"
                            selected actif
                            action SetScreenVariable("personnages_onglet", fiche["id"])

                            hbox:
                                spacing 16
                                yalign 0.5
                                fixed:
                                    xysize (56, 56)
                                    yalign 0.5
                                    if fiche["avatar"] and renpy.has_image(fiche["avatar"]):
                                        add navigation_rond(fiche["avatar"], 56)
                                    else:
                                        add navigation_rond(Solid(fiche["couleur"] or gui.accent_color), 56)
                                # Nom traduit par game/tl/<langue>/story/textes.rpy (tools/fiches.py).
                                text __(fiche["nom"]):
                                    substitute False
                                    yalign 0.5
                                    size 30
                                    color ((fiche["couleur"] or gui.accent_color) if actif else gui.idle_color)

            ## Fiche du personnage ouvert.
            for fiche in personnages_fiches:
                if fiche["id"] == personnages_onglet:
                    viewport:
                        xfill True
                        yfill True
                        mousewheel True
                        scrollbars "vertical"

                        vbox:
                            spacing 12

                            hbox:
                                spacing 24
                                fixed:
                                    xysize (96, 96)
                                    if fiche["avatar"] and renpy.has_image(fiche["avatar"]):
                                        add navigation_rond(fiche["avatar"], 96)
                                    else:
                                        add navigation_rond(Solid(fiche["couleur"] or gui.accent_color), 96)
                                text __(fiche["nom"]):
                                    substitute False
                                    yalign 0.5
                                    size gui.label_text_size
                                    color (fiche["couleur"] or gui.accent_color)

                            for champ, titre in (("jauges", None), ("competences", _("Skills")), ("relations", _("Relationships"))):
                                if fiche[champ]:
                                    if titre:
                                        null height 12
                                        text titre size 24 color gui.idle_small_color
                                    for jauge in fiche[champ]:
                                        $ valeur = personnages_valeur(jauge)
                                        $ maximum = jauge["max"]
                                        $ palier = personnages_palier(jauge, valeur)
                                        hbox:
                                            spacing 20
                                            text __(jauge["nom"]) min_width 260 size 26 substitute False yalign 0.5 color (jauge["couleur"] or gui.text_color)
                                            bar:
                                                value StaticValue(valeur - jauge["min"], max(jauge["max"] - jauge["min"], 1))
                                                xsize 300
                                                ysize 24
                                                yalign 0.5
                                            text "[valeur] / [maximum]" size 24 color gui.idle_small_color yalign 0.5
                                            if palier:
                                                text __(palier) size 24 color gui.accent_color substitute False yalign 0.5
