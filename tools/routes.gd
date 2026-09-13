## Rapport des routes du jeu : labels inatteignables, choix jamais proposés, fins.
##   godot --headless --path . --script res://tools/routes.gd
extends SceneTree

const Parser = preload("res://engine/rpy_parser.gd")
const RouteExplorer = preload("res://engine/route_explorer.gd")


func _init() -> void:
	var parser := Parser.new()
	parser.parse_dir("res://game/story")
	var story = parser.finish()
	if story == null:
		printerr("Erreurs de compilation :\n  " + "\n  ".join(parser.errors))
		quit(1)
		return
	var report := RouteExplorer.new().explore(story)
	print("États explorés : %d%s" % [report.states, "" if report.complete else " (limite atteinte, exploration partielle)"])
	print("\nFins atteintes (label : nombre d'états finaux distincts)")
	for label in report.endings:
		print("  %s : %d" % [label, report.endings[label]])
	_print_list("Labels jamais atteints", report.unreached_labels)
	_print_list("Choix jamais proposés", report.never_offered)
	_print_list("Erreurs d'exécution", report.errors)
	quit(0 if report.errors.is_empty() else 1)


func _print_list(title: String, items: Array) -> void:
	print("\n%s : %s" % [title, "aucun" if items.is_empty() else str(items.size())])
	for item in items:
		print("  - %s" % item)
