## Données partagées par toutes les parties, comme « persistent » dans Ren'Py :
## répliques déjà lues, labels atteints, images vues et préférences.
extends RefCounted

const DEFAULT_PATH := "user://persistent.txt"
const DEFAULT_PREFERENCES := {
	"text_cps": 0.0,
	"auto_delay": 1.5,
	"skip_unseen": false,
	"fullscreen": false,
	"music_volume": 1.0,
	"sound_volume": 1.0,
	## Code de la langue du jeu ; vide avant le premier lancement (langue du système).
	"language": "",
}

var seen_lines: Dictionary = {}
var seen_labels: Dictionary = {}
var seen_images: Dictionary = {}
var preferences: Dictionary = DEFAULT_PREFERENCES.duplicate()

var _path: String
var _dirty := false


func _init(path := DEFAULT_PATH) -> void:
	_path = path


func load_data() -> void:
	if not FileAccess.file_exists(_path):
		return
	var data = str_to_var(FileAccess.get_file_as_string(_path))
	if typeof(data) != TYPE_DICTIONARY:
		push_warning("%s illisible : données persistantes ignorées" % _path)
		return
	seen_lines = data.get("seen_lines", {})
	seen_labels = data.get("seen_labels", {})
	seen_images = data.get("seen_images", {})
	var saved: Dictionary = data.get("preferences", {})
	for key in DEFAULT_PREFERENCES:
		preferences[key] = saved.get(key, DEFAULT_PREFERENCES[key])


## N'écrit que si quelque chose a changé depuis la dernière écriture.
func save_data() -> void:
	if not _dirty:
		return
	var file := FileAccess.open(_path, FileAccess.WRITE)
	if file == null:
		push_warning("Impossible d'écrire %s" % _path)
		return
	file.store_string(var_to_str({
		"seen_lines": seen_lines,
		"seen_labels": seen_labels,
		"seen_images": seen_images,
		"preferences": preferences,
	}))
	_dirty = false


func is_line_seen(id: String) -> bool:
	return seen_lines.has(id)


func mark_line(id: String) -> void:
	_mark(seen_lines, id)


func is_label_seen(label_name: String) -> bool:
	return seen_labels.has(label_name)


func mark_label(label_name: String) -> void:
	_mark(seen_labels, label_name)


func mark_image(image_name: String) -> void:
	_mark(seen_images, image_name)


func set_preference(key: String, value: Variant) -> void:
	if preferences.get(key) != value:
		preferences[key] = value
		_dirty = true


func _mark(table: Dictionary, key: String) -> void:
	if key != "" and not table.has(key):
		table[key] = true
		_dirty = true
