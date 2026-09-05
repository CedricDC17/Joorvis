# Joorvis

Assistant Telegram mono-utilisateur.

Le traitement des rappels compatibles avec le parseur local est effectué sans appel au modèle. Les autres requêtes passent par une boucle d’outils.

## Installation

```bash
make install
```

`make install` crée l’environnement virtuel, installe les dépendances et prépare `.env`.

Variables obligatoires :

* `TELEGRAM` : token du bot Telegram
* `GROQ` : clé API Groq
* `MY_ID` : identifiant Telegram de l’utilisateur autorisé

Lancement :

```bash
make mid
```

### Service systemd

```bash
make service BOT=mid
sudo cp joorvis.service /etc/systemd/system/
sudo systemctl enable --now joorvis
make logs
```

## Versions

| Fonctionnalité                                    | light |      mid |   high |
| ------------------------------------------------- | ----: | -------: | -----: |
| Rappels ponctuels                                 |     ✅ |        ✅ |      ✅ |
| Rappels quotidiens / hebdomadaires / jours ouvrés |     ✅ |        ✅ |      ✅ |
| Analyse locale des rappels                        |     ✅ |        ✅ |      ✅ |
| Transcription des vocaux                          |     ✅ |        ✅ |      ✅ |
| Recherche web / lecture de page                   |     ✅ |        ✅ |      ✅ |
| Cours crypto                                      |     ✅ |        ✅ |      ✅ |
| Tâches                                            |       |        ✅ |      ✅ |
| Météo / calcul / devises                          |       |        ✅ |      ✅ |
| Mémoire longue durée                              |       |        ✅ |      ✅ |
| Brief du matin                                    |       | assemblé | rédigé |
| Vision                                            |       |          |      ✅ |
| Documents txt, md, csv, json, pdf                 |       |          |      ✅ |
| Notes / Wikipédia / recherche approfondie         |       |          |      ✅ |
| Export / purge / statistiques                     |       |          |      ✅ |
| Outils exposés au modèle                          |     3 |        8 |     10 |

Les trois versions utilisent la même base SQLite `joorvis.db`. Les migrations de colonnes manquantes sont effectuées au démarrage.

## Parsing local des rappels

Les formulations suivantes sont traitées localement :

```text
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

Déclencheurs :

```text
rappelle-moi
rappel
rdv
note
n'oublie pas de
penser à
faut que je
```

Heures implicites :

| Expression        | Heure |
| ----------------- | ----: |
| matin             | 09:00 |
| midi              | 12:00 |
| après-midi        | 14:00 |
| soir              | 19:00 |
| nuit              | 22:00 |
| aucune indication | 09:00 |

### Préfixe `+`

Le préfixe `+` ou `.` permet d'omettre le verbe :

```text
+ dentiste demain 10h
+ poubelle dans 2 h
+ acheter du pain
```

Le dernier exemple crée une tâche en `mid` et `high`.

### Requête ambiguë

Une phrase contenant plusieurs repères temporels incompatibles ou non résolus n'est pas interprétée localement. Elle est transmise au modèle.

Exemple :

```text
rappelle-moi la réunion de 14h à 16h
```

## Requêtes traitées par le modèle

Les requêtes qui ne correspondent pas au parseur local sont transmises au modèle :

* questions ;
* météo ;
* recherche web ;
* calcul ;
* requêtes de rappel hors schéma local ;
* autres opérations nécessitant les outils.

Le modèle peut appeler plusieurs outils en parallèle et recommencer jusqu'à `MAX_STEPS`.

## Commandes Telegram

| Commande       | light | mid | high |
| -------------- | ----: | --: | ---: |
| `/r` rappels   |     ✅ |   ✅ |    ✅ |
| `/undo`        |     ✅ |   ✅ |    ✅ |
| `/stats`       |     ✅ |   ✅ |    ✅ |
| `/reset`       |     ✅ |   ✅ |    ✅ |
| `/t` tâches    |       |   ✅ |    ✅ |
| `/memoire`     |       |   ✅ |    ✅ |
| `/brief`       |       |   ✅ |    ✅ |
| `/notes [mot]` |       |     |    ✅ |
| `/export`      |       |     |    ✅ |
| `/purge`       |       |     |    ✅ |

Un rappel déclenché expose les actions `+10 min`, `+1 h` et `✓`.

## Format des rappels

Le format de confirmation est commun au traitement local et au traitement via modèle :

```text
⏰ garage · 16h55 (dans 20 min)
⏰ dentiste · demain 10h
⏰ vitamines · tous les jours 8h
⏰ réveil · en semaine 7h30
```

Le délai relatif est affiché uniquement pour les échéances inférieures à trois heures.

Les outils retournent directement le texte de confirmation dans le champ `confirmation`. Le modèle doit reprendre cette valeur telle quelle.

## Corrections et contraintes du parseur

Le parseur :

* ne supprime pas le premier caractère du texte du rappel lors du nettoyage ;
* exige des limites de mots pour les motifs temporels ;
* refuse les formulations ambiguës ;
* reconnaît les récurrences hebdomadaires et les jours ouvrés ;
* reconnaît les moments de la journée ;
* reconnaît les dates comme `le 20 septembre` ;
* reconnaît un repère temporel placé au début de la phrase ;
* détecte les rappels manqués après un arrêt.

## Base de données

Les connexions SQLite sont gérées par contexte et fermées après utilisation.

Configuration SQLite :

* `journal_mode=WAL` ;
* délai d'attente configuré.

Les rappels sont persistants et rechargés au démarrage.

Les rappels échus pendant un arrêt sont signalés au redémarrage.

Un rappel déclenché reste en base jusqu'à ce que les actions de suivi puissent être effectuées.

## Boucle d'outils

Lorsqu'une requête nécessite le modèle :

1. le modèle reçoit les outils disponibles ;
2. il peut effectuer plusieurs appels en parallèle ;
3. les résultats sont réinjectés dans le contexte ;
4. la boucle continue jusqu'à obtention d'une réponse ou `MAX_STEPS` ;
5. le message Telegram initial est édité au fur et à mesure ;
6. l'historique des échanges d'outils est ensuite purgé.

`ctx` et `chat_id` ne sont pas exposés au modèle et sont injectés lors de l'exécution.

Les contenus provenant du web sont marqués comme non fiables. Une page web est traitée comme donnée et non comme instruction.

## Gestion du contexte

Les paramètres suivants contrôlent la mémoire de conversation :

* `MAX_TURNS` : nombre de tours conservés ;
* `TOKEN_BUDGET` : seuil d'élagage ;
* `TTL` : délai d'inactivité avant oubli ;
* `MAX_STEPS` : nombre maximal d'itérations de la boucle d'outils.

Lorsque `TOKEN_BUDGET` est dépassé, les tours les plus anciens sont supprimés.

## Déclaration des outils

Les outils sont définis à partir de leur signature :

```python
@tool
async def train(depart: Annotated[str, "Gare de départ"]) -> dict:
    """Prochains départs depuis une gare."""
    ...
```

Le décorateur `@tool` utilise les annotations et la docstring pour générer le schéma JSON transmis au modèle.

## Vérification

```bash
make check
```

`check.py` exécute les tests sans réseau ni token.

Les tests couvrent notamment :

* parsing des rappels ;
* récurrences ;
* tâches ;
* notes ;
* mémoire ;
* calcul ;
* cas d'erreur ;
* format des réponses.

Certaines sorties interdites sont également vérifiées, notamment :

* markdown dans les messages ;
* doubles espaces ;
* `None` visible ;
* identifiants techniques exposés ;
* formulations de confirmation incorrectes.

Autres commandes :

```bash
make lint
make db
make backup
```

* `make lint` : linting avec `ruff` ou `pyflakes` ;
* `make db` : contenu de la base ;
* `make backup` : copie datée de la base.

## Configuration

La configuration est stockée dans `.env`.

| Variable       | Défaut                   | Rôle                 |
| -------------- | ------------------------ | -------------------- |
| `TELEGRAM`     | —                        | token Telegram       |
| `GROQ`         | —                        | clé API Groq         |
| `MY_ID`        | —                        | identifiant Telegram |
| `CITY`         | `Paris`                  | ville par défaut     |
| `BRIEF`        | `off` / `7:30`           | heure du brief       |
| `TZ_NAME`      | `Europe/Paris`           | fuseau horaire       |
| `DB_PATH`      | `joorvis.db`             | chemin de la base    |
| `CHAT_MODEL`   | `openai/gpt-oss-120b`    | modèle principal     |
| `AUDIO_MODEL`  | `whisper-large-v3-turbo` | transcription audio  |
| `VISION_MODEL` | `llama-4-scout`          | modèle de vision     |

Paramètres internes :

* `MAX_TURNS`
* `TOKEN_BUDGET`
* `TTL`
* `MAX_STEPS`

Les noms des modèles sont configurables indépendamment du code.

## Architecture du traitement

### Rappel local

```text
Message Telegram
      │
      ▼
Préfixe + / .
      │
      ▼
Détection de récurrence
      │
      ▼
Détection du repère temporel
      │
      ▼
Texte restant = rappel
      │
      ├── ambiguïté détectée ──► modèle
      │
      └── valide ──────────────► base SQLite
```

### Requête avec modèle

```text
Message Telegram
      │
      ▼
Modèle
      │
      ▼
Appels d'outils
      │
      ▼
Résultats
      │
      └── boucle jusqu'à MAX_STEPS
                  │
                  ▼
               Réponse
```

Le message `· · ·` est édité pendant l'exécution puis remplacé par la réponse finale.

## Fichiers

```text
joorvis_light.py
joorvis_mid.py
joorvis_high.py
check.py
Makefile
requirements.txt
.env.example
```

Chaque version est exécutable indépendamment.

Le parseur, les formats et la base SQLite sont communs aux trois versions.
