import subprocess
import os
import threading
import sys
import time
import shutil # Import pour la suppression de répertoire
from installed_projects_manager import add_installed_project # Importe la fonction pour enregistrer le projet

# Cette fonction gère le clonage d'un dépôt Git et l'installation des dépendances Python
# Ajout du paramètre optionnel repo_info
def clone_repository(repo_url, install_path, repo_info=None, status_callback=None):
    """
    Clone un dépôt Git dans un répertoire spécifié et installe les dépendances Python
    si un fichier requirements.txt est trouvé. Enregistre le projet s'il réussit.

    Args:
        repo_url (str): L'URL du dépôt Git (HTTPS ou SSH).
        install_path (str): Le chemin complet où le dépôt doit être cloné.
        repo_info (dict, optional): Informations sur le dépôt à enregistrer
                                    ({'name': ..., 'full_name': ..., 'url': ..., 'language': ...}).
                                    Defaults to None.
        status_callback (function, optional): Une fonction de callback
                                               pour mettre à jour le statut.
                                               Prend un argument (message de statut).
                                               Defaults to None.

    Returns:
        bool: True si le processus complet réussit, False sinon.
    """
    if status_callback:
        status_callback(f"Clonage de {repo_url} dans {install_path}...")

    try:
        # Vérifie si le répertoire d'installation existe et n'est pas vide
        if os.path.exists(install_path):
            # Si le répertoire existe et n'est pas vide, on pourrait demander confirmation
            # ou simplement annuler pour éviter d'écraser des données.
            if os.listdir(install_path):
                 message = f"Erreur : Le répertoire d'installation '{install_path}' existe et n'est pas vide."
                 if status_callback:
                      status_callback(message)
                 print(message) # Log console
                 return False
            else:
                 # Si le répertoire existe mais est vide, on peut continuer
                 if status_callback:
                      status_callback(f"Répertoire existant et vide trouvé : {install_path}")
                 print(f"Répertoire existant et vide trouvé : {install_path}") # Log console
        else:
            # Si le répertoire n'existe pas, on le crée
            os.makedirs(install_path)
            if status_callback:
                status_callback(f"Répertoire créé : {install_path}")
            print(f"Répertoire créé : {install_path}") # Log console


        # Commande Git à exécuter
        # Utilisation de shell=False et spécification complète de la commande pour plus de sécurité et de robustesse
        command_clone = ["git", "clone", repo_url, install_path]

        # Exécute la commande Git clone
        if status_callback:
             status_callback(f"Exécution de la commande : {' '.join(command_clone)}")

        # Capture stdout et stderr pour un meilleur débogage en cas d'échec
        process_clone = subprocess.run(command_clone, capture_output=True, text=True, check=True, shell=False)

        if status_callback:
            status_callback(f"Clonage terminé avec succès dans {install_path}.")
            # Optionnel: afficher la sortie du clonage si besoin (peut être verbeux)
            # status_callback(f"Sortie clonage:\n{process_clone.stdout}")

        # --- Logique pour l'environnement virtuel et les dépendances Python ---

        # Vérifie si un fichier requirements.txt existe dans le répertoire cloné
        requirements_path = os.path.join(install_path, "requirements.txt")
        if os.path.exists(requirements_path):
            if status_callback:
                status_callback("Fichier requirements.txt trouvé. Préparation de l'environnement virtuel et installation des dépendances...")

            # Chemin vers l'exécutable Python pour créer le venv
            python_executable = sys.executable # Utilise l'exécutable Python qui exécute ce script

            # 1. Créer l'environnement virtuel
            venv_path = os.path.join(install_path, ".venv")
            if status_callback:
                 status_callback(f"Création de l'environnement virtuel dans {venv_path}...")
            command_venv = [python_executable, "-m", "venv", venv_path]
            # Exécute la commande venv dans le répertoire du projet cloné
            process_venv = subprocess.run(command_venv, capture_output=True, text=True, check=True, cwd=install_path, shell=False)

            if status_callback:
                status_callback("Environnement virtuel créé avec succès.")
                # status_callback(f"Sortie venv:\n{process_venv.stdout}")


            # Ajout d'un court délai pour laisser le système finir de créer les fichiers du venv
            time.sleep(1) # Peut être ajusté si nécessaire

            # Chemin vers l'exécutable pip dans le venv nouvellement créé
            # Construction robuste des chemins pour Windows et non-Windows
            venv_pip_path = None
            if sys.platform == "win32":
                 # Sur Windows, l'exécutable est dans Scripts et se termine par .exe
                 venv_pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
            else:
                 # Sur les systèmes non-Windows, l'exécutable est dans bin
                 venv_pip_path = os.path.join(venv_path, "bin", "pip")

            # Vérifie si l'exécutable pip a été trouvé
            if not os.path.exists(venv_pip_path):
                 message = f"Erreur : Exécutable pip introuvable dans le venv à l'emplacement attendu : {venv_pip_path}"
                 if status_callback:
                      status_callback(message)
                 print(message) # Log console
                 return False


            # 2. Installer les dépendances en utilisant le pip du venv (appel direct)
            if status_callback:
                status_callback("Installation des dépendances (pip install -r requirements.txt)...")
            # Appelle directement l'exécutable pip du venv
            command_pip_install = [venv_pip_path, "install", "-r", requirements_path]
            # Exécute la commande pip dans le répertoire du projet cloné
            process_pip_install = subprocess.run(command_pip_install, capture_output=True, text=True, check=True, cwd=install_path, shell=False)

            if status_callback:
                status_callback("Dépendances installées avec succès.")
                # status_callback(f"Sortie pip install:\n{process_pip_install.stdout}")

        else:
            if status_callback:
                status_callback("Aucun fichier requirements.txt trouvé. Pas d'installation de dépendances Python.")
            print("Aucun fichier requirements.txt trouvé.") # Log console


        # --- Enregistrement du projet installé ---
        # S'assurer que repo_info a été passé et qu'il contient les clés nécessaires
        if repo_info and all(k in repo_info for k in ['name', 'full_name', 'url', 'language']):
             project_info_to_save = {
                  'name': repo_info['name'],
                  'full_name': repo_info['full_name'],
                  'path': os.path.normpath(install_path), # Chemin d'installation réel, normalisé
                  'url': repo_info['url'], # URL de clonage
                  'language': repo_info['language'],
             }
             add_installed_project(project_info_to_save)
             if status_callback:
                  status_callback(f"Projet '{project_info_to_save['name']}' enregistré dans la bibliothèque.")
             print(f"Projet '{project_info_to_save['name']}' enregistré.") # Log console
        elif status_callback:
             status_callback("Avertissement : Informations de dépôt incomplètes ou manquantes pour l'enregistrement dans la bibliothèque.")
             print("Avertissement : Informations de dépôt incomplètes ou manquantes pour l'enregistrement.") # Log console


        # Message de succès final après toutes les étapes (clonage + venv/pip si applicable + enregistrement)
        final_success_message = f"Processus d'installation terminé avec succès pour {os.path.basename(install_path)}."
        if status_callback:
             status_callback(final_success_message)
        print(final_success_message) # Log console


        return True # Retourne True si le processus complet réussit

    except FileNotFoundError as e:
        message = f"Erreur FileNotFoundError: La commande ou l'exécutable '{e.filename}' n'a pas été trouvé."
        detail_message = "Cela peut indiquer que Git, Python ou un exécutable venv nécessaire n'est pas accessible ou n'existe pas.\nVeuillez vérifier votre installation de Git et Python et leur configuration PATH."
        if status_callback:
            status_callback(message)
            status_callback(detail_message)
        print(f"{message}\n{detail_message}") # Log console
        return False
    except subprocess.CalledProcessError as e:
        message = f"Erreur lors de l'exécution de la commande : {' '.join(e.cmd)}"
        detail_message = f"Code de retour : {e.returncode}\nSortie standard:\n{e.stdout}\nSortie d'erreur:\n{e.stderr}"
        if status_callback:
            status_callback(message)
            # Afficher seulement les premières lignes de sortie si elles sont très longues
            stdout_preview = e.stdout[:500] + '...' if len(e.stdout) > 500 else e.stdout
            stderr_preview = e.stderr[:500] + '...' if len(e.stderr) > 500 else e.stderr
            status_callback(f"Sortie:\n{stdout_preview}")
            status_callback(f"Erreur:\n{stderr_preview}")
        print(f"{message}\n{detail_message}") # Log console complet pour le débogage
        return False
    except Exception as e:
        message = f"Une erreur inattendue est survenue lors de l'installation : {e}"
        if status_callback:
            status_callback(message)
        print(message) # Log console
        return False

# Exemple d'utilisation (pour tester ce module indépendamment si besoin)
if __name__ == "__main__":
    # Ceci est un exemple de test pour project_installer.py, il ne gère pas l'UI
    # Utilisez l'application main.py pour tester l'intégration complète

    # Exemple de données de dépôt pour le test
    # Remplacez par une URL de dépôt réelle si vous testez, idéalement un petit projet Python avec requirements.txt
    test_repo_url = 'https://github.com/exemple/petit-projet-python.git' # REMPLACEZ CECI
    test_repo_name = 'petit-projet-python' # REMPLACEZ CECI
    test_repo_full_name = f'exemple/{test_repo_name}' # REMPLACEZ CECI
    test_repo_info = {
        'name': test_repo_name,
        'full_name': test_repo_full_name,
        'url': test_repo_url,
        'language': 'Python'
    }
    # Utiliser un répertoire de test dans le répertoire courant ou temporaire
    # test_install_path = os.path.join(tempfile.gettempdir(), test_repo_name) # Optionnel: utiliser un répertoire temporaire
    test_install_path = os.path.join(".", test_repo_name)


    print(f"Test de clonage et installation pour : {test_repo_info['full_name']}")

    def print_status(message):
        print(f"[STATUT INSTALLATEUR] {message}")

    # Nettoyer le répertoire de test s'il existe
    if os.path.exists(test_install_path):
        print(f"Suppression du répertoire de test existant : {test_install_path}")
        try:
            # Utiliser shutil.rmtree pour supprimer le répertoire et son contenu
            shutil.rmtree(test_install_path)
            print("Répertoire de test supprimé.")
        except OSError as e:
             print(f"Erreur lors de la suppression du répertoire de test : {e}")
             print("Veuillez vérifier les permissions et si le répertoire n'est pas utilisé par un autre processus.")
             # Sortir si la suppression échoue pour éviter des tests sur un état incorrect
             sys.exit(1)

    # Supprimer le fichier de projets installés pour un test propre
    from installed_projects_manager import INSTALLED_PROJECTS_PATH # Importe le chemin du fichier de test
    if os.path.exists(INSTALLED_PROJECTS_PATH):
         try:
             os.remove(INSTALLED_PROJECTS_PATH)
             print(f"Fichier de projets installés {os.path.basename(INSTALLED_PROJECTS_PATH)} supprimé pour le test.")
         except OSError as e:
              print(f"Erreur lors de la suppression du fichier de projets installés : {e}")


    # Appeler la fonction de clonage avec les infos du dépôt
    success = clone_repository(test_repo_info['url'], test_install_path, repo_info=test_repo_info, status_callback=print_status)

    if success:
        print("\nProcessus d'installation complet réussi !")
        # Vérifier si le projet a été enregistré
        from installed_projects_manager import load_installed_projects # Importe la fonction de chargement
        installed_projects = load_installed_projects()
        print(f"Projets enregistrés après le test : {installed_projects}")
    else:
        print("\nÉchec du processus d'installation.")

    # Exemple de test avec un répertoire existant non vide
    # Créer un répertoire de test non vide
    # test_existing_dir = "./test_existing_dir"
    # os.makedirs(test_existing_dir, exist_ok=True)
    # with open(os.path.join(test_existing_dir, "dummy_file.txt"), "w") as f:
    #      f.write("contenu")
    # print(f"\nTest d'installation dans un répertoire existant et non vide ({test_existing_dir}):")
    # success_existing = clone_repository(test_repo_url, test_existing_dir, status_callback=print_status)
    # print(f"Installation réussie dans répertoire existant : {success_existing}")
    # # Nettoyer le répertoire de test existant
    # if os.path.exists(test_existing_dir):
    #      try:
    #           shutil.rmtree(test_existing_dir)
    #      except OSError as e:
    #            print(f"Erreur lors du nettoyage du répertoire de test existant : {e}")