# Joorvis — make sans argument affiche cette aide.
#
#   make install        prépare l'environnement
#   make light          lance la version ultra light
#   make mid            lance la version équilibrée
#   make high           lance la version complète
#   make check          vérifie les textes de sortie, sans réseau ni token

PY      ?= python3
VENV    := .venv
BIN     := $(VENV)/bin
BOT     ?= mid
DB      ?= joorvis.db
SERVICE ?= joorvis

BLEU := \033[36m
GRIS := \033[90m
RAZ  := \033[0m

.DEFAULT_GOAL := help
.PHONY: help install light mid high run check lint db backup clean reset-db \
        service logs versions

help: ## affiche cette aide
	@printf "\n  $(BLEU)Joorvis$(RAZ)  ·  assistant Telegram, trois tailles\n\n"
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS=":.*?## "}; {printf "  $(BLEU)%-12s$(RAZ) %s\n", $$1, $$2}'
	@printf "\n  $(GRIS)variables : BOT=light|mid|high  DB=$(DB)  PY=$(PY)$(RAZ)\n\n"

# ── installation ───────────────────────────────────────────────────────

$(BIN)/python:
	@printf "  $(GRIS)création de $(VENV)$(RAZ)\n"
	@$(PY) -m venv $(VENV)
	@$(BIN)/pip install --quiet --upgrade pip

install: $(BIN)/python ## installe les dépendances dans .venv
	@$(BIN)/pip install --quiet -r requirements.txt
	@test -f .env || (cp .env.example .env && \
	  printf "  $(BLEU).env créé$(RAZ) — remplis TELEGRAM, GROQ et MY_ID\n")
	@printf "  $(BLEU)prêt$(RAZ) — puis : make mid\n"

# ── lancement ──────────────────────────────────────────────────────────

light: ## lance la version ultra light (3 outils)
	@$(MAKE) --no-print-directory run BOT=light

mid: ## lance la version équilibrée (8 outils)
	@$(MAKE) --no-print-directory run BOT=mid

high: ## lance la version complète (10 outils, photos, documents)
	@$(MAKE) --no-print-directory run BOT=high

run: guard-env ## lance BOT=light|mid|high
	@printf "  $(BLEU)joorvis $(BOT)$(RAZ)  $(GRIS)ctrl-c pour arrêter$(RAZ)\n"
	@$(BIN)/python joorvis_$(BOT).py

guard-env:
	@test -f .env || { printf "  Pas de .env. Lance d'abord : make install\n"; \
	  exit 1; }
	@test -x $(BIN)/python || { printf "  Pas de .venv. Lance : make install\n"; \
	  exit 1; }
	@grep -qE '^TELEGRAM=.+' .env || { printf "  TELEGRAM vide dans .env\n"; \
	  exit 1; }
	@grep -qE '^GROQ=.+' .env || { printf "  GROQ vide dans .env\n"; exit 1; }
	@grep -qE '^MY_ID=[0-9]+' .env || { printf "  MY_ID vide dans .env\n"; \
	  exit 1; }

# ── vérification ───────────────────────────────────────────────────────

check: ## vérifie les textes de sortie des trois versions
	@$(BIN)/python check.py 2>/dev/null || $(PY) check.py

lint: ## passe ruff ou pyflakes si l'un des deux est là
	@$(BIN)/python -m ruff check . 2>/dev/null \
	  || $(BIN)/python -m pyflakes *.py 2>/dev/null \
	  || printf "  $(GRIS)ni ruff ni pyflakes — pip install ruff$(RAZ)\n"

versions: ## rappelle ce que contient chaque version
	@printf "\n  $(BLEU)light$(RAZ)  rappels, web, crypto\n"
	@printf "  $(BLEU)mid$(RAZ)    + tâches, météo, calcul, devises, mémoire, brief\n"
	@printf "  $(BLEU)high$(RAZ)   + photos, documents, notes, Wikipédia, export, purge\n\n"

# ── base de données ────────────────────────────────────────────────────

db: ## affiche ce que contient la base
	@test -f $(DB) || { printf "  Pas encore de base.\n"; exit 0; }
	@sqlite3 $(DB) \
	  "SELECT 'rappels  ' || count(*) FROM reminders; \
	   SELECT 'tâches   ' || count(*) FROM tasks; \
	   SELECT 'notes    ' || count(*) FROM notes; \
	   SELECT 'mémoire  ' || count(*) FROM facts;" 2>/dev/null \
	  || printf "  $(GRIS)installe sqlite3 pour voir le détail$(RAZ)\n"

backup: ## copie datée de la base
	@test -f $(DB) && cp $(DB) "$(DB).$$(date +%Y%m%d-%H%M).bak" \
	  && printf "  copie faite\n" || printf "  Pas de base à copier.\n"

reset-db: backup ## efface la base (une copie est faite avant)
	@rm -f $(DB) $(DB)-wal $(DB)-shm && printf "  base effacée\n"

# ── service systemd ────────────────────────────────────────────────────

service: ## écrit une unité systemd pour tourner en fond au démarrage
	@printf '%s\n' \
	  '[Unit]' \
	  'Description=Joorvis ($(BOT))' \
	  'After=network-online.target' \
	  '' \
	  '[Service]' \
	  'Type=simple' \
	  'WorkingDirectory=$(CURDIR)' \
	  'ExecStart=$(CURDIR)/$(BIN)/python $(CURDIR)/joorvis_$(BOT).py' \
	  'Restart=always' \
	  'RestartSec=10' \
	  'User=$(USER)' \
	  '' \
	  '[Install]' \
	  'WantedBy=default.target' > $(SERVICE).service
	@printf "  $(SERVICE).service écrit. Ensuite :\n"
	@printf "  $(GRIS)sudo cp $(SERVICE).service /etc/systemd/system/\n"
	@printf "  sudo systemctl enable --now $(SERVICE)$(RAZ)\n"

logs: ## suit les logs du service
	@journalctl -u $(SERVICE) -f -n 50

# ── ménage ─────────────────────────────────────────────────────────────

clean: ## enlève les fichiers temporaires
	@rm -rf __pycache__ .ruff_cache *.service
	@printf "  nettoyé\n"
