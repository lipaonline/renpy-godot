# Fichier généré par tools/fiches.py depuis contenu/ : ne pas modifier à la main.
# Personnages et variables : contenu/bible.yaml.

define moi = Character(_("Moi"), color="#9ad0ff")
define lena = Character(_("Léna"), color="#c8a2ff")

default relation_lena = 3
default mystere = 0
default indice_photo = False


label start:
    jump ch01_sc01
