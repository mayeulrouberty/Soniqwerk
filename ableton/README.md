# Soniqwerk — intégration Ableton

Bridge entre le backend Soniqwerk et Ableton Live via Max for Live.

## Démarrage rapide

1. `cd ableton && npm install` — installe le package WebSocket `ws`
2. Démarrer le bridge WS : `cd backend && python -m ws_bridge` (port 8001)
3. Glisser `SONIQWERK.amxd` sur une track MIDI dans Ableton

C'est tout. Le bridge se connecte automatiquement et se reconnecte si la connexion coupe.

## SONIQWERK.amxd — panel de chat intégré

Le device M4L donne accès à un panel de chat 800×240px directement dans la zone des devices. Pas besoin d'ouvrir un navigateur.

- Taper une commande et appuyer sur Entrée pour interroger l'agent
- Le point de statut indique l'état de connexion (rouge/orange/vert)
- Cliquer sur l'URL ou le champ key dans la barre du haut pour les modifier
- Scroller l'historique avec la molette

Les trois fichiers doivent être dans le même dossier : `SONIQWERK.amxd`, `SONIQWERK_bridge.js`, `SONIQWERK_ui.js`.

Nécessite le backend sur `localhost:8000` et le bridge WS sur `localhost:8001`.

## Fichiers

```
ableton/
├── SONIQWERK.amxd        # device M4L — glisser dans Ableton
├── SONIQWERK_bridge.js   # node.script : bridge WS + client HTTP agent
├── SONIQWERK_ui.js       # jsui canvas : barre de statut, historique, saisie
├── package.json          # dépendance npm (ws)
└── README.md
```

## Dépannage

**Port 8001 déjà utilisé :**
```bash
lsof -i :8001
kill -9 <PID>
```

**"ws package not found" dans la console Max :** lancer `npm install` dans le dossier `ableton`.

**Le device se connecte mais les requêtes ne répondent pas :** vérifier que le backend FastAPI tourne sur le port 8000, pas seulement le bridge WS.
