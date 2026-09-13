#!/usr/bin/env python3
"""Chaîne d'écriture : bible narrative et fiches de scène (YAML) → script .rpy du
sous-ensemble commun Ren'Py / Godot. Format : contenu/LISEZMOI.md.

  verifier          contrôle la bible et les fiches, puis explore toutes les routes
  generer           vérifie ; écrit game/story/*.rpy, game/galerie.json et les tests de
                    parcours (Godot et Ren'Py) ; fait relire le script par Godot
  provisoires       images et vidéos provisoires pour tout ce qui manque encore
  production        images et vidéos à produire → contenu/production.md
  graphe            graphe des routes (Mermaid) → contenu/graphe.md
  contexte SCENE    paquet de contexte pour écrire ou réviser une scène
  traduire [LANGUE] met à jour contenu/traductions/<langue>.yaml (répliques et textes à traduire)

Usage : .venv/bin/python tools/fiches.py <commande>
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
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
FICHIER_ROUTES = "tests/routes_attendues.json"
FICHIER_TESTS_RENPY = "game/tests_routes.rpy"
FICHIER_LANGUES = "game/langues.json"
DOSSIER_TRADUCTIONS = "contenu/traductions"
DOSSIER_PROVISOIRES = "game/images/provisoires"
LISTE_VIDEOS_PROVISOIRES = "game/videos/provisoires.txt"
ROUTES_MAX = 12
## Âge minimum des personnages, réglable dans la bible par « age_minimum ».
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
ELEMENTS = ("narration", "decor", "montrer", "cacher", "video", "pause", "musique", "son", "effets", "si", "appel")
MODIFICATEURS = {
    "decor": {"transition"},
    "montrer": {"position", "transition"},
    "cacher": {"transition"},
    "si": {"alors", "sinon_si", "sinon"},
}
CHAMPS_FICHE = {"id", "titre", "chapitre", "lieu", "moment", "personnages", "objectif_narratif", "resume",
                "conditions", "contenu", "choix", "suite", "fin", "retour", "galerie", "notes"}
CHAMPS_OPTION = {"id", "libelle", "si", "effets", "contenu", "destination"}
FINS = ("choix", "suite", "fin", "retour")
MOTS_RESERVES = set(ELEMENTS) | set(FONCTIONS) | {
    "alors", "sinon", "sinon_si", "transition", "position", "label", "define", "default", "image",
    "scene", "show", "hide", "with", "jump", "call", "return", "pass", "play", "stop", "queue", "window",
    "menu", "if", "elif", "else", "while", "for", "python", "init", "screen", "transform", "style",
    "and", "or", "not", "in", "is", "True", "False", "None", "renpy", "store", "persistent", "config",
    "gui", "build", "start", "extend", "nvl", "voice", "centered", "narrator", "adv"}
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
        if isinstance(age, bool) or not isinstance(age, int):
            rapport.erreur(ici, "« age » obligatoire, en années")
        elif age < age_minimum:
            rapport.erreur(ici, f"âge {age} : la bible fixe l'âge minimum à {age_minimum} (« age_minimum »)")
        couleur = fiche.get("couleur")
        if couleur is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(couleur)):
            rapport.erreur(ici, "« couleur » attendue au format #rrggbb")
    for nom, variable in projet.variables.items():
        ici = f"{ou}, variable « {nom} »"
        if not isinstance(nom, str) or not IDENT.match(nom) or nom in MOTS_RESERVES or nom in projet.personnages:
            rapport.erreur(ici, "nom invalide, réservé ou déjà pris par un personnage")
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
        if not isinstance(lieu, dict):
            rapport.erreur(f"{ou}, lieu « {lid} »", "fiche attendue (description, decors)")
    if not isinstance(bible.get("regles_editoriales", []), list):
        rapport.erreur(ou, "« regles_editoriales » : liste attendue")
    _verifier_langues(bible.get("langues"), rapport)


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
        verif.erreur(f"la scène doit se terminer par un seul de : choix, suite, fin, retour (trouvé : {', '.join(fins) or 'aucun'})")
    if fiche.get("suite") is not None:
        verif.destination(fiche["suite"], "suite")
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
    produits = {"start"} | {sid.lower() for sid in projet.scenes} | set(projet.personnages) | set(projet.variables)
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
                        "decor, montrer, cacher, video, pause, musique, son, effets, si ou appel", chemin)
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
            if valeur is not None:
                self.image(valeur, chemin)
            self.transition(element, chemin)
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

    def texte(self, valeur, chemin):
        if isinstance(valeur, bool) or not isinstance(valeur, (str, int, float)) or not str(valeur).strip():
            self.erreur("texte attendu (mettez-le entre guillemets)", chemin)
            return
        for nom in INTERPOLATION.findall(str(valeur).replace("[[", "")):
            if nom not in self.projet.variables:
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
            if isinstance(noeud, ast.Name) and noeud.id not in FONCTIONS and noeud.id not in self.projet.variables:
                self.erreur(f"variable inconnue « {noeud.id} » dans « {texte} » (à déclarer dans la bible)", chemin)
                return

    def effets(self, effets, chemin):
        if not isinstance(effets, dict) or not effets:
            self.erreur("« effets » : dictionnaire variable: valeur attendu", chemin)
            return
        for nom, valeur in effets.items():
            variable = self.projet.variables.get(nom)
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
        initial = {nom: variable["defaut"] for nom, variable in self.projet.variables.items()}
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
        if fiche.get("suite"):
            return [(fiche["suite"], etat, "suite", ())]
        if fiche.get("retour"):
            self.rapport.avertir(self.projet.ou(sid), "scène à « retour » atteinte sans « appel » : son return termine la partie")
        etats = self.ex.fins.setdefault(sid, [])
        if etat not in etats:
            etats.append(etat)
            self.ex.fins_routes.append({"fin": sid, "etat": etat, "choix": choix})
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
        variable = self.projet.variables.get(nom, {})
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
        if self.ex.complete and not self.ex.fins:
            self.rapport.erreur("exploration", "aucune route n'atteint une fin (« fin: true »)")


def routes_de_test(exploration: Exploration, maximum: int = ROUTES_MAX) -> list:
    """Petit ensemble de routes complètes qui couvre toutes les fins et tous les choix
    proposés (glouton : on prend à chaque fois la route qui couvre le plus de nouveautés)."""
    candidates = sorted(exploration.fins_routes, key=lambda r: (r["fin"], [c[2] for c in r["choix"]]))

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
    lignes += ["", "", "label start:", f"    jump {projet.bible['debut'].lower()}", ""]
    return "\n".join(lignes)


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
            lignes.append(f"{marge}scene{' ' + valeur if valeur else ''}{_avec(element)}")
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
        if _est_nombre(projet.variables[nom]["defaut"]):
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


def _routes_json(projet: Projet, routes: list) -> str:
    """Routes attendues, rejouées par tests/run_tests.gd : l'état final calculé par
    l'explorateur Python doit être celui de l'interpréteur Godot, dans chaque langue
    (« choix_traduits » : les mêmes choix, tels qu'affichés dans la traduction)."""
    traduits = {code: traductions_de(projet, code)[1] for code in projet.langues_cibles}
    donnees = {"_genere_par": MARQUEUR, "routes": []}
    for numero, route in enumerate(routes, 1):
        choix = [libelle for _, _, libelle in route["choix"]]
        entree = {"nom": f"route_{numero:02d}", "choix": choix, "fin": route["fin"].lower(), "etat_final": route["etat"]}
        if traduits:
            entree["choix_traduits"] = {code: [textes.get(libelle, libelle) for libelle in choix]
                                        for code, textes in traduits.items()}
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
            lignes += ["", "", f"testcase route_{numero:02d}{suffixe}:", "    $ _test.timeout = 30.0",
                       "    $ _test.transition_timeout = 0.05",
                       f"    $ renpy.game.persistent._seen_ever.pop({fin}, None)",
                       f"    $ renpy.game.persistent._seen_ever.pop(renpy.astsupport.hash64({fin}), None)",
                       '    pause until screen "main_menu"']
            if plusieurs:
                # Un changement de langue reconstruit les styles : on le laisse finir avant Start(),
                # sinon Ren'Py peut rejouer l'action une fois la partie commencée.
                lignes += [f"    run Language({_chaine(_nom_renpy(code))})", "    pause 0.5"]
            lignes.append("    run Start()")
            for rang, (_, _, libelle) in enumerate(route["choix"]):
                # Pause : un clic pendant la transition d'apparition du menu serait perdu.
                lignes += ['    advance until screen "choice"', "    pause 0.5"]
                if suffixe and numero == 1 and rang == 0:
                    lignes.append(f'    screenshot "renpy_{code}.png"')
                lignes.append(f"    click {_chaine(textes.get(libelle, libelle))}")
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
                   '    $ assert all(renpy.seen_label(e["label"]) for e in galerie_entrees), galerie_entrees']
    return "\n".join(lignes) + "\n"


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
        for sid in projet.ordre():
            libelles = [str(option["libelle"]) for option in options_de(projet.scenes[sid])[1]]
            affiches = [str(traduits[libelle]["texte"]) if libelle in traduits else libelle for libelle in libelles]
            for double in sorted({libelle for libelle in affiches if affiches.count(libelle) > 1}):
                rapport.erreur(ou, f"{sid} : deux choix du même menu s'affichent « {double} »")
            for court in affiches:
                for long in affiches:
                    if court != long and court in long:
                        rapport.avertir(ou, f"{sid} : « {court} » est contenu dans « {long} » : "
                                            "les tests Ren'Py risquent de cliquer le mauvais choix")
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
        if nom not in projet.variables:
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
                noter(images, element["decor"], sid, "décor")
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
    return images, videos


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


def production(projet: Projet) -> tuple[str, str]:
    """Renvoie (markdown, résumé) de la liste des images et vidéos à produire."""
    images, videos = inventaire(projet)
    definitives, provisoires = _index_images(projet.racine)
    liste_provisoires = _videos_provisoires(projet.racine)
    etats_images = {}
    for nom in images:
        cle = nom.lower()
        etats_images[nom] = ("définitive", definitives[cle]) if cle in definitives else \
            ("provisoire", provisoires[cle]) if cle in provisoires else ("manquante", "")
    etats_videos = {relatif: _etat_video(projet.racine, relatif, liste_provisoires) for relatif in videos}

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
    declarees |= {nom for lieu in projet.lieux.values() if isinstance(lieu, dict) for nom in _liste(lieu.get("decors"))}
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
    if exploration is not None:
        inatteintes = [sid for sid in projet.ordre() if sid not in exploration.entrees]
        if inatteintes:
            lignes.append("    classDef inatteinte stroke:#c00,stroke-dasharray:5 5")
            lignes.append(f"    class {','.join(inatteintes)} inatteinte")
    return ("# Graphe des routes\n\nGénéré par `tools/fiches.py graphe`. Formes : rectangle = scène, "
            "ovale = fin, double cadre = scène appelée ; pointillés = appel.\n\n```mermaid\n"
            + "\n".join(lignes) + "\n```\n")


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
                   "", f"Décors disponibles : {', '.join(_liste(lieu.get('decors'))) or 'aucun'}.", ""]
    lignes += ["## Personnages présents", ""]
    for pid in _liste(fiche.get("personnages")):
        lignes += [f"### {pid}", "", "```yaml", _yaml(projet.personnages.get(pid)), "```", ""]
    etats = exploration.entrees.get(sid, [])
    lignes += ["## État possible à l'entrée", ""]
    if not etats:
        lignes += ["Scène jamais atteinte depuis « debut » : reliez-la d'abord à une autre scène.", ""]
    for nom, variable in projet.variables.items():
        valeurs = sorted({_litteral(etat.get(nom)) for etat in etats})
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
    if fiche.get("fin"):
        lignes.append("- fin de partie")
    if fiche.get("retour"):
        lignes.append("- retour à la scène qui l'a appelée")
    lignes += ["", "## Règles éditoriales", ""] + [f"- {regle}" for regle in _liste(projet.bible.get("regles_editoriales"))]
    lignes += ["", "## Format attendu", "",
               "Éléments du contenu : narration, <personnage>, decor (+ transition), montrer (+ position, transition), "
               "cacher, video, pause, musique, son, effets, si / alors / sinon_si / sinon, appel. "
               "Textes entre guillemets. Détails : contenu/LISEZMOI.md. Fiche actuelle :", "",
               "```yaml", _yaml(fiche), "```", ""]
    return "\n".join(lignes)


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
    commandes.add_parser("graphe", help="graphe des routes → contenu/graphe.md")
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
        print("Graphe : contenu/graphe.md")
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
