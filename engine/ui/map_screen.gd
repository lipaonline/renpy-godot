## Navigation (game/navigation.json), deux affichages :
## - « carte » : image de fond, un bouton par lieu visible placé sur l'image, avec dessous les
##   personnages présents ;
## - « pieces » : rangée d'icônes rondes des pièces en bas à gauche de l'écran, par-dessus la
##   scène en cours ou l'image de la carte ; l'avatar de chaque personnage présent est posé sur
##   l'icône de sa pièce, le nom de la pièce apparaît au survol, et une icône ronde de la carte
##   parente permet de sortir.
## Le lieu où l'on est (« vous êtes ici ») est mis en évidence. Un lieu qui ouvre une sous-carte
## l'affiche sur place ; choisir un lieu qui joue une scène émet chosen(label).
## Même disposition que l'écran « carte » de Ren'Py (game/navigation.rpy).
extends Control

signal chosen(label: String)
## Déplacement payé (entrée « temps » d'un lieu cliqué), avant sa scène ou sa sous-carte.
signal cost_paid(cost: Dictionary)

const Style = preload("res://engine/ui/ui_style.gd")
const Texts = preload("res://engine/ui/traductions_interface.gd")

const ICON_DIAMETER := 118.0
const AVATAR_DIAMETER := 44.0
const MAP_AVATAR_DIAMETER := 64.0
## Bas de la rangée des pièces : au-dessus du menu rapide quand elle attend un choix, au-dessus
## de la boîte de dialogue quand elle reste affichée pendant une scène.
const ROW_BOTTOM := 1030.0
const OVERLAY_BOTTOM := 790.0
const HERE_COLOR := Color("#4d3373b3")

## map_view de l'interpréteur : carte → {titre, affichage, image, parent, exit_text, lieux}.
var view: Callable
var assets: Variant
## Carte affichée (une sous-carte peut avoir été ouverte depuis la carte demandée), et lieu où l'on est.
var current := ""
var here := ""
## Rangée affichée pendant une scène (informative, sans clic) plutôt qu'en attente d'un choix.
var overlay := false

var _backdrop: ColorRect
var _background: TextureRect
var _missing: Label
var _title: Label
var _exit: Button
var _layer: Control
var _row: HBoxContainer
var _hovered: Label
var _buttons: Array = []
var _exit_icon: Button
var _breadcrumb: HBoxContainer
var _shortcuts: VBoxContainer
var _shortcut_buttons: Array = []


## Image recadrée en rond avec un anneau, comme AlphaMask côté Ren'Py.
class RoundIcon extends Control:
	var texture: Texture2D
	var ring := Color.WHITE
	var fill := Color("#3a3550")
	var diameter := 118.0
	var ring_width := 5.0

	func _init(size_px: float, ring_px: float) -> void:
		diameter = size_px
		ring_width = ring_px
		custom_minimum_size = Vector2(size_px, size_px)
		mouse_filter = MOUSE_FILTER_IGNORE

	func _draw() -> void:
		var center := Vector2(diameter, diameter) / 2.0
		if ring_width > 0.0:
			draw_circle(center, diameter / 2.0, ring)
		var radius := diameter / 2.0 - ring_width
		if texture == null:
			draw_circle(center, radius, fill)
			return
		# Polygone texturé : la texture recouvre le disque (recadrage centré, comme fit="cover").
		var texture_size := texture.get_size()
		var side := minf(texture_size.x, texture_size.y)
		var offset := (texture_size - Vector2(side, side)) / 2.0
		var points := PackedVector2Array()
		var uvs := PackedVector2Array()
		for i in 48:
			var angle := TAU * i / 48.0
			var direction := Vector2(cos(angle), sin(angle))
			points.append(center + direction * radius)
			uvs.append((offset + (Vector2(0.5, 0.5) + direction * 0.5) * side) / texture_size)
		draw_colored_polygon(points, Color.WHITE, uvs, texture)


func _init() -> void:
	set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	mouse_filter = MOUSE_FILTER_IGNORE
	visible = false
	_backdrop = ColorRect.new()
	_backdrop.color = Color(0.05, 0.05, 0.07)
	_add_full(_backdrop)
	_background = TextureRect.new()
	_background.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_background.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_add_full(_background)
	_missing = Style.label("", 30, Color(1, 1, 1, 0.45))
	_missing.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_missing.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_add_full(_missing)
	_layer = Control.new()
	_add_full(_layer)
	# Titre de la carte et noms des lieux viennent de l'histoire, déjà traduits : pas de
	# traduction automatique de l'interface sur ces nœuds.
	_title = Style.label("", Style.NAME_SIZE, Style.ACCENT)
	_title.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	_title.position = Vector2(75, 40)
	_title.size = Vector2(1400, 60)
	add_child(_title)
	_exit = Style.text_button("")
	_exit.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	_exit.position = Vector2(60, 990)
	_exit.pressed.connect(_on_exit)
	add_child(_exit)

	_row = HBoxContainer.new()
	_row.mouse_filter = MOUSE_FILTER_IGNORE
	_row.add_theme_constant_override("separation", 22)
	_row.anchor_top = ROW_BOTTOM / 1080.0
	_row.anchor_bottom = ROW_BOTTOM / 1080.0
	_row.offset_left = 50
	_row.grow_vertical = GROW_DIRECTION_BEGIN
	add_child(_row)
	# Fil d'Ariane : cartes parentes cliquables (plusieurs niveaux d'un coup), puis la carte affichée.
	_breadcrumb = HBoxContainer.new()
	_breadcrumb.mouse_filter = MOUSE_FILTER_IGNORE
	_breadcrumb.add_theme_constant_override("separation", 8)
	add_child(_breadcrumb)
	# Raccourcis : lieux proposés depuis toutes les cartes, en bas à droite.
	_shortcuts = VBoxContainer.new()
	_shortcuts.mouse_filter = MOUSE_FILTER_IGNORE
	_shortcuts.alignment = BoxContainer.ALIGNMENT_END
	_shortcuts.add_theme_constant_override("separation", 8)
	_shortcuts.anchor_left = 1.0
	_shortcuts.anchor_right = 1.0
	_shortcuts.anchor_top = 1.0
	_shortcuts.anchor_bottom = 1.0
	_shortcuts.offset_left = -700
	_shortcuts.offset_right = -60
	_shortcuts.offset_top = -500
	_shortcuts.offset_bottom = -90
	add_child(_shortcuts)
	_hovered = Style.label("", 28, Style.TEXT)
	_hovered.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	_hovered.add_theme_color_override("font_outline_color", Color.BLACK)
	_hovered.add_theme_constant_override("outline_size", 4)
	_hovered.position = Vector2(50, 860)
	_hovered.size = Vector2(900, 40)
	add_child(_hovered)


## Affiche une carte en attente d'un choix ; where : lieu où l'on est (mis en évidence), ou vide.
func open(map_id: String, where := "") -> void:
	current = map_id
	here = where
	overlay = false
	refresh()


## Garde la rangée des pièces d'un bâtiment affichée pendant une scène jouée dans une de ses
## pièces : mêmes icônes et avatars, mais sans clic, au-dessus de la boîte de dialogue.
func show_overlay(map_id: String, where: String) -> void:
	current = map_id
	here = where
	overlay = true
	refresh()


## Redessine la carte affichée (changement de langue, retour à la carte).
func refresh() -> void:
	if current == "" or not view.is_valid():
		return
	var data: Dictionary = view.call(current)
	if data.is_empty():
		close()
		return
	visible = true
	var rooms: bool = data.affichage == "pieces"
	if overlay and not rooms:
		close()
		return
	var texture: Texture2D = null if overlay else (assets.image_texture(data.image) if assets != null and data.image != "" else null)
	_background.texture = texture
	# La rangée des pièces sans image de carte laisse voir la scène en cours.
	_backdrop.visible = not rooms or texture != null
	_missing.text = "" if texture != null or data.image == "" or rooms else Texts.t("[ image manquante : %s ]") % data.image
	_title.text = data.titre
	_title.visible = not rooms
	_exit.text = data.exit_text
	_exit.visible = not rooms and data.exit_text != ""
	_row.anchor_top = (OVERLAY_BOTTOM if overlay else ROW_BOTTOM) / 1080.0
	_row.anchor_bottom = _row.anchor_top
	_row.modulate = Color(1, 1, 1, 0.75) if overlay else Color.WHITE
	_exit.set_meta("parent", data.parent)
	_hovered.text = ""
	for container in [_layer, _row]:
		for child in container.get_children():
			container.remove_child(child)
			child.queue_free()
	_buttons.clear()
	_exit_icon = null
	_shortcut_buttons.clear()
	for container in [_breadcrumb, _shortcuts]:
		for child in container.get_children():
			container.remove_child(child)
			child.queue_free()
	_breadcrumb.visible = not overlay and not data.chemin.is_empty()
	_breadcrumb.position = Vector2(50, 40) if rooms else Vector2(75, 110)
	if _breadcrumb.visible:
		for ancestor in data.chemin:
			var link := Style.text_button(ancestor.titre, 24)
			link.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
			link.pressed.connect(func() -> void: open(ancestor.id, here))
			_breadcrumb.add_child(link)
			_breadcrumb.add_child(Style.label("›", 24, Color(1, 1, 1, 0.6)))
		var current_title := Style.label(data.titre, 24, Style.TEXT)
		current_title.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
		_breadcrumb.add_child(current_title)
	_shortcuts.visible = not overlay
	if not overlay:
		for entry in data.raccourcis:
			var button := _place_button(entry.nom, false)
			button.size_flags_horizontal = SIZE_SHRINK_END
			button.pressed.connect(_on_place.bind(entry))
			_shortcuts.add_child(button)
			_shortcut_buttons.append(button)
	_row.visible = rooms
	if rooms:
		for entry in data.lieux:
			_row.add_child(_room_icon(entry))
		if data.exit_text != "":
			var parent_view: Dictionary = view.call(data.parent)
			_exit_icon = _icon_button(data.exit_text, parent_view.get("image", ""), false, [])
			var arrow := Style.label("←", 44, Style.TEXT)
			arrow.add_theme_color_override("font_outline_color", Color.BLACK)
			arrow.add_theme_constant_override("outline_size", 4)
			arrow.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
			arrow.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			arrow.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			_exit_icon.add_child(arrow)
			_exit_icon.pressed.connect(_on_exit)
			_row.add_child(_exit_icon)
	else:
		for entry in data.lieux:
			_layer.add_child(_hotspot(entry))


## Ferme la carte ; renvoie false si elle était déjà fermée.
func close() -> bool:
	if not visible:
		return false
	visible = false
	current = ""
	here = ""
	overlay = false
	return true


## Boutons cliquables dans l'ordre (lieux, puis retour) : lecture automatique et tests.
func buttons() -> Array:
	if overlay:
		return []
	var result := _buttons.duplicate()
	if _exit_icon != null:
		result.append(_exit_icon)
	elif _exit.visible:
		result.append(_exit)
	result.append_array(_shortcut_buttons)
	return result


## Clique le bouton de rang donné (borné), pour --choices et --actions.
func press(rank: int) -> void:
	var all := buttons()
	if not all.is_empty():
		all[clampi(rank, 0, all.size() - 1)].pressed.emit()


# --- Affichage « carte » ------------------------------------------------------------------

## Lieu centré sur sa position (en pourcentage de la carte) : le bouton porte le nom seul,
## les personnages présents sont listés dessous.
func _hotspot(entry: Dictionary) -> Control:
	var box := VBoxContainer.new()
	box.mouse_filter = MOUSE_FILTER_IGNORE
	box.alignment = BoxContainer.ALIGNMENT_CENTER
	box.add_theme_constant_override("separation", 6)
	box.anchor_left = entry.x / 100.0
	box.anchor_right = entry.x / 100.0
	box.anchor_top = entry.y / 100.0
	box.anchor_bottom = entry.y / 100.0
	box.grow_horizontal = GROW_DIRECTION_BOTH
	box.grow_vertical = GROW_DIRECTION_BOTH
	var button := _place_button(entry.nom, entry.lieu == here)
	button.size_flags_horizontal = SIZE_SHRINK_CENTER
	button.pressed.connect(_on_place.bind(entry))
	box.add_child(button)
	_buttons.append(button)
	if not entry.presents.is_empty():
		var presents := _presents_row(entry.presents, MAP_AVATAR_DIAMETER)
		presents.size_flags_horizontal = SIZE_SHRINK_CENTER
		box.add_child(presents)
	return box


func _place_button(text: String, is_here: bool) -> Button:
	var button := Button.new()
	button.text = text
	button.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	button.focus_mode = FOCUS_NONE
	button.mouse_default_cursor_shape = CURSOR_POINTING_HAND
	button.add_theme_font_size_override("font_size", 30)
	# Mêmes couleurs et marges que les styles navigation_lieu de Ren'Py : lisible sur toute carte.
	button.add_theme_color_override("font_color", Style.ACCENT if is_here else Color("#dddddd"))
	button.add_theme_color_override("font_hover_color", Style.SELECTED)
	button.add_theme_color_override("font_pressed_color", Style.SELECTED)
	button.add_theme_stylebox_override("normal", _box(HERE_COLOR if is_here else Color("#000000b3"), 28, 12))
	button.add_theme_stylebox_override("hover", _box(Color("#4d3373e6"), 28, 12))
	button.add_theme_stylebox_override("pressed", _box(Color("#4d3373e6"), 28, 12))
	return button


# --- Affichage « pieces » -----------------------------------------------------------------

## Icône ronde d'une pièce, avatars des personnages présents posés en bas, nom au survol.
func _room_icon(entry: Dictionary) -> Button:
	var button := _icon_button(entry.nom, entry.icone, entry.lieu == here, entry.presents)
	button.pressed.connect(_on_place.bind(entry))
	_buttons.append(button)
	return button


## Bouton rond : anneau blanc (violet pour la pièce où l'on est), image recadrée, avatars.
func _icon_button(name_text: String, image: String, is_here: bool, presents: Array) -> Button:
	var button := Button.new()
	button.focus_mode = FOCUS_NONE
	button.mouse_default_cursor_shape = CURSOR_POINTING_HAND
	button.custom_minimum_size = Vector2(ICON_DIAMETER, ICON_DIAMETER)
	button.tooltip_text = name_text
	# Pendant une scène, la rangée informe sans capter les clics (qui font avancer le texte).
	button.mouse_filter = MOUSE_FILTER_IGNORE if overlay else MOUSE_FILTER_STOP
	for state in ["normal", "hover", "pressed"]:
		button.add_theme_stylebox_override(state, StyleBoxEmpty.new())
	button.mouse_entered.connect(func() -> void: _hovered.text = name_text)
	button.mouse_exited.connect(func() -> void: _hovered.text = "")
	var icon := RoundIcon.new(ICON_DIAMETER, 5.0)
	icon.ring = Style.ACCENT if is_here else Color.WHITE
	icon.texture = assets.image_texture(image) if assets != null and image != "" else null
	icon.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	button.add_child(icon)
	if not presents.is_empty():
		var row := _presents_row(presents, AVATAR_DIAMETER)
		row.anchor_left = 0.5
		row.anchor_right = 0.5
		row.anchor_top = 1.0
		row.anchor_bottom = 1.0
		row.grow_horizontal = GROW_DIRECTION_BOTH
		row.grow_vertical = GROW_DIRECTION_BEGIN
		button.add_child(row)
	return button


# --- Personnages présents ---------------------------------------------------------------

## Avatars ronds (ou, sans avatar, disque à la couleur du personnage sur une carte : nom en couleur)
## des personnages présents, en ligne.
func _presents_row(presents: Array, diameter: float) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.mouse_filter = MOUSE_FILTER_IGNORE
	row.add_theme_constant_override("separation", 2)
	for character in presents:
		var texture: Texture2D = assets.image_texture(character.avatar) if assets != null and character.avatar != "" else null
		if texture != null or diameter == AVATAR_DIAMETER:
			var avatar := RoundIcon.new(diameter, 0.0)
			avatar.texture = texture
			avatar.fill = Color.from_string(character.couleur, Style.ACCENT)
			avatar.tooltip_text = character.nom
			row.add_child(avatar)
		else:
			var badge := Style.label("● " + character.nom, 22, Color.from_string(character.couleur, Style.ACCENT))
			badge.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
			badge.add_theme_stylebox_override("normal", Style.flat_box(Color(0, 0, 0, 0.6), 4.0))
			row.add_child(badge)
	return row


# --- Actions et utilitaires ----------------------------------------------------------------

func _on_place(entry: Dictionary) -> void:
	if not visible:
		return
	# Le déplacement se paie au clic, avant la scène ou la sous-carte (comme Ren'Py).
	var cost: Dictionary = entry.get("temps", {})
	if not cost.is_empty():
		cost_paid.emit(cost)
	if entry.label != "":
		chosen.emit(entry.label)
	elif entry.carte != "":
		open(entry.carte, here)


func _on_exit() -> void:
	var parent: String = _exit.get_meta("parent", "")
	if visible and parent != "":
		open(parent, here)


static func _box(color: Color, horizontal: float, vertical: float) -> StyleBoxFlat:
	var box := Style.flat_box(color)
	box.content_margin_left = horizontal
	box.content_margin_right = horizontal
	box.content_margin_top = vertical
	box.content_margin_bottom = vertical
	box.set_corner_radius_all(6)
	return box


func _add_full(control: Control) -> void:
	control.mouse_filter = MOUSE_FILTER_IGNORE
	control.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	add_child(control)
