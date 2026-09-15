## Temps côté Ren'Py : lit game/temps.json (produit par tools/fiches.py depuis la bible,
## « temps »), le même fichier que le lecteur Godot (engine/temps.gd). Fichier réservé à
## Ren'Py (hors de game/story/, donc ignoré par Godot).
##
## Les variables creneau, moment, jour et jour_semaine sont celles du script généré ; le label
## temps_* les font avancer (élément « temps » des fiches). Cet écran affiche pendant la
## partie, en haut à droite, « Jour 2 · mardi · matin » ou, avec un calendrier,
## « mardi 14 septembre 2027 · matin » (les noms sont traduits comme les autres textes).

init python:
    import builtins
    import json

    def temps_charger():
        vide = {"creneaux": [], "jours": False, "semaine": [], "date": False, "mois": []}
        try:
            with renpy.open_file("temps.json", "utf-8") as fichier:
                donnees = json.load(fichier)
        except Exception as exc:
            print("temps.json illisible ({}) : pas d'affichage du temps".format(exc))
            return vide
        # Dans le store Ren'Py, dict et list désignent les versions « révertables » :
        # json renvoie les types Python d'origine, d'où builtins.
        if not isinstance(donnees, builtins.dict) or not isinstance(donnees.get("creneaux"), builtins.list):
            print('temps.json : format attendu {"creneaux": [...], "jours": true, "semaine": [...]}')
            return vide
        return {"creneaux": [str(c) for c in donnees["creneaux"]], "jours": bool(donnees.get("jours")),
                "semaine": [str(j) for j in donnees.get("semaine") or []], "date": bool(donnees.get("date")),
                "mois": [str(m) for m in donnees.get("mois") or []]}

    def temps_texte():
        """« Jour 2 · mardi · matin », ou « mardi 14 septembre 2027 · matin » avec un calendrier."""
        morceaux = []
        if temps_modele["date"] and len(temps_modele["mois"]) == 12:
            mois = min(max(int(getattr(store, "mois", 1)), 1), 12)
            morceaux.append("{} {} {} {}".format(__(str(getattr(store, "jour_semaine", ""))), getattr(store, "jour_mois", 1),
                                                 __(temps_modele["mois"][mois - 1]), getattr(store, "annee", 0)))
        else:
            if temps_modele["jours"]:
                morceaux.append(__("Day") + " " + str(getattr(store, "jour", 1)))
            if temps_modele["semaine"]:
                morceaux.append(__(str(getattr(store, "jour_semaine", ""))))
        morceaux.append(__(str(getattr(store, "moment", ""))))
        return " · ".join(morceaux)

    temps_modele = temps_charger()
    if temps_modele["creneaux"]:
        config.overlay_screens.append("temps_permanent")


screen temps_permanent():
    zorder 5
    if not main_menu and not renpy.get_screen("carte"):
        text temps_texte():
            substitute False
            xalign 0.985
            ypos 18
            size 26
            color "#ffffff"
            outlines [(2, "#000000", 0, 0)]
            at Transform(alpha=0.85)
