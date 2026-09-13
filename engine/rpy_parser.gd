## Compilateur du sous-ensemble commun Ren'Py / Godot.
##
## Transforme des fichiers .rpy respectant SPEC-sous-ensemble-renpy.md en un
## programme linéaire exécuté par rpy_interpreter.gd. Tout ce qui sort du
## sous-ensemble produit une erreur avec fichier et numéro de ligne.
##
##   var parser = preload("res://engine/rpy_parser.gd").new()
##   parser.parse_dir("res://game/story")
##   var story = parser.finish()   # null en cas d'erreur : voir parser.errors
extends RefCounted

const IDENT := "[A-Za-z_][A-Za-z0-9_]*"
const DQ_STRING := "\"(?:[^\"\\\\]|\\\\.)*\""
const SQ_STRING := "'(?:[^'\\\\]|\\\\.)*'"
const STR_RE := "(?:" + DQ_STRING + "|" + SQ_STRING + ")"

const TRANSITIONS := ["dissolve", "fade", "None"]
const POSITIONS := ["left", "center", "right", "truecenter"]
const CHANNELS := ["music", "sound", "audio"]
const FUNCTIONS := ["min", "max", "abs", "str", "int", "float"]
const RESERVED := ["and", "or", "not", "in", "True", "False", "None"]
const BLOCK_STATEMENTS := ["if", "elif", "else", "while", "menu", "label"]
const IMAGE_MODIFIERS := ["behind", "onlayer", "zorder", "as", "expression"]
## Instructions Ren'Py reconnues mais volontairement exclues du sous-ensemble.
const OUT_OF_SUBSET := ["python", "init", "screen", "transform", "style", "translate",
	"nvl", "voice", "queue", "camera", "layeredimage", "testcase", "for"]

var errors: PackedStringArray = []

var _program: Array = []
var _labels: Dictionary = {}
var _characters: Dictionary = {}
var _inits: Array = []
var _images: Dictionary = {}
var _declared: Dictionary = {}
var _variables: Dictionary = {}
var _checks: Array = []
var _file := ""
var _current_label := ""
var _re: Dictionary = {}


func _init() -> void:
	var patterns := {
		"label": "^label\\s+(" + IDENT + ")\\s*:$",
		"define": "^(define|default)\\s+(" + IDENT + ")\\s*=\\s*(.+)$",
		"character": "^Character\\s*\\((.*)\\)$",
		"image": "^image\\s+([A-Za-z0-9_ ]+?)\\s*=\\s*(" + STR_RE + ")$",
		"assign": "^(" + IDENT + ")\\s*(\\+=|-=|\\*=|=(?!=))\\s*(.+)$",
		"movie": "^renpy\\.movie_cutscene\\s*\\(\\s*(" + STR_RE + ")\\s*\\)$",
		"pause": "^pause(?:\\s+([0-9]*\\.?[0-9]+))?$",
		"renpy_pause": "^renpy\\.pause\\s*\\(\\s*([0-9]*\\.?[0-9]+)?\\s*\\)$",
		"choice": "^(" + STR_RE + ")\\s*(?:if\\s+(.+?))?\\s*:$",
		"say": "^(?:(" + IDENT + ")\\s+)?(" + STR_RE + ")$",
		"say_named": "^(" + STR_RE + ")\\s+(" + STR_RE + ")$",
		"say_attributes": "^" + IDENT + "(?:\\s+[A-Za-z0-9_]+)+\\s+" + STR_RE + "$",
		"goto": "^(jump|call)\\s+(" + IDENT + ")$",
		"window": "^window\\s+(show|hide|auto)$",
		"kwarg": "^(" + IDENT + ")\\s*=\\s*(.+)$",
		"string": "^" + STR_RE + "$",
		"ident": "^" + IDENT + "$",
		"image_word": "^[A-Za-z0-9_]+$",
		"number": "^[0-9]*\\.?[0-9]+$",
		"interpolation": "\\[([^\\]]*)\\]",
	}
	for key in patterns:
		_re[key] = RegEx.create_from_string(patterns[key])


# --- Entrées -------------------------------------------------------------------

func parse_dir(dir: String) -> void:
	var files := _list_rpy(dir)
	if files.is_empty():
		errors.append("%s : aucun fichier .rpy trouvé" % dir)
	for path in files:
		parse_file(path)


func parse_file(path: String) -> void:
	if not FileAccess.file_exists(path):
		errors.append("%s : fichier introuvable" % path)
		return
	parse_string(FileAccess.get_file_as_string(path), path)


func parse_string(source: String, file_name: String) -> void:
	_file = file_name
	_current_label = ""
	for line in _build_tree(_read_lines(source)):
		_compile_toplevel(line)
	# Comme dans Ren'Py, la fin d'un fichier équivaut à un return.
	_emit({"op": "return", "line": 0})


## Vérifie les références croisées et renvoie l'histoire compilée, ou null.
func finish() -> Variant:
	var names := PackedStringArray(_variables.keys())
	for check in _checks:
		_file = check.file
		var kind: String = check.kind
		if kind == "label" and not _labels.has(check.name):
			_error(check.line, "label inconnu : « %s »" % check.name)
		elif kind == "character" and not _characters.has(check.name):
			_error(check.line, "personnage inconnu : « %s » (déclarez-le avec define %s = Character(\"…\"))" % [check.name, check.name])
		elif kind == "var" and not _variables.has(check.name):
			_error(check.line, "variable inconnue dans le texte : [%s]" % check.name)
		elif kind == "expr":
			_check_expression(check, names)
	if not _labels.has("start"):
		errors.append("label « start » introuvable : c'est le point d'entrée du jeu")
	if not errors.is_empty():
		return null
	return {
		"program": _program,
		"labels": _labels,
		"characters": _characters,
		"inits": _inits,
		"images": _images,
		"variables": names,
	}


# --- Lecture et indentation ------------------------------------------------------

func _list_rpy(dir: String) -> PackedStringArray:
	var files := PackedStringArray()
	if not DirAccess.dir_exists_absolute(dir):
		return files
	for file_name in DirAccess.get_files_at(dir):
		if file_name.get_extension() == "rpy":
			files.append(dir.path_join(file_name))
	for sub_dir in DirAccess.get_directories_at(dir):
		files.append_array(_list_rpy(dir.path_join(sub_dir)))
	files.sort()
	return files


func _read_lines(source: String) -> Array:
	var lines: Array = []
	var raw := source.trim_prefix("﻿").replace("\r\n", "\n").split("\n")
	for i in raw.size():
		var number := i + 1
		var body := _strip_comment(raw[i], number)
		if body.strip_edges().is_empty():
			continue
		var indent := 0
		while body[indent] == " ":
			indent += 1
		if body[indent] == "\t":
			_error(number, "tabulation dans l'indentation : Ren'Py n'accepte que des espaces")
			continue
		lines.append({"n": number, "indent": indent, "text": body.strip_edges(), "block": []})
	return lines


func _strip_comment(line: String, number: int) -> String:
	var quote := ""
	var i := 0
	while i < line.length():
		var c := line[i]
		if quote != "":
			if c == "\\":
				i += 1
			elif c == quote:
				quote = ""
		elif c == "\"" or c == "'":
			quote = c
		elif c == "#":
			return line.substr(0, i)
		i += 1
	if quote != "":
		_error(number, "chaîne non terminée (les chaînes sur plusieurs lignes sont hors sous-ensemble)")
		return ""
	return line


## Regroupe les lignes en arbre : chaque ligne finissant par « : » possède un bloc.
func _build_tree(lines: Array) -> Array:
	var root: Array = []
	var stack: Array = [[0, root]]
	var opener = null
	for line in lines:
		if opener != null:
			if line.indent > stack.back()[0]:
				stack.append([line.indent, opener.block])
			else:
				_error(opener.n, "bloc indenté attendu après « : »")
			opener = null
		while stack.size() > 1 and line.indent < stack.back()[0]:
			stack.pop_back()
		if line.indent != stack.back()[0]:
			_error(line.n, "indentation incohérente")
			continue
		stack.back()[1].append(line)
		if line.text.ends_with(":"):
			opener = line
	if opener != null:
		_error(opener.n, "bloc indenté attendu après « : »")
	return root


# --- Premier niveau --------------------------------------------------------------

func _compile_toplevel(line: Dictionary) -> void:
	var keyword := _keyword(line.text)
	match keyword:
		"label":
			var m: RegExMatch = _re.label.search(line.text)
			if m == null:
				_error(line.n, "syntaxe attendue : label nom:")
				return
			var name := m.get_string(1)
			if _labels.has(name):
				_error(line.n, "label « %s » déjà défini" % name)
				return
			_current_label = name
			_labels[name] = _emit({"op": "label", "name": name, "line": line.n})
			_compile_block(line.block)
		"define", "default":
			_compile_define(line)
		"image":
			_compile_image(line)
		_:
			if keyword in OUT_OF_SUBSET:
				_error(line.n, _out_of_subset(keyword))
			else:
				_error(line.n, "seuls label, define, default et image sont autorisés au premier niveau")


func _compile_define(line: Dictionary) -> void:
	var m: RegExMatch = _re.define.search(line.text)
	if m == null:
		_error(line.n, "syntaxe attendue : %s nom = valeur" % _keyword(line.text))
		return
	var kind := m.get_string(1)
	var name := m.get_string(2)
	var value := m.get_string(3).strip_edges()
	if _characters.has(name) or _declared.has(name) or name in RESERVED or name in FUNCTIONS:
		_error(line.n, "« %s » est déjà déclaré ou réservé" % name)
		return
	var character: RegExMatch = _re.character.search(value)
	if character != null:
		if kind != "define":
			_error(line.n, "un personnage se déclare avec define, pas default")
		_characters[name] = _parse_character(character.get_string(1), line)
		return
	_declared[name] = true
	_variables[name] = true
	_inits.append({"kind": kind, "name": name, "expr": _expression(value, line), "file": _file.get_file(), "line": line.n})


func _parse_character(args: String, line: Dictionary) -> Dictionary:
	var character := {"name": "", "color": "", "what_color": ""}
	var parts := _split_args(args)
	for i in parts.size():
		var part := parts[i].strip_edges()
		var kwarg: RegExMatch = _re.kwarg.search(part)
		if kwarg == null:
			if i == 0 and _re.string.search(part) != null:
				character.name = _unquote(part)
			elif i != 0 or part != "None":
				_error(line.n, "argument inattendu dans Character() : %s" % part)
			continue
		var key := kwarg.get_string(1)
		var value := kwarg.get_string(2).strip_edges()
		if key not in ["color", "who_color", "what_color"]:
			_error(line.n, "argument de Character() non supporté : %s (autorisés : color, who_color, what_color)" % key)
		elif _re.string.search(value) == null:
			_error(line.n, "%s doit être une chaîne, par exemple \"#c8a2ff\"" % key)
		else:
			character["what_color" if key == "what_color" else "color"] = _unquote(value)
	return character


func _compile_image(line: Dictionary) -> void:
	var m: RegExMatch = _re.image.search(line.text)
	if m == null:
		_error(line.n, "syntaxe attendue : image nom attribut = \"images/fichier.png\"")
		return
	var name := " ".join(m.get_string(1).to_lower().split(" ", false))
	_images[name] = _unquote(m.get_string(2))


# --- Blocs -----------------------------------------------------------------------

func _compile_block(block: Array) -> void:
	var i := 0
	while i < block.size():
		var line: Dictionary = block[i]
		var keyword := _keyword(line.text)
		if keyword == "if":
			i = _compile_if(block, i)
			continue
		if not line.block.is_empty() and keyword not in BLOCK_STATEMENTS:
			_error(line.n, "bloc inattendu après cette ligne")
		match keyword:
			"while":
				_compile_while(line)
			"menu":
				_compile_menu(line)
			"elif", "else":
				_error(line.n, "« %s » sans « if » juste avant" % keyword)
			"label", "define", "default", "image":
				_error(line.n, "« %s » doit être placé au premier niveau (sans indentation)" % keyword)
			"scene":
				_compile_scene(line)
			"show":
				_compile_show(line)
			"hide":
				_compile_hide(line)
			"with":
				_compile_with(line)
			"jump", "call":
				_compile_goto(line)
			"return":
				if line.text == "return":
					_emit({"op": "return", "line": line.n})
				else:
					_error(line.n, "return ne prend pas de valeur dans le sous-ensemble")
			"pass":
				if line.text != "pass":
					_error(line.n, "syntaxe attendue : pass")
			"pause":
				_compile_pause(line)
			"play":
				_compile_play(line)
			"stop":
				_compile_stop(line)
			"window":
				if _re.window.search(line.text) == null:
					_error(line.n, "syntaxe attendue : window show | hide | auto")
			"$":
				_compile_python(line)
			_:
				if keyword in OUT_OF_SUBSET:
					_error(line.n, _out_of_subset(keyword))
				else:
					var say = _parse_say(line)
					if say != null:
						_emit(say)
		i += 1


func _compile_if(block: Array, start: int) -> int:
	var end_jumps: Array = []
	var i := start
	while i < block.size():
		var line: Dictionary = block[i]
		var keyword := _keyword(line.text)
		if i > start and keyword != "elif" and keyword != "else":
			break
		if keyword == "else":
			if line.text.replace(" ", "") != "else:":
				_error(line.n, "syntaxe attendue : else:")
			_compile_block(line.block)
			i += 1
			break
		var jump_if_false := _emit({"op": "if_false", "expr": _expression(_condition(line, keyword), line), "target": -1, "line": line.n})
		_compile_block(line.block)
		end_jumps.append(_emit({"op": "goto", "target": -1, "line": line.n}))
		_program[jump_if_false].target = _program.size()
		i += 1
	for index in end_jumps:
		_program[index].target = _program.size()
	return i


func _compile_while(line: Dictionary) -> void:
	var top := _program.size()
	var exit_jump := _emit({"op": "if_false", "expr": _expression(_condition(line, "while"), line), "target": -1, "line": line.n})
	_compile_block(line.block)
	_emit({"op": "goto", "target": top, "line": line.n})
	_program[exit_jump].target = _program.size()


func _compile_menu(line: Dictionary) -> void:
	if line.text.replace(" ", "") != "menu:":
		_error(line.n, "syntaxe attendue : menu: (menus nommés et « set » hors sous-ensemble)")
		return
	var menu := {"op": "menu", "prompt": null, "choices": [], "end": -1, "line": line.n}
	_emit(menu)
	var end_jumps: Array = []
	for child in line.block:
		if not child.text.ends_with(":"):
			if menu.prompt != null or not menu.choices.is_empty():
				_error(child.n, "seule une réplique, placée avant les choix, est autorisée dans un menu")
				continue
			menu.prompt = _parse_say(child)
			continue
		var m: RegExMatch = _re.choice.search(child.text)
		if m == null:
			_error(child.n, "choix de menu attendu : \"Texte du choix\" [if condition]:")
			continue
		var text := _unquote(m.get_string(1))
		_check_text(text, child)
		var condition := m.get_string(2).strip_edges()
		menu.choices.append({
			"text": text,
			"expr": "" if condition.is_empty() else _expression(condition, child),
			"target": _program.size(),
		})
		_compile_block(child.block)
		end_jumps.append(_emit({"op": "goto", "target": -1, "line": child.n}))
	if menu.choices.is_empty():
		_error(line.n, "un menu doit proposer au moins un choix")
	menu.end = _program.size()
	for index in end_jumps:
		_program[index].target = _program.size()


# --- Instructions simples ----------------------------------------------------------

func _compile_scene(line: Dictionary) -> void:
	var parts := _image_clauses(line, false)
	_emit({"op": "scene", "image": parts.image, "transition": parts.transition, "line": line.n})


func _compile_show(line: Dictionary) -> void:
	var parts := _image_clauses(line, true)
	var image: String = parts.image
	if image.is_empty():
		_error(line.n, "show attend un nom d'image")
		return
	_emit({"op": "show", "image": image, "tag": image.get_slice(" ", 0), "at": parts.at, "transition": parts.transition, "line": line.n})


func _compile_hide(line: Dictionary) -> void:
	var parts := _image_clauses(line, false)
	var image: String = parts.image
	if image.is_empty():
		_error(line.n, "hide attend un nom d'image")
		return
	_emit({"op": "hide", "tag": image.get_slice(" ", 0), "transition": parts.transition, "line": line.n})


func _compile_with(line: Dictionary) -> void:
	var words: PackedStringArray = line.text.split(" ", false)
	if words.size() != 2 or words[1] not in TRANSITIONS:
		_error(line.n, "syntaxe attendue : with %s" % " | ".join(PackedStringArray(TRANSITIONS)))
		return
	_emit({"op": "with", "transition": "" if words[1] == "None" else words[1], "line": line.n})


## Analyse « scene|show|hide nom attributs [at position] [with transition] ».
func _image_clauses(line: Dictionary, allow_at: bool) -> Dictionary:
	var words: PackedStringArray = line.text.split(" ", false)
	var result := {"image": "", "at": "", "transition": ""}
	var names := PackedStringArray()
	var clauses_started := false
	var i := 1
	while i < words.size():
		var word := words[i]
		if word == "at" or word == "with":
			clauses_started = true
			if i + 1 >= words.size():
				_error(line.n, "« %s » doit être suivi d'une valeur" % word)
				break
			var value := words[i + 1]
			if word == "with":
				if value in TRANSITIONS:
					result.transition = "" if value == "None" else value
				else:
					_error(line.n, "transition non supportée : %s (autorisées : %s)" % [value, ", ".join(PackedStringArray(TRANSITIONS))])
			elif not allow_at:
				_error(line.n, "« at » n'est pas supporté ici")
			elif value in POSITIONS:
				result.at = value
			else:
				_error(line.n, "position non supportée : %s (autorisées : %s)" % [value, ", ".join(PackedStringArray(POSITIONS))])
			i += 2
			continue
		if word in IMAGE_MODIFIERS or clauses_started or _re.image_word.search(word) == null:
			_error(line.n, "« %s » n'est pas supporté dans le sous-ensemble" % word)
			break
		names.append(word)
		i += 1
	result.image = " ".join(names)
	return result


func _compile_goto(line: Dictionary) -> void:
	var m: RegExMatch = _re.goto.search(line.text)
	if m == null:
		_error(line.n, "syntaxe attendue : %s nom_du_label" % _keyword(line.text))
		return
	_checks.append({"kind": "label", "name": m.get_string(2), "file": _file, "line": line.n})
	_emit({"op": m.get_string(1), "label": m.get_string(2), "line": line.n})


func _compile_pause(line: Dictionary) -> void:
	var m: RegExMatch = _re.pause.search(line.text)
	if m == null:
		_error(line.n, "syntaxe attendue : pause ou pause 1.5")
		return
	_emit({"op": "pause", "seconds": _seconds(m.get_string(1)), "line": line.n})


func _compile_play(line: Dictionary) -> void:
	var tokens := _tokens(line.text)
	if tokens.size() < 3 or tokens[1] not in CHANNELS or _re.string.search(tokens[2]) == null:
		_error(line.n, "syntaxe attendue : play music \"audio/fichier.ogg\" [fadein 1.0] [loop|noloop]")
		return
	var instruction := {"op": "audio", "action": "play", "channel": tokens[1], "file": _unquote(tokens[2]),
		"fadein": 0.0, "fadeout": 0.0, "loop": tokens[1] == "music", "line": line.n}
	var i := 3
	while i < tokens.size():
		var token := tokens[i]
		if (token == "fadein" or token == "fadeout") and i + 1 < tokens.size() and _re.number.search(tokens[i + 1]) != null:
			instruction[token] = tokens[i + 1].to_float()
			i += 2
		elif token == "loop" or token == "noloop":
			instruction.loop = token == "loop"
			i += 1
		else:
			_error(line.n, "option audio non supportée : %s" % token)
			i += 1
	_emit(instruction)


func _compile_stop(line: Dictionary) -> void:
	var tokens := _tokens(line.text)
	if tokens.size() < 2 or tokens[1] not in CHANNELS:
		_error(line.n, "syntaxe attendue : stop music [fadeout 1.0]")
		return
	var instruction := {"op": "audio", "action": "stop", "channel": tokens[1], "fadeout": 0.0, "line": line.n}
	if tokens.size() == 4 and tokens[2] == "fadeout" and _re.number.search(tokens[3]) != null:
		instruction.fadeout = tokens[3].to_float()
	elif tokens.size() != 2:
		_error(line.n, "syntaxe attendue : stop music [fadeout 1.0]")
	_emit(instruction)


func _compile_python(line: Dictionary) -> void:
	var code: String = line.text.substr(1).strip_edges()
	var m: RegExMatch = _re.movie.search(code)
	if m != null:
		_emit({"op": "movie", "path": _unquote(m.get_string(1)), "line": line.n})
		return
	m = _re.renpy_pause.search(code)
	if m != null:
		_emit({"op": "pause", "seconds": _seconds(m.get_string(1)), "line": line.n})
		return
	m = _re.assign.search(code)
	if m == null:
		_error(line.n, "Python non supporté : seules les affectations (x = …, x += …, x -= …, x *= …) et renpy.movie_cutscene(…) sont autorisées")
		return
	var name := m.get_string(1)
	var operator := m.get_string(2)
	var value := m.get_string(3).strip_edges()
	if _characters.has(name) or name in RESERVED or name in FUNCTIONS:
		_error(line.n, "impossible d'affecter « %s »" % name)
		return
	_variables[name] = true
	var source := value if operator == "=" else "%s %s (%s)" % [name, operator.substr(0, 1), value]
	_emit({"op": "assign", "name": name, "expr": _expression(source, line), "line": line.n})


func _parse_say(line: Dictionary) -> Variant:
	var text: String = line.text
	var m: RegExMatch = _re.say.search(text)
	if m != null:
		var who := m.get_string(1)
		if who != "":
			_checks.append({"kind": "character", "name": who, "file": _file, "line": line.n})
		var said := _unquote(m.get_string(2))
		_check_text(said, line)
		return {"op": "say", "who": who, "name": "", "text": said, "id": _say_id(who, said), "line": line.n, "file": _file.get_file()}
	m = _re.say_named.search(text)
	if m != null:
		var said := _unquote(m.get_string(2))
		var speaker := _unquote(m.get_string(1))
		_check_text(said, line)
		return {"op": "say", "who": "", "name": speaker, "text": said, "id": _say_id(speaker, said), "line": line.n, "file": _file.get_file()}
	if _re.say_attributes.search(text) != null:
		_error(line.n, "attributs d'image dans une réplique non supportés : utilisez « show » avant la réplique")
	else:
		_error(line.n, "instruction non reconnue : %s" % text)
	return null


# --- Expressions -------------------------------------------------------------------

## Traduit une expression Python simple en expression Godot et planifie sa vérification.
func _expression(source: String, line: Dictionary) -> String:
	var translated := _translate(source)
	_checks.append({"kind": "expr", "source": source, "expr": translated.expr, "idents": translated.idents,
		"error": translated.error, "file": _file, "line": line.n})
	return translated.expr


func _translate(source: String) -> Dictionary:
	var out := ""
	var idents: Array = []
	var error := ""
	var i := 0
	while i < source.length():
		var c := source[i]
		if c == "\"" or c == "'":
			var j := i + 1
			while j < source.length() and source[j] != c:
				if source[j] == "\\":
					j += 1
				j += 1
			out += source.substr(i, j - i + 1)
			i = j + 1
			continue
		if _is_ident_char(c):
			var j := i
			while j < source.length() and (_is_ident_char(source[j]) or source[j] == "."):
				j += 1
			var word := source.substr(i, j - i)
			i = j
			if c.unicode_at(0) <= 57:
				out += word
				continue
			match word:
				"True":
					out += "true"
				"False":
					out += "false"
				"None":
					out += "null"
				"and", "or", "not", "in":
					out += word
				"is", "if", "else", "for", "lambda":
					error = "construction Python non supportée : « %s »" % word
					out += word
				_:
					if "." in word:
						error = "accès par point non supporté : « %s »" % word
					elif word not in FUNCTIONS or _next_char(source, i) != "(":
						idents.append(word)
					out += word
			continue
		if c == "/" or c == "%":
			error = "opérateur « %s » non supporté (résultat différent entre Python et Godot)" % c
		out += c
		i += 1
	return {"expr": out, "idents": idents, "error": error}


func _check_expression(check: Dictionary, names: PackedStringArray) -> void:
	if check.error != "":
		_error(check.line, "%s dans « %s »" % [check.error, check.source])
		return
	for ident in check.idents:
		if not _variables.has(ident):
			_error(check.line, "variable inconnue « %s » dans « %s » (déclarez-la avec default)" % [ident, check.source])
			return
	var expression := Expression.new()
	if expression.parse(check.expr, names) != OK:
		_error(check.line, "expression invalide « %s » : %s" % [check.source, expression.get_error_text()])


func _condition(line: Dictionary, keyword: String) -> String:
	var text: String = line.text
	if not text.ends_with(":"):
		_error(line.n, "« %s » doit se terminer par « : » et être suivi d'un bloc indenté" % keyword)
		return "False"
	var condition := text.substr(keyword.length(), text.length() - keyword.length() - 1).strip_edges()
	if condition.is_empty():
		_error(line.n, "condition manquante après « %s »" % keyword)
		return "False"
	return condition


func _check_text(text: String, line: Dictionary) -> void:
	for m in _re.interpolation.search_all(text.replace("[[", "")):
		var name: String = m.get_string(1)
		if _re.ident.search(name) == null:
			_error(line.n, "interpolation non supportée : [%s] (seules les variables simples [nom] sont permises)" % name)
		else:
			_checks.append({"kind": "var", "name": name, "file": _file, "line": line.n})


# --- Utilitaires -------------------------------------------------------------------

func _emit(instruction: Dictionary) -> int:
	if not instruction.has("file"):
		instruction.file = _file.get_file()
	instruction.in_label = _current_label
	_program.append(instruction)
	return _program.size() - 1


## Identifiant stable d'une réplique (texte déjà lu) : ne change que si le label,
## le personnage ou le texte changent, pas quand on insère des lignes ailleurs.
func _say_id(speaker: String, text: String) -> String:
	return ("%s|%s|%s" % [_current_label, speaker, text]).md5_text()


func _error(line: int, message: String) -> void:
	errors.append("%s:%d: %s" % [_file.get_file(), line, message])


func _out_of_subset(keyword: String) -> String:
	return "« %s » ne fait pas partie du sous-ensemble : ce code doit rester dans un fichier Ren'Py hors de game/story/" % keyword


func _keyword(text: String) -> String:
	if text.begins_with("$"):
		return "$"
	var end := 0
	while end < text.length() and _is_ident_char(text[end]):
		end += 1
	return text.substr(0, end)


func _is_ident_char(c: String) -> bool:
	var u := c.unicode_at(0)
	return u == 95 or (u >= 97 and u <= 122) or (u >= 65 and u <= 90) or (u >= 48 and u <= 57)


func _next_char(text: String, from: int) -> String:
	var i := from
	while i < text.length() and text[i] == " ":
		i += 1
	return text[i] if i < text.length() else ""


func _seconds(value: String) -> float:
	return value.to_float() if value != "" else -1.0


func _unquote(literal: String) -> String:
	var body := literal.substr(1, literal.length() - 2)
	var out := ""
	var i := 0
	while i < body.length():
		var c := body[i]
		if c == "\\" and i + 1 < body.length():
			i += 1
			match body[i]:
				"n":
					out += "\n"
				"t":
					out += "\t"
				_:
					out += body[i]
		else:
			out += c
		i += 1
	return out


## Découpe des arguments séparés par des virgules, en respectant chaînes et parenthèses.
func _split_args(source: String) -> PackedStringArray:
	var parts := PackedStringArray()
	var depth := 0
	var quote := ""
	var start := 0
	var i := 0
	while i < source.length():
		var c := source[i]
		if quote != "":
			if c == "\\":
				i += 1
			elif c == quote:
				quote = ""
		elif c == "\"" or c == "'":
			quote = c
		elif c in "([{":
			depth += 1
		elif c in ")]}":
			depth -= 1
		elif c == "," and depth == 0:
			parts.append(source.substr(start, i - start))
			start = i + 1
		i += 1
	if not source.substr(start).strip_edges().is_empty():
		parts.append(source.substr(start))
	return parts


## Découpe une ligne en mots, en gardant les chaînes entières (avec leurs guillemets).
func _tokens(text: String) -> PackedStringArray:
	var tokens := PackedStringArray()
	var current := ""
	var quote := ""
	var i := 0
	while i < text.length():
		var c := text[i]
		if quote != "":
			current += c
			if c == "\\" and i + 1 < text.length():
				i += 1
				current += text[i]
			elif c == quote:
				quote = ""
		elif c == "\"" or c == "'":
			quote = c
			current += c
		elif c == " ":
			if current != "":
				tokens.append(current)
				current = ""
		else:
			current += c
		i += 1
	if current != "":
		tokens.append(current)
	return tokens
