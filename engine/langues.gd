## Langues du jeu : game/langues.json (produit par tools/fiches.py depuis la bible, lu
## aussi par game/langues.rpy) et traductions Ren'Py de game/tl/<langue>/, lues par le
## compilateur comme le script.
##
##   var langues = preload("res://engine/langues.gd").new()
##   langues.load_file()
##   var translation = langues.load_translation("en", story)   # null en cas d'erreur
extends RefCounted

const Parser = preload("res://engine/rpy_parser.gd")
const LANGUAGES_PATH := "res://game/langues.json"
const TL_DIR := "res://game/tl"

## La langue des fiches d'abord, puis les traductions : [{code, renpy, nom}].
var languages: Array = [{"code": "fr", "renpy": "french", "nom": "Français"}]
var errors: PackedStringArray = []
var warnings: PackedStringArray = []


func load_file(path := LANGUAGES_PATH) -> void:
	if not FileAccess.file_exists(path):
		return
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(data) != TYPE_DICTIONARY:
		warnings.append("%s : format attendu {\"source\": …, \"traductions\": [ … ]}" % path.get_file())
		return
	if typeof(data.get("source")) == TYPE_DICTIONARY:
		languages = [_describe(data.source)]
	for item in data.get("traductions", []):
		if typeof(item) == TYPE_DICTIONARY:
			languages.append(_describe(item))


func source() -> String:
	return languages[0].code


func has(code: String) -> bool:
	return languages.any(func(language: Dictionary) -> bool: return language.code == code)


## Langue du système si le jeu la propose, sinon celle des fiches (comme Ren'Py au
## premier lancement, voir game/langues.rpy).
func detect() -> String:
	var locale := OS.get_locale_language()
	return locale if has(locale) else source()


## Traduction d'une langue pour l'interpréteur ; {} pour la langue des fiches, null en
## cas d'erreur (voir errors).
func load_translation(code: String, story: Dictionary, tl_dir := TL_DIR) -> Variant:
	if code == source():
		return {}
	var renpy_name := code
	for language in languages:
		if language.code == code:
			renpy_name = language.renpy
	var parser := Parser.new()
	parser.parse_translation_dir(tl_dir.path_join(renpy_name), renpy_name)
	var translation = parser.finish_translation(story)
	warnings.append_array(parser.warnings)
	if translation == null:
		errors.append_array(parser.errors)
	return translation


func _describe(item: Dictionary) -> Dictionary:
	var code := str(item.get("code", ""))
	return {"code": code, "renpy": str(item.get("renpy", code)), "nom": str(item.get("nom", code))}
