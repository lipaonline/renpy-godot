## Menu principal et menu de jeu, construits comme ceux de Ren'Py : navigation à
## gauche, page à droite (historique, sauvegarde, chargement, préférences, galerie).
extends Control

signal action(key: String, argument: Variant)

const Style = preload("res://engine/ui/ui_style.gd")
const SaveSlots = preload("res://engine/save_slots.gd")
const HistoryPage = preload("res://engine/ui/history_page.gd")
const SlotsPage = preload("res://engine/ui/slots_page.gd")
const PreferencesPage = preload("res://engine/ui/preferences_page.gd")
const GalleryPage = preload("res://engine/ui/gallery_page.gd")
const GalleryViewer = preload("res://engine/ui/gallery_viewer.gd")

const MAIN_NAVIGATION := [
	["start", "Nouvelle partie"], ["load", "Charger"], ["gallery", "Galerie"],
	["preferences", "Préférences"], ["quit", "Quitter"],
]
const GAME_NAVIGATION := [
	["history", "Historique"], ["save", "Sauvegarder"], ["load", "Charger"],
	["preferences", "Préférences"], ["main_menu", "Menu principal"], ["quit", "Quitter"],
]
const TITLES := {
	"history": "Historique", "save": "Sauvegarder", "load": "Charger",
	"preferences": "Préférences", "gallery": "Galerie",
}

## Données fournies par le lecteur : persistent, gallery, assets, history.
var context: Dictionary = {}
var in_game := false
var page := ""

var _main_layer: Control
var _game_layer: Control
var _game_name: Label
var _title: Label
var _navigation: VBoxContainer
var _navigation_mode := -1
var _content: Control
var _return_button: Button
var _pages: Dictionary = {}
var _viewer: GalleryViewer
var _confirm: Control
var _confirm_label: Label
var _confirm_callback := Callable()


func _init() -> void:
	set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	mouse_filter = MOUSE_FILTER_STOP
	visible = false
	_main_layer = _backdrop_layer("main_menu.png", "overlay/main_menu.png", Color(0.07, 0.05, 0.1))
	_game_layer = _backdrop_layer("game_menu.png", "overlay/game_menu.png", Color(0.05, 0.04, 0.08))

	_game_name = Style.label(str(ProjectSettings.get_setting("application/config/name", "")), Style.TITLE_SIZE, Style.ACCENT)
	_game_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_game_name.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	_game_name.position = Vector2(560, 780)
	_game_name.size = Vector2(1300, 240)
	add_child(_game_name)

	_title = Style.label("", Style.TITLE_SIZE, Style.ACCENT)
	_title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_title.position = Vector2(75, 0)
	_title.size = Vector2(1200, 180)
	add_child(_title)

	_navigation = VBoxContainer.new()
	_navigation.mouse_filter = MOUSE_FILTER_IGNORE
	_navigation.add_theme_constant_override("separation", 6)
	_navigation.anchor_top = 0.5
	_navigation.anchor_bottom = 0.5
	_navigation.offset_left = 60
	_navigation.offset_right = 60
	_navigation.grow_vertical = GROW_DIRECTION_BOTH
	add_child(_navigation)

	_content = Control.new()
	_content.mouse_filter = MOUSE_FILTER_IGNORE
	_content.position = Vector2(480, 180)
	_content.size = Vector2(1380, 800)
	add_child(_content)

	_return_button = Style.text_button("Retour")
	_return_button.position = Vector2(60, 990)
	_return_button.pressed.connect(cancel)
	add_child(_return_button)

	_viewer = GalleryViewer.new()
	add_child(_viewer)
	_build_confirm()


func show_main_menu() -> void:
	in_game = false
	_viewer.close()
	_confirm.visible = false
	visible = true
	_open("")


func show_game_menu(target: String) -> void:
	in_game = true
	_confirm.visible = false
	visible = true
	_open(target)


func open_page(target: String) -> void:
	_open(target)


func refresh_page() -> void:
	if visible:
		_open(page)


func close() -> void:
	_viewer.close()
	_confirm.visible = false
	visible = false
	page = ""


## Demande une confirmation (Oui / Non) avant d'appeler on_yes.
func ask(question: String, on_yes: Callable) -> void:
	_confirm_label.text = question
	_confirm_callback = on_yes
	_confirm.visible = true


func view_gallery_entry(index: int) -> void:
	var entries: Array = context.get("gallery", [])
	if index >= 0 and index < entries.size() and context.persistent.is_label_seen(entries[index].label):
		_viewer.open(entries[index], context.assets)


## Échap ou clic droit : ferme la couche du dessus. Renvoie false s'il n'y avait rien à fermer.
func cancel() -> bool:
	if _confirm.visible:
		_answer(false)
		return true
	if _viewer.close():
		return true
	if not visible:
		return false
	if in_game:
		action.emit("return", null)
		return true
	if page != "":
		_open("")
		return true
	return false


func _open(target: String) -> void:
	page = target
	var main_screen := not in_game and page == ""
	_main_layer.visible = main_screen
	_game_layer.visible = not main_screen
	_game_name.visible = main_screen
	_title.text = TITLES.get(page, "")
	_title.visible = page != ""
	_return_button.visible = not main_screen
	_update_navigation()
	for key in _pages:
		_pages[key].visible = false
	if page == "":
		return
	var node = _page(page)
	node.visible = true
	match page:
		"history":
			node.refresh(context.get("history", []))
		"save", "load":
			node.refresh(page)
		"preferences":
			node.refresh(context.persistent.preferences)
		"gallery":
			node.refresh(context.get("gallery", []), context.persistent, context.assets)


func _page(target: String) -> Control:
	var key := "slots" if target in ["save", "load"] else target
	if _pages.has(key):
		return _pages[key]
	var node: Control
	match key:
		"history":
			node = HistoryPage.new()
		"slots":
			var slots := SlotsPage.new()
			slots.slot_chosen.connect(_on_slot)
			node = slots
		"preferences":
			var preferences := PreferencesPage.new()
			preferences.changed.connect(func(pref_key: String, value: Variant) -> void: action.emit("preference", [pref_key, value]))
			node = preferences
		"gallery":
			var gallery := GalleryPage.new()
			gallery.view_requested.connect(func(entry: Dictionary) -> void: _viewer.open(entry, context.assets))
			node = gallery
	node.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	_content.add_child(node)
	_pages[key] = node
	return node


func _update_navigation() -> void:
	var mode := 1 if in_game else 0
	if mode != _navigation_mode:
		_navigation_mode = mode
		for child in _navigation.get_children():
			_navigation.remove_child(child)
			child.queue_free()
		for item in (GAME_NAVIGATION if in_game else MAIN_NAVIGATION):
			var button := Style.text_button(item[1])
			button.toggle_mode = true
			button.set_meta("key", item[0])
			button.pressed.connect(_on_navigation.bind(item[0]))
			_navigation.add_child(button)
	for button in _navigation.get_children():
		button.set_pressed_no_signal(button.get_meta("key") == page)


func _on_navigation(key: String) -> void:
	match key:
		"history", "save", "load", "preferences", "gallery":
			_open(key)
		"start":
			action.emit("start", null)
		"main_menu":
			ask("Revenir au menu principal ?\nLa progression non sauvegardée sera perdue.",
				func() -> void: action.emit("main_menu", null))
		"quit":
			ask("Quitter le jeu ?", func() -> void: action.emit("quit", null))


func _on_slot(slot: String) -> void:
	if page == "save":
		if SaveSlots.exists(slot):
			ask("Remplacer cette sauvegarde ?", func() -> void: action.emit("save", slot))
		else:
			action.emit("save", slot)
	elif in_game:
		ask("Charger cette partie ?\nLa progression non sauvegardée sera perdue.",
			func() -> void: action.emit("load", slot))
	else:
		action.emit("load", slot)


func _answer(accepted: bool) -> void:
	_confirm.visible = false
	_update_navigation()
	if accepted and _confirm_callback.is_valid():
		_confirm_callback.call()


func _backdrop_layer(background: String, overlay: String, fallback: Color) -> Control:
	var layer := Control.new()
	layer.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	layer.mouse_filter = MOUSE_FILTER_IGNORE
	layer.add_child(Style.gui_backdrop(background, fallback))
	layer.add_child(Style.gui_backdrop(overlay, Color(0, 0, 0, 0)))
	add_child(layer)
	return layer


func _build_confirm() -> void:
	_confirm = Control.new()
	_confirm.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	_confirm.mouse_filter = MOUSE_FILTER_STOP
	_confirm.visible = false
	add_child(_confirm)
	_confirm.add_child(Style.gui_backdrop("overlay/confirm.png", Color(0, 0, 0, 0.6)))
	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	center.mouse_filter = MOUSE_FILTER_IGNORE
	_confirm.add_child(center)
	var frame := PanelContainer.new()
	frame.add_theme_stylebox_override("panel", Style.flat_box(Color(0.04, 0.03, 0.07, 0.95), 60.0))
	center.add_child(frame)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 45)
	frame.add_child(column)
	_confirm_label = Style.label("", Style.INTERFACE_SIZE, Style.TEXT)
	_confirm_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_confirm_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_confirm_label.custom_minimum_size.x = 900
	column.add_child(_confirm_label)
	var buttons := HBoxContainer.new()
	buttons.alignment = BoxContainer.ALIGNMENT_CENTER
	buttons.add_theme_constant_override("separation", 150)
	column.add_child(buttons)
	for answer in [["Oui", true], ["Non", false]]:
		var button := Style.text_button(answer[0])
		button.pressed.connect(_answer.bind(answer[1]))
		buttons.add_child(button)
