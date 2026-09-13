## Préférences : vitesse du texte, avance automatique, avance rapide, affichage et volumes.
extends GridContainer

signal changed(key: String, value: Variant)

const Style = preload("res://engine/ui/ui_style.gd")
## Position la plus à droite du curseur de vitesse : texte instantané (text_cps = 0, défaut Ren'Py).
const INSTANT_CPS := 150.0

var _text_title: Label
var _text_speed: HSlider
var _auto_title: Label
var _auto_delay: HSlider
var _skip_unseen: CheckButton
var _fullscreen: CheckButton
var _music_title: Label
var _music: HSlider
var _sound_title: Label
var _sound: HSlider


func _init() -> void:
	columns = 2
	mouse_filter = MOUSE_FILTER_IGNORE
	add_theme_constant_override("h_separation", 60)
	add_theme_constant_override("v_separation", 40)

	_text_title = _title("")
	_text_speed = _slider(10.0, INSTANT_CPS, 5.0)
	_text_speed.value_changed.connect(_on_text_speed)

	_auto_title = _title("")
	_auto_delay = _slider(0.5, 5.0, 0.1)
	_auto_delay.value_changed.connect(_on_auto_delay)

	_title("Avance rapide")
	_skip_unseen = _check("Passer aussi le texte non lu")
	_skip_unseen.toggled.connect(func(on: bool) -> void: changed.emit("skip_unseen", on))

	_title("Affichage")
	_fullscreen = _check("Plein écran")
	_fullscreen.toggled.connect(func(on: bool) -> void: changed.emit("fullscreen", on))

	_music_title = _title("")
	_music = _slider(0.0, 1.0, 0.05)
	_music.value_changed.connect(func(value: float) -> void: _on_volume("music_volume", value))

	_sound_title = _title("")
	_sound = _slider(0.0, 1.0, 0.05)
	_sound.value_changed.connect(func(value: float) -> void: _on_volume("sound_volume", value))


func refresh(preferences: Dictionary) -> void:
	var cps: float = preferences.text_cps
	_text_speed.set_value_no_signal(INSTANT_CPS if cps <= 0.0 else cps)
	_auto_delay.set_value_no_signal(preferences.auto_delay)
	_skip_unseen.set_pressed_no_signal(preferences.skip_unseen)
	_fullscreen.set_pressed_no_signal(preferences.fullscreen)
	_music.set_value_no_signal(preferences.music_volume)
	_sound.set_value_no_signal(preferences.sound_volume)
	_update_titles()


func _update_titles() -> void:
	var cps := _text_speed.value
	_text_title.text = "Vitesse du texte : %s" % ("instantané" if cps >= INSTANT_CPS else "%d car./s" % int(cps))
	_auto_title.text = "Avance automatique : %s s" % String.num(_auto_delay.value, 1).replace(".", ",")
	_music_title.text = "Musique : %d %%" % roundi(_music.value * 100.0)
	_sound_title.text = "Sons : %d %%" % roundi(_sound.value * 100.0)


func _on_text_speed(value: float) -> void:
	_update_titles()
	changed.emit("text_cps", 0.0 if value >= INSTANT_CPS else value)


func _on_auto_delay(value: float) -> void:
	_update_titles()
	changed.emit("auto_delay", value)


func _on_volume(key: String, value: float) -> void:
	_update_titles()
	changed.emit(key, value)


func _title(text: String) -> Label:
	var result := Style.label(text, Style.LABEL_SIZE, Style.ACCENT)
	add_child(result)
	return result


func _slider(min_value: float, max_value: float, step: float) -> HSlider:
	var result := Style.slider(min_value, max_value, step)
	add_child(result)
	return result


func _check(text: String) -> CheckButton:
	var result := CheckButton.new()
	result.text = text
	result.focus_mode = FOCUS_NONE
	result.add_theme_font_size_override("font_size", Style.INTERFACE_SIZE)
	result.add_theme_color_override("font_color", Style.IDLE)
	result.add_theme_color_override("font_hover_color", Style.HOVER)
	result.add_theme_color_override("font_pressed_color", Style.SELECTED)
	result.add_theme_color_override("font_hover_pressed_color", Style.SELECTED)
	add_child(result)
	return result
