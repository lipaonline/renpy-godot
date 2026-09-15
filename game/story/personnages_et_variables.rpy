# Fichier généré par tools/fiches.py depuis contenu/ : ne pas modifier à la main.
# Personnages et variables : contenu/bible.yaml.

define moi = Character(_("Moi"), color="#9ad0ff")
define lena = Character(_("Léna"), color="#c8a2ff")
define karim = Character(_("Karim"), color="#f2b45c")

default mystere = 0
default indice_photo = False
default indice_carnet = False

# Jauges, compétences et relations des personnages (bible : « jauges », « competences », « relations »).
default moi_observation = 0
default lena_photographie = 4
default lena_moi = 3
default lena_karim = 5
default karim_chantier = 5

# Temps (bible, « temps ») : avance seulement par l'élément « temps » (label temps_avancer).
default creneau = 2
default moment = "soir"
default jour = 1
default jour_semaine_rang = 4
default jour_semaine = "vendredi"
default jour_mois = 16
default mois = 10
default annee = 2026
default temps_longueur_mois = 31
default temps_bissextile_rang = 2
default temps_saut = 0
default temps_cible_jour = 0
default temps_cible_mois = 0
default evenement_anniversaire_lena = False
default epoque = "present"
default epoque_present_annee = 2026
default epoque_present_mois = 10
default epoque_present_jour_mois = 16
default epoque_present_jour = 1
default epoque_present_jour_semaine_rang = 4
default epoque_present_creneau = 2
default epoque_present_temps_longueur_mois = 31
default epoque_present_temps_bissextile_rang = 2
default epoque_passe_annee = 2016
default epoque_passe_mois = 10
default epoque_passe_jour_mois = 16
default epoque_passe_jour = 1
default epoque_passe_jour_semaine_rang = 6
default epoque_passe_creneau = 2
default epoque_passe_temps_longueur_mois = 31
default epoque_passe_temps_bissextile_rang = 0

# Lieu de chaque personnage, recalculé à chaque carte (règles « presence » de la bible).
default lieu_lena = ""
default lieu_karim = ""


label start:
    jump ch01_sc01


# Un créneau de plus ; appelé par l'élément « temps » des fiches.
label temps_avancer:
    $ creneau += 1
    if creneau >= 3:
        $ creneau = 0
        call temps_jour_suivant
    call temps_calculer_noms
    return

# Un jour de plus, même créneau.
label temps_jour_suivant:
    $ jour += 1
    $ jour_semaine_rang += 1
    if jour_semaine_rang >= 7:
        $ jour_semaine_rang = 0
    $ jour_mois += 1
    if jour_mois > temps_longueur_mois:
        $ jour_mois = 1
        $ mois += 1
        if mois > 12:
            $ mois = 1
            $ annee += 1
            $ temps_bissextile_rang += 1
            if temps_bissextile_rang >= 4:
                $ temps_bissextile_rang = 0
        call temps_calculer_mois
    call temps_calculer_noms
    return

# Noms du créneau et du jour, événements du jour : recalculés après chaque changement.
label temps_calculer_noms:
    if creneau == 0:
        $ moment = "matin"
    elif creneau == 1:
        $ moment = "midi"
    elif creneau == 2:
        $ moment = "soir"
    if jour_semaine_rang == 0:
        $ jour_semaine = "lundi"
    elif jour_semaine_rang == 1:
        $ jour_semaine = "mardi"
    elif jour_semaine_rang == 2:
        $ jour_semaine = "mercredi"
    elif jour_semaine_rang == 3:
        $ jour_semaine = "jeudi"
    elif jour_semaine_rang == 4:
        $ jour_semaine = "vendredi"
    elif jour_semaine_rang == 5:
        $ jour_semaine = "samedi"
    elif jour_semaine_rang == 6:
        $ jour_semaine = "dimanche"
    $ evenement_anniversaire_lena = mois == 10 and jour_mois == 17
    return

# Longueur du mois courant (années bissextiles : tous les quatre ans, sauf 2100, 2200 et 2300).
label temps_calculer_mois:
    if mois == 2:
        if temps_bissextile_rang == 0 and annee != 2100 and annee != 2200 and annee != 2300:
            $ temps_longueur_mois = 29
        else:
            $ temps_longueur_mois = 28
    elif mois == 4 or mois == 6 or mois == 9 or mois == 11:
        $ temps_longueur_mois = 30
    else:
        $ temps_longueur_mois = 31
    return

# Saut de temps_saut jours (fiche : temps: { jours: n }).
label temps_sauter_jours:
    if temps_saut > 0:
        $ temps_saut -= 1
        call temps_jour_suivant
        jump temps_sauter_jours
    return

# Saut de temps_saut mois, même jour du mois ou dernier jour du mois d'arrivée (temps: { mois: n }).
label temps_sauter_mois:
    $ temps_cible_jour = jour_mois
    jump temps_sauter_mois_suivant
label temps_sauter_mois_suivant:
    if temps_saut > 0:
        $ temps_saut -= 1
        $ temps_cible_mois = mois + 1
        if temps_cible_mois > 12:
            $ temps_cible_mois = 1
        jump temps_sauter_mois_jours
    return
label temps_sauter_mois_jours:
    if mois == temps_cible_mois and (jour_mois == temps_cible_jour or jour_mois == temps_longueur_mois):
        jump temps_sauter_mois_suivant
    call temps_jour_suivant
    jump temps_sauter_mois_jours

# Voyage vers l'époque « present » (temps: { epoque: present }).
label temps_epoque_present:
    if epoque == "present":
        $ epoque_present_annee = annee
        $ epoque_present_mois = mois
        $ epoque_present_jour_mois = jour_mois
        $ epoque_present_jour = jour
        $ epoque_present_jour_semaine_rang = jour_semaine_rang
        $ epoque_present_creneau = creneau
        $ epoque_present_temps_longueur_mois = temps_longueur_mois
        $ epoque_present_temps_bissextile_rang = temps_bissextile_rang
    elif epoque == "passe":
        $ epoque_passe_annee = annee
        $ epoque_passe_mois = mois
        $ epoque_passe_jour_mois = jour_mois
        $ epoque_passe_jour = jour
        $ epoque_passe_jour_semaine_rang = jour_semaine_rang
        $ epoque_passe_creneau = creneau
        $ epoque_passe_temps_longueur_mois = temps_longueur_mois
        $ epoque_passe_temps_bissextile_rang = temps_bissextile_rang
    $ annee = epoque_present_annee
    $ mois = epoque_present_mois
    $ jour_mois = epoque_present_jour_mois
    $ jour = epoque_present_jour
    $ jour_semaine_rang = epoque_present_jour_semaine_rang
    $ creneau = epoque_present_creneau
    $ temps_longueur_mois = epoque_present_temps_longueur_mois
    $ temps_bissextile_rang = epoque_present_temps_bissextile_rang
    $ epoque = "present"
    call temps_calculer_noms
    return

# Voyage vers l'époque « passe » (temps: { epoque: passe }).
label temps_epoque_passe:
    if epoque == "present":
        $ epoque_present_annee = annee
        $ epoque_present_mois = mois
        $ epoque_present_jour_mois = jour_mois
        $ epoque_present_jour = jour
        $ epoque_present_jour_semaine_rang = jour_semaine_rang
        $ epoque_present_creneau = creneau
        $ epoque_present_temps_longueur_mois = temps_longueur_mois
        $ epoque_present_temps_bissextile_rang = temps_bissextile_rang
    elif epoque == "passe":
        $ epoque_passe_annee = annee
        $ epoque_passe_mois = mois
        $ epoque_passe_jour_mois = jour_mois
        $ epoque_passe_jour = jour
        $ epoque_passe_jour_semaine_rang = jour_semaine_rang
        $ epoque_passe_creneau = creneau
        $ epoque_passe_temps_longueur_mois = temps_longueur_mois
        $ epoque_passe_temps_bissextile_rang = temps_bissextile_rang
    $ annee = epoque_passe_annee
    $ mois = epoque_passe_mois
    $ jour_mois = epoque_passe_jour_mois
    $ jour = epoque_passe_jour
    $ jour_semaine_rang = epoque_passe_jour_semaine_rang
    $ creneau = epoque_passe_creneau
    $ temps_longueur_mois = epoque_passe_temps_longueur_mois
    $ temps_bissextile_rang = epoque_passe_temps_bissextile_rang
    $ epoque = "passe"
    call temps_calculer_noms
    return
