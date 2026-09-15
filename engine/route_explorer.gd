## Explore toutes les routes d'une histoire compilée en essayant chaque choix de
## chaque menu et chaque lieu accessible de chaque carte. Signale les labels jamais
## atteints, les choix et lieux jamais proposés, les fins atteintes et les erreurs d'exécution.
extends RefCounted

const Interpreter = preload("res://engine/rpy_interpreter.gd")

var max_states := 20000


## navigation : données de engine/navigation.gd (champ « data »), si le script affiche des cartes.
func explore(story: Dictionary, navigation := {}) -> Dictionary:
	var interp := Interpreter.new(story)
	interp.track_coverage = true
	if not navigation.is_empty():
		interp.set_navigation(navigation)
	interp.start()
	var pending: Array = [interp.snapshot()]
	var seen: Dictionary = {}
	var endings: Dictionary = {}
	var offered: Dictionary = {}
	var offered_places: Dictionary = {}
	var errors: Array = []
	var explored := 0
	while not pending.is_empty() and explored < max_states:
		explored += 1
		interp.restore(pending.pop_back())
		var running := true
		while running:
			var event := interp.next()
			match event.type:
				"menu":
					running = false
					var menu_pc := interp.menu_pc()
					var snap := interp.snapshot()
					for choice in event.choices:
						offered["%d:%d" % [menu_pc, choice.index]] = true
						interp.restore(snap)
						interp.choose(choice.index)
						_push(interp, seen, pending)
				"navigate":
					running = false
					var snap := interp.snapshot()
					for target in interp.map_targets(event.map):
						offered_places["%s:%d" % [target.carte, target.rang]] = true
						interp.restore(snap)
						interp.apply_costs(target.get("costs", []))
						interp.navigate_to(target.label)
						_push(interp, seen, pending)
				"end":
					running = false
					var label := interp.current_label()
					endings[label] = endings.get(label, 0) + 1
				"error":
					running = false
					if event.message not in errors:
						errors.append(event.message)

	var unreached: Array = []
	for name in story.labels:
		if not interp.coverage.has(story.labels[name]):
			unreached.append(name)
	var never_offered: Array = []
	for i in story.program.size():
		var instruction: Dictionary = story.program[i]
		if instruction.op != "menu":
			continue
		for c in instruction.choices.size():
			if not offered.has("%d:%d" % [i, c]):
				never_offered.append("%s:%d « %s »" % [instruction.file, instruction.line, instruction.choices[c].text])
	for map_id in navigation.get("cartes", {}):
		var places: Array = navigation.cartes[map_id].lieux
		for i in places.size():
			if places[i].label != "" and not offered_places.has("%s:%d" % [map_id, i]):
				never_offered.append("carte « %s », lieu « %s »" % [map_id, places[i].lieu])
	return {
		"endings": endings,
		"unreached_labels": unreached,
		"never_offered": never_offered,
		"errors": errors,
		"states": explored,
		"complete": pending.is_empty(),
	}


func _push(interp: Interpreter, seen: Dictionary, pending: Array) -> void:
	var state := interp.snapshot()
	var key := var_to_str([state.pc, state.store, state.call_stack])
	if not seen.has(key):
		seen[key] = true
		pending.append(state)
