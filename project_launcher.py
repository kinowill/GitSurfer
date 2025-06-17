import subprocess
import os
import sys
import threading
import time
import tempfile
import runpy
import shlex
import json # Still need json for reading package.json

# This function launches a project using automatic heuristics
def launch_project(project_path, status_callback=None, feedback_callback=None):
    """
    Tente de lancer un projet dans un répertoire spécifié en utilisant des heuristiques
    basées sur la structure courante des projets (Python, Node.js basique).

    Args:
        project_path (str): Le chemin complet vers le répertoire racine du projet.
        status_callback (function, optional): Une fonction de callback
                                               pour mettre à jour le statut général.
                                               Prend un argument (message de statut).
                                               Defaults to None.
        feedback_callback (function, optional): Une fonction de callback
                                                pour afficher le feedback spécifique au lancement.
                                                Prend un argument (message de feedback).
                                                Defaults to None.

    Returns:
        bool: True si le processus de lancement est initié, False sinon.
    """
    # Normaliser le chemin du projet
    project_path_norm = os.path.normpath(project_path)

    # Vérifier si le répertoire du projet existe
    if not os.path.isdir(project_path_norm):
         message = f"Erreur : Le répertoire du projet n'existe pas ou est inaccessible : {project_path_norm}"
         if status_callback: status_callback(message)
         if feedback_callback: feedback_callback(message)
         print(message) # Log console
         return False

    # --- Heuristique 1: Projet Python ---
    if status_callback: status_callback("Tentative de lancement en tant que projet Python standard (recherche main.py/app.py)...")
    print("Tentative de lancement Python standard...") # Log console

    script_names = ["main.py", "app.py"] # Scripts Python à essayer
    executed_python_script_name = None

    for script_name in script_names:
        script_path = os.path.join(project_path_norm, script_name)
        if os.path.isfile(script_path):
            executed_python_script_name = script_name
            break # Trouvé un script, on arrête de chercher

    if executed_python_script_name:
        message = f"Script Python '{executed_python_script_name}' trouvé. Préparation au lancement..."
        if status_callback:
            status_callback(message)
        if feedback_callback:
             feedback_callback(message)
        print(message) # Log console

        # Déterminer l'exécutable Python à utiliser (venv ou système)
        venv_path = os.path.join(project_path_norm, ".venv")
        python_executable = sys.executable # Par défaut, utilise l'exécutable Python qui exécute ce script

        # Construction robuste des chemins de l'exécutable Python du venv
        venv_python_path = None
        if sys.platform == "win32":
             venv_python_path = os.path.join(venv_path, "Scripts", "python.exe")
        else:
             venv_python_path = os.path.join(venv_path, "bin", "python")

        # Vérifie si l'exécutable Python du venv existe et est un fichier exécutable
        if os.path.isfile(venv_python_path) and os.access(venv_python_path, os.X_OK):
            python_executable = venv_python_path
            info_message = "Utilisation de l'exécutable Python de l'environnement virtuel."
            if status_callback: status_callback(info_message)
            if feedback_callback: feedback_callback(info_message)
            print(info_message) # Log console
        else:
            info_message = "Environnement virtuel Python non trouvé ou exécutable non standard. Utilisation de l'exécutable Python système."
            if status_callback: status_callback(info_message)
            if feedback_callback: feedback_callback(info_message)
            print(info_message) # Log console


        try:
            # Construire la chaîne de code Python à exécuter
            # Utilise runpy.run_path pour exécuter le script dans le nouveau répertoire courant
            # Met des guillemets autour du nom du script pour gérer les espaces ou caractères spéciaux
            python_code_string = f'import os; import runpy; os.chdir(r"{project_path_norm}"); runpy.run_path(r"{executed_python_script_name}", run_name="__main__")'

            # Commande pour exécuter l'interpréteur Python avec la chaîne de code
            # On passe le chemin de l'exécutable Python, -c, et la chaîne de code dans une liste
            command = [os.path.normpath(python_executable), "-c", python_code_string]

            # Afficher la commande qui va être exécutée (utile pour le débogage)
            if sys.version_info >= (3, 8):
                 display_command = shlex.join(command)
            else:
                 display_command = '"' + '" "'.join(command) + '"'

            if len(display_command) > 200:
                 display_command = display_command[:100] + " ... " + display_command[-100:]

            message_cmd = f"Commande de lancement : {display_command}"
            if status_callback: status_callback(message_cmd)
            if feedback_callback: feedback_callback(message_cmd)
            print(message_cmd) # Log console


            # Exécute la commande dans un sous-processus
            app_dir = os.path.dirname(os.path.abspath(__file__))
            process = subprocess.Popen(
                 command,
                 cwd=app_dir, # Exécute depuis le répertoire de l'application
                 stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE,
                 text=True,
                 shell=False
            )

            # Lire la sortie et l'erreur en arrière-plan
            threading.Thread(target=read_process_output, args=(process.stdout, "Sortie Projet (Python)", status_callback, feedback_callback)).start()
            threading.Thread(target=read_process_output, args=(process.stderr, "Erreur Projet (Python)", status_callback, feedback_callback)).start()

            if status_callback: status_callback("Processus Python standard démarré.")
            return True # Indique que le processus a été démarré

        except FileNotFoundError as e:
            message = f"Erreur FileNotFoundError lors du lancement Python : L'exécutable '{e.filename}' (Python) n'a pas été trouvé."
            detail_message = "Veuillez vérifier que l'exécutable Python (du venv ou système) est correct et accessible dans votre PATH."
            if status_callback: status_callback(message); status_callback(detail_message)
            if feedback_callback: feedback_callback(message); feedback_callback(detail_message)
            print(f"{message}\n{detail_message}") # Log console
            return False
        except Exception as e:
            message = f"Une erreur inattendue est survenue lors du lancement Python : {e}"
            if status_callback: status_callback(message)
            if feedback_callback: feedback_callback(message)
            print(message) # Log console
            return False

    else:
        # --- Heuristique 2: Projet Node.js ---
        if status_callback: status_callback("Aucun script Python trouvé. Tentative de lancement en tant que projet Node.js standard (recherche package.json)...")
        print("Aucun script Python trouvé. Tentative Node.js...") # Log console

        package_json_path = os.path.join(project_path_norm, "package.json")

        if os.path.isfile(package_json_path):
             if status_callback: status_callback("package.json trouvé. Lecture...")
             print("package.json trouvé.") # Log console
             try:
                  with open(package_json_path, "r", encoding="utf-8") as f:
                       package_json = json.load(f)

                  start_script = package_json.get("scripts", {}).get("start")

                  if start_script:
                       message = f"Script 'start' trouvé dans package.json : '{start_script}'. Préparation au lancement..."
                       if status_callback: status_callback(message)
                       if feedback_callback: feedback_callback(message)
                       print(message) # Log console

                       # La commande à exécuter est généralement 'npm start' ou 'yarn start'
                       # On peut essayer de détecter si yarn.lock existe pour préférer yarn
                       use_yarn = os.path.exists(os.path.join(project_path_norm, "yarn.lock"))
                       package_manager_command = "yarn" if use_yarn else "npm"
                       launch_command = [package_manager_command, "start"]

                       if status_callback: status_callback(f"Exécution de la commande de lancement Node.js : {' '.join(launch_command)}")
                       print(f"Exécution de la commande : {' '.join(launch_command)}") # Log console


                       try:
                            # Exécute la commande dans le répertoire du projet
                            process = subprocess.Popen(
                                 launch_command,
                                 cwd=project_path_norm, # Exécute depuis le répertoire du projet
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 text=True,
                                 shell=False # Préférer shell=False
                            )

                            # Lire la sortie et l'erreur en arrière-plan
                            threading.Thread(target=read_process_output, args=(process.stdout, f"Sortie Projet ({package_manager_command} start)", status_callback, feedback_callback)).start()
                            threading.Thread(target=read_process_output, args=(process.stderr, f"Erreur Projet ({package_manager_command} start)", status_callback, feedback_callback)).start()

                            if status_callback: status_callback(f"Processus Node.js ({package_manager_command} start) démarré.")
                            return True # Indique que le processus a été démarré

                       except FileNotFoundError as e:
                            message = f"Erreur FileNotFoundError lors du lancement Node.js : La commande '{e.filename}' ({package_manager_command}) n'a pas été trouvée."
                            detail_message = f"Veuillez vérifier que Node.js et/ou Yarn sont installés et accessibles dans votre PATH."
                            if status_callback: status_callback(message); status_callback(detail_message)
                            if feedback_callback: feedback_callback(message); feedback_callback(detail_message)
                            print(f"{message}\n{detail_message}") # Log console
                            return False
                       except Exception as e:
                           message = f"Une erreur inattendue est survenue lors du lancement Node.js : {e}"
                           if status_callback: status_callback(message)
                           if feedback_callback: feedback_callback(message)
                           print(message) # Log console
                           return False

                  else:
                      message = "package.json trouvé, mais aucun script 'start' n'a été défini."
                      if status_callback: status_callback(message)
                      if feedback_callback: feedback_callback(message)
                      print(message) # Log console
                      # Continuer à chercher d'autres heuristiques si on en ajoute

             except json.JSONDecodeError:
                  message = "Erreur : Fichier package.json invalide (format JSON)."
                  if status_callback: status_callback(message)
                  if feedback_callback: feedback_callback(message)
                  print(message) # Log console
                  # Continuer à chercher d'autres heuristiques

             except Exception as e:
                  message = f"Erreur lors de la lecture du fichier package.json : {e}"
                  if status_callback: status_callback(message)
                  if feedback_callback: feedback_callback(message)
                  print(message) # Log console
                  # Continuer à chercher d'autres heuristiques

        # --- Si aucune heuristique ne fonctionne ---
        message = "Aucune méthode de lancement automatique reconnue pour ce projet."
        if status_callback: status_callback(message)
        if feedback_callback: feedback_callback(message)
        print(message) # Log console
        return False


def read_process_output(pipe, status_prefix, status_callback, feedback_callback):
    """
    Lit la sortie d'un pipe de sous-processus ligne par ligne et l'envoie
    aux callbacks de statut et de feedback.
    """
    try:
        for line in iter(pipe.readline, ''):
            cleaned_line = line.strip()
            if cleaned_line:
                message = f"[{status_prefix}] {cleaned_line}"
                if status_callback:
                     # Utiliser self.after dans l'UI si nécessaire
                     status_callback(message)
                if feedback_callback:
                     # Utiliser self.after dans l'UI si nécessaire
                     feedback_callback(message)
                print(message) # Log console
    except Exception as e:
         error_message = f"Erreur lors de la lecture de la sortie du processus ({status_prefix}): {e}"
         if status_callback: status_callback(error_message)
         if feedback_callback: feedback_callback(error_message)
         print(error_message) # Log console
    finally:
        pipe.close()
        end_message = f"[{status_prefix}] Fin du flux."
        # if status_callback: status_callback(end_message) # Optionnel: peut être trop verbeux
        # if feedback_callback: feedback_callback(end_message) # Optionnel
        # print(end_message) # Log console

# Exemple d'utilisation (pour tester ce module indépendamment si besoin)
if __name__ == "__main__":
    # Ce test utilise des heuristiques.
    # Pour tester le lanceur, créez des répertoires de test avec:
    # - Un script Python (main.py ou app.py) et éventuellement un venv
    # - Un fichier package.json avec un script "start"
    # - Un répertoire sans aucun des éléments ci-dessus

    def print_status(message):
        print(f"[STATUT LANCEUR] {message}")

    def print_feedback(message):
         print(f"[FEEDBACK LANCEUR] {message}")

    # --- Exemples de tests (créez les répertoires et fichiers correspondants) ---

    # Testez un répertoire avec main.py (simuler un projet Python)
    # test_python_path = "./test_python_project"
    # os.makedirs(test_python_path, exist_ok=True)
    # with open(os.path.join(test_python_path, "main.py"), "w") as f:
    #      f.write("import sys\nprint('Bonjour depuis Python!')\n")
    # print(f"\nTest Lancement Python : {test_python_path}")
    # launch_project(test_python_path, status_callback=print_status, feedback_callback=print_feedback)
    # time.sleep(3) # Laisser le temps aux threads

    # Testez un répertoire avec package.json et script start (simuler un projet Node.js)
    # test_nodejs_path = "./test_nodejs_project"
    # os.makedirs(test_nodejs_path, exist_ok=True)
    # package_json_content = {"scripts": {"start": "echo 'Bonjour depuis Node.js start!'"}}
    # with open(os.path.join(test_nodejs_path, "package.json"), "w") as f:
    #      json.dump(package_json_content, f)
    # print(f"\nTest Lancement Node.js : {test_nodejs_path}")
    # launch_project(test_nodejs_path, status_callback=print_status, feedback_callback=print_feedback)
    # time.sleep(3)

    # Testez un répertoire sans aucun des éléments connus
    # test_unknown_path = "./test_unknown_project"
    # os.makedirs(test_unknown_path, exist_ok=True)
    # print(f"\nTest Lancement Inconnu : {test_unknown_path}")
    # launch_project(test_unknown_path, status_callback=print_status, feedback_callback=print_feedback)
    # time.sleep(3)

    # Nettoyage (optionnel)
    # import shutil
    # for path in [test_python_path, test_nodejs_path, test_unknown_path]:
    #      if os.path.exists(path):
    #           try: shutil.rmtree(path)
    #           except Exception as e: print(f"Erreur nettoyage {path}: {e}")

    print("\nFin du test de project_launcher avec heuristiques.")