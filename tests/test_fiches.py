"""Tests de tools/fiches.py :
    .venv/bin/python -m unittest discover -s tests -p "test_*.py"
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
DEMO = RACINE / "tests" / "fixtures" / "demo"
sys.path.insert(0, str(RACINE / "tools"))

import fiches  # noqa: E402


def bible(**changements):
    base = {
        "debut": "A",
        "personnages": {"moi": {"nom": "Moi", "age": 25}, "lena": {"nom": "Léna", "age": 27, "couleur": "#c8a2ff"}},
        "lieux": {"salon": {"description": "Salon", "decors": ["salon"]}},
        "variables": {"confiance": {"defaut": 0, "min": 0, "max": 5}, "indice": {"defaut": False}},
    }
    base.update(changements)
    return base


def scene(sid, **champs):
    fiche = {"id": sid, "titre": f"Scène {sid}", "lieu": "salon", "personnages": ["moi", "lena"]}
    fiche.update(champs)
    if not any(cle in fiche for cle in fiches.FINS):
        fiche["fin"] = True
    return fiche


def projet(*scenes, racine=None, **changements):
    resultat = fiches.Projet(racine=racine or Path(tempfile.mkdtemp()), bible=bible(**changements))
    for fiche in scenes:
        resultat.scenes[fiche["id"]] = fiche
        resultat.fichiers[fiche["id"]] = f"{fiche['id']}.yaml"
    return resultat


def verifier(p):
    rapport = fiches.Rapport()
    return rapport, fiches.verifier(p, rapport)


def contient(messages, *morceaux):
    return any(all(morceau in message for morceau in morceaux) for message in messages)


class ContenuDuJeu(unittest.TestCase):
    def test_contenu_valide_et_fichiers_a_jour(self):
        rapport = fiches.Rapport()
        p = fiches.charger(RACINE, rapport)
        exploration = fiches.verifier(p, rapport)
        self.assertEqual(rapport.erreurs, [])
        for relatif, texte in fiches.generer(p, exploration).items():
            chemin = RACINE / relatif
            self.assertTrue(chemin.exists() and chemin.read_text(encoding="utf-8") == texte,
                            f"{relatif} n'est pas à jour : lancez tools/fiches.py generer")
        for code in p.langues_cibles:
            self.assertEqual(yaml.safe_load(fiches.traduire(p, code)[0]), p.traductions.get(code),
                             f"contenu/traductions/{code}.yaml n'est pas à jour : lancez tools/fiches.py traduire {code}")


class JeuDEssaiDemo(unittest.TestCase):
    """La démo figée de tests/fixtures/demo sert aux tests du moteur Godot."""

    def test_demo_valide_et_script_identique(self):
        rapport = fiches.Rapport()
        p = fiches.charger(DEMO, rapport)
        exploration = fiches.verifier(p, rapport)
        self.assertEqual(rapport.erreurs, [])
        self.assertEqual(rapport.avertissements, [])
        self.assertEqual(set(exploration.fins), {"CH01_SC04", "CH01_SC05"})
        produits = fiches.generer(p)
        chapitre = produits["game/story/chapitre_01.rpy"]
        self.assertIn('        "L\'interroger sur la photo" if indice_photo:', chapitre)
        self.assertIn("    call ch01_souvenir", chapitre)
        self.assertIn('    old "Lui faire confiance"\n    new "Trust her"', produits["game/tl/english/story/textes.rpy"])
        for relatif, texte in produits.items():
            self.assertEqual((DEMO / relatif).read_text(encoding="utf-8"), texte, f"jeu d'essai {relatif} à régénérer")


class Bible(unittest.TestCase):
    def test_age_facultatif_mais_minimum(self):
        rapport, _ = verifier(projet(scene("A"), personnages={"moi": {"nom": "Moi"}, "lena": {"nom": "Léna", "age": 17},
                                                              "karim": {"nom": "Karim", "age": "vieux"}}))
        self.assertFalse(contient(rapport.erreurs, "« moi »"))
        self.assertTrue(contient(rapport.erreurs, "« lena »", "âge 17", "minimum à 18"))
        self.assertTrue(contient(rapport.erreurs, "« karim »", "« age » attendu"))

    def test_age_minimum_reglable(self):
        rapport, _ = verifier(projet(scene("A"), age_minimum=12,
                                     personnages={"moi": {"nom": "Moi", "age": 30}, "lena": {"nom": "Léna", "age": 14}}))
        self.assertEqual(rapport.erreurs, [])

    def test_debut_inconnu(self):
        rapport, _ = verifier(projet(scene("A"), debut="Z"))
        self.assertTrue(contient(rapport.erreurs, "« debut »"))


class JaugesEtCompetences(unittest.TestCase):
    def personnages(self, lena_extra=None, moi_extra=None):
        lena = {"nom": "Léna", "age": 27, "couleur": "#c8a2ff", "avatar": "lena avatar",
                "jauges": {"relation": {"defaut": 3, "min": 0, "max": 10, "paliers": {0: "distante", 6: "amie"}}},
                "competences": {"photographie": 4}}
        lena.update(lena_extra or {})
        moi = {"nom": "Moi", "competences": {"observation": {"defaut": 0, "max": 5, "nom": "Œil"}}}
        moi.update(moi_extra or {})
        return {"moi": moi, "lena": lena}

    def test_variables_generees_et_effets(self):
        a = scene("A", contenu=[{"effets": {"lena_relation": 3, "moi_observation": 1}},
                                {"si": "lena_relation >= 6 and lena_photographie > 3", "alors": [{"narration": "Amie."}]}])
        p = projet(a, personnages=self.personnages())
        rapport, exploration = verifier(p)
        self.assertEqual(rapport.erreurs, [])
        self.assertEqual(set(p.variables_personnages), {"lena_relation", "lena_photographie", "moi_observation"})
        self.assertEqual(p.variables_personnages["lena_relation"]["paliers"], [(0, "distante"), (6, "amie")])
        self.assertEqual(p.variables_personnages["moi_observation"]["nom"], "Œil")
        self.assertEqual(p.variables_personnages["lena_photographie"]["nom"], "Photographie")
        produits = fiches.generer(p, exploration)
        bible_rpy = produits["game/story/personnages_et_variables.rpy"]
        for ligne in ("default lena_relation = 3", "default lena_photographie = 4", "default moi_observation = 0"):
            self.assertIn(ligne, bible_rpy)
        self.assertIn("    $ lena_relation += 3", produits["game/story/chapitre_divers.rpy"])
        fiches_json = json.loads(produits["game/personnages.json"])["personnages"]
        self.assertEqual(list(fiches_json), ["moi", "lena"])
        self.assertEqual(fiches_json["lena"]["jauges"][0],
                         {"variable": "lena_relation", "nom": "Relation", "min": 0, "max": 10,
                          "paliers": [{"des": 0, "nom": "distante"}, {"des": 6, "nom": "amie"}]})
        self.assertEqual(fiches_json["lena"]["competences"][0]["max"], 4)
        self.assertEqual(fiches_json["moi"]["avatar"], "")
        textes = fiches.textes_a_traduire(p)
        self.assertEqual(textes["Relation"], "Jauges, compétences et relations")
        self.assertEqual(textes["amie"], "Paliers des jauges")
        self.assertIn("testcase personnages:", produits["game/tests_routes.rpy"])
        contexte = fiches.contexte(p, exploration, "A")
        self.assertIn("`lena_relation` : 3 (distante)", contexte)

    def test_relations_entre_personnages(self):
        personnages = self.personnages(lena_extra={"relations": {"moi": {"defaut": 3, "max": 10, "paliers": {0: "distante", 6: "amie"}}}})
        personnages["karim"] = {"nom": "Karim", "couleur": "#f2b45c",
                                "relations": {"lena": {"defaut": 5, "max": 10, "nom": "Anciens collègues"}}}
        a = scene("A", personnages=["moi", "lena", "karim"], contenu=[{"effets": {"lena_moi": 3, "karim_lena": -1}},
                                                                     {"si": "lena_moi >= 6", "alors": [{"narration": "Amie."}]}])
        p = projet(a, personnages=personnages)
        rapport, exploration = verifier(p)
        self.assertEqual(rapport.erreurs, [])
        self.assertEqual(p.variables_personnages["lena_moi"]["avec"], "moi")
        self.assertEqual(p.variables_personnages["lena_moi"]["description"], "Relation entre Léna et Moi.")
        self.assertEqual(p.personnages_avec_jauges(), ["moi", "lena", "karim"])
        produits = fiches.generer(p, exploration)
        self.assertIn("default karim_lena = 5", produits["game/story/personnages_et_variables.rpy"])
        fiches_json = json.loads(produits["game/personnages.json"])["personnages"]
        self.assertEqual([r["nom"] for r in fiches_json["moi"]["relations"]], ["Léna"])
        self.assertEqual(fiches_json["moi"]["relations"][0]["couleur"], "#c8a2ff")
        self.assertEqual([(r["variable"], r["nom"], r["avec"]) for r in fiches_json["lena"]["relations"]],
                         [("lena_moi", "Moi", "moi"), ("karim_lena", "Anciens collègues", "karim")])
        self.assertEqual([r["nom"] for r in fiches_json["karim"]["relations"]], ["Anciens collègues"])
        self.assertEqual(fiches.textes_a_traduire(p)["Anciens collègues"], "Jauges, compétences et relations")
        self.assertIn("`lena_moi` : 3 (distante)", fiches.contexte(p, exploration, "A"))

    def test_relations_invalides(self):
        personnages = self.personnages(lena_extra={"relations": {"lena": 1, "inconnu": 2, "moi": 3},
                                                   "competences": {"moi": 1}},
                                       moi_extra={"relations": {"lena": 4}})
        rapport, _ = verifier(projet(scene("A"), personnages=personnages))
        for morceaux in (("relation « lena »", "autre personnage"), ("relation « inconnu »", "autre personnage"),
                         ("« lena », relation « moi »", "déjà déclarée sur « moi »"),
                         ("compétence « moi »", "réservé aux relations")):
            self.assertTrue(contient(rapport.erreurs, *morceaux), (morceaux, rapport.erreurs))

    def test_bornes_sur_les_routes(self):
        a = scene("A", contenu=[{"effets": {"lena_relation": 9}}])
        rapport, _ = verifier(projet(a, personnages=self.personnages()))
        self.assertTrue(contient(rapport.avertissements, "« lena_relation » vaut 12", "maximum 10"))

    def test_fiches_invalides(self):
        lena = {"jauges": {"Relation": 1, "humeur": {"defaut": "haute"}, "confiance": {"defaut": 1, "min": 5, "max": 2},
                           "envie": {"defaut": 1, "max": 3, "paliers": {"bas": "x", 8: "y", 2: "y"}}, "vide": {"defaut": 0, "truc": 1}},
                "competences": [], "traits": "seul"}
        rapport, _ = verifier(projet(scene("A"), personnages=self.personnages(lena_extra=lena),
                                     variables={"lena_confiance": {"defaut": 0}}))
        for morceaux in (("« Relation »", "nom invalide"), ("« humeur »", "« defaut » obligatoire : un nombre"),
                         ("« confiance »", "« min » supérieur à « max »"), ("« envie »", "palier « bas »"),
                         ("« envie »", "palier 8 hors des bornes"), ("« envie »", "deux paliers portent le même nom"),
                         ("« vide »", "champs inconnus : truc"), ("« competences »", "dictionnaire"),
                         ("« traits »", "liste"), ("variable « lena_confiance »", "réservée à la jauge « confiance » de « lena »")):
            self.assertTrue(contient(rapport.erreurs, *morceaux), (morceaux, rapport.erreurs))

    def test_sans_jauges_ni_fichier_de_fiches(self):
        p = projet(scene("A"))
        produits = fiches.generer(p)
        self.assertEqual(json.loads(produits["game/personnages.json"])["personnages"], {})
        self.assertNotIn("testcase personnages:", fiches.generer(p, verifier(p)[1])["game/tests_routes.rpy"])


class Temps(unittest.TestCase):
    TEMPS = {"creneaux": ["matin", "midi", "soir"], "jours": True, "semaine": ["lundi", "mardi"], "debut": {"creneau": "midi", "jour_semaine": "mardi"}}

    def test_variables_avance_et_script(self):
        lieux = {"salon": {"description": "Salon", "decors": {"matin": "salon_jour", "soir": "salon_nuit"}}}
        a = scene("A", contenu=[{"decor": "salon", "transition": "fade"}, {"temps": 2}, {"temps": "matin"},
                                {"si": 'moment == "matin" and jour == 2 and jour_semaine == "lundi"', "alors": [{"narration": "Lundi matin."}]}])
        p = projet(a, temps=self.TEMPS, lieux=lieux)
        rapport, exploration = verifier(p)
        self.assertEqual(rapport.erreurs, [])
        self.assertEqual({nom: v["defaut"] for nom, v in p.variables_temps.items()},
                         {"creneau": 1, "moment": "midi", "jour": 1, "jour_semaine_rang": 1, "jour_semaine": "mardi"})
        etat = exploration.entrees["A"][0]
        self.assertEqual((etat["creneau"], etat["moment"], etat["jour"], etat["jour_semaine"]), (1, "midi", 1, "mardi"))
        # midi → (2) soir, matin du jour 2 (lundi) → (matin) matin du jour 3 (mardi)
        fin = fiches.Explorateur(p, fiches.Rapport(), 100)
        etat = p.avancer_temps(p.avancer_temps(etat))
        self.assertEqual((etat["moment"], etat["jour"], etat["jour_semaine"]), ("matin", 2, "lundi"))
        produits = fiches.generer(p, exploration)
        bible_rpy = produits["game/story/personnages_et_variables.rpy"]
        for ligne in ("default creneau = 1", 'default moment = "midi"', "default jour = 1", 'default jour_semaine = "mardi"',
                      "label temps_avancer:", "    if creneau >= 3:", "label temps_jour_suivant:\n    $ jour += 1", '        $ jour_semaine = "lundi"', '        $ moment = "soir"'):
            self.assertIn(ligne, bible_rpy)
        chapitre = produits["game/story/chapitre_divers.rpy"]
        self.assertIn('    if moment == "matin":\n        scene salon_jour with fade\n    elif moment == "soir":\n        scene salon_nuit with fade\n    else:\n        scene salon_jour with fade', chapitre)
        self.assertEqual(chapitre.count("call temps_avancer"), 2 + 3)
        self.assertIn('    if moment != "matin":\n        call temps_avancer', chapitre)
        self.assertEqual(json.loads(produits["game/temps.json"])["creneaux"], ["matin", "midi", "soir"])
        self.assertIn("testcase temps:", produits["game/tests_routes.rpy"])
        self.assertIn('temps_texte() == "Jour 1 · mardi · midi"', produits["game/tests_routes.rpy"])
        self.assertEqual(fiches.textes_a_traduire(p)["lundi"], "Temps : créneaux, jours et mois")
        images, _ = fiches.inventaire(p)
        self.assertEqual(set(images), {"salon_jour", "salon_nuit"})

    CALENDRIER = {"creneaux": ["matin", "soir"], "epoques": {"present": "2026-10-16", "passe": "2016-06-30"},
                  "debut": {"creneau": "soir"}, "evenements": {"noel": {"mois": 12, "jour": 25}}}

    def test_calendrier_evenements_et_epoques(self):
        a = scene("A", contenu=[{"temps": {"jours": 800}}, {"temps": {"mois": 3, "creneau": "matin"}},
                                {"temps": {"date": "2029-12-25"}}, {"temps": {"epoque": "passe"}}, {"temps": 1},
                                {"temps": {"epoque": "present"}}, {"si": "evenement_noel and epoque == \"present\"", "alors": [{"narration": "Noël."}]}],
                  suite="B")
        p = projet(a, scene("B"), temps=self.CALENDRIER)
        rapport, exploration = verifier(p)
        self.assertEqual(rapport.erreurs, [])
        defauts = {nom: v["defaut"] for nom, v in p.variables_temps.items()}
        self.assertEqual((defauts["jour_semaine"], defauts["jour_mois"], defauts["mois"], defauts["annee"], defauts["epoque"], defauts["evenement_noel"]),
                         ("vendredi", 16, 10, 2026, "present", False))
        self.assertEqual((defauts["epoque_passe_annee"], defauts["epoque_passe_jour_semaine_rang"]), (2016, 3))
        etat = exploration.entrees["A"][0]
        # 800 jours après le 16/10/2026 : 24/12/2028 ; 3 mois plus tard : 24/03/2029, matin ; puis le 25/12/2029.
        e1 = p.jour_suivant(etat, 800)
        self.assertEqual((e1["annee"], e1["mois"], e1["jour_mois"], e1["jour"], e1["jour_semaine"], e1["evenement_noel"]), (2028, 12, 24, 801, "dimanche", False))
        self.assertTrue(p.jour_suivant(e1)["evenement_noel"])
        e2 = p.sauter_mois(e1, 3)
        self.assertEqual((e2["annee"], e2["mois"], e2["jour_mois"], e2["temps_cible_jour"], e2["temps_cible_mois"]), (2029, 3, 24, 24, 3))
        e3 = p.aller_date(e2, fiches._date_de("2029-12-25"))
        self.assertEqual((e3["jour_semaine"], e3["jour"], e3["evenement_noel"]), ("mardi", 1167, True))
        e4 = p.avancer_temps(p.changer_epoque(e3, "passe"))
        self.assertEqual((e4["epoque"], e4["annee"], e4["mois"], e4["jour_mois"], e4["moment"], e4["evenement_noel"]), ("passe", 2016, 7, 1, "matin", False))
        e5 = p.changer_epoque(e4, "present")
        self.assertEqual((e5["annee"], e5["mois"], e5["jour_mois"], e5["jour_semaine"], e5["evenement_noel"]), (2029, 12, 25, "mardi", True))
        self.assertEqual((e5["epoque_passe_jour_mois"], e5["epoque_passe_creneau"]), (1, 0))
        fin = exploration.entrees["B"][0]
        self.assertEqual((fin["epoque"], fin["annee"], fin["mois"], fin["jour_mois"], fin["moment"]), ("present", 2029, 12, 25, "matin"))
        # Janvier 31 + 1 mois = 28 février ; + 1 mois = 31 mars (le jour visé est conservé).
        e = p.aller_date(etat, fiches._date_de("2027-01-31"))
        self.assertEqual((p.sauter_mois(e, 1)["jour_mois"], p.sauter_mois(e, 2)["jour_mois"]), (28, 31))
        produits = fiches.generer(p, exploration)
        bible_rpy = produits["game/story/personnages_et_variables.rpy"]
        for ligne in ("default jour_mois = 16", 'default jour_semaine = "vendredi"', "default evenement_noel = False", 'default epoque = "present"',
                      "label temps_calculer_mois:", "label temps_sauter_jours:", "label temps_sauter_mois_jours:", "label temps_epoque_passe:",
                      "    $ evenement_noel = mois == 12 and jour_mois == 25", "        $ epoque_present_annee = annee"):
            self.assertIn(ligne, bible_rpy)
        chapitre = produits["game/story/chapitre_divers.rpy"]
        for ligne in ("    $ temps_saut = 800\n    call temps_sauter_jours", "    $ temps_saut = 3\n    call temps_sauter_mois\n    $ creneau = 0\n    $ moment = \"matin\"",
                      "    $ annee = 2029\n    $ mois = 12\n    $ jour_mois = 25", "    $ jour = 1167\n    call temps_calculer_noms", "    call temps_epoque_passe"):
            self.assertIn(ligne, chapitre)
        self.assertIn('temps_texte() == "vendredi 16 octobre 2026 · soir"', produits["game/tests_routes.rpy"])
        self.assertEqual(json.loads(produits["game/temps.json"])["epoques"], ["present", "passe"])
        self.assertEqual(fiches.textes_a_traduire(p)["décembre"], "Temps : créneaux, jours et mois")
        self.assertNotIn("temps_longueur_mois", fiches.contexte(p, exploration, "A"))

    def test_erreurs_calendrier(self):
        a = scene("A", contenu=[{"temps": {"mois": 1}}, {"temps": {"jours": 1, "mois": 2}}, {"temps": {"epoque": "futur"}}])
        rapport, _ = verifier(projet(a, temps={"creneaux": ["matin", "soir"], "jours": True}))
        for morceaux in (("un saut « mois » demande une « date »",), ("exactement un de jours, mois, date ou epoque",), ("époque inconnue « futur »",)):
            self.assertTrue(contient(rapport.erreurs, *morceaux), (morceaux, rapport.erreurs))
        temps = {"creneaux": ["matin", "soir"], "date": "2026-13-01", "epoques": {"a": "2020-01-01", "c": "2021-01-01"}, "semaine": ["lundi"],
                 "evenements": {"Noel": {"mois": 2, "jour": 30}}, "debut": {"epoque": "b"}}
        rapport, _ = verifier(projet(scene("A"), temps=temps, variables={"epoque_x": {"defaut": 0}}))
        for morceaux in (("date", "AAAA-MM-JJ"), ("semaine", "7 noms"), ("epoques", "retirez « date »"),
                         ("debut", "époque inconnue « b »"), ("« Noel »", "nom invalide"), ("« Noel »", "date impossible"), ("« epoque_x » est réservé",)):
            self.assertTrue(contient(rapport.erreurs, *morceaux), (morceaux, rapport.erreurs))
        rapport, _ = verifier(projet(scene("A"), temps={"creneaux": ["matin", "soir"], "epoques": {"a": "2020-01-01"}}))
        self.assertTrue(contient(rapport.erreurs, "epoques", "au moins deux"))

    def test_erreurs(self):
        a = scene("A", moment="nuit", contenu=[{"temps": "nuit"}, {"temps": 0}, {"effets": {"jour": 1}}])
        rapport, _ = verifier(projet(a, temps=self.TEMPS, variables={"moment": {"defaut": 0}},
                                     personnages={"moi": {"nom": "Moi"}, "jour": {"nom": "Jour"}}))
        for morceaux in (("créneau inconnu « nuit »",), ("nombre de créneaux",), ("« jour » est une variable du temps",),
                         ("variable « moment »", "réservée au temps"), ("« jour » est réservé au temps",)):
            self.assertTrue(contient(rapport.erreurs, *morceaux), (morceaux, rapport.erreurs))
        self.assertTrue(contient(rapport.avertissements, "« moment: nuit »"))
        rapport, _ = verifier(projet(scene("A", contenu=[{"temps": 1}]), lieux={"salon": {"decors": {"matin": "x"}}}))
        self.assertTrue(contient(rapport.erreurs, "« temps » demande un bloc"))
        self.assertTrue(contient(rapport.erreurs, "par créneau demande un bloc"))
        rapport, _ = verifier(projet(scene("A"), temps={"creneaux": ["matin"], "debut": {"creneau": "soir"}, "jours": "oui"}))
        for morceaux in (("creneaux", "au moins 2"), ("debut", "créneau inconnu"), ("jours", "true ou false")):
            self.assertTrue(contient(rapport.erreurs, *morceaux), (morceaux, rapport.erreurs))


class CartesEtDeplacements(unittest.TestCase):
    def projet_villes(self):
        lieux = {"salon": {"description": "Salon", "decors": ["salon"]}, "lyon": {"nom": "Lyon"}, "paris": {"nom": "Paris"},
                 "archives": {"nom": "Les archives"}, "maison": {"nom": "Chez moi"}}
        cartes = {"france": {"titre": "La France", "lieux": [{"lieu": "lyon", "x": 50, "y": 50, "carte": "lyon"},
                                                            {"lieu": "paris", "x": 40, "y": 20, "carte": "paris", "temps": 1, "si": 'moment != "soir"'}]},
                  "lyon": {"titre": "Lyon", "parent": "france", "lieux": [{"lieu": "maison", "x": 50, "y": 50, "scene": "B", "raccourci": True},
                                                                         {"lieu": "salon", "x": 20, "y": 20, "scene": "B", "si": 'moment == "soir"'}]},
                  "paris": {"titre": "Paris", "parent": "france", "lieux": [{"lieu": "archives", "x": 50, "y": 50, "scene": "C", "si": 'moment != "soir"', "temps": {"jours": 1}}]}}
        a = scene("A", carte="lyon")
        return projet(a, scene("B"), scene("C"), lieux=lieux, cartes=cartes,
                      temps={"creneaux": ["matin", "midi", "soir"], "jours": True, "debut": {"creneau": "midi"}})

    def test_couts_et_raccourcis(self):
        p = self.projet_villes()
        rapport, exploration = verifier(p)
        self.assertEqual(rapport.erreurs, [])
        vrai = lambda expr, couts=(): True  # noqa: E731
        cibles = fiches.cibles_carte(p, "paris", vrai)
        self.assertEqual([(c["scene"], c["clics"], c["couts"]) for c in cibles],
                         [("C", [("lieu", "archives")], [{"jours": 1}]), ("B", [("raccourci", "maison")], []),
                          ("B", [("parent", "france"), ("lieu", "lyon"), ("lieu", "salon")], [])])
        self.assertEqual(fiches._clics_textes(p, cibles[1]["clics"]), ["Chez moi"])
        # Depuis Lyon à midi : Paris coûte un créneau, il est alors soir et les archives sont fermées.
        self.assertEqual(exploration.entrees.get("C", []), [])
        self.assertTrue(contient(rapport.avertissements, "CH02_C" if False else "C.yaml", "jamais atteinte"))
        navigation = json.loads(fiches.generer(p, exploration)["game/navigation.json"])
        self.assertEqual(navigation["cartes"]["france"]["lieux"][1]["temps"], {"creneaux": 1})
        self.assertEqual(navigation["cartes"]["paris"]["lieux"][0]["temps"], {"jours": 1})
        self.assertEqual([(r["lieu"], r["carte_origine"], r["raccourci"]) for r in navigation["raccourcis"]], [("maison", "lyon", True)])

    def test_couts_appliques_sur_les_routes(self):
        p = self.projet_villes()
        p.bible["temps"]["debut"] = {"creneau": "matin"}
        rapport, exploration = verifier(p)
        self.assertEqual(rapport.erreurs, [])
        # Matin : Paris (midi), archives ouvertes, un jour de plus à l'arrivée (même créneau).
        etat = exploration.entrees["C"][0]
        self.assertEqual((etat["moment"], etat["jour"]), ("midi", 2))

    def test_erreurs(self):
        p = self.projet_villes()
        p.bible["cartes"]["france"]["lieux"][1]["temps"] = 0
        p.bible["cartes"]["paris"]["lieux"][0]["raccourci"] = "oui"
        p.bible["cartes"]["paris"]["lieux"].append({"lieu": "salon", "x": 1, "y": 1, "scene": "B"})
        rapport, _ = verifier(p)
        for morceaux in (("france", "« temps » : nombre de créneaux"), ("paris", "« raccourci » : true ou false")):
            self.assertTrue(contient(rapport.erreurs, *morceaux), (morceaux, rapport.erreurs))
        del p.bible["temps"]
        p.bible["cartes"]["france"]["lieux"][1]["temps"] = 1
        del p.bible["cartes"]["france"]["lieux"][1]["si"]
        for carte in p.bible["cartes"].values():
            for entree in carte["lieux"]:
                entree.pop("si", None); entree.pop("temps", None)
        p.bible["cartes"]["france"]["lieux"][1]["temps"] = 1
        rapport, _ = verifier(p)
        self.assertTrue(contient(rapport.erreurs, "coût du déplacement", "bloc « temps »"))


class Renommages(unittest.TestCase):
    def test_renommages_valides_et_fichier(self):
        p = projet(scene("A", suite="B"), scene("B"), renommages={"variables": {"amitie": "confiance", "vieux": "amitie"},
                                                              "scenes": {"C": "B"}})
        rapport, exploration = verifier(p)
        self.assertEqual(rapport.erreurs, [])
        self.assertEqual(p.renommages, {"variables": [("amitie", "confiance"), ("vieux", "amitie")], "scenes": [("c", "b")]})
        produits = fiches.generer(p, exploration)
        self.assertEqual(json.loads(produits["game/renommages.json"])["scenes"], [{"ancien": "c", "nouveau": "b"}])
        # Chaîne aplatie : vieux → amitie → confiance devient vieux → confiance.
        self.assertEqual(json.loads(produits["game/renommages.json"])["variables"],
                         [{"ancien": "amitie", "nouveau": "confiance"}, {"ancien": "vieux", "nouveau": "confiance"}])
        tests_renpy = produits["game/tests_routes.rpy"]
        self.assertIn("testcase renommages:", tests_renpy)
        self.assertIn('    $ setattr(store, "amitie", 70 + 1)', tests_renpy)
        self.assertIn("    $ assert confiance == 70 + 1, confiance", tests_renpy)
        self.assertEqual(json.loads(fiches.generer(projet(scene("A")))["game/renommages.json"])["variables"], [])

    def test_renommages_invalides(self):
        p = projet(scene("A"), renommages={"variables": {"confiance": "indice", "x": "nulle_part", "y": "y"}, "scenes": {"Z": "NOPE"}})
        rapport, _ = verifier(p)
        for morceaux in (("« confiance »", "existe encore"), ("« x »", "variable inconnue « nulle_part »"),
                         ("« y »", "identiques"), ("scenes, « Z »", "scène inconnue « NOPE »")):
            self.assertTrue(contient(rapport.erreurs, *morceaux), (morceaux, rapport.erreurs))
        rapport, _ = verifier(projet(scene("A"), renommages=["confiance"]))
        self.assertTrue(contient(rapport.erreurs, "renommages", "attendu : variables"))


class Structure(unittest.TestCase):
    def test_destination_et_element_inconnus(self):
        rapport, _ = verifier(projet(scene("A", contenu=[{"montre": "lena"}], suite="B")))
        self.assertTrue(contient(rapport.erreurs, "destination inconnue « B »"))
        self.assertTrue(contient(rapport.erreurs, "contenu[1]", "élément non reconnu"))

    def test_personnage_absent_de_la_scene(self):
        rapport, _ = verifier(projet(scene("A", personnages=["moi"], contenu=[{"lena": "Salut."}])))
        self.assertEqual(rapport.erreurs, [])
        self.assertTrue(contient(rapport.avertissements, "« lena » parle sans figurer"))

    def test_expressions_et_textes(self):
        contenu = [
            {"si": "confiance / 2 > 1", "alors": [{"narration": "a"}]},
            {"si": "inconnue > 1", "alors": [{"narration": "b"}]},
            {"si": "0 < confiance < 3", "alors": [{"narration": "c"}]},
            {"narration": "Valeur : [nope]"},
            {"effets": {"indice": 3}},
        ]
        rapport, _ = verifier(projet(scene("A", contenu=contenu)))
        self.assertTrue(contient(rapport.erreurs, "division"))
        self.assertTrue(contient(rapport.erreurs, "variable inconnue « inconnue »"))
        self.assertTrue(contient(rapport.erreurs, "comparaisons enchaînées"))
        self.assertTrue(contient(rapport.erreurs, "[nope]"))
        self.assertTrue(contient(rapport.erreurs, "« indice » est un booléen"))

    def test_libelles_en_double_ou_inclus(self):
        a = scene("A", choix=[{"libelle": "Oui", "destination": "B"}, {"libelle": "Oui", "destination": "B"},
                              {"libelle": "Oui, bien sûr", "destination": "B"}])
        rapport, _ = verifier(projet(a, scene("B")))
        self.assertTrue(contient(rapport.erreurs, "libellé « Oui » en double"))
        self.assertTrue(contient(rapport.avertissements, "« Oui » est contenu dans « Oui, bien sûr »"))

    def test_appel_d_une_scene_sans_retour(self):
        rapport, _ = verifier(projet(scene("A", contenu=[{"appel": "B"}]), scene("B")))
        self.assertTrue(contient(rapport.erreurs, "« B » doit se terminer par « retour: true »"))

    def test_conditions_au_format_compact(self):
        self.assertEqual(fiches.conditions_de({"conditions": {"confiance_min": 2, "indice": True}}),
                         ["confiance >= 2", "indice == True"])


class Routes(unittest.TestCase):
    def test_condition_d_entree_fausse_sur_une_route(self):
        a = scene("A", choix=[{"libelle": "Oui", "effets": {"confiance": 1}, "destination": "B"},
                              {"libelle": "Non", "destination": "B"}])
        b = scene("B", conditions=["confiance >= 1"])
        rapport, _ = verifier(projet(a, b))
        self.assertTrue(contient(rapport.erreurs, "B.yaml", "« confiance >= 1 » fausse", "« Non »"))

    def test_bornes_et_choix_indisponibles(self):
        a = scene("A", contenu=[{"effets": {"confiance": 9}}],
                  choix=[{"libelle": "Caché", "si": "indice", "destination": "B"}])
        rapport, _ = verifier(projet(a, scene("B")))
        self.assertTrue(contient(rapport.avertissements, "« confiance » vaut 9", "maximum 5"))
        self.assertTrue(contient(rapport.erreurs, "aucun choix disponible"))
        self.assertTrue(contient(rapport.avertissements, "jamais proposé"))
        self.assertTrue(contient(rapport.avertissements, "B.yaml", "jamais atteinte"))

    def test_routes_de_test_couvrent_fins_et_choix(self):
        a = scene("A", choix=[{"libelle": "Oui", "effets": {"confiance": 1}, "destination": "B"},
                              {"libelle": "Non", "destination": "C"}])
        b = scene("B", choix=[{"libelle": "Encore", "destination": "C"}, {"libelle": "Stop", "destination": "D"}])
        p = projet(a, b, scene("C"), scene("D"))
        rapport, exploration = verifier(p)
        self.assertEqual(rapport.erreurs, [])
        routes = fiches.routes_de_test(exploration)
        self.assertEqual({route["fin"] for route in routes}, {"C", "D"})
        self.assertEqual({(sid, rang) for route in routes for sid, rang, _ in route["choix"]},
                         {("A", 0), ("A", 1), ("B", 0), ("B", 1)})
        produits = fiches.generer(p, exploration)
        attendues = json.loads(produits["tests/routes_attendues.json"])["routes"]
        self.assertIn({"nom": "route_02", "choix": ["Oui", "Stop"], "fin": "d",
                       "etat_final": {"confiance": 1, "indice": False}}, attendues)
        tests_renpy = produits["game/tests_routes.rpy"]
        self.assertIn('    run Function(tests_viser, "Stop")', tests_renpy)
        self.assertIn('    $ assert renpy.seen_label("d")', tests_renpy)


class Generation(unittest.TestCase):
    def test_script_produit(self):
        a = scene("A", contenu=[
            {"decor": "salon", "transition": "fade"},
            {"montrer": "lena sourire", "position": "right", "transition": "dissolve"},
            {"lena": 'Elle a dit "oui".'},
            {"si": "confiance >= 2", "alors": [{"narration": "Proche."}], "sinon": []},
            {"effets": {"confiance": -1, "indice": True}},
        ], choix={"question": {"narration": "Et maintenant ?"},
                  "options": [{"libelle": "Rester", "si": "indice", "destination": "B"},
                              {"libelle": "Partir", "effets": {"confiance": 2}, "destination": "B"}]})
        texte = fiches.generer(projet(a, scene("B")))["game/story/chapitre_divers.rpy"]
        attendu = [
            "label a:",
            "    scene salon with fade",
            "    show lena sourire at right with dissolve",
            '    lena "Elle a dit \\"oui\\"."',
            "    if confiance >= 2:",
            '        "Proche."',
            "    else:",
            "        pass",
            "    $ confiance -= 1",
            "    $ indice = True",
            "    menu:",
            '        "Et maintenant ?"',
            '        "Rester" if indice:',
            "            jump b",
            '        "Partir":',
            "            $ confiance += 2",
        ]
        for ligne in attendu:
            self.assertIn(ligne + "\n", texte + "\n")

    def test_ecriture_protegee_et_nettoyage(self):
        with tempfile.TemporaryDirectory() as dossier:
            racine = Path(dossier)
            story = racine / "game" / "story"
            story.mkdir(parents=True)
            (story / "manuel.rpy").write_text("label a:\n    return\n", encoding="utf-8")
            (story / "chapitre_99.rpy").write_text(f"# {fiches.MARQUEUR}\n", encoding="utf-8")
            (racine / "game" / "galerie.json").write_text("{}", encoding="utf-8")
            p = projet(scene("A"), racine=racine)

            rapport, _ = verifier(p)
            self.assertTrue(contient(rapport.erreurs, "manuel.rpy", "définit aussi « a »"))

            rapport = fiches.Rapport()
            ecrits, supprimes = fiches.ecrire(p, fiches.generer(p), rapport)
            self.assertTrue(contient(rapport.erreurs, "game/galerie.json", "écrit à la main"))
            self.assertEqual(supprimes, ["game/story/chapitre_99.rpy"])
            self.assertIn("game/story/chapitre_divers.rpy", ecrits)

            rapport = fiches.Rapport()
            fiches.ecrire(p, fiches.generer(p), rapport, remplacer=True)
            self.assertEqual(rapport.erreurs, [])
            self.assertIn("entrees", json.loads((racine / "game" / "galerie.json").read_text(encoding="utf-8")))


class Traductions(unittest.TestCase):
    @staticmethod
    def projet_traduit():
        a = scene("A", contenu=[{"narration": "Il pleut."}, {"lena": "Il pleut."}, {"narration": "Il pleut."},
                                {"narration": "Valeur : [confiance]."}],
                  choix={"question": {"lena": "Tu restes ?"},
                         "options": [{"libelle": "Oui", "effets": {"confiance": 1}, "destination": "B"},
                                     {"libelle": "Non", "destination": "B"}]},
                  galerie={"titre": "Souvenir", "images": ["salon"]})
        return projet(a, scene("B"), langues={"source": "fr", "traductions": ["en"]})

    @staticmethod
    def traduire_tout(p, prefixe="EN "):
        donnees = yaml.safe_load(fiches.traduire(p, "en")[0])
        for entree in donnees["repliques"].values():
            entree["texte"] = prefixe + entree["source"]
        for entree in donnees["textes"]:
            entree["texte"] = prefixe + entree["source"]
        p.traductions["en"] = donnees
        return donnees

    def test_identifiants_stables_et_uniques(self):
        p = self.projet_traduit()
        ids = [replique.rid for replique in fiches.repliques(p)]
        self.assertEqual(ids, [replique.rid for replique in fiches.repliques(p)])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids[2], ids[0] + "_1", "même réplique répétée dans la scène : suffixe")
        self.assertNotEqual(ids[0], ids[1], "même texte, autre personnage : autre identifiant")
        produits = fiches.generer(p)
        chapitre = produits["game/story/chapitre_divers.rpy"]
        self.assertIn(f'    "Il pleut." id {ids[0]}\n', chapitre)
        self.assertIn(f'        lena "Tu restes ?" id {ids[4]}\n', chapitre)
        self.assertIn('define lena = Character(_("Léna"), color="#c8a2ff")', produits[fiches.FICHIER_BIBLE_RPY])
        sans_traduction = fiches.generer(projet(scene("A", contenu=[{"narration": "Il pleut."}])))
        self.assertNotIn(" id ", sans_traduction["game/story/chapitre_divers.rpy"])
        self.assertFalse(any(relatif.startswith("game/tl/") for relatif in sans_traduction))

    def test_traduire_puis_generer(self):
        p = self.projet_traduit()
        rapport, _ = verifier(p)
        self.assertTrue(contient(rapport.avertissements, "en.yaml", "absent"))
        _, bilan = fiches.traduire(p, "en")
        self.assertEqual((bilan["repliques"], bilan["textes"], bilan["a_traduire"]), (5, 5, 10))
        donnees = self.traduire_tout(p)
        ids = list(donnees["repliques"])
        donnees["repliques"][ids[3]]["texte"] = "Value: [confiance]."
        for entree in donnees["textes"]:
            entree["texte"] = {"Oui": "Yes", "Non": "No"}.get(entree["source"], entree["texte"])
        rapport, exploration = verifier(p)
        self.assertEqual((rapport.erreurs, rapport.avertissements), ([], []))
        produits = fiches.generer(p, exploration)
        tl = produits["game/tl/english/story/chapitre_divers.rpy"]
        self.assertIn(f"translate english {ids[0]}:\n\n    # \"Il pleut.\"\n    \"EN Il pleut.\"\n", tl)
        self.assertIn('    lena "EN Tu restes ?"', tl)
        self.assertIn('    old "Oui"\n    new "Yes"', produits["game/tl/english/story/textes.rpy"])
        self.assertEqual(json.loads(produits[fiches.FICHIER_LANGUES])["traductions"],
                         [{"code": "en", "renpy": "english", "nom": "English"}])
        for route in json.loads(produits[fiches.FICHIER_ROUTES])["routes"]:
            self.assertEqual(route["choix_traduits"]["en"], [{"Oui": "Yes", "Non": "No"}[c] for c in route["choix"]])
        tests_renpy = produits[fiches.FICHIER_TESTS_RENPY]
        self.assertIn('    run Language("english")\n    pause 0.5\n    run Start()', tests_renpy)
        self.assertIn('    run Function(tests_viser, "Yes")', tests_renpy)

    def test_texte_change_reprise_a_revoir_et_obsoletes(self):
        p = self.projet_traduit()
        self.traduire_tout(p)
        contenu = p.scenes["A"]["contenu"]
        contenu[3] = {"narration": "Valeur actuelle : [confiance]."}
        del contenu[1]
        p.scenes["A"]["choix"]["options"].append({"libelle": "Peut-être", "destination": "B"})
        texte, bilan = fiches.traduire(p, "en")
        nouveau = yaml.safe_load(texte)
        corrigee = [entree for entree in nouveau["repliques"].values() if entree["source"].startswith("Valeur actuelle")][0]
        self.assertEqual((corrigee["texte"], corrigee["a_revoir"]), ("EN Valeur : [confiance].", "Valeur : [confiance]."))
        self.assertEqual((bilan["a_revoir"], bilan["a_traduire"], bilan["obsoletes"]), (1, 1, 1))
        self.assertEqual([(entree["source"], entree["texte"]) for entree in nouveau["obsoletes"]], [("Il pleut.", "EN Il pleut.")])
        p.traductions["en"] = nouveau
        rapport, _ = verifier(p)
        self.assertTrue(contient(rapport.avertissements, "1 réplique(s) ou texte(s) à traduire"))
        self.assertTrue(contient(rapport.avertissements, "1 traduction(s) à revoir"))
        self.assertEqual(yaml.safe_load(fiches.traduire(p, "en")[0]), nouveau, "traduire est stable")

    def test_erreurs_de_traduction(self):
        p = self.projet_traduit()
        donnees = self.traduire_tout(p)
        ids = list(donnees["repliques"])
        donnees["repliques"][ids[3]]["texte"] = "Value: [inconnue]."
        donnees["repliques"][ids[0]]["texte"] = "{i}Rain.{/i}"
        for entree in donnees["textes"]:
            if entree["source"] in ("Oui", "Non"):
                entree["texte"] = "Same"
        rapport, _ = verifier(p)
        self.assertTrue(contient(rapport.erreurs, ids[3], "[inconnue]"))
        self.assertTrue(contient(rapport.erreurs, "A : deux choix du même menu", "« Same »"))
        self.assertTrue(contient(rapport.avertissements, ids[0], "balises"))
        self.assertTrue(contient(rapport.avertissements, ids[3], "[variables]"))

    def test_langues_de_la_bible(self):
        rapport, _ = verifier(projet(scene("A"), langues={"source": "fr", "traductions": ["xx", "fr"]}))
        self.assertTrue(contient(rapport.erreurs, "code de langue inconnu 'xx'"))
        self.assertTrue(contient(rapport.erreurs, "« fr » est déjà la langue source"))

    def test_importer_une_reponse_et_paquet(self):
        p = self.projet_traduit()
        p.traductions["en"] = yaml.safe_load(fiches.traduire(p, "en")[0])
        rid = fiches.repliques(p)[0].rid
        reponse = (f"```yaml\nrepliques:\n  {rid}:\n    texte: \"It rains.\"\n  inconnue_12345678:\n    texte: \"x\"\n"
                   "textes:\n  - source: \"Oui\"\n    texte: \"Yes\"\n```\n")
        self.assertEqual(fiches.importer_traductions(p, "en", reponse), 2)
        lignes, textes = fiches.traductions_de(p, "en")
        self.assertEqual((lignes[rid], textes["Oui"]), ("It rains.", "Yes"))
        paquet = fiches.paquet_traduction(p, "en", yaml.safe_load(fiches.traduire(p, "en")[0]))
        self.assertIn("- Oui → Yes", paquet)
        self.assertNotIn(f"  {rid}:", paquet)
        self.assertIn("```yaml\nrepliques:", paquet)


class GrapheHtml(unittest.TestCase):
    def test_disposition_cycles_et_scenes_isolees(self):
        a = scene("A", choix=[{"libelle": "Oui", "destination": "B"}, {"libelle": "Non", "destination": "C"}])
        b = scene("B", suite="D")
        c = scene("C", choix=[{"libelle": "Encore", "destination": "A"}, {"libelle": "Stop", "destination": "D"},
                              {"libelle": "Caché", "si": "indice", "destination": "D"}])
        p = projet(a, b, c, scene("D"), scene("Z"))
        rapport, exploration = verifier(p)
        self.assertEqual(rapport.erreurs, [])
        donnees = fiches.donnees_graphe(p, exploration, rapport)
        scenes = {s["id"]: s for s in donnees["scenes"]}
        self.assertLess(scenes["A"]["x"], scenes["B"]["x"])
        self.assertLess(scenes["B"]["x"], scenes["D"]["x"])
        self.assertLess(scenes["C"]["x"], scenes["D"]["x"])
        retour = [arete for arete in donnees["aretes"] if (arete["de"], arete["vers"]) == ("C", "A")]
        self.assertTrue(retour and retour[0]["arriere"], "C → A ferme un cycle")
        cache = [sortie for sortie in scenes["C"]["sorties"] if sortie["libelle"] == "Caché"][0]
        self.assertFalse(cache["propose"])
        self.assertFalse(scenes["Z"]["atteinte"])
        self.assertIn("jamais atteinte", " ".join(scenes["Z"]["avertissements"]))
        for x in {s["x"] for s in scenes.values()}:
            colonne = sorted((s for s in scenes.values() if s["x"] == x), key=lambda s: s["y"])
            for haut, bas in zip(colonne, colonne[1:]):
                self.assertGreaterEqual(bas["y"], haut["y"] + haut["h"], "scènes superposées")

    def test_page_de_la_demo(self):
        rapport = fiches.Rapport()
        p = fiches.charger(DEMO, rapport)
        exploration = fiches.verifier(p, rapport)
        page = fiches.graphe_html(p, exploration, rapport)
        self.assertIn(fiches.MARQUEUR, page)
        self.assertNotIn("{{TITRE}}", page)
        donnees = json.loads(page.split("const DONNEES = ", 1)[1].split(";</script>", 1)[0])
        scenes = {s["id"]: s for s in donnees["scenes"]}
        self.assertEqual(set(scenes), set(p.scenes))
        self.assertTrue(all(s["atteinte"] for s in scenes.values()))
        self.assertTrue(scenes["CH01_SC01"]["debut"])
        entree = {e["variable"]: e["valeurs"] for e in scenes["CH01_SC02"]["entree"]}
        self.assertEqual(entree["relation_lena"], ["3", "4"])
        self.assertEqual([(s["type"], s["libelle"]) for s in scenes["CH01_SC03B"]["sorties"]],
                         [("appel", "appel CH01_SOUVENIR"), ("suite", "suite")])
        self.assertEqual(scenes["CH01_SC02"]["traductions"], [{"code": "en", "total": 7, "faites": 7}])
        self.assertEqual({r["fin"] for r in donnees["routes"]}, {"CH01_SC04", "CH01_SC05"})
        route = donnees["routes"][0]
        self.assertEqual(route["scenes"][0], "CH01_SC01")
        self.assertEqual([e["choix"] for e in route["etapes"] if e["choix"]], route["choix"])


class Provisoires(unittest.TestCase):
    def test_images_provisoires_puis_remplacees(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as dossier:
            racine = Path(dossier)
            (racine / "game" / "images").mkdir(parents=True)
            p = projet(scene("A", contenu=[{"decor": "salon"}, {"montrer": "lena sourire"}]), racine=racine)

            crees, retires = fiches.provisoires(p)
            self.assertEqual(sorted(crees), ["game/images/provisoires/lena sourire.png", "game/images/provisoires/salon.png"])
            self.assertEqual(retires, [])
            self.assertEqual(Image.open(racine / "game/images/provisoires/salon.png").size, (1920, 1080))
            self.assertEqual(Image.open(racine / "game/images/provisoires/lena sourire.png").size, (620, 940))
            self.assertIn("2 provisoires", fiches.production(p)[1])

            # Une image définitive arrive : la provisoire disparaît.
            definitive = racine / "game" / "images" / "salon.png"
            definitive.write_bytes((racine / "game/images/provisoires/salon.png").read_bytes())
            crees, retires = fiches.provisoires(p)
            self.assertEqual((crees, retires), ([], ["game/images/provisoires/salon.png"]))
            self.assertIn("1 définitives, 1 provisoires", fiches.production(p)[1])


if __name__ == "__main__":
    unittest.main()
