# GitSurfer

Application desktop pour explorer, installer et lancer des projets GitHub — sans toucher à un terminal.

## Fonctionnalités

- **Recherche GitHub** — cherche les dépôts par mot-clé, affiche les 10 premiers résultats triés par étoiles
- **Fiche détaillée** — étoiles, forks, langage, description, lien GitHub direct
- **Installation en un clic** — clone le dépôt, crée automatiquement un environnement virtuel et installe les dépendances si un `requirements.txt` est présent
- **Bibliothèque** — liste tous les projets installés, avec accès rapide au lancement et à la suppression
- **Lancement automatique** — détecte le type de projet (Python : `main.py` / `app.py`, Node.js : script `start` dans `package.json`) et le lance sans configuration
- **Lecteur de README** — affiche le `README.md` ou `README.rst` du projet installé directement dans l'interface
- **Suppression propre** — retire le projet du disque et de la bibliothèque en une action

## Prérequis

- Python 3.10 ou supérieur
- Git installé et accessible dans le PATH

## Installation

```bash
git clone https://github.com/kinowill/GitSurfer.git
cd GitSurfer
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
python main.py
```

## Stack

| Composant | Rôle |
|---|---|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | Interface graphique (thème sombre) |
| [PyGithub](https://github.com/PyGithub/PyGithub) | Accès à l'API GitHub |
| [requests](https://github.com/psf/requests) | Requêtes HTTP |

## Token GitHub (optionnel)

Par défaut, l'app utilise l'API GitHub sans authentification (limite : 10 requêtes/minute).
Pour augmenter cette limite, ajoute ton token dans `github_connector.py` :

```python
GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"
```

> Ne commite jamais ton token. Utilise une variable d'environnement ou un fichier `.env` ignoré par git.

## Licence

MIT
