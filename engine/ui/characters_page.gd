## Page « Personnages » du menu de jeu : un onglet vertical par personnage de
## game/personnages.json (avatar rond et nom, sans limite de largeur), et la fiche du
## personnage ouvert (avatar, nom dans sa couleur, jauges, compétences et relations avec
## barre, valeur et palier). Les valeurs viennent du store de l'interpréteur, d'où une page
## réservée à la partie en cours.
extends HBoxContainer

const Style = preload("res://engine/ui/ui_style.gd")
const Characters = preload("res://engine/characters.gd")
const MapScreen = preload("res://engine/ui/map_screen.gd")
const AVATAR_SIZE := 96.0
const TAB_AVATAR_SIZE := 56.0
const TABS_WIDTH := 360.0

var selected := ""

var _tabs: VBoxContainer
var _sheet: VBoxContainer
var _characters: Array = []
var _store: Dictionary = {}
var _assets: Variant
var _translate := Callable()


func _init() -> void:
	mouse_filter = MOUSE_FILTER_IGNORE
	add_theme_constant_override("separation", 40)
	var tabs_scroll := ScrollContainer.new()
	tabs_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	tabs_scroll.custom_minimum_size.x = TABS_WIDTH
	tabs_scroll.size_flags_vertical = SIZE_EXPAND_FILL
	add_child(tabs_scroll)
	_tabs = VBoxContainer.new()
	_tabs.mouse_filter = MOUSE_FILTER_IGNORE
	_tabs.add_theme_constant_override("separation", 8)
	_tabs.size_flags_horizontal = SIZE_EXPAND_FILL
	tabs_scroll.add_child(_tabs)

	var sheet_scroll := ScrollContainer.new()
	sheet_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sheet_scroll.size_flags_horizontal = SIZE_EXPAND_FILL
	sheet_scroll.size_flags_vertical = SIZE_EXPAND_FILL
	add_child(sheet_scroll)
	_sheet = VBoxContainer.new()
	_sheet.mouse_filter = MOUSE_FILTER_IGNORE
	_sheet.add_theme_constant_override("separation", 12)
	_sheet.size_flags_horizontal = SIZE_EXPAND_FILL
	sheet_scroll.add_child(_sheet)


## store : variables de l'histoire ; translate : traduction des noms (game/tl/<langue>/story/textes.rpy).
func refresh(characters: Array, store: Dictionary, assets: Variant, translate := Callable()) -> void:
	_characters = characters
	_store = store
	_assets = assets
	_translate = translate
	_clear(_tabs)
	if characters.is_empty():
		_tabs.add_child(Style.label("Aucune fiche dans game/personnages.json.", Style.INTERFACE_SIZE, Style.IDLE))
		_clear(_sheet)
		return
	var ids: Array = characters.map(func(character: Dictionary) -> String: return character.id)
	if not ids.has(selected):
		selected = ids[0]
	for character in characters:
		_tabs.add_child(_tab(character))
	_show_sheet()


## Ouvre l'onglet d'un personnage (identifiant de la bible).
func select(character_id: String) -> void:
	if selected == character_id:
		return
	selected = character_id
	for tab in _tabs.get_children():
		if tab is Button:
			tab.set_pressed_no_signal(tab.get_meta("id") == selected)
			_tint_tab(tab)
	_show_sheet()


func _tab(character: Dictionary) -> Button:
	var button := Button.new()
	button.focus_mode = FOCUS_NONE
	button.toggle_mode = true
	button.custom_minimum_size = Vector2(TABS_WIDTH, 76)
	button.set_meta("id", character.id)
	button.set_meta("color", Color.from_string(character.couleur, Style.ACCENT))
	# Boîtes plates (comme les boutons de choix) : l'onglet ouvert est surligné, les autres transparents.
	button.add_theme_stylebox_override("normal", Style.flat_box(Color(0, 0, 0, 0), 8.0))
	button.add_theme_stylebox_override("hover", Style.flat_box(Color(0.7, 0.55, 1.0, 0.12), 8.0))
	for state in ["pressed", "hover_pressed"]:
		button.add_theme_stylebox_override(state, Style.flat_box(Color(0.7, 0.55, 1.0, 0.25), 8.0))
	button.pressed.connect(func() -> void: select(character.id))

	var row := HBoxContainer.new()
	row.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	row.offset_left = 12
	row.offset_right = -12
	row.mouse_filter = MOUSE_FILTER_IGNORE
	row.add_theme_constant_override("separation", 16)
	button.add_child(row)
	var avatar := _avatar(character, TAB_AVATAR_SIZE)
	avatar.size_flags_vertical = SIZE_SHRINK_CENTER
	row.add_child(avatar)
	var name_label := Style.label(_translated(character.nom), 30, Style.IDLE)
	name_label.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	name_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	name_label.size_flags_vertical = SIZE_EXPAND_FILL
	name_label.set_meta("name", true)
	row.add_child(name_label)
	button.set_pressed_no_signal(character.id == selected)
	_tint_tab(button)
	return button


## Le nom de l'onglet ouvert prend la couleur du personnage, les autres restent gris.
func _tint_tab(button: Button) -> void:
	for child in button.get_child(0).get_children():
		if child is Label and child.has_meta("name"):
			child.add_theme_color_override("font_color", button.get_meta("color") if button.button_pressed else Style.IDLE)


func _show_sheet() -> void:
	_clear(_sheet)
	for character in _characters:
		if character.id == selected:
			_fill_sheet(character)
			return


func _fill_sheet(character: Dictionary) -> void:
	var color := Color.from_string(character.couleur, Style.ACCENT)
	var header := HBoxContainer.new()
	header.mouse_filter = MOUSE_FILTER_IGNORE
	header.add_theme_constant_override("separation", 24)
	header.add_child(_avatar(character, AVATAR_SIZE))
	var name_label := Style.label(_translated(character.nom), Style.LABEL_SIZE, color)
	name_label.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	name_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	header.add_child(name_label)
	_sheet.add_child(header)
	for field in [["jauges", ""], ["competences", "Compétences"], ["relations", "Relations"]]:
		var gauges: Array = character[field[0]]
		if gauges.is_empty():
			continue
		if field[1] != "":
			var title := Style.label(field[1], 24, Style.IDLE_SMALL)
			var spacer := MarginContainer.new()
			spacer.add_theme_constant_override("margin_top", 12)
			spacer.mouse_filter = MOUSE_FILTER_IGNORE
			spacer.add_child(title)
			_sheet.add_child(spacer)
		for gauge in gauges:
			_sheet.add_child(_gauge_row(gauge))


func _gauge_row(gauge: Dictionary) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.mouse_filter = MOUSE_FILTER_IGNORE
	row.add_theme_constant_override("separation", 20)
	var raw = _store.get(gauge.variable, 0)
	var value: float = float(raw) if typeof(raw) in [TYPE_INT, TYPE_FLOAT] else 0.0
	var name_label := Style.label(_translated(gauge.nom), 26, Color.from_string(gauge.couleur, Style.TEXT))
	name_label.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	name_label.custom_minimum_size.x = 260
	name_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	row.add_child(name_label)
	var bar := ProgressBar.new()
	bar.show_percentage = false
	bar.min_value = gauge.min
	bar.max_value = maxf(gauge.max, gauge.min + 1.0)
	bar.value = value
	bar.custom_minimum_size = Vector2(300, 24)
	bar.size_flags_vertical = SIZE_SHRINK_CENTER
	bar.add_theme_stylebox_override("background", Style.flat_box(Color(1, 1, 1, 0.15)))
	bar.add_theme_stylebox_override("fill", Style.flat_box(Style.ACCENT))
	bar.mouse_filter = MOUSE_FILTER_IGNORE
	row.add_child(bar)
	var amount := Style.label("%s / %s" % [_number(value), _number(gauge.max)], 24, Style.IDLE_SMALL)
	amount.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	amount.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	row.add_child(amount)
	var threshold := Characters.threshold_name(gauge, value)
	if threshold != "":
		var threshold_label := Style.label(_translated(threshold), 24, Style.ACCENT)
		threshold_label.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
		threshold_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		row.add_child(threshold_label)
	return row


func _avatar(character: Dictionary, diameter: float) -> Control:
	var avatar := MapScreen.RoundIcon.new(diameter, 0.0)
	avatar.fill = Color.from_string(character.couleur, Style.ACCENT)
	if _assets != null and character.avatar != "":
		avatar.texture = _assets.image_texture(character.avatar)
	return avatar


func _translated(text: String) -> String:
	return _translate.call(text) if _translate.is_valid() else text


static func _clear(container: Control) -> void:
	for child in container.get_children():
		container.remove_child(child)
		child.queue_free()


static func _number(value: float) -> String:
	return str(int(value)) if value == floorf(value) else str(value)
