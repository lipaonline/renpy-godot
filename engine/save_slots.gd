## Emplacements de sauvegarde : user://saves/<emplacement>.save (état de la partie,
## date, dernière réplique) et <emplacement>.png (vignette).
## Emplacements : « quick » (sauvegarde rapide) et « page-numéro » (« 1-1 » à « 5-6 »).
extends RefCounted

const DIR := "user://saves"
const THUMBNAIL_SIZE := Vector2i(384, 216)


static func write(slot: String, state: Dictionary, description: String, screenshot: Image) -> bool:
	DirAccess.make_dir_recursive_absolute(DIR)
	var file := FileAccess.open(_path(slot, "save"), FileAccess.WRITE)
	if file == null:
		return false
	var now := Time.get_datetime_dict_from_system()
	var date := "%02d/%02d/%04d %02d:%02d" % [now.day, now.month, now.year, now.hour, now.minute]
	file.store_string(var_to_str({"state": state, "description": description, "date": date}))
	file.close()
	var picture_path := _path(slot, "png")
	if screenshot != null and not screenshot.is_empty():
		var small := screenshot.duplicate() as Image
		small.resize(THUMBNAIL_SIZE.x, THUMBNAIL_SIZE.y, Image.INTERPOLATE_BILINEAR)
		small.save_png(picture_path)
	elif FileAccess.file_exists(picture_path):
		DirAccess.remove_absolute(picture_path)
	return true


## {state, description, date}, ou {} si l'emplacement est vide ou illisible.
static func read(slot: String) -> Dictionary:
	var path := _path(slot, "save")
	if not FileAccess.file_exists(path):
		return {}
	var data = str_to_var(FileAccess.get_file_as_string(path))
	if typeof(data) != TYPE_DICTIONARY or not data.has("state"):
		return {}
	return data


static func exists(slot: String) -> bool:
	return FileAccess.file_exists(_path(slot, "save"))


static func thumbnail(slot: String) -> Texture2D:
	var path := _path(slot, "png")
	if not FileAccess.file_exists(path):
		return null
	var image := Image.load_from_file(path)
	return ImageTexture.create_from_image(image) if image != null else null


static func delete(slot: String) -> void:
	for extension in ["save", "png"]:
		var path := _path(slot, extension)
		if FileAccess.file_exists(path):
			DirAccess.remove_absolute(path)


static func _path(slot: String, extension: String) -> String:
	return DIR.path_join("%s.%s" % [slot, extension])
