"""
check.py — vérifie les textes de sortie des trois versions, sans réseau
ni token. Lancer avec : make check

Ce que ça contrôle :
  · le parseur local sur une soixantaine de formulations
  · les formats de date, d'heure et de délai
  · les lignes de confirmation, les listes, les boutons, l'aide, les stats
  · les outils qui ne sortent pas de la machine (rappels, tâches, notes,
    mémoire, calcul)
  · quelques règles de style : pas de markdown, pas de double espace,
    pas de « Tu dois » ni d'identifiant qui traîne dans un message
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import tempfile
from datetime import timedelta

os.environ.setdefault("TELEGRAM", "test")
os.environ.setdefault("GROQ", "test")
os.environ.setdefault("MY_ID", "1")
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "check.db")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VERT, ROUGE, GRIS, RAZ = "\033[32m", "\033[31m", "\033[90m", "\033[0m"
erreurs: list[str] = []
CHAT = 4242


def ok(cond, message):
    if not cond:
        erreurs.append(message)
    return cond


def titre(t):
    print(f"\n{GRIS}{'─' * 68}{RAZ}\n  {t}\n")


# ── faux job queue : les rappels sont enregistrés, rien n'est planifié ──

class FauxJob:
    def __init__(self, name):
        self.name = name

    def schedule_removal(self):
        pass


class FauxJobQueue:
    def __init__(self):
        self.jobs_: list[FauxJob] = []

    def run_once(self, cb, when=None, chat_id=None, data=None, name=None):
        self.jobs_.append(FauxJob(name))

    def run_daily(self, cb, time=None, chat_id=None, data=None, name=None):
        self.jobs_.append(FauxJob(name))

    def get_jobs_by_name(self, name):
        return [j for j in self.jobs_ if j.name == name]

    def jobs(self):
        return list(self.jobs_)


class FauxCtx:
    def __init__(self):
        self.job_queue = FauxJobQueue()
        self.chat_data: dict = {}


# ── batterie de phrases ────────────────────────────────────────────────
# (phrase, doit être reconnu en local)

PHRASES = [
    ("rappelle-moi le garage dans 20 min", True),
    ("rappelle-moi d'appeler Paul dans 1h30", True),
    ("rappelle moi le dentiste demain 10h", True),
    ("rappelle-moi le dentiste demain à 10h30", True),
    ("rappelle-moi la réunion jeudi 14h30", True),
    ("rappelle-moi de courir ce soir", True),
    ("rappelle-moi de courir à 18h30", True),
    ("rappelle-moi la poubelle ce soir 20h", True),
    ("rappelle-moi dans 20 min de sortir le plat", True),
    ("rappelle-moi le 20 septembre à 14h de payer", True),
    ("rappelle-moi de payer le loyer le 5", True),
    ("rappelle-moi de sortir dans 3 jours", True),
    ("rappelle-moi la révision dans 2 semaines", True),
    ("rappelle-moi le rdv après-demain 9h", True),
    ("rappelle-moi le colis demain matin", True),
    ("rappelle-moi le médecin mardi 11h", True),
    ("rappelle-moi de manger à midi", True),
    ("note acheter du lait demain", True),
    ("n'oublie pas de m'appeler lundi à 9h", True),
    ("penser à la lessive samedi", True),
    ("rdv médecin mardi 11h", True),
    ("tous les jours vitamines 8h", True),
    ("chaque matin méditation", True),
    ("chaque soir fermer les volets", True),
    ("chaque lundi sortir la poubelle 20h", True),
    ("tous les mardis piscine 18h", True),
    ("en semaine réveil 7h30", True),
    ("le week-end grasse matinée 10h", True),
    ("rappelle-moi tous les jours à 22h de me coucher", True),
    # ce qui doit partir au modèle plutôt que d'être mal deviné
    ("rappelle-moi la réunion de 14h à 16h", False),
    ("quelle heure est-il", False),
    ("il est 15h30 non ?", False),
    ("rappelle-moi", False),
    ("rappelle-moi de faire un truc", False),
    ("je cours tous les jours", False),
    ("c'est quoi le prix du bitcoin", False),
    ("il fait quel temps demain", False),
    ("merci", False),
]

RACCOURCIS = [("dentiste demain 10h", True), ("poubelle dans 2 h", True),
              ("18h30 courir", True), ("acheter du pain", False)]


def verif_parseur(J, nom):
    titre(f"{nom} · parseur local  ({len(PHRASES)} phrases)")
    for phrase, attendu in PHRASES:
        p = J.parse_local(phrase)
        trouve = p is not None
        marque = VERT + "✓" + RAZ if trouve == attendu else ROUGE + "✗" + RAZ
        ok(trouve == attendu,
           f"{nom} : « {phrase} » → {'reconnu' if trouve else 'non reconnu'}, "
           f"attendu {'reconnu' if attendu else 'non reconnu'}")
        if p:
            r = faux_rappel(J, p)
            sortie = J.ligne(r)
            print(f"  {marque} {sortie:<50} {GRIS}{phrase}{RAZ}")
            verif_style(sortie, f"{nom} / {phrase}")
            ok(p["dt"] > J.now() or p["kind"] == "recur",
               f"{nom} : « {phrase} » programmé dans le passé")
            ok(len(p["texte"]) > 1,
               f"{nom} : « {phrase} » texte de rappel vide ou trop court")
        else:
            print(f"  {marque} {'—':<50} {GRIS}{phrase}{RAZ}")

    print()
    for phrase, attendu in RACCOURCIS:
        p = J.parse_local(phrase, strict=False)
        marque = VERT + "✓" + RAZ if (p is not None) == attendu else ROUGE + "✗" + RAZ
        ok((p is not None) == attendu, f"{nom} : raccourci « + {phrase} »")
        rendu = J.ligne(faux_rappel(J, p)) if p else "— (devient une tâche)"
        print(f"  {marque} {rendu:<50} {GRIS}+ {phrase}{RAZ}")


def faux_rappel(J, p):
    hm = f"{p['dt'].hour:02d}:{p['dt'].minute:02d}"
    recur = p["kind"] == "recur"
    return {"id": "abc123", "chat_id": CHAT, "texte": p["texte"],
            "quand": hm if recur else p["dt"].isoformat(timespec="minutes"),
            "recurrent": hm if recur else None,
            "jours": ",".join(map(str, p["jours"])) if p["jours"] else None,
            "fired": 0}


# ── style : ce qui ne doit jamais apparaître dans un message ────────────

INTERDIT = [
    (re.compile(r"\*\*|^#{1,6} |`"), "markdown"),
    (re.compile(r"Tu dois "), "formule « Tu dois »"),
    (re.compile(r"  +"), "double espace"),
    (re.compile(r"\bNone\b|\bnull\b"), "valeur None visible"),
    (re.compile(r"[0-9a-f]{6,}"), "identifiant technique visible"),
]


def verif_style(texte, contexte, sauf=()):
    for rx, quoi in INTERDIT:
        if quoi in sauf:
            continue
        if rx.search(texte):
            erreurs.append(f"{contexte} : {quoi} → {texte!r}")


def verif_formats(J, nom):
    titre(f"{nom} · formats de date et de délai")
    n = J.now()
    cas = [
        ("dans 40 s", n + timedelta(seconds=40)),
        ("dans 20 min", n + timedelta(minutes=20)),
        ("dans 1 h 30", n + timedelta(minutes=90)),
        ("dans 5 h", n + timedelta(hours=5)),
        ("demain", n + timedelta(days=1)),
        ("dans 3 jours", n + timedelta(days=3)),
        ("dans 6 jours", n + timedelta(days=6)),
        ("dans 40 jours", n + timedelta(days=40)),
        ("l'an prochain", n + timedelta(days=400)),
    ]
    for label, dt in cas:
        quand, delta = J.fmt_when(dt), J.fmt_delta(dt)
        print(f"  {label:<14} {GRIS}→{RAZ} {quand:<26} {delta}")
        verif_style(quand + " " + delta, f"{nom} / format {label}")
        ok(not quand.endswith(" "), f"{nom} : format {label} finit par un espace")

    print()
    for rec, jours, attendu in [("08:00", None, "tous les jours 8h"),
                                ("20:00", "0", "chaque lundi 20h"),
                                ("07:30", "0,1,2,3,4", "en semaine 7h30"),
                                ("10:00", "5,6", "le week-end 10h"),
                                ("09:00", "0,2", "lun, mer 9h")]:
        rendu = J.label_recur(rec, jours)
        marque = VERT + "✓" + RAZ if rendu == attendu else ROUGE + "✗" + RAZ
        ok(rendu == attendu, f"{nom} : label_recur({rec}, {jours}) = {rendu!r}, "
                             f"attendu {attendu!r}")
        print(f"  {marque} {rendu}")


# ── outils hors ligne ──────────────────────────────────────────────────

def verif_outils(J, nom):
    titre(f"{nom} · outils, sans réseau")
    ctx = FauxCtx()
    run = asyncio.run
    # les trois modules partagent le même fichier de base : on repart de zéro
    with J.db() as con:
        for t in ("reminders", "tasks", "notes", "facts"):
            try:
                con.execute(f"DELETE FROM {t} WHERE chat_id = ?", (CHAT,))
            except Exception:
                pass

    demain = (J.now() + timedelta(days=1)).replace(hour=10, minute=0,
                                                   second=0, microsecond=0)
    r = run(J.reminders(action="create", texte="dentiste",
                        quand=demain.isoformat(timespec="minutes"),
                        ctx=ctx, chat_id=CHAT))
    ok("confirmation" in r, f"{nom} : create ne renvoie pas de confirmation")
    print(f"  create   {r.get('confirmation')}")
    verif_style(r.get("confirmation", ""), f"{nom} / create")

    r2 = run(J.reminders(action="create", texte="vitamines", quand="08:00",
                         repeter="jour", ctx=ctx, chat_id=CHAT))
    print(f"  create   {r2.get('confirmation')}")
    r3 = run(J.reminders(action="create", texte="piscine", quand="18:00",
                         repeter="mardi", ctx=ctx, chat_id=CHAT))
    print(f"  create   {r3.get('confirmation')}")
    ok("chaque mardi" in r3.get("confirmation", ""),
       f"{nom} : repeter=mardi mal rendu → {r3}")

    for mauvais in [dict(action="create", texte="x", quand="pas une date"),
                    dict(action="create", texte="x", quand="2000-01-01T09:00"),
                    dict(action="create", texte="", quand="10:00"),
                    dict(action="create", texte="x", quand="26:00",
                         repeter="jour"),
                    dict(action="nawak")]:
        e = run(J.reminders(**mauvais, ctx=ctx, chat_id=CHAT))
        ok("error" in e, f"{nom} : {mauvais} aurait dû être refusé → {e}")
        print(f"  refus    {GRIS}{e.get('error')}{RAZ}")

    liste = run(J.reminders(action="list", ctx=ctx, chat_id=CHAT))
    print(f"  list     {liste}")
    ok(len(liste["rappels"]) == 3, f"{nom} : la liste devrait contenir 3 rappels")

    rs = J.fetch_reminders(CHAT)
    print("  boutons  " + " | ".join(f"✕ {x['texte'][:28]} · {x['_label']}"
                                     for x in rs))
    for x in rs:
        verif_style(f"✕ {x['texte']} · {x['_label']}", f"{nom} / bouton")

    ann = run(J.reminders(action="cancel", id=rs[0]["id"], ctx=ctx, chat_id=CHAT))
    print(f"  cancel   {ann.get('confirmation')}")
    ok("confirmation" in ann, f"{nom} : cancel muet")
    ok("error" in run(J.reminders(action="cancel", id="zzzz", ctx=ctx,
                                  chat_id=CHAT)),
       f"{nom} : cancel d'un id inconnu devrait échouer")

    if "taches" in J.REGISTRY:
        t = run(J.taches(action="add", texte="acheter du pain",
                         ctx=ctx, chat_id=CHAT))
        print(f"  tâche    {t.get('confirmation')}")
        tl = run(J.taches(action="list", ctx=ctx, chat_id=CHAT))
        tid = tl["taches"][0]["id"]
        print(f"  done     {run(J.taches(action='done', id=tid, ctx=ctx, chat_id=CHAT)).get('confirmation')}")
        ok(run(J.taches(action="list", ctx=ctx, chat_id=CHAT))["taches"] == [],
           f"{nom} : la tâche validée reste dans la liste")

    if "memoire" in J.REGISTRY:
        run(J.memoire(action="retenir", cle="allergie", valeur="arachides",
                      ctx=ctx, chat_id=CHAT))
        f = run(J.memoire(action="lister", ctx=ctx, chat_id=CHAT))
        print(f"  mémoire  {f}")
        ok(f["faits"] and f["faits"][0]["valeur"] == "arachides",
           f"{nom} : la mémoire n'a pas retenu")
        sm = J.system_msg(CHAT)["content"]
        ok("arachides" in sm, f"{nom} : les faits n'entrent pas dans le prompt")

    if "calcul" in J.REGISTRY:
        for expr, att in [("(1200*1.2)/3", 480), ("2**10", 1024),
                          ("round(7/3, 2)", 2.33)]:
            v = run(J.calcul(expression=expr))
            ok(v.get("resultat") == att,
               f"{nom} : calcul({expr}) = {v}, attendu {att}")
            print(f"  calcul   {expr} = {v.get('resultat')}")
        for mauvais in ["__import__('os')", "open('/etc/passwd')", "1/0",
                        "9**9**9"]:
            v = run(J.calcul(expression=mauvais))
            ok("error" in v, f"{nom} : calcul({mauvais}) aurait dû être refusé")
        print(f"  refus    {GRIS}expressions dangereuses bloquées{RAZ}")

    if "notes" in J.REGISTRY:
        run(J.notes(action="add", texte="idée : refaire le site",
                    ctx=ctx, chat_id=CHAT))
        ns = run(J.notes(action="search", texte="site", ctx=ctx, chat_id=CHAT))
        ok(ns["notes"], f"{nom} : note introuvable après ajout")
        print(f"  note     {ns['notes'][0]['texte']}")


def verif_textes(J, nom):
    titre(f"{nom} · aide et messages fixes")
    print("  " + J.AIDE.replace("\n", "\n  "))
    verif_style(J.AIDE, f"{nom} / aide", sauf=("double espace",))
    ok(len(J.AIDE) < 1200, f"{nom} : l'aide dépasse 1200 caractères")
    ok("markdown" not in J.SYSTEM.lower() or "aucun markdown" in J.SYSTEM,
       f"{nom} : le prompt système ne dit pas d'éviter le markdown")
    for mot in ("confirmation", "outils"):
        ok(mot in J.SYSTEM, f"{nom} : le prompt système ne parle pas de {mot}")

    if hasattr(J, "texte_brief"):
        brief = asyncio.run(J.texte_brief(CHAT))
        print(f"\n  {GRIS}brief du matin :{RAZ}\n  " + brief.replace("\n", "\n  "))
        verif_style(brief, f"{nom} / brief")


def main():
    modules = [("light", "joorvis_light"), ("mid", "joorvis_mid"),
               ("high", "joorvis_high")]
    for nom, mod in modules:
        J = __import__(mod)
        J.db_init()
        print(f"\n{'═' * 70}\n  {mod}  ·  {len(J.REGISTRY)} outils : "
              f"{', '.join(J.REGISTRY)}\n{'═' * 70}")
        verif_parseur(J, nom)
        verif_formats(J, nom)
        verif_outils(J, nom)
        verif_textes(J, nom)

    print(f"\n{'═' * 70}")
    if erreurs:
        print(f"{ROUGE}  {len(erreurs)} problème(s){RAZ}\n")
        for e in erreurs:
            print(f"   · {e}")
        sys.exit(1)
    print(f"{VERT}  tout est bon{RAZ}\n")


if __name__ == "__main__":
    main()
