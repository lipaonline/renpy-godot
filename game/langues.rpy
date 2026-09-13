## Langues du jeu (Ren'Py) : lit game/langues.json, produit par tools/fiches.py depuis la
## bible (« langues »), le même fichier que le lecteur Godot. Fichier réservé à Ren'Py
## (hors de game/story/, donc ignoré par Godot).
##
## La langue des fiches est la langue par défaut : ses répliques sont celles du script, son
## interface est traduite dans game/tl/<langue>/ (textes de l'interface Ren'Py, en anglais
## à l'origine). Chaque traduction a ses répliques, noms, choix et titres de galerie dans
## game/tl/<langue>/story/, produits depuis contenu/traductions/<code>.yaml.

init -1 python:
    import builtins
    import json

    def langues_charger():
        source = {"code": "fr", "renpy": "french", "nom": "Français"}
        try:
            with renpy.open_file("langues.json", "utf-8") as fichier:
                donnees = json.load(fichier)
        except Exception as exc:
            print("langues.json illisible ({}) : langue des fiches seule".format(exc))
            return [source]
        if not isinstance(donnees, builtins.dict):
            return [source]
        if isinstance(donnees.get("source"), builtins.dict):
            source = donnees["source"]
        traductions = donnees.get("traductions", [])
        return [source] + [langue for langue in traductions if isinstance(langue, builtins.dict)]

    ## [{code, renpy, nom}] : la langue des fiches d'abord, puis les traductions.
    langues_disponibles = langues_charger()

    ## Premier lancement : la langue du système si le jeu la propose, sinon celle des fiches.
    def langues_depuis_locale(locale, region):
        for langue in langues_disponibles:
            if langue["code"] == locale:
                return langue["renpy"]
        return None

define config.default_language = langues_disponibles[0]["renpy"]
define config.enable_language_autodetect = True
define config.locale_to_language_function = langues_depuis_locale

## Joueur d'une version précédente du jeu, ou langue retirée : langue par défaut. Au premier
## lancement, _apply_default_preferences (init 1500) choisit ensuite la langue du système.
init 999 python:
    if _preferences.language not in [langue["renpy"] for langue in langues_disponibles]:
        _preferences.language = config.default_language
