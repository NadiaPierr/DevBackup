"""CustomTkinter user interface for Dev Project Backup."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from backup_manager import LANGUAGES, BackupManager, BackupPlan, Project, Version


ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class DevBackupApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Dev Project Backup")
        self.geometry("1050x650")
        self.minsize(850, 520)
        self.manager = BackupManager()
        self.projects: list[Project] = []
        self.selected_project: Project | None = None
        self._build_ui()
        self.refresh_projects()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(sidebar, text="DEV BACKUP", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=24, pady=(26, 8), sticky="w")
        ctk.CTkLabel(sidebar, text="Τα projects σου", text_color="gray60").grid(row=1, column=0, padx=24, pady=(0, 12), sticky="w")
        self.project_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.project_list.grid(row=2, column=0, padx=10, sticky="nsew")
        self.project_list.grid_columnconfigure(0, weight=1)
        sidebar_actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        sidebar_actions.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        sidebar_actions.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(sidebar_actions, text="＋  Προσθήκη project", command=self.open_add_dialog).grid(row=0, column=0, sticky="ew")
        self.remove_button = ctk.CTkButton(
            sidebar_actions, text="Αφαίρεση από τον κατάλογο", fg_color="transparent",
            border_width=1, text_color=("#b42318", "#ff8a80"), command=self.remove_selected_project,
            state="disabled",
        )
        self.remove_button.grid(row=1, column=0, pady=(8, 0), sticky="ew")

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, padx=32, pady=26, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(3, weight=1)
        self.title_label = ctk.CTkLabel(self.content, text="Επίλεξε ένα project", font=ctk.CTkFont(size=28, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")
        self.info_label = ctk.CTkLabel(self.content, text="Πρόσθεσε το πρώτο project για να ξεκινήσεις.", text_color="gray60")
        self.info_label.grid(row=1, column=0, pady=(4, 20), sticky="w")

        actions = ctk.CTkFrame(self.content, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        actions.grid_columnconfigure(0, weight=1)
        self.note_entry = ctk.CTkEntry(actions, placeholder_text="Όνομα έκδοσης, π.χ. v1.0-login")
        self.note_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.rules_button = ctk.CTkButton(actions, text="Ρυθμίσεις…", width=100, command=self.open_rules_dialog, state="disabled")
        self.rules_button.grid(row=0, column=1, padx=(0, 10))
        self.backup_button = ctk.CTkButton(actions, text="Δημιουργία backup", command=self.start_backup, state="disabled")
        self.backup_button.grid(row=0, column=2)

        versions_card = ctk.CTkFrame(self.content)
        versions_card.grid(row=3, column=0, sticky="nsew")
        versions_card.grid_columnconfigure(0, weight=1)
        versions_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(versions_card, text="Ιστορικό εκδόσεων", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=20, pady=(18, 8), sticky="w")
        self.version_list = ctk.CTkScrollableFrame(versions_card, fg_color="transparent")
        self.version_list.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.version_list.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(self.content, text=f"Τοπική αποθήκευση: {self.manager.data_dir}", text_color="gray60")
        self.status_label.grid(row=4, column=0, pady=(12, 0), sticky="w")

    @staticmethod
    def _clear(frame: ctk.CTkFrame) -> None:
        for widget in frame.winfo_children():
            widget.destroy()

    def refresh_projects(self) -> None:
        self.projects = self.manager.list_projects()
        self._clear(self.project_list)
        for project in self.projects:
            ctk.CTkButton(self.project_list, text=f"{project.name}\n{project.language}", anchor="w", height=52,
                          fg_color="transparent", hover_color=("gray80", "gray25"),
                          command=lambda p=project: self.select_project(p)).grid(sticky="ew", pady=3)
        if self.selected_project:
            match = next((p for p in self.projects if p.id == self.selected_project.id), None)
            if match:
                self.select_project(match)

    def select_project(self, project: Project) -> None:
        self.selected_project = project
        self.title_label.configure(text=project.name)
        self.info_label.configure(text=f"{project.language}  •  {project.path}\nBackup: {project.backup_dir}")
        self.backup_button.configure(state="normal")
        self.rules_button.configure(state="normal")
        self.remove_button.configure(state="normal")
        self.refresh_versions()

    def refresh_versions(self) -> None:
        self._clear(self.version_list)
        if not self.selected_project:
            return
        versions = self.manager.list_versions(self.selected_project.id)
        if not versions:
            ctk.CTkLabel(self.version_list, text="Δεν υπάρχουν ακόμη backups.", text_color="gray60").grid(pady=30)
        for version in versions:
            self._version_row(version)

    def _version_row(self, version: Version) -> None:
        row = ctk.CTkFrame(self.version_list)
        row.grid(sticky="ew", padx=4, pady=5)
        row.grid_columnconfigure(0, weight=1)
        date = datetime.fromisoformat(version.created_at).strftime("%d/%m/%Y  %H:%M")
        label = f"{date}   •   {self.manager.format_size(version.size)}"
        if version.note:
            label += f"\n{version.note}"
        ctk.CTkLabel(row, text=label, justify="left").grid(row=0, column=0, padx=14, pady=10, sticky="w")
        ctk.CTkButton(row, text="Επαναφορά…", width=105, command=lambda v=version: self.restore_version(v)).grid(row=0, column=1, padx=12)

    def open_add_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Νέο project")
        dialog.geometry("620x620")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            dialog,
            text="Νέο project",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(padx=24, pady=(22, 2), sticky="w")
        ctk.CTkLabel(
            dialog,
            text="Όνομα, πηγή και προορισμός backup.",
            text_color="gray60",
        ).grid(padx=24, pady=(0, 18), sticky="w")

        ctk.CTkLabel(dialog, text="Όνομα project").grid(padx=24, sticky="w")
        name = ctk.CTkEntry(dialog, placeholder_text="π.χ. E-shop API")
        name.grid(padx=24, pady=(3, 8), sticky="ew")
        ctk.CTkLabel(dialog, text="Τεχνολογία / γλώσσα").grid(padx=24, sticky="w")
        language = ctk.CTkOptionMenu(dialog, values=list(LANGUAGES))
        language.set("Python")
        language.grid(padx=24, pady=(3, 14), sticky="ew")

        ctk.CTkLabel(
            dialog,
            text="Πηγή — φάκελος project",
            font=ctk.CTkFont(weight="bold"),
        ).grid(padx=24, sticky="w")
        path_row = ctk.CTkFrame(dialog, fg_color="transparent")
        path_row.grid(padx=24, pady=(3, 8), sticky="ew")
        path_row.grid_columnconfigure(0, weight=1)
        path = ctk.CTkEntry(path_row, placeholder_text=r"π.χ. C:\Projects\eshop-api")
        path.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ctk.CTkButton(path_row, text="Επιλογή…", width=90, command=lambda: self._choose_source(path, name)).grid(row=0, column=1)
        ctk.CTkLabel(
            dialog,
            text="Προορισμός — φάκελος ZIP backups",
            font=ctk.CTkFont(weight="bold"),
        ).grid(padx=24, sticky="w")
        backup_row = ctk.CTkFrame(dialog, fg_color="transparent")
        backup_row.grid(padx=24, pady=(3, 10), sticky="ew")
        backup_row.grid_columnconfigure(0, weight=1)
        backup_path = ctk.CTkEntry(backup_row, placeholder_text=r"π.χ. D:\Backups\Projects")
        backup_path.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        backup_path.insert(0, str(self.manager.default_backup_root))
        ctk.CTkButton(
            backup_row, text="Επιλογή…", width=90,
            command=lambda: self._choose_folder(backup_path, "Επίλεξε φάκελο αποθήκευσης backup"),
        ).grid(row=0, column=1)

        ctk.CTkLabel(dialog, text="Εξαιρέσεις (προαιρετικά)").grid(padx=24, sticky="w")
        exclusions = ctk.CTkEntry(
            dialog,
            placeholder_text="Χώρισέ τα με κόμμα, π.χ. data/*.csv, tmp, *.log",
        )
        exclusions.grid(padx=24, pady=(3, 6), sticky="ew")
        use_gitignore = ctk.CTkCheckBox(dialog, text="Χρήση κανόνων από το .gitignore")
        use_gitignore.select()
        use_gitignore.grid(padx=24, pady=(4, 5), sticky="w")
        include_sensitive = ctk.CTkCheckBox(
            dialog,
            text="Συμπερίληψη πιθανών secrets (.env, keys, credentials)",
        )
        include_sensitive.grid(padx=24, pady=5, sticky="w")

        def save() -> None:
            try:
                patterns = [item.strip() for item in exclusions.get().replace(";", ",").split(",") if item.strip()]
                project = self.manager.add_project(
                    name.get(),
                    path.get(),
                    language.get(),
                    custom_excludes=patterns,
                    use_gitignore=bool(use_gitignore.get()),
                    include_sensitive=bool(include_sensitive.get()),
                    backup_root=backup_path.get(),
                )
                dialog.destroy()
                self.refresh_projects()
                self.select_project(project)
            except Exception as exc:
                messagebox.showerror("Αποτυχία", str(exc), parent=dialog)

        ctk.CTkButton(
            dialog,
            text="Δημιουργία project",
            height=40,
            command=save,
        ).grid(padx=24, pady=(12, 20), sticky="ew")

    @staticmethod
    def _choose_source(path_entry: ctk.CTkEntry, name_entry: ctk.CTkEntry) -> None:
        selected = filedialog.askdirectory(title="Επίλεξε φάκελο project")
        if selected:
            path_entry.delete(0, "end")
            path_entry.insert(0, selected)
            if not name_entry.get():
                name_entry.insert(0, Path(selected).name)

    @staticmethod
    def _choose_folder(path_entry: ctk.CTkEntry, title: str) -> None:
        selected = filedialog.askdirectory(title=title)
        if selected:
            path_entry.delete(0, "end")
            path_entry.insert(0, selected)

    def open_rules_dialog(self) -> None:
        if not self.selected_project:
            return
        project = self.selected_project
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Ρυθμίσεις — {project.name}")
        dialog.geometry("600x430")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(dialog, text="Ρυθμίσεις backup", font=ctk.CTkFont(size=22, weight="bold")).grid(padx=24, pady=(24, 16), sticky="w")
        backup_row = ctk.CTkFrame(dialog, fg_color="transparent")
        backup_row.grid(padx=24, pady=6, sticky="ew")
        backup_row.grid_columnconfigure(0, weight=1)
        backup_path = ctk.CTkEntry(backup_row, placeholder_text="Φάκελος αποθήκευσης νέων backups")
        backup_path.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        backup_path.insert(0, project.backup_dir)
        ctk.CTkButton(
            backup_row, text="Επιλογή…", width=90,
            command=lambda: self._choose_folder(backup_path, "Επίλεξε φάκελο αποθήκευσης νέων backups"),
        ).grid(row=0, column=1)
        ctk.CTkLabel(
            dialog, text="Η αλλαγή ισχύει για νέα backups· τα υπάρχοντα ZIP δεν μετακινούνται.",
            text_color="gray60",
        ).grid(padx=24, pady=(0, 8), sticky="w")
        exclusions = ctk.CTkEntry(dialog, placeholder_text="Εξαιρέσεις χωρισμένες με κόμμα")
        exclusions.grid(padx=24, pady=6, sticky="ew")
        exclusions.insert(0, ", ".join(project.custom_excludes or []))
        use_gitignore = ctk.CTkCheckBox(dialog, text="Χρήση κανόνων από το .gitignore")
        use_gitignore.grid(padx=24, pady=(14, 6), sticky="w")
        if project.use_gitignore:
            use_gitignore.select()
        include_sensitive = ctk.CTkCheckBox(dialog, text="Συμπερίληψη πιθανών secrets (.env, keys, credentials)")
        include_sensitive.grid(padx=24, pady=6, sticky="w")
        if project.include_sensitive:
            include_sensitive.select()

        def save() -> None:
            patterns = [item.strip() for item in exclusions.get().replace(";", ",").split(",") if item.strip()]
            try:
                updated = self.manager.update_project_rules(
                    project.id, patterns, bool(use_gitignore.get()), bool(include_sensitive.get()), backup_path.get()
                )
                self.selected_project = updated
                dialog.destroy()
                self.refresh_projects()
                self.status_label.configure(text="Οι ρυθμίσεις backup αποθηκεύτηκαν.")
            except Exception as exc:
                messagebox.showerror("Αποτυχία", str(exc), parent=dialog)

        ctk.CTkButton(dialog, text="Αποθήκευση ρυθμίσεων", command=save).grid(padx=24, pady=22, sticky="ew")

    def remove_selected_project(self) -> None:
        if not self.selected_project:
            return
        project = self.selected_project
        version_count = len(self.manager.list_versions(project.id))
        confirmed = messagebox.askyesno(
            "Αφαίρεση project",
            f"Να αφαιρεθεί το «{project.name}» και το ιστορικό {version_count} εκδόσεων από τον κατάλογο;\n\n"
            f"Τα υπάρχοντα ZIP ΔΕΝ θα διαγραφούν και θα παραμείνουν στο:\n{project.backup_dir}",
            parent=self,
        )
        if not confirmed:
            return
        self.manager.remove_project(project.id)
        self.selected_project = None
        self.refresh_projects()
        self._clear(self.version_list)
        self.title_label.configure(text="Επίλεξε ένα project")
        self.info_label.configure(text="Το project αφαιρέθηκε από τον κατάλογο. Τα ZIP διατηρήθηκαν.")
        self.backup_button.configure(state="disabled")
        self.rules_button.configure(state="disabled")
        self.remove_button.configure(state="disabled")
        self.status_label.configure(text=f"Τοπικός κατάλογος: {self.manager.data_dir}")

    def start_backup(self) -> None:
        if not self.selected_project:
            return
        project_id, note = self.selected_project.id, self.note_entry.get()
        if not note.strip():
            messagebox.showwarning("Όνομα έκδοσης", "Δώσε ένα όνομα για τη νέα έκδοση.", parent=self)
            self.note_entry.focus_set()
            return
        try:
            plan = self.manager.build_plan(project_id)
        except Exception as exc:
            messagebox.showerror("Αποτυχία προεπισκόπησης", str(exc), parent=self)
            return
        if not self._confirm_plan(plan):
            return
        self.backup_button.configure(state="disabled", text="Δημιουργία…")
        self.status_label.configure(text="Το backup δημιουργείται τοπικά…")

        def work() -> None:
            try:
                self.manager.create_backup(project_id, note, plan)
                self.after(0, lambda: self._backup_finished(None))
            except Exception as exc:
                self.after(0, lambda error=exc: self._backup_finished(error))

        threading.Thread(target=work, daemon=True).start()

    def _confirm_plan(self, plan: BackupPlan) -> bool:
        lines = [
            f"Αρχεία στο backup: {len(plan.included)}",
            f"Συνολικό αρχικό μέγεθος: {self.manager.format_size(plan.total_size)}",
            f"Εξαιρούμενα αρχεία: {len(plan.excluded)}",
        ]
        if plan.sensitive:
            action = "θα συμπεριληφθούν" if self.selected_project and self.selected_project.include_sensitive else "εξαιρούνται"
            lines.append(f"\nΠιθανά secrets ({action}):")
            lines.extend(f"  • {path}" for path in plan.sensitive[:8])
            if len(plan.sensitive) > 8:
                lines.append(f"  …και {len(plan.sensitive) - 8} ακόμη")
        if plan.large:
            lines.append("\nΜεγάλα αρχεία (≥100 MB):")
            lines.extend(f"  • {path}" for path in plan.large[:8])
            if len(plan.large) > 8:
                lines.append(f"  …και {len(plan.large) - 8} ακόμη")
        if not plan.included:
            messagebox.showwarning("Κενό backup", "Δεν βρέθηκαν αρχεία για backup.", parent=self)
            return False
        lines.append("\nΝα δημιουργηθεί αυτή η έκδοση;")
        return messagebox.askyesno("Προεπισκόπηση backup", "\n".join(lines), parent=self)

    def _backup_finished(self, error: Exception | None) -> None:
        self.backup_button.configure(state="normal", text="Δημιουργία backup")
        if error:
            self.status_label.configure(text="Το backup απέτυχε.")
            messagebox.showerror("Αποτυχία backup", str(error), parent=self)
            return
        self.note_entry.delete(0, "end")
        self.status_label.configure(text="Το backup ολοκληρώθηκε επιτυχώς.")
        self.refresh_versions()

    def restore_version(self, version: Version) -> None:
        destination = filedialog.askdirectory(title="Φάκελος επαναφοράς")
        if not destination:
            return
        target = Path(destination).resolve()
        is_live_project = bool(
            self.selected_project and target == Path(self.selected_project.path).resolve()
        )
        warning = "Ο φάκελος δεν είναι κενός. Υπάρχοντα αρχεία με ίδιο όνομα μπορεί να αντικατασταθούν."
        if is_live_project:
            warning += "\n\nΠριν από την επαναφορά θα δημιουργηθεί αυτόματα ένα backup της τρέχουσας κατάστασης."
        warning += "\n\nΣυνέχεια;"
        if any(target.iterdir()) and not messagebox.askyesno("Επιβεβαίωση επαναφοράς", warning, parent=self):
            return
        try:
            restored, safety_version = self.manager.restore_with_safety_backup(version.id, destination)
            if safety_version:
                self.refresh_versions()
                message = (
                    f"Η έκδοση επαναφέρθηκε στο:\n{restored}\n\n"
                    "Δημιουργήθηκε πρώτα αυτόματο backup της προηγούμενης κατάστασης."
                )
            else:
                message = f"Η έκδοση επαναφέρθηκε στο:\n{restored}"
            messagebox.showinfo("Ολοκληρώθηκε", message, parent=self)
        except Exception as exc:
            messagebox.showerror("Αποτυχία επαναφοράς", str(exc), parent=self)
