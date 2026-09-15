## Cartes de navigation décrites dans game/navigation.json (produit par tools/fiches.py
## depuis la bible : « cartes » et « presence »), le même fichier que game/navigation.rpy
## côté Ren'Py.
##
##   {"cartes": {"ville": {"titre": "La ville", "affichage": "carte", "image": "carte_ville",
##                         "parent": "", "lieux": [{"lieu": "cafe", "nom": "Le café", "icone": "",
##                                    "x": 80, "y": 66, "label": "ch02_cafe", "carte": "", "si": "heure < 2"}]}},
##    "personnages": {"lena": {"nom": "Léna", "couleur": "#c8a2ff", "avatar": "lena avatar",
##                             "variable": "lieu_lena", "presence": [{"lieu": "cafe", "si": "heure == 1"}]}}}
##
## Affichage « carte » : image avec les lieux placés dessus (x, y en pourcentage) ; « pieces » :
## barre en bas de l'écran, une vignette par pièce (icône du lieu, avatars des personnages
## présents). Un lieu joue un label (« label ») ou ouvre une sous-carte (« carte ») ; « si » le
## montre sous condition. La présence : la première règle vraie donne le lieu du personnage,
## rangé dans sa variable à chaque carte. Les conditions, écrites dans le sous-ensemble, sont
## traduites en expressions Godot et vérifiées avec les variables de l'histoire.
extends RefCounted

const Parser = preload("res://engine/rpy_parser.gd")


## Renvoie {data: {cartes, personnages}, errors: [String]} ; sans fichier, des cartes vides.
static func load_file(path: String, story: Dictionary) -> Dictionary:
	if not FileAccess.file_exists(path):
		return build({}, story, path.get_file())
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(data) != TYPE_DICTIONARY:
		return {"data": {"cartes": {}, "personnages": {}},
			"errors": ["%s : format attendu {\"cartes\": { … }, \"personnages\": { … }}" % path.get_file()]}
	return build(data, story, path.get_file())


## Vérifie et prépare les données (déjà lues) pour l'interpréteur.
static func build(data: Dictionary, story: Dictionary, where := "navigation.json") -> Dictionary:
	var parser := Parser.new()
	var names := PackedStringArray(story.variables)
	var errors: Array = []
	var raw_maps = data.get("cartes", {})
	if typeof(raw_maps) != TYPE_DICTIONARY:
		errors.append("%s : « cartes » doit être un objet" % where)
		raw_maps = {}
	var maps := {}
	for map_id in raw_maps:
		var raw = raw_maps[map_id]
		var here := "%s, carte « %s »" % [where, map_id]
		if typeof(raw) != TYPE_DICTIONARY:
			errors.append("%s : objet attendu" % here)
			continue
		var places: Array = []
		var raw_places = raw.get("lieux", [])
		if typeof(raw_places) != TYPE_ARRAY:
			errors.append("%s : « lieux » doit être une liste" % here)
			raw_places = []
		for i in raw_places.size():
			var entry = raw_places[i]
			var place := "%s, lieu %d" % [here, i + 1]
			if typeof(entry) != TYPE_DICTIONARY:
				errors.append("%s : objet attendu" % place)
				continue
			var label := str(entry.get("label", ""))
			var sub_map := str(entry.get("carte", ""))
			if label != "" and not story.labels.has(label):
				errors.append("%s : label inconnu « %s »" % [place, label])
				continue
			if sub_map != "" and (not raw_maps.has(sub_map) or sub_map == map_id):
				errors.append("%s : sous-carte inconnue « %s »" % [place, sub_map])
				continue
			if label == "" and sub_map == "":
				errors.append("%s : il faut « label » (scène jouée) ou « carte » (sous-carte ouverte)" % place)
				continue
			places.append(_place(parser, entry, label, sub_map, names, place, errors))
		var parent := str(raw.get("parent", ""))
		if parent != "" and (not raw_maps.has(parent) or parent == map_id):
			errors.append("%s : carte parente inconnue « %s »" % [here, parent])
			parent = ""
		var layout := str(raw.get("affichage", "carte"))
		if layout not in ["carte", "pieces"]:
			errors.append("%s : « affichage » doit valoir carte ou pieces (reçu « %s »)" % [here, layout])
			layout = "carte"
		maps[map_id] = {"id": map_id, "titre": str(raw.get("titre", map_id)), "affichage": layout,
			"image": str(raw.get("image", "")), "parent": parent, "lieux": places}

	# Raccourcis : lieux proposés depuis toutes les cartes (bouton en bas à droite).
	var shortcuts: Array = []
	var raw_shortcuts = data.get("raccourcis", [])
	if typeof(raw_shortcuts) != TYPE_ARRAY:
		errors.append("%s : « raccourcis » doit être une liste" % where)
		raw_shortcuts = []
	for i in raw_shortcuts.size():
		var entry = raw_shortcuts[i]
		var place := "%s, raccourci %d" % [where, i + 1]
		if typeof(entry) != TYPE_DICTIONARY:
			errors.append("%s : objet attendu" % place)
			continue
		var label := str(entry.get("label", ""))
		var sub_map := str(entry.get("carte", ""))
		if (label != "" and not story.labels.has(label)) or (sub_map != "" and not raw_maps.has(sub_map)) or (label == "" and sub_map == ""):
			errors.append("%s : label ou sous-carte inconnu" % place)
			continue
		var shortcut := _place(parser, entry, label, sub_map, names, place, errors)
		shortcut["carte_origine"] = str(entry.get("carte_origine", ""))
		shortcuts.append(shortcut)

	var raw_characters = data.get("personnages", {})
	if typeof(raw_characters) != TYPE_DICTIONARY:
		errors.append("%s : « personnages » doit être un objet" % where)
		raw_characters = {}
	var characters := {}
	for pid in raw_characters:
		var raw = raw_characters[pid]
		var here := "%s, personnage « %s »" % [where, pid]
		if typeof(raw) != TYPE_DICTIONARY:
			errors.append("%s : objet attendu" % here)
			continue
		var variable := str(raw.get("variable", "lieu_%s" % pid))
		if variable not in story.variables:
			errors.append("%s : variable « %s » absente du script (attendu : default %s = \"\")" % [here, variable, variable])
			continue
		var rules: Array = []
		var raw_rules = raw.get("presence", [])
		if typeof(raw_rules) != TYPE_ARRAY:
			errors.append("%s : « presence » doit être une liste" % here)
			raw_rules = []
		for j in raw_rules.size():
			var rule = raw_rules[j]
			if typeof(rule) != TYPE_DICTIONARY:
				errors.append("%s, règle %d : objet attendu" % [here, j + 1])
				continue
			rules.append({"lieu": str(rule.get("lieu", "")),
				"expr": _condition(parser, str(rule.get("si", "")), names, "%s, règle %d" % [here, j + 1], errors)})
		characters[pid] = {"id": pid, "nom": str(raw.get("nom", pid)), "couleur": str(raw.get("couleur", "")),
			"avatar": str(raw.get("avatar", "")), "variable": variable, "presence": rules}

	# Lieu de chaque scène (label → lieu) : la rangée des pièces reste affichée pendant les
	# scènes jouées dans une pièce d'un bâtiment.
	var scenes := {}
	var raw_scenes = data.get("scenes", {})
	if typeof(raw_scenes) != TYPE_DICTIONARY:
		errors.append("%s : « scenes » doit être un objet" % where)
		raw_scenes = {}
	for label in raw_scenes:
		if not story.labels.has(label):
			errors.append("%s, scenes : label inconnu « %s »" % [where, label])
			continue
		scenes[label] = str(raw_scenes[label])

	# Les cartes que le script affiche doivent exister.
	for instruction in story.program:
		if instruction.op == "navigate" and not maps.has(instruction.map):
			errors.append("%s:%d: carte inconnue « %s » (game/navigation.json)" % [instruction.file, instruction.line, instruction.map])
	return {"data": {"cartes": maps, "raccourcis": shortcuts, "personnages": characters, "scenes": scenes}, "errors": errors}


## Un lieu d'une carte ; « temps » : coût du déplacement ({creneaux: n} ou {jours: n}), payé
## quand le joueur clique le lieu (Interpreter.apply_costs), avant sa scène ou sa sous-carte.
static func _place(parser: Parser, entry: Dictionary, label: String, sub_map: String, names: PackedStringArray, where: String, errors: Array) -> Dictionary:
	var lieu := str(entry.get("lieu", ""))
	var cost = entry.get("temps")
	return {
		"lieu": lieu, "nom": str(entry.get("nom", lieu)), "icone": str(entry.get("icone", "")),
		"x": float(entry.get("x", 50)), "y": float(entry.get("y", 50)),
		"label": label, "carte": sub_map,
		"expr": _condition(parser, str(entry.get("si", "")), names, where, errors),
		"temps": cost if typeof(cost) == TYPE_DICTIONARY else {},
		"raccourci": bool(entry.get("raccourci", false)),
	}


## Condition du sous-ensemble → expression Godot ; vide = toujours vraie.
static func _condition(parser: Parser, source: String, names: PackedStringArray, where: String, errors: Array) -> String:
	if source.strip_edges().is_empty():
		return ""
	var result := parser.compile_expression(source, names)
	if result.error != "":
		errors.append("%s : %s" % [where, result.error])
		return "false"
	return result.expr
