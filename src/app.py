"""Modern CustomTkinter interface for Dev Project Backup."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from backup_manager import LANGUAGES, BackupManager, BackupPlan, Project, Version
from version import __version__

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

ACCENT, ACCENT_HOVER, DANGER = "#2563EB", "#1D4ED8", "#DC2626"
MUTED = ("#64748B", "#94A3B8")
CARD = ("#FFFFFF", "#172033")
CARD_ALT = ("#F8FAFC", "#111827")
BORDER = ("#E2E8F0", "#2B364A")
SIDEBAR = ("#F1F5F9", "#0B1120")


class DevBackupApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Dev Project Backup {__version__}")
        self.geometry("1180x760")
        self.minsize(940, 620)
        self.configure(fg_color=("#F8FAFC", "#0F172A"))
        self.manager = BackupManager()
        self.projects: list[Project] = []
        self.selected_project: Project | None = None
        self._build_ui()
        self.refresh_projects()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        sidebar = ctk.CTkFrame(self, width=292, corner_radius=0, fg_color=SIDEBAR)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(2, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, padx=22, pady=(24, 22), sticky="ew")
        brand.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(brand, text="DB", width=42, height=42, corner_radius=12, fg_color=ACCENT,
                     text_color="white", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ctk.CTkLabel(brand, text="Dev Backup", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=1, sticky="sw")
        ctk.CTkLabel(brand, text=f"Τοπικά backups  •  v{__version__}", text_color=MUTED,
                     font=ctk.CTkFont(size=12)).grid(row=1, column=1, sticky="nw")
        ctk.CTkLabel(sidebar, text="PROJECTS", text_color=MUTED,
                     font=ctk.CTkFont(size=11, weight="bold")).grid(row=1, column=0, padx=24, pady=(0, 8), sticky="w")
        self.project_count = ctk.CTkLabel(sidebar, text="", text_color=MUTED, font=ctk.CTkFont(size=11))
        self.project_count.grid(row=1, column=0, padx=24, pady=(0, 8), sticky="e")
        self.project_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent", corner_radius=0)
        self.project_list.grid(row=2, column=0, padx=10, sticky="nsew")
        self.project_list.grid_columnconfigure(0, weight=1)
        side_actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        side_actions.grid(row=3, column=0, padx=18, pady=18, sticky="ew")
        side_actions.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(side_actions, text="＋  Προσθήκη project", height=42, corner_radius=10,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.open_add_dialog).grid(sticky="ew")
        self.remove_button = ctk.CTkButton(side_actions, text="Αφαίρεση από τη λίστα", height=36,
            fg_color="transparent", hover_color=("#FEE2E2", "#3F1D24"), text_color=(DANGER, "#FCA5A5"),
            command=self.remove_selected_project, state="disabled")
        self.remove_button.grid(row=1, column=0, pady=(7, 0), sticky="ew")

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, padx=34, pady=28, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(4, weight=1)
        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        self.eyebrow_label = ctk.CTkLabel(header, text="ΕΠΙΛΕΞΕ PROJECT", text_color=ACCENT,
                                          font=ctk.CTkFont(size=11, weight="bold"))
        self.eyebrow_label.grid(row=0, column=0, sticky="w")
        self.title_label = ctk.CTkLabel(header, text="Τα backups σου, οργανωμένα",
                                        font=ctk.CTkFont(size=30, weight="bold"))
        self.title_label.grid(row=1, column=0, pady=(2, 0), sticky="w")
        self.info_label = ctk.CTkLabel(header, text="Επίλεξε ένα project αριστερά ή πρόσθεσε το πρώτο σου.",
                                       text_color=MUTED, justify="left")
        self.info_label.grid(row=2, column=0, pady=(5, 0), sticky="w")
        self.rules_button = ctk.CTkButton(header, text="⚙  Ρυθμίσεις", width=112, height=36, corner_radius=9,
            fg_color="transparent", border_width=1, border_color=BORDER, text_color=("#334155", "#E2E8F0"),
            hover_color=("#E2E8F0", "#243047"), command=self.open_rules_dialog, state="disabled")
        self.rules_button.grid(row=1, column=1, rowspan=2, padx=(16, 0), sticky="e")

        metrics = ctk.CTkFrame(self.content, fg_color="transparent")
        metrics.grid(row=1, column=0, pady=(22, 14), sticky="ew")
        for column in range(3): metrics.grid_columnconfigure(column, weight=1)
        self.version_count_label = self._metric(metrics, 0, "ΕΚΔΟΣΕΙΣ")
        self.last_backup_label = self._metric(metrics, 1, "ΤΕΛΕΥΤΑΙΟ BACKUP")
        self.storage_label = self._metric(metrics, 2, "ΣΥΝΟΛΙΚΟ ΜΕΓΕΘΟΣ")

        create = ctk.CTkFrame(self.content, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=14)
        create.grid(row=2, column=0, sticky="ew")
        create.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(create, text="Νέο backup", font=ctk.CTkFont(size=17, weight="bold")).grid(row=0, column=0, padx=20, pady=(17, 2), sticky="w")
        ctk.CTkLabel(create, text="Δώσε ένα σύντομο όνομα ώστε να αναγνωρίζεις εύκολα αυτή την έκδοση.",
                     text_color=MUTED).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 12), sticky="w")
        self.note_entry = ctk.CTkEntry(create, height=43, corner_radius=9,
                                       placeholder_text="π.χ. v1.2 — πριν τις αλλαγές στο login")
        self.note_entry.grid(row=2, column=0, padx=(20, 10), pady=(0, 20), sticky="ew")
        self.note_entry.bind("<Return>", lambda _event: self.start_backup())
        self.note_entry.bind("<KP_Enter>", lambda _event: self.start_backup())
        self.backup_button = ctk.CTkButton(create, text="Δημιουργία backup", height=43, corner_radius=9,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.start_backup, state="disabled")
        self.backup_button.grid(row=2, column=1, padx=(0, 20), pady=(0, 20))

        history_head = ctk.CTkFrame(self.content, fg_color="transparent")
        history_head.grid(row=3, column=0, pady=(22, 10), sticky="ew")
        history_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(history_head, text="Ιστορικό εκδόσεων", font=ctk.CTkFont(size=19, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(history_head, text="Οι νεότερες εμφανίζονται πρώτες", text_color=MUTED,
                     font=ctk.CTkFont(size=12)).grid(row=0, column=1, sticky="e")
        versions_card = ctk.CTkFrame(self.content, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=14)
        versions_card.grid(row=4, column=0, sticky="nsew")
        versions_card.grid_columnconfigure(0, weight=1)
        versions_card.grid_rowconfigure(0, weight=1)
        self.version_list = ctk.CTkScrollableFrame(versions_card, fg_color="transparent")
        self.version_list.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        self.version_list.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(self.content, text="Έτοιμο", text_color=MUTED,
                                         font=ctk.CTkFont(size=12), anchor="w")
        self.status_label.grid(row=5, column=0, pady=(10, 0), sticky="ew")

    @staticmethod
    def _metric(parent: ctk.CTkFrame, column: int, title: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=12)
        card.grid(row=0, column=column, padx=(0 if column == 0 else 5, 0 if column == 2 else 5), sticky="ew")
        ctk.CTkLabel(card, text=title, text_color=MUTED, font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w", padx=16, pady=(12, 2))
        label = ctk.CTkLabel(card, text="—", font=ctk.CTkFont(size=18, weight="bold"))
        label.pack(anchor="w", padx=16, pady=(0, 12))
        return label

    @staticmethod
    def _clear(frame: ctk.CTkFrame) -> None:
        for widget in frame.winfo_children(): widget.destroy()

    def refresh_projects(self) -> None:
        self.projects = self.manager.list_projects()
        self.project_count.configure(text=str(len(self.projects)))
        self._clear(self.project_list)
        if not self.projects:
            ctk.CTkLabel(self.project_list, text="Δεν υπάρχουν projects ακόμη.\nΠρόσθεσε ένα για να ξεκινήσεις.",
                         text_color=MUTED, justify="left", wraplength=220).grid(padx=12, pady=24, sticky="w")
        for project in self.projects:
            selected = bool(self.selected_project and project.id == self.selected_project.id)
            ctk.CTkButton(self.project_list, text=f"{project.name}\n{project.language}", anchor="w", height=58,
                corner_radius=10, fg_color=ACCENT if selected else "transparent",
                hover_color=ACCENT_HOVER if selected else ("#E2E8F0", "#1E293B"),
                text_color="white" if selected else ("#1E293B", "#E2E8F0"),
                command=lambda p=project: self.select_project(p)).grid(sticky="ew", pady=3)

    def select_project(self, project: Project) -> None:
        self.selected_project = project
        self.refresh_projects()
        self.eyebrow_label.configure(text=f"{project.language.upper()} PROJECT")
        self.title_label.configure(text=project.name)
        self.info_label.configure(text=f"Πηγή: {project.path}\nΑποθήκευση: {project.backup_dir}")
        self.backup_button.configure(state="normal")
        self.rules_button.configure(state="normal")
        self.remove_button.configure(state="normal")
        self.note_entry.focus_set()
        self.refresh_versions()
        self.status_label.configure(text="Έτοιμο για νέο backup", text_color=MUTED)

    def refresh_versions(self) -> None:
        self._clear(self.version_list)
        if not self.selected_project: return
        versions = self.manager.list_versions(self.selected_project.id)
        self.version_count_label.configure(text=str(len(versions)))
        self.storage_label.configure(text=self.manager.format_size(sum(item.size for item in versions)))
        self.last_backup_label.configure(text=datetime.fromisoformat(versions[0].created_at).strftime("%d/%m/%Y") if versions else "Κανένα ακόμη")
        if not versions:
            empty = ctk.CTkFrame(self.version_list, fg_color="transparent")
            empty.grid(sticky="nsew", pady=48)
            ctk.CTkLabel(empty, text="○", text_color=ACCENT, font=ctk.CTkFont(size=36)).pack()
            ctk.CTkLabel(empty, text="Δεν υπάρχουν backups ακόμη", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(8, 3))
            ctk.CTkLabel(empty, text="Ονόμασε την πρώτη έκδοση παραπάνω και δημιούργησέ την.", text_color=MUTED).pack()
        for version in versions: self._version_row(version)

    def _version_row(self, version: Version) -> None:
        row = ctk.CTkFrame(self.version_list, fg_color=CARD_ALT, corner_radius=10)
        row.grid(sticky="ew", padx=3, pady=4)
        row.grid_columnconfigure(1, weight=1)
        created = datetime.fromisoformat(version.created_at)
        ctk.CTkLabel(row, text=created.strftime("%d\n%b").upper(), width=48, height=48, corner_radius=9,
            fg_color=("#DBEAFE", "#172554"), text_color=("#1D4ED8", "#93C5FD"),
            font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, padx=(12, 10), pady=10)
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(text, text=version.note.strip() if version.note else "Χωρίς όνομα",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(text, text=f"{created.strftime('%H:%M')}  •  {self.manager.format_size(version.size)}",
                     text_color=MUTED, font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(2, 0))
        ctk.CTkButton(row, text="Επαναφορά", width=98, height=34, corner_radius=8, fg_color="transparent",
            border_width=1, border_color=BORDER, text_color=("#334155", "#E2E8F0"),
            hover_color=("#E2E8F0", "#243047"), command=lambda v=version: self.restore_version(v)).grid(row=0, column=2, padx=12)

    def _dialog(self, title: str, subtitle: str, geometry: str) -> tuple[ctk.CTkToplevel, ctk.CTkScrollableFrame]:
        dialog = ctk.CTkToplevel(self)
        dialog.title(title); dialog.geometry(geometry); dialog.transient(self); dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1); dialog.grid_rowconfigure(1, weight=1)
        head = ctk.CTkFrame(dialog, fg_color="transparent")
        head.grid(row=0, column=0, padx=28, pady=(24, 12), sticky="ew")
        ctk.CTkLabel(head, text=title, font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(head, text=subtitle, text_color=MUTED, wraplength=580, justify="left").pack(anchor="w", pady=(4, 0))
        body = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        body.grid(row=1, column=0, padx=24, pady=(0, 20), sticky="nsew"); body.grid_columnconfigure(0, weight=1)
        return dialog, body

    @staticmethod
    def _field(parent, row: int, label: str, placeholder: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, pady=(10, 5), sticky="w")
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder, height=39); entry.grid(row=row + 1, column=0, sticky="ew")
        return entry

    @staticmethod
    def _path_field(parent, row: int, label: str, placeholder: str, choose) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, pady=(12, 5), sticky="w")
        holder = ctk.CTkFrame(parent, fg_color="transparent"); holder.grid(row=row + 1, column=0, sticky="ew"); holder.grid_columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(holder, placeholder_text=placeholder, height=39); entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ctk.CTkButton(holder, text="Επιλογή…", width=92, height=39, command=lambda: choose(entry)).grid(row=0, column=1)
        return entry

    def open_add_dialog(self) -> None:
        dialog, body = self._dialog("Νέο project", "Σύνδεσε έναν φάκελο και όρισε πού θα αποθηκεύονται τα backups.", "680x670")
        name = self._field(body, 0, "Όνομα project", "π.χ. E-shop API")
        ctk.CTkLabel(body, text="Τεχνολογία / γλώσσα", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, pady=(12, 5), sticky="w")
        language = ctk.CTkOptionMenu(body, values=list(LANGUAGES), height=39); language.set("Python"); language.grid(row=3, column=0, sticky="ew")
        path = self._path_field(body, 4, "Φάκελος project", "Επίλεξε τον φάκελο με τον κώδικα", lambda e: self._choose_source(e, name))
        backup_path = self._path_field(body, 6, "Φάκελος αποθήκευσης", "Πού θα δημιουργούνται τα ZIP backups", lambda e: self._choose_folder(e, "Επίλεξε φάκελο αποθήκευσης"))
        backup_path.insert(0, str(self.manager.default_backup_root))
        exclusions = self._field(body, 8, "Εξαιρέσεις (προαιρετικά)", "π.χ. data/*.csv, tmp, *.log")
        use_gitignore = ctk.CTkCheckBox(body, text="Χρήση κανόνων από το .gitignore"); use_gitignore.select(); use_gitignore.grid(row=10, column=0, pady=(14, 7), sticky="w")
        include_sensitive = ctk.CTkCheckBox(body, text="Συμπερίληψη πιθανών secrets (.env, keys, credentials)"); include_sensitive.grid(row=11, column=0, pady=7, sticky="w")
        def save() -> None:
            try:
                patterns = [x.strip() for x in exclusions.get().replace(";", ",").split(",") if x.strip()]
                project = self.manager.add_project(name.get(), path.get(), language.get(), custom_excludes=patterns,
                    use_gitignore=bool(use_gitignore.get()), include_sensitive=bool(include_sensitive.get()), backup_root=backup_path.get())
                dialog.destroy(); self.select_project(project)
            except Exception as exc: messagebox.showerror("Δεν ήταν δυνατή η προσθήκη", str(exc), parent=dialog)
        ctk.CTkButton(body, text="Προσθήκη project", height=43, command=save).grid(row=12, column=0, pady=(18, 4), sticky="ew")
        dialog.bind("<Return>", lambda _event: save())

    @staticmethod
    def _choose_source(path_entry, name_entry) -> None:
        selected = filedialog.askdirectory(title="Επίλεξε φάκελο project")
        if selected:
            path_entry.delete(0, "end"); path_entry.insert(0, selected)
            if not name_entry.get(): name_entry.insert(0, Path(selected).name)

    @staticmethod
    def _choose_folder(path_entry, title: str) -> None:
        selected = filedialog.askdirectory(title=title)
        if selected: path_entry.delete(0, "end"); path_entry.insert(0, selected)

    def open_rules_dialog(self) -> None:
        if not self.selected_project: return
        project = self.selected_project
        dialog, body = self._dialog("Ρυθμίσεις backup", f"Κανόνες για το {project.name}", "640x530")
        backup_path = self._path_field(body, 0, "Φάκελος αποθήκευσης", "Φάκελος νέων backups", lambda e: self._choose_folder(e, "Επίλεξε φάκελο αποθήκευσης")); backup_path.insert(0, project.backup_dir)
        ctk.CTkLabel(body, text="Η αλλαγή ισχύει μόνο για νέα backups.", text_color=MUTED).grid(row=2, column=0, pady=(5, 4), sticky="w")
        exclusions = self._field(body, 3, "Εξαιρέσεις", "π.χ. .venv, node_modules, *.log")
        if project.custom_excludes: exclusions.insert(0, ", ".join(project.custom_excludes))
        use_gitignore = ctk.CTkCheckBox(body, text="Χρήση κανόνων από το .gitignore"); use_gitignore.grid(row=5, column=0, pady=(15, 7), sticky="w")
        if project.use_gitignore: use_gitignore.select()
        include_sensitive = ctk.CTkCheckBox(body, text="Συμπερίληψη πιθανών secrets (.env, keys, credentials)"); include_sensitive.grid(row=6, column=0, pady=7, sticky="w")
        if project.include_sensitive: include_sensitive.select()
        def save() -> None:
            try:
                patterns = [x.strip() for x in exclusions.get().replace(";", ",").split(",") if x.strip()]
                self.selected_project = self.manager.update_project_rules(project.id, patterns, bool(use_gitignore.get()), bool(include_sensitive.get()), backup_path.get())
                dialog.destroy(); self.refresh_projects(); self.info_label.configure(text=f"Πηγή: {self.selected_project.path}\nΑποθήκευση: {self.selected_project.backup_dir}"); self.status_label.configure(text="✓ Οι ρυθμίσεις αποθηκεύτηκαν")
            except Exception as exc: messagebox.showerror("Δεν αποθηκεύτηκαν οι ρυθμίσεις", str(exc), parent=dialog)
        ctk.CTkButton(body, text="Αποθήκευση ρυθμίσεων", height=42, command=save).grid(row=7, column=0, pady=(19, 0), sticky="ew")

    def remove_selected_project(self) -> None:
        if not self.selected_project: return
        project = self.selected_project; count = len(self.manager.list_versions(project.id))
        if not messagebox.askyesno("Αφαίρεση project", f"Να αφαιρεθεί το «{project.name}» και το ιστορικό {count} εκδόσεων από τη λίστα;\n\nΤα ZIP δεν θα διαγραφούν και θα παραμείνουν στο:\n{project.backup_dir}", parent=self): return
        self.manager.remove_project(project.id); self.selected_project = None; self.refresh_projects(); self._clear(self.version_list)
        self.eyebrow_label.configure(text="ΕΠΙΛΕΞΕ PROJECT"); self.title_label.configure(text="Τα backups σου, οργανωμένα")
        self.info_label.configure(text="Το project αφαιρέθηκε από τη λίστα. Τα ZIP διατηρήθηκαν.")
        for label in (self.version_count_label, self.last_backup_label, self.storage_label): label.configure(text="—")
        self.backup_button.configure(state="disabled"); self.rules_button.configure(state="disabled"); self.remove_button.configure(state="disabled")

    def start_backup(self) -> None:
        if not self.selected_project: return
        project_id, note = self.selected_project.id, self.note_entry.get().strip()
        if not note:
            messagebox.showwarning("Χρειάζεται όνομα έκδοσης", "Δώσε ένα σύντομο, αναγνωρίσιμο όνομα για το νέο backup.", parent=self); self.note_entry.focus_set(); return
        try: plan = self.manager.build_plan(project_id)
        except Exception as exc: messagebox.showerror("Αποτυχία προεπισκόπησης", str(exc), parent=self); return
        if not self._confirm_plan(plan): return
        self.backup_button.configure(state="disabled", text="Δημιουργία…"); self.note_entry.configure(state="disabled")
        self.status_label.configure(text="●  Το backup δημιουργείται τοπικά…", text_color=ACCENT)
        def work() -> None:
            try: self.manager.create_backup(project_id, note, plan); self.after(0, lambda: self._backup_finished(None))
            except Exception as exc: self.after(0, lambda error=exc: self._backup_finished(error))
        threading.Thread(target=work, daemon=True).start()

    def _confirm_plan(self, plan: BackupPlan) -> bool:
        if not plan.included: messagebox.showwarning("Κενό backup", "Δεν βρέθηκαν αρχεία για backup.", parent=self); return False
        lines = [f"{len(plan.included)} αρχεία  •  {self.manager.format_size(plan.total_size)}", f"{len(plan.excluded)} αρχεία θα εξαιρεθούν"]
        if plan.sensitive:
            action = "θα συμπεριληφθούν" if self.selected_project and self.selected_project.include_sensitive else "θα εξαιρεθούν"
            lines += [f"\nΠιθανά secrets ({action}):", *[f"  • {p}" for p in plan.sensitive[:6]]]
        if plan.large: lines += ["\nΜεγάλα αρχεία (≥100 MB):", *[f"  • {p}" for p in plan.large[:6]]]
        lines.append("\nΝα δημιουργηθεί αυτό το backup;")
        return messagebox.askyesno("Έλεγχος πριν τη δημιουργία", "\n".join(lines), parent=self)

    def _backup_finished(self, error: Exception | None) -> None:
        self.backup_button.configure(state="normal", text="Δημιουργία backup"); self.note_entry.configure(state="normal")
        if error:
            self.status_label.configure(text="✕  Το backup απέτυχε", text_color=(DANGER, "#FCA5A5")); messagebox.showerror("Αποτυχία backup", str(error), parent=self); return
        self.note_entry.delete(0, "end"); self.status_label.configure(text="✓  Το backup ολοκληρώθηκε επιτυχώς", text_color=("#15803D", "#86EFAC")); self.refresh_versions()

    def restore_version(self, version: Version) -> None:
        destination = filedialog.askdirectory(title="Επίλεξε φάκελο επαναφοράς")
        if not destination: return
        target = Path(destination).resolve(); is_live = bool(self.selected_project and target == Path(self.selected_project.path).resolve())
        if any(target.iterdir()):
            warning = "Ο φάκελος δεν είναι κενός. Αρχεία με το ίδιο όνομα μπορεί να αντικατασταθούν."
            if is_live: warning += "\n\nΘα δημιουργηθεί πρώτα αυτόματο backup της τρέχουσας κατάστασης."
            if not messagebox.askyesno("Επιβεβαίωση επαναφοράς", warning + "\n\nΣυνέχεια;", parent=self): return
        try:
            restored, safety = self.manager.restore_with_safety_backup(version.id, destination)
            if safety: self.refresh_versions()
            extra = "\n\nΔημιουργήθηκε πρώτα safety backup της προηγούμενης κατάστασης." if safety else ""
            self.status_label.configure(text="✓  Η επαναφορά ολοκληρώθηκε", text_color=("#15803D", "#86EFAC"))
            messagebox.showinfo("Η επαναφορά ολοκληρώθηκε", f"Η έκδοση επανήλθε στο:\n{restored}{extra}", parent=self)
        except Exception as exc: messagebox.showerror("Αποτυχία επαναφοράς", str(exc), parent=self)
