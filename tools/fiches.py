#!/usr/bin/env python3
"""Chaîne d'écriture : bible narrative et fiches de scène (YAML) → script .rpy du
sous-ensemble commun Ren'Py / Godot. Format : contenu/LISEZMOI.md.

  verifier          contrôle la bible et les fiches, puis explore toutes les routes
  generer           vérifie ; écrit game/story/*.rpy, game/galerie.json, game/navigation.json
                    (cartes et présence des personnages) et les tests de parcours (Godot et
                    Ren'Py) ; fait relire le script par Godot
  provisoires       images et vidéos provisoires pour tout ce qui manque encore
  production        images et vidéos à produire → contenu/production.md
  graphe [--ouvrir] graphe des routes → contenu/graphe.html (interactif) et graphe.md (Mermaid)
  contexte SCENE    paquet de contexte pour écrire ou réviser une scène
  traduire [LANGUE] met à jour contenu/traductions/<langue>.yaml (répliques et textes à traduire)

Usage : .venv/bin/python tools/fiches.py <commande>
"""
from __future__ import annotations

import argparse
import calendar
import datetime
import ast
import difflib
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML manquant : python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")

RACINE = Path(__file__).resolve().parent.parent
MARQUEUR = "Fichier généré par tools/fiches.py depuis contenu/ : ne pas modifier à la main."
FICHIER_BIBLE_RPY = "game/story/personnages_et_variables.rpy"
FICHIER_GALERIE = "game/galerie.json"
FICHIER_NAVIGATION = "game/navigation.json"
FICHIER_PERSONNAGES = "game/personnages.json"
FICHIER_RENOMMAGES = "game/renommages.json"
FICHIER_TEMPS = "game/temps.json"
FICHIER_ROUTES = "tests/routes_attendues.json"
FICHIER_TESTS_RENPY = "game/tests_routes.rpy"
FICHIER_LANGUES = "game/langues.json"
DOSSIER_TRADUCTIONS = "contenu/traductions"
DOSSIER_PROVISOIRES = "game/images/provisoires"
LISTE_VIDEOS_PROVISOIRES = "game/videos/provisoires.txt"
FICHIER_GRAPHE_HTML = "contenu/graphe.html"
MODELE_GRAPHE_HTML = Path(__file__).resolve().parent / "graphe_modele.html"
## Géométrie du graphe HTML, en pixels : les positions des scènes et des liens sont
## calculées ici, la page (tools/graphe_modele.html) reprend ces valeurs.
GRAPHE = {"largeur": 300, "entete": 70, "haut_sorties": 4, "ligne": 26, "bas": 8,
          "ecart_colonnes": 150, "ecart_noeuds": 36, "marge": 60}
ROUTES_MAX = 12
## Âge minimum des personnages qui en déclarent un (facultatif), réglable dans la bible par « age_minimum ».
AGE_MINIMUM = 18
## Langues possibles (bible, « langues ») : code → (nom de la traduction Ren'Py, nom affiché).
LANGUES = {
    "fr": ("french", "Français"), "en": ("english", "English"), "es": ("spanish", "Español"),
    "de": ("german", "Deutsch"), "it": ("italian", "Italiano"), "pt": ("portuguese", "Português"),
    "nl": ("dutch", "Nederlands"), "pl": ("polish", "Polski"), "ru": ("russian", "Русский"),
    "ja": ("japanese", "日本語"), "ko": ("korean", "한국어"), "zh": ("schinese", "简体中文"),
}
LANGUE_SOURCE = "fr"
CHAMPS_TRADUCTION = {"repliques", "textes", "obsoletes"}
## Seuil de ressemblance pour reprendre une traduction quand son texte source a changé.
SEUIL_REPRISE = 0.6

TRANSITIONS = ("dissolve", "fade")
POSITIONS = ("left", "center", "right", "truecenter")
FONCTIONS = {"min": min, "max": max, "abs": abs, "str": str, "int": int, "float": float}
EXTENSIONS_IMAGES = (".png", ".jpg", ".jpeg", ".webp")
ELEMENTS = ("narration", "decor", "montrer", "cacher", "video", "pause", "musique", "son", "effets", "si", "appel", "temps")
MODIFICATEURS = {
    "decor": {"transition"},
    "montrer": {"position", "transition"},
    "cacher": {"transition"},
    "si": {"alors", "sinon_si", "sinon"},
}
CHAMPS_FICHE = {"id", "titre", "chapitre", "lieu", "moment", "personnages", "objectif_narratif", "resume",
                "conditions", "contenu", "choix", "suite", "fin", "retour", "carte", "galerie", "notes"}
CHAMPS_OPTION = {"id", "libelle", "si", "effets", "contenu", "destination"}
FINS = ("choix", "suite", "fin", "retour", "carte")
## Navigation (bible, « cartes »). Deux affichages : « carte » (une image avec des lieux placés
## dessus, x et y en pourcentage) et « pieces » (une barre en bas de l'écran, une vignette par
## pièce : icône du lieu et avatars des personnages présents). Un lieu joue une scène ou ouvre
## une sous-carte (les pièces d'un bâtiment). « presence » d'un personnage : règles { lieu, si }
## lues dans l'ordre à chaque carte ; le résultat est la variable lieu_<personnage>.
CHAMPS_CARTE = {"titre", "affichage", "image", "parent", "lieux"}
AFFICHAGES_CARTE = ("carte", "pieces")
CHAMPS_LIEU_CARTE = {"lieu", "x", "y", "scene", "carte", "si", "temps", "raccourci"}
CHAMPS_PRESENCE = {"lieu", "si"}
PREFIXE_PRESENCE = "lieu_"
## Jauges, compétences et relations d'un personnage : { defaut, min, max, nom, description, paliers }.
## Une relation est déclarée sur l'un des deux personnages, sous l'id de l'autre ; elle vaut pour les deux.
CHAMPS_JAUGE = {"defaut", "min", "max", "nom", "description", "paliers"}
GENRES_JAUGES = (("jauges", "jauge"), ("competences", "compétence"), ("relations", "relation"))
## Temps (bible, « temps ») : créneaux de la journée, jours, semaine. Variables produites :
## creneau (rang), moment (nom du créneau), jour, jour_semaine et jour_semaine_rang ; le label
## temps_avancer du script généré fait passer au créneau suivant.
CHAMPS_TEMPS = {"creneaux", "jours", "semaine", "debut", "date", "evenements", "epoques"}
LABEL_TEMPS = "temps_avancer"
LABELS_TEMPS = ("temps_avancer", "temps_jour_suivant", "temps_calculer_noms", "temps_calculer_mois", "temps_sauter_jours",
                "temps_sauter_mois", "temps_sauter_mois_suivant", "temps_sauter_mois_jours")
VARIABLES_TEMPS = ("creneau", "moment", "jour", "jour_semaine", "jour_semaine_rang", "jour_mois", "mois", "annee", "epoque")
## Avec une date de départ (« date »), les variables jour_mois, mois et annee suivent un vrai
## calendrier ; « evenements » donne des booléens evenement_<nom> vrais le jour dit ; « epoques »
## (nom → date) permet les voyages dans le temps : chaque époque garde sa propre date.
PREFIXES_TEMPS = ("temps_", "evenement_", "epoque_")
CHAMPS_EPOQUE = ("annee", "mois", "jour_mois", "jour", "jour_semaine_rang", "creneau", "temps_longueur_mois", "temps_bissextile_rang")
SEMAINE_NOMS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_NOMS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
SAUT_MAXIMUM = 36600
MOTS_RESERVES = set(ELEMENTS) | set(FONCTIONS) | {
    "alors", "sinon", "sinon_si", "transition", "position", "label", "define", "default", "image",
    "scene", "show", "hide", "with", "jump", "call", "return", "pass", "play", "stop", "queue", "window",
    "menu", "if", "elif", "else", "while", "for", "python", "init", "screen", "transform", "style",
    "and", "or", "not", "in", "is", "True", "False", "None", "renpy", "store", "persistent", "config",
    "gui", "build", "start", "extend", "nvl", "voice", "centered", "narrator", "adv", "naviguer"}
IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")
ID_SCENE = re.compile(r"^[A-Z][A-Z0-9_]*$")
MOT_IMAGE = re.compile(r"^[A-Za-z0-9_]+( [A-Za-z0-9_]+)*$")
INTERPOLATION = re.compile(r"\[([^\[\]]*)\]")
BALISE = re.compile(r"\{/?[a-z_]+[^{}]*\}")
NOEUDS_AUTORISES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Name, ast.Load, ast.Constant, ast.Call, ast.List, ast.Tuple,
)


# --- Rapport et projet ---------------------------------------------------------------

class Rapport:
    """Erreurs (bloquantes) et avertissements, sans doublons."""

    def __init__(self):
        self.erreurs: list[str] = []
        self.avertissements: list[str] = []
        self._cles: set = set()

    def erreur(self, ou, message, cle=None):
        self._ajouter(self.erreurs, ou, message, cle)

    def avertir(self, ou, message, cle=None):
        self._ajouter(self.avertissements, ou, message, cle)

    def _ajouter(self, liste, ou, message, cle):
        cle = cle or (ou, message)
        if cle in self._cles:
            return
        self._cles.add(cle)
        liste.append(f"{ou} : {message}")

    def afficher(self):
        for message in self.erreurs:
            print(f"ERREUR     {message}")
        for message in self.avertissements:
            print(f"attention  {message}")


@dataclass
class Projet:
    racine: Path
    bible: dict
    scenes: dict = field(default_factory=dict)
    fichiers: dict = field(default_factory=dict)
    traductions: dict = field(default_factory=dict)  # code de langue → contenu de contenu/traductions/<code>.yaml

    @property
    def personnages(self) -> dict:
        return _dict(self.bible.get("personnages"))

    @property
    def langue_source(self) -> str:
        return str(_dict(self.bible.get("langues")).get("source", LANGUE_SOURCE))

    @property
    def langues_cibles(self) -> list:
        """Codes des traductions déclarées dans la bible (« langues.traductions »)."""
        codes = _liste(_dict(self.bible.get("langues")).get("traductions"))
        return [code for code in dict.fromkeys(codes) if code in LANGUES and code != self.langue_source]

    @property
    def variables(self) -> dict:
        return _dict(self.bible.get("variables"))

    @property
    def lieux(self) -> dict:
        return _dict(self.bible.get("lieux"))

    @property
    def cartes(self) -> dict:
        return _dict(self.bible.get("cartes"))

    @property
    def variables_presence(self) -> dict:
        """Variables calculées à chaque carte : lieu_<personnage> pour chaque personnage qui a
        des règles de présence. {nom : {defaut, description, personnage}}."""
        resultat = {}
        for pid, fiche in self.personnages.items():
            if isinstance(pid, str) and isinstance(fiche, dict) and fiche.get("presence") is not None:
                resultat[f"{PREFIXE_PRESENCE}{pid}"] = {
                    "defaut": "", "personnage": pid,
                    "description": f"Lieu où se trouve {pid} (règles « presence » de la bible, recalculé à chaque carte).",
                }
        return resultat

    @property
    def variables_personnages(self) -> dict:
        """Jauges, compétences et relations des personnages (« jauges », « competences »,
        « relations » de la bible), une variable <personnage>_<nom> chacune : {nom : {defaut, min,
        max, description, personnage, genre, cle, nom, paliers, avec}}. « paliers » : [(seuil, nom)]
        croissants, ou []. Une relation (clé : id de l'autre personnage, « avec ») vaut pour les deux."""
        resultat = {}
        for pid, fiche in self.personnages.items():
            if not isinstance(pid, str) or not isinstance(fiche, dict):
                continue
            for champ, genre in GENRES_JAUGES:
                for cle, jauge in _dict(fiche.get(champ)).items():
                    jauge = _jauge(jauge)
                    if not isinstance(cle, str):
                        continue
                    paliers = sorted((seuil, str(nom)) for seuil, nom in _dict(jauge.get("paliers")).items() if _est_nombre(seuil))
                    if genre == "relation":
                        nom = str(jauge.get("nom") or "")
                        description = f"Relation entre {self.nom_personnage(pid)} et {self.nom_personnage(cle)}."
                    else:
                        nom = str(jauge.get("nom") or cle.replace("_", " ").capitalize())
                        description = f"{genre.capitalize()} « {cle} » de {pid}."
                    resultat[f"{pid}_{cle}"] = {
                        "defaut": jauge.get("defaut"), "personnage": pid, "genre": genre, "cle": cle, "nom": nom,
                        "avec": cle if genre == "relation" else "",
                        "description": str(jauge.get("description") or description), "paliers": paliers,
                        **{borne: jauge[borne] for borne in ("min", "max") if borne in jauge},
                    }
        return resultat

    def nom_personnage(self, pid) -> str:
        return str(_dict(self.personnages.get(pid)).get("nom") or pid)

    @property
    def variables_modifiables(self) -> dict:
        """Variables de la bible et des personnages : celles que « effets » peut changer."""
        return {**self.variables, **self.variables_personnages}

    @property
    def variables_toutes(self) -> dict:
        """Variables de la bible, des personnages, du temps, puis de présence : tout ce qu'une expression peut lire."""
        return {**self.variables, **self.variables_personnages, **self.variables_temps, **self.variables_presence}

    @property
    def temps(self) -> dict | None:
        """Modèle de temps de la bible : {creneaux: [noms], jours: bool, semaine: [noms],
        debut: {creneau: rang, jour: n, jour_semaine: rang}}, ou None s'il n'est pas déclaré."""
        bloc = self.bible.get("temps")
        if not isinstance(bloc, dict):
            return None
        creneaux = [str(c) for c in _liste(bloc.get("creneaux"))]
        semaine = [str(j) for j in _liste(bloc.get("semaine"))]
        debut = _dict(bloc.get("debut"))
        epoques = {str(nom): _date_de(quand) for nom, quand in _dict(bloc.get("epoques")).items() if _date_de(quand) is not None}
        epoque = str(debut["epoque"]) if debut.get("epoque") in epoques else next(iter(epoques), "")
        date = epoques[epoque] if epoques else _date_de(bloc.get("date"))
        if date is not None and not semaine:
            semaine = list(SEMAINE_NOMS)
        rang = creneaux.index(str(debut["creneau"])) if debut.get("creneau") in creneaux else 0
        if date is not None and len(semaine) == 7:
            rang_semaine = date.weekday()
        else:
            rang_semaine = semaine.index(str(debut["jour_semaine"])) if debut.get("jour_semaine") in semaine else 0
        jour = debut.get("jour") if isinstance(debut.get("jour"), int) and not isinstance(debut.get("jour"), bool) else 1
        evenements = {}
        for nom, quand in _dict(bloc.get("evenements")).items():
            quand = _dict(quand)
            if isinstance(nom, str) and _est_nombre(quand.get("mois")) and _est_nombre(quand.get("jour")):
                evenements[nom] = (int(quand["mois"]), int(quand["jour"]))
        return {"creneaux": creneaux, "jours": bool(bloc.get("jours", False)) or bool(semaine) or date is not None,
                "semaine": semaine, "date": date, "evenements": evenements, "epoques": epoques,
                "debut": {"creneau": rang, "jour": jour, "jour_semaine": rang_semaine, "epoque": epoque}}

    @property
    def variables_temps(self) -> dict:
        """Variables du temps, lues par les fiches et modifiées seulement par l'élément « temps »."""
        temps = self.temps
        if temps is None or not temps["creneaux"]:
            return {}
        debut = temps["debut"]
        resultat = {
            "creneau": {"defaut": debut["creneau"], "min": 0, "max": len(temps["creneaux"]) - 1,
                        "description": f"Rang du créneau de la journée : {', '.join(f'{i} {c}' for i, c in enumerate(temps['creneaux']))}."},
            "moment": {"defaut": temps["creneaux"][debut["creneau"]],
                       "description": f"Nom du créneau ({', '.join(temps['creneaux'])}) ; avance avec l'élément « temps »."},
        }
        if temps["jours"]:
            resultat["jour"] = {"defaut": debut["jour"], "min": 1, "description": "Numéro du jour ; passe au suivant après le dernier créneau."}
        if temps["semaine"]:
            resultat["jour_semaine_rang"] = {"defaut": debut["jour_semaine"], "min": 0, "max": len(temps["semaine"]) - 1,
                                             "description": "Rang du jour dans la semaine (interne).", "interne": True}
            resultat["jour_semaine"] = {"defaut": temps["semaine"][debut["jour_semaine"]],
                                        "description": f"Jour de la semaine ({', '.join(temps['semaine'])})."}
        date = temps["date"]
        if date is not None:
            resultat["jour_mois"] = {"defaut": date.day, "min": 1, "max": 31, "description": "Jour du mois (1 à 31)."}
            resultat["mois"] = {"defaut": date.month, "min": 1, "max": 12, "description": "Mois (1 janvier … 12 décembre)."}
            resultat["annee"] = {"defaut": date.year, "description": "Année."}
            for nom, defaut in (("temps_longueur_mois", _longueur_mois(date.year, date.month)), ("temps_bissextile_rang", date.year % 4),
                                ("temps_saut", 0), ("temps_cible_jour", 0), ("temps_cible_mois", 0)):
                resultat[nom] = {"defaut": defaut, "description": "Calcul du calendrier (interne).", "interne": True}
            for nom, (mois, jour) in temps["evenements"].items():
                resultat[f"evenement_{nom}"] = {"defaut": (date.month, date.day) == (mois, jour),
                                                "description": f"Vrai le {jour} {MOIS_NOMS[mois - 1]} (bible, temps.evenements)."}
            if temps["epoques"]:
                resultat["epoque"] = {"defaut": debut["epoque"], "description": f"Époque courante ({', '.join(temps['epoques'])}) ; "
                                      "change avec « temps: { epoque: nom } », chaque époque gardant sa date."}
                for nom, quand in temps["epoques"].items():
                    valeurs = {"annee": quand.year, "mois": quand.month, "jour_mois": quand.day, "jour": 1,
                               "jour_semaine_rang": quand.weekday() if len(temps["semaine"]) == 7 else 0,
                               "creneau": debut["creneau"], "temps_longueur_mois": _longueur_mois(quand.year, quand.month),
                               "temps_bissextile_rang": quand.year % 4}
                    for champ in CHAMPS_EPOQUE:
                        resultat[f"epoque_{nom}_{champ}"] = {"defaut": valeurs[champ], "interne": True,
                                                             "description": f"Date laissée dans l'époque « {nom} » (interne)."}
        return resultat

    def avancer_temps(self, etat: dict) -> dict:
        """Un créneau de plus dans un état (explorateur) : mêmes règles que le label temps_avancer."""
        temps = self.temps
        etat = dict(etat)
        etat["creneau"] = etat.get("creneau", 0) + 1
        if etat["creneau"] >= len(temps["creneaux"]):
            etat["creneau"] = 0
            etat = self.jour_suivant(etat)
        etat["moment"] = temps["creneaux"][etat["creneau"]]
        return etat

    def jour_suivant(self, etat: dict, jours: int = 1) -> dict:
        """Un jour de plus (ou plusieurs), sans changer de créneau : label temps_jour_suivant."""
        temps = self.temps
        etat = dict(etat)
        if temps["jours"]:
            etat["jour"] = etat.get("jour", 1) + jours
        if temps["semaine"]:
            etat["jour_semaine_rang"] = (etat.get("jour_semaine_rang", 0) + jours) % len(temps["semaine"])
            etat["jour_semaine"] = temps["semaine"][etat["jour_semaine_rang"]]
        if temps["date"] is not None:
            date = datetime.date(etat["annee"], etat["mois"], etat["jour_mois"]) + datetime.timedelta(days=jours)
            etat.update({"annee": date.year, "mois": date.month, "jour_mois": date.day,
                         "temps_longueur_mois": _longueur_mois(date.year, date.month), "temps_bissextile_rang": date.year % 4})
            for nom, (mois, jour) in temps["evenements"].items():
                etat[f"evenement_{nom}"] = (date.month, date.day) == (mois, jour)
        return etat

    def sauter_mois(self, etat: dict, nombre: int) -> dict:
        """N mois plus tard, même jour du mois (ou le dernier jour du mois d'arrivée) : label temps_sauter_mois."""
        etat = dict(etat)
        cible_jour = etat["jour_mois"]
        etat["temps_cible_jour"] = cible_jour
        for _ in range(nombre):
            mois_cible = etat["mois"] % 12 + 1
            etat["temps_cible_mois"] = mois_cible
            while not (etat["mois"] == mois_cible and etat["jour_mois"] in (cible_jour, etat["temps_longueur_mois"])):
                etat = self.jour_suivant(etat)
        etat["temps_saut"] = 0
        return etat

    def aller_date(self, etat: dict, date: datetime.date) -> dict:
        """À une date connue d'avance, passée ou future : les champs sont posés directement."""
        temps = self.temps
        etat = dict(etat)
        etat.update(self.champs_date(date))
        etat["jour"] = (date - temps["date"]).days + 1
        for nom, (mois, jour) in temps["evenements"].items():
            etat[f"evenement_{nom}"] = (date.month, date.day) == (mois, jour)
        return etat

    def champs_date(self, date: datetime.date) -> dict:
        """Champs du calendrier d'une date connue à la génération (sans le compteur de jours)."""
        temps = self.temps
        champs = {"annee": date.year, "mois": date.month, "jour_mois": date.day,
                  "temps_longueur_mois": _longueur_mois(date.year, date.month), "temps_bissextile_rang": date.year % 4}
        if len(temps["semaine"]) == 7:
            champs["jour_semaine_rang"] = date.weekday()
            champs["jour_semaine"] = temps["semaine"][date.weekday()]
        return champs

    def changer_epoque(self, etat: dict, nom: str) -> dict:
        """Voyage dans le temps : la date courante est rangée dans l'époque quittée, celle de
        l'époque rejointe est reprise (label temps_epoque_<nom>)."""
        temps = self.temps
        etat = dict(etat)
        courante = etat["epoque"]
        for champ in CHAMPS_EPOQUE:
            etat[f"epoque_{courante}_{champ}"] = etat[champ]
        for champ in CHAMPS_EPOQUE:
            etat[champ] = etat[f"epoque_{nom}_{champ}"]
        etat["epoque"] = nom
        etat["moment"] = temps["creneaux"][etat["creneau"]]
        if temps["semaine"]:
            etat["jour_semaine"] = temps["semaine"][etat["jour_semaine_rang"]]
        for nom_ev, (mois, jour) in temps["evenements"].items():
            etat[f"evenement_{nom_ev}"] = (etat["mois"], etat["jour_mois"]) == (mois, jour)
        return etat

    def decors_par_creneau(self, nom) -> dict | None:
        """{créneau: image} d'un lieu dont « decors » est un dictionnaire, ou None."""
        decors = _dict(self.lieux.get(nom)).get("decors")
        return decors if isinstance(decors, dict) and decors and self.temps is not None else None

    @property
    def renommages(self) -> dict:
        """Renommages depuis les versions publiées (bible, « renommages ») : {"variables": [(ancien,
        nouveau)], "scenes": [(ancien label, nouveau label)]}, dans l'ordre de déclaration."""
        bloc = _dict(self.bible.get("renommages"))
        variables = [(str(a), str(n)) for a, n in _dict(bloc.get("variables")).items()]
        scenes = [(str(a).lower(), str(n).lower()) for a, n in _dict(bloc.get("scenes")).items()]
        return {"variables": variables, "scenes": scenes}

    def personnages_avec_jauges(self) -> list:
        """Personnages qui ont au moins une jauge, une compétence ou une relation (déclarée sur
        eux ou sur l'autre personnage), dans l'ordre de la bible."""
        cites = set()
        for variable in self.variables_personnages.values():
            cites |= {variable["personnage"], variable["avec"]}
        return [pid for pid in self.personnages if pid in cites]

    def nom_lieu(self, lid) -> str:
        """Nom affiché d'un lieu (« nom » de la bible, sinon l'identifiant mis en forme)."""
        return str(_dict(self.lieux.get(lid)).get("nom") or str(lid).replace("_", " ").capitalize())

    def titre_carte(self, cid) -> str:
        return str(_dict(self.cartes.get(cid)).get("titre") or str(cid).replace("_", " ").capitalize())

    def affichage_carte(self, cid) -> str:
        affichage = _dict(self.cartes.get(cid)).get("affichage")
        return str(affichage) if affichage in AFFICHAGES_CARTE else "carte"

    def parents_cartes(self) -> dict:
        """{carte : carte parente} : « parent » déclaré, sinon la seule carte qui l'ouvre.
        Le bouton de sortie d'une carte ramène à sa parente."""
        ouvertes_par: dict = {}
        for cid, carte in self.cartes.items():
            for entree in _liste(_dict(carte).get("lieux")):
                if isinstance(entree, dict) and entree.get("carte") in self.cartes and entree["carte"] != cid:
                    ouvertes_par.setdefault(entree["carte"], [])
                    if cid not in ouvertes_par[entree["carte"]]:
                        ouvertes_par[entree["carte"]].append(cid)
        parents = {}
        for cid, carte in self.cartes.items():
            explicite = _dict(carte).get("parent")
            if explicite in self.cartes and explicite != cid:
                parents[cid] = explicite
            elif len(ouvertes_par.get(cid, [])) == 1:
                parents[cid] = ouvertes_par[cid][0]
            else:
                parents[cid] = ""
        return parents

    def raccourcis(self) -> list:
        """Lieux proposés depuis toutes les cartes (« raccourci: true ») : [(carte d'origine, entrée)]."""
        return [(cid, entree) for cid, carte in self.cartes.items() for entree in _liste(_dict(carte).get("lieux"))
                if isinstance(entree, dict) and entree.get("raccourci") is True]

    def ordre(self) -> list:
        return sorted(self.scenes)

    def ou(self, sid) -> str:
        return self.fichiers.get(sid, sid)


def charger(racine: Path, rapport: Rapport) -> Projet:
    contenu = racine / "contenu"
    bible = _lire_yaml(contenu / "bible.yaml", racine, rapport)
    if not isinstance(bible, dict):
        rapport.erreur("contenu/bible.yaml", "fichier absent, vide ou mal formé")
        bible = {}
    projet = Projet(racine, bible)
    for chemin in sorted((contenu / "scenes").rglob("*.yaml")):
        ou = chemin.relative_to(racine).as_posix()
        fiche = _lire_yaml(chemin, racine, rapport)
        if fiche is None:
            continue
        if not isinstance(fiche, dict):
            rapport.erreur(ou, "une fiche de scène (champs id, titre, contenu…) est attendue")
            continue
        sid = fiche.get("id")
        if not isinstance(sid, str) or not ID_SCENE.match(sid):
            rapport.erreur(ou, "« id » manquant ou invalide (majuscules, chiffres et _, par exemple CH02_SC08)")
            continue
        if sid in projet.scenes:
            rapport.erreur(ou, f"id {sid} déjà utilisé par {projet.fichiers[sid]}")
            continue
        projet.scenes[sid] = fiche
        projet.fichiers[sid] = ou
    for code in projet.langues_cibles:
        donnees = _lire_yaml(racine / DOSSIER_TRADUCTIONS / f"{code}.yaml", racine, rapport)
        if donnees is not None:
            projet.traductions[code] = donnees
    return projet


def _lire_yaml(chemin: Path, racine: Path, rapport: Rapport):
    if not chemin.exists():
        return None
    try:
        with open(chemin, encoding="utf-8") as fichier:
            return yaml.safe_load(fichier)
    except yaml.YAMLError as exc:
        rapport.erreur(chemin.relative_to(racine).as_posix(),
                       f"YAML invalide ({exc}). Astuce : mettez les textes entre guillemets, surtout s'ils contiennent « : »")
        return None


# --- Vérification statique -------------------------------------------------------------

def verifier(projet: Projet, rapport: Rapport, limite: int = 20000):
    """Contrôles de structure puis exploration des routes. Renvoie l'exploration,
    ou None si la structure contient des erreurs."""
    _verifier_bible(projet, rapport)
    for sid in projet.ordre():
        _verifier_fiche(projet, sid, rapport)
    _verifier_conflits(projet, rapport)
    if not rapport.erreurs:
        _verifier_traductions(projet, rapport)
    if rapport.erreurs:
        return None
    return Explorateur(projet, rapport, limite).explorer()


def _verifier_bible(projet: Projet, rapport: Rapport):
    ou = "contenu/bible.yaml"
    bible = projet.bible
    if bible.get("debut") not in projet.scenes:
        rapport.erreur(ou, f"« debut » doit désigner une scène existante (actuellement : {bible.get('debut')!r})")
    if not projet.personnages:
        rapport.erreur(ou, "« personnages » : au moins un personnage attendu")
    age_minimum = bible.get("age_minimum", AGE_MINIMUM)
    if isinstance(age_minimum, bool) or not isinstance(age_minimum, int):
        rapport.erreur(ou, "« age_minimum » doit être un nombre entier")
        age_minimum = AGE_MINIMUM
    relations_vues: set = set()
    for pid, fiche in projet.personnages.items():
        ici = f"{ou}, personnage « {pid} »"
        if not isinstance(pid, str) or not IDENT.match(pid) or pid in MOTS_RESERVES:
            rapport.erreur(ici, "identifiant invalide ou réservé (minuscules, chiffres et _)")
        if not isinstance(fiche, dict):
            rapport.erreur(ici, "fiche attendue (nom, age, couleur…)")
            continue
        if not isinstance(fiche.get("nom"), str) or not fiche["nom"].strip():
            rapport.erreur(ici, "« nom » manquant")
        age = fiche.get("age")
        if age is None:
            pass
        elif isinstance(age, bool) or not isinstance(age, int):
            rapport.erreur(ici, "« age » attendu en années (nombre entier)")
        elif age < age_minimum:
            rapport.erreur(ici, f"âge {age} : la bible fixe l'âge minimum à {age_minimum} (« age_minimum »)")
        couleur = fiche.get("couleur")
        if couleur is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(couleur)):
            rapport.erreur(ici, "« couleur » attendue au format #rrggbb")
        if "traits" in fiche and not isinstance(fiche["traits"], list):
            rapport.erreur(ici, "« traits » : liste de textes attendue")
        for champ, genre in GENRES_JAUGES:
            if champ not in fiche:
                continue
            if not isinstance(fiche[champ], dict) or not fiche[champ]:
                rapport.erreur(ici, f"« {champ} » : dictionnaire nom: {{ defaut, min, max, paliers… }} attendu")
                continue
            for cle, jauge in fiche[champ].items():
                la = f"{ici}, {genre} « {cle} »"
                if genre == "relation":
                    if cle not in projet.personnages or cle == pid:
                        rapport.erreur(la, "la clé d'une relation est l'identifiant d'un autre personnage de la bible")
                        continue
                    paire = frozenset((pid, cle))
                    if paire in relations_vues:
                        rapport.erreur(la, f"relation déjà déclarée sur « {cle} » (une relation vaut pour les deux personnages)")
                        continue
                    relations_vues.add(paire)
                elif cle in projet.personnages:
                    rapport.erreur(la, "nom réservé aux relations (identifiant d'un personnage) : déclarez-la dans « relations »")
                    continue
                _verifier_jauge(rapport, la, cle, jauge, projet)
    verif = _Verif(projet, rapport, ou, [])
    for pid, fiche in projet.personnages.items():
        if not isinstance(fiche, dict) or not isinstance(pid, str):
            continue
        ici = f"{ou}, personnage « {pid} »"
        if "avatar" in fiche:
            verif.image(fiche["avatar"], f"personnage « {pid} », avatar")
        presence = fiche.get("presence")
        if presence is None:
            continue
        if not isinstance(presence, list) or not presence:
            rapport.erreur(ici, "« presence » : liste de règles { lieu, si } attendue (la première règle vraie donne le lieu)")
            continue
        for rang, regle in enumerate(presence, 1):
            la = f"{ici}, presence[{rang}]"
            if not isinstance(regle, dict) or "lieu" not in regle or set(regle) - CHAMPS_PRESENCE:
                rapport.erreur(la, "attendu : - lieu: identifiant du lieu, et si: condition (facultatif)")
                continue
            if regle["lieu"] not in projet.lieux:
                rapport.erreur(la, f"lieu inconnu « {regle['lieu']} » (à déclarer dans « lieux » de la bible)")
            if "si" in regle:
                verif.expression(regle["si"], la)
    for nom, variable in projet.variables.items():
        ici = f"{ou}, variable « {nom} »"
        if not isinstance(nom, str) or not IDENT.match(nom) or nom in MOTS_RESERVES or nom in projet.personnages:
            rapport.erreur(ici, "nom invalide, réservé ou déjà pris par un personnage")
        elif nom in projet.variables_personnages:
            jauge = projet.variables_personnages[nom]
            rapport.erreur(ici, f"réservée à la {jauge['genre']} « {jauge['cle']} » de « {jauge['personnage']} » : "
                                "choisissez un autre nom")
        elif nom in projet.variables_presence:
            rapport.erreur(ici, f"réservée à la présence de « {projet.variables_presence[nom]['personnage']} » "
                                "(calculée à chaque carte) : choisissez un autre nom")
        elif nom in projet.variables_temps:
            rapport.erreur(ici, "réservée au temps (bible, « temps ») : choisissez un autre nom")
        if not isinstance(variable, dict) or "defaut" not in variable:
            rapport.erreur(ici, "« defaut » obligatoire")
            continue
        defaut = variable["defaut"]
        if not isinstance(defaut, (bool, int, float, str)):
            rapport.erreur(ici, "« defaut » doit être un nombre, un booléen ou un texte")
        for borne in ("min", "max"):
            if borne not in variable:
                continue
            if not _est_nombre(defaut):
                rapport.erreur(ici, f"« {borne} » réservé aux variables numériques")
            elif not _est_nombre(variable[borne]):
                rapport.erreur(ici, f"« {borne} » doit être un nombre")
    for lid, lieu in projet.lieux.items():
        ici = f"{ou}, lieu « {lid} »"
        if not isinstance(lid, str) or not IDENT.match(lid):
            rapport.erreur(ici, "identifiant invalide (minuscules, chiffres et _)")
        if not isinstance(lieu, dict):
            rapport.erreur(ici, "fiche attendue (nom, description, decors, icone)")
            continue
        if "nom" in lieu and (not isinstance(lieu["nom"], str) or not lieu["nom"].strip()):
            rapport.erreur(ici, "« nom » : texte attendu (nom affiché sur les cartes)")
        if "icone" in lieu:
            verif.image(lieu["icone"], f"lieu « {lid} », icone")
        decors = lieu.get("decors")
        if isinstance(decors, dict):
            temps = projet.temps
            if temps is None:
                rapport.erreur(ici, "« decors » par créneau demande un bloc « temps » dans la bible")
            for creneau, image in decors.items():
                if temps is not None and creneau not in temps["creneaux"] and creneau not in temps["epoques"]:
                    rapport.erreur(ici, f"decors : « {creneau} » n'est ni un créneau ni une époque de la bible "
                                        f"({', '.join(temps['creneaux'] + list(temps['epoques']))})")
                verif.image(image, f"lieu « {lid} », decors[{creneau}]")
        elif decors is not None and not isinstance(decors, list):
            rapport.erreur(ici, "« decors » : liste d'images, ou dictionnaire créneau: image")
    _verifier_cartes(projet, rapport, verif)
    if not isinstance(bible.get("regles_editoriales", []), list):
        rapport.erreur(ou, "« regles_editoriales » : liste attendue")
    _verifier_renommages(projet, rapport, ou)
    _verifier_temps(projet, rapport, ou)
    _verifier_langues(bible.get("langues"), rapport)


def _verifier_temps(projet: Projet, rapport: Rapport, ou: str):
    bloc = projet.bible.get("temps")
    if bloc is None:
        return
    ici = f"{ou}, temps"
    if not isinstance(bloc, dict) or set(bloc) - CHAMPS_TEMPS:
        rapport.erreur(ici, "attendu : creneaux (liste), jours (booléen), semaine (liste), debut (creneau, jour, jour_semaine)")
        return
    for champ, minimum in (("creneaux", 2), ("semaine", 2)):
        noms = bloc.get(champ)
        if noms is None and champ == "semaine":
            continue
        if not isinstance(noms, list) or len(noms) < minimum or len(set(map(str, noms))) != len(noms) \
                or not all(isinstance(nom, str) and IDENT.match(nom) for nom in noms):
            rapport.erreur(f"{ici}, {champ}", f"liste d'au moins {minimum} noms distincts attendue (minuscules, chiffres et _)")
    if "jours" in bloc and not isinstance(bloc["jours"], bool):
        rapport.erreur(f"{ici}, jours", "true ou false attendu")
    if "date" in bloc and _date_de(bloc["date"]) is None:
        rapport.erreur(f"{ici}, date", "date de départ attendue au format AAAA-MM-JJ")
    if "date" in bloc and isinstance(bloc.get("semaine"), list) and len(bloc["semaine"]) != 7:
        rapport.erreur(f"{ici}, semaine", "avec une date, la semaine compte 7 noms (lundi en premier)")
    epoques = bloc.get("epoques")
    if epoques is not None:
        if "date" in bloc:
            rapport.erreur(f"{ici}, epoques", "avec des époques, la date de départ est celle de l'époque de « debut » : retirez « date »")
        if not isinstance(epoques, dict) or len(epoques) < 2:
            rapport.erreur(f"{ici}, epoques", "dictionnaire nom: date (AAAA-MM-JJ) d'au moins deux époques attendu")
        else:
            for nom, quand in epoques.items():
                if not isinstance(nom, str) or not IDENT.match(nom) or nom in MOTS_RESERVES:
                    rapport.erreur(f"{ici}, epoques, « {nom} »", "nom invalide (minuscules, chiffres et _)")
                if _date_de(quand) is None:
                    rapport.erreur(f"{ici}, epoques, « {nom} »", "date attendue au format AAAA-MM-JJ")
            debut = _dict(bloc.get("debut"))
            if "epoque" in debut and debut["epoque"] not in epoques:
                rapport.erreur(f"{ici}, debut", f"époque inconnue « {debut['epoque']} »")
    evenements = bloc.get("evenements")
    if evenements is not None:
        if "date" not in bloc and not isinstance(epoques, dict):
            rapport.erreur(f"{ici}, evenements", "les événements demandent une « date » de départ (ou des époques)")
        if not isinstance(evenements, dict):
            rapport.erreur(f"{ici}, evenements", "dictionnaire nom: { mois, jour } attendu")
            evenements = {}
        for nom, quand in evenements.items():
            la = f"{ici}, evenements, « {nom} »"
            if not isinstance(nom, str) or not IDENT.match(nom):
                rapport.erreur(la, "nom invalide (minuscules, chiffres et _)")
            if not isinstance(quand, dict) or set(quand) - {"mois", "jour"} or not _est_nombre(quand.get("mois")) or not _est_nombre(quand.get("jour")):
                rapport.erreur(la, "attendu : { mois: 1-12, jour: 1-31 }")
            elif not 1 <= quand["mois"] <= 12 or not 1 <= quand["jour"] <= _longueur_mois(2024, int(quand["mois"])):
                rapport.erreur(la, f"date impossible : mois {quand['mois']}, jour {quand['jour']}")
    debut = bloc.get("debut")
    if debut is not None:
        if not isinstance(debut, dict) or set(debut) - {"creneau", "jour", "jour_semaine", "epoque"}:
            rapport.erreur(f"{ici}, debut", "attendu : creneau (nom), jour (nombre), jour_semaine (nom), epoque (nom)")
        else:
            if "creneau" in debut and debut["creneau"] not in _liste(bloc.get("creneaux")):
                rapport.erreur(f"{ici}, debut", f"créneau inconnu « {debut['creneau']} »")
            if "jour_semaine" in debut and debut["jour_semaine"] not in _liste(bloc.get("semaine")):
                rapport.erreur(f"{ici}, debut", f"jour de la semaine inconnu « {debut['jour_semaine']} »")
            if "jour" in debut and (isinstance(debut["jour"], bool) or not isinstance(debut["jour"], int) or debut["jour"] < 1):
                rapport.erreur(f"{ici}, debut", "« jour » : nombre entier à partir de 1")
    for nom in list(projet.personnages) + list(projet.variables_personnages) + list(projet.variables_presence) + list(projet.variables):
        if nom in VARIABLES_TEMPS or str(nom).startswith(PREFIXES_TEMPS):
            rapport.erreur(ici, f"le nom « {nom} » est réservé au temps (creneau, moment, jour…, temps_*, evenement_*) : renommez-le")
    for label in LABELS_TEMPS + tuple(f"temps_epoque_{nom}" for nom in _dict(bloc.get("epoques"))):
        if label.upper() in projet.scenes:
            rapport.erreur(ici, f"l'identifiant de scène {label.upper()} est réservé au temps")


def _verifier_renommages(projet: Projet, rapport: Rapport, ou: str):
    """« renommages » : variables et scènes renommées depuis une version publiée ; les
    anciennes sauvegardes reprennent l'ancienne valeur ou l'ancien label sous le nouveau nom."""
    bloc = projet.bible.get("renommages")
    if bloc is None:
        return
    ici = f"{ou}, renommages"
    if not isinstance(bloc, dict) or set(bloc) - {"variables", "scenes"}:
        rapport.erreur(ici, "attendu : variables: {ancien: nouveau} et scenes: {ANCIEN: NOUVEAU}")
        return
    for champ, existants, texte in (("variables", set(projet.variables_toutes), "variable"),
                                    ("scenes", set(projet.scenes), "scène")):
        entrees = bloc.get(champ)
        if entrees is None:
            continue
        if not isinstance(entrees, dict):
            rapport.erreur(f"{ici}, {champ}", "dictionnaire ancien: nouveau attendu")
            continue
        nouveaux: dict = {}
        for ancien, nouveau in entrees.items():
            la = f"{ici}, {champ}, « {ancien} »"
            if not isinstance(ancien, str) or not isinstance(nouveau, str) or not nouveau:
                rapport.erreur(la, "ancien et nouveau noms attendus (textes)")
                continue
            if ancien in existants:
                rapport.erreur(la, f"cette {texte} existe encore : un renommage ne concerne qu'un nom disparu")
            if nouveau not in existants and nouveau not in entrees:
                rapport.erreur(la, f"{texte} inconnue « {nouveau} » : le nouveau nom doit exister dans la bible")
            elif champ == "variables" and nouveau in projet.variables_toutes and nouveau not in projet.variables_modifiables:
                rapport.erreur(la, f"« {nouveau} » est calculée (temps, présence) : elle ne reprend pas d'ancienne valeur")
            if nouveau in nouveaux:
                rapport.avertir(la, f"« {nouveaux[nouveau]} » est aussi renommée en « {nouveau} » : la dernière l'emporte")
            nouveaux[nouveau] = ancien
            if ancien == nouveau:
                rapport.erreur(la, "ancien et nouveau noms identiques")


def _jauge(valeur) -> dict:
    """Fiche d'une jauge : un nombre seul vaut { defaut: nombre }."""
    if _est_nombre(valeur):
        return {"defaut": valeur}
    return valeur if isinstance(valeur, dict) else {}


def _verifier_jauge(rapport: Rapport, ici: str, cle, jauge, projet: Projet):
    if not isinstance(cle, str) or not IDENT.match(cle) or cle in MOTS_RESERVES:
        rapport.erreur(ici, "nom invalide ou réservé (minuscules, chiffres et _)")
        return
    if not _est_nombre(jauge) and not isinstance(jauge, dict):
        rapport.erreur(ici, "nombre (valeur de départ) ou fiche { defaut, min, max, nom, description, paliers } attendu")
        return
    jauge = _jauge(jauge)
    if set(jauge) - CHAMPS_JAUGE:
        rapport.erreur(ici, f"champs inconnus : {', '.join(sorted(set(jauge) - CHAMPS_JAUGE))}")
    if not _est_nombre(jauge.get("defaut")):
        rapport.erreur(ici, "« defaut » obligatoire : un nombre (jauges et compétences sont numériques)")
        return
    for borne in ("min", "max"):
        if borne in jauge and not _est_nombre(jauge[borne]):
            rapport.erreur(ici, f"« {borne} » doit être un nombre")
    if _est_nombre(jauge.get("min")) and _est_nombre(jauge.get("max")) and jauge["min"] > jauge["max"]:
        rapport.erreur(ici, "« min » supérieur à « max »")
    if "nom" in jauge and (not isinstance(jauge["nom"], str) or not jauge["nom"].strip()):
        rapport.erreur(ici, "« nom » : texte attendu (nom affiché dans le jeu)")
    if "paliers" in jauge:
        paliers = jauge["paliers"]
        if not isinstance(paliers, dict) or not paliers:
            rapport.erreur(ici, "« paliers » : dictionnaire seuil: nom attendu (le plus haut seuil atteint donne le palier)")
        else:
            for seuil, nom in paliers.items():
                if not _est_nombre(seuil):
                    rapport.erreur(ici, f"palier « {seuil} » : le seuil doit être un nombre")
                elif _est_nombre(jauge.get("min")) and seuil < jauge["min"] or _est_nombre(jauge.get("max")) and seuil > jauge["max"]:
                    rapport.erreur(ici, f"palier {seuil} hors des bornes min / max")
                if not isinstance(nom, str) or not nom.strip():
                    rapport.erreur(ici, f"palier « {seuil} » : nom attendu (texte)")
            noms = [str(nom) for nom in paliers.values()]
            if len(set(noms)) != len(noms):
                rapport.erreur(ici, "deux paliers portent le même nom")


def _verifier_cartes(projet: Projet, rapport: Rapport, verif: _Verif):
    ou = "contenu/bible.yaml"
    brut = projet.bible.get("cartes")
    if brut is not None and not isinstance(brut, dict):
        rapport.erreur(ou, "« cartes » : dictionnaire identifiant → carte (titre, image, lieux) attendu")
        return
    ouvertes_par: dict = {}
    for cid, carte in projet.cartes.items():
        ici = f"{ou}, carte « {cid} »"
        if not isinstance(cid, str) or not IDENT.match(cid):
            rapport.erreur(ici, "identifiant invalide (minuscules, chiffres et _)")
        if not isinstance(carte, dict):
            rapport.erreur(ici, "carte attendue (titre, image, parent, lieux)")
            continue
        for cle in set(carte) - CHAMPS_CARTE:
            rapport.erreur(ici, f"champ inconnu « {cle} » (champs possibles : {', '.join(sorted(CHAMPS_CARTE))})")
        if "titre" in carte and (not isinstance(carte["titre"], str) or not carte["titre"].strip()):
            rapport.erreur(ici, "« titre » : texte attendu")
        if "affichage" in carte and carte["affichage"] not in AFFICHAGES_CARTE:
            rapport.erreur(ici, f"« affichage » : {' ou '.join(AFFICHAGES_CARTE)} attendu (carte : image avec lieux placés dessus ; "
                                "pieces : barre des pièces en bas de l'écran)")
        positions = projet.affichage_carte(cid) == "carte"
        if "image" in carte:
            verif.image(carte["image"], f"carte « {cid} », image")
        parent = carte.get("parent")
        if parent is not None and (parent not in projet.cartes or parent == cid):
            rapport.erreur(ici, f"« parent » doit désigner une autre carte (actuellement : {parent!r})")
        lieux = carte.get("lieux")
        if not isinstance(lieux, list) or not lieux:
            rapport.erreur(ici, "« lieux » : liste de { lieu, x, y, scene ou carte } attendue")
            continue
        for rang, entree in enumerate(lieux, 1):
            la = f"{ici}, lieux[{rang}]"
            if not isinstance(entree, dict):
                rapport.erreur(la, "attendu : lieu, x, y, puis scene (fiche jouée) ou carte (sous-carte ouverte)")
                continue
            for cle in set(entree) - CHAMPS_LIEU_CARTE:
                rapport.erreur(la, f"champ inconnu « {cle} » (champs possibles : {', '.join(sorted(CHAMPS_LIEU_CARTE))})")
            if entree.get("lieu") not in projet.lieux:
                rapport.erreur(la, f"lieu inconnu « {entree.get('lieu')} » (à déclarer dans « lieux » de la bible)")
            for axe in ("x", "y"):
                valeur = entree.get(axe)
                if positions and (not _est_nombre(valeur) or not 0 <= valeur <= 100):
                    rapport.erreur(la, f"« {axe} » : position en pourcentage de l'image, de 0 à 100")
                elif not positions and valeur is not None:
                    rapport.avertir(la, f"« {axe} » ignoré : les pièces s'alignent dans une barre (affichage: pieces)")
            destinations = [cle for cle in ("scene", "carte") if cle in entree]
            if len(destinations) != 1:
                rapport.erreur(la, "une seule destination attendue : scene (fiche jouée) ou carte (sous-carte ouverte)")
            elif "scene" in entree and entree["scene"] not in projet.scenes:
                rapport.erreur(la, f"scène inconnue « {entree['scene']} »")
            elif "carte" in entree:
                if entree["carte"] not in projet.cartes or entree["carte"] == cid:
                    rapport.erreur(la, f"sous-carte inconnue « {entree['carte']} » (ou identique à la carte)")
                else:
                    ouvertes_par.setdefault(entree["carte"], set()).add(cid)
            if "si" in entree:
                verif.expression(entree["si"], la)
            if "temps" in entree:
                cout = entree["temps"]
                if projet.temps is None:
                    rapport.erreur(la, "« temps » (coût du déplacement) demande un bloc « temps » dans la bible")
                elif isinstance(cout, dict):
                    if set(cout) != {"jours"} or isinstance(cout["jours"], bool) or not isinstance(cout["jours"], int) or cout["jours"] < 1:
                        rapport.erreur(la, "« temps » : nombre de créneaux (1, 2…) ou { jours: n }")
                    elif not projet.temps["jours"]:
                        rapport.erreur(la, "un coût en jours demande « jours: true » ou une date dans la bible")
                elif isinstance(cout, bool) or not isinstance(cout, int) or cout < 1:
                    rapport.erreur(la, "« temps » : nombre de créneaux (1, 2…) ou { jours: n }")
            if "raccourci" in entree and not isinstance(entree["raccourci"], bool):
                rapport.erreur(la, "« raccourci » : true ou false (lieu proposé depuis toutes les cartes)")
        noms = [projet.nom_lieu(entree.get("lieu")) for entree in lieux if isinstance(entree, dict)]
        lieux_ids = [entree.get("lieu") for entree in lieux if isinstance(entree, dict)]
        for nom in sorted({n for n in noms if len({lieux_ids[i] for i, m in enumerate(noms) if m == n}) > 1}):
            rapport.erreur(ici, f"deux lieux différents s'affichent « {nom} » sur cette carte")
        for court in noms:
            for long in noms:
                if court != long and court in long:
                    rapport.avertir(ici, f"« {court} » est contenu dans « {long} » : les tests Ren'Py risquent de cliquer le mauvais lieu")
    raccourcis = projet.raccourcis()
    for cid, carte in projet.cartes.items():
        if not isinstance(carte, dict):
            continue
        lieux_ici = {_dict(e).get("lieu") for e in _liste(carte.get("lieux"))}
        noms_ici = {projet.nom_lieu(lid) for lid in lieux_ici}
        for origine, entree in raccourcis:
            if entree.get("lieu") not in lieux_ici and projet.nom_lieu(entree.get("lieu")) in noms_ici:
                rapport.erreur(f"{ou}, carte « {cid} »", f"le raccourci « {projet.nom_lieu(entree.get('lieu'))} » porte le nom d'un lieu de cette carte")
    for cid, cartes in ouvertes_par.items():
        if len(cartes) > 1 and _dict(projet.cartes.get(cid)).get("parent") is None:
            rapport.erreur(f"{ou}, carte « {cid} »",
                           f"ouverte depuis plusieurs cartes ({', '.join(sorted(cartes))}) : précisez « parent »")


def _verifier_langues(langues, rapport: Rapport):
    ou = "contenu/bible.yaml, « langues »"
    if langues is None:
        return
    codes = ", ".join(LANGUES)
    if not isinstance(langues, dict) or set(langues) - {"source", "traductions"}:
        rapport.erreur(ou, "attendu : source (langue des fiches) et traductions (liste de codes), "
                           "par exemple {source: fr, traductions: [en]}")
        return
    source = langues.get("source", LANGUE_SOURCE)
    if source not in LANGUES:
        rapport.erreur(ou, f"langue source inconnue {source!r} (codes possibles : {codes})")
    traductions = langues.get("traductions", [])
    if not isinstance(traductions, list):
        rapport.erreur(ou, "« traductions » : liste de codes attendue, par exemple [en]")
        return
    for code in traductions:
        if code not in LANGUES:
            rapport.erreur(ou, f"code de langue inconnu {code!r} (codes possibles : {codes})")
        elif code == source:
            rapport.erreur(ou, f"« {code} » est déjà la langue source")
        elif traductions.count(code) > 1:
            rapport.erreur(ou, f"« {code} » déclarée plusieurs fois")


def _verifier_moment(projet: Projet, fiche: dict, rapport: Rapport, ou: str):
    temps = projet.temps
    if temps is not None and isinstance(fiche.get("moment"), str) and fiche["moment"] not in temps["creneaux"]:
        rapport.avertir(ou, f"« moment: {fiche['moment']} » n'est pas un créneau de la bible ({', '.join(temps['creneaux'])})")


def _verifier_fiche(projet: Projet, sid: str, rapport: Rapport):
    fiche = projet.scenes[sid]
    verif = _Verif(projet, rapport, projet.ou(sid), _liste(fiche.get("personnages")))
    for cle in fiche:
        if cle not in CHAMPS_FICHE:
            verif.erreur(f"champ inconnu « {cle} » (champs possibles : {', '.join(sorted(CHAMPS_FICHE))})")
    if not isinstance(fiche.get("titre"), str):
        verif.avertir("« titre » manquant")
    lieu = fiche.get("lieu")
    if lieu is not None and lieu not in projet.lieux:
        verif.erreur(f"lieu inconnu « {lieu} » (à déclarer dans « lieux » de la bible)")
    _verifier_moment(projet, fiche, rapport, projet.ou(sid))
    if not isinstance(fiche.get("personnages", []), list):
        verif.erreur("« personnages » : liste attendue")
    for pid in verif.presents:
        if pid not in projet.personnages:
            verif.erreur(f"personnage inconnu « {pid} »")
    if fiche.get("conditions") is not None and not isinstance(fiche["conditions"], (list, dict, str, bool)):
        verif.erreur("« conditions » : liste d'expressions attendue")
    for condition in conditions_de(fiche):
        verif.expression(condition, "conditions")
    verif.contenu(fiche.get("contenu"), "contenu")
    fins = [cle for cle in FINS if fiche.get(cle) not in (None, False)]
    if len(fins) != 1:
        verif.erreur(f"la scène doit se terminer par un seul de : choix, suite, fin, retour, carte (trouvé : {', '.join(fins) or 'aucun'})")
    if fiche.get("suite") is not None:
        verif.destination(fiche["suite"], "suite")
    if fiche.get("carte") is not None and fiche["carte"] not in projet.cartes:
        verif.erreur(f"carte inconnue « {fiche['carte']} » (à déclarer dans « cartes » de la bible)", "carte")
    if fiche.get("choix") is not None:
        verif.choix(fiche)
    for cle in ("fin", "retour"):
        if fiche.get(cle) not in (None, True, False):
            verif.erreur(f"« {cle} » : true attendu")
    if fiche.get("galerie") is not None:
        verif.galerie(fiche["galerie"])


def _verifier_conflits(projet: Projet, rapport: Rapport):
    """Un fichier .rpy écrit à la main ne doit pas redéfinir ce que produisent les fiches."""
    story = projet.racine / "game" / "story"
    if not story.is_dir():
        return
    labels_epoques = {f"temps_epoque_{nom}" for nom in (projet.temps or {}).get("epoques", {})}
    produits = {"start", *LABELS_TEMPS, *labels_epoques} | {sid.lower() for sid in projet.scenes} | set(projet.personnages) | set(projet.variables_toutes)
    for chemin in sorted(story.rglob("*.rpy")):
        texte = chemin.read_text(encoding="utf-8")
        if MARQUEUR in texte[:400]:
            continue
        for trouve in re.finditer(r"^(?:label|define|default)\s+([A-Za-z_]\w*)", texte, re.M):
            if trouve.group(1) in produits:
                rapport.erreur(chemin.relative_to(projet.racine).as_posix(),
                               f"écrit à la main, définit aussi « {trouve.group(1)} », produit par les fiches : "
                               "reportez son contenu dans contenu/ puis supprimez-le")


class _Verif:
    """Contrôles d'une fiche ; les messages sont préfixés par le chemin dans la fiche."""

    def __init__(self, projet: Projet, rapport: Rapport, ou: str, presents: list):
        self.projet = projet
        self.rapport = rapport
        self.ou = ou
        self.presents = [p for p in presents if isinstance(p, str)]

    def erreur(self, message, chemin=""):
        self.rapport.erreur(self.ou, f"{chemin} : {message}" if chemin else message)

    def avertir(self, message, chemin=""):
        self.rapport.avertir(self.ou, f"{chemin} : {message}" if chemin else message)

    def contenu(self, elements, chemin):
        if elements is None:
            return
        if not isinstance(elements, list):
            self.erreur("liste d'éléments attendue", chemin)
            return
        for index, element in enumerate(elements, 1):
            self.element(element, f"{chemin}[{index}]")

    def element(self, element, chemin, seulement_repliques=False):
        cle = cle_element(element, self.projet)
        if cle is None:
            decrit = sorted(map(str, element)) if isinstance(element, dict) else element
            self.erreur(f"élément non reconnu {decrit!r} : attendu narration, un personnage de la bible, "
                        "decor, montrer, cacher, video, pause, musique, son, effets, si, appel ou temps", chemin)
            return
        replique = cle == "narration" or cle in self.projet.personnages
        if seulement_repliques and not replique:
            self.erreur("seule une réplique (narration ou personnage) est possible ici", chemin)
            return
        inattendues = set(element) - {cle} - MODIFICATEURS.get(cle, set())
        if inattendues:
            self.erreur(f"clé(s) inattendue(s) avec « {cle} » : {', '.join(sorted(map(str, inattendues)))}", chemin)
        valeur = element[cle]
        if replique:
            self.texte(valeur, chemin)
            if cle in self.projet.personnages and cle not in self.presents:
                self.avertir(f"« {cle} » parle sans figurer dans « personnages »", chemin)
        elif cle == "decor":
            if valeur is not None and self.projet.decors_par_creneau(valeur) is None:
                self.image(valeur, chemin)
            self.transition(element, chemin)
        elif cle == "temps":
            temps = self.projet.temps
            if temps is None:
                self.erreur("« temps » demande un bloc « temps » dans la bible (creneaux, jours…)", chemin)
            elif isinstance(valeur, str):
                if valeur not in temps["creneaux"]:
                    self.erreur(f"« temps » : créneau inconnu « {valeur} » ({', '.join(temps['creneaux'])})", chemin)
            elif isinstance(valeur, dict):
                self.saut_de_temps(valeur, chemin)
            elif isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 1:
                self.erreur("« temps » attend un nombre de créneaux (1, 2…), le nom du prochain créneau, "
                            "ou un saut { jours: n }, { mois: n }, { date: AAAA-MM-JJ } (+ creneau: nom)", chemin)
        elif cle == "montrer":
            self.image(valeur, chemin)
            position = element.get("position")
            if position is not None and position not in POSITIONS:
                self.erreur(f"position « {position} » non supportée ({', '.join(POSITIONS)})", chemin)
            self.transition(element, chemin)
        elif cle == "cacher":
            if not isinstance(valeur, str) or not re.fullmatch(r"[A-Za-z0-9_]+", valeur):
                self.erreur("« cacher » attend le tag de l'image (son premier mot, par exemple lena)", chemin)
            self.transition(element, chemin)
        elif cle == "video":
            if not isinstance(valeur, str) or not valeur.endswith(".webm"):
                self.erreur("« video » attend un chemin .webm relatif à game/ (par exemple videos/scene.webm)", chemin)
        elif cle == "pause":
            if valeur is not None and (not _est_nombre(valeur) or valeur <= 0):
                self.erreur("« pause » attend une durée en secondes, ou rien pour attendre un clic", chemin)
        elif cle in ("musique", "son"):
            if not isinstance(valeur, str) or not valeur:
                self.erreur(f"« {cle} » attend un fichier audio relatif à game/, ou stop", chemin)
        elif cle == "effets":
            self.effets(valeur, chemin)
        elif cle == "si":
            self.expression(valeur, chemin)
            self.contenu(element.get("alors"), f"{chemin}.alors")
            branches = element.get("sinon_si")
            if branches is not None and not isinstance(branches, list):
                self.erreur("« sinon_si » : liste de { si, alors } attendue", chemin)
            for index, branche in enumerate(_liste(branches), 1):
                ici = f"{chemin}.sinon_si[{index}]"
                if not isinstance(branche, dict) or "si" not in branche or set(branche) - {"si", "alors"}:
                    self.erreur("attendu : - si: condition / alors: [...]", ici)
                    continue
                self.expression(branche["si"], ici)
                self.contenu(branche.get("alors"), f"{ici}.alors")
            self.contenu(element.get("sinon"), f"{chemin}.sinon")
        elif cle == "appel":
            cible = self.projet.scenes.get(valeur)
            if cible is None:
                self.erreur(f"scène appelée inconnue « {valeur} »", chemin)
            elif not cible.get("retour") or cible.get("choix") is not None:
                self.erreur(f"« {valeur} » doit se terminer par « retour: true », sans choix, pour être appelée", chemin)

    def saut_de_temps(self, saut: dict, chemin):
        temps = self.projet.temps
        sortes = [cle for cle in ("jours", "mois", "date", "epoque") if cle in saut]
        if set(saut) - {"jours", "mois", "date", "epoque", "creneau"} or len(sortes) != 1:
            self.erreur("saut de temps : exactement un de jours, mois, date ou epoque, et creneau facultatif", chemin)
            return
        sorte = sortes[0]
        if sorte == "epoque" and saut["epoque"] not in temps["epoques"]:
            self.erreur(f"époque inconnue « {saut['epoque']} » (temps.epoques : {', '.join(temps['epoques']) or 'aucune'})", chemin)
        if sorte in ("jours", "mois"):
            if isinstance(saut[sorte], bool) or not isinstance(saut[sorte], int) or saut[sorte] < 1:
                self.erreur(f"« {sorte} » : nombre entier à partir de 1", chemin)
        if sorte in ("mois", "date") and temps["date"] is None:
            self.erreur(f"un saut « {sorte} » demande une « date » de départ dans la bible (temps.date)", chemin)
        if sorte == "date" and _date_de(saut["date"]) is None:
            self.erreur("« date » : AAAA-MM-JJ attendu", chemin)
        if sorte == "jours" and not temps["jours"]:
            self.erreur("un saut « jours » demande « jours: true » ou une date dans la bible", chemin)
        if "creneau" in saut and saut["creneau"] not in temps["creneaux"]:
            self.erreur(f"créneau inconnu « {saut['creneau']} » ({', '.join(temps['creneaux'])})", chemin)

    def texte(self, valeur, chemin):
        if isinstance(valeur, bool) or not isinstance(valeur, (str, int, float)) or not str(valeur).strip():
            self.erreur("texte attendu (mettez-le entre guillemets)", chemin)
            return
        for nom in INTERPOLATION.findall(str(valeur).replace("[[", "")):
            if nom not in self.projet.variables_toutes:
                self.erreur(f"[{nom}] : variable inconnue dans le texte", chemin)

    def expression(self, expr, chemin):
        texte = _expr_texte(expr)
        if not texte.strip():
            self.erreur("condition vide", chemin)
            return
        try:
            arbre = ast.parse(texte, mode="eval")
        except SyntaxError:
            self.erreur(f"expression invalide « {texte} »", chemin)
            return
        for noeud in ast.walk(arbre):
            if isinstance(noeud, (ast.Div, ast.FloorDiv, ast.Mod)):
                self.erreur(f"« {texte} » : division et modulo non supportés (résultats différents entre Python et Godot)", chemin)
                return
            if not isinstance(noeud, NOEUDS_AUTORISES):
                self.erreur(f"« {texte} » : construction non supportée par le sous-ensemble ({type(noeud).__name__})", chemin)
                return
            if isinstance(noeud, ast.Compare) and len(noeud.ops) > 1:
                self.erreur(f"« {texte} » : comparaisons enchaînées non supportées (écrivez a < b and b < c)", chemin)
                return
            if isinstance(noeud, ast.Call) and (not isinstance(noeud.func, ast.Name) or noeud.func.id not in FONCTIONS or noeud.keywords):
                self.erreur(f"« {texte} » : seules les fonctions {', '.join(FONCTIONS)} sont permises", chemin)
                return
            if isinstance(noeud, ast.Name) and noeud.id not in FONCTIONS and noeud.id not in self.projet.variables_toutes:
                self.erreur(f"variable inconnue « {noeud.id} » dans « {texte} » (à déclarer dans la bible)", chemin)
                return

    def effets(self, effets, chemin):
        if not isinstance(effets, dict) or not effets:
            self.erreur("« effets » : dictionnaire variable: valeur attendu", chemin)
            return
        for nom, valeur in effets.items():
            variable = self.projet.variables_modifiables.get(nom)
            if nom in self.projet.variables_temps:
                self.erreur(f"« {nom} » est une variable du temps : elle avance avec l'élément « temps », pas par effets", chemin)
                continue
            if nom in self.projet.variables_presence:
                self.erreur(f"« {nom} » est calculée à chaque carte par les règles « presence » de "
                            f"« {self.projet.variables_presence[nom]['personnage']} » : elle ne se modifie pas par effets", chemin)
                continue
            if not isinstance(variable, dict):
                self.erreur(f"variable inconnue « {nom} » (à déclarer dans la bible)", chemin)
                continue
            defaut = variable.get("defaut")
            if _est_nombre(defaut) and not _est_nombre(valeur):
                self.erreur(f"« {nom} » est numérique : un nombre est attendu (il s'ajoute à la valeur actuelle)", chemin)
            elif isinstance(defaut, bool) and not isinstance(valeur, bool):
                self.erreur(f"« {nom} » est un booléen : true ou false attendu", chemin)
            elif isinstance(defaut, str) and not isinstance(valeur, str):
                self.erreur(f"« {nom} » est un texte : un texte est attendu", chemin)

    def destination(self, sid, chemin):
        if sid not in self.projet.scenes:
            self.erreur(f"destination inconnue « {sid} »", chemin)

    def choix(self, fiche):
        brut = fiche["choix"]
        if not isinstance(brut, (list, dict)):
            self.erreur("« choix » : liste d'options, ou question + options", "choix")
            return
        if isinstance(brut, dict) and set(brut) - {"question", "options"}:
            self.erreur("clés possibles : question, options", "choix")
        question, options = options_de(fiche)
        if question is not None:
            self.element(question, "choix.question", seulement_repliques=True)
        if not options:
            self.erreur("au moins une option attendue", "choix")
            return
        for index, option in enumerate(options, 1):
            ici = f"choix[{index}]"
            if not isinstance(option, dict):
                self.erreur("option attendue (libelle, destination…)", ici)
                continue
            for cle in set(option) - CHAMPS_OPTION:
                self.erreur(f"champ inconnu « {cle} » (champs possibles : {', '.join(sorted(CHAMPS_OPTION))})", ici)
            if "libelle" in option:
                self.texte(option["libelle"], f"{ici}.libelle")
            else:
                self.erreur("« libelle » manquant", ici)
            if "si" in option:
                self.expression(option["si"], f"{ici}.si")
            if "effets" in option:
                self.effets(option["effets"], f"{ici}.effets")
            self.contenu(option.get("contenu"), f"{ici}.contenu")
            if "destination" in option:
                self.destination(option["destination"], f"{ici}.destination")
            else:
                self.erreur("« destination » manquante", ici)
        libelles = [str(option["libelle"]) for option in options if isinstance(option, dict) and "libelle" in option]
        for libelle in sorted({l for l in libelles if libelles.count(l) > 1}):
            self.erreur(f"libellé « {libelle} » en double dans ce menu", "choix")
        for court in libelles:
            for long in libelles:
                if court != long and court in long:
                    self.avertir(f"« {court} » est contenu dans « {long} » : les tests Ren'Py risquent de cliquer le mauvais choix", "choix")

    def galerie(self, galerie):
        if not isinstance(galerie, dict):
            self.erreur("« galerie » : titre, vignette, images ou video attendus")
            return
        for cle in set(galerie) - {"titre", "vignette", "images", "video"}:
            self.erreur(f"champ inconnu « {cle} »", "galerie")
        images, video = galerie.get("images"), galerie.get("video")
        if not images and not video:
            self.erreur("il faut « images » ou « video »", "galerie")
        if images is not None:
            if not isinstance(images, list):
                self.erreur("« images » : liste de noms d'images attendue", "galerie")
            for nom in _liste(images):
                self.image(nom, "galerie.images")
        if video is not None and (not isinstance(video, str) or not video.endswith(".webm")):
            self.erreur("« video » attend un chemin .webm relatif à game/", "galerie")
        if "vignette" in galerie:
            self.image(galerie["vignette"], "galerie.vignette")
        elif video:
            self.erreur("« vignette » obligatoire pour une vidéo", "galerie")

    def image(self, nom, chemin):
        if not isinstance(nom, str) or not MOT_IMAGE.match(nom):
            self.erreur(f"nom d'image invalide {nom!r} (mots séparés par une espace, par exemple « lena sourire »)", chemin)

    def transition(self, element, chemin):
        transition = element.get("transition")
        if transition is not None and transition not in TRANSITIONS:
            self.erreur(f"transition « {transition} » non supportée ({', '.join(TRANSITIONS)})", chemin)


# --- Exploration des routes ------------------------------------------------------------

@dataclass
class Exploration:
    entrees: dict = field(default_factory=dict)        # scène → états distincts à l'entrée
    routes: dict = field(default_factory=dict)         # scène → première route qui l'atteint
    fins: dict = field(default_factory=dict)           # scène finale → états distincts
    fins_routes: list = field(default_factory=list)    # [{fin, etat, choix: ((scène, rang, libellé), …)}]
    predecesseurs: dict = field(default_factory=dict)  # scène → {(scène source, étape)}
    choix_proposes: set = field(default_factory=set)   # {(scène, rang de l'option)}
    lieux_proposes: set = field(default_factory=set)   # {(carte, rang du lieu)} lieux accessibles au moins une fois
    etats: int = 0
    complete: bool = True


class Explorateur:
    """Joue toutes les combinaisons de choix en suivant les variables, comme un
    joueur qui essaierait tout ; les états identiques ne sont explorés qu'une fois."""

    def __init__(self, projet: Projet, rapport: Rapport, limite: int):
        self.projet = projet
        self.rapport = rapport
        self.limite = limite
        self.ex = Exploration()

    def explorer(self) -> Exploration:
        debut = self.projet.bible["debut"]
        initial = {nom: variable["defaut"] for nom, variable in self.projet.variables_toutes.items()}
        a_visiter = [(debut, initial, (debut,), ())]
        vus = set()
        while a_visiter:
            if self.ex.etats >= self.limite:
                self.ex.complete = False
                self.rapport.avertir("exploration", f"limite de {self.limite} états atteinte : exploration partielle")
                break
            sid, etat, route, choix = a_visiter.pop()
            cle = (sid, _gel(etat))
            if cle in vus:
                continue
            vus.add(cle)
            self.ex.etats += 1
            for destination, suite, etape, choix_fait in self._jouer(sid, etat, route, choix):
                self.ex.predecesseurs.setdefault(destination, set()).add((sid, etape))
                a_visiter.append((destination, suite, route + (etape, destination), choix + choix_fait))
        self._bilan()
        return self.ex

    def _entrer(self, sid, etat, route):
        etats = self.ex.entrees.setdefault(sid, [])
        if etat not in etats:
            etats.append(dict(etat))
        self.ex.routes.setdefault(sid, route)
        for condition in conditions_de(self.projet.scenes[sid]):
            if not self._vrai(condition, etat, sid):
                self.rapport.erreur(self.projet.ou(sid),
                                    f"condition d'entrée « {condition} » fausse (état : {_texte_etat(etat)}) "
                                    f"sur la route : {_texte_route(route)}", cle=(sid, "condition", condition))

    def _jouer(self, sid, etat, route, choix):
        fiche = self.projet.scenes[sid]
        self._entrer(sid, etat, route)
        etat = self._executer(fiche.get("contenu"), dict(etat), sid, route, (sid,))
        if etat is None:
            return []
        if fiche.get("choix") is not None:
            _, options = options_de(fiche)
            suivants, proposes = [], 0
            for index, option in enumerate(options):
                if "si" in option and not self._vrai(option["si"], etat, sid):
                    continue
                proposes += 1
                self.ex.choix_proposes.add((sid, index))
                apres = self._effets(option.get("effets"), dict(etat), sid, route)
                apres = self._executer(option.get("contenu"), apres, sid, route, (sid,))
                if apres is not None:
                    suivants.append((option["destination"], apres, f"« {option['libelle']} »",
                                     ((sid, index, str(option["libelle"])),)))
            if proposes == 0:
                self.rapport.erreur(self.projet.ou(sid),
                                    f"aucun choix disponible (état : {_texte_etat(etat)}) sur la route : {_texte_route(route)} ; "
                                    "le jeu continuerait dans la scène suivante du fichier", cle=(sid, "aucun choix"))
            return suivants
        if fiche.get("carte") is not None:
            # Comme le jeu : la présence est recalculée, puis chaque lieu accessible (sur la carte,
            # ses sous-cartes et ses parentes) est une destination possible.
            etat = self._presences(etat, sid)
            suivants = []
            vrai = lambda expr, couts=(): self._vrai(expr, self._apres_couts(etat, couts), sid)  # noqa: E731
            for cible in cibles_carte(self.projet, fiche["carte"], vrai, self.ex.lieux_proposes):
                # Coût des déplacements cliqués (entrées « temps » des cartes), dans l'ordre des clics.
                apres = self._apres_couts(etat, cible["couts"])
                suivants.append((cible["scene"], apres, f"carte « {_texte_clics(self.projet, cible['clics'])} »",
                                 ((sid, f"carte:{cible['carte']}:{cible['rang']}", cible["clics"]),)))
            if not suivants:
                self.rapport.erreur(self.projet.ou(sid),
                                    f"aucun lieu accessible sur la carte « {fiche['carte']} » (état : {_texte_etat(etat)}) "
                                    f"sur la route : {_texte_route(route)} ; le jeu continuerait dans la scène suivante du fichier",
                                    cle=(sid, "aucun lieu"))
            return suivants
        if fiche.get("suite"):
            return [(fiche["suite"], etat, "suite", ())]
        if fiche.get("retour"):
            self.rapport.avertir(self.projet.ou(sid), "scène à « retour » atteinte sans « appel » : son return termine la partie")
        etats = self.ex.fins.setdefault(sid, [])
        if etat not in etats:
            etats.append(etat)
            self.ex.fins_routes.append({"fin": sid, "etat": etat, "choix": choix, "route": route})
        return []

    def _executer(self, elements, etat, sid, route, pile):
        for element in _liste(elements):
            cle = cle_element(element, self.projet)
            if cle == "effets":
                etat = self._effets(element["effets"], etat, sid, route)
            elif cle == "si":
                branches = [(element["si"], element.get("alors"))]
                branches += [(branche["si"], branche.get("alors")) for branche in _liste(element.get("sinon_si"))]
                bloc = element.get("sinon")
                for condition, alors in branches:
                    if self._vrai(condition, etat, sid):
                        bloc = alors
                        break
                etat = self._executer(bloc, etat, sid, route, pile)
            elif cle == "temps":
                etat = self._temps(element["temps"], etat)
            elif cle == "appel":
                cible = element["appel"]
                if cible in pile:
                    self.rapport.erreur(self.projet.ou(sid), f"appel récursif de {cible} ({' → '.join(pile)})")
                    return None
                self.ex.predecesseurs.setdefault(cible, set()).add((pile[-1], "appel"))
                self._entrer(cible, etat, route + ("appel", cible))
                etat = self._executer(self.projet.scenes[cible].get("contenu"), etat, cible, route, pile + (cible,))
            if etat is None:
                return None
        return etat

    def _apres_couts(self, etat, couts):
        """État après des déplacements payés (entrées « temps » des cartes : créneaux ou jours)."""
        apres = dict(etat)
        for cout in couts:
            apres = self.projet.jour_suivant(apres, int(cout["jours"])) if isinstance(cout, dict) else self._temps(int(cout), apres)
        return apres

    def _temps(self, valeur, etat):
        """Élément « temps » : n créneaux de plus, jusqu'au prochain créneau nommé, ou un saut de jours,
        de mois ou jusqu'à une date (créneau conservé, sauf « creneau » indiqué)."""
        if isinstance(valeur, dict):
            if "jours" in valeur:
                etat = self.projet.jour_suivant(etat, int(valeur["jours"]))
            elif "mois" in valeur:
                etat = self.projet.sauter_mois(etat, int(valeur["mois"]))
            elif "epoque" in valeur:
                etat = self.projet.changer_epoque(etat, valeur["epoque"])
            else:
                etat = self.projet.aller_date(etat, _date_de(valeur["date"]))
            if "creneau" in valeur:
                etat = dict(etat)
                etat["creneau"] = self.projet.temps["creneaux"].index(valeur["creneau"])
                etat["moment"] = valeur["creneau"]
            return etat
        if isinstance(valeur, str):
            etat = self.projet.avancer_temps(etat)
            for _ in self.projet.temps["creneaux"]:
                if etat["moment"] == valeur:
                    break
                etat = self.projet.avancer_temps(etat)
            return etat
        for _ in range(int(valeur)):
            etat = self.projet.avancer_temps(etat)
        return etat

    def _presences(self, etat, sid):
        """Lieu de chaque personnage : la première règle « presence » vraie, sinon aucun lieu."""
        for nom, variable in self.projet.variables_presence.items():
            lieu = ""
            for regle in _liste(_dict(self.projet.personnages.get(variable["personnage"])).get("presence")):
                if isinstance(regle, dict) and ("si" not in regle or self._vrai(regle["si"], etat, sid)):
                    lieu = str(regle.get("lieu", ""))
                    break
            etat[nom] = lieu
        return etat

    def _effets(self, effets, etat, sid, route):
        for nom, valeur in _dict(effets).items():
            actuel = etat.get(nom)
            if _est_nombre(valeur) and _est_nombre(actuel):
                etat[nom] = actuel + valeur
            else:
                etat[nom] = valeur
            self._bornes(nom, etat[nom], sid, route)
        return etat

    def _bornes(self, nom, valeur, sid, route):
        variable = self.projet.variables_modifiables.get(nom, {})
        if not _est_nombre(valeur):
            return
        for borne, depasse, texte in (("min", valeur < variable.get("min", valeur), "sous le minimum"),
                                      ("max", valeur > variable.get("max", valeur), "au-dessus du maximum")):
            if depasse:
                self.rapport.avertir(self.projet.ou(sid),
                                     f"« {nom} » vaut {valeur}, {texte} {variable[borne]}, sur la route : {_texte_route(route)}",
                                     cle=(sid, nom, borne))

    def _vrai(self, expr, etat, sid) -> bool:
        texte = _expr_texte(expr)
        try:
            return bool(eval(texte, {"__builtins__": {}, **FONCTIONS}, dict(etat)))  # noqa: S307 — expressions validées par _Verif.expression
        except Exception as exc:  # noqa: BLE001
            self.rapport.erreur(self.projet.ou(sid), f"évaluation impossible de « {texte} » (état : {_texte_etat(etat)}) : {exc}",
                                cle=(sid, "eval", texte))
            return False

    def _bilan(self):
        for sid in self.projet.ordre():
            if sid not in self.ex.entrees:
                self.rapport.avertir(self.projet.ou(sid), "scène jamais atteinte depuis « debut »")
                continue
            _, options = options_de(self.projet.scenes[sid])
            for index, option in enumerate(options):
                if (sid, index) not in self.ex.choix_proposes:
                    self.rapport.avertir(self.projet.ou(sid),
                                         f"choix « {option.get('libelle')} » jamais proposé (condition « {option.get('si')} » toujours fausse)")
        for cid, carte in self.projet.cartes.items():
            for rang, entree in enumerate(_liste(_dict(carte).get("lieux"))):
                if isinstance(entree, dict) and (cid, rang) not in self.ex.lieux_proposes:
                    condition = f" (condition « {_expr_texte(entree['si'])} » toujours fausse)" if "si" in entree else " (carte jamais affichée)"
                    self.rapport.avertir(f"contenu/bible.yaml, carte « {cid} »",
                                         f"lieu « {entree.get('lieu')} » jamais accessible{condition}")
        if self.ex.complete and not self.ex.fins:
            self.rapport.erreur("exploration", "aucune route n'atteint une fin (« fin: true »)")


def cibles_carte(projet: Projet, cid, vrai, proposes: set | None = None) -> list:
    """Destinations accessibles depuis une carte : les lieux visibles de la carte, les raccourcis,
    puis les lieux de ses sous-cartes et de ses cartes parentes, avec le chemin de clics le plus
    court pour y arriver et les coûts en temps payés en chemin. vrai(expression, couts) évalue
    une condition après ces coûts ; proposes, s'il est donné, reçoit les (carte, rang) de tous les
    lieux visibles. [{carte, rang, scene, clics: [("lieu" | "raccourci", id) | ("parent", carte)], couts}]"""
    parents = projet.parents_cartes()
    file, vus, resultat, atteints = [(cid, [], [])], {cid}, [], set()

    def visiter(courante, rang, entree, chemin, couts, genre):
        # La condition d'un lieu s'évalue après les déplacements déjà payés pour arriver à sa carte.
        if not isinstance(entree, dict) or ("si" in entree and not vrai(entree["si"], couts)):
            return
        if proposes is not None:
            proposes.add((courante, rang))
        clics = chemin + [(genre, entree.get("lieu"))]
        couts = couts + ([entree["temps"]] if "temps" in entree else [])
        if entree.get("scene") in projet.scenes:
            if (courante, rang) not in atteints:
                atteints.add((courante, rang))
                resultat.append({"carte": courante, "rang": rang, "scene": entree["scene"], "clics": clics, "couts": couts})
        elif entree.get("carte") in projet.cartes and entree["carte"] not in vus:
            vus.add(entree["carte"])
            file.append((entree["carte"], clics, couts))

    # Les lieux de la carte affichée, puis les raccourcis (proposés partout, sauf sur leur propre
    # carte où le lieu se clique directement), puis les sous-cartes et les cartes parentes.
    premiere = True
    while file:
        courante, chemin, couts = file.pop(0)
        lieux = _liste(_dict(projet.cartes.get(courante)).get("lieux"))
        for rang, entree in enumerate(lieux):
            visiter(courante, rang, entree, chemin, couts, "lieu")
        if premiere:
            premiere = False
            ici = {_dict(e).get("lieu") for e in lieux}
            for origine, entree in projet.raccourcis():
                if entree.get("lieu") not in ici:
                    rang = _liste(_dict(projet.cartes.get(origine)).get("lieux")).index(entree)
                    visiter(origine, rang, entree, [], [], "raccourci")
        parent = parents.get(courante, "")
        if parent and parent not in vus:
            vus.add(parent)
            file.append((parent, chemin + [("parent", parent)], couts))
    return resultat


def _clics_textes(projet: Projet, clics: list, textes: dict | None = None) -> list:
    """Textes cliqués sur les cartes pour un chemin (nom du lieu, ou « ← titre » de la carte
    parente), traduits avec textes ({texte source : traduction}) s'il est donné."""
    textes = textes or {}
    resultat = []
    for genre, cible in clics:
        texte = projet.nom_lieu(cible) if genre in ("lieu", "raccourci") else projet.titre_carte(cible)
        texte = textes.get(texte, texte)
        resultat.append(texte if genre in ("lieu", "raccourci") else f"← {texte}")
    return resultat


def _texte_clics(projet: Projet, clics: list, textes: dict | None = None) -> str:
    return " › ".join(_clics_textes(projet, clics, textes))


def _libelle_choix(projet: Projet, libelle) -> str:
    """Libellé d'une étape de route : le texte du choix, ou le chemin cliqué sur les cartes."""
    return _texte_clics(projet, libelle) if isinstance(libelle, list) else str(libelle)


def routes_de_test(exploration: Exploration, maximum: int = ROUTES_MAX) -> list:
    """Petit ensemble de routes complètes qui couvre toutes les fins et tous les choix
    proposés (glouton : on prend à chaque fois la route qui couvre le plus de nouveautés)."""
    candidates = sorted(exploration.fins_routes, key=lambda r: (r["fin"], [str(c[2]) for c in r["choix"]]))

    def couverture(route):
        return {("fin", route["fin"])} | {("choix", sid, rang) for sid, rang, _ in route["choix"]}

    a_couvrir = set().union(*(couverture(route) for route in candidates)) if candidates else set()
    choisies = []
    while a_couvrir and len(choisies) < maximum:
        meilleure = max(candidates, key=lambda route: len(couverture(route) & a_couvrir))
        gain = couverture(meilleure) & a_couvrir
        if not gain:
            break
        choisies.append(meilleure)
        a_couvrir -= gain
    return choisies


# --- Génération ------------------------------------------------------------------------------

def generer(projet: Projet, exploration: Exploration | None = None) -> dict:
    """Renvoie {chemin relatif : contenu} de tous les fichiers produits : script, galerie,
    langues et traductions (game/tl/<langue>/story/) ; avec l'exploration, ajoute les
    tests de parcours pour Godot et Ren'Py."""
    avec_ids = bool(projet.langues_cibles)
    fichiers = {FICHIER_BIBLE_RPY: _rpy_bible(projet)}
    for chapitre, sids in sorted(_chapitres(projet).items()):
        fichiers[f"game/story/chapitre_{chapitre}.rpy"] = _rpy_chapitre(projet, chapitre, sids, avec_ids)
    fichiers[FICHIER_GALERIE] = _galerie_json(projet)
    fichiers[FICHIER_NAVIGATION] = _navigation_json(projet)
    fichiers[FICHIER_PERSONNAGES] = _personnages_json(projet)
    fichiers[FICHIER_RENOMMAGES] = _renommages_json(projet)
    fichiers[FICHIER_TEMPS] = _temps_json(projet)
    fichiers[FICHIER_LANGUES] = _langues_json(projet)
    for code in projet.langues_cibles:
        fichiers.update(_rpy_traduction(projet, code))
    if exploration is not None:
        routes = routes_de_test(exploration)
        fichiers[FICHIER_ROUTES] = _routes_json(projet, routes)
        fichiers[FICHIER_TESTS_RENPY] = _tests_renpy(projet, routes)
    return fichiers


def ecrire(projet: Projet, fichiers: dict, rapport: Rapport, remplacer: bool = False):
    """Écrit les fichiers produits sans jamais écraser un fichier écrit à la main
    (sauf remplacer=True), puis supprime les fichiers générés devenus inutiles."""
    ecrits, supprimes = [], []
    for relatif, texte in fichiers.items():
        chemin = projet.racine / relatif
        if chemin.exists():
            ancien = chemin.read_text(encoding="utf-8")
            if ancien == texte:
                continue
            if MARQUEUR not in ancien[:400] and not remplacer:
                rapport.erreur(relatif, "fichier écrit à la main : relancez avec --remplacer pour l'écraser")
                continue
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(texte, encoding="utf-8")
        ecrits.append(relatif)
    # Script et traductions générés devenus inutiles (scène, chapitre ou langue retirés).
    generes = [chemin for dossier in ("game/story", "game/tl") if (projet.racine / dossier).is_dir()
               for chemin in sorted((projet.racine / dossier).rglob("*.rpy"))]
    for chemin in generes:
        relatif = chemin.relative_to(projet.racine).as_posix()
        if relatif not in fichiers and MARQUEUR in chemin.read_text(encoding="utf-8")[:400]:
            chemin.unlink()
            compile_renpy = chemin.with_suffix(".rpyc")
            if compile_renpy.exists():
                compile_renpy.unlink()
            supprimes.append(relatif)
    return ecrits, supprimes


def _chapitre(sid, fiche) -> str:
    if isinstance(fiche.get("chapitre"), int):
        return f"{fiche['chapitre']:02d}"
    trouve = re.match(r"CH(\d+)", sid)
    return f"{int(trouve.group(1)):02d}" if trouve else "divers"


def _chapitres(projet: Projet) -> dict:
    """{chapitre : [scènes]}, scènes dans l'ordre."""
    chapitres: dict = {}
    for sid in projet.ordre():
        chapitres.setdefault(_chapitre(sid, projet.scenes[sid]), []).append(sid)
    return chapitres


def _rpy_bible(projet: Projet) -> str:
    lignes = [f"# {MARQUEUR}", "# Personnages et variables : contenu/bible.yaml.", ""]
    for pid, personnage in projet.personnages.items():
        # _() : le nom est traduit comme les autres textes de l'interface.
        arguments = [f"_({_chaine(personnage['nom'])})"]
        if personnage.get("couleur"):
            arguments.append(f"color={_chaine(personnage['couleur'])}")
        lignes.append(f"define {pid} = Character({', '.join(arguments)})")
    lignes.append("")
    for nom, variable in projet.variables.items():
        lignes.append(f"default {nom} = {_litteral(variable['defaut'])}")
    jauges = projet.variables_personnages
    if jauges:
        lignes += ["", "# Jauges, compétences et relations des personnages (bible : « jauges », « competences », « relations »)."]
        for nom, variable in jauges.items():
            lignes.append(f"default {nom} = {_litteral(variable['defaut'])}")
    temps = projet.variables_temps
    if temps:
        lignes += ["", "# Temps (bible, « temps ») : avance seulement par l'élément « temps » (label temps_avancer)."]
        for nom, variable in temps.items():
            lignes.append(f"default {nom} = {_litteral(variable['defaut'])}")
    presence = projet.variables_presence
    if presence:
        lignes += ["", "# Lieu de chaque personnage, recalculé à chaque carte (règles « presence » de la bible)."]
        for nom in presence:
            lignes.append(f'default {nom} = ""')
    lignes += ["", "", "label start:", f"    jump {projet.bible['debut'].lower()}", ""]
    if temps:
        lignes += _rpy_temps(projet)
    return "\n".join(lignes)


def _rpy_temps(projet: Projet) -> list:
    """Labels du temps : temps_avancer (créneau suivant, jour suivant après le dernier), temps_jour_suivant
    (jour, semaine, calendrier, événements) et, avec une date, les sauts de jours, de mois et jusqu'à une date."""
    modele = projet.temps
    lignes = ["", "# Un créneau de plus ; appelé par l'élément « temps » des fiches.", f"label {LABEL_TEMPS}:",
              "    $ creneau += 1", f"    if creneau >= {len(modele['creneaux'])}:", "        $ creneau = 0",
              "        call temps_jour_suivant", "    call temps_calculer_noms", "    return",
              "", "# Un jour de plus, même créneau.", "label temps_jour_suivant:"]
    if modele["jours"]:
        lignes.append("    $ jour += 1")
    if modele["semaine"]:
        lignes += ["    $ jour_semaine_rang += 1", f"    if jour_semaine_rang >= {len(modele['semaine'])}:",
                   "        $ jour_semaine_rang = 0"]
    if modele["date"] is not None:
        lignes += ["    $ jour_mois += 1", "    if jour_mois > temps_longueur_mois:", "        $ jour_mois = 1", "        $ mois += 1",
                   "        if mois > 12:", "            $ mois = 1", "            $ annee += 1", "            $ temps_bissextile_rang += 1",
                   "            if temps_bissextile_rang >= 4:", "                $ temps_bissextile_rang = 0",
                   "        call temps_calculer_mois"]
    lignes += ["    call temps_calculer_noms", "    return",
               "", "# Noms du créneau et du jour, événements du jour : recalculés après chaque changement.",
               "label temps_calculer_noms:"]
    for rang, nom in enumerate(modele["creneaux"]):
        lignes += [f"    {'if' if rang == 0 else 'elif'} creneau == {rang}:", f"        $ moment = {_chaine(nom)}"]
    for rang, nom in enumerate(modele["semaine"]):
        lignes += [f"    {'if' if rang == 0 else 'elif'} jour_semaine_rang == {rang}:", f"        $ jour_semaine = {_chaine(nom)}"]
    for nom, (mois, jour) in (modele["evenements"] if modele["date"] is not None else {}).items():
        lignes.append(f"    $ evenement_{nom} = mois == {mois} and jour_mois == {jour}")
    lignes.append("    return")
    if modele["date"] is None:
        return lignes + [""]
    lignes += ["", "# Longueur du mois courant (années bissextiles : tous les quatre ans, sauf 2100, 2200 et 2300).",
               "label temps_calculer_mois:", "    if mois == 2:",
               "        if temps_bissextile_rang == 0 and annee != 2100 and annee != 2200 and annee != 2300:",
               "            $ temps_longueur_mois = 29", "        else:", "            $ temps_longueur_mois = 28",
               "    elif mois == 4 or mois == 6 or mois == 9 or mois == 11:", "        $ temps_longueur_mois = 30",
               "    else:", "        $ temps_longueur_mois = 31", "    return",
               "", "# Saut de temps_saut jours (fiche : temps: { jours: n }).", "label temps_sauter_jours:",
               "    if temps_saut > 0:", "        $ temps_saut -= 1", "        call temps_jour_suivant", "        jump temps_sauter_jours",
               "    return",
               "", "# Saut de temps_saut mois, même jour du mois ou dernier jour du mois d'arrivée (temps: { mois: n }).",
               "label temps_sauter_mois:", "    $ temps_cible_jour = jour_mois", "    jump temps_sauter_mois_suivant",
               "label temps_sauter_mois_suivant:", "    if temps_saut > 0:", "        $ temps_saut -= 1",
               "        $ temps_cible_mois = mois + 1", "        if temps_cible_mois > 12:", "            $ temps_cible_mois = 1",
               "        jump temps_sauter_mois_jours", "    return",
               "label temps_sauter_mois_jours:",
               "    if mois == temps_cible_mois and (jour_mois == temps_cible_jour or jour_mois == temps_longueur_mois):",
               "        jump temps_sauter_mois_suivant", "    call temps_jour_suivant", "    jump temps_sauter_mois_jours", ""]
    for nom in modele["epoques"]:
        # Voyage dans le temps : la date courante est rangée dans l'époque quittée, celle de l'époque rejointe reprise.
        lignes += [f"# Voyage vers l'époque « {nom} » (temps: {{ epoque: {nom} }}).", f"label temps_epoque_{nom}:"]
        for rang, courante in enumerate(modele["epoques"]):
            lignes.append(f"    {'if' if rang == 0 else 'elif'} epoque == {_chaine(courante)}:")
            lignes += [f"        $ epoque_{courante}_{champ} = {champ}" for champ in CHAMPS_EPOQUE]
        lignes += [f"    $ {champ} = epoque_{nom}_{champ}" for champ in CHAMPS_EPOQUE]
        lignes += [f"    $ epoque = {_chaine(nom)}", "    call temps_calculer_noms", "    return", ""]
    return lignes


@dataclass
class Replique:
    """Réplique du script, repérée pour la traduction."""
    rid: str    # identifiant (clause « id » de la réplique dans le .rpy)
    sid: str    # scène
    qui: str    # id du personnage, vide pour la narration
    texte: str  # texte dans la langue des fiches


class _Script:
    """Script d'une scène en cours d'écriture. Chaque réplique reçoit un identifiant stable,
    label + empreinte du personnage et du texte (ch01_sc02_1a2b3c4d), qui la relie à ses
    traductions ; il n'est écrit dans le .rpy que si la bible déclare des traductions."""

    def __init__(self, projet: Projet, sid: str, avec_ids: bool):
        self.projet = projet
        self.sid = sid
        self.avec_ids = avec_ids
        self.repliques: list = []

    def replique(self, qui: str, texte, marge: str) -> str:
        texte = str(texte)
        base = f"{self.sid.lower()}_{hashlib.md5(f'{qui}|{texte}'.encode('utf-8')).hexdigest()[:8]}"
        pris = {replique.rid for replique in self.repliques}
        rid, rang = base, 0
        while rid in pris:  # même réplique répétée dans la scène : suffixe, comme Ren'Py
            rang += 1
            rid = f"{base}_{rang}"
        self.repliques.append(Replique(rid, self.sid, qui, texte))
        ligne = f"{marge}{qui + ' ' if qui else ''}{_chaine(texte)}"
        return f"{ligne} id {rid}" if self.avec_ids else ligne


def _rpy_chapitre(projet: Projet, chapitre: str, sids: list, avec_ids: bool) -> str:
    lignes = [f"# {MARQUEUR}", f"# Chapitre {chapitre} : {', '.join(sids)}."]
    for sid in sids:
        lignes += _rpy_scene(_Script(projet, sid, avec_ids))
    lignes.append("")
    return "\n".join(lignes)


def _rpy_scene(script: _Script) -> list:
    sid = script.sid
    fiche = script.projet.scenes[sid]
    entete = f"    # {sid} — {fiche.get('titre', '')}"
    details = [str(valeur) for valeur in (fiche.get("lieu"), fiche.get("moment")) if valeur]
    if details:
        entete += f" ({', '.join(details)})"
    lignes = ["", "", f"label {sid.lower()}:", entete]
    lignes += [f"    # objectif : {objectif}" for objectif in _liste(fiche.get("objectif_narratif"))]
    lignes += _rpy_elements(script, fiche.get("contenu"), 1)
    lignes += _rpy_fin(script, fiche)
    return lignes


def _rpy_elements(script: _Script, elements, niveau: int) -> list:
    projet = script.projet
    marge = "    " * niveau
    lignes = []
    for element in _liste(elements):
        cle = cle_element(element, projet)
        valeur = element[cle]
        if cle == "narration":
            lignes.append(script.replique("", valeur, marge))
        elif cle in projet.personnages:
            lignes.append(script.replique(cle, valeur, marge))
        elif cle == "decor":
            decors = projet.decors_par_creneau(valeur) if valeur else None
            if decors is None:
                lignes.append(f"{marge}scene{' ' + valeur if valeur else ''}{_avec(element)}")
            else:
                # Décor du créneau courant ; à défaut, le premier déclaré.
                for rang, (creneau, image) in enumerate(decors.items()):
                    variable = "epoque" if creneau in projet.temps["epoques"] else "moment"
                    lignes.append(f"{marge}{'if' if rang == 0 else 'elif'} {variable} == {_chaine(creneau)}:")
                    lignes.append(f"{marge}    scene {image}{_avec(element)}")
                lignes += [f"{marge}else:", f"{marge}    scene {next(iter(decors.values()))}{_avec(element)}"]
        elif cle == "temps":
            if isinstance(valeur, dict):
                if "jours" in valeur:
                    lignes += [f"{marge}$ temps_saut = {int(valeur['jours'])}", f"{marge}call temps_sauter_jours"]
                elif "mois" in valeur:
                    lignes += [f"{marge}$ temps_saut = {int(valeur['mois'])}", f"{marge}call temps_sauter_mois"]
                elif "epoque" in valeur:
                    lignes.append(f"{marge}call temps_epoque_{valeur['epoque']}")
                else:
                    # Date connue d'avance : tout est posé directement (passé ou futur).
                    date = _date_de(valeur["date"])
                    champs = projet.champs_date(date)
                    champs.pop("jour_semaine", None)
                    champs["jour"] = (date - projet.temps["date"]).days + 1
                    lignes += [f"{marge}$ {nom} = {valeur_champ}" for nom, valeur_champ in champs.items()]
                    lignes.append(f"{marge}call temps_calculer_noms")
                if "creneau" in valeur:
                    lignes += [f"{marge}$ creneau = {projet.temps['creneaux'].index(valeur['creneau'])}",
                               f"{marge}$ moment = {_chaine(valeur['creneau'])}"]
            elif isinstance(valeur, str):
                lignes.append(f"{marge}call {LABEL_TEMPS}")
                for _ in projet.temps["creneaux"][1:]:
                    lignes += [f"{marge}if moment != {_chaine(valeur)}:", f"{marge}    call {LABEL_TEMPS}"]
            else:
                lignes += [f"{marge}call {LABEL_TEMPS}"] * int(valeur)
        elif cle == "montrer":
            position = f" at {element['position']}" if element.get("position") else ""
            lignes.append(f"{marge}show {valeur}{position}{_avec(element)}")
        elif cle == "cacher":
            lignes.append(f"{marge}hide {valeur}{_avec(element)}")
        elif cle == "video":
            lignes.append(f"{marge}$ renpy.movie_cutscene({_chaine(valeur)})")
        elif cle == "pause":
            lignes.append(f"{marge}pause" + (f" {valeur}" if valeur is not None else ""))
        elif cle in ("musique", "son"):
            canal = "music" if cle == "musique" else "sound"
            lignes.append(f"{marge}stop {canal}" if valeur == "stop" else f"{marge}play {canal} {_chaine(valeur)}")
        elif cle == "effets":
            lignes += _rpy_effets(projet, valeur, marge)
        elif cle == "si":
            lignes.append(f"{marge}if {_expr_texte(valeur)}:")
            lignes += _rpy_bloc(script, element.get("alors"), niveau + 1)
            for branche in _liste(element.get("sinon_si")):
                lignes.append(f"{marge}elif {_expr_texte(branche['si'])}:")
                lignes += _rpy_bloc(script, branche.get("alors"), niveau + 1)
            if element.get("sinon") is not None:
                lignes.append(f"{marge}else:")
                lignes += _rpy_bloc(script, element.get("sinon"), niveau + 1)
        elif cle == "appel":
            lignes.append(f"{marge}call {valeur.lower()}")
    return lignes


def _rpy_bloc(script: _Script, elements, niveau: int) -> list:
    return _rpy_elements(script, elements, niveau) or ["    " * niveau + "pass"]


def _rpy_effets(projet: Projet, effets: dict, marge: str) -> list:
    lignes = []
    for nom, valeur in effets.items():
        if _est_nombre(projet.variables_modifiables[nom]["defaut"]):
            lignes.append(f"{marge}$ {nom} {'+=' if valeur >= 0 else '-='} {abs(valeur)!r}")
        else:
            lignes.append(f"{marge}$ {nom} = {_litteral(valeur)}")
    return lignes


def _rpy_fin(script: _Script, fiche: dict) -> list:
    projet = script.projet
    if fiche.get("choix") is not None:
        question, options = options_de(fiche)
        lignes = ["    menu:"]
        if question is not None:
            lignes += _rpy_elements(script, [question], 2)
        for option in options:
            condition = f" if {_expr_texte(option['si'])}" if "si" in option else ""
            lignes += ["", f"        {_chaine(str(option['libelle']))}{condition}:"]
            lignes += _rpy_effets(projet, _dict(option.get("effets")), "            ")
            lignes += _rpy_elements(script, option.get("contenu"), 3)
            lignes.append(f"            jump {option['destination'].lower()}")
        return lignes
    if fiche.get("suite"):
        return [f"    jump {fiche['suite'].lower()}"]
    if fiche.get("carte") is not None:
        # Carte de navigation (game/navigation.json) : le joueur choisit un lieu, qui saute à sa scène.
        # Le lieu de la scène, s'il est déclaré, est signalé « vous êtes ici » sur la carte.
        arguments = [_chaine(str(fiche["carte"]))]
        if fiche.get("lieu") in projet.lieux:
            arguments.append(_chaine(str(fiche["lieu"])))
        return [f"    $ naviguer({', '.join(arguments)})"]
    return ["    return"]


def _avec(element) -> str:
    return f" with {element['transition']}" if element.get("transition") else ""


def _titre_galerie(sid: str, fiche: dict) -> str:
    return str(_dict(fiche.get("galerie")).get("titre", fiche.get("titre", sid)))


def _galerie_json(projet: Projet) -> str:
    entrees = []
    for sid in projet.ordre():
        fiche = projet.scenes[sid]
        galerie = fiche.get("galerie")
        if not galerie:
            continue
        images = list(galerie.get("images") or [])
        entree = {"titre": _titre_galerie(sid, fiche), "label": sid.lower(),
                  "vignette": galerie.get("vignette", images[0] if images else "")}
        if galerie.get("video"):
            entree["video"] = galerie["video"]
        if images:
            entree["images"] = images
        entrees.append(entree)
    return json.dumps({"_genere_par": MARQUEUR, "entrees": entrees}, ensure_ascii=False, indent=2) + "\n"


def _navigation_json(projet: Projet) -> str:
    """Cartes de navigation et règles de présence, lues par game/navigation.rpy (Ren'Py) et
    par le lecteur Godot (engine/navigation.gd). Les conditions sont des expressions du
    sous-ensemble, évaluées par chaque moteur avec les variables du jeu."""
    parents = projet.parents_cartes()
    cartes = {}
    for cid, carte in projet.cartes.items():
        carte = _dict(carte)
        lieux = []
        for entree in _liste(carte.get("lieux")):
            if not isinstance(entree, dict):
                continue
            lieux.append(_entree_navigation(projet, entree))
        cartes[cid] = {"titre": projet.titre_carte(cid), "affichage": projet.affichage_carte(cid),
                       "image": str(carte.get("image") or ""), "parent": parents.get(cid, ""), "lieux": lieux}
    # Raccourcis : lieux proposés depuis toutes les cartes (bouton en bas à droite).
    raccourcis = [dict(_entree_navigation(projet, entree), carte_origine=origine) for origine, entree in projet.raccourcis()]
    personnages = {}
    for nom, variable in projet.variables_presence.items():
        pid = variable["personnage"]
        fiche = _dict(projet.personnages.get(pid))
        personnages[pid] = {
            "nom": str(fiche.get("nom", pid)), "couleur": str(fiche.get("couleur") or ""),
            "avatar": str(fiche.get("avatar") or ""), "variable": nom,
            "presence": [{"lieu": str(regle.get("lieu", "")), "si": _expr_texte(regle["si"]) if "si" in regle else ""}
                         for regle in _liste(fiche.get("presence")) if isinstance(regle, dict)],
        }
    # Lieu de chaque scène : la rangée des pièces reste affichée pendant les scènes jouées dans
    # une pièce d'un bâtiment (carte « pieces »).
    scenes = {sid.lower(): str(fiche["lieu"]) for sid in projet.ordre()
              for fiche in [projet.scenes[sid]] if fiche.get("lieu") in projet.lieux}
    return json.dumps({"_genere_par": MARQUEUR, "cartes": cartes, "raccourcis": raccourcis, "personnages": personnages,
                       "scenes": scenes}, ensure_ascii=False, indent=2) + "\n"


def _entree_navigation(projet: Projet, entree: dict) -> dict:
    """Un lieu d'une carte pour navigation.json ; « temps » : coût du déplacement, {"creneaux": n}
    ou {"jours": n}, appliqué par le moteur quand le joueur choisit le lieu."""
    cout = entree.get("temps")
    return {
        "lieu": str(entree.get("lieu", "")), "nom": projet.nom_lieu(entree.get("lieu")),
        "icone": str(_dict(projet.lieux.get(entree.get("lieu"))).get("icone") or ""),
        "x": entree.get("x", 50), "y": entree.get("y", 50),
        "label": str(entree["scene"]).lower() if entree.get("scene") else "",
        "carte": str(entree.get("carte") or ""),
        "si": _expr_texte(entree["si"]) if "si" in entree else "",
        "temps": ({"jours": int(cout["jours"])} if isinstance(cout, dict) else {"creneaux": int(cout)}) if cout else None,
        "raccourci": entree.get("raccourci") is True,
    }


def _personnages_json(projet: Projet) -> str:
    """Fiches des personnages pour l'écran « Personnages » du menu de jeu (Ren'Py :
    game/personnages.rpy ; Godot : engine/ui/characters_page.gd) : jauges, compétences et
    relations avec leur variable, leurs bornes et leurs paliers. Une relation figure sur les
    fiches des deux personnages (« avec » : l'autre, dont le nom et la couleur sont repris si
    la relation n'a pas de nom). Seuls les personnages qui ont au moins une entrée figurent."""
    personnages = {}
    for pid in projet.personnages_avec_jauges():
        fiche = _dict(projet.personnages.get(pid))
        entree = {"nom": str(fiche.get("nom", pid)), "couleur": str(fiche.get("couleur") or ""),
                  "avatar": str(fiche.get("avatar") or ""), "jauges": [], "competences": [], "relations": []}
        for nom, variable in projet.variables_personnages.items():
            autre = variable["avec"] if variable["personnage"] == pid else variable["personnage"] if variable["avec"] == pid else None
            if autre is None:
                continue
            jauge = {"variable": nom, "nom": variable["nom"],
                     "min": variable.get("min", 0), "max": variable.get("max", max(variable["defaut"], 0)),
                     "paliers": [{"des": seuil, "nom": palier} for seuil, palier in variable["paliers"]]}
            if variable["genre"] == "relation":
                fiche_autre = _dict(projet.personnages.get(autre))
                jauge.update({"nom": variable["nom"] or projet.nom_personnage(autre), "avec": autre,
                              "couleur": str(fiche_autre.get("couleur") or "")})
                entree["relations"].append(jauge)
            else:
                entree["jauges" if variable["genre"] == "jauge" else "competences"].append(jauge)
        personnages[pid] = entree
    return json.dumps({"_genere_par": MARQUEUR, "personnages": personnages}, ensure_ascii=False, indent=2) + "\n"


def _temps_json(projet: Projet) -> str:
    """Modèle de temps pour l'affichage du jour et du créneau pendant la partie (Ren'Py :
    game/temps.rpy ; Godot : engine/temps.gd). Les valeurs sont les variables creneau, moment,
    jour et jour_semaine du script."""
    temps = projet.temps or {"creneaux": [], "jours": False, "semaine": [], "date": None}
    return json.dumps({"_genere_par": MARQUEUR, "creneaux": temps["creneaux"], "jours": temps["jours"],
                       "semaine": temps["semaine"], "date": temps["date"] is not None,
                       "mois": list(MOIS_NOMS) if temps["date"] is not None else [],
                       "epoques": list(temps.get("epoques") or [])}, ensure_ascii=False, indent=2) + "\n"


def _renommages_json(projet: Projet) -> str:
    """Renommages appliqués aux anciennes sauvegardes, lus par game/sauvegardes.rpy (Ren'Py :
    config.label_overrides et un rappel après chargement) et par le lecteur Godot
    (engine/renommages.gd, appliqués par l'interpréteur au chargement d'un état)."""
    renommages = projet.renommages
    return json.dumps({"_genere_par": MARQUEUR,
                       "variables": [{"ancien": a, "nouveau": n} for a, n in _aplatir(renommages["variables"])],
                       "scenes": [{"ancien": a, "nouveau": n} for a, n in _aplatir(renommages["scenes"])]},
                      ensure_ascii=False, indent=2) + "\n"


def _aplatir(renommages: list) -> list:
    """Renommages en chaîne (a → b, b → c) ramenés au nom final (a → c, b → c), pour que les
    moteurs n'aient qu'un pas à faire ; une boucle s'arrête au dernier nom visité."""
    suivants = dict(renommages)
    resultat = []
    for ancien, nouveau in renommages:
        vus = {ancien}
        while nouveau in suivants and nouveau not in vus:
            vus.add(nouveau)
            nouveau = suivants[nouveau]
        resultat.append((ancien, nouveau))
    return resultat


def _routes_json(projet: Projet, routes: list) -> str:
    """Routes attendues, rejouées par tests/run_tests.gd : l'état final calculé par
    l'explorateur Python doit être celui de l'interpréteur Godot, dans chaque langue
    (« choix_traduits » : les mêmes choix, tels qu'affichés dans la traduction). Une étape
    est le texte d'un choix, ou la liste des textes cliqués sur les cartes."""
    traduits = {code: traductions_de(projet, code)[1] for code in projet.langues_cibles}

    def etapes(textes):
        return [_clics_textes(projet, libelle, textes) if isinstance(libelle, list) else textes.get(libelle, libelle)
                for _, _, libelle in route["choix"]]

    donnees = {"_genere_par": MARQUEUR, "routes": []}
    for numero, route in enumerate(routes, 1):
        entree = {"nom": f"route_{numero:02d}", "choix": etapes({}), "fin": route["fin"].lower(), "etat_final": route["etat"]}
        if traduits:
            entree["choix_traduits"] = {code: etapes(textes) for code, textes in traduits.items()}
        donnees["routes"].append(entree)
    return json.dumps(donnees, ensure_ascii=False, indent=2) + "\n"


def _tests_renpy(projet: Projet, routes: list) -> str:
    """Testcases Ren'Py : chaque route rejoue ses choix et doit atteindre sa fin, dans la
    langue des fiches puis dans chaque traduction (choix cliqués par leur texte traduit) ;
    « galerie » débloque toutes les entrées puis ouvre l'écran de galerie."""
    lignes = [f"# {MARQUEUR}", "# Tests de parcours Ren'Py : renpy.sh <projet> test"]
    langues = [(projet.langue_source, {})] + [(code, traductions_de(projet, code)[1]) for code in projet.langues_cibles]
    plusieurs = len(langues) > 1
    for numero, route in enumerate(routes, 1):
        fin = _chaine(route["fin"].lower())
        for code, textes in langues:
            suffixe = f"_{code}" if code != projet.langue_source else ""
            # La condition « label » des tests perd les labels traversés pendant un clic :
            # on oublie la fin attendue (clé en clair ou hachée, selon config.hash_seen),
            # on joue jusqu'au menu principal, puis renpy.seen_label doit la retrouver.
            # Les routes qui traversent des cartes enchaînent beaucoup de clics : délai large.
            lignes += ["", "", f"testcase route_{numero:02d}{suffixe}:", "    $ _test.timeout = 120.0",
                       "    $ _test.transition_timeout = 0.05",
                       f"    $ renpy.game.persistent._seen_ever.pop({fin}, None)",
                       f"    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64({fin}), None)",
                       '    pause until screen "main_menu"']
            if plusieurs:
                # Un changement de langue reconstruit les styles : on le laisse finir avant Start(),
                # sinon Ren'Py peut rejouer l'action une fois la partie commencée.
                lignes += [f"    run Language({_chaine(_nom_renpy(code))})", "    pause 0.5"]
            lignes.append("    run Start()")
            capture_carte = not suffixe
            for rang, (_, _, libelle) in enumerate(route["choix"]):
                # Un choix de menu, ou une suite de clics sur les cartes (écran Ren'Py « carte » :
                # lieu, sous-carte ou retour à la carte parente).
                clics = [("carte", texte) for texte in _clics_textes(projet, libelle, textes)] \
                    if isinstance(libelle, list) else [("choice", textes.get(libelle, libelle))]
                for etape, (ecran, texte) in enumerate(clics, 1):
                    # Pause : un clic pendant la transition d'apparition du menu serait perdu ; la
                    # carte remplace aussi la boîte de dialogue (fondu), d'où une pause plus longue.
                    # Entre deux clics sur les cartes, l'écran « carte » est déjà là : pas d'« advance »
                    # (son clic pourrait tomber sur un bouton de la carte), seulement une pause.
                    if ecran == "carte" and etape > 1:
                        lignes.append("    pause 1.0")
                    else:
                        lignes += [f'    advance until screen "{ecran}"', "    pause 0.5" if ecran == "choice" else "    pause 1.0"]
                    if suffixe and numero == 1 and rang == 0 and ecran == "choice":
                        lignes.append(f'    screenshot "renpy_{code}.png"')
                    if capture_carte and ecran == "carte":
                        # Premier passage par les cartes de chaque route : une capture avant chaque clic
                        # (carte, puis sous-carte).
                        lignes.append(f'    screenshot "renpy_carte_{numero:02d}_{etape}.png"')
                    # Le bouton est activé par son texte (focus puis Entrée, game/tests_outils.rpy) : la
                    # souris simulée de Ren'Py 8.5 clique à côté quand la fenêtre est mise à l'échelle.
                    lignes += [f"    run Function(tests_viser, {_chaine(texte)})", "    pause 0.5"]
                    if ecran == "choice":
                        lignes.append('    pause until not screen "choice"')
                if isinstance(libelle, list):
                    capture_carte = False
            lignes += ['    advance until screen "main_menu"',
                       f"    $ assert renpy.seen_label({fin}), {_chaine('fin attendue non atteinte : ' + route['fin'].lower())}"]
    labels = [sid.lower() for sid in projet.ordre() if projet.scenes[sid].get("galerie")]
    if labels:
        lignes += ["", "", "testcase galerie:", "    $ _test.timeout = 30.0", '    pause until screen "main_menu"']
        if plusieurs:
            lignes += [f"    run Language({_chaine(_nom_renpy(projet.langue_source))})", "    pause 0.5"]
        lignes += ["    run Start()", "    pause 0.5"]
        for label in labels:
            lignes += [f'    run Jump("{label}")', "    pause 0.5"]
        lignes += ["    run MainMenu(confirm=False)", "    pause 1.0", '    run ShowMenu("galerie")', "    pause 1.0",
                   '    screenshot "renpy_galerie.png"',
                   f"    $ assert len(galerie_entrees) == {len(labels)}, galerie_entrees",
                   '    $ assert all(renpy.seen_label(e["label"]) for e in galerie_entrees), galerie_entrees',
                   # Retour au menu principal, que le testcase suivant attend.
                   "    run Return()", "    pause 1.0"]
    fiches_personnages = projet.personnages_avec_jauges()
    if fiches_personnages:
        # L'écran « Personnages » lit les variables de la partie : ouvert depuis le menu de jeu.
        lignes += ["", "", "testcase personnages:", "    $ _test.timeout = 30.0", '    pause until screen "main_menu"']
        if plusieurs:
            lignes += [f"    run Language({_chaine(_nom_renpy(projet.langue_source))})", "    pause 0.5"]
        lignes += ["    run Start()", '    advance until screen "say"', "    pause 0.5",
                   '    run ShowMenu("personnages")', "    pause 1.0", '    screenshot "renpy_personnages.png"',
                   f"    $ assert [f['id'] for f in personnages_fiches] == {fiches_personnages!r}, personnages_fiches"]
        for nom, variable in projet.variables_personnages.items():
            lignes.append(f"    $ assert {nom} == {_litteral(variable['defaut'])}, {nom}")
        if len(fiches_personnages) > 1:
            # Onglet du deuxième personnage (les onglets portent les noms, traduits).
            lignes += [f'    run Function(tests_onglet, "personnages", "personnages_onglet", {_chaine(fiches_personnages[1])})',
                       "    pause 0.5", '    screenshot "renpy_personnages_2.png"']
        lignes += ["    run MainMenu(confirm=False)", "    pause 1.0"]
    temps = projet.temps
    if temps is not None:
        # Le temps démarre au créneau de « debut » et s'affiche pendant la partie.
        debut = projet.variables_temps
        lignes += ["", "", "testcase temps:", "    $ _test.timeout = 30.0", '    pause until screen "main_menu"']
        if plusieurs:
            lignes += [f"    run Language({_chaine(_nom_renpy(projet.langue_source))})", "    pause 0.5"]
        lignes += ["    run Start()", '    advance until screen "say"', "    pause 0.5", '    screenshot "renpy_temps.png"',
                   f"    $ assert moment == {_litteral(debut['moment']['defaut'])}, moment",
                   f"    $ assert temps_texte() == {_chaine(_texte_temps(projet))}, temps_texte()",
                   "    run MainMenu(confirm=False)", "    pause 1.0"]
    renommages = projet.renommages["variables"]
    if renommages:
        # Une sauvegarde qui contient les anciens noms doit reprendre leurs valeurs sous les nouveaux.
        lignes += ["", "", "testcase renommages:", "    $ _test.timeout = 30.0", '    pause until screen "main_menu"']
        if plusieurs:
            lignes += [f"    run Language({_chaine(_nom_renpy(projet.langue_source))})", "    pause 0.5"]
        lignes += ["    run Start()", '    advance until screen "say"', "    pause 0.5"]
        for numero, (ancien, _) in enumerate(renommages, 1):
            lignes.append(f"    $ setattr(store, {_chaine(ancien)}, 70 + {numero})")
        # Ren'Py sauvegarde l'état du début de l'instruction en cours : on avance d'un cran.
        lignes += ["    advance", '    advance until screen "say"', "    pause 0.5",
                   '    run FileSave("test_renommages", confirm=False)', "    pause 0.5",
                   '    run FileLoad("test_renommages", confirm=False)', "    pause 1.0"]
        for numero, (ancien, nouveau) in enumerate(renommages, 1):
            lignes += [f"    $ assert {nouveau} == 70 + {numero}, {nouveau}",
                       f"    $ assert not hasattr(store, {_chaine(ancien)}), {_chaine(ancien)}"]
        lignes += ["    run MainMenu(confirm=False)", "    pause 1.0"]
    return "\n".join(lignes) + "\n"


def _texte_temps(projet: Projet) -> str:
    """Texte du temps affiché au départ (même format dans les deux moteurs : « Jour 1 · matin »)."""
    temps, debut = projet.temps, projet.variables_temps
    morceaux = []
    if temps["date"] is not None:
        date = temps["date"]
        morceaux.append(f"{debut['jour_semaine']['defaut']} {date.day} {MOIS_NOMS[date.month - 1]} {date.year}")
    else:
        if temps["jours"]:
            morceaux.append(f"Jour {debut['jour']['defaut']}")
        if temps["semaine"]:
            morceaux.append(debut["jour_semaine"]["defaut"])
    morceaux.append(debut["moment"]["defaut"])
    return " · ".join(morceaux)


def controle_godot(racine: Path) -> bool:
    """Fait relire le script généré par le compilateur Godot (tools/routes.gd)."""
    godot = shutil.which("godot") or shutil.which("godot4")
    if godot is None:
        print("(godot introuvable : relecture par le compilateur Godot ignorée)")
        return True
    resultat = subprocess.run([godot, "--headless", "--path", str(racine), "--script", "res://tools/routes.gd"],
                              capture_output=True, text=True, timeout=600)
    lignes = [ligne for ligne in (resultat.stdout + resultat.stderr).splitlines()
              if ligne.strip() and not ligne.startswith("Godot Engine")]
    print("Relecture par le compilateur Godot :")
    for ligne in lignes:
        print(f"  {ligne}")
    return resultat.returncode == 0


# --- Traductions ------------------------------------------------------------------------------
#
# Les fiches sont écrites dans la langue source. Chaque traduction a son fichier
# contenu/traductions/<code>.yaml : les répliques y sont repérées par leur identifiant
# (clause « id » du script), les noms, choix et titres de galerie par leur texte, comme
# dans Ren'Py. generer en tire game/tl/<langue>/story/*.rpy, lu par Ren'Py et par Godot.

def _nom_renpy(code: str) -> str:
    return LANGUES.get(code, (code, code))[0]


def _langues_json(projet: Projet) -> str:
    """Langues du jeu, lues par game/langues.rpy (Ren'Py) et par le lecteur Godot."""
    def decrire(code):
        nom_renpy, nom = LANGUES.get(code, (code, code))
        return {"code": code, "renpy": nom_renpy, "nom": nom}

    donnees = {"_genere_par": MARQUEUR, "source": decrire(projet.langue_source),
               "traductions": [decrire(code) for code in projet.langues_cibles]}
    return json.dumps(donnees, ensure_ascii=False, indent=2) + "\n"


def repliques(projet: Projet) -> list:
    """Toutes les répliques du script (narration, personnages, questions des menus), dans
    l'ordre, avec l'identifiant qui les relie à leurs traductions."""
    resultat = []
    for sid in projet.ordre():
        script = _Script(projet, sid, avec_ids=True)
        _rpy_scene(script)
        resultat += script.repliques
    return resultat


def textes_a_traduire(projet: Projet) -> dict:
    """Textes traduits comme des chaînes Ren'Py (« translate strings ») : noms des
    personnages, choix des menus et titres de la galerie. {texte : groupe}, dans l'ordre."""
    resultat: dict = {}
    for personnage in projet.personnages.values():
        resultat.setdefault(str(personnage["nom"]), "Noms des personnages")
    for variable in projet.variables_personnages.values():
        if variable["nom"]:
            resultat.setdefault(variable["nom"], "Jauges, compétences et relations")
    for variable in projet.variables_personnages.values():
        for _, palier in variable["paliers"]:
            resultat.setdefault(palier, "Paliers des jauges")
    temps = projet.temps
    if temps is not None:
        for nom in temps["creneaux"] + temps["semaine"] + (list(MOIS_NOMS) if temps["date"] is not None else []):
            resultat.setdefault(nom, "Temps : créneaux, jours et mois")
    for cid, carte in projet.cartes.items():
        resultat.setdefault(projet.titre_carte(cid), "Titres des cartes")
    for cid, carte in projet.cartes.items():
        for entree in _liste(_dict(carte).get("lieux")):
            if isinstance(entree, dict) and entree.get("lieu") in projet.lieux:
                resultat.setdefault(projet.nom_lieu(entree["lieu"]), "Noms des lieux (cartes)")
    for sid in projet.ordre():
        fiche = projet.scenes[sid]
        groupe = f"{sid} — {fiche.get('titre', '')}"
        for option in options_de(fiche)[1]:
            resultat.setdefault(str(option["libelle"]), f"{groupe} : choix")
        if fiche.get("galerie"):
            resultat.setdefault(_titre_galerie(sid, fiche), f"{groupe} : galerie")
    return resultat


def traductions_de(projet: Projet, code: str) -> tuple[dict, dict]:
    """Traductions faites d'une langue : ({id de réplique : texte}, {texte source : texte})."""
    donnees = _dict(projet.traductions.get(code))
    lignes = {str(rid): str(entree["texte"]) for rid, entree in _dict(donnees.get("repliques")).items()
              if isinstance(entree, dict) and _rempli(entree.get("texte"))}
    textes = {str(entree["source"]): str(entree["texte"]) for entree in _liste(donnees.get("textes"))
              if isinstance(entree, dict) and "source" in entree and _rempli(entree.get("texte"))}
    return lignes, textes


def _rempli(valeur) -> bool:
    return isinstance(valeur, (str, int, float)) and not isinstance(valeur, bool) and bool(str(valeur).strip())


def _label_de(rid: str) -> str:
    return re.sub(r"_[0-9a-f]{8}(?:_\d+)?$", "", rid)


def _verifier_traductions(projet: Projet, rapport: Rapport):
    """Fichiers de traduction : structure, textes à traduire ou à revoir, variables et
    balises conservées, choix d'un même menu toujours distincts une fois traduits."""
    if not projet.langues_cibles:
        return
    actuelles = repliques(projet)
    ids = {replique.rid for replique in actuelles}
    sources = textes_a_traduire(projet)
    for code in projet.langues_cibles:
        ou = f"{DOSSIER_TRADUCTIONS}/{code}.yaml"
        donnees = projet.traductions.get(code)
        if donnees is None:
            rapport.avertir(ou, f"absent ou vide : lancez tools/fiches.py traduire {code}")
            continue
        if not isinstance(donnees, dict):
            rapport.erreur(ou, "« repliques » et « textes » attendus")
            continue
        for cle in sorted(set(map(str, donnees)) - CHAMPS_TRADUCTION):
            rapport.erreur(ou, f"champ inconnu « {cle} » (champs possibles : {', '.join(sorted(CHAMPS_TRADUCTION))})")
        entrees = donnees.get("repliques") or {}
        if not isinstance(entrees, dict):
            rapport.erreur(ou, "« repliques » : identifiant → {qui, source, texte} attendu")
            entrees = {}
        a_traduire = a_revoir = 0
        for replique in actuelles:
            entree = entrees.get(replique.rid)
            ici = f"{ou}, {replique.rid}"
            if entree is not None and (not isinstance(entree, dict) or set(entree) - {"qui", "source", "texte", "a_revoir"}):
                rapport.erreur(ici, "attendu : qui, source, texte (et a_revoir)")
                continue
            if entree is None or not _rempli(entree.get("texte")):
                a_traduire += 1
                continue
            if entree.get("a_revoir") or entree.get("source", replique.texte) != replique.texte:
                a_revoir += 1
            _verifier_texte_traduit(projet, rapport, ici, replique.texte, entree["texte"])
        obsoletes = len(set(map(str, entrees)) - ids)
        if donnees.get("textes") is not None and not isinstance(donnees["textes"], list):
            rapport.erreur(ou, "« textes » : liste de - source: … / texte: … attendue")
        vus, traduits = set(), {}
        for rang, entree in enumerate(_liste(donnees.get("textes")), 1):
            ici = f"{ou}, textes[{rang}]"
            if not isinstance(entree, dict) or "source" not in entree or set(entree) - {"source", "texte", "a_revoir"}:
                rapport.erreur(ici, "attendu : - source: … / texte: … (et a_revoir)")
                continue
            source = str(entree["source"])
            if source in vus:
                rapport.erreur(ici, f"« {source} » est traduit deux fois")
                continue
            vus.add(source)
            if _rempli(entree.get("texte")):
                traduits[source] = entree
        for source in sources:
            entree = traduits.get(source)
            if entree is None:
                a_traduire += 1
                continue
            if entree.get("a_revoir"):
                a_revoir += 1
            _verifier_texte_traduit(projet, rapport, f"{ou}, texte « {source} »", source, entree["texte"])
        obsoletes += len(vus - set(sources))
        groupes = [(sid, "choix du même menu", "choix", [str(option["libelle"]) for option in options_de(projet.scenes[sid])[1]])
                   for sid in projet.ordre()]
        for cid, carte in projet.cartes.items():
            noms = dict.fromkeys(projet.nom_lieu(entree["lieu"]) for entree in _liste(_dict(carte).get("lieux"))
                                 if isinstance(entree, dict) and entree.get("lieu") in projet.lieux)
            groupes.append((f"carte « {cid} »", "lieux de la même carte", "lieu", list(noms)))
        for ou_groupe, quoi, cible, libelles in groupes:
            affiches = [str(traduits[libelle]["texte"]) if libelle in traduits else libelle for libelle in libelles]
            for double in sorted({libelle for libelle in affiches if affiches.count(libelle) > 1}):
                rapport.erreur(ou, f"{ou_groupe} : deux {quoi} s'affichent « {double} »")
            for court in affiches:
                for long in affiches:
                    if court != long and court in long:
                        rapport.avertir(ou, f"{ou_groupe} : « {court} » est contenu dans « {long} » : "
                                            f"les tests Ren'Py risquent de cliquer le mauvais {cible}")
        if a_traduire:
            rapport.avertir(ou, f"{a_traduire} réplique(s) ou texte(s) à traduire (le jeu affiche alors le texte "
                                f"d'origine) : lancez tools/fiches.py traduire {code}, puis complétez « texte »")
        if a_revoir:
            rapport.avertir(ou, f"{a_revoir} traduction(s) à revoir : le texte d'origine a changé (« a_revoir »)")
        if obsoletes:
            rapport.avertir(ou, f"{obsoletes} entrée(s) ne correspondent plus au script : "
                                f"lancez tools/fiches.py traduire {code}")


def _verifier_texte_traduit(projet: Projet, rapport: Rapport, ici: str, source: str, traduction):
    traduction, source = str(traduction), str(source)
    noms = INTERPOLATION.findall(traduction.replace("[[", ""))
    for nom in noms:
        if nom not in projet.variables_toutes:
            rapport.erreur(ici, f"[{nom}] : variable inconnue dans la traduction")
    if set(noms) != set(INTERPOLATION.findall(source.replace("[[", ""))):
        rapport.avertir(ici, "les [variables] de la traduction diffèrent de celles du texte d'origine")
    if sorted(BALISE.findall(traduction.replace("{{", ""))) != sorted(BALISE.findall(source.replace("{{", ""))):
        rapport.avertir(ici, "les balises {…} de la traduction diffèrent de celles du texte d'origine")


def _rpy_traduction(projet: Projet, code: str) -> dict:
    """Traductions Ren'Py d'une langue : un bloc « translate » par réplique traduite, dans
    game/tl/<langue>/story/chapitre_XX.rpy, et les textes dans textes.rpy."""
    nom_renpy, nom = LANGUES[code]
    lignes_traduites, textes_traduits = traductions_de(projet, code)
    source = f"{DOSSIER_TRADUCTIONS}/{code}.yaml"
    fichiers = {}
    par_chapitre: dict = {}
    for replique in repliques(projet):
        if replique.rid in lignes_traduites:
            par_chapitre.setdefault(_chapitre(replique.sid, projet.scenes[replique.sid]), []).append(replique)
    for chapitre, liste in sorted(par_chapitre.items()):
        lignes = [f"# {MARQUEUR}", f"# Traduction {code} ({nom}) du chapitre {chapitre} : {source}."]
        scene = None
        for replique in liste:
            if replique.sid != scene:
                scene = replique.sid
                lignes += ["", f"# {scene} — {projet.scenes[scene].get('titre', '')}"]
            qui = f"{replique.qui} " if replique.qui else ""
            lignes += ["", f"translate {nom_renpy} {replique.rid}:", "",
                       f"    # {qui}{_chaine(replique.texte)}", f"    {qui}{_chaine(lignes_traduites[replique.rid])}"]
        fichiers[f"game/tl/{nom_renpy}/story/chapitre_{chapitre}.rpy"] = "\n".join(lignes) + "\n"
    paires = [(texte, textes_traduits[texte]) for texte in textes_a_traduire(projet) if texte in textes_traduits]
    if paires:
        lignes = [f"# {MARQUEUR}", f"# Traduction {code} ({nom}) des noms, des choix et des titres de la galerie : {source}.",
                  "", f"translate {nom_renpy} strings:"]
        for original, traduction in paires:
            lignes += ["", f"    old {_chaine(original)}", f"    new {_chaine(traduction)}"]
        fichiers[f"game/tl/{nom_renpy}/story/textes.rpy"] = "\n".join(lignes) + "\n"
    return fichiers


def traduire(projet: Projet, code: str) -> tuple[str, dict]:
    """Contenu à jour de contenu/traductions/<code>.yaml, et son bilan. Ajoute les nouvelles
    répliques et les nouveaux textes, garde les traductions faites. Quand un texte d'origine
    change, sa traduction est reprise et marquée « a_revoir » (avec l'ancien texte) ; les
    traductions qui ne servent plus passent dans « obsoletes »."""
    donnees = _dict(projet.traductions.get(code))
    anciennes = {str(rid): entree for rid, entree in _dict(donnees.get("repliques")).items() if isinstance(entree, dict)}
    anciens_textes = {str(entree["source"]): entree for entree in _liste(donnees.get("textes"))
                      if isinstance(entree, dict) and "source" in entree}
    anciennes_obsoletes = [entree for entree in _liste(donnees.get("obsoletes"))
                           if isinstance(entree, dict) and _rempli(entree.get("texte"))]
    bilan = {"nouveaux": 0, "repris": 0}

    actuelles = repliques(projet)
    ids = {replique.rid for replique in actuelles}
    reserve = [{"id": rid, "source": str(entree.get("source", "")), "texte": entree["texte"]}
               for rid, entree in anciennes.items() if rid not in ids and _rempli(entree.get("texte"))]
    reserve += [entree for entree in anciennes_obsoletes if "id" in entree]
    lignes_repliques = []
    for replique in actuelles:
        entree = anciennes.get(replique.rid)
        texte, a_revoir = "", None
        if entree is not None and _rempli(entree.get("texte")):
            texte = entree["texte"]
            ancienne_source = entree.get("source", replique.texte)
            a_revoir = entree.get("a_revoir") or (ancienne_source if ancienne_source != replique.texte else None)
        else:
            reprise = _reprendre(reserve, replique.texte, _label_de(replique.rid))
            if reprise is not None:
                texte = reprise["texte"]
                a_revoir = reprise["source"] if reprise["source"] != replique.texte else None
                bilan["repris"] += 1
            elif entree is None:
                bilan["nouveaux"] += 1
        lignes_repliques.append((replique, texte, a_revoir))

    actuels = textes_a_traduire(projet)
    reserve_textes = [{"source": source, "texte": entree["texte"]} for source, entree in anciens_textes.items()
                      if source not in actuels and _rempli(entree.get("texte"))]
    reserve_textes += [entree for entree in anciennes_obsoletes if "id" not in entree]
    entrees_textes = []
    for source, groupe in actuels.items():
        entree = anciens_textes.get(source)
        texte, a_revoir = "", None
        if entree is not None and _rempli(entree.get("texte")):
            texte, a_revoir = entree["texte"], entree.get("a_revoir")
        else:
            reprise = _reprendre(reserve_textes, source)
            if reprise is not None:
                texte = reprise["texte"]
                a_revoir = reprise["source"] if reprise["source"] != source else None
                bilan["repris"] += 1
            elif entree is None:
                bilan["nouveaux"] += 1
        entrees_textes.append((source, groupe, texte, a_revoir))

    obsoletes = reserve + reserve_textes
    tous = [(texte, a_revoir) for _, texte, a_revoir in lignes_repliques]
    tous += [(texte, a_revoir) for _, _, texte, a_revoir in entrees_textes]
    bilan.update({"repliques": len(lignes_repliques), "textes": len(entrees_textes),
                  "a_traduire": sum(1 for texte, _ in tous if not _rempli(texte)),
                  "a_revoir": sum(1 for texte, a_revoir in tous if _rempli(texte) and a_revoir),
                  "obsoletes": len(obsoletes)})
    return _fichier_traduction(projet, code, lignes_repliques, entrees_textes, obsoletes), bilan


def _reprendre(reserve: list, texte: str, label: str | None = None):
    """Retire de la réserve et renvoie la traduction dont le texte d'origine ressemble le
    plus à texte (identique d'abord, puis même scène, puis la plus proche), ou None."""
    candidates = []
    for candidate in reserve:
        ratio = difflib.SequenceMatcher(None, str(candidate.get("source", "")), texte).ratio()
        if ratio >= SEUIL_REPRISE:
            meme_scene = label is not None and _label_de(str(candidate.get("id", ""))) == label
            candidates.append(((ratio == 1.0, meme_scene, ratio), candidate))
    if not candidates:
        return None
    choisie = max(candidates, key=lambda paire: paire[0])[1]
    reserve.remove(choisie)
    return choisie


def _fichier_traduction(projet: Projet, code: str, lignes_repliques: list, entrees_textes: list, obsoletes: list) -> str:
    nom = LANGUES[code][1]
    titre = projet.bible.get("titre")
    lignes = [f"# Traduction « {code} » ({nom}){f' de « {titre} »' if titre else ''}. "
              f"Langue des fiches : {projet.langue_source}.",
              "#",
              "# Complétez « texte ». Un texte vide n'est pas encore traduit : le jeu affiche l'original.",
              "# « source » rappelle le texte d'origine : ne le modifiez pas.",
              "# « a_revoir » : le texte d'origine a changé (ancienne version indiquée). Vérifiez la",
              "# traduction, puis supprimez la ligne « a_revoir ».",
              "# Gardez tels quels les [variables] et les balises {i}…{/i}.",
              f"# Après une modification des fiches : .venv/bin/python tools/fiches.py traduire {code}",
              "", "repliques:" if lignes_repliques else "repliques: {}"]
    scene = None
    for replique, texte, a_revoir in lignes_repliques:
        if replique.sid != scene:
            scene = replique.sid
            lignes += ["", f"  # {scene} — {projet.scenes[scene].get('titre', '')}"]
        lignes += [f"  {replique.rid}:", f"    qui: {replique.qui or 'narration'}", f"    source: {_chaine(replique.texte)}"]
        if a_revoir:
            lignes.append(f"    a_revoir: {_valeur_yaml(a_revoir)}")
        lignes.append(f"    texte: {_valeur_yaml(texte)}")
    lignes += ["", "textes:" if entrees_textes else "textes: []"]
    groupe_courant = None
    for source, groupe, texte, a_revoir in entrees_textes:
        if groupe != groupe_courant:
            groupe_courant = groupe
            lignes += ["", f"  # {groupe}"]
        lignes.append(f"  - source: {_chaine(source)}")
        if a_revoir:
            lignes.append(f"    a_revoir: {_valeur_yaml(a_revoir)}")
        lignes.append(f"    texte: {_valeur_yaml(texte)}")
    if obsoletes:
        lignes += ["", "# Traductions qui ne servent plus (texte d'origine supprimé ou trop changé) :",
                   "# réutilisez-les ou supprimez-les.", "obsoletes:"]
        for entree in obsoletes:
            cles = [cle for cle in ("id", "source", "texte") if cle in entree]
            for rang, cle in enumerate(cles):
                lignes.append(f"  {'- ' if rang == 0 else '  '}{cle}: {_valeur_yaml(entree[cle])}")
    return "\n".join(lignes) + "\n"


def _valeur_yaml(valeur) -> str:
    if isinstance(valeur, bool):
        return "true" if valeur else "false"
    return _chaine("" if valeur is None else str(valeur))


def importer_traductions(projet: Projet, code: str, texte: str) -> int:
    """Reprend les traductions d'un YAML au format du fichier de traduction (réponse d'un
    traducteur ou d'une IA au paquet de traduction). Seuls les « texte » non vides des
    répliques et des textes du jeu sont repris ; renvoie leur nombre."""
    reponse = yaml.safe_load(re.sub(r"^\s*```\w*\s*$", "", texte, flags=re.M))
    if not isinstance(reponse, dict):
        raise ValueError("YAML attendu, avec « repliques » et/ou « textes »")
    donnees = dict(_dict(projet.traductions.get(code)))
    actuelles = {replique.rid: replique for replique in repliques(projet)}
    entrees = {str(rid): dict(entree) for rid, entree in _dict(donnees.get("repliques")).items() if isinstance(entree, dict)}
    repris = 0
    for rid, entree in _dict(reponse.get("repliques")).items():
        replique = actuelles.get(str(rid))
        if replique is None or not isinstance(entree, dict) or not _rempli(entree.get("texte")):
            continue
        entrees[replique.rid] = {"qui": replique.qui or "narration", "source": replique.texte, "texte": str(entree["texte"])}
        repris += 1
    sources = textes_a_traduire(projet)
    textes = [dict(entree) for entree in _liste(donnees.get("textes")) if isinstance(entree, dict)]
    index = {str(entree.get("source")): entree for entree in textes}
    for entree in _liste(reponse.get("textes")):
        if not isinstance(entree, dict) or str(entree.get("source")) not in sources or not _rempli(entree.get("texte")):
            continue
        cible = index.setdefault(str(entree["source"]), {"source": str(entree["source"])})
        if cible not in textes:
            textes.append(cible)
        cible["texte"] = str(entree["texte"])
        cible.pop("a_revoir", None)
        repris += 1
    donnees["repliques"], donnees["textes"] = entrees, textes
    projet.traductions[code] = donnees
    return repris


def paquet_traduction(projet: Projet, code: str, donnees: dict) -> str:
    """Paquet pour un traducteur ou une IA : consignes, contexte du jeu, glossaire et
    entrées à traduire (vides ou à revoir), au format du fichier de traduction."""
    nom = LANGUES[code][1]
    nom_source = LANGUES.get(projet.langue_source, (None, projet.langue_source))[1]
    a_faire = {rid: entree for rid, entree in _dict(donnees.get("repliques")).items()
               if isinstance(entree, dict) and (not _rempli(entree.get("texte")) or entree.get("a_revoir"))}
    textes = [entree for entree in _liste(donnees.get("textes")) if isinstance(entree, dict)]
    textes_a_faire = [entree for entree in textes if not _rempli(entree.get("texte")) or entree.get("a_revoir")]
    glossaire = [entree for entree in textes if entree not in textes_a_faire]
    lignes = [f"# Paquet de traduction — {nom} ({code})", "",
              "## Consigne", "",
              f"Traduis les entrées de la section « À traduire ». Langue d'origine : {nom_source} "
              f"({projet.langue_source}) ; langue cible : {nom} ({code}). C'est un jeu narratif : garde le ton, "
              "le rythme et la voix de chaque personnage.",
              "",
              "- Remplis seulement « texte » : ne change ni les identifiants, ni « source », ni « qui ».",
              "- Garde tels quels les [variables] et les balises {i}…{/i}, {b}…{/b}.",
              "- « a_revoir » donne l'ancien texte d'origine, « texte » sa traduction : adapte-la au nouveau texte "
              "d'origine (« source »).",
              "- Les choix des menus restent courts et tous différents dans un même menu.",
              "- Réponds uniquement par le bloc YAML complété.",
              "", f"Pour reprendre la réponse : enregistrez-la dans un fichier, puis "
              f"`.venv/bin/python tools/fiches.py traduire {code} --importer reponse.yaml`.", ""]
    if projet.bible.get("synopsis"):
        lignes += ["## Synopsis", "", str(projet.bible["synopsis"]).strip(), ""]
    lignes += ["## Personnages", ""]
    for pid, personnage in projet.personnages.items():
        details = [str(personnage.get(cle)) for cle in ("role", "personnalite") if personnage.get(cle)]
        lignes.append(f"- `{pid}` : {personnage.get('nom')}" + (f" — {' ; '.join(details)}" if details else ""))
    regles = _liste(projet.bible.get("regles_editoriales"))
    if regles:
        lignes += ["", "## Règles éditoriales", ""] + [f"- {regle}" for regle in regles]
    if glossaire:
        lignes += ["", "## Glossaire (déjà traduit)", ""]
        lignes += [f"- {entree.get('source')} → {entree.get('texte')}" for entree in glossaire]
    lignes += ["", "## À traduire", ""]
    if not a_faire and not textes_a_faire:
        return "\n".join(lignes + ["Tout est traduit.", ""])
    bloc = ["repliques:" if a_faire else "repliques: {}"]
    for rid, entree in a_faire.items():
        bloc += [f"  {rid}:", f"    qui: {entree.get('qui', 'narration')}", f"    source: {_valeur_yaml(entree.get('source'))}"]
        if entree.get("a_revoir"):
            bloc.append(f"    a_revoir: {_valeur_yaml(entree['a_revoir'])}")
        bloc.append(f"    texte: {_valeur_yaml(entree.get('texte'))}")
    bloc.append("textes:" if textes_a_faire else "textes: []")
    for entree in textes_a_faire:
        bloc.append(f"  - source: {_valeur_yaml(entree.get('source'))}")
        if entree.get("a_revoir"):
            bloc.append(f"    a_revoir: {_valeur_yaml(entree['a_revoir'])}")
        bloc.append(f"    texte: {_valeur_yaml(entree.get('texte'))}")
    return "\n".join(lignes + ["```yaml"] + bloc + ["```", ""])


# --- Médias : inventaire, production, provisoires -------------------------------------------

def tous_les_elements(projet: Projet, fiche: dict):
    """Tous les éléments d'une fiche, y compris dans les si, la question et les options."""
    question, options = options_de(fiche)
    listes = [fiche.get("contenu")] + ([[question]] if question is not None else [])
    listes += [option.get("contenu") for option in options if isinstance(option, dict)]
    a_parcourir = [element for liste in listes for element in _liste(liste)]
    while a_parcourir:
        element = a_parcourir.pop(0)
        yield element
        if cle_element(element, projet) == "si":
            a_parcourir += _liste(element.get("alors")) + _liste(element.get("sinon"))
            for branche in _liste(element.get("sinon_si")):
                a_parcourir += _liste(branche.get("alors"))


def inventaire(projet: Projet) -> tuple[dict, dict]:
    """Images et vidéos utilisées : {nom: {scenes: [...], usages: [...]}}."""
    images: dict = {}
    videos: dict = {}

    def noter(table, nom, sid, usage):
        entree = table.setdefault(nom, {"scenes": [], "usages": []})
        if sid not in entree["scenes"]:
            entree["scenes"].append(sid)
        if usage not in entree["usages"]:
            entree["usages"].append(usage)

    for sid in projet.ordre():
        fiche = projet.scenes[sid]
        for element in tous_les_elements(projet, fiche):
            cle = cle_element(element, projet)
            if cle == "decor" and element["decor"]:
                decors = projet.decors_par_creneau(element["decor"])
                for image in (decors.values() if decors else [element["decor"]]):
                    noter(images, image, sid, "décor")
            elif cle == "montrer":
                noter(images, element["montrer"], sid, "personnage")
            elif cle == "video":
                noter(videos, element["video"], sid, "scène")
        galerie = _dict(fiche.get("galerie"))
        for nom in _liste(galerie.get("images")):
            noter(images, nom, sid, "galerie")
        if galerie.get("vignette"):
            noter(images, galerie["vignette"], sid, "vignette de galerie")
        if galerie.get("video"):
            noter(videos, galerie["video"], sid, "galerie")
    for cid, carte in projet.cartes.items():
        if not isinstance(carte, dict):
            continue
        if isinstance(carte.get("image"), str) and carte["image"]:
            noter(images, carte["image"], f"carte {cid}", "carte")
        for entree in _liste(carte.get("lieux")):
            icone = _dict(projet.lieux.get(_dict(entree).get("lieu"))).get("icone")
            if isinstance(icone, str) and icone:
                noter(images, icone, f"carte {cid}", "icône de lieu")
    for pid, fiche in projet.personnages.items():
        if isinstance(fiche, dict) and isinstance(fiche.get("avatar"), str) and fiche["avatar"] and fiche.get("presence") is not None:
            noter(images, fiche["avatar"], "cartes", "avatar")
    return images, videos


def _lieux_des_cartes(projet: Projet, image: str) -> list:
    """Lieux placés sur les cartes qui utilisent cette image : [(nom, x, y)]."""
    resultat = []
    for carte in projet.cartes.values():
        if not isinstance(carte, dict) or carte.get("image") != image:
            continue
        for entree in _liste(carte.get("lieux")):
            if isinstance(entree, dict) and _est_nombre(entree.get("x")) and _est_nombre(entree.get("y")):
                resultat.append((projet.nom_lieu(entree.get("lieu")), entree["x"], entree["y"]))
    return resultat


def _index_images(racine: Path) -> tuple[dict, dict]:
    """Images présentes : (définitives, provisoires), par nom Ren'Py en minuscules."""
    definitives, provisoires = {}, {}
    dossier = racine / "game" / "images"
    if dossier.is_dir():
        for chemin in dossier.rglob("*"):
            if chemin.suffix.lower() in EXTENSIONS_IMAGES:
                cible = provisoires if (racine / DOSSIER_PROVISOIRES) in chemin.parents else definitives
                cible[chemin.stem.lower()] = chemin.relative_to(racine).as_posix()
    return definitives, provisoires


def _videos_provisoires(racine: Path) -> dict:
    """Vidéos provisoires : {chemin relatif à game/ : empreinte du fichier créé}."""
    liste = racine / LISTE_VIDEOS_PROVISOIRES
    if not liste.exists():
        return {}
    resultat = {}
    for ligne in liste.read_text(encoding="utf-8").splitlines():
        if ligne.strip() and not ligne.startswith("#"):
            chemin, _, empreinte = ligne.rpartition(" ")
            resultat[chemin] = empreinte
    return resultat


def _etat_video(racine: Path, relatif: str, provisoires: dict) -> tuple[str, str]:
    webm = racine / "game" / relatif
    ogv = webm.with_suffix(".ogv")
    if not webm.exists():
        etat_webm = "manquante"
    elif relatif in provisoires and _empreinte(webm) == provisoires[relatif]:
        etat_webm = "provisoire"
    else:
        etat_webm = "définitive"
    if not ogv.exists():
        etat_ogv = "manquant"
    elif webm.exists() and ogv.stat().st_mtime < webm.stat().st_mtime:
        etat_ogv = "à reconvertir"
    else:
        etat_ogv = "à jour"
    return etat_webm, etat_ogv


def _etats_medias(projet: Projet) -> tuple[dict, dict, dict, dict]:
    """Images et vidéos utilisées, avec leur état : (images, vidéos, {image : (état, fichier)},
    {vidéo : (état du WebM, état de l'OGV)})."""
    images, videos = inventaire(projet)
    definitives, provisoires_ = _index_images(projet.racine)
    liste_provisoires = _videos_provisoires(projet.racine)
    etats_images = {}
    for nom in images:
        cle = nom.lower()
        etats_images[nom] = ("définitive", definitives[cle]) if cle in definitives else \
            ("provisoire", provisoires_[cle]) if cle in provisoires_ else ("manquante", "")
    etats_videos = {relatif: _etat_video(projet.racine, relatif, liste_provisoires) for relatif in videos}
    return images, videos, etats_images, etats_videos


def production(projet: Projet) -> tuple[str, str]:
    """Renvoie (markdown, résumé) de la liste des images et vidéos à produire."""
    images, videos, etats_images, etats_videos = _etats_medias(projet)

    def compter(etats, valeur):
        return sum(1 for etat in etats if etat == valeur)

    etats_i = [etat for etat, _ in etats_images.values()]
    etats_v = [etat for etat, _ in etats_videos.values()]
    resume = (f"Images : {len(images)} utilisées — {compter(etats_i, 'définitive')} définitives, "
              f"{compter(etats_i, 'provisoire')} provisoires, {compter(etats_i, 'manquante')} manquantes. "
              f"Vidéos : {len(videos)} utilisées — {compter(etats_v, 'définitive')} définitives, "
              f"{compter(etats_v, 'provisoire')} provisoires, {compter(etats_v, 'manquante')} manquantes ; "
              f"OGV à jour : {sum(1 for _, ogv in etats_videos.values() if ogv == 'à jour')}/{len(videos)}.")
    lignes = ["# Liste de production", "", f"Généré par `tools/fiches.py production`. {resume}", "",
              "« provisoire » : image ou vidéo de remplacement créée par `tools/fiches.py provisoires`, à produire.", "",
              "## Images", "", "| Image | Usage | Scènes | État | Fichier |", "|---|---|---|---|---|"]
    for nom in sorted(images):
        etat, fichier = etats_images[nom]
        etat_affiche = etat if etat == "définitive" else f"**{etat}**"
        lignes.append(f"| {nom} | {', '.join(images[nom]['usages'])} | {', '.join(images[nom]['scenes'])} | "
                      f"{etat_affiche} | {f'`{fichier}`' if fichier else ''} |")
    lignes += ["", "## Vidéos", "", "| Vidéo | Scènes | WebM (Ren'Py) | OGV (Godot) |", "|---|---|---|---|"]
    for relatif in sorted(videos):
        etat_webm, etat_ogv = etats_videos[relatif]
        lignes.append(f"| {relatif} | {', '.join(videos[relatif]['scenes'])} | "
                      f"{etat_webm if etat_webm == 'définitive' else f'**{etat_webm}**'} | "
                      f"{etat_ogv if etat_ogv == 'à jour' else f'**{etat_ogv}**'} |")
    declarees = {nom for p in projet.personnages.values() if isinstance(p, dict) for nom in _liste(p.get("images"))}
    declarees |= {nom for lieu in projet.lieux.values() if isinstance(lieu, dict) for nom in _decors_de(lieu)}
    declarees |= {carte["image"] for carte in projet.cartes.values() if isinstance(carte, dict) and carte.get("image")}
    declarees |= {lieu["icone"] for lieu in projet.lieux.values() if isinstance(lieu, dict) and lieu.get("icone")}
    declarees |= {p["avatar"] for p in projet.personnages.values() if isinstance(p, dict) and p.get("avatar")}
    inutilisees = sorted(declarees - set(images))
    non_declarees = sorted(set(images) - declarees)
    lignes += ["", "## Cohérence avec la bible", "",
               f"- Déclarées dans la bible mais jamais utilisées : {', '.join(inutilisees) or 'aucune'}.",
               f"- Utilisées mais absentes de la bible (personnages.images, lieux.decors) : {', '.join(non_declarees) or 'aucune'}."]
    return "\n".join(lignes) + "\n", resume


def provisoires(projet: Projet) -> tuple[list, list]:
    """Crée une image ou une vidéo provisoire pour chaque média manquant ; retire les
    images provisoires remplacées par une définitive ou devenues inutiles."""
    images, videos = inventaire(projet)
    racine = projet.racine
    definitives, existantes = _index_images(racine)
    utiles = {nom.lower() for nom in images}
    crees, retires = [], []
    for cle, relatif in sorted(existantes.items()):
        if cle in definitives or cle not in utiles:
            (racine / relatif).unlink()
            retires.append(relatif)
            del existantes[cle]
    dossier = racine / DOSSIER_PROVISOIRES
    for nom, entree in sorted(images.items()):
        if nom.lower() in definitives or nom.lower() in existantes:
            continue
        dossier.mkdir(parents=True, exist_ok=True)
        chemin = dossier / f"{nom}.png"
        if "personnage" in entree["usages"]:
            _dessiner_personnage(nom, chemin)
        elif "carte" in entree["usages"]:
            _dessiner_carte(nom, chemin, _lieux_des_cartes(projet, nom))
        elif "icône de lieu" in entree["usages"]:
            _dessiner_icone(nom, chemin)
        elif "avatar" in entree["usages"]:
            _dessiner_avatar(nom, chemin, _personnage_de_l_avatar(projet, nom))
        else:
            _dessiner_decor(nom, chemin)
        crees.append(chemin.relative_to(racine).as_posix())
    liste = _videos_provisoires(racine)
    videos_creees = []
    for relatif in sorted(videos):
        webm = racine / "game" / relatif
        if webm.exists():
            if relatif in liste and _empreinte(webm) != liste[relatif]:
                del liste[relatif]  # remplacée par la vidéo définitive
            continue
        if shutil.which("ffmpeg") is None:
            print(f"(ffmpeg introuvable : vidéo provisoire {relatif} non créée)")
            continue
        _video_provisoire(webm)
        liste[relatif] = _empreinte(webm)
        videos_creees.append(relatif)
        crees.append(f"game/{relatif}")
    if liste or (racine / LISTE_VIDEOS_PROVISOIRES).exists():
        (racine / LISTE_VIDEOS_PROVISOIRES).parent.mkdir(parents=True, exist_ok=True)
        (racine / LISTE_VIDEOS_PROVISOIRES).write_text(
            "# Vidéos provisoires créées par tools/fiches.py provisoires (chemin empreinte).\n"
            + "".join(f"{chemin} {empreinte}\n" for chemin, empreinte in sorted(liste.items())), encoding="utf-8")
    if videos_creees and (racine / "tools" / "convertir_videos.py").exists():
        subprocess.run([sys.executable, str(racine / "tools" / "convertir_videos.py")], check=False)
    return crees, retires


def _couleur(nom: str) -> tuple:
    valeur = int(hashlib.md5(nom.encode("utf-8")).hexdigest()[:6], 16)
    return tuple(40 + ((valeur >> decalage) & 0xFF) // 2 for decalage in (16, 8, 0))


def _police(taille: int):
    from PIL import ImageFont
    return ImageFont.load_default(size=taille)


def _dessiner_decor(nom: str, chemin: Path):
    from PIL import Image, ImageDraw
    haut = _couleur(nom)
    bas = tuple(min(255, composante + 70) for composante in haut)
    image = Image.new("RGB", (1920, 1080))
    dessin = ImageDraw.Draw(image)
    for y in range(1080):
        t = y / 1079
        dessin.line([(0, y), (1920, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(haut, bas)))
    dessin.text((960, 490), nom, font=_police(96), fill=(255, 255, 255), anchor="mm")
    # Sans accent : la police par défaut de Pillow ne les contient pas.
    dessin.text((960, 590), "PROVISOIRE", font=_police(40), fill=(255, 255, 255), anchor="mm")
    image.save(chemin)


def _dessiner_carte(nom: str, chemin: Path, lieux: list):
    """Carte provisoire : fond quadrillé, un repère par lieu à sa position (en pourcentage)."""
    from PIL import Image, ImageDraw
    fond = _couleur(nom)
    image = Image.new("RGB", (1920, 1080), fond)
    dessin = ImageDraw.Draw(image)
    trait = tuple(min(255, composante + 35) for composante in fond)
    for x in range(0, 1920, 120):
        dessin.line([(x, 0), (x, 1080)], fill=trait)
    for y in range(0, 1080, 120):
        dessin.line([(0, y), (1920, y)], fill=trait)
    # En haut à droite : le jeu affiche le titre de la carte en haut à gauche.
    dessin.text((1880, 30), nom, font=_police(64), fill=(255, 255, 255), anchor="ra")
    dessin.text((1880, 110), "PROVISOIRE", font=_police(32), fill=(255, 255, 255), anchor="ra")
    for nom_lieu, x, y in lieux:
        cx, cy = 1920 * x / 100, 1080 * y / 100
        dessin.ellipse([cx - 90, cy - 90, cx + 90, cy + 90], outline=(255, 255, 255), width=4)
        dessin.text((cx, cy + 120), _sans_accents(nom_lieu), font=_police(32), fill=(255, 255, 255), anchor="mm")
    image.save(chemin)


def _dessiner_icone(nom: str, chemin: Path):
    """Icône provisoire d'une pièce (vignette de la barre des pièces) : 240 × 135, dégradé et nom."""
    from PIL import Image, ImageDraw
    haut = _couleur(nom)
    bas = tuple(min(255, composante + 70) for composante in haut)
    image = Image.new("RGB", (240, 135))
    dessin = ImageDraw.Draw(image)
    for y in range(135):
        t = y / 134
        dessin.line([(0, y), (240, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(haut, bas)))
    dessin.rectangle([0, 0, 239, 134], outline=(255, 255, 255), width=2)
    dessin.text((120, 62), _sans_accents(nom), font=_police(22), fill=(255, 255, 255), anchor="mm")
    dessin.text((120, 100), "provisoire", font=_police(16), fill=(255, 255, 255), anchor="mm")
    image.save(chemin)


def _personnage_de_l_avatar(projet: Projet, image: str) -> tuple:
    """(initiale, couleur) du personnage dont c'est l'avatar."""
    for pid, fiche in projet.personnages.items():
        if isinstance(fiche, dict) and fiche.get("avatar") == image:
            couleur = str(fiche.get("couleur") or "")
            rvb = tuple(int(couleur[i:i + 2], 16) for i in (1, 3, 5)) if re.fullmatch(r"#[0-9a-fA-F]{6}", couleur) else _couleur(pid)
            return str(fiche.get("nom") or pid)[:1].upper(), rvb
    return image[:1].upper(), _couleur(image)


def _dessiner_avatar(nom: str, chemin: Path, personnage: tuple):
    """Avatar provisoire : disque à la couleur du personnage, avec son initiale (96 × 96, fond transparent)."""
    from PIL import Image, ImageDraw
    initiale, couleur = personnage
    image = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    dessin = ImageDraw.Draw(image)
    dessin.ellipse([2, 2, 93, 93], fill=tuple(couleur) + (255,), outline=(255, 255, 255, 255), width=3)
    dessin.text((48, 46), _sans_accents(initiale), font=_police(48), fill=(20, 20, 30), anchor="mm")
    image.save(chemin)


def _sans_accents(texte: str) -> str:
    """Texte réduit à l'ASCII (é → e) : la police par défaut de Pillow n'a pas les accents."""
    import unicodedata
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()


def _dessiner_personnage(nom: str, chemin: Path):
    from PIL import Image, ImageDraw
    couleur = tuple(min(255, composante + 80) for composante in _couleur(nom.split(" ")[0])) + (255,)
    image = Image.new("RGBA", (620, 940), (0, 0, 0, 0))
    dessin = ImageDraw.Draw(image)
    dessin.ellipse([200, 40, 420, 290], fill=couleur)
    dessin.rounded_rectangle([90, 310, 530, 1200], radius=190, fill=couleur)
    dessin.text((310, 600), nom, font=_police(44), fill=(255, 255, 255), anchor="mm")
    dessin.text((310, 660), "provisoire", font=_police(30), fill=(255, 255, 255), anchor="mm")
    image.save(chemin)


def _video_provisoire(webm: Path, secondes: int = 3):
    webm.parent.mkdir(parents=True, exist_ok=True)
    teinte = "0x%02x%02x%02x" % _couleur(webm.stem)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"color=c={teinte}:size=1280x720:rate=30:duration={secondes}",
                    "-f", "lavfi", "-i", f"sine=frequency=330:duration={secondes}",
                    "-c:v", "libvpx-vp9", "-b:v", "300k", "-c:a", "libopus", "-shortest", str(webm)], check=True)


def _empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()[:16]


# --- Graphe et contexte ---------------------------------------------------------------------

def graphe(projet: Projet, exploration: Exploration | None) -> str:
    lignes = ["flowchart TD", f"    DEBUT((début)) --> {projet.bible['debut']}"]
    for sid in projet.ordre():
        fiche = projet.scenes[sid]
        titre = _mermaid(f"{sid}<br/>{fiche.get('titre', '')}")
        if fiche.get("fin"):
            forme = f'(["{titre}"])'
        elif fiche.get("retour"):
            forme = f'[["{titre}"]]'
        else:
            forme = f'["{titre}"]'
        lignes.append(f"    {sid}{forme}")
    for sid in projet.ordre():
        fiche = projet.scenes[sid]
        for element in tous_les_elements(projet, fiche):
            if cle_element(element, projet) == "appel":
                lignes.append(f"    {sid} -.->|appel| {element['appel']}")
        _, options = options_de(fiche)
        for option in options:
            libelle = str(option.get("libelle", ""))
            if "si" in option:
                libelle += f" (si {_expr_texte(option['si'])})"
            lignes.append(f'    {sid} -->|"{_mermaid(libelle)}"| {option["destination"]}')
        if fiche.get("suite"):
            lignes.append(f"    {sid} --> {fiche['suite']}")
        if fiche.get("carte") is not None:
            for cible in cibles_carte(projet, fiche["carte"], lambda expr, couts=(): True):
                lignes.append(f'    {sid} -->|"carte : {_mermaid(_texte_clics(projet, cible["clics"]))}"| {cible["scene"]}')
    if exploration is not None:
        inatteintes = [sid for sid in projet.ordre() if sid not in exploration.entrees]
        if inatteintes:
            lignes.append("    classDef inatteinte stroke:#c00,stroke-dasharray:5 5")
            lignes.append(f"    class {','.join(inatteintes)} inatteinte")
    return ("# Graphe des routes\n\nGénéré par `tools/fiches.py graphe`. Formes : rectangle = scène, "
            "ovale = fin, double cadre = scène appelée ; pointillés = appel ; « carte : … » = lieu choisi sur une carte.\n\n```mermaid\n"
            + "\n".join(lignes) + "\n```\n")


def graphe_html(projet: Projet, exploration: Exploration, rapport: Rapport) -> str:
    """Graphe interactif des routes (contenu/graphe.html) : une page autonome, sans
    dépendance, à ouvrir dans un navigateur. Modèle : tools/graphe_modele.html."""
    donnees = donnees_graphe(projet, exploration, rapport)
    texte = json.dumps(donnees, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    modele = MODELE_GRAPHE_HTML.read_text(encoding="utf-8")
    return modele.replace("{{TITRE}}", html.escape(donnees["titre"])).replace("/*DONNEES*/null", texte)


def donnees_graphe(projet: Projet, exploration: Exploration, rapport: Rapport) -> dict:
    """Données du graphe HTML : scènes avec leur position, liens, routes de test et
    avertissements de verifier."""
    debut = projet.bible.get("debut")
    images, videos, etats_images, etats_videos = _etats_medias(projet)
    repliques_scene: dict = {}
    for replique in repliques(projet):
        repliques_scene.setdefault(replique.sid, []).append(replique)
    traductions = {code: traductions_de(projet, code) for code in projet.langues_cibles}
    problemes = [_probleme(projet, message) for message in rapport.erreurs + rapport.avertissements]
    scenes, aretes = [], []
    for sid in projet.ordre():
        fiche = projet.scenes[sid]
        sorties = _sorties(projet, sid, exploration)
        for rang, sortie in enumerate(sorties):
            if sortie.get("destination"):
                aretes.append({"de": sid, "vers": sortie["destination"], "sortie": rang, "type": sortie["type"],
                               "libelle": sortie["libelle"], "propose": sortie.get("propose", True)})
        question, options = options_de(fiche)
        lignes = repliques_scene.get(sid, [])
        textes_scene = [str(option["libelle"]) for option in options]
        if fiche.get("galerie"):
            textes_scene.append(_titre_galerie(sid, fiche))
        medias = [{"nom": nom, "type": "image", "usages": ", ".join(entree["usages"]), "etat": etats_images[nom][0]}
                  for nom, entree in sorted(images.items()) if sid in entree["scenes"]]
        medias += [{"nom": relatif, "type": "vidéo", "usages": ", ".join(entree["usages"]),
                    "etat": etats_videos[relatif][0], "ogv": etats_videos[relatif][1]}
                   for relatif, entree in sorted(videos.items()) if sid in entree["scenes"]]
        entrees = exploration.entrees.get(sid, [])
        scenes.append({
            "id": sid, "titre": str(fiche.get("titre") or ""), "lieu": str(fiche.get("lieu") or ""),
            "moment": str(fiche.get("moment") or ""), "fichier": projet.ou(sid),
            "resume": str(fiche.get("resume") or "").strip(), "notes": str(fiche.get("notes") or "").strip(),
            "objectifs": [str(objectif) for objectif in _liste(fiche.get("objectif_narratif"))],
            "personnages": [str(_dict(projet.personnages.get(pid)).get("nom", pid)) for pid in _liste(fiche.get("personnages"))],
            "conditions": conditions_de(fiche),
            "debut": sid == debut, "atteinte": sid in exploration.entrees,
            "fin": bool(fiche.get("fin")), "retour": bool(fiche.get("retour")),
            "repliques": len(lignes),
            "apercu": _apercu(projet, fiche.get("contenu")),
            "question": _apercu(projet, [question])[0] if question is not None else None,
            "sorties": sorties,
            "entree": [{"variable": nom, "valeurs": sorted({_litteral(etat.get(nom)) for etat in entrees})}
                       for nom in projet.variables_toutes],
            "route": _texte_route(exploration.routes[sid]) if sid in exploration.routes else "",
            "medias": medias,
            "galerie": _titre_galerie(sid, fiche) if fiche.get("galerie") else "",
            "traductions": [{"code": code, "total": len(lignes) + len(textes_scene),
                             "faites": sum(r.rid in faites for r in lignes) + sum(t in textes for t in textes_scene)}
                            for code, (faites, textes) in traductions.items()],
            "avertissements": [probleme["message"] for probleme in problemes if probleme["scene"] == sid],
            "h": GRAPHE["entete"] + GRAPHE["haut_sorties"] + len(sorties) * GRAPHE["ligne"] + GRAPHE["bas"],
        })
    positions, arriere = _disposition(debut, projet.ordre(), [(arete["de"], arete["vers"]) for arete in aretes],
                                      {scene["id"]: scene["h"] for scene in scenes})
    for scene in scenes:
        scene["x"], scene["y"] = positions[scene["id"]]
    for arete in aretes:
        arete["arriere"] = (arete["de"], arete["vers"]) in arriere
    routes = []
    for numero, route in enumerate(routes_de_test(exploration), 1):
        chemin = route.get("route", ())
        libelles = iter(_libelle_choix(projet, libelle) for _, _, libelle in route["choix"])
        etapes = [{"de": chemin[i], "vers": chemin[i + 2], "choix": None if chemin[i + 1] == "suite" else next(libelles, None)}
                  for i in range(0, len(chemin) - 2, 2)]
        routes.append({"nom": f"route_{numero:02d}", "fin": route["fin"], "choix": [_libelle_choix(projet, c[2]) for c in route["choix"]],
                       "scenes": list(chemin[0::2]), "etapes": etapes,
                       "etat": {nom: _litteral(valeur) for nom, valeur in route["etat"].items()}})
    return {
        "_genere_par": MARQUEUR,
        "titre": str(projet.bible.get("titre") or "Graphe des routes"),
        "geometrie": {cle: GRAPHE[cle] for cle in ("largeur", "entete", "haut_sorties", "ligne")},
        "largeur": max((scene["x"] + GRAPHE["largeur"] for scene in scenes), default=0) + GRAPHE["marge"],
        "hauteur": max((scene["y"] + scene["h"] for scene in scenes), default=0) + GRAPHE["marge"],
        "stats": {"scenes": len(scenes), "fins": len(exploration.fins), "etats": exploration.etats,
                  "complete": exploration.complete},
        "langues": [projet.langue_source] + projet.langues_cibles,
        "scenes": scenes, "aretes": aretes, "routes": routes, "problemes": problemes,
    }


def _sorties(projet: Projet, sid: str, exploration: Exploration) -> list:
    """Sorties d'une scène dans le graphe : appels, puis choix ou suite, ou fin, ou retour."""
    fiche = projet.scenes[sid]
    appels = []
    for element in tous_les_elements(projet, fiche):
        if cle_element(element, projet) == "appel" and element["appel"] not in appels:
            appels.append(element["appel"])
    sorties = [{"type": "appel", "libelle": f"appel {cible}", "destination": cible} for cible in appels]
    # Une scène jamais atteinte, ou une exploration partielle, ne dit rien des choix proposés.
    tout_propose = sid not in exploration.entrees or not exploration.complete
    for rang, option in enumerate(options_de(fiche)[1]):
        sorties.append({"type": "choix", "libelle": str(option["libelle"]),
                        "si": _expr_texte(option["si"]) if "si" in option else "",
                        "effets": _texte_effets(option.get("effets")), "destination": option["destination"],
                        "propose": tout_propose or (sid, rang) in exploration.choix_proposes,
                        "contenu": _apercu(projet, option.get("contenu"))})
    if fiche.get("suite"):
        sorties.append({"type": "suite", "libelle": "suite", "destination": fiche["suite"]})
    if fiche.get("carte") is not None:
        entrees = {cid: _liste(_dict(carte).get("lieux")) for cid, carte in projet.cartes.items()}
        for cible in cibles_carte(projet, fiche["carte"], lambda expr, couts=(): True):
            entree = _dict(entrees[cible["carte"]][cible["rang"]])
            sorties.append({"type": "carte", "libelle": _texte_clics(projet, cible["clics"]),
                            "si": _expr_texte(entree["si"]) if "si" in entree else "", "effets": "",
                            "destination": cible["scene"],
                            "propose": tout_propose or (cible["carte"], cible["rang"]) in exploration.lieux_proposes,
                            "contenu": []})
    if fiche.get("fin"):
        sorties.append({"type": "fin", "libelle": "fin de partie"})
    if fiche.get("retour"):
        sorties.append({"type": "retour", "libelle": "retour à la scène appelante"})
    return sorties


def _apercu(projet: Projet, elements, niveau: int = 0) -> list:
    """Contenu d'une scène en lignes lisibles : [{n: niveau, t: type, texte, qui}]."""
    lignes = []
    for element in _liste(elements):
        cle = cle_element(element, projet)
        if cle == "narration":
            lignes.append({"n": niveau, "t": "narration", "texte": str(element[cle])})
        elif cle in projet.personnages:
            nom = str(_dict(projet.personnages[cle]).get("nom", cle))
            lignes.append({"n": niveau, "t": "replique", "qui": nom, "texte": str(element[cle])})
        elif cle == "si":
            lignes.append({"n": niveau, "t": "si", "texte": f"si {_expr_texte(element['si'])}"})
            lignes += _apercu(projet, element.get("alors"), niveau + 1)
            for branche in _liste(element.get("sinon_si")):
                lignes.append({"n": niveau, "t": "si", "texte": f"sinon si {_expr_texte(branche.get('si'))}"})
                lignes += _apercu(projet, branche.get("alors"), niveau + 1)
            if element.get("sinon") is not None:
                lignes.append({"n": niveau, "t": "si", "texte": "sinon"})
                lignes += _apercu(projet, element.get("sinon"), niveau + 1)
        elif cle is not None:
            lignes.append({"n": niveau, "t": "action", "texte": _texte_action(element, cle)})
    return lignes


def _texte_action(element: dict, cle: str) -> str:
    valeur = element[cle]
    transition = f" ({element['transition']})" if element.get("transition") else ""
    if cle == "decor":
        return f"décor {valeur or '(vide)'}{transition}"
    if cle == "montrer":
        return f"montre {valeur}" + (f", {element['position']}" if element.get("position") else "") + transition
    if cle == "cacher":
        return f"retire {valeur}{transition}"
    if cle == "pause":
        return "pause jusqu'au clic" if valeur is None else f"pause {valeur} s"
    if cle == "effets":
        return f"effets : {_texte_effets(valeur)}"
    return f"{cle} {valeur}"


def _texte_effets(effets) -> str:
    return ", ".join(f"{nom} {valeur:+}" if _est_nombre(valeur) else f"{nom} = {_litteral(valeur)}"
                     for nom, valeur in _dict(effets).items())


def _probleme(projet: Projet, message: str) -> dict:
    """Message du rapport, rattaché à sa scène quand on la retrouve (fiche ou réplique)."""
    ou, _, texte = message.partition(" : ")
    scene = next((sid for sid, fichier in projet.fichiers.items() if ou == fichier or ou.startswith(fichier + ",")), "")
    if not scene:
        trouve = re.search(r", ([a-z0-9_]+)_[0-9a-f]{8}(?:_\d+)?$", ou)
        if trouve:
            scene = next((sid for sid in projet.scenes if sid.lower() == trouve.group(1)), "")
    return {"ou": ou, "message": texte or message, "scene": scene}


def _disposition(debut, ordre: list, aretes: list, hauteurs: dict) -> tuple[dict, set]:
    """Place les scènes du graphe HTML de gauche à droite. Colonnes : plus long chemin depuis
    le début, sans les retours en arrière. Ordre dans chaque colonne : barycentre des voisins.
    Renvoie ({scène : (x, y)}, liens de retour en arrière)."""
    suivants = {sid: [] for sid in ordre}
    for de, vers in aretes:
        if vers in suivants and vers not in suivants[de]:
            suivants[de].append(vers)
    # Parcours en profondeur : un lien vers une scène en cours de parcours ferme un cycle.
    etat, arriere, decouverte = {}, set(), []
    for racine in ([debut] if debut in suivants else []) + list(ordre):
        if racine in etat:
            continue
        etat[racine] = "en cours"
        decouverte.append(racine)
        pile = [(racine, iter(suivants[racine]))]
        while pile:
            sid, reste = pile[-1]
            for vers in reste:
                if etat.get(vers) == "en cours":
                    arriere.add((sid, vers))
                elif vers not in etat:
                    etat[vers] = "en cours"
                    decouverte.append(vers)
                    pile.append((vers, iter(suivants[vers])))
                    break
            else:
                etat[sid] = "fini"
                pile.pop()
    avant = {sid: [vers for vers in suivants[sid] if (sid, vers) not in arriere] for sid in ordre}
    precedents = {sid: [de for de in ordre if sid in avant[de]] for sid in ordre}
    entrants = {sid: len(precedents[sid]) for sid in ordre}
    colonne = {sid: 0 for sid in ordre}
    file = [sid for sid in decouverte if entrants[sid] == 0]
    while file:
        sid = file.pop(0)
        for vers in avant[sid]:
            colonne[vers] = max(colonne[vers], colonne[sid] + 1)
            entrants[vers] -= 1
            if entrants[vers] == 0:
                file.append(vers)
    colonnes = [[] for _ in range(max(colonne.values(), default=0) + 1)]
    for sid in decouverte:
        colonnes[colonne[sid]].append(sid)
    # Étapes fictives pour les liens qui sautent des colonnes : elles comptent pour l'ordre.
    gauche, droite = {}, {}
    for sid in ordre:
        for vers in avant[sid]:
            precedent = sid
            for c in range(colonne[sid] + 1, colonne[vers]):
                fictif = ("fictif", sid, vers, c)
                colonnes[c].append(fictif)
                gauche.setdefault(fictif, []).append(precedent)
                droite.setdefault(precedent, []).append(fictif)
                precedent = fictif
            gauche.setdefault(vers, []).append(precedent)
            droite.setdefault(precedent, []).append(vers)
    for _ in range(4):
        for c in range(1, len(colonnes)):
            colonnes[c] = _par_barycentre(colonnes[c], gauche, colonnes[c - 1])
        for c in range(len(colonnes) - 2, -1, -1):
            colonnes[c] = _par_barycentre(colonnes[c], droite, colonnes[c + 1])
    # Hauteur : celle des scènes qui y mènent (une suite de scènes reste sur une ligne),
    # sans chevaucher la scène précédente de la colonne.
    positions = {}
    for c, liste in enumerate(colonnes):
        x = GRAPHE["marge"] + c * (GRAPHE["largeur"] + GRAPHE["ecart_colonnes"])
        bas = GRAPHE["marge"]
        for sid in (noeud for noeud in liste if isinstance(noeud, str)):
            souhaits = [positions[de][1] for de in precedents[sid] if de in positions]
            y = max(bas, sum(souhaits) / len(souhaits)) if souhaits else bas
            positions[sid] = (x, round(y))
            bas = round(y) + hauteurs[sid] + GRAPHE["ecart_noeuds"]
    return positions, arriere


def _par_barycentre(colonne: list, voisins: dict, reference: list) -> list:
    rangs = {noeud: rang for rang, noeud in enumerate(reference)}
    actuels = {noeud: rang for rang, noeud in enumerate(colonne)}

    def cle(noeud):
        places = [rangs[voisin] for voisin in voisins.get(noeud, []) if voisin in rangs]
        return sum(places) / len(places) if places else actuels[noeud]

    return sorted(colonne, key=cle)


def contexte(projet: Projet, exploration: Exploration, sid: str) -> str:
    """Paquet de contexte pour écrire ou réviser une scène : bible, état des variables,
    ce qui précède, suites prévues et format attendu."""
    fiche = projet.scenes[sid]
    lignes = [f"# Contexte d'écriture — {sid} : {fiche.get('titre', '')}", "",
              "## Consigne", "",
              "Écris ou révise le contenu de cette scène en respectant la bible, l'objectif narratif et les règles "
              "éditoriales ci-dessous. Réponds uniquement par la fiche YAML complète, au format décrit à la fin.", ""]
    if projet.bible.get("synopsis"):
        lignes += ["## Synopsis", "", str(projet.bible["synopsis"]).strip(), ""]
    if projet.bible.get("mystere_central"):
        lignes += ["## Mystère central (vérité réservée aux auteurs)", "", "```yaml", _yaml(projet.bible["mystere_central"]), "```", ""]
    lignes += ["## Objectif narratif", ""] + [f"- {o}" for o in _liste(fiche.get("objectif_narratif"))]
    if not fiche.get("objectif_narratif"):
        lignes.append("- (non précisé)")
    lignes.append("")
    lieu = projet.lieux.get(fiche.get("lieu"))
    if isinstance(lieu, dict):
        lignes += [f"## Lieu : {fiche['lieu']} ({fiche.get('moment', 'moment non précisé')})", "", str(lieu.get("description", "")),
                   "", f"Décors disponibles : {', '.join(_decors_de(lieu)) or 'aucun'}"
                   + (f" (par créneau : « decor: {fiche['lieu']} »)" if isinstance(lieu.get("decors"), dict) else "") + ".", ""]
    lignes += ["## Personnages présents", ""]
    for pid in _liste(fiche.get("personnages")):
        lignes += [f"### {pid}", "", "```yaml", _yaml(projet.personnages.get(pid)), "```", ""]
    etats = exploration.entrees.get(sid, [])
    lignes += ["## État possible à l'entrée", ""]
    if not etats:
        lignes += ["Scène jamais atteinte depuis « debut » : reliez-la d'abord à une autre scène.", ""]
    for nom, variable in projet.variables_toutes.items():
        if variable.get("interne"):
            continue
        valeurs = sorted({_litteral(etat.get(nom)) for etat in etats})
        paliers = variable.get("paliers") or []
        if paliers:
            noms = sorted({_palier(paliers, etat.get(nom)) for etat in etats if _est_nombre(etat.get(nom))})
            valeurs = [f"{', '.join(valeurs)} ({', '.join(noms)})"] if noms else valeurs
        lignes.append(f"- `{nom}` : {', '.join(valeurs) or '?'} — {variable.get('description', '')}")
    conditions = conditions_de(fiche)
    lignes += ["", "## Conditions d'entrée", "", *(f"- `{c}`" for c in conditions), *(["- aucune"] if not conditions else []), ""]
    lignes += ["## Ce qui précède", ""]
    etapes_par_source: dict = {}
    for source, etape in sorted(exploration.predecesseurs.get(sid, set())):
        etapes_par_source.setdefault(source, []).append(etape)
    for source, etapes in etapes_par_source.items():
        precedente = projet.scenes[source]
        lignes.append(f"- {source} ({precedente.get('titre', '')}) via {', '.join(etapes)} : "
                      f"{precedente.get('resume', 'pas de résumé')}")
    if not etapes_par_source:
        lignes.append("- rien : c'est la scène de départ" if sid == projet.bible.get("debut") else "- aucune scène n'y mène")
    if sid in exploration.routes:
        lignes += ["", f"Exemple de route : {_texte_route(exploration.routes[sid])}"]
    lignes += ["", "## Suites prévues", ""]
    _, options = options_de(fiche)
    for option in options:
        cible = projet.scenes.get(option.get("destination"), {})
        lignes.append(f"- « {option.get('libelle')} » → {option.get('destination')} ({cible.get('titre', '')})")
    if fiche.get("suite"):
        lignes.append(f"- suite → {fiche['suite']} ({projet.scenes[fiche['suite']].get('titre', '')})")
    if fiche.get("carte") is not None:
        lignes.append(f"- carte « {fiche['carte']} » : le joueur choisit un lieu (la présence des personnages est recalculée avant)")
        for cible in cibles_carte(projet, fiche["carte"], lambda expr, couts=(): True):
            lignes.append(f"  - {_texte_clics(projet, cible['clics'])} → {cible['scene']} ({projet.scenes[cible['scene']].get('titre', '')})")
    if fiche.get("fin"):
        lignes.append("- fin de partie")
    if fiche.get("retour"):
        lignes.append("- retour à la scène qui l'a appelée")
    lignes += ["", "## Règles éditoriales", ""] + [f"- {regle}" for regle in _liste(projet.bible.get("regles_editoriales"))]
    lignes += ["", "## Format attendu", "",
               "Éléments du contenu : narration, <personnage>, decor (+ transition), montrer (+ position, transition), "
               "cacher, video, pause, musique, son, effets, si / alors / sinon_si / sinon, appel. "
               "Fin de scène : choix, suite, fin, retour ou carte. "
               "Textes entre guillemets. Détails : contenu/LISEZMOI.md. Fiche actuelle :", "",
               "```yaml", _yaml(fiche), "```", ""]
    return "\n".join(lignes)


def _date_de(valeur):
    """Date de la bible (YAML la lit déjà, ou texte AAAA-MM-JJ), ou None."""
    if isinstance(valeur, datetime.datetime):
        return valeur.date()
    if isinstance(valeur, datetime.date):
        return valeur
    if isinstance(valeur, str):
        try:
            return datetime.date.fromisoformat(valeur.strip())
        except ValueError:
            return None
    return None


def _longueur_mois(annee: int, mois: int) -> int:
    return calendar.monthrange(annee, mois)[1]


def _decors_de(lieu: dict) -> list:
    decors = lieu.get("decors")
    return list(decors.values()) if isinstance(decors, dict) else _liste(decors)


def _palier(paliers: list, valeur) -> str:
    """Nom du plus haut palier dont le seuil est atteint, ou « - » (mêmes règles dans les deux moteurs)."""
    nom = "-"
    for seuil, candidat in paliers:
        if valeur >= seuil:
            nom = candidat
    return nom


# --- Utilitaires ------------------------------------------------------------------------------

class _DumperFiche(yaml.SafeDumper):
    """YAML des fiches : textes entre guillemets (sûrs même avec « : »), identifiants nus."""


def _representer_texte(dumper, valeur):
    style = None if re.fullmatch(r"[A-Za-z0-9_./-]+", valeur) else '"'
    return dumper.represent_scalar("tag:yaml.org,2002:str", valeur, style=style)


_DumperFiche.add_representer(str, _representer_texte)


def _yaml(donnees) -> str:
    return yaml.dump(donnees, Dumper=_DumperFiche, allow_unicode=True, sort_keys=False, width=1000).rstrip()


def cle_element(element, projet: Projet):
    """Type d'un élément de contenu (narration, id de personnage, decor…), ou None."""
    if not isinstance(element, dict):
        return None
    cles = [cle for cle in element if cle in ELEMENTS or cle in projet.personnages]
    return cles[0] if len(cles) == 1 else None


def options_de(fiche) -> tuple:
    choix = fiche.get("choix")
    if isinstance(choix, list):
        return None, choix
    if isinstance(choix, dict):
        return choix.get("question"), _liste(choix.get("options"))
    return None, []


def conditions_de(fiche) -> list:
    """Conditions d'entrée, en liste d'expressions. Accepte aussi le format compact :
    {relation_lena_min: 4, indice_photo: true}."""
    brutes = fiche.get("conditions")
    if brutes is None:
        return []
    if isinstance(brutes, dict):
        resultat = []
        for cle, valeur in brutes.items():
            cle = str(cle)
            if cle.endswith("_min"):
                resultat.append(f"{cle[:-4]} >= {_litteral(valeur)}")
            elif cle.endswith("_max"):
                resultat.append(f"{cle[:-4]} <= {_litteral(valeur)}")
            else:
                resultat.append(f"{cle} == {_litteral(valeur)}")
        return resultat
    if not isinstance(brutes, list):
        brutes = [brutes]
    return [_expr_texte(condition) for condition in brutes]


def _expr_texte(expr) -> str:
    if isinstance(expr, bool):
        return "True" if expr else "False"
    return str(expr)


def _litteral(valeur) -> str:
    if isinstance(valeur, bool):
        return "True" if valeur else "False"
    if valeur is None:
        return "None"
    if isinstance(valeur, str):
        return _chaine(valeur)
    return repr(valeur)


def _chaine(texte: str) -> str:
    return '"' + texte.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _mermaid(texte: str) -> str:
    return texte.replace('"', "#quot;")


def _est_nombre(valeur) -> bool:
    return isinstance(valeur, (int, float)) and not isinstance(valeur, bool)


def _dict(valeur) -> dict:
    return valeur if isinstance(valeur, dict) else {}


def _liste(valeur) -> list:
    return valeur if isinstance(valeur, list) else []


def _gel(etat: dict) -> tuple:
    return tuple(sorted(etat.items()))


def _texte_etat(etat: dict) -> str:
    return ", ".join(f"{nom} = {_litteral(valeur)}" for nom, valeur in sorted(etat.items()))


def _texte_route(route: tuple, etapes_max: int = 12) -> str:
    morceaux = list(route)
    if len(morceaux) > 2 * etapes_max + 1:
        morceaux = ["…"] + morceaux[-2 * etapes_max:]
    return " → ".join(morceaux)


# --- Ligne de commande -------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bible et fiches de scène → script .rpy commun Ren'Py / Godot.")
    commandes = parser.add_subparsers(dest="commande", required=True)
    commandes.add_parser("verifier", help="contrôle la bible et les fiches, explore toutes les routes")
    commande_generer = commandes.add_parser("generer", help="écrit le script, la galerie et les tests de parcours")
    commande_generer.add_argument("--remplacer", action="store_true", help="écrase aussi les fichiers écrits à la main")
    commande_generer.add_argument("--sans-godot", action="store_true", help="ne pas faire relire le script par Godot")
    commandes.add_parser("provisoires", help="images et vidéos provisoires pour ce qui manque")
    commandes.add_parser("production", help="images et vidéos à produire → contenu/production.md")
    commande_graphe = commandes.add_parser("graphe", help="graphe des routes → contenu/graphe.html (interactif) et graphe.md (Mermaid)")
    commande_graphe.add_argument("--ouvrir", action="store_true", help="ouvre le graphe interactif dans le navigateur")
    commande_contexte = commandes.add_parser("contexte", help="contexte pour écrire ou réviser une scène")
    commande_contexte.add_argument("scene", help="identifiant de la scène, par exemple CH01_SC02")
    commande_contexte.add_argument("-o", "--sortie", help="fichier de sortie (sinon : affichage)")
    commande_traduire = commandes.add_parser("traduire", help="met à jour contenu/traductions/<langue>.yaml")
    commande_traduire.add_argument("langues", nargs="*", help="codes de langue (par défaut : toutes les traductions de la bible)")
    commande_traduire.add_argument("--paquet", help="écrit aussi le paquet à donner à un traducteur ou à une IA")
    commande_traduire.add_argument("--importer", help="reprend les traductions d'un fichier YAML (réponse au paquet)")
    args = parser.parse_args(argv)

    rapport = Rapport()
    projet = charger(RACINE, rapport)
    exploration = verifier(projet, rapport)
    rapport.afficher()
    if exploration is not None:
        fins = ", ".join(f"{sid} ({len(etats)} état(s))" for sid, etats in sorted(exploration.fins.items()))
        print(f"{len(projet.scenes)} scènes, {exploration.etats} états explorés, fins atteintes : {fins or 'aucune'}.")
    if rapport.erreurs:
        print(f"{len(rapport.erreurs)} erreur(s) : corrigez-les avant de générer.")
        return 1
    if args.commande == "verifier":
        return 0

    if args.commande == "generer":
        ecrits, supprimes = ecrire(projet, generer(projet, exploration), rapport, remplacer=args.remplacer)
        for relatif in ecrits:
            print(f"écrit      {relatif}")
        for relatif in supprimes:
            print(f"supprimé   {relatif}")
        if not ecrits and not supprimes and not rapport.erreurs:
            print("Fichiers générés déjà à jour.")
        if rapport.erreurs:
            rapport.afficher()
            return 1
        return 0 if args.sans_godot or controle_godot(RACINE) else 1
    if args.commande == "provisoires":
        crees, retires = provisoires(projet)
        for relatif in crees:
            print(f"créé       {relatif}")
        for relatif in retires:
            print(f"retiré     {relatif}")
        print(production(projet)[1])
        return 0
    if args.commande == "production":
        texte, resume = production(projet)
        (RACINE / "contenu" / "production.md").write_text(texte, encoding="utf-8")
        print(f"{resume}\nDétail : contenu/production.md")
        return 0
    if args.commande == "graphe":
        (RACINE / "contenu" / "graphe.md").write_text(graphe(projet, exploration), encoding="utf-8")
        page = RACINE / FICHIER_GRAPHE_HTML
        page.write_text(graphe_html(projet, exploration, rapport), encoding="utf-8")
        print(f"Graphe : {FICHIER_GRAPHE_HTML} (à ouvrir dans un navigateur) et contenu/graphe.md (Mermaid)")
        if args.ouvrir:
            webbrowser.open(page.as_uri())
        return 0
    if args.commande == "contexte":
        if args.scene not in projet.scenes:
            print(f"Scène inconnue : {args.scene}")
            return 1
        texte = contexte(projet, exploration, args.scene)
        if args.sortie:
            Path(args.sortie).write_text(texte, encoding="utf-8")
            print(f"Contexte : {args.sortie}")
        else:
            print(texte)
        return 0
    if args.commande == "traduire":
        return _commande_traduire(projet, args)
    return 0


def _commande_traduire(projet: Projet, args) -> int:
    codes = args.langues or projet.langues_cibles
    if not codes:
        print("Aucune traduction déclarée : ajoutez à la bible « langues: {source: fr, traductions: [en]} ».")
        return 1
    inconnues = [code for code in codes if code not in projet.langues_cibles]
    if inconnues:
        print(f"Langue(s) absente(s) de « langues.traductions » dans la bible : {', '.join(inconnues)}.")
        return 1
    if (args.paquet or args.importer) and len(codes) != 1:
        print("--paquet et --importer s'utilisent avec une seule langue.")
        return 1
    for code in codes:
        if args.importer:
            try:
                repris = importer_traductions(projet, code, Path(args.importer).read_text(encoding="utf-8"))
            except (OSError, ValueError, yaml.YAMLError) as exc:
                print(f"{args.importer} : lecture impossible ({exc}).")
                return 1
            print(f"{args.importer} : {repris} traduction(s) reprise(s).")
        texte, bilan = traduire(projet, code)
        chemin = projet.racine / DOSSIER_TRADUCTIONS / f"{code}.yaml"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        if not chemin.exists() or chemin.read_text(encoding="utf-8") != texte:
            chemin.write_text(texte, encoding="utf-8")
        print(f"{chemin.relative_to(projet.racine).as_posix()} : {bilan['repliques']} répliques, {bilan['textes']} textes ; "
              f"{bilan['nouveaux']} nouveau(x), {bilan['repris']} repris, {bilan['a_traduire']} à traduire, "
              f"{bilan['a_revoir']} à revoir, {bilan['obsoletes']} obsolète(s).")
        if args.paquet:
            Path(args.paquet).write_text(paquet_traduction(projet, code, yaml.safe_load(texte)), encoding="utf-8")
            print(f"Paquet de traduction : {args.paquet}")
        if bilan["a_traduire"] or bilan["a_revoir"]:
            print(f"  Complétez ou revoyez « texte » dans {chemin.relative_to(projet.racine).as_posix()}.")
    print("Ensuite : .venv/bin/python tools/fiches.py generer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
