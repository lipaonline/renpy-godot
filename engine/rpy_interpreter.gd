## Exécute une histoire compilée par rpy_parser.gd.
##
## L'interpréteur ne dessine rien : next() renvoie l'événement suivant et le
## lecteur décide comment l'afficher. Événements :
##   bloquants     say, menu, movie, pause, end, error
##   non bloquants scene, show, hide, audio, with
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

var _names: PackedStringArray
var _expressions: Dictionary = {}
var _menu = null
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
	var saved: Dictionary = state.get("store", {})
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
	_ended = false
	return _fatal == ""


## Copie complète de l'état en mémoire, utilisée par l'explorateur de routes.
func snapshot() -> Dictionary:
	return {"pc": pc, "store": store.duplicate(true), "call_stack": call_stack.duplicate(),
		"stage": stage.duplicate(true), "menu": _menu, "resume": _resume_pc, "ended": _ended}


func restore(snap: Dictionary) -> void:
	pc = snap.pc
	store = snap.store.duplicate(true)
	call_stack = snap.call_stack.duplicate()
	stage = snap.stage.duplicate(true)
	_menu = snap.menu
	_resume_pc = snap.resume
	_ended = snap.ended
	_fatal = ""
	_checkpoints.clear()


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


func _say_event(instruction: Dictionary) -> Dictionary:
	var event := {"type": "say", "id": instruction.get("id", ""), "who": instruction.who, "name": instruction.name,
		"color": "", "what_color": "", "text": _interpolate(instruction.text)}
	if instruction.who != "":
		var character: Dictionary = story.characters[instruction.who]
		event.name = character.name
		event.color = character.color
		event.what_color = character.what_color
	event.name = _interpolate(event.name)
	return event


func _menu_event(instruction: Dictionary) -> Dictionary:
	var choices: Array = []
	for i in instruction.choices.size():
		var choice: Dictionary = instruction.choices[i]
		if choice.expr != "" and not _truthy(_eval(choice.expr)):
			continue
		choices.append({"index": i, "text": _interpolate(choice.text)})
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
	if typeof(ref) != TYPE_ARRAY or ref.size() != 2 or not story.labels.has(ref[0]):
		return -1
	var target: int = story.labels[ref[0]] + int(ref[1])
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
