import json
import os

# Nom du fichier où les informations des projets installés seront stockées
INSTALLED_PROJECTS_FILE = "installed_projects.json"

# Chemin par défaut pour le fichier de stockage (dans le répertoire de l'application)
# On pourrait aussi le mettre dans un répertoire utilisateur spécifique plus tard
APP_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALLED_PROJECTS_PATH = os.path.join(APP_DIR, INSTALLED_PROJECTS_FILE)

# --- Fonctions pour gérer le fichier de stockage ---

def load_installed_projects():
    """
    Charge la liste des projets installés depuis le fichier JSON.

    Returns:
        list: Une liste de dictionnaires, où chaque dictionnaire représente un projet installé.
              Retourne une liste vide si le fichier n'existe pas ou est vide/invalide.
    """
    if not os.path.exists(INSTALLED_PROJECTS_PATH):
        # print(f"Fichier de projets installés non trouvé : {INSTALLED_PROJECTS_FILE}") # Log console
        return []

    try:
        with open(INSTALLED_PROJECTS_PATH, "r", encoding="utf-8") as f:
            # Charger le contenu du fichier
            content = f.read()
            if not content: # Gérer le cas où le fichier est vide
                # print(f"Fichier de projets installés vide : {INSTALLED_PROJECTS_FILE}") # Log console
                return []
            projects = json.loads(content)

            # S'assurer que c'est bien une liste et que les éléments sont des dictionnaires
            if not isinstance(projects, list):
                print(f"Avertissement: Le contenu de {INSTALLED_PROJECTS_FILE} n'est pas une liste. Rénitialisation.") # Log console
                return []
            
            # Validation basique : s'assurer que chaque élément est un dict avec au moins un 'path'
            valid_projects = [p for p in projects if isinstance(p, dict) and 'path' in p]
            if len(valid_projects) < len(projects):
                 print(f"Avertissement: {len(projects) - len(valid_projects)} entrées invalides trouvées dans {INSTALLED_PROJECTS_FILE}. Elles ont été ignorées.") # Log console

            return valid_projects

    except json.JSONDecodeError:
        print(f"Erreur: Fichier JSON invalide : {INSTALLED_PROJECTS_FILE}. Rénitialisation.") # Log console
        return []
    except Exception as e:
        print(f"Erreur lors du chargement de {INSTALLED_PROJECTS_FILE}: {e}") # Log console
        return []

def save_installed_projects(projects):
    """
    Sauvegarde la liste actuelle des projets installés dans le fichier JSON.

    Args:
        projects (list): La liste des dictionnaires représentant les projets.
    """
    try:
        with open(INSTALLED_PROJECTS_PATH, "w", encoding="utf-8") as f:
            json.dump(projects, f, indent=4) # Utilise indent=4 pour une meilleure lisibilité
        # print(f"Projets installés sauvegardés dans {INSTALLED_PROJECTS_FILE}") # Log console
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de {INSTALLED_PROJECTS_FILE}: {e}") # Log console

# --- Fonctions pour gérer la liste des projets installés en mémoire ---

def add_installed_project(project_info):
    """
    Ajoute un projet à la liste des projets installés et sauvegarde la liste.

    Args:
        project_info (dict): Un dictionnaire contenant les informations du projet
                             (ex: {'name': 'repo_name', 'path': '/chemin/installation', 'url': 'github_url', 'language': 'Python'}).
    """
    projects = load_installed_projects()

    # Vérifier si le projet est déjà dans la liste (basé sur le chemin d'installation)
    # Utiliser os.path.normpath pour standardiser les chemins avant comparaison
    normalized_new_path = os.path.normpath(project_info.get('path', ''))
    for p in projects:
        if os.path.normpath(p.get('path', '')) == normalized_new_path:
            print(f"Projet déjà enregistré à ce chemin : {project_info.get('path')}") # Log console
            return # Ne pas ajouter si déjà présent

    projects.append(project_info)
    save_installed_projects(projects)
    print(f"Projet enregistré : {project_info.get('name')} à {project_info.get('path')}") # Log console

def remove_installed_project(project_path):
    """
    Retire un projet de la liste des projets installés basé sur son chemin
    et sauvegarde la liste.

    Args:
        project_path (str): Le chemin d'installation du projet à retirer.
    """
    projects = load_installed_projects()
    
    # Filtrer la liste pour exclure le projet avec le chemin spécifié (normalisé)
    normalized_path_to_remove = os.path.normpath(project_path)
    updated_projects = [p for p in projects if os.path.normpath(p.get('path', '')) != normalized_path_to_remove]

    if len(updated_projects) < len(projects):
        save_installed_projects(updated_projects)
        print(f"Projet retiré de la liste : {project_path}") # Log console
        return True # Indique que le projet a été trouvé et retiré
    else:
        print(f"Projet non trouvé dans la liste : {project_path}") # Log console
        return False # Indique que le projet n'a pas été trouvé


def get_installed_project_by_path(project_path):
    """
    Trouve un projet installé dans la liste basé sur son chemin.

    Args:
        project_path (str): Le chemin d'installation du projet.

    Returns:
        dict or None: Le dictionnaire du projet s'il est trouvé, sinon None.
    """
    projects = load_installed_projects()
    normalized_target_path = os.path.normpath(project_path)
    for p in projects:
        if os.path.normpath(p.get('path', '')) == normalized_target_path:
            return p
    return None

# Exemple d'utilisation (pour tester ce module indépendamment si besoin)
if __name__ == "__main__":
    # Nettoyer le fichier de test si besoin
    if os.path.exists(INSTALLED_PROJECTS_PATH):
        # Ajout d'une gestion d'erreur pour la suppression du fichier
        try:
            os.remove(INSTALLED_PROJECTS_PATH)
            print(f"Fichier de test {INSTALLED_PROJECTS_FILE} supprimé.")
        except OSError as e:
             print(f"Erreur lors de la suppression du fichier de test {INSTALLED_PROJECTS_FILE}: {e}")


    # Ajouter quelques projets fictifs
    add_installed_project({'name': 'test-project-1', 'full_name': 'test/test-project-1', 'path': '/fake/path/project1', 'url': 'http://github.com/test/p1', 'language': 'Python'})
    add_installed_project({'name': 'test-project-2', 'full_name': 'test/test-project-2', 'path': '/fake/path/project2', 'url': 'http://github.com/test/p2', 'language': 'JavaScript'})
    add_installed_project({'name': 'test-project-1', 'full_name': 'test/test-project-1', 'path': '/fake/path/project1', 'url': 'http://github.com/test/p1', 'language': 'Python'}) # Doublon, ne devrait pas être ajouté

    # Charger et afficher les projets
    print("\nProjets installés après ajout:")
    all_projects = load_installed_projects()
    for p in all_projects:
        # Vérifier si les clés existent avant d'y accéder
        name = p.get('name', 'N/A')
        path = p.get('path', 'N/A')
        lang = p.get('language', 'N/A')
        print(f"- {name} à {path} ({lang})")


    # Retirer un projet
    print("\nTentative de retrait de /fake/path/project1:")
    removed = remove_installed_project('/fake/path/project1')
    print(f"Projet retiré : {removed}")

    print("\nTentative de retrait d'un chemin inexistant:")
    removed = remove_installed_project('/fake/path/nonexistent')
    print(f"Projet retiré : {removed}")


    # Charger et afficher à nouveau
    print("\nProjets installés après suppression:")
    all_projects = load_installed_projects()
    for p in all_projects:
         name = p.get('name', 'N/A')
         path = p.get('path', 'N/A')
         lang = p.get('language', 'N/A')
         print(f"- {name} à {path} ({lang})")

    # Chercher un projet
    print("\nCherche un projet par chemin:")
    found_project = get_installed_project_by_path('/fake/path/project2')
    print(f"Projet trouvé par chemin '/fake/path/project2': {found_project}")

    not_found_project = get_installed_project_by_path('/fake/path/project1')
    print(f"Projet trouvé par chemin '/fake/path/project1': {not_found_project}")