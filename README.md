# Joorvis

Assistant personnel Telegram, en trois tailles. Un seul utilisateur : le tien.
Tout le reste est ignoré en silence.

Le principe qui tient l'ensemble : **ce qui peut être compris sans le modèle
ne coûte pas un token.** « rappelle-moi le dentiste demain 10h » est traité
par une analyse locale, en quelques millisecondes et gratuitement. Le modèle
n'entre en jeu que pour ce qui demande vraiment de comprendre.

```
make install     # crée .venv, installe, prépare .env
                 # → remplis TELEGRAM, GROQ et MY_ID
make mid         # lance
```

---

## Choisir sa version

| | light | mid | high |
|---|---|---|---|
| Rappels ponctuels, quotidiens, hebdo, jours ouvrés | ✅ | ✅ | ✅ |
| Analyse locale sans token | ✅ | ✅ | ✅ |
| Vocaux transcrits | ✅ | ✅ | ✅ |
| Recherche web, lecture de page | ✅ | ✅ | ✅ |
| Cours crypto | ✅ | ✅ | ✅ |
| Tâches | | ✅ | ✅ |
| Météo, calcul exact, devises | | ✅ | ✅ |
| Mémoire longue durée | | ✅ | ✅ |
| Brief du matin | | ✅ assemblé | ✅ rédigé |
| Photos lues par un modèle de vision | | | ✅ |
| Documents txt, md, csv, json, pdf | | | ✅ |
| Notes, Wikipédia, recherche approfondie | | | ✅ |
| Export, purge, stats sur 7 jours | | | ✅ |
| Outils exposés au modèle | 3 | 8 | 10 |
| Prompt système | ~120 tokens | ~230 | ~280 |

**light** si tu veux surtout des rappels et que la facture reste invisible.
**mid** pour l'usage quotidien : c'est la version par défaut.
**high** si tu veux lui envoyer une photo de ticket, un PDF, et qu'il se
débrouille.

Les trois partagent la même base `joorvis.db` et le même format : tu peux
passer de l'une à l'autre sans rien perdre. Les colonnes manquantes sont
ajoutées automatiquement au démarrage.

---

## Installation

1. **Créer le bot** — parle à [@BotFather](https://t.me/BotFather),
   `/newbot`, récupère le token.
2. **Ton identifiant** — parle à [@userinfobot](https://t.me/userinfobot),
   note le nombre.
3. **Clé Groq** — [console.groq.com](https://console.groq.com), gratuite.
4. `make install`, remplis `.env`, puis `make mid`.

Pour que ça tourne en permanence sur un serveur ou un Raspberry :

```
make service BOT=mid
sudo cp joorvis.service /etc/systemd/system/
sudo systemctl enable --now joorvis
make logs
```

---

## Parler au bot

### Ce qui ne coûte rien

Ces formulations sont reconnues localement. Le modèle n'est jamais appelé.

```
rappelle-moi le garage dans 20 min
rappelle-moi d'appeler Paul dans 1h30
rappelle-moi le dentiste demain 10h
rappelle-moi le colis demain matin
rappelle-moi la réunion jeudi 14h30
rappelle-moi de courir ce soir
rappelle-moi de manger à midi
rappelle-moi le 20 septembre à 14h de payer
rappelle-moi de payer le loyer le 5
rappelle-moi la révision dans 2 semaines

tous les jours vitamines 8h
chaque matin méditation
chaque lundi sortir la poubelle 20h
tous les mardis piscine 18h
en semaine réveil 7h30
le week-end grasse matinée 10h
```

Déclencheurs acceptés : `rappelle-moi`, `rappel`, `rdv`, `note`,
`n'oublie pas de`, `penser à`, `faut que je`.

Moments de la journée, quand l'heure n'est pas précisée :
matin `9h` · midi `12h` · après-midi `14h` · soir `19h` · nuit `22h` ·
sans indication `9h`.

### Le raccourci `+`

Le préfixe `+` (ou `.`) rend le verbe inutile.

```
+ dentiste demain 10h     → rappel, il y a une heure
+ poubelle dans 2 h       → rappel
+ acheter du pain         → tâche (mid et high), il n'y a pas d'heure
```

### Ce qui part au modèle

Tout le reste : questions, météo, web, calcul, et toute phrase de rappel
qui sort des schémas ci-dessus. Le bot appelle ses outils tout seul et
répond en une fois.

Quand une phrase est **ambiguë**, elle part au modèle plutôt que d'être
mal devinée. « rappelle-moi la réunion de 14h à 16h » contient deux heures :
le parseur local passe la main au lieu de choisir au hasard.

### Commandes

| | light | mid | high |
|---|---|---|---|
| `/r` rappels, avec bouton d'annulation | ✅ | ✅ | ✅ |
| `/undo` annule la dernière action | ✅ | ✅ | ✅ |
| `/stats` consommation | ✅ | ✅ | ✅ 7 jours |
| `/reset` oublie le fil en cours | ✅ | ✅ | ✅ |
| `/t` tâches | | ✅ | ✅ |
| `/memoire` ce qu'il retient de toi | | ✅ | ✅ |
| `/brief` le point du jour | | ✅ | ✅ |
| `/notes [mot]` | | | ✅ |
| `/export` toutes tes données en JSON | | | ✅ |
| `/purge` effacer, avec confirmation | | | ✅ |

Un rappel qui sonne propose `+10 min`, `+1 h`, `✓`.

---

## Ce qui a été corrigé par rapport aux versions précédentes

Ces points venaient des scripts d'origine et sont réglés dans les trois
versions.

**« Tu dois le dentiste demain à 10h ».** La confirmation reprenait un
gabarit qui ne tenait pas debout dès que la tâche n'était pas un verbe.
Format unique désormais, le même en local et via le modèle :

```
⏰ garage · 16h55 (dans 20 min)
⏰ dentiste · demain 10h
⏰ vitamines · tous les jours 8h
⏰ réveil · en semaine 7h30
```

Le délai n'apparaît que sous 3 heures — au-delà, l'heure suffit et la
parenthèse n'apportait rien. Les outils renvoient la ligne toute faite dans
un champ `confirmation` que le modèle doit recopier tel quel : il ne peut
plus reformuler une date à sa façon.

**Le premier caractère du rappel disparaissait.** « rappelle-moi d'appeler
Paul » donnait « ppeler Paul » : le nettoyage retirait « a » ou « de » sans
vérifier qu'un espace suivait.

**« sortir la poubelle 20h » se lisait « le 2 » puis « 0h ».** Les motifs
temporels pouvaient s'accrocher au milieu d'un mot. Ils exigent maintenant
un mot entier.

**Les connexions SQLite n'étaient jamais fermées.** `with sqlite3.connect()`
valide la transaction mais ne ferme rien : les descripteurs s'accumulaient à
chaque rappel. Remplacé par un gestionnaire de contexte qui ferme, avec
`journal_mode=WAL` et un délai d'attente.

**Le snooze relisait le texte du message Telegram.** `removeprefix("⏰ ")`
sur le message affiché : un rappel déjà repoussé revenait déformé. Le texte
vient maintenant de la base, et le rappel garde son identifiant.

**« dans 20 min » affichait « dans 19 min »** — troncature au lieu d'arrondi.

**`MY_ID` absent faisait planter au démarrage** avec une trace Python
illisible. Message clair désormais, sur les trois variables obligatoires.

**Une édition de message ratée perdait la réponse.** Le statut « · · · »
devient la réponse ; si Telegram refuse l'édition, la réponse est envoyée
comme nouveau message au lieu de disparaître.

**Le brief du matin ne partait pas si le modèle était indisponible.**
Il est maintenant assemblé sans modèle, et seulement embelli par lui en
version high.

Ajouté au passage : récurrences hebdomadaires et jours ouvrés, moments de la
journée, dates du type « le 20 septembre », repère temporel en début de
phrase (« rappelle-moi dans 20 min de sortir le plat »), refus explicite des
phrases ambiguës, rattrapage des rappels manqués pendant un arrêt, et
`check.py`.

---

## Vérifier

```
make check
```

Aucun réseau, aucun token. Le script passe une soixantaine de formulations
dans le parseur des trois versions, affiche la sortie exacte de chacune,
teste les outils hors ligne (rappels, tâches, notes, mémoire, calcul, et
leurs cas d'erreur), et refuse : markdown dans un message, double espace,
`None` visible, identifiant technique affiché, formule « Tu dois ».

```
make lint      # ruff ou pyflakes
make db        # ce que contient la base
make backup    # copie datée
```

---

## Réglages

Tout est dans `.env`, rien à toucher dans le code.

| Variable | Défaut | Rôle |
|---|---|---|
| `TELEGRAM` | — | token BotFather |
| `GROQ` | — | clé console.groq.com |
| `MY_ID` | — | ton identifiant Telegram |
| `CITY` | `Paris` | ville par défaut (mid, high) |
| `BRIEF` | `off` / `7:30` | heure du brief, ou `off` |
| `TZ_NAME` | `Europe/Paris` | fuseau |
| `DB_PATH` | `joorvis.db` | base |
| `CHAT_MODEL` | `openai/gpt-oss-120b` | modèle principal |
| `AUDIO_MODEL` | `whisper-large-v3-turbo` | transcription des vocaux |
| `VISION_MODEL` | `llama-4-scout` | lecture des photos (high) |

Si un modèle disparaît du catalogue Groq, seule la ligne correspondante
change — le code n'en dépend pas.

Dans le fichier, en haut : `MAX_TURNS` (tours gardés), `TOKEN_BUDGET`
(seuil d'élagage), `TTL` (inactivité avant oubli), `MAX_STEPS` (garde-fou
de la boucle d'outils).

---

## Comment c'est fait

**Un message arrive.** S'il commence par `+`, le verbe devient optionnel.
Le parseur local cherche une récurrence, puis un repère temporel, en début
ou en fin de phrase. Ce qui reste devient le texte du rappel — sauf s'il
contient encore une heure ou un jour, signe que la phrase est trop ambiguë
pour être devinée : elle part alors au modèle.

**Sinon, la boucle d'outils.** Le modèle voit les outils, en appelle
plusieurs en parallèle, reçoit les résultats, recommence si besoin
(`MAX_STEPS` fois au plus). Le message « · · · » est édité au fur et à
mesure pour montrer ce qui tourne, puis devient la réponse : un seul
message par requête.

**L'historique est purgé des échanges d'outils** après chaque tour. C'est ce
qui empêche une recherche web de peser sur les vingt messages suivants.
Au-delà de `TOKEN_BUDGET`, les tours les plus anciens sortent.

**Les outils sont déclarés par leur signature.** Le décorateur `@tool` lit
les annotations et la docstring pour produire le schéma JSON envoyé au
modèle. Ajouter un outil, c'est écrire une fonction :

```python
@tool
async def train(depart: Annotated[str, "Gare de départ"]) -> dict:
    """Prochains départs depuis une gare."""
    ...
```

`ctx` et `chat_id` sont masqués au modèle et injectés à l'exécution.

**Le contenu web est marqué comme non fiable** dans la réponse de l'outil,
et le prompt système rappelle qu'une page est une donnée à lire, jamais un
ordre à suivre.

**Les rappels survivent au redémarrage.** Ils sont en base, rechargés au
démarrage ; ceux qui sont tombés pendant l'arrêt sont annoncés en une fois.
Un rappel qui a sonné reste en base le temps qu'un « +10 min » puisse le
relire, puis disparaît.

---

## Fichiers

```
joorvis_light.py   version ultra light
joorvis_mid.py     version équilibrée
joorvis_high.py    version complète
check.py           vérification des sorties, sans réseau
Makefile           make pour voir les cibles
requirements.txt
.env.example
```

Chaque version est un fichier autonome : tu peux en déployer une sans les
autres. Le noyau commun (parseur, formats, base) est identique dans les
trois, ce qui rend un correctif facile à reporter.
