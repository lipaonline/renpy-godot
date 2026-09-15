## Renommages décrits dans game/renommages.json (produit par tools/fiches.py depuis la bible,
## « renommages »), le même fichier que game/sauvegardes.rpy côté Ren'Py : une ancienne
## sauvegarde qui contient un nom disparu reprend sa valeur (variable) ou sa position (label)
## sous le nouveau nom.
##
##   {"variables": [{"ancien": "relation_lena", "nouveau": "lena_moi"}],
##    "scenes": [{"ancien": "ch01_sc03", "nouveau": "ch01_sc03a"}]}
extends RefCounted


## Renvoie {data: {variables: [{ancien, nouveau}], scenes: [{ancien, nouveau}]}, errors: [String]}.
## Sans fichier, aucun renommage.
static func load_file(path: String, story: Dictionary) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {"data": empty(), "errors": []}
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(data) != TYPE_DICTIONARY:
		return {"data": empty(), "errors": ["%s : format attendu {\"variables\": [ … ], \"scenes\": [ … ]}" % path.get_file()]}
	return build(data, story, path.get_file())


static func empty() -> Dictionary:
	return {"variables": [], "scenes": []}


## Vérifie les données (déjà lues) : chaque nouveau nom doit exister dans le script.
static func build(data: Dictionary, story: Dictionary, where := "renommages.json") -> Dictionary:
	var result := empty()
	var errors: Array = []
	var known := {"variables": PackedStringArray(story.get("variables", [])), "scenes": PackedStringArray(story.labels.keys())}
	for field in ["variables", "scenes"]:
		var entries = data.get(field, [])
		if typeof(entries) != TYPE_ARRAY:
			errors.append("%s : « %s » doit être une liste" % [where, field])
			continue
		for i in entries.size():
			var entry = entries[i]
			var here := "%s, %s %d" % [where, field, i + 1]
			if typeof(entry) != TYPE_DICTIONARY or str(entry.get("ancien", "")) == "" or str(entry.get("nouveau", "")) == "":
				errors.append("%s : objet { ancien, nouveau } attendu" % here)
				continue
			var new_name := str(entry.nouveau)
			if not known[field].has(new_name) and not _renamed_later(entries, i, new_name):
				errors.append("%s : nom inconnu « %s » (le nouveau nom doit exister dans le script)" % [here, new_name])
				continue
			result[field].append({"ancien": str(entry.ancien), "nouveau": new_name})
	return {"data": result, "errors": errors}


## Un renommage en chaîne (a → b, puis b → c) accepte un nom intermédiaire.
static func _renamed_later(entries: Array, index: int, name: String) -> bool:
	for j in range(index + 1, entries.size()):
		if typeof(entries[j]) == TYPE_DICTIONARY and str(entries[j].get("ancien", "")) == name:
			return true
	return false
