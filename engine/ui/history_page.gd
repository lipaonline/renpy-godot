## Historique des répliques, les plus récentes en bas (écran « history » de Ren'Py).
extends ScrollContainer

const Style = preload("res://engine/ui/ui_style.gd")

var _list: VBoxContainer


func _init() -> void:
	horizontal_scroll_mode = SCROLL_MODE_DISABLED
	_list = VBoxContainer.new()
	_list.size_flags_horizontal = SIZE_EXPAND_FILL
	_list.mouse_filter = MOUSE_FILTER_IGNORE
	_list.add_theme_constant_override("separation", 30)
	add_child(_list)


func refresh(history: Array) -> void:
	for child in _list.get_children():
		_list.remove_child(child)
		child.queue_free()
	if history.is_empty():
		_list.add_child(Style.label("L'historique est vide.", Style.INTERFACE_SIZE, Style.IDLE))
		return
	for entry in history:
		var row := HBoxContainer.new()
		row.mouse_filter = MOUSE_FILTER_IGNORE
		row.add_theme_constant_override("separation", 22)
		# Répliques de l'histoire : traduites par l'interpréteur, pas par l'interface.
		var speaker := Style.label(entry.name, Style.TEXT_SIZE, Color.from_string(entry.color, Style.ACCENT))
		speaker.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
		speaker.custom_minimum_size.x = 233
		speaker.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		speaker.vertical_alignment = VERTICAL_ALIGNMENT_TOP
		row.add_child(speaker)
		var text := RichTextLabel.new()
		text.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
		text.bbcode_enabled = true
		text.fit_content = true
		text.scroll_active = false
		text.mouse_filter = MOUSE_FILTER_IGNORE
		text.custom_minimum_size.x = 1110
		for font_size in ["normal_font_size", "bold_font_size", "italics_font_size", "bold_italics_font_size"]:
			text.add_theme_font_size_override(font_size, Style.TEXT_SIZE)
		text.text = Style.renpy_to_bbcode(entry.text)
		row.add_child(text)
		_list.add_child(row)
	_scroll_to_end.call_deferred()


func _scroll_to_end() -> void:
	await get_tree().process_frame
	scroll_vertical = int(get_v_scroll_bar().max_value)
