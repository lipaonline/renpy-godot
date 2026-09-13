## Galerie décrite dans game/galerie.json, un format que Ren'Py pourra lire aussi.
## Une entrée est débloquée dès que son label a été atteint une fois
## (côté Ren'Py : renpy.seen_label).
##
##   {"entrees": [{"titre": "…", "label": "lena_confiance", "vignette": "lena rougit",
##                 "video": "videos/scene.webm"}  ou  "images": ["cg 1", "cg 2"]]}
extends RefCounted


## Renvoie {entries: [{title, label, thumbnail, images, video}], errors: [String]}.
static func load_file(path: String, story: Dictionary) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {"entries": [], "errors": []}
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(data) != TYPE_DICTIONARY or typeof(data.get("entrees")) != TYPE_ARRAY:
		return {"entries": [], "errors": ["%s : format attendu {\"entrees\": [ … ]}" % path.get_file()]}
	var entries: Array = []
	var errors: Array = []
	for i in data.entrees.size():
		var entry = data.entrees[i]
		var where := "%s, entrée %d" % [path.get_file(), i + 1]
		if typeof(entry) != TYPE_DICTIONARY:
			errors.append("%s : objet attendu" % where)
			continue
		var label: String = str(entry.get("label", ""))
		if not story.labels.has(label):
			errors.append("%s : label inconnu « %s »" % [where, label])
			continue
		var images: Array = entry.get("images", [])
		var video: String = str(entry.get("video", ""))
		if images.is_empty() and video == "":
			errors.append("%s : il faut « images » ou « video »" % where)
			continue
		var thumbnail: String = str(entry.get("vignette", images[0] if not images.is_empty() else ""))
		entries.append({"title": str(entry.get("titre", label)), "label": label, "thumbnail": thumbnail,
			"images": images, "video": video})
	return {"entries": entries, "errors": errors}
