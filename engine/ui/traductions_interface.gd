## Traductions de l'interface du lecteur Godot. Les textes de l'interface sont écrits en
## français dans le code ; chaque langue a ici son dictionnaire (texte français →
## traduction). Les nœuds Godot traduisent seuls leur texte (traduction automatique) ;
## les textes composés passent par tr(). Une langue sans dictionnaire affiche l'interface
## en anglais, langue de repli de Godot.
extends RefCounted

const TEXTS := {
	"en": {
		# Menus
		"Nouvelle partie": "Start",
		"Charger": "Load",
		"Galerie": "Gallery",
		"Préférences": "Preferences",
		"Quitter": "Quit",
		"Historique": "History",
		"Sauvegarder": "Save",
		"Menu principal": "Main Menu",
		"Retour": "Return",
		"Oui": "Yes",
		"Non": "No",
		"Revenir au menu principal ?\nLa progression non sauvegardée sera perdue.":
			"Return to the main menu?\nUnsaved progress will be lost.",
		"Quitter le jeu ?": "Quit the game?",
		"Remplacer cette sauvegarde ?": "Overwrite this save?",
		"Charger cette partie ?\nLa progression non sauvegardée sera perdue.":
			"Load this game?\nUnsaved progress will be lost.",
		# Pages
		"L'historique est vide.": "The history is empty.",
		"Sauvegarde rapide": "Quick save",
		"Emplacement %s": "Slot %s",
		"%s — vide": "%s — empty",
		"Aucune entrée dans game/galerie.json.": "No entries in game/galerie.json.",
		"Verrouillé": "Locked",
		"Vidéo introuvable : %s": "Video not found: %s",
		"[ image manquante : %s ]": "[ missing image: %s ]",
		# Préférences
		"Vitesse du texte : %s": "Text speed: %s",
		"instantané": "instant",
		"%d car./s": "%d char./s",
		"Avance automatique : %s s": "Auto-forward time: %s s",
		"Avance rapide": "Skip",
		"Passer aussi le texte non lu": "Skip unseen text too",
		"Affichage": "Display",
		"Plein écran": "Fullscreen",
		"Musique : %d %%": "Music: %d%%",
		"Sons : %d %%": "Sound: %d%%",
		"Langue": "Language",
		# Partie
		"Avance rapide  »": "Skip  »",
		"Avance rapide arrêtée : texte pas encore lu": "Skip stopped: unseen text",
		"Vidéo : %s\n\nLa version Godot attend « %s » (Ogg Theora).\nCliquez pour continuer.":
			"Video: %s\n\nThe Godot version expects “%s” (Ogg Theora).\nClick to continue.",
		"Impossible de sauvegarder maintenant": "Cannot save right now",
		"Échec de la sauvegarde": "Save failed",
		"Sauvegarde rapide effectuée": "Quick save done",
		"Partie sauvegardée": "Game saved",
		"Aucune sauvegarde rapide": "No quick save",
		"Sauvegarde illisible ou incompatible avec le script actuel": "Save unreadable or incompatible with the current script",
		"Partie chargée": "Game loaded",
	},
}
## Menu rapide : textes courts, traduits dans le contexte « menu rapide » (en anglais,
## « Retour » y devient « Back » et non « Return », comme dans Ren'Py).
const QUICK_MENU_CONTEXT := "menu rapide"
const QUICK_MENU_TEXTS := {
	"en": {
		"Retour": "Back", "Historique": "History", "Passer": "Skip", "Auto": "Auto", "Sauvegarder": "Save",
		"Sauv. rapide": "Q.Save", "Charg. rapide": "Q.Load", "Préférences": "Prefs",
	},
}

static var _installed := false


## Texte traduit dans la langue de l'interface, pour les textes composés (« %s »).
static func t(text: String, context := "") -> String:
	return String(TranslationServer.translate(text, context))


## Choisit la langue de l'interface (code de langue : fr, en…).
static func set_language(code: String) -> void:
	if not _installed:
		_installed = true
		# Le français est la langue du code : cette traduction à l'identique évite que Godot
		# prenne sa langue de repli (l'anglais) quand le jeu est en français.
		var identity := Translation.new()
		identity.locale = "fr"
		for text in TEXTS.en:
			identity.add_message(text, text)
		for text in QUICK_MENU_TEXTS.en:
			identity.add_message(text, text, QUICK_MENU_CONTEXT)
		TranslationServer.add_translation(identity)
		for language in TEXTS:
			var translation := Translation.new()
			translation.locale = language
			for text in TEXTS[language]:
				translation.add_message(text, TEXTS[language][text])
			for text in QUICK_MENU_TEXTS.get(language, {}):
				translation.add_message(text, QUICK_MENU_TEXTS[language][text], QUICK_MENU_CONTEXT)
			TranslationServer.add_translation(translation)
	TranslationServer.set_locale(code)
