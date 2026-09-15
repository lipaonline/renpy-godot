## Tests headless du compilateur, de l'interpréteur et des données de jeu.
##   godot --headless --path . --script res://tests/run_tests.gd
##
## Les tests du moteur utilisent la démo figée de tests/fixtures/demo ; ceux du jeu
## (game/story) sont génériques, et les routes attendues sont produites par
## tools/fiches.py à partir des fiches.
extends SceneTree

const Parser = preload("res://engine/rpy_parser.gd")
const Interpreter = preload("res://engine/rpy_interpreter.gd")
const RouteExplorer = preload("res://engine/route_explorer.gd")
const PersistentData = preload("res://engine/persistent_data.gd")
const SaveSlots = preload("res://engine/save_slots.gd")
const Gallery = preload("res://engine/gallery.gd")
const Characters = preload("res://engine/characters.gd")
const Renames = preload("res://engine/renommages.gd")
const Temps = preload("res://engine/temps.gd")
const Assets = preload("res://engine/assets.gd")
const Langues = preload("res://engine/langues.gd")
const Navigation = preload("res://engine/navigation.gd")
const InterfaceTexts = preload("res://engine/ui/traductions_interface.gd")

const DEMO_DIR := "res://tests/fixtures/demo/game"
const DEMO_STORY := "res://tests/fixtures/demo/game/story"
const GAME_STORY := "res://game/story"
const GAME_NAVIGATION := "res://game/navigation.json"
const ROUTES_PATH := "res://tests/routes_attendues.json"
const BLOCKING_EVENTS := ["say", "menu", "navigate", "movie", "pause", "end", "error"]

var _passed := 0
var _failed := 0


func _init() -> void:
	print("Démo figée : routes")
	test_demo_routes()
	print("Expressions et interpolation")
	test_expressions()
	print("Contrôle de flux")
	test_control_flow()
	print("Erreurs hors sous-ensemble")
	test_errors()
	print("Sauvegarde")
	test_save_load()
	print("Historique et retour arrière")
	test_history_rollback()
	test_saved_history()
	print("Labels atteints et texte déjà lu")
	test_labels_and_ids()
	print("Données persistantes et emplacements")
	test_persistent_and_slots()
	print("Explorateur de routes (démo)")
	test_route_explorer()
	print("Navigation : cartes et présence")
	test_navigation()
	test_navigation_errors()
	print("Traductions")
	test_translation_parser()
	test_translation_runtime()
	test_demo_translation()
	test_interface_texts()
	print("Jeu (game/story)")
	test_game_story()
	print("Routes attendues (tools/fiches.py)")
	test_expected_routes()
	print("Galerie du jeu")
	test_gallery()
	print("Fiches des personnages")
	test_characters()
	print("Renommages et anciennes sauvegardes")
	test_renames()
	print("Temps : créneaux et jours")
	test_time()
	print("\n%d réussi(s), %d échec(s)" % [_passed, _failed])
	quit(1 if _failed > 0 else 0)


func test_demo_routes() -> void:
	var story := demo_story()
	check(not story.is_empty(), "la démo compile sans erreur")
	if story.is_empty():
		return

	var confiance := play(story, ["Regarder la boîte aux lettres", "Lui faire confiance"])
	check(confiance.store.relation_lena == 5, "confiance : relation_lena = 5")
	check("[movie videos/lena_scene_01.webm]" in confiance.lines, "confiance : la vidéo est lancée")
	check("Léna m'a fait confiance ce soir." in confiance.lines, "confiance : bonne conclusion")
	check(confiance.lines.back() == "[end]", "confiance : la partie se termine")

	var enquete := play(story, ["Regarder la boîte aux lettres", "L'interroger sur la photo"])
	check(enquete.store.mystere == 2, "interrogatoire : mystere = 2")
	check("Un souvenir remonte : l'odeur du plâtre, et la voix de mon père sur le chantier." in enquete.lines,
		"interrogatoire : call souvenir puis retour")
	check("Je repars avec plus de questions que de réponses." in enquete.lines, "interrogatoire : branche elif")

	var direct := play(story, ["Monter directement", "Repartir sous la pluie"])
	check(direct.menus.size() == 2 and "L'interroger sur la photo" not in direct.menus[1],
		"choix conditionnel masqué sans l'indice")
	check(direct.store.relation_lena == 2, "départ : relation_lena = 2")
	check("Je redescends l'escalier. La porte se referme derrière moi." in direct.lines, "départ : fin solitaire")
	check("Fin du prototype" not in "".join(PackedStringArray(direct.lines)), "départ : chapitre suivant non joué")


func test_expressions() -> void:
	var compiled := compile("""
default a = 3
default ok = True
default nom = "Alex"
default vide = None
label start:
    if a >= 3 and ok and not (nom == 'Bob') and vide == None:
        "oui [nom] [a] [ok] [vide] [[crochets]"
    else:
        "non"
    $ a += 2
    $ a -= 1
    $ a *= 3
    $ nom = nom + "!"
    "a=[a] nom=[nom] max=[a]"
    return
""")
	check(compiled[0] != null, "compile : %s" % ", ".join(compiled[1]))
	if compiled[0] == null:
		return
	var result := play(compiled[0], [])
	check("oui Alex 3 True None [crochets]" in result.lines, "condition and/not/None et interpolation")
	check("a=12 nom=Alex! max=12" in result.lines, "+=, -=, *= et concaténation")
	check(typeof(result.store.a) == TYPE_INT, "les entiers restent des entiers")


func test_control_flow() -> void:
	var compiled := compile("""
default i = 0
default total = 0
label start:
    while i < 3:
        $ i += 1
        $ total += i
    call bonus
    "total=[total]"
    menu:
        "Caché" if False:
            "jamais"
    "après le menu"
    return
label bonus:
    $ total += 100
    return
""")
	check(compiled[0] != null, "compile : %s" % ", ".join(compiled[1]))
	if compiled[0] == null:
		return
	var result := play(compiled[0], [])
	check(result.lines == ["total=106", "après le menu", "[end]"], "while, call/return et menu sans choix visible : %s" % [result.lines])


func test_errors() -> void:
	var compiled := compile("""
init python:
    x = 1
define lena = Character("Léna", couleur="#fff")
default n = 0
label start:
    show lena at zoomed
    $ import os
    jump nulle_part
    inconnu "Bonjour"
    if n = 1:
        "x"
    $ n = n / 2
    "valeur [m]"
    screen truc
    return
""")
	var errors: PackedStringArray = compiled[1]
	check(compiled[0] == null, "le script invalide est refusé")
	var expected := [
		[2, "« init » ne fait pas partie du sous-ensemble"],
		[4, "argument de Character() non supporté : couleur"],
		[7, "position non supportée : zoomed"],
		[8, "Python non supporté"],
		[9, "label inconnu : « nulle_part »"],
		[10, "personnage inconnu : « inconnu »"],
		[11, "expression invalide « n = 1 »"],
		[13, "opérateur « / » non supporté"],
		[14, "variable inconnue dans le texte : [m]"],
		[15, "« screen » ne fait pas partie du sous-ensemble"],
	]
	for item in expected:
		var prefix := "test.rpy:%d: " % item[0]
		var found := false
		for error in errors:
			if error.begins_with(prefix) and item[1] in error:
				found = true
		check(found, "ligne %d : %s" % item)
	check(errors.size() == expected.size(), "aucune erreur en trop (%d attendues) :\n    %s" % [expected.size(), "\n    ".join(errors)])


func test_save_load() -> void:
	var story := demo_story()
	if story.is_empty():
		return
	var interp := Interpreter.new(story)
	interp.start()
	var event := {}
	var menus := 0
	while true:
		event = interp.next()
		if event.type == "menu":
			menus += 1
			if menus == 2:
				break
			interp.choose(choice_index(event, "Regarder la boîte aux lettres"))
		elif event.type == "end" or event.type == "error":
			break
	check(menus == 2, "arrivée au second menu")
	var saved := var_to_str(interp.get_state())
	var relation_before = interp.store.relation_lena

	interp.choose(choice_index(event, "Lui faire confiance"))
	while interp.next().type not in ["end", "error"]:
		pass
	check(interp.store.relation_lena == 5, "la partie continue après la sauvegarde")

	var loaded := Interpreter.new(story)
	check(loaded.set_state(str_to_var(saved)), "chargement accepté")
	var again := loaded.next()
	check(again.type == "menu" and again.choices.size() == 3, "le menu est reproposé après chargement")
	check(again.prompt != null and again.prompt.name == "Léna", "la réplique du menu est rejouée")
	check(loaded.store.relation_lena == relation_before, "les variables sont restaurées")
	check(typeof(loaded.store.relation_lena) == TYPE_INT, "les types sont conservés (var_to_str)")
	check(loaded.stage.scene == "appartement_soir" and loaded.stage.shown.has("lena"), "la scène est restaurée")


func test_history_rollback() -> void:
	var story := demo_story()
	if story.is_empty():
		return
	var interp := Interpreter.new(story)
	interp.start()
	check(not interp.can_rollback(), "pas de retour arrière avant la première réplique")
	var first := next_blocking(interp)
	var second := next_blocking(interp)
	var menu := next_blocking(interp)
	check(first.type == "say" and second.type == "say" and menu.type == "menu", "trois premières interactions")
	check(interp.history.size() == 2 and interp.history[1].text == second.text, "historique : deux répliques")
	interp.choose(choice_index(menu, "Monter directement"))
	next_blocking(interp)
	check(interp.store.relation_lena == 4 and interp.stage.scene == "appartement_soir", "après le choix : variable et décor modifiés")

	check(interp.rollback(), "retour arrière accepté")
	var again := interp.next()
	check(again.type == "menu" and again.choices.size() == 2, "retour arrière : le menu est reproposé")
	check(interp.store.relation_lena == 3 and interp.stage.scene == "rue_nuit", "retour arrière : variable et décor restaurés")
	check(interp.history.size() == 2, "retour arrière : historique tronqué")

	check(interp.rollback(), "second retour arrière")
	var back := interp.next()
	check(back.type == "say" and back.text == second.text, "retour sur la réplique précédente")
	check(interp.history.size() == 2 and interp.history.back().text == second.text, "pas de doublon dans l'historique")

	interp.rollback()
	interp.next()
	check(not interp.can_rollback() and interp.history.size() == 1, "retour jusqu'à la première réplique, pas au-delà")

	var ending := Interpreter.new(story)
	ending.start()
	drive(ending, ["Monter directement", "Repartir sous la pluie"])
	check(ending.rollback() and ending.next().text == "Je redescends l'escalier. La porte se referme derrière moi.",
		"retour arrière depuis la fin de partie")


func test_saved_history() -> void:
	var story := demo_story()
	if story.is_empty():
		return
	var interp := Interpreter.new(story)
	interp.start()
	next_blocking(interp)
	var current := next_blocking(interp)
	var state: Dictionary = str_to_var(var_to_str(interp.get_state()))
	check(state.history.size() == 1, "la sauvegarde exclut la réplique en cours")
	var loaded := Interpreter.new(story)
	loaded.set_state(state)
	var replay := next_blocking(loaded)
	check(replay.text == current.text and loaded.history.size() == 2, "après chargement : réplique rejouée, historique sans doublon")


func test_labels_and_ids() -> void:
	var story := demo_story()
	if story.is_empty():
		return
	var reached: Array = []
	var interp := Interpreter.new(story)
	interp.label_entered.connect(func(label_name: String) -> void: reached.append(label_name))
	interp.start()
	drive(interp, ["Monter directement", "Repartir sous la pluie"])
	check(reached == ["start", "ch01_sc01", "ch01_sc02", "ch01_sc05"], "labels atteints signalés : %s" % [reached])

	var one := Interpreter.new(story)
	one.start()
	var other := Interpreter.new(demo_story())
	other.start()
	var a := next_blocking(one)
	var b := next_blocking(other)
	var c := next_blocking(one)
	check(a.id != "" and a.id == b.id, "identifiant de réplique stable entre deux compilations")
	check(a.id != c.id, "deux répliques différentes ont des identifiants différents")


func test_persistent_and_slots() -> void:
	var path := "user://test_persistent.txt"
	var data := PersistentData.new(path)
	data.mark_line("ligne")
	data.mark_label("start")
	data.set_preference("text_cps", 42.0)
	data.save_data()
	var reloaded := PersistentData.new(path)
	reloaded.load_data()
	check(reloaded.is_line_seen("ligne") and reloaded.is_label_seen("start"), "persistant : texte lu et labels relus")
	check(reloaded.preferences.text_cps == 42.0 and reloaded.preferences.skip_unseen == false,
		"persistant : préférences relues, valeurs par défaut conservées")
	DirAccess.remove_absolute(path)

	var story := demo_story()
	if story.is_empty():
		return
	var interp := Interpreter.new(story)
	interp.start()
	next_blocking(interp)
	var screenshot := Image.create_empty(1920, 1080, false, Image.FORMAT_RGB8)
	screenshot.fill(Color.DARK_SLATE_BLUE)
	check(SaveSlots.write("test-1", interp.get_state(), "Il pleut…", screenshot), "emplacement écrit")
	var saved := SaveSlots.read("test-1")
	check(saved.get("description") == "Il pleut…" and saved.state.resume == interp.get_state().resume, "emplacement relu")
	var picture := SaveSlots.thumbnail("test-1")
	check(picture != null and picture.get_size() == Vector2(384, 216), "vignette réduite à 384 × 216")
	SaveSlots.delete("test-1")
	check(not SaveSlots.exists("test-1") and SaveSlots.read("test-1").is_empty(), "emplacement supprimé")


func test_route_explorer() -> void:
	var story := demo_story()
	if story.is_empty():
		return
	var report := RouteExplorer.new().explore(story)
	check(report.complete, "exploration complète (%d états)" % report.states)
	check(report.errors.is_empty(), "aucune erreur d'exécution : %s" % [report.errors])
	check(report.unreached_labels.is_empty(), "tous les labels sont atteignables : %s" % [report.unreached_labels])
	check(report.never_offered.is_empty(), "tous les choix sont proposés au moins une fois : %s" % [report.never_offered])
	check(report.endings.has("ch01_sc04") and report.endings.has("ch01_sc05"), "deux fins atteintes : %s" % [report.endings])


## Petit jeu à cartes : une ville (café, immeuble) et les pièces de l'immeuble (salon, cuisine).
## Léna est dans la cuisine le matin, au café ensuite ; le salon n'est ouvert que le matin,
## le café avant le soir (heure 2), et la cuisine termine la partie dès midi.
const NAVIGATION_STORY := """
define lena = Character(_("Léna"), color="#c8a2ff")
default heure = 0
default lieu_lena = ""
label start:
    "Bonjour." id nav_a
    jump ville
label ville:
    $ naviguer("ville", "rue")
label cafe:
    if lieu_lena == "cafe":
        lena "Un café ?" id nav_b
    $ heure += 1
    jump ville
label salon:
    "Le salon." id nav_c
    $ heure += 1
    jump ville
label cuisine:
    if heure >= 1:
        "Fin." id nav_d
        return
    "La cuisine." id nav_e
    $ heure += 1
    jump ville
"""
const NAVIGATION_DATA := {
	"cartes": {
		"ville": {"titre": "La ville", "image": "carte_ville", "lieux": [
			{"lieu": "immeuble", "nom": "L'immeuble", "x": 50, "y": 40, "carte": "immeuble"},
			{"lieu": "cafe", "nom": "Le café", "x": 80, "y": 70, "label": "cafe", "si": "heure < 2"},
		]},
		"immeuble": {"titre": "L'immeuble", "affichage": "pieces", "parent": "ville", "lieux": [
			{"lieu": "salon", "nom": "Le salon", "icone": "icone_salon", "label": "salon", "si": "heure == 0"},
			{"lieu": "cuisine", "nom": "La cuisine", "icone": "icone_cuisine", "label": "cuisine"},
		]},
	},
	"personnages": {
		"lena": {"nom": "Léna", "couleur": "#c8a2ff", "avatar": "lena avatar", "variable": "lieu_lena", "presence": [
			{"lieu": "cuisine", "si": "heure == 0"}, {"lieu": "cafe", "si": ""},
		]},
	},
	"scenes": {"cafe": "cafe", "salon": "salon", "cuisine": "cuisine"},
}


func navigation_sample() -> Array:
	var compiled := compile(NAVIGATION_STORY)
	if compiled[0] == null:
		return [null, null, compiled[1]]
	var navigation := Navigation.build(NAVIGATION_DATA, compiled[0], "test.json")
	return [compiled[0], navigation.data, navigation.errors]


func test_navigation() -> void:
	var sample := navigation_sample()
	check(sample[0] != null and sample[2].is_empty(), "histoire et cartes de test valides : %s" % [sample[2]])
	if sample[0] == null or not sample[2].is_empty():
		return
	var story: Dictionary = sample[0]
	var interp := Interpreter.new(story)
	interp.set_navigation(sample[1])
	interp.start()
	next_blocking(interp)
	var event := next_blocking(interp)
	check(event.type == "navigate" and event.map == "ville" and event.here == "rue", "la carte est demandée après la réplique, avec le lieu où l'on est")
	check(interp.store.lieu_lena == "cuisine", "présence calculée à l'affichage de la carte : lieu_lena = cuisine")
	var ville := interp.map_view("ville")
	check(ville.titre == "La ville" and ville.affichage == "carte" and ville.exit_text == "" and ville.lieux.size() == 2,
		"carte de la ville : affichage carte, deux lieux, pas de sortie")
	check(ville.lieux[0].presents.size() == 1 and ville.lieux[0].presents[0].nom == "Léna" and ville.lieux[0].presents[0].avatar == "lena avatar",
		"Léna (et son avatar) est signalée sur l'immeuble, qui contient la cuisine")
	check(ville.lieux[1].presents.is_empty(), "personne au café le matin")
	var immeuble := interp.map_view("immeuble")
	check(immeuble.affichage == "pieces" and immeuble.exit_text == "← La ville" and immeuble.lieux.size() == 2
		and immeuble.lieux[1].icone == "icone_cuisine", "sous-carte : barre des pièces, sortie vers la ville, salon et cuisine avec icônes")
	check(interp.overlay_for_label("cuisine") == {"map": "immeuble", "lieu": "cuisine"} and interp.overlay_for_label("cafe").is_empty()
		and interp.overlay_for_label("start").is_empty(), "rangée permanente : dans la cuisine (bâtiment), pas au café ni hors scène")
	var targets := interp.map_targets("ville").map(func(target: Dictionary) -> String: return target.label)
	check(targets == ["cafe", "salon", "cuisine"], "lieux accessibles depuis la ville, sous-carte comprise : %s" % [targets])
	check(not interp.navigate_to("start") and interp.navigate_to("salon"), "seul un lieu accessible est accepté")
	check(next_blocking(interp).text == "Le salon.", "le lieu choisi joue sa scène")
	event = next_blocking(interp)
	check(event.type == "navigate" and interp.store.heure == 1 and interp.store.lieu_lena == "cafe",
		"retour à la carte : la présence est recalculée (Léna au café)")
	immeuble = interp.map_view("immeuble")
	check(immeuble.lieux.size() == 1 and immeuble.lieux[0].lieu == "cuisine", "le salon est masqué à midi (condition fausse)")
	check(interp.map_view("ville").lieux[1].presents.size() == 1, "Léna signalée au café")

	check(interp.rollback() and interp.next().text == "Le salon.", "retour arrière depuis une carte")
	check(interp.rollback() and interp.next().type == "navigate" and interp.store.heure == 0, "retour arrière jusqu'à la carte précédente")
	var saved := var_to_str(interp.get_state())
	var loaded := Interpreter.new(story)
	loaded.set_navigation(sample[1])
	check(loaded.set_state(str_to_var(saved)) and loaded.next().type == "navigate", "la carte est reproposée après chargement")
	check(loaded.navigate_to("cafe") and loaded.next().type == "navigate", "café sans Léna : aucune réplique, retour à la carte")
	loaded.set_translation({"lines": {}, "strings": {"La ville": "The town", "Le café": "The café", "Léna": "Lena"}})
	var translated := loaded.map_view("ville")
	check(translated.titre == "The town" and translated.lieux[1].nom == "The café" and translated.lieux[1].presents[0].nom == "Lena",
		"titre, lieux et personnages traduits sur la carte")
	check(loaded.current_event().type == "navigate", "changement de langue : la carte en cours est réaffichée")

	var report := RouteExplorer.new().explore(story, sample[1])
	check(report.complete and report.errors.is_empty() and report.unreached_labels.is_empty() and report.never_offered.is_empty(),
		"exploration : tous les lieux proposés, toutes les scènes atteintes %s %s %s" % [report.errors, report.unreached_labels, report.never_offered])
	check(report.endings.has("cuisine"), "fin atteinte par la cuisine : %s" % [report.endings])
	var played := play(story, [["L'immeuble", "La cuisine"], ["Le café"], ["L'immeuble", "La cuisine"]], {}, sample[1])
	check(played.lines == ["Bonjour.", "> L'immeuble › La cuisine", "La cuisine.", "> Le café", "Léna: Un café ?",
		"> L'immeuble › La cuisine", "Fin.", "[end]"], "route jouée par les clics sur les cartes : %s" % [played.lines])


func test_navigation_errors() -> void:
	var compiled := compile(NAVIGATION_STORY)
	if compiled[0] == null:
		return
	var bad := Navigation.build({
		"cartes": {
			"ville": {"lieux": [
				{"lieu": "a", "label": "nulle_part"}, {"lieu": "b", "carte": "ailleurs"}, {"lieu": "c"},
				{"lieu": "d", "label": "cafe", "si": "inconnue > 1"}, {"lieu": "e", "label": "cafe", "si": "heure / 2"},
			], "parent": "ailleurs", "affichage": "liste"},
		},
		"personnages": {"lena": {"variable": "lieu_inconnu", "presence": []}},
	}, compiled[0], "test.json")
	var expected := ["label inconnu « nulle_part »", "sous-carte inconnue « ailleurs »", "il faut « label »",
		"variable inconnue « inconnue »", "opérateur « / »", "carte parente inconnue « ailleurs »",
		"« affichage » doit valoir carte ou pieces", "variable « lieu_inconnu » absente"]
	for text in expected:
		check(bad.errors.any(func(error: String) -> bool: return text in error), "erreur signalée : %s" % text)
	check(bad.errors.size() == expected.size(), "aucune erreur en trop :\n    %s" % "\n    ".join(bad.errors))
	var missing := Navigation.build({"cartes": {}}, compiled[0], "test.json")
	check(missing.errors.size() == 1 and "carte inconnue « ville »" in missing.errors[0],
		"carte affichée par le script mais absente des données : %s" % [missing.errors])
	var interp := Interpreter.new(compiled[0])
	interp.start()
	next_blocking(interp)
	var event := next_blocking(interp)
	check(event.type == "error" and "carte inconnue" in event.message, "sans données de navigation : erreur d'exécution")


const TRANSLATED_STORY := """
define lena = Character(_("Léna"), color="#c8a2ff")
default n = 2
label start:
    lena "Bonjour." id start_a
    "Il reste [n] jours." id start_b
    menu:
        lena "Tu viens ?" id start_c
        "Oui":
            return
        "Non":
            return
"""
const ENGLISH := """
translate english start_a:

    # lena "Bonjour."
    lena "Hello."

translate english start_b:
    "[n] days left."

translate english start_c:
    lena "Coming?"

translate english autre:
    "Orphan line."

translate english strings:

    old "Léna"
    new "Lena"

    old "Oui"
    new "Yes"

translate english python:
    pass
"""


## [histoire, traduction anglaise] du petit script ci-dessus.
func translation_sample() -> Array:
	var parser := Parser.new()
	parser.parse_string(TRANSLATED_STORY, "histoire.rpy")
	var story = parser.finish()
	if story == null:
		return [null, null, parser.errors, []]
	var tl := Parser.new()
	tl.parse_translation_string(ENGLISH, "tl.rpy", "english")
	return [story, tl.finish_translation(story), tl.errors, tl.warnings]


func test_translation_parser() -> void:
	var sample := translation_sample()
	check(sample[0] != null, "script avec clauses id et noms entre _() : %s" % ", ".join(sample[2]))
	if sample[0] == null:
		return
	var story: Dictionary = sample[0]
	check(story.characters.lena.name == "Léna" and story.say_ids.has("start_c"), "nom entre _() et identifiants relevés")
	check(sample[1] != null, "traduction lue : %s" % ", ".join(sample[2]))
	if sample[1] != null:
		check(sample[1].lines.size() == 4 and sample[1].strings.get("Oui") == "Yes", "répliques et textes traduits")
	check(sample[3].size() == 1 and "autre" in sample[3][0], "traduction d'une réplique absente du script signalée : %s" % [sample[3]])

	var duplicate := compile("label start:\n    \"a\" id x\n    \"b\" id x\n    return\n")
	check(duplicate[0] == null and "déjà utilisé" in "\n".join(duplicate[1]), "identifiant de réplique en double refusé")
	var in_story := compile("translate english x:\n    \"a\"\nlabel start:\n    return\n")
	check(in_story[0] == null and "game/tl/" in "\n".join(in_story[1]), "translate dans game/story : renvoyé vers game/tl/")

	var bad := Parser.new()
	bad.parse_translation_string("""
translate english start_a:
    lena "Un."
    lena "Deux."
translate english start_b:
    inconnu "Qui ?"
translate english start_c:
    "Valeur [m]"
translate french start_d:
    "Mauvaise langue."
translate english start_e:
    "Avec id." id start_e
translate english strings:
    old "a"
    old "b"
    new "B"
    new "C"
label ailleurs:
    return
""", "tl.rpy", "english")
	check(bad.finish_translation(story) == null, "traduction invalide refusée")
	var expected := [
		[2, "une seule réplique"],
		[6, "personnage inconnu : « inconnu »"],
		[8, "variable inconnue dans le texte : [m]"],
		[9, "traduction « french »"],
		[12, "ne prend pas de clause id"],
		[14, "« old » sans « new »"],
		[17, "« new » sans « old »"],
		[18, "seuls les blocs « translate english"],
	]
	for item in expected:
		var found := false
		for error in bad.errors:
			if error.begins_with("tl.rpy:%d: " % item[0]) and item[1] in error:
				found = true
		check(found, "traduction, ligne %d : %s" % item)
	check(bad.errors.size() == expected.size(), "aucune erreur en trop :\n    %s" % "\n    ".join(bad.errors))


func test_translation_runtime() -> void:
	var sample := translation_sample()
	if sample[0] == null or sample[1] == null:
		check(false, "exemple de traduction compilé")
		return
	var interp := Interpreter.new(sample[0])
	interp.set_translation(sample[1])
	interp.start()
	var first := next_blocking(interp)
	check(first.text == "Hello." and first.name == "Lena" and first.id == "start_a",
		"réplique et nom traduits, même identifiant (texte déjà lu commun aux langues)")
	check(next_blocking(interp).text == "2 days left.", "interpolation dans la traduction")
	var menu := next_blocking(interp)
	check(menu.prompt.text == "Coming?" and menu.choices[0].text == "Yes" and menu.choices[1].text == "Non",
		"menu : question et choix traduits, choix sans traduction inchangé")
	interp.set_translation({})
	var again := interp.current_event()
	check(again.type == "menu" and again.prompt.text == "Tu viens ?" and again.choices[0].text == "Oui"
		and interp.history.back().text == "Tu viens ?", "changement de langue : menu réaffiché, historique mis à jour")

	var other := Interpreter.new(sample[0])
	other.start()
	check(next_blocking(other).text == "Bonjour.", "sans traduction : texte d'origine")
	other.set_translation(sample[1])
	var current := other.current_event()
	check(current.text == "Hello." and other.history.size() == 1 and other.history[0].text == "Hello.",
		"changement de langue : réplique réaffichée sans doublon dans l'historique")


func test_demo_translation() -> void:
	var story := demo_story()
	if story.is_empty():
		return
	var langues := Langues.new()
	langues.load_file(DEMO_DIR.path_join("langues.json"))
	check(langues.source() == "fr" and langues.has("en") and not langues.has("de"), "démo : langues fr et en")
	var translation = langues.load_translation("en", story, DEMO_DIR.path_join("tl"))
	check(translation != null and langues.warnings.is_empty(), "démo : traduction anglaise lue %s %s" % [langues.errors, langues.warnings])
	if translation == null:
		return
	var missing: Array = story.say_ids.keys().filter(func(id: String) -> bool: return not translation.lines.has(id))
	check(missing.is_empty(), "démo : toutes les répliques traduites (manquantes : %s)" % [missing])
	var result := play(story, ["Check the letterbox", "Ask her about the photo"], translation)
	check(result.store.mystere == 2 and "A memory comes back: the smell of plaster, and my father's voice on the building site." in result.lines,
		"démo en anglais : choix traduits, route jouée jusqu'au bout")
	check("Me: Third floor… This is it." in result.lines, "démo en anglais : nom du personnage traduit")


func test_interface_texts() -> void:
	var empty: Array = InterfaceTexts.TEXTS.en.keys().filter(func(text: String) -> bool: return str(InterfaceTexts.TEXTS.en[text]).strip_edges() == "")
	check(empty.is_empty(), "interface : aucune traduction anglaise vide %s" % [empty])
	var context := InterfaceTexts.QUICK_MENU_CONTEXT
	InterfaceTexts.set_language("en")
	var english := [InterfaceTexts.t("Nouvelle partie"), InterfaceTexts.t("Retour"), InterfaceTexts.t("Retour", context)]
	InterfaceTexts.set_language("fr")
	var french := [InterfaceTexts.t("Nouvelle partie"), InterfaceTexts.t("Retour"), InterfaceTexts.t("Retour", context)]
	check(english == ["Start", "Return", "Back"], "interface en anglais, contexte du menu rapide : %s" % [english])
	check(french == ["Nouvelle partie", "Retour", "Retour"], "interface en français, sans repli sur l'anglais : %s" % [french])


func test_game_story() -> void:
	var story := game_story()
	check(not story.is_empty(), "le script du jeu compile sans erreur")
	if story.is_empty():
		return
	var navigation := Navigation.load_file(GAME_NAVIGATION, story)
	check(navigation.errors.is_empty(), "cartes de navigation du jeu valides : %s" % [navigation.errors])
	var report := RouteExplorer.new().explore(story, navigation.data)
	check(report.complete and report.errors.is_empty(), "exploration complète sans erreur (%d états) %s" % [report.states, report.errors])
	# Les labels temps_* sont une bibliothèque générée : une fiche n'utilise pas forcément chaque saut.
	var unreached: Array = report.unreached_labels.filter(func(label: String) -> bool: return not label.begins_with("temps_"))
	check(unreached.is_empty(), "tous les labels sont atteignables : %s" % [unreached])
	check(report.never_offered.is_empty(), "tous les choix sont proposés : %s" % [report.never_offered])
	check(not report.endings.is_empty(), "au moins une fin : %s" % [report.endings])


## Rejoue les routes calculées par l'explorateur Python : même fin et même état final,
## dans la langue des fiches puis dans chaque traduction (choix cliqués par leur texte traduit).
func test_expected_routes() -> void:
	var story := game_story()
	if story.is_empty():
		return
	if not FileAccess.file_exists(ROUTES_PATH):
		check(false, "tests/routes_attendues.json présent (tools/fiches.py generer)")
		return
	var data = JSON.parse_string(FileAccess.get_file_as_string(ROUTES_PATH))
	check(typeof(data) == TYPE_DICTIONARY and not data.routes.is_empty(), "au moins une route attendue")
	var navigation := Navigation.load_file(GAME_NAVIGATION, story)
	var langues := Langues.new()
	langues.load_file()
	var translations := {}
	for code in langues.languages.slice(1).map(func(language: Dictionary) -> String: return language.code):
		translations[code] = langues.load_translation(code, story)
		check(translations[code] != null, "traduction « %s » du jeu lue %s" % [code, langues.errors])
	for route in data.routes:
		check_route(story, navigation.data, route, route.choix, {}, route.nom)
		for code in route.get("choix_traduits", {}):
			if translations.get(code) != null:
				check_route(story, navigation.data, route, route.choix_traduits[code], translations[code], "%s (%s)" % [route.nom, code])


func check_route(story: Dictionary, navigation: Dictionary, route: Dictionary, choices: Array, translation: Dictionary, name: String) -> void:
	var interp := Interpreter.new(story)
	interp.set_navigation(navigation)
	interp.set_translation(translation)
	interp.start()
	var result := drive(interp, choices)
	var differences: Array = []
	for variable in route.etat_final:
		if interp.store.get(variable) != route.etat_final[variable]:
			differences.append("%s = %s (attendu %s)" % [variable, interp.store.get(variable), route.etat_final[variable]])
	var reached: bool = result.lines.back() == "[end]" and interp.current_label() == route.fin
	check(reached and differences.is_empty(), "%s : %d choix → %s %s%s" % [name, choices.size(), route.fin,
		"" if reached else "(arrivée : %s, %s) " % [interp.current_label(), result.lines.back()], differences])


func test_gallery() -> void:
	var story := game_story()
	if story.is_empty():
		return
	var gallery := Gallery.load_file("res://game/galerie.json", story)
	check(gallery.errors.is_empty() and not gallery.entries.is_empty(), "galerie valide : %s" % [gallery.errors])
	var assets := Assets.new()
	assets.index_dir("res://game/images")
	for entry in gallery.entries:
		var names: Array = entry.images.duplicate()
		names.append(entry.thumbnail)
		for image_name in names:
			check(assets.images.has(image_name), "galerie : image « %s » présente (définitive ou provisoire)" % image_name)
		if entry.video != "":
			check(Assets.video_stream(entry.video) != null, "galerie : vidéo %s disponible en .ogv" % entry.video)

	var path := "user://test_galerie.json"
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string('{"entrees": [{"titre": "x", "label": "nulle_part", "images": ["a"]}, {"label": "start"}]}')
	file.close()
	var bad := Gallery.load_file(path, story)
	check(bad.errors.size() == 2 and "nulle_part" in bad.errors[0], "galerie : label inconnu et entrée vide signalés : %s" % [bad.errors])
	DirAccess.remove_absolute(path)


func test_characters() -> void:
	var story := game_story()
	if story.is_empty():
		return
	var sheets := Characters.load_file("res://game/personnages.json", story)
	check(sheets.errors.is_empty() and not sheets.characters.is_empty(), "personnages.json valide : %s" % [sheets.errors])
	var interp := Interpreter.new(story)
	interp.start()
	var assets := Assets.new()
	assets.index_dir("res://game/images")
	for character in sheets.characters:
		if character.avatar != "":
			check(assets.images.has(character.avatar), "personnages : avatar « %s » présent" % character.avatar)
		for gauge in character.jauges + character.competences + character.relations:
			var value = interp.store.get(gauge.variable)
			var numeric := typeof(value) in [TYPE_INT, TYPE_FLOAT]
			check(numeric, "personnages : « %s » est une variable numérique du script" % gauge.variable)
			if numeric:
				check(gauge.min <= value and value <= gauge.max, "personnages : « %s » = %s dans [%s, %s]" % [gauge.variable, value, gauge.min, gauge.max])
	# Paliers : le plus haut seuil atteint gagne, aucun sous le premier seuil.
	var gauge := {"paliers": [{"des": 4.0, "nom": "voisine"}, {"des": 6.0, "nom": "amie"}]}
	check(Characters.threshold_name(gauge, 3.0) == "" and Characters.threshold_name(gauge, 5.0) == "voisine"
		and Characters.threshold_name(gauge, 9.0) == "amie", "personnages : paliers")

	var path := "user://test_personnages.json"
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string('{"personnages": {"x": {"nom": "X", "jauges": [{"variable": "nulle_part"}, {"nom": "sans variable"}]}, "y": 3}}')
	file.close()
	var bad := Characters.load_file(path, story)
	check(bad.errors.size() == 3 and "nulle_part" in bad.errors[0], "personnages : variable inconnue, jauge sans variable et fiche invalide signalées : %s" % [bad.errors])
	DirAccess.remove_absolute(path)


func test_renames() -> void:
	var story := demo_story()
	if story.is_empty():
		return
	# Une sauvegarde faite avant les renommages : ancienne variable, ancien label.
	var interp := Interpreter.new(story)
	interp.start()
	while not interp.next().type in BLOCKING_EVENTS:
		pass
	var state := interp.get_state()
	var some_label: String = state.resume[0]
	var some_variable: String = story.variables[0]
	state.store["vieux_nom"] = state.store[some_variable]
	state.store.erase(some_variable)
	state.store["vieux_nom"] = 42
	state.resume[0] = "vieux_label"
	state.call_stack = [["autre_vieux_label", 0]]
	var without := Interpreter.new(story)
	check(not without.set_state(state), "sans renommage, un ancien label empêche le chargement")
	var loaded := Interpreter.new(story)
	loaded.set_renames({"variables": [{"ancien": "vieux_nom", "nouveau": some_variable}],
		"scenes": [{"ancien": "vieux_label", "nouveau": some_label}, {"ancien": "autre_vieux_label", "nouveau": "vieux_label"}]})
	check(loaded.set_state(state), "avec renommages, la sauvegarde se charge")
	check(loaded.store.get(some_variable) == 42, "la valeur de l'ancienne variable passe sous le nouveau nom")
	check(not loaded.store.has("vieux_nom"), "l'ancien nom disparaît du store")
	check(loaded.pc == story.labels[some_label] + int(state.resume[1]) and loaded.call_stack == [story.labels[some_label]],
		"labels renommés, en chaîne, résolus : %s %s" % [loaded.pc, loaded.call_stack])

	var game := game_story()
	if not game.is_empty():
		var renames := Renames.load_file("res://game/renommages.json", game)
		check(renames.errors.is_empty(), "renommages.json valide : %s" % [renames.errors])
	var bad := Renames.build({"variables": [{"ancien": "x", "nouveau": "nulle_part"}, {"ancien": "y"}], "scenes": "non"}, story)
	check(bad.errors.size() == 3 and "nulle_part" in bad.errors[0], "renommages : nouveau nom inconnu, entrée incomplète et liste invalide signalés : %s" % [bad.errors])


func test_time() -> void:
	var story := game_story()
	if story.is_empty():
		return
	var temps := Temps.load_file("res://game/temps.json", story)
	check(temps.errors.is_empty() and not temps.data.creneaux.is_empty(), "temps.json valide : %s" % [temps.errors])
	var interp := Interpreter.new(story)
	interp.start()
	while not interp.next().type in BLOCKING_EVENTS:
		pass
	var start_text := Temps.text(temps.data, interp.store)
	var expected_start := ("%s %d %s %d" % [interp.store.jour_semaine, interp.store.jour_mois, temps.data.mois[interp.store.mois - 1], interp.store.annee]) \
		if temps.data.date else "Jour 1"
	check(start_text.begins_with(expected_start + " · ") and start_text.ends_with(str(interp.store.moment)), "texte du temps au départ : %s" % start_text)
	# temps_avancer : une journée complète (autant d'appels que de créneaux) revient au même
	# créneau, un jour plus tard. Script : les déclarations du jeu, et un start qui appelle le label.
	var count: int = temps.data.creneaux.size()
	var source := with_start(FileAccess.get_file_as_string("res://game/story/personnages_et_variables.rpy"),
		"label start:\n" + "    call temps_avancer\n".repeat(count) + "    \"fin\"")
	var compiled: Array = compile(source)
	check(compiled[1].is_empty(), "script de temps compilé : %s" % [compiled[1]])
	var day_interp := Interpreter.new(compiled[0])
	day_interp.start()
	var before: int = day_interp.store.creneau
	var day: int = day_interp.store.jour
	while not day_interp.next().type in BLOCKING_EVENTS:
		pass
	check(day_interp.store.creneau == before and day_interp.store.moment == temps.data.creneaux[before] and day_interp.store.jour == day + 1,
		"temps_avancer : une journée complète revient au même créneau, un jour plus tard (%s)" % Temps.text(temps.data, day_interp.store))
	var english := Temps.text({"creneaux": ["matin"], "jours": true, "semaine": ["lundi"], "date": false, "mois": []},
		{"jour": 3, "jour_semaine": "lundi", "moment": "matin"}, func(t: String) -> String: return {"matin": "morning", "lundi": "Monday"}.get(t, t))
	check(english == "Jour 3 · Monday · morning", "texte traduit : %s" % english)
	if temps.data.date:
		test_calendar(story, temps.data)
	var bad := Temps.load_file("res://game/galerie.json", story)
	check(bad.errors.size() == 1 and bad.data.creneaux.is_empty(), "temps : fichier au mauvais format signalé")


## Calendrier généré : sauts de jours et de mois comparés au calendrier de Godot, voyage entre époques.
func test_calendar(story: Dictionary, model: Dictionary) -> void:
	var declarations := FileAccess.get_file_as_string("res://game/story/personnages_et_variables.rpy")
	var epoques: Array = model.get("epoques", [])
	var scenario := "label start:\n    $ temps_saut = 800\n    call temps_sauter_jours\n    \"a\"\n" \
		+ "    $ temps_saut = 3\n    call temps_sauter_mois\n    \"b\"\n"
	if epoques.size() >= 2:
		scenario += "    call temps_epoque_%s\n    \"c\"\n    call temps_epoque_%s\n    \"d\"\n" % [epoques[1], epoques[0]]
	var compiled: Array = compile(with_start(declarations, scenario))
	check(compiled[1].is_empty(), "script de calendrier compilé : %s" % [compiled[1]])
	if not compiled[1].is_empty():
		return
	var interp := Interpreter.new(compiled[0])
	interp.start()
	var origin := _unix(interp.store)
	var weekday_origin: int = interp.store.jour_semaine_rang
	while interp.next().type != "say":
		pass
	var after_days := Time.get_datetime_dict_from_unix_time(origin + 800 * 86400)
	check(interp.store.annee == after_days.year and interp.store.mois == after_days.month and interp.store.jour_mois == after_days.day,
		"800 jours plus tard : %d-%02d-%02d attendu, %d-%02d-%02d obtenu" % [after_days.year, after_days.month, after_days.day, interp.store.annee, interp.store.mois, interp.store.jour_mois])
	check(interp.store.jour_semaine_rang == (weekday_origin + 800) % 7 and interp.store.jour == 801, "jour de la semaine et compteur de jours")
	var day_of_month: int = interp.store.jour_mois
	var month: int = interp.store.mois
	while interp.next().type != "say":
		pass
	var expected_month: int = (month - 1 + 3) % 12 + 1
	check(interp.store.mois == expected_month and (interp.store.jour_mois == day_of_month or interp.store.jour_mois == interp.store.temps_longueur_mois),
		"3 mois plus tard : mois %d, jour %d (obtenu %d/%d)" % [expected_month, day_of_month, interp.store.jour_mois, interp.store.mois])
	if epoques.size() >= 2:
		var before := {"annee": interp.store.annee, "mois": interp.store.mois, "jour_mois": interp.store.jour_mois, "jour": interp.store.jour}
		while interp.next().type != "say":
			pass
		check(interp.store.epoque == epoques[1] and interp.store.annee != before.annee, "voyage vers « %s » : %s" % [epoques[1], Temps.text(model, interp.store)])
		while interp.next().type != "say":
			pass
		check(interp.store.epoque == epoques[0] and interp.store.annee == before.annee and interp.store.mois == before.mois
			and interp.store.jour_mois == before.jour_mois and interp.store.jour == before.jour, "retour à « %s » : la date laissée est reprise" % epoques[0])


## Remplace le « label start » du script généré (qui saute à la première scène) par un scénario.
static func with_start(declarations: String, scenario: String) -> String:
	var found := RegEx.create_from_string("label start:\\n    jump [a-z0-9_]+").search(declarations)
	if found == null:
		return declarations
	return declarations.substr(0, found.get_start()) + scenario + declarations.substr(found.get_end())


static func _unix(store: Dictionary) -> int:
	return Time.get_unix_time_from_datetime_dict({"year": store.annee, "month": store.mois, "day": store.jour_mois, "hour": 12, "minute": 0, "second": 0})


# --- Outils ------------------------------------------------------------------------------

func check(condition: bool, label: String) -> void:
	if condition:
		_passed += 1
		print("  ok      ", label)
	else:
		_failed += 1
		printerr("  ÉCHEC   ", label)


func load_story(dir: String) -> Dictionary:
	var parser := Parser.new()
	parser.parse_dir(dir)
	var story = parser.finish()
	if story == null:
		printerr("\n".join(parser.errors))
		return {}
	return story


func demo_story() -> Dictionary:
	return load_story(DEMO_STORY)


func game_story() -> Dictionary:
	return load_story(GAME_STORY)


func compile(source: String) -> Array:
	var parser := Parser.new()
	parser.parse_string(source, "test.rpy")
	return [parser.finish(), parser.errors]


func choice_index(event: Dictionary, text: String) -> int:
	for choice in event.choices:
		if choice.text == text:
			return choice.index
	return -1


## Suit des clics sur les cartes comme le joueur (par les textes affichés) ; renvoie le label
## du lieu finalement choisi, ou une chaîne vide.
func click_map(interp: Interpreter, map_id: String, clicks: Array) -> String:
	var current := map_id
	for text in clicks:
		var view := interp.map_view(current)
		if view.is_empty():
			return ""
		if text == view.exit_text:
			current = view.parent
			continue
		var found := false
		for entry in view.lieux + view.raccourcis:
			if entry.nom == text:
				found = true
				# Le déplacement se paie au clic, comme dans le lecteur.
				if not entry.get("temps", {}).is_empty():
					interp.apply_costs([entry.temps])
				if entry.label != "":
					return entry.label
				current = entry.carte
				break
		if not found:
			return ""
	return ""


func next_blocking(interp: Interpreter) -> Dictionary:
	var event := interp.next()
	while event.type not in BLOCKING_EVENTS:
		event = interp.next()
	return event


## Joue l'histoire en répondant aux menus avec les textes donnés, dans l'ordre ; une réponse
## à une carte est la liste des textes cliqués (lieu, sous-carte ou « ← carte parente »).
func play(story: Dictionary, answers: Array, translation := {}, navigation := {}) -> Dictionary:
	var interp := Interpreter.new(story)
	interp.set_translation(translation)
	if not navigation.is_empty():
		interp.set_navigation(navigation)
	interp.start()
	var result := drive(interp, answers)
	result.store = interp.store
	return result


func drive(interp: Interpreter, answers: Array) -> Dictionary:
	var lines: Array = []
	var menus: Array = []
	var pending := answers.duplicate()
	var done := false
	while not done:
		var event := interp.next()
		match event.type:
			"say":
				lines.append(event.text if event.name == "" else "%s: %s" % [event.name, event.text])
			"menu":
				menus.append(event.choices.map(func(choice): return choice.text))
				var wanted = pending.pop_front()
				var index := choice_index(event, str(wanted))
				if index < 0:
					lines.append("!choix introuvable : %s" % wanted)
					done = true
				else:
					lines.append("> %s" % wanted)
					interp.choose(index)
			"navigate":
				var wanted = pending.pop_front()
				var clicks: Array = wanted if typeof(wanted) == TYPE_ARRAY else [wanted]
				var label := click_map(interp, event.map, clicks)
				if label == "" or not interp.navigate_to(label):
					lines.append("!lieu introuvable : %s" % [clicks])
					done = true
				else:
					lines.append("> %s" % " › ".join(PackedStringArray(clicks)))
			"movie":
				lines.append("[movie %s]" % event.path)
			"end":
				lines.append("[end]")
				done = true
			"error":
				lines.append("!erreur %s" % event.message)
				done = true
	return {"lines": lines, "menus": menus}
