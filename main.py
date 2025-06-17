import customtkinter as ctk
import tkinter as tk
from github import Repository
from github_connector import search_github_projects
from project_installer import clone_repository
# Importe la fonction de lancement mise à jour avec les heuristiques
from project_launcher import launch_project
from installed_projects_manager import load_installed_projects, remove_installed_project, get_installed_project_by_path
import threading
import tkinter.filedialog as filedialog
import os
import textwrap
import tkinter.messagebox as messagebox
import shutil
import sys
import json # Toujours nécessaire pour lire .gitsurfer.json potentiellement (même si le lanceur ne l'utilise plus)
import shlex # Nécessaire pour shlex.quote ou shlex.join si on affiche des commandes

# --- Définition des Constantes pour les Couleurs et Polices ---
COLOR_BACKGROUND_PRIMARY = "#252526"
COLOR_BACKGROUND_SECONDARY = "#2D2D30"
COLOR_TEXT_PRIMARY = "#E0E0E0"
COLOR_TEXT_SECONDARY = "#A0A0A0"
COLOR_ACCENT = "#007ACC"
COLOR_ACCENT_HOVER = "#0066b3"
COLOR_RED = "#E51400"
COLOR_DARKRED = "#B91D00"

FONT_PRIMARY = ("Segoe UI", 12)
FONT_TITLE = ("Segoe UI", 24, "bold")
FONT_CARD_TITLE = ("Segoe UI", 18, "bold")
FONT_CARD_INFO = ("Segoe UI", 14)
FONT_CARD_DESCRIPTION = ("Segoe UI", 12)
FONT_STATUS = ("Segoe UI", 12, "italic")
FONT_DETAIL_TITLE = ("Segoe UI", 20, "bold")
FONT_DETAIL_TEXT = ("Segoe UI", 12)
FONT_FEEDBACK = ("Segoe UI", 10)
FONT_INSTALL_PATH_CHECK = ("Segoe UI", 10, "italic")
FONT_LIBRARY_CARD_TITLE = ("Segoe UI", 16, "bold")
FONT_LIBRARY_CARD_PATH = ("Segoe UI", 10, "italic")
# FONT_LAUNCH_INFO = ("Segoe UI", 10, "italic") # Ce label affichera maintenant le feedback direct du lanceur


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuration de la Fenêtre Principale ---
        self.title("GitSurfer")
        self.geometry("1200x800")
        self.configure(fg_color=COLOR_BACKGROUND_PRIMARY)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # --- Variables d'état ---
        self.current_detail_repo = None

        # --- Widgets de l'application ---
        self.tabview = ctk.CTkTabview(self, fg_color="transparent")
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        self.tabview.grid_columnconfigure(0, weight=1)

        self.tabview.add("Rechercher")
        self.tabview.tab("Rechercher").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Rechercher").grid_columnconfigure(1, weight=2)
        self.tabview.tab("Rechercher").grid_rowconfigure(1, weight=1)

        self.tabview.add("Bibliothèque")
        self.tabview.tab("Bibliothèque").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Bibliothèque").grid_rowconfigure(0, weight=1)

        # Widgets "Rechercher"
        self.search_frame = ctk.CTkFrame(self.tabview.tab("Rechercher"), corner_radius=0, fg_color=COLOR_BACKGROUND_SECONDARY)
        self.search_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Rechercher des projets GitHub...",
            fg_color=COLOR_BACKGROUND_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            placeholder_text_color=COLOR_TEXT_SECONDARY,
            border_color=COLOR_ACCENT,
            border_width=1,
            font=FONT_PRIMARY
        )
        self.search_entry.grid(row=0, column=0, padx=(20, 10), pady=10, sticky="ew")
        self.search_entry.bind("<Return>", lambda event=None: self.perform_search())

        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Rechercher",
            command=self.perform_search,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=FONT_PRIMARY
        )
        self.search_button.grid(row=0, column=1, padx=(0, 20), pady=10)

        self.results_scroll_frame = ctk.CTkScrollableFrame(
            self.tabview.tab("Rechercher"),
            corner_radius=0,
            fg_color="transparent"
        )
        self.results_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=10)
        self.results_scroll_frame.grid_columnconfigure(0, weight=1)

        self.results_placeholder_label = ctk.CTkLabel(
            self.results_scroll_frame,
            text="Les résultats de la recherche apparaîtront ici.",
            font=FONT_TITLE,
            text_color=COLOR_TEXT_SECONDARY
        )
        self.results_placeholder_label.pack(expand=True)

        self.detail_scroll_frame = ctk.CTkScrollableFrame(
             self.tabview.tab("Rechercher"),
             corner_radius=0,
             fg_color=COLOR_BACKGROUND_SECONDARY
        )
        self.detail_scroll_frame.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=10)
        self.detail_scroll_frame.grid_columnconfigure(0, weight=1)

        self.detail_placeholder_label = ctk.CTkLabel(
             self.detail_scroll_frame,
             text="Sélectionnez un projet pour voir les détails.",
             font=FONT_TITLE,
             text_color=COLOR_TEXT_SECONDARY
        )
        self.detail_placeholder_label.pack(expand=True)

        self.launch_feedback_label = None
        self.install_path_check_label = None


        # Widgets "Bibliothèque"
        self.library_scroll_frame = ctk.CTkScrollableFrame(
             self.tabview.tab("Bibliothèque"),
             corner_radius=0,
             fg_color="transparent"
        )
        self.library_scroll_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        self.library_scroll_frame.grid_columnconfigure(0, weight=1)

        self.library_placeholder_label = ctk.CTkLabel(
             self.library_scroll_frame,
             text="Aucun projet installé pour l'instant.",
             font=FONT_TITLE,
             text_color=COLOR_TEXT_SECONDARY
        )
        self.library_placeholder_label.pack(expand=True)


        # Barre de statut
        self.status_bar = ctk.CTkFrame(self, height=35, corner_radius=0, fg_color=COLOR_BACKGROUND_SECONDARY)
        self.status_bar.grid(row=1, column=0, sticky="nsew")
        self.status_bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Prêt.",
            font=FONT_STATUS,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # Chargement initial des projets installés
        self.load_and_display_installed_projects()


    # --- Méthodes de l'application ---

    def update_status(self, message):
        """
        Met à jour le texte de la barre de statut.
        Utilise after() pour s'assurer que la mise à jour se fait dans le thread principal de Tkinter.
        """
        display_message = (message[:100] + '...') if len(message) > 100 else message
        self.after(0, lambda: self.status_label.configure(text=display_message))

    def update_launch_feedback(self, message):
         """
         Met à jour le texte du label de feedback de lancement dans le panneau de détails.
         """
         if self.launch_feedback_label:
              current_text = self.launch_feedback_label.cget("text")
              new_text = f"{current_text}\n{message}" if current_text else message
              max_lines = 10
              lines = new_text.splitlines()
              if len(lines) > max_lines:
                   new_text = "\n".join(lines[-max_lines:])

              self.after(0, lambda: self.launch_feedback_label.configure(text=new_text))


    def perform_search(self):
        search_query = self.search_entry.get().strip()
        if not search_query:
            self.update_status("La requête de recherche est vide.")
            return

        self.update_status(f"Lancement de la recherche pour : {search_query}")

        self.clear_results()
        self.clear_details()
        self.results_placeholder_label = ctk.CTkLabel(
            self.results_scroll_frame,
            text="Recherche en cours...",
            font=FONT_TITLE,
            text_color=COLOR_TEXT_SECONDARY
        )
        self.results_placeholder_label.pack(expand=True)

        search_thread = threading.Thread(target=self._run_search_in_thread, args=(search_query,))
        search_thread.start()

    def _run_search_in_thread(self, query):
        found_repositories = search_github_projects(query)
        self.after(0, self._display_results_in_ui, found_repositories)

    def _display_results_in_ui(self, found_repositories):
        self.clear_results()

        if found_repositories:
            self.update_status(f"{len(found_repositories)} résultats trouvés.")
            for repo in found_repositories:
                self.create_project_card(repo)
        else:
            self.update_status("Aucun projet trouvé.")
            self.results_placeholder_label = ctk.CTkLabel(
                self.results_scroll_frame,
                text="Aucun projet trouvé.",
                font=FONT_TITLE,
                text_color=COLOR_TEXT_SECONDARY
            )
            self.results_placeholder_label.pack(expand=True)

    def clear_results(self):
        for widget in self.results_scroll_frame.winfo_children():
            widget.destroy()

    def clear_details(self):
         for widget in self.detail_scroll_frame.winfo_children():
              widget.destroy()
         self.launch_feedback_label = None
         self.install_path_check_label = None
         self.current_detail_repo = None
         self.detail_placeholder_label = ctk.CTkLabel(
              self.detail_scroll_frame,
              text="Sélectionnez un projet pour voir les détails.",
              font=FONT_TITLE,
              text_color=COLOR_TEXT_SECONDARY
         )
         self.detail_placeholder_label.pack(expand=True)


    def clear_library(self):
         for widget in self.library_scroll_frame.winfo_children():
              widget.destroy()
         self.library_placeholder_label = ctk.CTkLabel(
              self.library_scroll_frame,
              text="Aucun projet installé pour l'instant.",
              font=FONT_TITLE,
              text_color=COLOR_TEXT_SECONDARY
         )
         self.library_placeholder_label.pack(expand=True)


    def create_project_card(self, repo: Repository):
        card_frame = ctk.CTkFrame(
            self.results_scroll_frame,
            corner_radius=8,
            fg_color=COLOR_BACKGROUND_SECONDARY
        )
        card_frame.pack(fill="x", pady=5, padx=5)
        card_frame.grid_columnconfigure(0, weight=1)

        card_frame.bind("<Button-1>", lambda event, r=repo: self.show_project_details(r))
        for widget in card_frame.winfo_children():
             widget.bind("<Button-1>", lambda event, r=repo: self.show_project_details(r))


        project_name_label = ctk.CTkLabel(
            card_frame,
            text=repo.full_name,
            font=FONT_CARD_TITLE,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w"
        )
        project_name_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        project_name_label.bind("<Button-1>", lambda event, r=repo: self.show_project_details(r))

        info_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        info_frame.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.bind("<Button-1>", lambda event, r=repo: self.show_project_details(r))
        for widget in info_frame.winfo_children():
             widget.bind("<Button-1>", lambda event, r=repo: self.show_project_details(r))


        stars_label = ctk.CTkLabel(
            info_frame,
            text=f"⭐ {repo.stargazers_count}",
            font=FONT_CARD_INFO,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        stars_label.grid(row=0, column=0, sticky="w")
        stars_label.bind("<Button-1>", lambda event, r=repo: self.show_project_details(r))


        language_text = repo.language if repo.language else "N/A"
        language_label = ctk.CTkLabel(
            info_frame,
            text=f"Langage: {language_text}",
            font=FONT_CARD_INFO,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="e"
        )
        language_label.grid(row=0, column=1, sticky="e", padx=(10, 0))
        language_label.bind("<Button-1>", lambda event, r=repo: self.show_project_details(r))


        description_text = repo.description if repo.description else "Pas de description."
        description_label = ctk.CTkLabel(
            card_frame,
            text=description_text,
            font=FONT_CARD_DESCRIPTION,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=550
        )
        description_label.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        description_label.bind("<Button-1>", lambda event, r=repo: self.show_project_details(r))


        install_button = ctk.CTkButton(
            card_frame,
            text="Installer",
            width=100,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            font=FONT_PRIMARY,
            command=lambda r=repo: self.prompt_install_path(r)
        )
        install_button.grid(row=0, column=1, rowspan=3, padx=10, pady=10, sticky="ns")

    def show_project_details(self, repo: Repository):
         """
         Affiche les détails d'un projet sélectionné dans le panneau de droite (onglet Rechercher).
         """
         self.clear_details()
         self.current_detail_repo = repo

         self.update_status(f"Affichage des détails pour {repo.full_name}...")

         detail_title_label = ctk.CTkLabel(
              self.detail_scroll_frame,
              text=repo.full_name,
              font=FONT_DETAIL_TITLE,
              text_color=COLOR_TEXT_PRIMARY,
              anchor="w",
              wraplength=550,
              justify="left"
         )
         detail_title_label.pack(padx=20, pady=(20, 10), fill="x")

         detail_info_frame = ctk.CTkFrame(self.detail_scroll_frame, fg_color="transparent")
         detail_info_frame.pack(padx=20, pady=(0, 10), fill="x")
         detail_info_frame.grid_columnconfigure(0, weight=1)

         stars_label = ctk.CTkLabel(detail_info_frame, text=f"⭐ {repo.stargazers_count}", font=FONT_CARD_INFO, text_color=COLOR_TEXT_SECONDARY, anchor="w")
         stars_label.grid(row=0, column=0, sticky="w")

         forks_label = ctk.CTkLabel(detail_info_frame, text=f"🍴 {repo.forks_count}", font=FONT_CARD_INFO, text_color=COLOR_TEXT_SECONDARY, anchor="w")
         forks_label.grid(row=0, column=1, sticky="w", padx=20)

         language_label = ctk.CTkLabel(detail_info_frame, text=f"Langage: {repo.language if repo.language else 'N/A'}", font=FONT_CARD_INFO, text_color=COLOR_TEXT_SECONDARY, anchor="e")
         language_label.grid(row=0, column=2, sticky="e", padx=(10, 0))

         detail_description_label = ctk.CTkLabel(
              self.detail_scroll_frame,
              text=repo.description if repo.description else "Pas de description détaillée.",
              font=FONT_DETAIL_TEXT,
              text_color=COLOR_TEXT_SECONDARY,
              anchor="w",
              wraplength=550,
              justify="left"
         )
         detail_description_label.pack(padx=20, pady=(0, 20), fill="x")

         github_link_label = ctk.CTkLabel(
              self.detail_scroll_frame,
              text=f"Voir sur GitHub: {repo.html_url}",
              font=FONT_DETAIL_TEXT,
              text_color=COLOR_ACCENT,
              cursor="hand2",
              anchor="w"
         )
         github_link_label.pack(padx=20, pady=(0, 20), fill="x")
         github_link_label.bind("<Button-1>", lambda event, url=repo.html_url: self.open_url(url))

         self.readme_content_label = ctk.CTkLabel(
              self.detail_scroll_frame,
              text="Statut du README : Non chargé (Projet non installé ou README introuvable).",
              font=FONT_DETAIL_TEXT,
              text_color=COLOR_TEXT_SECONDARY,
              anchor="w",
              wraplength=550,
              justify="left"
         )
         self.readme_content_label.pack(padx=20, pady=(0, 20), fill="x")

         self.launch_feedback_label = ctk.CTkLabel(
              self.detail_scroll_frame,
              text="",
              font=FONT_FEEDBACK,
              text_color=COLOR_TEXT_SECONDARY,
              anchor="w",
              wraplength=550,
              justify="left"
         )
         self.launch_feedback_label.pack(padx=20, pady=(0, 10), fill="x")


         potential_install_base_dir = os.path.join(os.path.expanduser("~"), "GitSurfer_Projects")
         potential_install_path = os.path.join(potential_install_base_dir, repo.name)
         normalized_potential_install_path = os.path.normpath(potential_install_path)
         installed_project_info = get_installed_project_by_path(normalized_potential_install_path)

         self.install_path_check_label = ctk.CTkLabel(
             self.detail_scroll_frame,
             text=f"Chemin d'installation attendu : {normalized_potential_install_path}",
             font=FONT_INSTALL_PATH_CHECK,
             text_color=COLOR_TEXT_SECONDARY,
             anchor="w",
             wraplength=550,
             justify="left"
         )
         self.install_path_check_label.pack(padx=20, pady=(0, 5), fill="x")


         if installed_project_info:
             self.install_path_check_label.configure(text=f"Projet trouvé à : {installed_project_info['path']}", text_color="green")

             # Bouton Lancer - Toujours affiché pour les projets installés dans les détails également
             launch_button = ctk.CTkButton(
                  self.detail_scroll_frame,
                  text="Lancer le Projet",
                  fg_color="green",
                  hover_color="darkgreen",
                  text_color=COLOR_TEXT_PRIMARY,
                  font=FONT_PRIMARY,
                  command=lambda path=installed_project_info['path']: self.launch_project_from_ui(path)
             )
             launch_button.pack(padx=20, pady=10)

             readme_thread = threading.Thread(
                  target=self._load_readme_in_thread,
                  args=(installed_project_info['path'], self.readme_content_label)
             )
             readme_thread.start()

             delete_button = ctk.CTkButton(
                  self.detail_scroll_frame,
                  text="Supprimer le Projet",
                  fg_color=COLOR_RED,
                  hover_color=COLOR_DARKRED,
                  text_color=COLOR_TEXT_PRIMARY,
                  font=FONT_PRIMARY,
                  command=lambda path=installed_project_info['path']: self.delete_installed_project(path)
             )
             delete_button.pack(padx=20, pady=10)

         else:
             self.install_path_check_label.configure(text=f"Projet non installé au chemin attendu : {normalized_potential_install_path}", text_color="red")
             self.readme_content_label.configure(text="Installez le projet pour voir le README, le lancer et le supprimer.")


    def _load_readme_in_thread(self, project_path, readme_label):
        readme_content = "README.md ou README.rst introuvable dans le projet installé."
        readme_path_md = os.path.join(project_path, "README.md")
        readme_path_rst = os.path.join(project_path, "README.rst")

        try:
            if os.path.exists(readme_path_md):
                with open(readme_path_md, "r", encoding="utf-8") as f:
                    readme_content = f.read()
                readme_content = f"--- README.md ---\n\n{readme_content}"
            elif os.path.exists(readme_path_rst):
                 with open(readme_path_rst, "r", encoding="utf-8") as f:
                     readme_content = f.read()
                 readme_content = f"--- README.rst ---\n\n{readme_content}"

        except Exception as e:
             readme_content = f"Erreur lors de la lecture du fichier README : {e}"
             print(f"Erreur lors du chargement du README : {e}")

        self.after(0, lambda: readme_label.configure(text=readme_content))


    def prompt_install_path(self, repo: Repository):
        initial_dir = os.path.join(os.path.expanduser("~"), "GitSurfer_Projects")
        if not os.path.exists(initial_dir):
             try:
                  os.makedirs(initial_dir)
             except OSError as e:
                  print(f"Erreur lors de la création du répertoire initial d'installation : {e}")
                  initial_dir = os.path.expanduser("~")

        install_directory = filedialog.askdirectory(
            title=f"Sélectionner le répertoire d'installation pour {repo.name}",
            initialdir=initial_dir
        )

        if install_directory:
            project_name = repo.name
            full_install_path = os.path.join(install_directory, project_name)

            installed_info = get_installed_project_by_path(full_install_path)
            if installed_info:
                 messagebox.showinfo("Installation Annulée", f"Le projet '{installed_info.get('name', 'Inconnu')}' semble déjà installé à :\n{installed_info['path']}")
                 self.update_status("Installation annulée : Projet déjà installé à ce chemin.")
                 return

            self.update_status(f"Préparation de l'installation de {repo.full_name} dans {full_install_path}...")

            repo_info_for_install = {
                 'name': repo.name,
                 'full_name': repo.full_name,
                 'url': repo.clone_url,
                 'language': repo.language if repo.language else 'Unknown'
            }
            install_thread = threading.Thread(
                target=self._run_installation_in_thread,
                args=(repo.clone_url, full_install_path, repo_info_for_install, self.update_status)
            )
            install_thread.start()
        else:
            self.update_status("Installation annulée par l'utilisateur.")

    def _run_installation_in_thread(self, repo_url, install_path, repo_info, status_callback):
        success = clone_repository(repo_url, install_path, repo_info=repo_info, status_callback=status_callback)
        self.after(0, self._post_installation_update, success, install_path, repo_info)


    def _post_installation_update(self, success, install_path, repo_info):
        if success:
            self.load_and_display_installed_projects()
            installed_project_info = get_installed_project_by_path(install_path)
            if self.current_detail_repo and installed_project_info:
                 potential_detail_path = os.path.normpath(os.path.join(os.path.expanduser("~"), "GitSurfer_Projects", self.current_detail_repo.name))
                 if os.path.normpath(installed_project_info['path']) == potential_detail_path:
                      self.show_project_details(self.current_detail_repo)
            pass
        else:
            pass

    def launch_project_from_ui(self, project_path):
         normalized_project_path = os.path.normpath(project_path)

         if not os.path.isdir(normalized_project_path):
              message = f"Erreur : Le répertoire du projet n'existe plus ou est inaccessible : {normalized_project_path}"
              self.update_status(message)
              messagebox.showerror("Erreur de Lancement", message)
              self.after(0, self.check_and_clean_installed_projects)
              return

         self.update_status(f"Préparation au lancement du projet dans {normalized_project_path}...")
         if self.launch_feedback_label:
              self.after(0, lambda: self.launch_feedback_label.configure(text=""))

         launch_thread = threading.Thread(
              target=launch_project,
              args=(normalized_project_path, self.update_status, self.update_launch_feedback)
         )
         launch_thread.start()


    def open_url(self, url):
         import webbrowser
         try:
              webbrowser.open(url)
              self.update_status(f"Ouverture de l'URL : {url}")
         except Exception as e:
              self.update_status(f"Erreur lors de l'ouverture de l'URL {url}: {e}")
              messagebox.showerror("Erreur d'ouverture d'URL", f"Impossible d'ouvrir l'URL :\n{url}\nErreur : {e}")


    def load_and_display_installed_projects(self):
         self.clear_library()

         installed_projects = load_installed_projects()

         if not installed_projects:
              self.library_placeholder_label.pack(expand=True)
         else:
              if self.library_placeholder_label:
                   self.library_placeholder_label.pack_forget()

              for project_info in installed_projects:
                   if os.path.isdir(project_info.get('path', '')):
                        self.create_installed_project_card(project_info)
                   else:
                        missing_path = project_info.get('path', 'Chemin Inconnu')
                        missing_name = project_info.get('name', 'Projet Inconnu')
                        message = f"Avertissement : Le répertoire du projet installé '{missing_name}' est manquant sur le disque : {missing_path}. Il sera retiré de la liste."
                        print(message)
                        self.update_status(message)
                        self.after(0, lambda path=missing_path: remove_installed_project(path))

         self.after(200, self._update_library_display_count)

    def _update_library_display_count(self):
        displayed_projects_count = len(self.library_scroll_frame.winfo_children()) - (1 if self.library_placeholder_label.winfo_ismapped() else 0)
        self.update_status(f"{displayed_projects_count} projets installés affichés.")


    def check_and_clean_installed_projects(self):
         installed_projects = load_installed_projects()
         projects_to_remove = []
         for project_info in installed_projects:
              project_path = project_info.get('path')
              if project_path and not os.path.isdir(os.path.normpath(project_path)):
                   projects_to_remove.append(project_path)

         if projects_to_remove:
              self.update_status(f"Détection de {len(projects_to_remove)} projets installés dont le répertoire est manquant. Nettoyage de la liste...")
              for path in projects_to_remove:
                   self.after(0, lambda p=path: remove_installed_project(p))
              self.after(500, self.load_and_display_installed_projects)
         else:
              pass


    def create_installed_project_card(self, project_info):
         card_frame = ctk.CTkFrame(
              self.library_scroll_frame,
              corner_radius=8,
              fg_color=COLOR_BACKGROUND_SECONDARY
         )
         card_frame.pack(fill="x", pady=5, padx=5)

         card_frame.grid_columnconfigure(0, weight=1)
         card_frame.grid_columnconfigure(1, weight=0)
         card_frame.grid_columnconfigure(2, weight=0)


         project_name_label = ctk.CTkLabel(
              card_frame,
              text=project_info.get('full_name', project_info.get('name', 'Projet inconnu')),
              font=FONT_LIBRARY_CARD_TITLE,
              text_color=COLOR_TEXT_PRIMARY,
              anchor="w"
         )
         project_name_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

         project_path_label = ctk.CTkLabel(
              card_frame,
              text=f"Chemin : {project_info.get('path', 'N/A')}",
              font=FONT_LIBRARY_CARD_PATH,
              text_color=COLOR_TEXT_SECONDARY,
              anchor="w",
              wraplength=600,
              justify="left"
         )
         project_path_label.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

         # Bouton Lancer - Toujours affiché pour les projets installés
         launch_button = ctk.CTkButton(
              card_frame,
              text="Lancer",
              width=80,
              fg_color="green",
              hover_color="darkgreen",
              text_color=COLOR_TEXT_PRIMARY,
              font=FONT_PRIMARY,
              command=lambda path=project_info.get('path'): self.launch_project_from_ui(path)
         )
         launch_button.grid(row=0, column=1, rowspan=2, padx=5, pady=10, sticky="ns")


         delete_button = ctk.CTkButton(
              card_frame,
              text="Supprimer",
              width=80,
              fg_color=COLOR_RED,
              hover_color=COLOR_DARKRED,
              text_color=COLOR_TEXT_PRIMARY,
              font=FONT_PRIMARY,
              command=lambda path=project_info.get('path'): self.delete_installed_project(path)
         )
         delete_button.grid(row=0, column=2, rowspan=2, padx=(5, 10), pady=10, sticky="ns")


    def delete_installed_project(self, project_path):
         if not project_path:
              self.update_status("Erreur : Chemin du projet à supprimer non spécifié.")
              return

         project_info = get_installed_project_by_path(project_path)
         project_name = project_info.get('full_name', project_info.get('name', os.path.basename(project_path))) if project_info else os.path.basename(project_path)


         confirm = messagebox.askyesno(
              "Confirmer la suppression",
              f"Voulez-vous vraiment supprimer le projet '{project_name}' et son répertoire d'installation ?\n\n"
              f"Chemin : {project_path}\n\n"
              f"Cette action est irréversible et supprimera tous les fichiers dans ce répertoire."
         )

         if confirm:
              self.update_status(f"Suppression du projet et du répertoire : {project_path}...")
              delete_thread = threading.Thread(target=self._run_delete_in_thread, args=(project_path,))
              delete_thread.start()
         else:
              self.update_status("Suppression annulée par l'utilisateur.")

    def _run_delete_in_thread(self, project_path):
         try:
              normalized_project_path = os.path.normpath(project_path)

              if os.path.exists(normalized_project_path):
                   shutil.rmtree(normalized_project_path)
                   message = f"Répertoire du projet supprimé avec succès : {normalized_project_path}"
                   print(message)
                   self.after(0, lambda: self.update_status(message))

                   removed_from_list = remove_installed_project(normalized_project_path)
                   if removed_from_list:
                       message_list = f"Projet retiré de la liste des projets installés."
                       print(message_list)
                       self.after(0, lambda: self.update_status(message_list))
                   else:
                       message_list_err = f"Avertissement : Le projet a été supprimé du disque, mais n'a pas été trouvé dans la liste des projets installés."
                       print(message_list_err)
                       self.after(0, lambda: self.update_status(message_list_err))

                   self.after(0, self.load_and_display_installed_projects)

                   if self.current_detail_repo and 'path' in self.current_detail_repo and os.path.normpath(self.current_detail_repo['path']) == normalized_project_path:
                        self.after(0, self.clear_details)


              else:
                   message = f"Erreur : Le répertoire du projet n'existe pas et ne peut pas être supprimé : {normalized_project_path}"
                   print(message)
                   self.after(0, lambda: self.update_status(message))
                   self.after(0, lambda path=normalized_project_path: remove_installed_project(path))
                   self.after(500, self.load_and_display_installed_projects)

         except OSError as e:
              error_path_in_exception = getattr(e, 'filename', normalized_project_path)
              normalized_error_path = os.path.normpath(error_path_in_exception) if error_path_in_exception else "Chemin inconnu"

              message = f"Erreur système lors de la suppression du répertoire {normalized_project_path}: {e}"
              print(message)
              self.after(0, lambda: self.update_status(message))

              def show_error_box():
                   error_detail = f"Veuillez vérifier les permissions et si des fichiers ne sont pas utilisés par un autre programme.\n\n Détails: {e}"
                   if sys.platform == "win32" and getattr(e, 'errno', None) == 5:
                        messagebox.showerror(
                            "Erreur de suppression (Accès Refusé)",
                            f"Impossible de supprimer le répertoire {normalized_project_path}:\n\n"
                            f"Cause possible : Les fichiers sont peut-être utilisés par un autre programme ou il y a un problème de permissions.\n"
                            f"Fichier/Dossier problématique : {normalized_error_path}\n\n"
                            f"Veuillez fermer toutes les applications qui pourraient accéder à ce répertoire (éditeurs, consoles, etc.) et vérifier les permissions du dossier.\n\n"
                            f"Détails de l'erreur système : {e}"
                        )
                   else:
                        messagebox.showerror(
                            "Erreur de suppression (Système)",
                            f"Impossible de supprimer le répertoire {normalized_project_path}:\n\n"
                            f"{error_detail}"
                        )
              self.after(0, show_error_box)

         except Exception as e:
              message = f"Une erreur inattendue est survenue lors de la suppression : {e}"
              print(message)
              self.after(0, lambda: self.update_status(message))
              self.after(0, lambda: messagebox.showerror("Erreur inattendue lors de la suppression", f"Une erreur est survenue :\n{e}"))


if __name__ == "__main__":
    app = App()
    app.mainloop()