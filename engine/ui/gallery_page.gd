## Galerie : une vignette par entrée de game/galerie.json, verrouillée tant que son
## label n'a jamais été atteint.
extends ScrollContainer

signal view_requested(entry: Dictionary)

const Style = preload("res://engine/ui/ui_style.gd")
const THUMBNAIL_SIZE := Vector2(400, 225)

var _grid: GridContainer


func _init() -> void:
	horizontal_scroll_mode = SCROLL_MODE_DISABLED
	_grid = GridContainer.new()
	_grid.columns = 3
	_grid.mouse_filter = MOUSE_FILTER_IGNORE
	_grid.add_theme_constant_override("h_separation", 30)
	_grid.add_theme_constant_override("v_separation", 30)
	add_child(_grid)


## translate : traduction des titres (game/tl/<langue>/story/textes.rpy), sinon titres d'origine.
func refresh(entries: Array, persistent: Variant, assets: Variant, translate := Callable()) -> void:
	for child in _grid.get_children():
		_grid.remove_child(child)
		child.queue_free()
	if entries.is_empty():
		_grid.add_child(Style.label("Aucune entrée dans game/galerie.json.", Style.INTERFACE_SIZE, Style.IDLE))
		return
	for entry in entries:
		var title: String = translate.call(entry.title) if translate.is_valid() else entry.title
		_grid.add_child(_tile(entry, title, persistent.is_label_seen(entry.label), assets))


func _tile(entry: Dictionary, title_text: String, unlocked: bool, assets: Variant) -> Button:
	var button := Button.new()
	button.focus_mode = FOCUS_NONE
	button.disabled = not unlocked
	button.custom_minimum_size = Vector2(430, 310)
	var idle := Style.gui_box("button/slot_idle_background.png", Style.SLOT_BORDERS, Style.flat_box(Color(0, 0, 0, 0.35), 15.0))
	var hover := Style.gui_box("button/slot_hover_background.png", Style.SLOT_BORDERS, Style.flat_box(Color(0.7, 0.55, 1.0, 0.25), 15.0))
	for state in ["normal", "disabled"]:
		button.add_theme_stylebox_override(state, idle)
	for state in ["hover", "pressed"]:
		button.add_theme_stylebox_override(state, hover)
	button.pressed.connect(func() -> void: view_requested.emit(entry))

	var column := VBoxContainer.new()
	column.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	column.alignment = BoxContainer.ALIGNMENT_CENTER
	column.mouse_filter = MOUSE_FILTER_IGNORE
	button.add_child(column)

	var picture := TextureRect.new()
	picture.custom_minimum_size = THUMBNAIL_SIZE
	picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	picture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	picture.mouse_filter = MOUSE_FILTER_IGNORE
	if unlocked:
		picture.texture = assets.image_texture(entry.thumbnail)
	else:
		var lock := Style.label("Verrouillé", Style.INTERFACE_SIZE, Style.INSENSITIVE)
		lock.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
		lock.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		lock.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		picture.add_child(lock)
	column.add_child(picture)

	var title := Style.label(title_text if unlocked else "???", 24, Style.IDLE_SMALL if unlocked else Style.INSENSITIVE)
	title.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED  # déjà traduit par l'histoire
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(title)
	return button
