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
    def test_age_obligatoire_et_minimum(self):
        rapport, _ = verifier(projet(scene("A"), personnages={"moi": {"nom": "Moi"}, "lena": {"nom": "Léna", "age": 17}}))
        self.assertTrue(contient(rapport.erreurs, "« moi »", "« age » obligatoire"))
        self.assertTrue(contient(rapport.erreurs, "« lena »", "âge 17", "minimum à 18"))

    def test_age_minimum_reglable(self):
        rapport, _ = verifier(projet(scene("A"), age_minimum=12,
                                     personnages={"moi": {"nom": "Moi", "age": 30}, "lena": {"nom": "Léna", "age": 14}}))
        self.assertEqual(rapport.erreurs, [])

    def test_debut_inconnu(self):
        rapport, _ = verifier(projet(scene("A"), debut="Z"))
        self.assertTrue(contient(rapport.erreurs, "« debut »"))


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
        self.assertIn('    click "Stop"', tests_renpy)
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
        self.assertIn('    click "Yes"', tests_renpy)

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
