# Fichier généré par tools/fiches.py depuis contenu/ : ne pas modifier à la main.
# Chapitre 02 : CH02_CAFE, CH02_CANNES, CH02_CAVE, CH02_CHAMBRE, CH02_CHANTIER, CH02_CUISINE, CH02_EPILOGUE, CH02_HALL, CH02_HEURE, CH02_LENA, CH02_MATIN, CH02_PARIS, CH02_SALLE_DE_BAIN, CH02_SALON, CH02_SOIR.


label ch02_cafe:
    # CH02_CAFE — Le café de la gare (cafe)
    # objectif : recompenser_la_confiance
    scene cafe_jour with dissolve
    if lieu_lena == "cafe":
        show lena rougit at right with dissolve
        lena "Je t'attendais, en fait. Assieds-toi." id ch02_cafe_2062cc3c
        lena "Ton père m'a demandé de me taire. Mais il n'a jamais dit jusqu'à quand." id ch02_cafe_a523bd15
        $ lena_moi += 1
        $ mystere += 1
    else:
        "Un café au comptoir, seul. Par la vitre, le chantier. Personne ne m'attend ici." id ch02_cafe_0fa951d3
    call temps_avancer
    call ch02_heure
    $ naviguer("ville", "cafe")


label ch02_cannes:
    # CH02_CANNES — La plage (cannes_plage)
    # objectif : comprendre_la_carte_postale
    scene plage_jour with dissolve
    "La plage de la carte postale, vide en cette saison. Il l'a envoyée d'ici, un mois après son départ." id ch02_cannes_182d1369
    if moi_observation >= 1:
        "Au dos, un détail que je n'avais jamais vu : le cachet de la poste est celui de Lyon." id ch02_cannes_c30d528d
        $ mystere += 1
    call temps_avancer
    call ch02_heure
    $ naviguer("cannes", "cannes_plage")


label ch02_cave:
    # CH02_CAVE — La cave (cave)
    # objectif : retrouver_les_outils_du_pere
    scene cave_immeuble with dissolve
    if mystere >= 3:
        "Les outils du père sont toujours là, marqués au nom du chantier. Je sais déjà où ils l'ont mené." id ch02_cave_89604a02
    else:
        "Dans le box du père, une caisse d'outils marquée au nom du chantier. Il y travaillait encore la veille de son départ." id ch02_cave_4f361bf2
        $ mystere += 1
    if moi_observation >= 1:
        "Un détail m'accroche : une date gravée sur le manche du marteau, la veille de son départ." id ch02_cave_6658aed8
    call temps_avancer
    call ch02_heure
    $ naviguer("immeuble", "cave")


label ch02_chambre:
    # CH02_CHAMBRE — La chambre (chambre)
    scene chambre_matin with dissolve
    "Le lit est fait, la commode vide. Il n'a rien laissé ici, ou quelqu'un est passé avant moi." id ch02_chambre_b6af121d
    $ naviguer("appartement", "chambre")


label ch02_chantier:
    # CH02_CHANTIER — Le chantier (chantier)
    # objectif : rencontrer_karim
    # objectif : reveler_la_promesse
    scene chantier_jour with dissolve
    if lieu_lena == "chantier":
        show lena serieuse at left with dissolve
        lena "Tu m'as suivie ? … Non. Tu as trouvé le chantier tout seul. Comme lui." id ch02_chantier_89ec5556
        moi "C'est ici qu'il a été pris en photo." id ch02_chantier_0c666814
        lena "C'est ici que tout a commencé. Demande à Karim, il était là." id ch02_chantier_747e4d54
        $ lena_moi += 1
        $ lena_karim += 1
        $ mystere += 1
    show karim neutre at right with dissolve
    if indice_carnet or indice_photo:
        karim "Le fils du chef d'équipe. Vous avez ses yeux. Il est parti un soir de pluie, et il m'a fait promettre." id ch02_chantier_4edcee93
        moi "Promettre quoi ?" id ch02_chantier_cab9d323
        karim "De ne rien dire à personne. Sauf à vous, si vous veniez un jour." id ch02_chantier_18c0b266
        $ mystere += 1
    else:
        karim "Un chantier, ça ne se visite pas. Revenez quand vous saurez ce que vous cherchez." id ch02_chantier_7d5c5392
    call temps_avancer
    call ch02_heure
    $ naviguer("ville", "chantier")


label ch02_cuisine:
    # CH02_CUISINE — La cuisine (cuisine)
    scene cuisine_matin with dissolve
    "La cafetière tousse encore. Par la fenêtre, la cour et, plus loin, les grues du chantier." id ch02_cuisine_6d7ddc56
    $ naviguer("appartement", "cuisine")


label ch02_epilogue:
    # CH02_EPILOGUE — Trois mois plus tard (rue, matin)
    # objectif : clore_la_demo_sur_une_ellipse
    $ temps_saut = 3
    call temps_sauter_mois
    $ creneau = 0
    $ moment = "matin"
    scene rue_jour with fade
    "Trois mois ont passé. Nous sommes le [jour_mois]/[mois]/[annee], et je repasse devant l'immeuble sans plus chercher personne." id ch02_epilogue_a30f93f9
    "{i}Fin de la démo.{/i}" id ch02_epilogue_f794f676
    return


label ch02_hall:
    # CH02_HALL — Le hall (hall)
    # objectif : rattraper_l_indice_de_la_photo
    scene hall_immeuble with dissolve
    if indice_photo:
        "La boîte aux lettres de Léna est vide. La photo, je l'ai déjà vue." id ch02_hall_84eaa21d
    else:
        "Une vieille photo dépasse encore de la fente. Un homme devant un chantier… mon père. Cette fois, je la prends." id ch02_hall_3804d007
        $ indice_photo = True
        $ mystere += 1
        $ moi_observation += 1
    call temps_avancer
    call ch02_heure
    $ naviguer("immeuble", "hall")


label ch02_heure:
    # CH02_HEURE — L'heure tourne
    if moment == "midi":
        "Midi. Il me reste un endroit à voir avant ce soir." id ch02_heure_19d14db3
    elif moment == "soir":
        "Le soir tombe. Léna m'attend au troisième étage." id ch02_heure_21c1d694
    return


label ch02_lena:
    # CH02_LENA — Chez Léna, dans la journée (appartement_lena)
    # objectif : orienter_vers_le_chantier
    if moment == "matin":
        scene appartement_jour with dissolve
    elif moment == "midi":
        scene appartement_jour with dissolve
    elif moment == "soir":
        scene appartement_soir with dissolve
    else:
        scene appartement_jour with dissolve
    if lieu_lena == "appartement_lena":
        show lena sourire at right with dissolve
        lena "Déjà debout ? Entre, le café est chaud." id ch02_lena_ea31797f
        moi "Tu connaissais bien mon père ?" id ch02_lena_ca161494
        lena "Assez pour savoir qu'il ne serait pas parti sans raison. Cherche du côté du chantier." id ch02_lena_14daaeea
        $ lena_moi += 1
    else:
        "Je frappe. Personne. Léna est sortie ; sa porte reste close." id ch02_lena_c8ca0772
    call temps_avancer
    call ch02_heure
    $ naviguer("immeuble", "appartement_lena")


label ch02_matin:
    # CH02_MATIN — Le lendemain (chambre, matin)
    # objectif : ouvrir_la_journee_libre
    call temps_avancer
    if moment != "matin":
        call temps_avancer
    if moment != "matin":
        call temps_avancer
    scene chambre_matin with fade
    "Je me réveille dans le lit de mon père, entre les cartons. Dehors, la pluie a cessé." id ch02_matin_40ac964d
    moi "Une journée. L'appartement, l'immeuble, la ville : par où je commence ?" id ch02_matin_c8713892
    $ naviguer("appartement", "chambre")


label ch02_paris:
    # CH02_PARIS — Les archives (paris_archives)
    # objectif : retrouver_le_registre_du_chantier
    scene archives_jour with dissolve
    if indice_carnet:
        "Le registre confirme le carnet : le chantier a fermé une semaine après le départ de mon père." id ch02_paris_9929ea2e
    else:
        "Dans le registre du chantier, son nom revient chaque jour. Puis plus rien, du jour au lendemain." id ch02_paris_57208d17
        $ mystere += 1
    call temps_avancer
    call ch02_heure
    $ naviguer("paris", "paris_archives")


label ch02_salle_de_bain:
    # CH02_SALLE_DE_BAIN — La salle de bain (salle_de_bain)
    scene salle_de_bain_matin with dissolve
    "De l'eau froide sur le visage. Dans le miroir piqué, j'ai ses yeux, paraît-il." id ch02_salle_de_bain_b9156303
    $ naviguer("appartement", "salle_de_bain")


label ch02_salon:
    # CH02_SALON — Le salon (salon)
    # objectif : trouver_le_carnet_de_chantier
    scene salon_matin with dissolve
    if indice_carnet:
        "Les cartons n'ont plus rien à me dire. Le carnet est dans ma poche." id ch02_salon_ce615f4a
    else:
        "Sous les cartons, un carnet de chantier. Un nom revient à chaque page : Karim, chef de chantier." id ch02_salon_41be80d2
        $ indice_carnet = True
        $ mystere += 1
    call temps_avancer
    call ch02_heure
    $ naviguer("appartement", "salon")


label ch02_soir:
    # CH02_SOIR — Le soir, chez Léna (appartement_lena, soir)
    # objectif : conclure_la_demo_selon_l_enquete_et_la_confiance
    if moment == "matin":
        scene appartement_jour with fade
    elif moment == "midi":
        scene appartement_jour with fade
    elif moment == "soir":
        scene appartement_soir with fade
    else:
        scene appartement_jour with fade
    if evenement_anniversaire_lena:
        "Sur la table, un gâteau entamé et une seule bougie : c'est son anniversaire, et elle n'en a rien dit." id ch02_soir_e13e5124
    show lena sourire at right with dissolve
    lena "Tu es revenu. Alors, ta journée ?" id ch02_soir_263d35c7
    if mystere >= 4:
        show lena serieuse
        lena "Tu sais presque tout. Il est parti pour protéger quelqu'un sur ce chantier. Et il m'a écrit, chaque année." id ch02_soir_fa6e0969
        "{i}Fin de la démo{/i} — relation avec Léna : [lena_moi], mystère : [mystere]. Léna a tenu sa promesse jusqu'au bout, et l'a rompue pour moi." id ch02_soir_0d7c77c0
    elif lena_moi >= 6:
        show lena rougit
        lena "Je ne peux pas encore tout te dire. Mais reste, ce soir. On a le temps." id ch02_soir_1ffebbe7
        "{i}Fin de la démo{/i} — relation avec Léna : [lena_moi], mystère : [mystere]. La promesse tient encore, mais plus pour longtemps." id ch02_soir_44ffaf1e
    else:
        lena "Tu n'as pas trouvé grand-chose. Reviens quand tu en sauras plus." id ch02_soir_7d39f445
        "{i}Fin de la démo{/i} — relation avec Léna : [lena_moi], mystère : [mystere]. La porte se referme, sans claquer." id ch02_soir_9bec1892
    jump ch02_epilogue
