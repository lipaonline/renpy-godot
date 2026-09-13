## Styles de l'interface, repris de l'interface générée par Ren'Py (game/gui.rpy)
## pour que les deux versions du jeu se ressemblent.
extends RefCounted

const Assets = preload("res://engine/assets.gd")

const ACCENT := Color("#b48cff")
const IDLE := Color("#888888")
const IDLE_SMALL := Color("#aaaaaa")
const HOVER := Color("#d2baff")
const SELECTED := Color("#ffffff")
const INSENSITIVE := Color("#8888887f")
const TEXT := Color("#ffffff")
const TEXT_SIZE := 33
const NAME_SIZE := 45
const INTERFACE_SIZE := 33
const LABEL_SIZE := 36
const TITLE_SIZE := 75
const QUICK_SIZE := 24
const CHOICE_BORDERS := [150, 8, 150, 8]
const SLOT_BORDERS := [15, 15, 15, 15]


## Bouton texte sans fond (navigation, menu rapide), comme les boutons Ren'Py.
static func text_button(text: String, font_size := INTERFACE_SIZE) -> Button:
	var button := Button.new()
	button.text = text
	button.flat = true
	button.alignment = HORIZONTAL_ALIGNMENT_LEFT
	button.focus_mode = Control.FOCUS_NONE
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.add_theme_font_size_override("font_size", font_size)
	button.add_theme_color_override("font_color", IDLE)
	button.add_theme_color_override("font_focus_color", IDLE)
	button.add_theme_color_override("font_hover_color", HOVER)
	button.add_theme_color_override("font_pressed_color", SELECTED)
	button.add_theme_color_override("font_hover_pressed_color", SELECTED)
	button.add_theme_color_override("font_disabled_color", INSENSITIVE)
	return button


## Bouton de choix de menu, avec les images de game/gui/button. Son texte vient de
## l'histoire, déjà traduit par l'interpréteur : pas de traduction de l'interface.
static func choice_button(text: String) -> Button:
	var button := Button.new()
	button.text = text
	button.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	button.focus_mode = Control.FOCUS_NONE
	button.custom_minimum_size = Vector2(1185, 0)
	button.add_theme_font_size_override("font_size", TEXT_SIZE)
	button.add_theme_color_override("font_color", IDLE)
	button.add_theme_color_override("font_hover_color", SELECTED)
	button.add_theme_color_override("font_pressed_color", SELECTED)
	var idle := gui_box("button/choice_idle_background.png", CHOICE_BORDERS, flat_box(Color(0, 0, 0, 0.6), 8.0))
	var hover := gui_box("button/choice_hover_background.png", CHOICE_BORDERS, flat_box(Color(0.3, 0.2, 0.45, 0.9), 8.0))
	button.add_theme_stylebox_override("normal", idle)
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_stylebox_override("pressed", hover)
	return button


static func label(text: String, font_size := INTERFACE_SIZE, color := TEXT) -> Label:
	var result := Label.new()
	result.text = text
	result.mouse_filter = Control.MOUSE_FILTER_IGNORE
	result.add_theme_font_size_override("font_size", font_size)
	result.add_theme_color_override("font_color", color)
	return result


static func flat_box(color: Color, margin := 0.0) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = color
	box.set_content_margin_all(margin)
	return box


## Cadre tiré d'une image de game/gui, découpé comme les Borders de Ren'Py.
static func gui_box(file: String, borders: Array, fallback: StyleBox) -> StyleBox:
	var texture := Assets.load_texture(Assets.GUI_DIR.path_join(file))
	if texture == null:
		return fallback
	var box := StyleBoxTexture.new()
	box.texture = texture
	box.texture_margin_left = borders[0]
	box.texture_margin_top = borders[1]
	box.texture_margin_right = borders[2]
	box.texture_margin_bottom = borders[3]
	box.content_margin_left = borders[0]
	box.content_margin_top = borders[1]
	box.content_margin_right = borders[2]
	box.content_margin_bottom = borders[3]
	return box


## Image plein écran de game/gui, ou couleur unie si elle manque.
static func gui_backdrop(file: String, fallback: Color) -> Control:
	var texture := Assets.load_texture(Assets.GUI_DIR.path_join(file))
	var node: Control
	if texture != null:
		var rect := TextureRect.new()
		rect.texture = texture
		rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		rect.stretch_mode = TextureRect.STRETCH_SCALE
		node = rect
	else:
		var color_rect := ColorRect.new()
		color_rect.color = fallback
		node = color_rect
	node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	node.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return node


static func slider(min_value: float, max_value: float, step: float) -> HSlider:
	var result := HSlider.new()
	result.min_value = min_value
	result.max_value = max_value
	result.step = step
	result.focus_mode = Control.FOCUS_NONE
	result.custom_minimum_size = Vector2(525, 40)
	return result


## Balises Ren'Py ({b}, {i}, {color=…}) vers BBCode Godot ; les autres sont retirées.
static func renpy_to_bbcode(text: String) -> String:
	var result := text.replace("{{", "\u0001").replace("[", "[lb]")
	result = RegEx.create_from_string("\\{(/?)(b|i|u|s|color)(=[^}]*)?\\}").sub(result, "[$1$2$3]", true)
	result = RegEx.create_from_string("\\{[^}]*\\}").sub(result, "", true)
	return result.replace("\u0001", "{")


## Texte sans balises Ren'Py (description des sauvegardes).
static func plain_text(text: String) -> String:
	var result := text.replace("{{", "\u0001")
	result = RegEx.create_from_string("\\{[^}]*\\}").sub(result, "", true)
	return result.replace("\u0001", "{")
