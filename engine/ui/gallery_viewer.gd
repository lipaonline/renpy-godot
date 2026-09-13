## Visionneuse plein écran de la galerie : images une par une (clic pour la suivante)
## ou vidéo (clic ou fin de la vidéo pour fermer).
extends Control

const Style = preload("res://engine/ui/ui_style.gd")
const Assets = preload("res://engine/assets.gd")
const Texts = preload("res://engine/ui/traductions_interface.gd")

var _image: TextureRect
var _video: VideoStreamPlayer
var _notice: Label
var _pending: Array = []
var _assets: Variant
var _video_missing := false


func _init() -> void:
	set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	mouse_filter = MOUSE_FILTER_STOP
	visible = false
	var backdrop := ColorRect.new()
	backdrop.color = Color.BLACK
	backdrop.mouse_filter = MOUSE_FILTER_IGNORE
	backdrop.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	add_child(backdrop)
	_image = TextureRect.new()
	_image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_image.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_image.mouse_filter = MOUSE_FILTER_IGNORE
	_image.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	add_child(_image)
	_video = VideoStreamPlayer.new()
	_video.expand = true
	_video.visible = false
	_video.mouse_filter = MOUSE_FILTER_IGNORE
	_video.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	_video.finished.connect(close)
	add_child(_video)
	_notice = Style.label("", 30, Style.IDLE_SMALL)
	_notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_notice.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_notice.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	add_child(_notice)


func open(entry: Dictionary, assets: Variant) -> void:
	_assets = assets
	_notice.text = ""
	_image.texture = null
	_video_missing = false
	visible = true
	if entry.video != "":
		var stream := Assets.video_stream(entry.video)
		if stream == null:
			_notice.text = Texts.t("Vidéo introuvable : %s") % Assets.ogv_path(entry.video).trim_prefix("res://")
			_video_missing = true
			return
		_video.stream = stream
		_video.visible = true
		_video.play()
		return
	_pending = entry.images.duplicate()
	_show_next()


## Ferme la visionneuse ; renvoie false si elle était déjà fermée.
func close() -> bool:
	if not visible:
		return false
	_video.stop()
	_video.visible = false
	visible = false
	return true


func _show_next() -> void:
	if _pending.is_empty():
		close()
		return
	var image_name: String = _pending.pop_front()
	_image.texture = _assets.image_texture(image_name)
	_notice.text = "" if _image.texture != null else Texts.t("[ image manquante : %s ]") % image_name


func _gui_input(event: InputEvent) -> void:
	var mouse := event as InputEventMouseButton
	if mouse == null or not mouse.pressed or mouse.button_index != MOUSE_BUTTON_LEFT:
		return
	accept_event()
	if _video.visible or _video_missing:
		close()
	else:
		_show_next()
