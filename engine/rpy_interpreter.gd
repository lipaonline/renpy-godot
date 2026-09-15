## Exécute une histoire compilée par rpy_parser.gd.
##
## L'interpréteur ne dessine rien : next() renvoie l'événement suivant et le
## lecteur décide comment l'afficher. Événements :
##   bloquants     say, menu, navigate, movie, pause, end, error
##   non bloquants scene, show, hide, audio, with
##
## navigate : une carte (engine/navigation.gd) attend un lieu ; map_view() décrit la carte à
## afficher et navigate_to() saute à la scène du lieu choisi.
##
## Il tient aussi l'historique des répliques et un point de retour arrière par
## interaction (réplique, menu, vidéo, pause), comme Ren'Py.
extends RefCounted

signal label_entered(label_name: String)

const MAX_STEPS := 100000
const HISTORY_LENGTH := 250
const ROLLBACK_LENGTH := 128

var story: Dictionary
var store: Dictionary = {}
## État visuel courant, conservé dans les sauvegardes : {scene, shown: {tag: {image, at}}, music}
var stage: Dictionary = {}
var call_stack: Array = []
## Répliques affichées, les plus récentes à la fin : [{name, color, text}]
var history: Array = []
var pc := 0
var track_coverage := false
var coverage: Dictionary = {}
## Traduction en cours (rpy_parser.finish_translation), vide pour la langue des fiches :
## {lines: {id: réplique traduite}, strings: {texte: traduction}}.
var translation: Dictionary = {}
## Cartes de navigation et règles de présence (engine/navigation.gd, champ « data »).
var navigation: Dictionary = {"cartes": {}, "personnages": {}}

var _names: PackedStringArray
var _expressions: Dictionary = {}
var _menu = null
## Carte affichée, en attente d'un lieu (vide sinon), et lieu où l'on est (« vous êtes ici »).
var _navigate := ""
var _navigate_here := ""
var _resume_pc := -1
var _ended := false
var _fatal := ""
var _where := ""
var _checkpoints: Array = []
## Nombre de répliques ajoutées à l'historique depuis le début (troncature comprise).
var _history_total := 0
## Valeur de _history_total juste avant l'interaction en cours.
var _history_before := 0


func _init(compiled_story: Dictionary) -> void:
	story = compiled_story
	_names = compiled_story.variables


func start(label := "start") -> void:
	_fatal = ""
	_ended = false
	_menu = null
	_navigate = ""
	_resume_pc = -1
	call_stack.clear()
	history.clear()
	_checkpoints.clear()
	_history_total = 0
	_history_before = 0
	stage = {"scene": "", "shown": {}, "music": ""}
	store.clear()
	for name in _names:
		store[name] = null
	for init in story.inits:
		_where = "%s:%d" % [init.file, init.line]
		store[init.name] = _eval(init.expr)
	pc = story.labels.get(label, -1)
	if pc < 0:
		_fatal = "label « %s » introuvable" % label


func next() -> Dictionary:
	if _fatal != "":
		return {"type": "error", "message": _fatal}
	if _ended:
		return {"type": "end"}
	if _menu != null:
		return _menu_event(_menu)
	if _navigate != "":
		return _navigate_event()
	var program: Array = story.program
	var steps := 0
	while pc < program.size() and _fatal == "":
		steps += 1
		if steps > MAX_STEPS:
			_fail("boucle infinie : aucune interaction après %d instructions" % MAX_STEPS)
			break
		var index := pc
		var instruction: Dictionary = program[pc]
		pc += 1
		_where = "%s:%d" % [instruction.file, instruction.line]
		if track_coverage:
			coverage[index] = true
		var event := _execute(instruction, index)
		if not event.is_empty() and _fatal == "":
			return event
	if _fatal != "":
		return {"type": "error", "message": _fatal}
	_ended = true
	return {"type": "end"}


## Choisit une option du menu en attente (index dans la liste complète des choix).
func choose(index: int) -> bool:
	if _menu == null:
		return false
	var choices: Array = _menu.choices
	if index < 0 or index >= choices.size():
		return false
	var choice: Dictionary = choices[index]
	if choice.expr != "" and not _truthy(_eval(choice.expr)):
		return false
	_menu = null
	pc = choice.target
	return true


# --- Navigation ------------------------------------------------------------------------

func set_navigation(data: Dictionary) -> void:
	navigation = data


## Renommages (game/renommages.json) appliqués aux anciennes sauvegardes : variables et labels.
var renames: Dictionary = {"variables": [], "scenes": []}


func set_renames(data: Dictionary) -> void:
	renames = data


## Carte en attente : {type, map, here} (here : lieu où l'on est, ou vide).
func _navigate_event() -> Dictionary:
	return {"type": "navigate", "map": _navigate, "here": _navigate_here}


## Saute à la scène d'un lieu accessible depuis la carte en attente.
func navigate_to(label: String) -> bool:
	if _navigate == "" or not story.labels.has(label):
		return false
	# Les déplacements ont déjà été payés au clic : les conditions s'évaluent sur l'état courant.
	for target in map_targets(_navigate, false):
		if target.label == label:
			_navigate = ""
			pc = story.labels[label]
			return true
	return false


## Carte à afficher : titre, affichage (carte ou pieces), image, sortie vers la carte parente,
## fil d'Ariane (cartes parentes, de la racine à la parente directe), lieux visibles avec les
## personnages présents (un lieu qui ouvre une sous-carte montre ceux de toutes ses pièces) et
## raccourcis (lieux proposés partout, sauf sur leur propre carte). Textes traduits.
## {id, titre, affichage, image, parent, exit_text, chemin: [{id, titre}],
##  lieux: [{lieu, nom, icone, x, y, label, carte, temps, presents: [{id, nom, couleur, avatar}]}], raccourcis: [même forme]}
func map_view(map_id: String) -> Dictionary:
	var carte: Dictionary = navigation.cartes.get(map_id, {})
	if carte.is_empty():
		return {}
	var view := {"id": map_id, "titre": _interpolate(translate_string(carte.titre)), "affichage": carte.get("affichage", "carte"),
		"image": carte.image, "parent": carte.parent, "exit_text": "", "chemin": [], "lieux": [], "raccourcis": []}
	if carte.parent != "" and navigation.cartes.has(carte.parent):
		view.exit_text = "← " + _interpolate(translate_string(navigation.cartes[carte.parent].titre))
	var seen := {map_id: true}
	var parent: String = carte.parent
	while parent != "" and navigation.cartes.has(parent) and not seen.has(parent):
		seen[parent] = true
		view.chemin.push_front({"id": parent, "titre": _interpolate(translate_string(navigation.cartes[parent].titre))})
		parent = navigation.cartes[parent].parent
	var here: Array = []
	for entry in carte.lieux:
		here.append(entry.lieu)
		if entry.expr == "" or _truthy(_eval(entry.expr)):
			view.lieux.append(_place_view(entry))
	for entry in navigation.get("raccourcis", []):
		if not here.has(entry.lieu) and (entry.expr == "" or _truthy(_eval(entry.expr))):
			view.raccourcis.append(_place_view(entry))
	return view


func _place_view(entry: Dictionary) -> Dictionary:
	var covered: Array = [entry.lieu]
	if entry.carte != "":
		covered.append_array(_map_places(entry.carte, {}))
	return {"lieu": entry.lieu, "nom": _interpolate(translate_string(entry.nom)), "icone": entry.get("icone", ""),
		"x": entry.x, "y": entry.y, "label": entry.label, "carte": entry.carte, "temps": entry.get("temps", {}),
		"presents": _present_characters(covered)}


## Paie des déplacements (entrées « temps » des cartes : {creneaux: n} ou {jours: n}) en exécutant
## tout de suite les labels du temps du script, comme Ren'Py au clic sur le lieu.
func apply_costs(costs: Array) -> void:
	for cost in costs:
		if typeof(cost) != TYPE_DICTIONARY:
			continue
		if int(cost.get("jours", 0)) > 0:
			store["temps_saut"] = int(cost.jours)
			_run_label_now("temps_sauter_jours")
		for _i in int(cost.get("creneaux", 0)):
			_run_label_now("temps_avancer")


## Exécute un label sans interaction (labels temps_*) et revient où l'on était.
func _run_label_now(label: String) -> void:
	if not story.labels.has(label) or _fatal != "":
		return
	var saved_pc := pc
	var base := call_stack.size()
	call_stack.append(saved_pc)
	pc = story.labels[label]
	var steps := 0
	while call_stack.size() > base and _fatal == "" and pc < story.program.size():
		steps += 1
		if steps > MAX_STEPS:
			_fail("boucle infinie dans le label « %s »" % label)
			break
		var instruction: Dictionary = story.program[pc]
		pc += 1
		_where = "%s:%d" % [instruction.file, instruction.line]
		if not _execute(instruction, pc - 1).is_empty():
			_fail("le label « %s » ne doit pas interagir (coût de déplacement)" % label)
			break
	pc = saved_pc


## Scènes accessibles depuis une carte : lieux visibles de la carte, puis les raccourcis, puis
## ceux des sous-cartes et des cartes parentes. Avec with_costs, les conditions d'une sous-carte
## sont évaluées après le coût du déplacement qui y mène (comme au clic) ; sans, sur l'état
## courant (déplacements déjà payés). [{label, lieu, carte, rang, costs}]
func map_targets(map_id: String, with_costs := true) -> Array:
	# Seul le store bouge quand on paie un déplacement : on le remet tel quel (restore() effacerait
	# les points de retour arrière).
	var base_store := store.duplicate(true)
	var queue: Array = [[map_id, []]]
	var seen := {map_id: true}
	var reached := {}
	var targets: Array = []
	var first := true
	while not queue.is_empty():
		var item: Array = queue.pop_front()
		var current: String = item[0]
		var costs: Array = item[1]
		var carte: Dictionary = navigation.cartes.get(current, {})
		if carte.is_empty():
			continue
		if with_costs:
			store = base_store.duplicate(true)
			apply_costs(costs)
		for i in carte.lieux.size():
			_visit_target(carte.lieux[i], current, i, costs, queue, seen, reached, targets)
		if first:
			first = false
			var here: Array = carte.lieux.map(func(entry: Dictionary) -> String: return entry.lieu)
			for entry in navigation.get("raccourcis", []):
				if here.has(entry.lieu):
					continue
				var origin: String = entry.get("carte_origine", "")
				var rank: int = navigation.cartes.get(origin, {"lieux": []}).lieux.find(entry)
				_visit_target(entry, origin, rank, [], queue, seen, reached, targets)
		if carte.parent != "" and not seen.has(carte.parent):
			seen[carte.parent] = true
			queue.append([carte.parent, costs])
	if with_costs:
		store = base_store
	return targets


func _visit_target(entry: Dictionary, current: String, rank: int, costs: Array, queue: Array, seen: Dictionary, reached: Dictionary, targets: Array) -> void:
	if entry.expr != "" and not _truthy(_eval(entry.expr)):
		return
	var next_costs: Array = costs.duplicate()
	if not entry.get("temps", {}).is_empty():
		next_costs.append(entry.temps)
	if entry.label != "":
		var key := "%s:%d" % [current, rank]
		if not reached.has(key):
			reached[key] = true
			targets.append({"label": entry.label, "lieu": entry.lieu, "carte": current, "rang": rank, "costs": next_costs})
	elif entry.carte != "" and not seen.has(entry.carte):
		seen[entry.carte] = true
		queue.append([entry.carte, next_costs])


## Rangée des pièces à garder affichée pendant une scène : {map, lieu} si le lieu de la scène
## (label) appartient à une carte « pieces », sinon vide.
func overlay_for_label(label: String) -> Dictionary:
	var lieu: String = navigation.get("scenes", {}).get(label, "")
	if lieu == "":
		return {}
	for map_id in navigation.cartes:
		var carte: Dictionary = navigation.cartes[map_id]
		if carte.get("affichage", "carte") != "pieces":
			continue
		for entry in carte.lieux:
			if entry.lieu == lieu:
				return {"map": map_id, "lieu": lieu}
	return {}


## Lieu d'un personnage d'après ses règles « presence » : la première règle vraie, sinon aucun.
func _character_place(character: Dictionary) -> String:
	for rule in character.presence:
		if rule.expr == "" or _truthy(_eval(rule.expr)):
			return rule.lieu
		if _fatal != "":
			break
	return ""


## Lieu de chaque personnage rangé dans sa variable (lieu_<personnage>), comme naviguer()
## côté Ren'Py, pour que les fiches puissent le tester.
func _apply_presence() -> void:
	for pid in navigation.personnages:
		var character: Dictionary = navigation.personnages[pid]
		if not store.has(character.variable):
			_fail("variable de présence « %s » absente du script" % character.variable)
			return
		var lieu := _character_place(character)
		if _fatal != "":
			return
		store[character.variable] = lieu


## Identifiants des lieux d'une carte et de ses sous-cartes.
func _map_places(map_id: String, seen: Dictionary) -> Array:
	var places: Array = []
	if seen.has(map_id) or not navigation.cartes.has(map_id):
		return places
	seen[map_id] = true
	for entry in navigation.cartes[map_id].lieux:
		places.append(entry.lieu)
		if entry.carte != "":
			places.append_array(_map_places(entry.carte, seen))
	return places


## Personnages présents sur des lieux, d'après leurs règles évaluées maintenant (la rangée des
## pièces s'affiche aussi pendant les scènes, avant tout naviguer()).
func _present_characters(places: Array) -> Array:
	var result: Array = []
	for pid in navigation.personnages:
		var character: Dictionary = navigation.personnages[pid]
		if _character_place(character) in places:
			result.append({"id": pid, "nom": _interpolate(translate_string(character.nom)), "couleur": character.couleur,
				"avatar": character.get("avatar", "")})
	return result


# --- Retour arrière --------------------------------------------------------------------

func can_rollback() -> bool:
	return _checkpoints.size() >= (1 if _ended else 2)


## Revient à l'interaction précédente ; next() la rejoue ensuite (un menu peut
## alors recevoir une autre réponse).
func rollback() -> bool:
	if not can_rollback():
		return false
	if not _ended:
		_checkpoints.pop_back()
	var checkpoint: Dictionary = _checkpoints.pop_back()
	store = checkpoint.store.duplicate(true)
	call_stack = checkpoint.call_stack.duplicate()
	stage = checkpoint.stage.duplicate(true)
	var removed: int = _history_total - checkpoint.history_total
	history.resize(maxi(0, history.size() - removed))
	_history_total = checkpoint.history_total
	_history_before = _history_total
	pc = checkpoint.resume
	_menu = null
	_navigate = ""
	_ended = false
	_fatal = ""
	return true


# --- Sauvegarde ------------------------------------------------------------------------

## État sérialisable (var_to_str) : positions exprimées en label + décalage.
## L'historique exclut la réplique en cours, qui sera rejouée au chargement.
func get_state() -> Dictionary:
	var current_lines := _history_total - _history_before
	return {
		"version": 1,
		"resume": _to_ref(_resume_pc),
		"call_stack": call_stack.map(_to_ref),
		"store": store.duplicate(true),
		"stage": stage.duplicate(true),
		"history": history.slice(0, maxi(0, history.size() - current_lines)),
	}


## Restaure un état ; la prochaine interaction (réplique ou menu) est rejouée.
func set_state(state: Dictionary) -> bool:
	var resume := _from_ref(state.get("resume", []))
	if resume < 0:
		return false
	var targets: Array = []
	for ref in state.get("call_stack", []):
		var target := _from_ref(ref)
		if target < 0:
			return false
		targets.append(target)
	var saved: Dictionary = state.get("store", {}).duplicate()
	# Variables renommées depuis la sauvegarde : l'ancienne valeur passe sous le nouveau nom
	# (plusieurs passes : les chaînes a → b, b → c passent quel que soit l'ordre déclaré).
	var variable_renames: Array = renames.get("variables", [])
	for _pass in variable_renames.size():
		for rename in variable_renames:
			if saved.has(rename.ancien) and not saved.has(rename.nouveau):
				saved[rename.nouveau] = saved[rename.ancien]
	_fatal = ""
	store.clear()
	for name in _names:
		store[name] = saved.get(name)
	# Comme Ren'Py : les define sont recalculés, les nouveaux default initialisés.
	for init in story.inits:
		if init.kind == "define" or not saved.has(init.name):
			store[init.name] = _eval(init.expr)
	call_stack = targets
	stage = state.get("stage", {"scene": "", "shown": {}, "music": ""}).duplicate(true)
	history = state.get("history", []).duplicate(true)
	_history_total = history.size()
	_history_before = _history_total
	_checkpoints.clear()
	pc = resume
	_menu = null
	_navigate = ""
	_ended = false
	return _fatal == ""


## Copie complète de l'état en mémoire, utilisée par l'explorateur de routes.
func snapshot() -> Dictionary:
	return {"pc": pc, "store": store.duplicate(true), "call_stack": call_stack.duplicate(),
		"stage": stage.duplicate(true), "menu": _menu, "navigate": _navigate, "navigate_here": _navigate_here,
		"resume": _resume_pc, "ended": _ended}


func restore(snap: Dictionary) -> void:
	pc = snap.pc
	store = snap.store.duplicate(true)
	call_stack = snap.call_stack.duplicate()
	stage = snap.stage.duplicate(true)
	_menu = snap.menu
	_navigate = snap.get("navigate", "")
	_navigate_here = snap.get("navigate_here", "")
	_resume_pc = snap.resume
	_ended = snap.ended
	_fatal = ""
	_checkpoints.clear()


# --- Langue ----------------------------------------------------------------------------

func set_translation(value: Dictionary) -> void:
	translation = value


## Nom, choix ou titre traduit, comme les « translate strings » de Ren'Py.
func translate_string(text: String) -> String:
	return translation.get("strings", {}).get(text, text)


## L'interaction en cours recalculée (après un changement de langue) : la réplique, le menu
## ou la carte en attente ; la ligne d'historique d'une réplique est mise à jour. Vide sinon.
func current_event() -> Dictionary:
	if _fatal != "" or _ended or _resume_pc < 0:
		return {}
	if _navigate != "":
		return _navigate_event()
	if _menu != null:
		var event := _menu_event(_menu)
		if event.prompt != null:
			_replace_current_history(event.prompt)
		return event
	var instruction: Dictionary = story.program[_resume_pc]
	if instruction.op != "say" or pc != _resume_pc + 1:
		return {}
	var said := _say_event(instruction)
	_replace_current_history(said)
	return said


func _replace_current_history(say_event: Dictionary) -> void:
	if _history_total > _history_before and not history.is_empty():
		history[history.size() - 1] = {"name": say_event.name, "color": say_event.color, "text": say_event.text}


## Index de l'instruction de menu en attente, ou -1.
func menu_pc() -> int:
	return _resume_pc if _menu != null else -1


func current_label() -> String:
	return _to_ref(maxi(pc - 1, 0))[0]


# --- Exécution -------------------------------------------------------------------------

func _execute(instruction: Dictionary, index: int) -> Dictionary:
	match instruction.op:
		"label":
			label_entered.emit(instruction.name)
		"say":
			_resume_pc = index
			var event := _say_event(instruction)
			_interaction(event)
			return event
		"menu":
			var event := _menu_event(instruction)
			if event.choices.is_empty():
				# Aucun choix visible : Ren'Py passe le menu.
				pc = instruction.end
				return {}
			_menu = instruction
			_resume_pc = index
			_interaction(event.prompt)
			return event
		"navigate":
			var map_id: String = instruction.map
			if not navigation.cartes.has(map_id):
				_fail("carte inconnue « %s » (game/navigation.json)" % map_id)
				return {}
			_apply_presence()
			if _fatal != "":
				return {}
			if map_targets(map_id).is_empty():
				# Aucun lieu accessible : comme un menu sans choix, on continue.
				return {}
			_navigate = map_id
			_navigate_here = instruction.get("here", "")
			_resume_pc = index
			_interaction(null)
			return _navigate_event()
		"movie":
			_resume_pc = index
			_interaction(null)
			return {"type": "movie", "path": instruction.path}
		"pause":
			_resume_pc = index
			_interaction(null)
			return {"type": "pause", "seconds": instruction.seconds}
		"scene":
			stage.scene = instruction.image
			stage.shown = {}
			return {"type": "scene", "image": instruction.image, "transition": instruction.transition}
		"show":
			var at: String = instruction.at
			if at.is_empty():
				at = stage.shown.get(instruction.tag, {}).get("at", "center")
			stage.shown[instruction.tag] = {"image": instruction.image, "at": at}
			return {"type": "show", "tag": instruction.tag, "image": instruction.image, "at": at, "transition": instruction.transition}
		"hide":
			stage.shown.erase(instruction.tag)
			return {"type": "hide", "tag": instruction.tag, "transition": instruction.transition}
		"with":
			return {"type": "with", "transition": instruction.transition}
		"audio":
			if instruction.channel == "music":
				stage.music = instruction.file if instruction.action == "play" else ""
			var event: Dictionary = instruction.duplicate()
			event.erase("op")
			event.type = "audio"
			return event
		"assign":
			var value = _eval(instruction.expr)
			if _fatal == "":
				store[instruction.name] = value
		"if_false":
			if not _truthy(_eval(instruction.expr)):
				pc = instruction.target
		"goto":
			pc = instruction.target
		"jump":
			pc = story.labels[instruction.label]
		"call":
			call_stack.append(pc)
			pc = story.labels[instruction.label]
		"return":
			if call_stack.is_empty():
				_ended = true
				return {"type": "end"}
			pc = call_stack.pop_back()
	return {}


## Enregistre une interaction : réplique dans l'historique et point de retour arrière.
func _interaction(say_event: Variant) -> void:
	_history_before = _history_total
	if say_event != null:
		history.append({"name": say_event.name, "color": say_event.color, "text": say_event.text})
		_history_total += 1
		if history.size() > HISTORY_LENGTH:
			history.pop_front()
	_checkpoints.append({
		"resume": _resume_pc,
		"store": store.duplicate(true),
		"call_stack": call_stack.duplicate(),
		"stage": stage.duplicate(true),
		"history_total": _history_before,
	})
	if _checkpoints.size() > ROLLBACK_LENGTH:
		_checkpoints.pop_front()


## Réplique à afficher : sa traduction si elle existe (même identifiant, donc même
## « texte déjà lu » dans toutes les langues), sinon l'original.
func _say_event(instruction: Dictionary) -> Dictionary:
	var id: String = instruction.get("id", "")
	var said: Dictionary = translation.get("lines", {}).get(id, instruction)
	var event := {"type": "say", "id": id, "who": said.who, "name": said.name,
		"color": "", "what_color": "", "text": _interpolate(said.text)}
	if said.who != "":
		var character: Dictionary = story.characters[said.who]
		event.name = character.name
		event.color = character.color
		event.what_color = character.what_color
	if event.name != "":
		event.name = _interpolate(translate_string(event.name))
	return event


func _menu_event(instruction: Dictionary) -> Dictionary:
	var choices: Array = []
	for i in instruction.choices.size():
		var choice: Dictionary = instruction.choices[i]
		if choice.expr != "" and not _truthy(_eval(choice.expr)):
			continue
		choices.append({"index": i, "text": _interpolate(translate_string(choice.text))})
	var prompt = null
	if instruction.prompt != null:
		prompt = _say_event(instruction.prompt)
	return {"type": "menu", "prompt": prompt, "choices": choices}


func _eval(expr: String) -> Variant:
	var expression: Expression = _expressions.get(expr)
	if expression == null:
		expression = Expression.new()
		if expression.parse(expr, _names) != OK:
			_fail("expression invalide « %s » : %s" % [expr, expression.get_error_text()])
			return null
		_expressions[expr] = expression
	var values: Array = []
	for name in _names:
		values.append(store[name])
	var result = expression.execute(values, null, false)
	if expression.has_execute_failed():
		_fail("impossible d'évaluer « %s » : %s" % [expr, expression.get_error_text()])
		return null
	return result


func _fail(message: String) -> void:
	if _fatal == "":
		_fatal = "%s: %s" % [_where, message]


## Remplace [variable] par sa valeur ; [[ produit un crochet littéral.
func _interpolate(text: String) -> String:
	if text.find("[") == -1:
		return text
	var out := ""
	var i := 0
	while i < text.length():
		var c := text[i]
		if c == "[":
			if text.substr(i + 1, 1) == "[":
				out += "["
				i += 2
				continue
			var close := text.find("]", i)
			if close > i:
				var name := text.substr(i + 1, close - i - 1)
				if store.has(name):
					out += _to_text(store[name])
					i = close + 1
					continue
		out += c
		i += 1
	return out


func _to_ref(index: int) -> Array:
	var best := ""
	var best_index := -1
	for name in story.labels:
		var start: int = story.labels[name]
		if start <= index and start > best_index:
			best = name
			best_index = start
	return [best, index - best_index]


func _from_ref(ref: Variant) -> int:
	if typeof(ref) != TYPE_ARRAY or ref.size() != 2:
		return -1
	var label: String = str(ref[0])
	# Label renommé depuis la sauvegarde (plusieurs passes : chaînes dans n'importe quel ordre).
	var label_renames: Array = renames.get("scenes", [])
	for _pass in label_renames.size():
		for rename in label_renames:
			if label == rename.ancien:
				label = rename.nouveau
	if not story.labels.has(label):
		return -1
	var target: int = story.labels[label] + int(ref[1])
	return target if target < story.program.size() else -1


static func _truthy(value: Variant) -> bool:
	match typeof(value):
		TYPE_NIL:
			return false
		TYPE_BOOL:
			return value
		TYPE_INT, TYPE_FLOAT:
			return value != 0
		TYPE_STRING, TYPE_STRING_NAME:
			return not String(value).is_empty()
		TYPE_ARRAY, TYPE_DICTIONARY:
			return not value.is_empty()
	return true


## Affichage à la manière de Python (True, False, None).
static func _to_text(value: Variant) -> String:
	match typeof(value):
		TYPE_NIL:
			return "None"
		TYPE_BOOL:
			return "True" if value else "False"
	return str(value)
