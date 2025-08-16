# Gossip Miri (Python • Railway)

Un bot Discord (Python, `discord.py`) pour **confessions anonymes** avec threads, réponses anonymes, logs, et suppression des gossips par leur auteur.

## Fonctionnalités
- Panneau d'accueil avec bouton **Soumettre une confession**.
- Publication d'une **confession** en embed stylé (auteur *Gossip Miri*, couleur `#9B6B43`, footer *XOXO, Gossip Miri 💋*), **sans numérotation**.
- Création automatique d'un **thread** sous chaque confession.
- Deux boutons sous chaque confession : **💭 Répondre** (via modal) et **🔐 Soumettre un autre gossip**.
- **Réponse anonyme possible** (via champ *oui/non*).
- **Logs** dans un salon dédié (tag + avatar de l'auteur, sans mention directe).
- **/deletegossip** : menu déroulant listant **tous** tes anciens gossips (jusqu’à 25) à supprimer.
- **/gossip_panel** : publier le panneau d’accueil (permission *Manage Guild*).

## Configuration
- Crée un bot Discord, active **Privileged Gateway Intents** (*Server Members*).
- Invite le bot avec les permissions nécessaires : lire/écrire, gérer threads, éventuellement *Manage Webhooks* si tu veux, mais non requis ici.

Variables d'environnement (voir `.env.example`) :
```
DISCORD_TOKEN=...

# IDs par défaut (modifiable)
GUILD_ID=1382730341944397967
GOSSIP_CHANNEL_ID=1400520302416367796
LOG_CHANNEL_ID=1400520703874433146

# (optionnel) Icône pour l'auteur de l'embed
GOSSIP_AUTHOR_ICON=https://i.imgur.com/1f7h3G9.png
```

## Lancer en local
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DISCORD_TOKEN=...  # ou fichier .env si tu utilises python-dotenv
python main.py
```

## Déploiement sur Railway

### Option A — Via Dockerfile (recommandé)
1. Crée un **nouveau projet** sur Railway.
2. Choisis *Deploy from Repository* ou *Deploy from Zip Upload* selon ton flux. (Tu peux aussi *Connect* un repo plus tard.)
3. Dans **Variables**, ajoute :
   - `DISCORD_TOKEN`
   - (facultatif) `GUILD_ID`, `GOSSIP_CHANNEL_ID`, `LOG_CHANNEL_ID`, `GOSSIP_AUTHOR_ICON`
4. Railway détectera le `Dockerfile` et lancera `python main.py` automatiquement.

### Option B — Sans Dockerfile (Buildpack Python)
1. Supprime le `Dockerfile` (ou ignore-le) et assure-toi d'avoir `requirements.txt`.
2. Dans **Start Command** sur Railway, mets : `python main.py`.
3. Renseigne les variables d'environnement comme ci-dessus.

## Commandes
- `/gossip_panel` : poste le panneau d’accueil avec bouton *Soumettre une confession*. (Admin gestion serveur)
- `/deletegossip` : ouvre un menu pour supprimer un de **tes** gossips.

## Notes
- Les données (auteur → message) sont stockées en JSON local `data/gossips.json`. Sur Railway, le stockage est **éphémère** (réinitialisé à chaque redeploy). Si tu veux une persistance forte, ajoute une base (Redis/DB).
- Le champ *anonyme* du modal est un **oui/non** (Discord ne propose pas de case à cocher dans un modal).

Bon déploiement ✨
