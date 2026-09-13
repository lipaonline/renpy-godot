## Grille d'emplacements de sauvegarde (3 × 2 par page, comme Ren'Py) avec vignettes.
## La page « Q » contient la sauvegarde rapide (chargement seulement).
extends VBoxContainer

signal slot_chosen(slot: String)

const Style = preload("res://engine/ui/ui_style.gd")
const SaveSlots = preload("res://engine/save_slots.gd")
const PAGES := ["quick", "1", "2", "3", "4", "5"]
const COLUMNS := 3
const ROWS := 2

var mode := "load"
var _page := "1"
var _grid: GridContainer
var _pager: HBoxContainer


func _init() -> void:
	mouse_filter = MOUSE_FILTER_IGNORE
	add_theme_constant_override("separation", 40)
	_grid = GridContainer.new()
	_grid.columns = COLUMNS
	_grid.mouse_filter = MOUSE_FILTER_IGNORE
	_grid.add_theme_constant_override("h_separation", 30)
	_grid.add_theme_constant_override("v_separation", 30)
	add_child(_grid)
	_pager = HBoxContainer.new()
	_pager.alignment = BoxContainer.ALIGNMENT_CENTER
	_pager.mouse_filter = MOUSE_FILTER_IGNORE
	_pager.add_theme_constant_override("separation", 36)
	add_child(_pager)
	for page in PAGES:
		var button := Style.text_button("Q" if page == "quick" else page)
		button.toggle_mode = true
		button.pressed.connect(_set_page.bind(page))
		_pager.add_child(button)


## mode : « save » ou « load ».
func refresh(new_mode: String) -> void:
	mode = new_mode
	if mode == "save" and _page == "quick":
		_page = "1"
	_rebuild()


func _set_page(page: String) -> void:
	_page = page
	_rebuild()


func _rebuild() -> void:
	for i in _pager.get_child_count():
		var button: Button = _pager.get_child(i)
		button.set_pressed_no_signal(PAGES[i] == _page)
		button.disabled = mode == "save" and PAGES[i] == "quick"
	for child in _grid.get_children():
		_grid.remove_child(child)
		child.queue_free()
	var slots: Array = []
	if _page == "quick":
		slots.append("quick")
	else:
		for i in COLUMNS * ROWS:
			slots.append("%s-%d" % [_page, i + 1])
	for slot in slots:
		_grid.add_child(_slot_button(slot))


func _slot_button(slot: String) -> Button:
	var info := SaveSlots.read(slot)
	var button := Button.new()
	button.focus_mode = FOCUS_NONE
	button.custom_minimum_size = Vector2(414, 309)
	button.disabled = mode == "load" and info.is_empty()
	var idle := Style.gui_box("button/slot_idle_background.png", Style.SLOT_BORDERS, Style.flat_box(Color(0, 0, 0, 0.35), 15.0))
	var hover := Style.gui_box("button/slot_hover_background.png", Style.SLOT_BORDERS, Style.flat_box(Color(0.7, 0.55, 1.0, 0.25), 15.0))
	for state in ["normal", "disabled"]:
		button.add_theme_stylebox_override(state, idle)
	for state in ["hover", "pressed"]:
		button.add_theme_stylebox_override(state, hover)
	button.pressed.connect(func() -> void: slot_chosen.emit(slot))

	var column := VBoxContainer.new()
	column.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	column.alignment = BoxContainer.ALIGNMENT_CENTER
	column.mouse_filter = MOUSE_FILTER_IGNORE
	column.add_theme_constant_override("separation", 4)
	button.add_child(column)

	var picture := TextureRect.new()
	picture.custom_minimum_size = Vector2(384, 216)
	picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	picture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	picture.mouse_filter = MOUSE_FILTER_IGNORE
	picture.texture = SaveSlots.thumbnail(slot) if not info.is_empty() else null
	column.add_child(picture)

	var slot_title := "Sauvegarde rapide" if slot == "quick" else "Emplacement %s" % slot.get_slice("-", 1)
	var heading := Style.label("%s — %s" % [slot_title, info.date] if not info.is_empty() else "%s — vide" % slot_title, 22, Style.IDLE_SMALL)
	heading.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(heading)
	var description := Style.label(str(info.get("description", "")), 20, Style.TEXT)
	description.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	description.custom_minimum_size.x = 384
	description.clip_text = true
	description.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	column.add_child(description)
	return button
