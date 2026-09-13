## Menu rapide en bas de l'écran, comme celui de Ren'Py.
extends HBoxContainer

signal action(key: String)

const Style = preload("res://engine/ui/ui_style.gd")
const ITEMS := [
	["rollback", "Retour"], ["history", "Historique"], ["skip", "Passer"], ["auto", "Auto"],
	["save", "Sauvegarder"], ["quicksave", "Sauv. rapide"], ["quickload", "Charg. rapide"],
	["preferences", "Préférences"],
]
const TOGGLES := ["skip", "auto"]

var _buttons: Dictionary = {}


func _init() -> void:
	alignment = BoxContainer.ALIGNMENT_CENTER
	mouse_filter = MOUSE_FILTER_IGNORE
	add_theme_constant_override("separation", 30)
	for item in ITEMS:
		var button := Style.text_button(item[1], Style.QUICK_SIZE)
		button.toggle_mode = item[0] in TOGGLES
		button.pressed.connect(_on_pressed.bind(item[0]))
		add_child(button)
		_buttons[item[0]] = button


func set_toggle(key: String, on: bool) -> void:
	_buttons[key].set_pressed_no_signal(on)


func set_enabled(key: String, enabled: bool) -> void:
	_buttons[key].disabled = not enabled


func _on_pressed(key: String) -> void:
	action.emit(key)
