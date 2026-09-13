## Images et vidéos du jeu, avec les conventions de Ren'Py :
## « game/images/lena sourire.png » définit l'image « lena sourire ».
extends RefCounted

const GAME_DIR := "res://game"
const GUI_DIR := "res://game/gui"
const IMAGE_EXTENSIONS := ["png", "jpg", "jpeg", "webp"]

## Nom d'image Ren'Py → chemin res://
var images: Dictionary = {}


func index_dir(dir: String) -> void:
	if not DirAccess.dir_exists_absolute(dir):
		return
	for file_name in DirAccess.get_files_at(dir):
		var file := file_name.trim_suffix(".import").trim_suffix(".remap")
		if file.get_extension().to_lower() in IMAGE_EXTENSIONS:
			images[file.get_basename().to_lower()] = dir.path_join(file)
	for sub_dir in DirAccess.get_directories_at(dir):
		index_dir(dir.path_join(sub_dir))


## Ajoute les images déclarées par l'instruction « image » (chemins relatifs à game/).
func add_definitions(definitions: Dictionary) -> void:
	for image_name in definitions:
		images[image_name] = GAME_DIR.path_join(definitions[image_name])


func image_texture(image_name: String) -> Texture2D:
	var path: String = images.get(image_name.to_lower(), "")
	return load_texture(path) if path != "" else null


static func load_texture(path: String) -> Texture2D:
	if ResourceLoader.exists(path):
		var resource := load(path)
		if resource is Texture2D:
			return resource as Texture2D
	if not FileAccess.file_exists(path):
		return null
	# Fichier pas encore importé par l'éditeur : lecture directe.
	var image := Image.load_from_file(ProjectSettings.globalize_path(path))
	return ImageTexture.create_from_image(image) if image != null else null


## Ren'Py lit le .webm ; Godot lit le .ogv (Ogg Theora) de même nom.
static func ogv_path(path: String) -> String:
	return GAME_DIR.path_join(path.get_basename() + ".ogv")


static func video_stream(path: String) -> VideoStream:
	var ogv := ogv_path(path)
	if ResourceLoader.exists(ogv):
		var stream := load(ogv) as VideoStream
		if stream != null:
			return stream
	if FileAccess.file_exists(ogv):
		var theora := VideoStreamTheora.new()
		theora.file = ogv
		return theora
	return null
