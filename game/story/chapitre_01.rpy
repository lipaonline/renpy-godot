# Fichier généré par tools/fiches.py depuis contenu/ : ne pas modifier à la main.
# Chapitre 01 : CH01_SC01, CH01_SC02, CH01_SC03A, CH01_SC03B, CH01_SC04, CH01_SC05, CH01_SOUVENIR.


label ch01_sc01:
    # CH01_SC01 — L'arrivée (rue, nuit)
    # objectif : installer_l_ambiance
    # objectif : proposer_l_indice_de_la_photo
    scene rue_nuit with fade
    "Il pleut depuis des heures quand j'arrive enfin devant l'immeuble."
    moi "Troisième étage… C'est ici."
    menu:

        "Monter directement":
            $ relation_lena += 1
            jump ch01_sc02

        "Regarder la boîte aux lettres":
            $ indice_photo = True
            "Une vieille photo dépasse de la fente. Un homme devant un chantier… mon père ?"
            jump ch01_sc02


label ch01_sc02:
    # CH01_SC02 — L'appartement de Léna (appartement_lena, soir)
    # objectif : premiere_rencontre_avec_lena
    # objectif : choisir_entre_confiance_et_enquete
    scene appartement_soir with dissolve
    show lena sourire at right with dissolve
    lena "Je ne pensais pas que tu viendrais."
    if indice_photo:
        moi "Il y avait une photo dans ta boîte aux lettres."
        lena "Tu as l'œil. On en reparlera."
    menu:
        lena "Alors… tu restes un peu ?"

        "Lui faire confiance":
            $ relation_lena += 2
            jump ch01_sc03a

        "L'interroger sur la photo" if indice_photo:
            $ mystere += 1
            jump ch01_sc03b

        "Repartir sous la pluie":
            $ relation_lena -= 2
            hide lena with dissolve
            pause 1.0
            jump ch01_sc05


label ch01_sc03a:
    # CH01_SC03A — La confiance (appartement_lena, soir)
    # objectif : rapprochement_avec_lena
    show lena rougit
    lena "Merci. Ça compte pour moi, tu sais."
    $ renpy.movie_cutscene("videos/lena_scene_01.webm")
    jump ch01_sc04


label ch01_sc03b:
    # CH01_SC03B — L'interrogatoire (appartement_lena, soir)
    # objectif : reveler_que_lena_connait_le_pere
    show lena serieuse
    lena "Ton père… Oui, je l'ai connu. Bien plus que tu ne le crois."
    call ch01_souvenir
    $ mystere += 1
    jump ch01_sc04


label ch01_sc04:
    # CH01_SC04 — Fin de la démo (appartement_lena, soir)
    scene appartement_soir with fade
    "{i}Fin de la démo{/i} — relation avec Léna : [relation_lena], mystère : [mystere]."
    if relation_lena >= 5:
        "Léna m'a fait confiance ce soir."
    elif mystere >= 2:
        "Je repars avec plus de questions que de réponses."
    else:
        "La soirée s'achève sur un silence."
    return


label ch01_sc05:
    # CH01_SC05 — Fin solitaire (rue, nuit)
    scene rue_nuit with fade
    "Je redescends l'escalier. La porte se referme derrière moi."
    return


label ch01_souvenir:
    # CH01_SOUVENIR — Souvenir du père
    "Un souvenir remonte : l'odeur du plâtre, et la voix de mon père sur le chantier."
    return
