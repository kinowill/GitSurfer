import os
from github import Github
from github import GithubException
import requests # Ajout de requests pour une meilleure gestion des erreurs spécifiques

# --- Configuration ---
# Pour une utilisation non authentifiée, le taux de requêtes est très limité (60/heure).
# Pour augmenter cette limite (5000/heure), utilisez un Personal Access Token.
# Stockez ce token de manière sécurisée (variables d'environnement, fichier de configuration externe, etc.)
# Exemple : GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
# Si vous utilisez un token, initialisez l'objet Github comme ceci :
# g = Github(GITHUB_TOKEN)
# Pour l'instant, on reste en non authentifié pour la simplicité.
GITHUB_TOKEN = None # Remplacez par votre token si vous en utilisez un

# Cette fonction recherche des dépôts sur GitHub
def search_github_projects(query):
    """
    Recherche des dépôts sur GitHub en utilisant un terme de recherche.

    Args:
        query (str): Le terme de recherche.

    Returns:
        list: Une liste d'objets Repository si la recherche réussit,
              None en cas d'erreur ou si la requête est vide.
    """
    if not query:
        print("La requête de recherche est vide.") # Log console
        return None

    try:
        # Initialise l'objet Github, utilise le token si disponible
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
        else:
            g = Github() # Utilisation non authentifiée

        print(f"Recherche GitHub pour : '{query}'...") # Log console

        # Effectue la recherche de dépôts
        # Tri par étoiles (stars) et ordre descendant (desc)
        # La méthode search_repositories retourne un objet PaginatedList
        # On limite à 10 résultats pour cet exemple simple.
        repositories = g.search_repositories(query=query, sort='stars', order='desc')

        # Récupère les 10 premiers résultats (ou moins si moins de 10)
        results = []
        # Utilise une boucle for sur l'itérateur pour une meilleure gestion des PaginatedList
        # Limite explicite à 10
        for i, repo in enumerate(repositories):
            if i >= 10:
                break
            results.append(repo)
            # print(f"- {repo.full_name}: {repo.stargazers_count} étoiles") # Afficher en console pour déboguer


        print(f"Recherche terminée. {len(results)} résultats trouvés.") # Log console
        return results

    except GithubException as e:
        print(f"Erreur API GitHub : {e.status} - {e.data.get('message', 'Aucun message d\'erreur')}") # Log console plus détaillé
        # Gérer les erreurs spécifiques de l'API GitHub (ex: limite de taux dépassée, mauvaise authentification)
        # Vous pouvez inspecter e.status et e.data pour plus de détails
        if e.status == 403 and 'rate limit exceeded' in str(e):
             print("Astuce : Votre limite de taux GitHub est dépassée. Veuillez patienter ou utiliser un token.")
        return None
    except requests.exceptions.ConnectionError as e:
         print(f"Erreur de connexion lors de la recherche GitHub : {e}") # Log console
         print("Veuillez vérifier votre connexion Internet.")
         return None
    except Exception as e:
        print(f"Une erreur inattendue est survenue lors de la recherche GitHub : {e}") # Log console
        # Gérer les autres erreurs potentielles
        return None

# Exemple d'utilisation (pour tester ce module indépendamment si besoin)
if __name__ == "__main__":
    test_query = "customtkinter"
    found_repos = search_github_projects(test_query)

    if found_repos:
        print(f"\nDépôts trouvés pour '{test_query}':")
        for repo in found_repos:
            print(f"- {repo.full_name} ({repo.stargazers_count} étoiles) - {repo.description}")
    else:
        print(f"\nAucun dépôt trouvé ou une erreur est survenue pour '{test_query}'.")