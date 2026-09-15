# Fichier généré par tools/fiches.py depuis contenu/ : ne pas modifier à la main.
# Chapitre 01 : CH01_SC01, CH01_SC02, CH01_SC03A, CH01_SC03B, CH01_SC04, CH01_SC05, CH01_SOUVENIR.


label ch01_sc01:
    # CH01_SC01 — L'arrivée (rue, soir)
    # objectif : installer_l_ambiance
    # objectif : proposer_l_indice_de_la_photo
    scene rue_nuit with fade
    "Il pleut depuis des heures quand j'arrive enfin devant l'immeuble." id ch01_sc01_e08e9cdc
    moi "Troisième étage… C'est ici." id ch01_sc01_227717a7
    menu:

        "Monter directement":
            $ lena_moi += 1
            jump ch01_sc02

        "Regarder la boîte aux lettres":
            $ indice_photo = True
            $ moi_observation += 1
            "Une vieille photo dépasse de la fente. Un homme devant un chantier… mon père ?" id ch01_sc01_18ff5070
            jump ch01_sc02


label ch01_sc02:
    # CH01_SC02 — L'appartement de Léna (appartement_lena, soir)
    # objectif : premiere_rencontre_avec_lena
    # objectif : choisir_entre_confiance_et_enquete
    if moment == "matin":
        scene appartement_jour with dissolve
    elif moment == "midi":
        scene appartement_jour with dissolve
    elif moment == "soir":
        scene appartement_soir with dissolve
    else:
        scene appartement_jour with dissolve
    show lena sourire at right with dissolve
    lena "Je ne pensais pas que tu viendrais." id ch01_sc02_14e17bdd
    if indice_photo:
        moi "Il y avait une photo dans ta boîte aux lettres." id ch01_sc02_8d58a627
        lena "Tu as l'œil. On en reparlera." id ch01_sc02_41989a26
    menu:
        lena "Alors… tu restes un peu ?" id ch01_sc02_911f1e69

        "Lui faire confiance":
            $ lena_moi += 2
            jump ch01_sc03a

        "L'interroger sur la photo" if indice_photo:
            $ mystere += 1
            jump ch01_sc03b

        "Repartir sous la pluie":
            $ lena_moi -= 2
            hide lena with dissolve
            pause 1.0
            jump ch01_sc05


label ch01_sc03a:
    # CH01_SC03A — La confiance (appartement_lena, soir)
    # objectif : rapprochement_avec_lena
    show lena rougit
    lena "Merci. Ça compte pour moi, tu sais." id ch01_sc03a_06c46afe
    $ renpy.movie_cutscene("videos/lena_scene_01.webm")
    jump ch01_sc04


label ch01_sc03b:
    # CH01_SC03B — L'interrogatoire (appartement_lena, soir)
    # objectif : reveler_que_lena_connait_le_pere
    show lena serieuse
    lena "Ton père… Oui, je l'ai connu. Bien plus que tu ne le crois." id ch01_sc03b_e5b495de
    call ch01_souvenir
    $ mystere += 1
    jump ch01_sc04


label ch01_sc04:
    # CH01_SC04 — Fin de la soirée (appartement_lena, soir)
    if moment == "matin":
        scene appartement_jour with fade
    elif moment == "midi":
        scene appartement_jour with fade
    elif moment == "soir":
        scene appartement_soir with fade
    else:
        scene appartement_jour with fade
    "{i}Fin de la soirée{/i} — relation avec Léna : [lena_moi], mystère : [mystere]." id ch01_sc04_c9e521d1
    if lena_moi >= 5:
        "Léna m'a fait confiance ce soir." id ch01_sc04_e2a8df7c
    elif mystere >= 2:
        "Je repars avec plus de questions que de réponses." id ch01_sc04_9eb9ce0e
    else:
        "La soirée s'achève sur un silence." id ch01_sc04_187203a5
    "Sur le palier, elle a ajouté : « Reviens demain soir. D'ici là, la ville est à toi. »" id ch01_sc04_d6c3c2bf
    jump ch02_matin


label ch01_sc05:
    # CH01_SC05 — Fin solitaire (rue, soir)
    scene rue_nuit with fade
    "Je redescends l'escalier. La porte se referme derrière moi." id ch01_sc05_eb701393
    return


label ch01_souvenir:
    # CH01_SOUVENIR — Souvenir du père
    call temps_epoque_passe
    "Un souvenir remonte : l'odeur du plâtre, et la voix de mon père sur le chantier." id ch01_souvenir_81d95cb6
    call temps_epoque_present
    return
