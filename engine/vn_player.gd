## Lecteur de visual novel : scène (fond, personnages, dialogues, choix, vidéos), cartes
## de navigation (lieux et personnages présents), menus (principal, jeu, sauvegardes,
## historique, préférences, galerie), avance rapide, avance automatique et retour arrière,
## comme dans Ren'Py.
##
## Commandes : clic / Espace / Entrée = continuer ; molette vers le haut / Page ↑ = retour
## arrière ; Ctrl maintenu ou Tab = avance rapide ; A = avance automatique ; H = historique ;
## Échap / clic droit = menu ; F5 / F9 = sauvegarde / chargement rapide.
##
## Arguments après « -- » :
##   --choices=1,0   démarre la partie tout de suite, choisit ces options (rang parmi
##                   les choix affichés) et quitte à la fin
##   --autoplay      démarre la partie tout de suite et avance seul
##   --actions=a,b   joue une suite d'actions d'interface, une toutes les 1,5 s
##                   (voir _run_action) : sert aux captures (screenshot:fichier.png) et aux
##                   tests visuels
##   --langue=en     joue dans cette langue, sans changer la préférence enregistrée
extends Control

const Parser = preload("res://engine/rpy_parser.gd")
const Interpreter = preload("res://engine/rpy_interpreter.gd")
const Assets = preload("res://engine/assets.gd")
const PersistentData = preload("res://engine/persistent_data.gd")
const SaveSlots = preload("res://engine/save_slots.gd")
const Gallery = preload("res://engine/gallery.gd")
const Characters = preload("res://engine/characters.gd")
const Renames = preload("res://engine/renommages.gd")
const Temps = preload("res://engine/temps.gd")
const Navigation = preload("res://engine/navigation.gd")
const Style = preload("res://engine/ui/ui_style.gd")
const GameMenu = preload("res://engine/ui/game_menu.gd")
const QuickMenu = preload("res://engine/ui/quick_menu.gd")
const MapScreen = preload("res://engine/ui/map_screen.gd")
const Langues = preload("res://engine/langues.gd")
const InterfaceTexts = preload("res://engine/ui/traductions_interface.gd")

const STORY_DIR := "res://game/story"
const GALLERY_PATH := "res://game/galerie.json"
const CHARACTERS_PATH := "res://game/personnages.json"
const RENAMES_PATH := "res://game/renommages.json"
const TEMPS_PATH := "res://game/temps.json"
const NAVIGATION_PATH := "res://game/navigation.json"
const XALIGN := {"left": 0.0, "center": 0.5, "right": 1.0, "truecenter": 0.5}
const TRANSITION_TIME := 0.5
const SKIP_DELAY := 0.05
const AUTOPLAY_DELAY := 1.5
const PERSISTENT_SAVE_INTERVAL := 10.0
const BLOCKING_EVENTS := ["say", "menu", "navigate", "movie", "pause", "end", "error"]

var _interp: Interpreter
var _assets: Assets
var _persistent: PersistentData
var _langues: Langues
var _story: Dictionary = {}
var _language := ""
var _forced_language := ""
var _characters: Dictionary = {}
var _waiting := ""
var _step := 0
var _in_game := false
var _skipping := false
var _skip_held := false
var _auto := false
var _current_seen := false
var _current_music := ""
var _last_say: Dictionary = {}
var _screenshot: Image
var _text_tween: Tween
var _autoplay := false
var _autoplay_choices: Array = []
var _actions: Array = []

var _stage: Control
var _background: TextureRect
var _missing_background: Label
var _character_layer: Control
var _fade: ColorRect
var _dialogue: Panel
var _speaker: Label
var _text: RichTextLabel
var _choices: VBoxContainer
var _map: MapScreen
var _video: VideoStreamPlayer
var _notice_layer: CenterContainer
var _notice: Label
var _skip_indicator: Label
var _quick_menu: QuickMenu
var _time_label: Label
var _time_model: Dictionary = Temps.empty()
var _game_menu: GameMenu
var _toast: Label
var _music: AudioStreamPlayer
var _sound: AudioStreamPlayer


func _ready() -> void:
	_parse_arguments()
	_persistent = PersistentData.new()
	_persistent.load_data()
	_build_ui()
	var parser := Parser.new()
	parser.parse_dir(STORY_DIR)
	var story = parser.finish()
	if story == null:
		_fatal("Le script contient des erreurs :\n\n" + "\n".join(parser.errors))
		return
	_assets = Assets.new()
	_assets.index_dir(Assets.GAME_DIR.path_join("images"))
	_assets.add_definitions(story.images)
	var gallery := Gallery.load_file(GALLERY_PATH, story)
	for problem in gallery.errors:
		push_warning(problem)
	var characters := Characters.load_file(CHARACTERS_PATH, story)
	for problem in characters.errors:
		push_warning(problem)
	_story = story
	_langues = Langues.new()
	_langues.load_file()
	_interp = Interpreter.new(story)
	_interp.label_entered.connect(_persistent.mark_label)
	_interp.label_entered.connect(_update_overlay)
	var navigation := Navigation.load_file(NAVIGATION_PATH, story)
	if not navigation.errors.is_empty():
		_fatal("Les cartes de navigation contiennent des erreurs :\n\n" + "\n".join(navigation.errors))
		return
	_interp.set_navigation(navigation.data)
	var renames := Renames.load_file(RENAMES_PATH, story)
	for problem in renames.errors:
		push_warning(problem)
	_interp.set_renames(renames.data)
	var temps := Temps.load_file(TEMPS_PATH, story)
	for problem in temps.errors:
		push_warning(problem)
	_time_model = temps.data
	_map.view = _interp.map_view
	_map.assets = _assets
	_game_menu.context = {"persistent": _persistent, "gallery": gallery.entries, "characters": characters.characters,
		"store": _interp.store, "assets": _assets, "history": [], "languages": _langues.languages,
		"translate": _interp.translate_string}
	_apply_preferences()
	if _waiting == "fatal":
		return
	var timer := Timer.new()
	timer.wait_time = PERSISTENT_SAVE_INTERVAL
	timer.autostart = true
	timer.timeout.connect(_persistent.save_data)
	add_child(timer)
	if _autoplay and _actions.is_empty():
		_start_game()
	else:
		_show_main_menu()
	if not _actions.is_empty():
		_schedule_action()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST and _persistent != null:
		_persistent.save_data()


## Ctrl maintenu : avance rapide tant que la touche est enfoncée.
func _process(_delta: float) -> void:
	var held := _in_game and not _game_menu.visible and Input.is_key_pressed(KEY_CTRL)
	if held != _skip_held:
		_skip_held = held
		_set_skip(held)


func _unhandled_input(event: InputEvent) -> void:
	if _waiting == "fatal" or _interp == null:
		return
	var key := event as InputEventKey
	if key != null and key.pressed and not key.echo:
		var handled := true
		match key.keycode:
			KEY_ESCAPE:
				_on_cancel()
			KEY_F5:
				_quicksave()
			KEY_F9:
				_quickload()
			KEY_TAB:
				_set_skip(not _skipping)
			KEY_A:
				_set_auto(not _auto)
			KEY_H:
				_open_game_menu("history")
			KEY_PAGEUP:
				_rollback()
			_:
				handled = false
		if handled:
			get_viewport().set_input_as_handled()
			return
	var mouse := event as InputEventMouseButton
	if mouse != null and mouse.pressed:
		if mouse.button_index == MOUSE_BUTTON_RIGHT:
			get_viewport().set_input_as_handled()
			_on_cancel()
			return
		if mouse.button_index == MOUSE_BUTTON_WHEEL_UP:
			get_viewport().set_input_as_handled()
			_rollback()
			return
	if _game_menu.visible or not _in_game:
		return
	var clicked := mouse != null and mouse.pressed and mouse.button_index == MOUSE_BUTTON_LEFT
	if clicked or event.is_action_pressed("ui_accept"):
		get_viewport().set_input_as_handled()
		if _skipping:
			# Comme Ren'Py : un clic arrête l'avance rapide.
			_set_skip(false)
		else:
			_continue()


# --- Déroulement de la partie ----------------------------------------------------------

func _start_game() -> void:
	_game_menu.close()
	_in_game = true
	_stage.visible = true
	_quick_menu.visible = true
	_stop_media()
	_clear_choices()
	_map.close()
	_show_scene("", "")
	_dialogue.visible = false
	_set_skip(false)
	_set_auto(false)
	_interp.start()
	_advance()


func _show_main_menu() -> void:
	_in_game = false
	_step += 1
	_waiting = ""
	_set_skip(false)
	_set_auto(false)
	_kill_text_tween()
	_stop_media()
	_music.stop()
	_sound.stop()
	_current_music = ""
	_clear_choices()
	_map.close()
	_dialogue.visible = false
	_stage.visible = false
	_quick_menu.visible = false
	_persistent.save_data()
	_game_menu.show_main_menu()


func _on_game_end() -> void:
	_set_skip(false)
	_set_auto(false)
	_persistent.save_data()
	if _autoplay and _actions.is_empty():
		get_tree().quit()
		return
	# Comme Ren'Py : la fin de la partie ramène au menu principal.
	_show_main_menu()


func _quit() -> void:
	_persistent.save_data()
	get_tree().quit()


func _advance() -> void:
	_step += 1
	_waiting = ""
	while not _handle(_interp.next()):
		pass
	if _in_game:
		_refresh_quick_menu()
	_schedule_autoplay()


## Traite un événement ; renvoie true s'il faut attendre le joueur.
func _handle(event: Dictionary) -> bool:
	match event.type:
		"scene":
			_persistent.mark_image(event.image)
			_show_scene(event.image, _transition(event.transition))
		"show":
			_persistent.mark_image(event.image)
			_show_character(event.tag, event.image, event.at, _transition(event.transition))
		"hide":
			_hide_character(event.tag, _transition(event.transition))
		"audio":
			_play_audio(event)
		"say":
			_waiting = "say"
			_show_say(event)
		"menu":
			_waiting = "menu"
			_set_skip(false)
			_show_menu(event)
		"navigate":
			_waiting = "navigate"
			_set_skip(false)
			_show_map(event.map, event.get("here", ""))
		"movie":
			_waiting = "movie"
			_play_movie(event.path)
		"pause":
			_waiting = "pause"
			_start_pause(event.seconds)
		"end":
			_waiting = "end"
			_on_game_end()
		"error":
			_fatal(event.message)
	return event.type in BLOCKING_EVENTS


func _continue() -> void:
	match _waiting:
		"say":
			if _text_animating():
				_kill_text_tween()
				_text.visible_ratio = 1.0
				_on_text_shown()
				return
			_advance()
		"pause":
			_advance()
		"movie":
			_finish_movie()


func _on_choice(index: int) -> void:
	if _waiting != "menu" or _game_menu.visible:
		return
	_clear_choices()
	if _interp.choose(index):
		_advance()


## Lieu choisi sur la carte : saute à sa scène.
func _on_map_choice(label: String) -> void:
	if _waiting != "navigate" or _game_menu.visible:
		return
	if _interp.navigate_to(label):
		_map.close()
		_advance()


func _rollback() -> void:
	if not _in_game or _game_menu.visible or _interp == null or not _interp.can_rollback():
		return
	_set_skip(false)
	_interp.rollback()
	_stop_media()
	_clear_choices()
	_map.close()
	_rebuild_stage(_interp.stage)
	_advance()


## Appelle callback après un délai, sauf si la partie a avancé ou si un menu est ouvert.
func _after(seconds: float, callback: Callable) -> void:
	var step := _step
	get_tree().create_timer(seconds).timeout.connect(func() -> void:
		if step == _step and _in_game and not _game_menu.visible:
			callback.call()
	)


# --- Avance rapide et automatique ------------------------------------------------------

func _set_skip(on: bool) -> void:
	var enabled := on and _in_game and _waiting != "fatal"
	var changed := enabled != _skipping
	_skipping = enabled
	_quick_menu.set_toggle("skip", _skipping)
	_skip_indicator.visible = _skipping
	if not changed or not _skipping:
		return
	match _waiting:
		"say":
			_kill_text_tween()
			_text.visible_ratio = 1.0
			_on_text_shown()
		"pause", "movie":
			_after(SKIP_DELAY, _continue)


func _set_auto(on: bool) -> void:
	_auto = on and _in_game
	_quick_menu.set_toggle("auto", _auto)
	if _auto and _waiting == "say" and not _text_animating():
		_on_text_shown()


## Texte entièrement affiché : l'avance rapide ou automatique peut enchaîner.
func _on_text_shown() -> void:
	if _waiting != "say":
		return
	if _skipping:
		if _current_seen or _persistent.preferences.skip_unseen:
			_after(SKIP_DELAY, _advance)
		else:
			# Comme Ren'Py : l'avance rapide s'arrête sur le texte jamais lu.
			_set_skip(false)
			_show_toast("Avance rapide arrêtée : texte pas encore lu")
	elif _auto:
		var delay: float = _persistent.preferences.auto_delay + String(_last_say.get("text", "")).length() * 0.02
		_after(delay, _auto_advance)


func _auto_advance() -> void:
	if _auto and not _skipping and _waiting == "say" and not _text_animating():
		_advance()


## Après la fermeture d'un menu : relance l'avance rapide ou automatique en cours.
func _resume_modes() -> void:
	if _waiting == "say" and not _text_animating():
		_on_text_shown()
	elif _skipping and _waiting in ["pause", "movie"]:
		_after(SKIP_DELAY, _continue)


func _transition(transition: String) -> String:
	return "" if _skipping else transition


# --- Scène -----------------------------------------------------------------------------

func _show_scene(image: String, transition: String) -> void:
	for tag in _characters:
		_characters[tag].queue_free()
	_characters.clear()
	var previous := _background.texture
	var texture: Texture2D = _assets.image_texture(image) if image != "" else null
	_background.texture = texture
	_missing_background.text = "" if texture != null or image == "" else InterfaceTexts.t("[ image manquante : %s ]") % image
	match transition:
		"dissolve":
			if previous != null:
				var ghost := _texture_rect(TextureRect.STRETCH_KEEP_ASPECT_COVERED)
				ghost.texture = previous
				ghost.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
				_stage.add_child(ghost)
				_stage.move_child(ghost, _background.get_index() + 1)
				var tween := create_tween()
				tween.tween_property(ghost, "modulate:a", 0.0, TRANSITION_TIME)
				tween.tween_callback(ghost.queue_free)
		"fade":
			_fade.color.a = 1.0
			create_tween().tween_property(_fade, "color:a", 0.0, TRANSITION_TIME)


func _show_character(tag: String, image: String, at: String, transition: String) -> void:
	var rect: TextureRect = _characters.get(tag)
	var is_new := rect == null
	if is_new:
		rect = _texture_rect(TextureRect.STRETCH_KEEP_ASPECT)
		_character_layer.add_child(rect)
		_characters[tag] = rect
	for child in rect.get_children():
		child.queue_free()
	var texture := _assets.image_texture(image)
	if texture == null:
		texture = _placeholder_texture()
		var label := Style.label("[ %s ]" % image, 26, Style.TEXT)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		label.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
		rect.add_child(label)
	rect.texture = texture
	var viewport_size := get_viewport_rect().size
	var ratio := minf(1.0, viewport_size.y / texture.get_size().y)
	var sprite_size := texture.get_size() * ratio
	var yalign := 0.5 if at == "truecenter" else 1.0
	rect.size = sprite_size
	rect.position = (viewport_size - sprite_size) * Vector2(XALIGN.get(at, 0.5), yalign)
	if is_new and transition != "":
		rect.modulate.a = 0.0
		create_tween().tween_property(rect, "modulate:a", 1.0, TRANSITION_TIME)


func _hide_character(tag: String, transition: String) -> void:
	var rect: TextureRect = _characters.get(tag)
	if rect == null:
		return
	_characters.erase(tag)
	if transition == "":
		rect.queue_free()
		return
	var tween := create_tween()
	tween.tween_property(rect, "modulate:a", 0.0, TRANSITION_TIME)
	tween.tween_callback(rect.queue_free)


## Redessine la scène après un retour arrière ou un chargement.
func _rebuild_stage(stage: Dictionary) -> void:
	_update_overlay(_interp.current_label())
	_show_scene(stage.scene, "")
	for tag in stage.shown:
		_show_character(tag, stage.shown[tag].image, stage.shown[tag].at, "")
	var music: String = stage.get("music", "")
	if music == "":
		_current_music = ""
		_music.stop()
	elif music != _current_music or not _music.playing:
		_play_audio({"action": "play", "channel": "music", "file": music, "fadein": 0.0, "fadeout": 0.0, "loop": true})


func _show_say(event: Dictionary) -> void:
	_update_time()
	_last_say = event
	_current_seen = _persistent.is_line_seen(event.id)
	_persistent.mark_line(event.id)
	_clear_choices()
	_dialogue.visible = true
	_speaker.text = event.name
	_speaker.visible = event.name != ""
	_speaker.add_theme_color_override("font_color", Color.from_string(event.color, Style.ACCENT))
	_text.add_theme_color_override("default_color", Color.from_string(event.what_color, Style.TEXT))
	_text.text = Style.renpy_to_bbcode(event.text)
	_kill_text_tween()
	var cps: float = _persistent.preferences.text_cps
	if _skipping or cps <= 0.0:
		_text.visible_ratio = 1.0
		_on_text_shown()
		return
	_text.visible_ratio = 0.0
	_text_tween = create_tween()
	_text_tween.tween_property(_text, "visible_ratio", 1.0, String(event.text).length() / cps)
	_text_tween.finished.connect(_on_text_shown)


func _show_menu(event: Dictionary) -> void:
	if event.prompt != null:
		_show_say(event.prompt)
	else:
		_dialogue.visible = false
	_clear_choices()
	for choice in event.choices:
		var button := Style.choice_button(choice.text)
		button.pressed.connect(_on_choice.bind(choice.index))
		_choices.add_child(button)


func _clear_choices() -> void:
	for child in _choices.get_children():
		child.visible = false
		child.queue_free()


## Carte de navigation (game/navigation.json) : comme un « call screen » de Ren'Py, sans
## boîte de dialogue ; le menu rapide reste disponible. here : lieu où l'on est, ou vide.
func _show_map(map_id: String, here: String) -> void:
	if _time_label != null:
		_time_label.visible = false
	_dialogue.visible = false
	_clear_choices()
	_map.open(map_id, here)


## Dans une pièce d'un bâtiment (carte « pieces »), la rangée des pièces reste affichée pendant
## la scène, comme l'écran permanent de Ren'Py ; ailleurs, elle disparaît.
## Texte du temps (« Jour 2 · matin »), caché sur les cartes et sans bloc « temps » dans la bible.
func _update_time() -> void:
	if _interp == null or _time_label == null:
		return
	var text := Temps.text(_time_model, _interp.store, _interp.translate_string)
	_time_label.text = text
	_time_label.visible = _in_game and text != "" and _waiting != "navigate"


func _update_overlay(label_name: String) -> void:
	_update_time()
	if _interp == null or _waiting == "navigate":
		return
	var where := _interp.overlay_for_label(label_name)
	if where.is_empty():
		if _map.overlay:
			_map.close()
	else:
		_map.show_overlay(where.map, where.lieu)


func _kill_text_tween() -> void:
	if _text_tween != null:
		_text_tween.kill()
		_text_tween = null


func _text_animating() -> bool:
	return _text_tween != null and _text_tween.is_running()


# --- Vidéo, pause, audio ------------------------------------------------------------

func _play_movie(path: String) -> void:
	# Comme Ren'Py pendant une cinématique : ni boîte de dialogue ni menu rapide.
	_dialogue.visible = false
	_quick_menu.visible = false
	_clear_choices()
	if _skipping:
		_after(SKIP_DELAY, _finish_movie)
		return
	var stream := Assets.video_stream(path)
	if stream == null:
		_show_notice(InterfaceTexts.t("Vidéo : %s\n\nLa version Godot attend « %s » (Ogg Theora).\nCliquez pour continuer.")
			% [path, Assets.ogv_path(path).trim_prefix("res://")])
		return
	_video.stream = stream
	_video.visible = true
	_video.play()


func _finish_movie() -> void:
	if _waiting != "movie":
		return
	_stop_media()
	_advance()


func _stop_media() -> void:
	_video.stop()
	_video.visible = false
	_notice_layer.visible = false
	_quick_menu.visible = _in_game and not _game_menu.visible


func _start_pause(seconds: float) -> void:
	if _skipping:
		_after(SKIP_DELAY, _advance)
	elif seconds > 0.0:
		_after(seconds, _advance)


func _play_audio(event: Dictionary) -> void:
	var channel: String = event.channel
	var player := _music if channel == "music" else _sound
	if event.action == "stop":
		if channel == "music":
			_current_music = ""
		_stop_audio(player, event.fadeout)
		return
	var path := Assets.GAME_DIR.path_join(event.file)
	var stream: AudioStream = load(path) as AudioStream if ResourceLoader.exists(path) else null
	if stream == null:
		push_warning("Audio introuvable : %s" % path)
		return
	stream.set("loop", event.loop)
	if channel == "music":
		_current_music = event.file
	var volume := _volume_db(channel)
	player.stream = stream
	player.volume_db = -40.0 if event.fadein > 0.0 else volume
	player.play()
	if event.fadein > 0.0:
		create_tween().tween_property(player, "volume_db", volume, event.fadein)


func _stop_audio(player: AudioStreamPlayer, fadeout: float) -> void:
	if fadeout <= 0.0:
		player.stop()
		return
	var tween := create_tween()
	tween.tween_property(player, "volume_db", -40.0, fadeout)
	tween.tween_callback(player.stop)


func _volume_db(channel: String) -> float:
	var key := "music_volume" if channel == "music" else "sound_volume"
	return linear_to_db(maxf(float(_persistent.preferences[key]), 0.0001))


# --- Menus -------------------------------------------------------------------------------

func _open_game_menu(target: String) -> void:
	if not _in_game or _waiting == "fatal":
		return
	if _game_menu.visible:
		_game_menu.open_page(target)
		return
	# La vignette des sauvegardes montre l'écran de jeu, pas le menu.
	_take_screenshot()
	_video.paused = true
	_quick_menu.visible = false
	_game_menu.context.history = _interp.history
	_game_menu.context.store = _interp.store
	_game_menu.show_game_menu(target)
	_persistent.save_data()


func _close_game_menu() -> void:
	_game_menu.close()
	if not _in_game:
		return
	_quick_menu.visible = _waiting != "movie"
	_video.paused = false
	_resume_modes()


## Échap / clic droit : ferme la couche du dessus, sinon ouvre le menu de jeu.
func _on_cancel() -> void:
	if _game_menu.cancel():
		return
	if _in_game and not _game_menu.visible:
		_open_game_menu("save")


func _on_menu_action(key: String, argument: Variant) -> void:
	match key:
		"start":
			_start_game()
		"return":
			_close_game_menu()
		"save":
			_save_to(argument)
		"load":
			_load_from(argument)
		"main_menu":
			_show_main_menu()
		"quit":
			_quit()
		"preference":
			if argument[0] == "language":
				_forced_language = ""
			_persistent.set_preference(argument[0], argument[1])
			_apply_preferences()


func _on_quick_action(key: String) -> void:
	match key:
		"rollback":
			_rollback()
		"history":
			_open_game_menu("history")
		"skip":
			_set_skip(not _skipping)
		"auto":
			_set_auto(not _auto)
		"save":
			_open_game_menu("save")
		"quicksave":
			_quicksave()
		"quickload":
			_quickload()
		"preferences":
			_open_game_menu("preferences")


func _refresh_quick_menu() -> void:
	_quick_menu.set_enabled("rollback", _interp.can_rollback())
	_quick_menu.set_enabled("quickload", SaveSlots.exists("quick"))


func _apply_preferences() -> void:
	_music.volume_db = _volume_db("music")
	_sound.volume_db = _volume_db("sound")
	var language := _wanted_language()
	if language != _language:
		_set_language(language)
	if DisplayServer.get_name() == "headless":
		return
	var mode: DisplayServer.WindowMode = DisplayServer.WINDOW_MODE_FULLSCREEN if _persistent.preferences.fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
	if DisplayServer.window_get_mode() != mode:
		DisplayServer.window_set_mode(mode)


# --- Langue ---------------------------------------------------------------------------

## Langue demandée par --langue, sinon la préférence. Au premier lancement (ou si la langue
## a disparu du jeu) : celle du système si le jeu la propose, sinon celle des fiches,
## comme Ren'Py (game/langues.rpy).
func _wanted_language() -> String:
	if _forced_language != "" and _langues.has(_forced_language):
		return _forced_language
	var code := str(_persistent.preferences.language)
	if not _langues.has(code):
		code = _langues.detect()
		_persistent.set_preference("language", code)
	return code


func _set_language(code: String) -> void:
	var translation = _langues.load_translation(code, _story)
	for problem in _langues.warnings:
		push_warning(problem)
	_langues.warnings.clear()
	if translation == null:
		_fatal("La traduction « %s » contient des erreurs :\n\n%s" % [code, "\n".join(_langues.errors)])
		return
	_language = code
	_game_menu.context.language = code
	_interp.set_translation(translation)
	InterfaceTexts.set_language(code)
	_quick_menu.refresh_texts()
	_game_menu.refresh_page.call_deferred()
	_redisplay()


## Réaffiche la réplique, le menu ou la carte en cours dans la nouvelle langue.
func _redisplay() -> void:
	if not _in_game or _waiting not in ["say", "menu", "navigate"]:
		return
	var event := _interp.current_event()
	if event.is_empty():
		return
	if _waiting == "navigate":
		_map.refresh()
	elif _waiting == "menu":
		_show_menu(event)
	else:
		var seen := _current_seen
		_show_say(event)
		_current_seen = seen


# --- Sauvegardes ------------------------------------------------------------------------

func _can_save() -> bool:
	return _in_game and _waiting in ["say", "menu", "navigate", "pause", "movie"]


func _take_screenshot() -> void:
	_screenshot = null
	if DisplayServer.get_name() == "headless":
		return
	var texture := get_viewport().get_texture()
	if texture != null:
		_screenshot = texture.get_image()


func _save_to(slot: String) -> void:
	if not _can_save():
		_show_toast("Impossible de sauvegarder maintenant")
		return
	var description := Style.plain_text(str(_last_say.get("text", "")))
	if not SaveSlots.write(slot, _interp.get_state(), description, _screenshot):
		_show_toast("Échec de la sauvegarde")
		return
	_show_toast("Sauvegarde rapide effectuée" if slot == "quick" else "Partie sauvegardée")
	_game_menu.refresh_page.call_deferred()
	_refresh_quick_menu()


func _quicksave() -> void:
	if _game_menu.visible or not _can_save():
		return
	_take_screenshot()
	_save_to("quick")


func _quickload() -> void:
	if _interp == null or _game_menu.visible:
		return
	if not SaveSlots.exists("quick"):
		_show_toast("Aucune sauvegarde rapide")
		return
	_load_from("quick")


func _load_from(slot: String) -> void:
	var data := SaveSlots.read(slot)
	if data.is_empty() or not _interp.set_state(data.state):
		_show_toast("Sauvegarde illisible ou incompatible avec le script actuel")
		return
	_game_menu.close()
	_in_game = true
	_stage.visible = true
	_quick_menu.visible = true
	_stop_media()
	_clear_choices()
	_map.close()
	_set_skip(false)
	_set_auto(false)
	_rebuild_stage(_interp.stage)
	_advance()
	_show_toast("Partie chargée")


# --- Lecture automatique et actions scriptées -------------------------------------------

func _parse_arguments() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg == "--autoplay":
			_autoplay = true
		elif arg.begins_with("--choices="):
			_autoplay = true
			for part in arg.trim_prefix("--choices=").split(",", false):
				_autoplay_choices.append(part.to_int())
		elif arg.begins_with("--actions="):
			_actions.append_array(Array(arg.trim_prefix("--actions=").split(",", false)))
		elif arg.begins_with("--langue="):
			_forced_language = arg.trim_prefix("--langue=")


func _schedule_autoplay() -> void:
	if not _autoplay or not _actions.is_empty() or _waiting == "fatal":
		return
	var step := _step
	get_tree().create_timer(AUTOPLAY_DELAY).timeout.connect(func() -> void:
		if step == _step:
			_autoplay_action()
	)


func _autoplay_action() -> void:
	match _waiting:
		"menu", "navigate":
			_press_choice(_autoplay_choices.pop_front() if not _autoplay_choices.is_empty() else 0)
		"say":
			_kill_text_tween()
			_advance()
		"movie":
			# Une vraie vidéo avance seule à la fin (signal finished).
			if not _video.visible:
				_finish_movie()
		"pause":
			_advance()


func _schedule_action() -> void:
	get_tree().create_timer(AUTOPLAY_DELAY).timeout.connect(_run_next_action)


func _run_next_action() -> void:
	if _actions.is_empty():
		return
	var action: String = _actions.pop_front()
	print("[action] %s" % action)
	_run_action(action)
	_schedule_action()


## Actions : start, advance, choose:RANG (choix d'un menu ou lieu d'une carte), rollback,
## skip, auto, menu:PAGE, page:PAGE, back, save:EMPLACEMENT, load:EMPLACEMENT, quicksave,
## quickload, view:N (galerie), pref:CLÉ=VALEUR, screenshot:FICHIER.png, mainmenu, wait, quit.
func _run_action(action: String) -> void:
	var key := action.get_slice(":", 0)
	var argument := action.substr(key.length() + 1)
	match key:
		"start":
			_start_game()
		"advance":
			if _text_animating():
				_continue()
			_continue()
		"choose":
			_press_choice(argument.to_int())
		"screenshot":
			var texture := get_viewport().get_texture()
			if texture != null:
				texture.get_image().save_png(argument)
		"rollback":
			_rollback()
		"skip":
			_set_skip(not _skipping)
		"auto":
			_set_auto(not _auto)
		"menu", "page":
			if _in_game:
				_open_game_menu(argument)
			else:
				_game_menu.open_page(argument)
		"back":
			_on_cancel()
		"save":
			if not _game_menu.visible:
				_take_screenshot()
			_save_to(argument)
		"load":
			_load_from(argument)
		"quicksave":
			_quicksave()
		"quickload":
			_quickload()
		"view":
			_game_menu.view_gallery_entry(argument.to_int())
		"character":
			_game_menu.select_character(argument)
		"pref":
			_persistent.set_preference(argument.get_slice("=", 0), str_to_var(argument.get_slice("=", 1)))
			_apply_preferences()
		"mainmenu":
			_show_main_menu()
		"wait":
			pass
		"quit":
			_quit()
		_:
			push_warning("Action inconnue : %s" % action)


func _press_choice(rank: int) -> void:
	if _map.visible:
		_map.press(rank)
		return
	var buttons: Array = _choices.get_children().filter(func(node: Node) -> bool: return not node.is_queued_for_deletion())
	if buttons.is_empty():
		return
	var button: Button = buttons[clampi(rank, 0, buttons.size() - 1)]
	button.pressed.emit()


# --- Messages ---------------------------------------------------------------------------

func _fatal(message: String) -> void:
	push_error(message)
	_waiting = "fatal"
	_game_menu.close()
	_stage.visible = true
	_dialogue.visible = false
	_quick_menu.visible = false
	_clear_choices()
	if _map != null:
		_map.close()
	_notice.add_theme_color_override("font_color", Color(1, 0.6, 0.55))
	_show_notice(message)


func _show_notice(text: String) -> void:
	_notice.text = text
	_notice_layer.visible = true


func _show_toast(text: String) -> void:
	_toast.text = text
	_toast.modulate.a = 1.0
	var tween := create_tween()
	tween.tween_interval(1.2)
	tween.tween_property(_toast, "modulate:a", 0.0, 0.5)


# --- Construction de l'interface --------------------------------------------------------

func _build_ui() -> void:
	_stage = Control.new()
	_add_full(self, _stage)
	var backdrop := ColorRect.new()
	backdrop.color = Color(0.05, 0.05, 0.07)
	_add_full(_stage, backdrop)
	_background = _texture_rect(TextureRect.STRETCH_KEEP_ASPECT_COVERED)
	_add_full(_stage, _background)
	_missing_background = Style.label("", 30, Color(1, 1, 1, 0.45))
	_missing_background.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_missing_background.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_add_full(_stage, _missing_background)
	_character_layer = Control.new()
	_add_full(_stage, _character_layer)
	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_add_full(_stage, _fade)

	# Boîte de dialogue : mêmes positions que l'interface Ren'Py (game/gui.rpy).
	_dialogue = Panel.new()
	_dialogue.add_theme_stylebox_override("panel", Style.gui_box("textbox.png", [0, 0, 0, 0], Style.flat_box(Color(0, 0, 0, 0.75))))
	_dialogue.set_anchors_and_offsets_preset(PRESET_BOTTOM_WIDE)
	_dialogue.offset_top = -278
	_dialogue.offset_bottom = 0
	_dialogue.visible = false
	_stage.add_child(_dialogue)
	# Nom et réplique viennent de l'histoire, traduite par l'interpréteur : pas de
	# traduction de l'interface sur ces nœuds.
	_speaker = Style.label("", Style.NAME_SIZE, Style.ACCENT)
	_speaker.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	_speaker.position = Vector2(360, 4)
	_speaker.size = Vector2(1000, 62)
	_dialogue.add_child(_speaker)
	_text = RichTextLabel.new()
	_text.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	_text.bbcode_enabled = true
	_text.scroll_active = false
	_text.position = Vector2(402, 75)
	_text.size = Vector2(1116, 190)
	for font_size in ["normal_font_size", "bold_font_size", "italics_font_size", "bold_italics_font_size"]:
		_text.add_theme_font_size_override(font_size, Style.TEXT_SIZE)
	_dialogue.add_child(_text)

	# Choix centrés sur y = 405, comme le style choice_vbox de Ren'Py.
	_choices = VBoxContainer.new()
	_choices.add_theme_constant_override("separation", 33)
	_choices.anchor_left = 0.5
	_choices.anchor_right = 0.5
	_choices.anchor_top = 405.0 / 1080.0
	_choices.anchor_bottom = 405.0 / 1080.0
	_choices.grow_horizontal = GROW_DIRECTION_BOTH
	_choices.grow_vertical = GROW_DIRECTION_BOTH
	_stage.add_child(_choices)

	_map = MapScreen.new()
	_map.chosen.connect(_on_map_choice)
	_map.cost_paid.connect(func(cost: Dictionary) -> void: _interp.apply_costs([cost]))
	_stage.add_child(_map)

	_video = VideoStreamPlayer.new()
	_video.expand = true
	_video.visible = false
	_video.finished.connect(_finish_movie)
	_add_full(_stage, _video)

	_notice_layer = CenterContainer.new()
	_notice_layer.visible = false
	_add_full(_stage, _notice_layer)
	_notice = Style.label("", 30, Style.TEXT)
	_notice.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED  # messages déjà traduits ou erreurs du script
	_notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_notice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_notice.custom_minimum_size = Vector2(1300, 0)
	_notice.add_theme_stylebox_override("normal", Style.flat_box(Color(0, 0, 0, 0.82), 48.0))
	_notice_layer.add_child(_notice)

	_skip_indicator = Style.label("Avance rapide  »", 24, Style.TEXT)
	_skip_indicator.add_theme_stylebox_override("normal", Style.flat_box(Color(0, 0, 0, 0.6), 12.0))
	_skip_indicator.position = Vector2(15, 15)
	_skip_indicator.visible = false
	_stage.add_child(_skip_indicator)

	# Temps (jour et créneau) en haut à droite, comme l'écran temps_permanent de Ren'Py.
	_time_label = Style.label("", 26, Style.TEXT)
	_time_label.add_theme_color_override("font_outline_color", Color.BLACK)
	_time_label.add_theme_constant_override("outline_size", 4)
	_time_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_time_label.anchor_left = 1.0
	_time_label.anchor_right = 1.0
	_time_label.offset_left = -900
	_time_label.offset_right = -28
	_time_label.offset_top = 18
	_time_label.offset_bottom = 60
	_time_label.modulate.a = 0.85
	_time_label.mouse_filter = MOUSE_FILTER_IGNORE
	_time_label.visible = false
	_stage.add_child(_time_label)
	_quick_menu = QuickMenu.new()
	_quick_menu.action.connect(_on_quick_action)
	_quick_menu.set_anchors_and_offsets_preset(PRESET_CENTER_BOTTOM)
	_quick_menu.offset_top = -38
	_quick_menu.offset_bottom = -2
	_quick_menu.grow_horizontal = GROW_DIRECTION_BOTH
	_quick_menu.grow_vertical = GROW_DIRECTION_BEGIN
	_quick_menu.visible = false
	_stage.add_child(_quick_menu)
	_ignore_mouse(_stage)

	_game_menu = GameMenu.new()
	_game_menu.action.connect(_on_menu_action)
	add_child(_game_menu)

	_toast = Style.label("", 26, Style.TEXT)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_toast.set_anchors_and_offsets_preset(PRESET_TOP_RIGHT)
	_toast.offset_left = -900
	_toast.offset_right = -40
	_toast.offset_top = 30
	_toast.offset_bottom = 80
	_toast.modulate.a = 0.0
	add_child(_toast)

	_music = AudioStreamPlayer.new()
	add_child(_music)
	_sound = AudioStreamPlayer.new()
	add_child(_sound)


func _add_full(parent: Node, control: Control) -> void:
	control.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	parent.add_child(control)


func _texture_rect(stretch: TextureRect.StretchMode) -> TextureRect:
	var rect := TextureRect.new()
	rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	rect.stretch_mode = stretch
	rect.mouse_filter = MOUSE_FILTER_IGNORE
	return rect


func _placeholder_texture() -> Texture2D:
	var image := Image.create_empty(480, 860, false, Image.FORMAT_RGBA8)
	image.fill(Color(0.55, 0.5, 0.65, 0.55))
	return ImageTexture.create_from_image(image)


## Seuls les boutons captent la souris dans la scène ; le reste laisse passer les clics.
func _ignore_mouse(node: Node) -> void:
	if node is Control and not (node is Button):
		node.mouse_filter = MOUSE_FILTER_IGNORE
	for child in node.get_children():
		_ignore_mouse(child)
