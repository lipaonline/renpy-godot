## Temps décrit dans game/temps.json (produit par tools/fiches.py depuis la bible, « temps »),
## le même fichier que game/temps.rpy côté Ren'Py.
##
##   {"creneaux": ["matin", "midi", "soir"], "jours": true, "semaine": ["lundi", …],
##    "date": true, "mois": ["janvier", …], "epoques": ["present", "passe"]}
##
## Les variables creneau, moment, jour, jour_semaine, jour_mois, mois et annee sont celles du
## script ; les labels temps_* du script généré les font avancer. Le lecteur affiche
## « Jour 2 · mardi · matin », ou avec un calendrier « mardi 14 septembre 2027 · matin ».
extends RefCounted


## Renvoie {data: {creneaux, jours, semaine}, errors: [String]} ; sans fichier, pas de temps.
static func load_file(path: String, story: Dictionary) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {"data": empty(), "errors": []}
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(data) != TYPE_DICTIONARY or typeof(data.get("creneaux")) != TYPE_ARRAY:
		return {"data": empty(), "errors": ["%s : format attendu {\"creneaux\": [ … ], \"jours\": true, \"semaine\": [ … ]}" % path.get_file()]}
	var result := {"creneaux": Array(data.creneaux).map(func(c: Variant) -> String: return str(c)),
		"jours": bool(data.get("jours", false)),
		"semaine": Array(data.get("semaine", [])).map(func(j: Variant) -> String: return str(j)),
		"date": bool(data.get("date", false)),
		"mois": Array(data.get("mois", [])).map(func(m: Variant) -> String: return str(m))}
	var errors: Array = []
	if not result.creneaux.is_empty():
		var names := PackedStringArray(story.get("variables", []))
		for variable in ["creneau", "moment"] + (["jour"] if result.jours else []) + (["jour_semaine"] if not result.semaine.is_empty() else []) \
				+ (["jour_mois", "mois", "annee"] if result.date else []):
			if not names.is_empty() and not names.has(variable):
				errors.append("%s : variable « %s » absente du script (attendu : default %s = …)" % [path.get_file(), variable, variable])
		if not story.get("labels", {}).has("temps_avancer") and not story.is_empty():
			errors.append("%s : label temps_avancer absent du script" % path.get_file())
	return {"data": result, "errors": errors}


static func empty() -> Dictionary:
	return {"creneaux": [], "jours": false, "semaine": [], "date": false, "mois": []}


## Texte affiché pendant la partie : « Jour 2 · mardi · matin » (noms traduits par translate).
static func text(model: Dictionary, store: Dictionary, translate := Callable()) -> String:
	if model.creneaux.is_empty():
		return ""
	var parts: PackedStringArray = []
	if model.date and model.mois.size() == 12:
		# « mardi 14 septembre 2027 » : jour de la semaine, jour du mois, mois, année.
		var month: int = clampi(int(store.get("mois", 1)), 1, 12)
		parts.append("%s %d %s %d" % [_translated(str(store.get("jour_semaine", "")), translate), int(store.get("jour_mois", 1)),
			_translated(model.mois[month - 1], translate), int(store.get("annee", 0))])
	else:
		if model.jours:
			parts.append(TranslationServer.translate("Jour %d") % int(store.get("jour", 1)))
		if not model.semaine.is_empty():
			parts.append(_translated(str(store.get("jour_semaine", "")), translate))
	parts.append(_translated(str(store.get("moment", "")), translate))
	return " · ".join(parts)


static func _translated(text_value: String, translate: Callable) -> String:
	return translate.call(text_value) if translate.is_valid() else text_value
