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
const Assets = preload("res://engine/assets.gd")

const DEMO_STORY := "res://tests/fixtures/demo/game/story"
const GAME_STORY := "res://game/story"
const ROUTES_PATH := "res://tests/routes_attendues.json"
const BLOCKING_EVENTS := ["say", "menu", "movie", "pause", "end", "error"]

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
	print("Jeu (game/story)")
	test_game_story()
	print("Routes attendues (tools/fiches.py)")
	test_expected_routes()
	print("Galerie du jeu")
	test_gallery()
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


func test_game_story() -> void:
	var story := game_story()
	check(not story.is_empty(), "le script du jeu compile sans erreur")
	if story.is_empty():
		return
	var report := RouteExplorer.new().explore(story)
	check(report.complete and report.errors.is_empty(), "exploration complète sans erreur (%d états) %s" % [report.states, report.errors])
	check(report.unreached_labels.is_empty(), "tous les labels sont atteignables : %s" % [report.unreached_labels])
	check(report.never_offered.is_empty(), "tous les choix sont proposés : %s" % [report.never_offered])
	check(not report.endings.is_empty(), "au moins une fin : %s" % [report.endings])


## Rejoue les routes calculées par l'explorateur Python : même fin et même état final.
func test_expected_routes() -> void:
	var story := game_story()
	if story.is_empty():
		return
	if not FileAccess.file_exists(ROUTES_PATH):
		check(false, "tests/routes_attendues.json présent (tools/fiches.py generer)")
		return
	var data = JSON.parse_string(FileAccess.get_file_as_string(ROUTES_PATH))
	check(typeof(data) == TYPE_DICTIONARY and not data.routes.is_empty(), "au moins une route attendue")
	for route in data.routes:
		var interp := Interpreter.new(story)
		interp.start()
		var result := drive(interp, route.choix)
		var differences: Array = []
		for variable in route.etat_final:
			if interp.store.get(variable) != route.etat_final[variable]:
				differences.append("%s = %s (attendu %s)" % [variable, interp.store.get(variable), route.etat_final[variable]])
		var reached: bool = result.lines.back() == "[end]" and interp.current_label() == route.fin
		check(reached and differences.is_empty(), "%s : %d choix → %s %s%s" % [route.nom, route.choix.size(), route.fin,
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


func next_blocking(interp: Interpreter) -> Dictionary:
	var event := interp.next()
	while event.type not in BLOCKING_EVENTS:
		event = interp.next()
	return event


## Joue l'histoire en répondant aux menus avec les textes donnés, dans l'ordre.
func play(story: Dictionary, answers: Array) -> Dictionary:
	var interp := Interpreter.new(story)
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
			"movie":
				lines.append("[movie %s]" % event.path)
			"end":
				lines.append("[end]")
				done = true
			"error":
				lines.append("!erreur %s" % event.message)
				done = true
	return {"lines": lines, "menus": menus}
