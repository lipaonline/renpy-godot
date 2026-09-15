## Navigation Ren'Py : lit game/navigation.json (cartes, lieux placés dessus, règles de présence
## des personnages), le même fichier que le lecteur Godot (engine/navigation.gd). Fichier
## réservé à Ren'Py (hors de game/story/, donc ignoré par Godot).
##
## Le script affiche une carte avec « $ naviguer("ville") » (fiche : carte: ville) :
## 1. le lieu de chaque personnage est recalculé (première règle « presence » vraie) et rangé
##    dans la variable lieu_<personnage>, que les fiches peuvent tester ;
## 2. l'écran « carte » attend que le joueur choisisse un lieu, qui saute à sa scène
##    (le nom « navigation » est pris par le menu principal de Ren'Py, screens.rpy).
## Deux affichages : « carte » (image avec les lieux placés dessus) et « pieces » (rangée
## d'icônes rondes des pièces en bas à gauche, l'avatar de chaque personnage présent posé sur
## l'icône de sa pièce, le nom de la pièce au survol). Le lieu où l'on est est mis en évidence.
## Un lieu peut ouvrir une sous-carte (les pièces d'un bâtiment) sur place ; un bouton ramène
## à la carte parente. Sur chaque lieu, le jeu affiche les personnages qui s'y trouvent (pour
## un bâtiment : ceux de toutes ses pièces). Même comportement que l'interpréteur Godot.

init python:
    import builtins
    import json

    def navigation_charger():
        vide = {"cartes": {}, "personnages": {}, "scenes": {}}
        try:
            with renpy.open_file("navigation.json", "utf-8") as fichier:
                donnees = json.load(fichier)
        except Exception as exc:
            print("navigation.json illisible ({}) : aucune carte".format(exc))
            return vide
        # Dans le store Ren'Py, dict et list désignent les versions « révertables » :
        # json renvoie les types Python d'origine, d'où builtins.
        if not isinstance(donnees, builtins.dict) or not isinstance(donnees.get("cartes"), builtins.dict):
            print('navigation.json : format attendu {"cartes": {...}, "personnages": {...}}')
            return vide
        cartes = {}
        for cid, carte in donnees["cartes"].items():
            ou = "navigation.json, carte « {} »".format(cid)
            if not isinstance(carte, builtins.dict):
                print("{} : objet attendu".format(ou))
                continue
            lieux = []
            for numero, entree in enumerate(carte.get("lieux") or [], 1):
                if not isinstance(entree, builtins.dict):
                    print("{}, lieu {} : objet attendu".format(ou, numero))
                    continue
                label = entree.get("label") or ""
                if label and not renpy.has_label(label):
                    print("{}, lieu {} : label inconnu « {} »".format(ou, numero, label))
                    continue
                lieux.append(navigation_entree(entree, label))
            cartes[cid] = {"titre": carte.get("titre", cid), "affichage": carte.get("affichage") or "carte",
                           "image": carte.get("image") or "", "parent": carte.get("parent") or "", "lieux": lieux}
        # Raccourcis : lieux proposés depuis toutes les cartes (bouton en bas à droite).
        raccourcis = []
        for numero, entree in enumerate(donnees.get("raccourcis") or [], 1):
            if not isinstance(entree, builtins.dict):
                print("navigation.json, raccourci {} : objet attendu".format(numero))
                continue
            label = entree.get("label") or ""
            if label and not renpy.has_label(label):
                print("navigation.json, raccourci {} : label inconnu « {} »".format(numero, label))
                continue
            raccourcis.append(navigation_entree(entree, label))
        personnages = {}
        for pid, perso in (donnees.get("personnages") or {}).items():
            if not isinstance(perso, builtins.dict):
                continue
            personnages[pid] = {
                "nom": perso.get("nom", pid), "couleur": perso.get("couleur") or "", "avatar": perso.get("avatar") or "",
                "variable": perso.get("variable", "lieu_" + pid),
                "presence": [{"lieu": r.get("lieu", ""), "si": r.get("si") or ""}
                             for r in perso.get("presence") or [] if isinstance(r, builtins.dict)],
            }
        scenes = {label: lieu for label, lieu in (donnees.get("scenes") or {}).items() if renpy.has_label(label)}
        return {"cartes": cartes, "raccourcis": raccourcis, "personnages": personnages, "scenes": scenes}

    def navigation_entree(entree, label):
        """Un lieu d'une carte ; « temps » : coût du déplacement ({creneaux: n} ou {jours: n}), payé
        quand le joueur clique le lieu, avant sa scène ou l'ouverture de sa sous-carte."""
        cout = entree.get("temps")
        return {
            "lieu": entree.get("lieu", ""), "nom": entree.get("nom", entree.get("lieu", "")),
            "icone": entree.get("icone") or "",
            "x": float(entree.get("x", 50)) / 100.0, "y": float(entree.get("y", 50)) / 100.0,
            "label": label, "carte": entree.get("carte") or "", "si": entree.get("si") or "",
            "temps": cout if isinstance(cout, builtins.dict) else None,
            "raccourci": bool(entree.get("raccourci")),
        }

    navigation_donnees = navigation_charger()
    navigation_cartes = navigation_donnees["cartes"]

    def navigation_vrai(condition):
        """Condition du sous-ensemble (chaîne vide : toujours vraie), évaluée dans le store."""
        return not condition or bool(renpy.python.py_eval(condition))

    def navigation_presences():
        """Range le lieu de chaque personnage dans sa variable (lieu_<personnage>), pour les fiches."""
        for perso in navigation_donnees["personnages"].values():
            setattr(store, perso["variable"], navigation_lieu_de(perso))

    def navigation_lieux_de(cid, vus=None):
        """Identifiants des lieux d'une carte et de ses sous-cartes."""
        vus = vus if vus is not None else set()
        resultat = set()
        if cid in vus or cid not in navigation_cartes:
            return resultat
        vus.add(cid)
        for entree in navigation_cartes[cid]["lieux"]:
            resultat.add(entree["lieu"])
            if entree["carte"]:
                resultat |= navigation_lieux_de(entree["carte"], vus)
        return resultat

    def navigation_lieu_de(perso):
        """Lieu d'un personnage d'après ses règles « presence » : la première vraie, sinon aucun."""
        for regle in perso["presence"]:
            if navigation_vrai(regle["si"]):
                return regle["lieu"]
        return ""

    def navigation_presents(entree):
        """Personnages présents sur un lieu de la carte, d'après leurs règles évaluées maintenant :
        [{nom traduit, couleur, avatar}] ; l'avatar est vide s'il n'est pas déclaré ou si l'image
        manque. Un lieu qui ouvre une sous-carte montre les personnages de toutes ses pièces."""
        lieux = {entree["lieu"]}
        if entree["carte"]:
            lieux |= navigation_lieux_de(entree["carte"])
        resultat = []
        for perso in navigation_donnees["personnages"].values():
            if navigation_lieu_de(perso) in lieux:
                avatar = perso["avatar"] if perso["avatar"] and renpy.has_image(perso["avatar"]) else ""
                resultat.append({"nom": __(perso["nom"]), "couleur": perso["couleur"], "avatar": avatar})
        return resultat

    def navigation_raccourcis(cid):
        """Raccourcis à proposer sur une carte : ceux dont le lieu n'y figure pas déjà, si visibles."""
        ici = {entree["lieu"] for entree in navigation_cartes[cid]["lieux"]}
        return [entree for entree in navigation_donnees["raccourcis"]
                if entree["lieu"] not in ici and navigation_vrai(entree["si"])]

    def navigation_chemin(cid):
        """Cartes parentes, de la racine à la carte parente directe (fil d'Ariane)."""
        chemin, vus = [], {cid}
        parent = navigation_cartes[cid]["parent"]
        while parent in navigation_cartes and parent not in vus:
            vus.add(parent)
            chemin.insert(0, parent)
            parent = navigation_cartes[parent]["parent"]
        return chemin

    def navigation_cout(cout):
        """Paie un déplacement : n créneaux (label temps_avancer) ou n jours (temps_sauter_jours)."""
        if not cout:
            return
        if cout.get("jours"):
            store.temps_saut = int(cout["jours"])
            renpy.call_in_new_context("temps_sauter_jours")
        for _ in range(int(cout.get("creneaux") or 0)):
            renpy.call_in_new_context("temps_avancer")

    def navigation_cibles(cid):
        """Labels accessibles depuis une carte : lieux visibles de la carte, de ses sous-cartes
        et de ses cartes parentes, et les raccourcis."""
        file, vus, resultat = [cid], {cid}, []
        for entree in navigation_raccourcis(cid):
            if entree["label"]:
                resultat.append(entree["label"])
            elif entree["carte"] in navigation_cartes and entree["carte"] not in vus:
                vus.add(entree["carte"])
                file.append(entree["carte"])
        while file:
            courante = file.pop(0)
            carte = navigation_cartes[courante]
            for entree in carte["lieux"]:
                if not navigation_vrai(entree["si"]):
                    continue
                if entree["label"]:
                    resultat.append(entree["label"])
                elif entree["carte"] in navigation_cartes and entree["carte"] not in vus:
                    vus.add(entree["carte"])
                    file.append(entree["carte"])
            if carte["parent"] in navigation_cartes and carte["parent"] not in vus:
                vus.add(carte["parent"])
                file.append(carte["parent"])
        return resultat

    def navigation_rond(quoi, taille):
        """Image recadrée en rond (icône de pièce, avatar), comme les icônes du lecteur Godot."""
        masque = Transform("gui/navigation_rond.png", xysize=(taille, taille))
        return AlphaMask(Transform(quoi, fit="cover", xysize=(taille, taille)), masque)

    def navigation_action(entree):
        """Action d'un lieu : payer le déplacement s'il coûte du temps, puis jouer sa scène ou
        ouvrir sa sous-carte sur place."""
        action = Jump(entree["label"]) if entree["label"] else SetScreenVariable("courante", entree["carte"])
        if entree["temps"]:
            return [Function(navigation_cout, entree["temps"]), action]
        return action

    def navigation_batiment(label):
        """Rangée des pièces à garder affichée pendant une scène : (carte, lieu) si le lieu de la
        scène appartient à une carte « pieces », sinon None."""
        lieu = navigation_donnees["scenes"].get(label, "")
        for cid, carte in navigation_cartes.items():
            if carte["affichage"] == "pieces" and any(entree["lieu"] == lieu for entree in carte["lieux"]):
                return (cid, lieu)
        return None

    def navigation_label(name, abnormal):
        """À l'entrée de chaque scène : note où l'on est (variable sauvegardée, donc retrouvée au
        chargement) ; les scènes appelées sans lieu (souvenirs, interludes) ne changent rien."""
        if name in navigation_donnees["scenes"]:
            store.navigation_scene = name

    config.label_callback = navigation_label

    def naviguer(cid, ici=""):
        """Instruction du sous-ensemble « $ naviguer("carte", "lieu") » (tools/fiches.py, fin de
        scène carte:). ici : lieu où l'on est, mis en évidence sur la carte (facultatif)."""
        if cid not in navigation_cartes:
            raise Exception("carte inconnue « {} » (game/navigation.json)".format(cid))
        navigation_presences()
        if not navigation_cibles(cid):
            # Aucun lieu accessible : on continue, comme un menu sans choix (verifier le signale).
            return
        # La boîte de dialogue se cache, comme devant un « call screen » du script (et comme Godot).
        _window_hide()
        renpy.call_screen("carte", cid, ici)


## Scène en cours (label), pour la rangée permanente des pièces.
default navigation_scene = ""

## Rangée des pièces affichée pendant toute scène jouée dans une pièce d'un bâtiment (écran
## permanent, sans clic : les clics font avancer le texte), au-dessus de la boîte de dialogue.
## Elle s'efface quand l'écran « carte » prend le relais.
screen pieces_permanentes():
    zorder 5
    $ batiment = navigation_batiment(navigation_scene) if not renpy.get_screen("carte") and not main_menu else None
    if batiment:
        $ cid, ici = batiment
        hbox:
            xpos 50
            yanchor 1.0
            ypos 790
            spacing 22
            at Transform(alpha=0.75)
            for entree in navigation_cartes[cid]["lieux"]:
                if navigation_vrai(entree["si"]):
                    fixed:
                        xysize (118, 118)
                        use carte_icone(entree["icone"], entree["lieu"] == ici, navigation_presents(entree))
            if navigation_cartes[cid]["parent"]:
                fixed:
                    xysize (118, 118)
                    use carte_icone(navigation_cartes[navigation_cartes[cid]["parent"]]["image"], False, [])
                    text "←" align (0.5, 0.5) size 44 color "#ffffff" outlines [(2, "#000000", 0, 0)]

init python:
    config.overlay_screens.append("pieces_permanentes")


## Carte : selon l'affichage, image de fond, titre et un bouton par lieu placé sur l'image
## (personnages présents dessous), ou la rangée d'icônes rondes des pièces en bas à gauche
## (avatars posés sur l'icône, nom au survol, icône de la carte parente pour sortir). Le lieu
## « ici » est mis en évidence. Même disposition que engine/ui/map_screen.gd.
screen carte(carte, ici=""):

    ## Carte affichée : une sous-carte s'ouvre sur place. Variable d'écran, donc remise à la
    ## carte demandée au chargement d'une sauvegarde, comme dans Godot.
    default courante = carte

    $ donnees = navigation_cartes[courante]
    $ parent = donnees["parent"]
    $ image_carte = donnees["image"]
    $ pieces = donnees["affichage"] == "pieces"

    if image_carte and renpy.has_image(image_carte):
        add Transform(image_carte, fit="cover", xysize=(config.screen_width, config.screen_height))
    elif not pieces:
        ## La rangée des pièces sans image de carte laisse voir la scène en cours.
        add Solid("#0d0d12")
        if image_carte:
            text "[[ image manquante : [image_carte] ]" align (0.5, 0.5) size 30 color "#ffffff73"

    if pieces:
        hbox:
            xpos 50
            yanchor 1.0
            ypos 1030
            spacing 22
            for entree in donnees["lieux"]:
                if navigation_vrai(entree["si"]):
                    ## « alt » : le nom de la pièce, que les tests Ren'Py cliquent par ce texte.
                    button:
                        style "navigation_rond"
                        xysize (118, 118)
                        alt __(entree["nom"])
                        tooltip __(entree["nom"])
                        action navigation_action(entree)
                        use carte_icone(entree["icone"], entree["lieu"] == ici, navigation_presents(entree))
            if parent:
                button:
                    style "navigation_rond"
                    xysize (118, 118)
                    alt ("← " + __(navigation_cartes[parent]["titre"]))
                    tooltip ("← " + __(navigation_cartes[parent]["titre"]))
                    action SetScreenVariable("courante", parent)
                    use carte_icone(navigation_cartes[parent]["image"], False, [])
                    text "←" align (0.5, 0.5) size 44 color "#ffffff" outlines [(2, "#000000", 0, 0)]
        ## Nom de la pièce survolée.
        $ survol = GetTooltip()
        if survol:
            text survol:
                substitute False
                xpos 50
                yanchor 1.0
                ypos 900
                size 28
                color "#ffffff"
                outlines [(2, "#000000", 0, 0)]
    else:
        text __(donnees["titre"]):
            substitute False
            pos (75, 40)
            size gui.name_text_size
            color gui.accent_color

        if parent:
            textbutton "← " + __(navigation_cartes[parent]["titre"]):
                pos (60, 990)
                action SetScreenVariable("courante", parent)

        for entree in donnees["lieux"]:
            if navigation_vrai(entree["si"]):
                vbox:
                    pos (entree["x"], entree["y"])
                    anchor (0.5, 0.5)
                    spacing 6
                    ## Le bouton ne contient que le nom : les tests Ren'Py le cliquent par son texte.
                    textbutton __(entree["nom"]):
                        xalign 0.5
                        style ("navigation_lieu_ici" if entree["lieu"] == ici else "navigation_lieu")
                        action navigation_action(entree)
                    hbox:
                        xalign 0.5
                        spacing 4
                        for perso in navigation_presents(entree):
                            use carte_present(perso)

    ## Fil d'Ariane : les cartes parentes, cliquables pour remonter de plusieurs niveaux.
    $ chemin = navigation_chemin(courante)
    if chemin:
        hbox:
            pos ((75, 110) if not pieces else (50, 40))
            spacing 8
            for ancetre in chemin:
                textbutton __(navigation_cartes[ancetre]["titre"]):
                    style "navigation_ariane"
                    action SetScreenVariable("courante", ancetre)
                text "›" size 24 color "#ffffff99" yalign 0.5
            text __(donnees["titre"]) substitute False size 24 color "#ffffff" yalign 0.5

    ## Raccourcis : lieux proposés depuis toutes les cartes, en bas à droite.
    vbox:
        xanchor 1.0
        xpos 1860
        yanchor 1.0
        ypos 990
        spacing 8
        for entree in navigation_raccourcis(courante):
            textbutton __(entree["nom"]):
                xalign 1.0
                style "navigation_lieu"
                action navigation_action(entree)

## Icône ronde d'une pièce (112 px, anneau blanc, violet pour la pièce où l'on est), avec les
## avatars des personnages présents posés en bas.
screen carte_icone(icone, ici, presents):
    fixed:
        xysize (118, 118)
        add navigation_rond(Solid(gui.accent_color if ici else "#ffffff"), 118)
        if icone and renpy.has_image(icone):
            add navigation_rond(icone, 108) pos (5, 5)
        else:
            add navigation_rond(Solid("#3a3550"), 108) pos (5, 5)
        hbox:
            xalign 0.5
            yalign 1.0
            spacing 2
            for perso in presents:
                if perso["avatar"]:
                    add navigation_rond(perso["avatar"], 44)
                else:
                    add navigation_rond(Solid(perso["couleur"] or gui.accent_color), 44)


## Un personnage présent sur une carte : son avatar, sinon son nom dans sa couleur.
screen carte_present(perso):
    if perso["avatar"]:
        add navigation_rond(perso["avatar"], 64)
    else:
        frame:
            style "navigation_presence"
            text ("● " + perso["nom"]) substitute False size 22 color (perso["couleur"] or gui.accent_color)


## Mêmes couleurs et marges que engine/ui/map_screen.gd : lisible sur toute carte.
## Les styles « _ici » signalent le lieu où l'on est.
style navigation_lieu is button:
    background "#000000b3"
    hover_background "#4d3373e6"
    padding (28, 12, 28, 12)

style navigation_lieu_text is button_text:
    size 30
    xalign 0.5
    idle_color "#dddddd"
    hover_color "#ffffff"

style navigation_lieu_ici is navigation_lieu:
    background "#4d3373b3"

style navigation_lieu_ici_text is navigation_lieu_text:
    idle_color gui.accent_color

style navigation_ariane is button:
    padding (6, 2, 6, 2)

style navigation_ariane_text is button_text:
    size 24
    color "#ffffffb3"
    hover_color "#ffffff"

style navigation_rond is button:
    background None
    padding (0, 0, 0, 0)

style navigation_presence is empty:
    background "#00000099"
    padding (10, 4, 10, 4)
