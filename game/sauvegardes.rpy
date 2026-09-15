## Anciennes sauvegardes côté Ren'Py : lit game/renommages.json (produit par tools/fiches.py
## depuis la bible, « renommages »), le même fichier que le lecteur Godot (engine/renommages.gd).
## Fichier réservé à Ren'Py (hors de game/story/, donc ignoré par Godot).
##
## - scenes : un label renommé est redirigé par config.label_overrides, ce qui couvre la position
##   sauvegardée, la pile des « call » et les jump du script ;
## - variables : après chaque chargement, la valeur restée sous l'ancien nom passe sous le
##   nouveau, puis l'ancien nom est retiré (renommages en chaîne possibles, dans l'ordre déclaré).

init python:
    import builtins
    import json

    def renommages_charger():
        vide = {"variables": [], "scenes": []}
        try:
            with renpy.open_file("renommages.json", "utf-8") as fichier:
                donnees = json.load(fichier)
        except Exception as exc:
            print("renommages.json illisible ({}) : aucun renommage".format(exc))
            return vide
        # Dans le store Ren'Py, dict et list désignent les versions « révertables » :
        # json renvoie les types Python d'origine, d'où builtins.
        if not isinstance(donnees, builtins.dict):
            print('renommages.json : format attendu {"variables": [...], "scenes": [...]}')
            return vide
        resultat = {}
        for champ in ("variables", "scenes"):
            resultat[champ] = []
            for numero, entree in enumerate(donnees.get(champ) or [], 1):
                if not isinstance(entree, builtins.dict) or not entree.get("ancien") or not entree.get("nouveau"):
                    print("renommages.json, {} {} : objet {{ ancien, nouveau }} attendu".format(champ, numero))
                    continue
                resultat[champ].append((entree["ancien"], entree["nouveau"]))
        return resultat

    def renommages_appliquer():
        for ancien, nouveau in renommages["variables"]:
            if hasattr(store, ancien):
                setattr(store, nouveau, getattr(store, ancien))
                delattr(store, ancien)

    renommages = renommages_charger()
    for ancien, nouveau in renommages["scenes"]:
        config.label_overrides[ancien] = nouveau
    config.after_load_callbacks.append(renommages_appliquer)
