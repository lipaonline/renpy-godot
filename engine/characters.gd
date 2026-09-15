## Fiches des personnages décrites dans game/personnages.json (produit par tools/fiches.py depuis
## les blocs « jauges » et « competences » de la bible), le même fichier que game/personnages.rpy
## côté Ren'Py.
##
##   {"personnages": {"lena": {"nom": "Léna", "couleur": "#c8a2ff", "avatar": "lena avatar",
##                             "jauges": [{"variable": "lena_relation", "nom": "Relation", "min": 0, "max": 10,
##                                         "paliers": [{"des": 0, "nom": "distante"}, {"des": 6, "nom": "amie"}]}],
##                             "competences": [{"variable": "lena_photographie", "nom": "Photographie",
##                                              "min": 0, "max": 5, "paliers": []}],
##                             "relations": [{"variable": "lena_karim", "avec": "karim", "nom": "Karim",
##                                            "couleur": "#f2b45c", "min": 0, "max": 10, "paliers": []}]}}}
##
## Chaque jauge lit une variable de l'histoire (<personnage>_<nom>) ; le plus haut palier dont le
## seuil est atteint donne le nom affiché. Une relation figure sur les fiches des deux personnages
## (« avec » : l'autre, dont le nom et la couleur sont repris). Mêmes règles que l'écran Ren'Py.
extends RefCounted


## Renvoie {characters: [{id, nom, couleur, avatar, jauges, competences, relations}], errors: [String]}.
## Une jauge : {variable, nom, couleur, min, max, paliers: [{des, nom}]} ; sans fichier, aucune fiche.
static func load_file(path: String, story: Dictionary) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {"characters": [], "errors": []}
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(data) != TYPE_DICTIONARY or typeof(data.get("personnages")) != TYPE_DICTIONARY:
		return {"characters": [], "errors": ["%s : format attendu {\"personnages\": { … }}" % path.get_file()]}
	var characters: Array = []
	var errors: Array = []
	var names := PackedStringArray(story.get("variables", []))
	for pid in data.personnages:
		var raw = data.personnages[pid]
		var where := "%s, personnage « %s »" % [path.get_file(), pid]
		if typeof(raw) != TYPE_DICTIONARY:
			errors.append("%s : objet attendu" % where)
			continue
		var character := {"id": str(pid), "nom": str(raw.get("nom", pid)), "couleur": str(raw.get("couleur", "")),
			"avatar": str(raw.get("avatar", "")), "jauges": [], "competences": [], "relations": []}
		for field in ["jauges", "competences", "relations"]:
			var raw_gauges = raw.get(field, [])
			if typeof(raw_gauges) != TYPE_ARRAY:
				errors.append("%s : « %s » doit être une liste" % [where, field])
				continue
			for i in raw_gauges.size():
				var entry = raw_gauges[i]
				var here := "%s, %s %d" % [where, field, i + 1]
				if typeof(entry) != TYPE_DICTIONARY or str(entry.get("variable", "")) == "":
					errors.append("%s : objet avec « variable » attendu" % here)
					continue
				var variable := str(entry.variable)
				if not names.is_empty() and not names.has(variable):
					errors.append("%s : variable inconnue « %s » (à déclarer par default dans le script)" % [here, variable])
					continue
				var thresholds: Array = []
				for raw_threshold in entry.get("paliers", []):
					if typeof(raw_threshold) == TYPE_DICTIONARY:
						thresholds.append({"des": float(raw_threshold.get("des", 0)), "nom": str(raw_threshold.get("nom", ""))})
				thresholds.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a.des < b.des)
				character[field].append({"variable": variable, "nom": str(entry.get("nom", variable)),
					"couleur": str(entry.get("couleur", "")), "min": float(entry.get("min", 0)),
					"max": float(entry.get("max", 0)), "paliers": thresholds})
		characters.append(character)
	return {"characters": characters, "errors": errors}


## Nom du plus haut palier atteint par value, ou une chaîne vide.
static func threshold_name(gauge: Dictionary, value: float) -> String:
	var found := ""
	for threshold in gauge.paliers:
		if value >= threshold.des:
			found = threshold.nom
	return found
