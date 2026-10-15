"""Local storage and snapshot operations for Dev Project Backup."""

from __future__ import annotations

import json
import re
import uuid
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import pathspec

from app_paths import get_data_dir, get_default_backup_root


LANGUAGES = (
    "Python", "JavaScript / TypeScript", "Java", "C#", "C / C++",
    "Go", "Rust", "PHP", "Ruby", "Other",
)

COMMON_IGNORES = {".git", ".idea", ".vscode", ".DS_Store", "Thumbs.db"}
SENSITIVE_PATTERNS = {
    ".env", ".env.*", "*.pem", "*.key", "id_rsa", "id_ed25519",
    "credentials.json", "service-account.json",
}
SAFE_ENV_EXAMPLES = {".env.example", ".env.sample", ".env.template"}
LARGE_FILE_SIZE = 100 * 1024 * 1024
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
LANGUAGE_IGNORES = {
    "Python": {".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", "*.pyc"},
    "JavaScript / TypeScript": {"node_modules", ".next", "dist", "coverage"},
    "Java": {"target", ".gradle", "build", "*.class"},
    "C#": {"bin", "obj", ".vs"},
    "C / C++": {"build", "cmake-build-*", "*.o", "*.obj"},
    "Go": {"vendor", "bin"},
    "Rust": {"target"},
    "PHP": {"vendor"},
    "Ruby": {"vendor", ".bundle"},
    "Other": set(),
}


@dataclass(slots=True)
class Project:
    id: str
    name: str
    path: str
    language: str
    created_at: str
    custom_excludes: list[str] | None = None
    use_gitignore: bool = True
    include_sensitive: bool = False
    backup_dir: str = ""


@dataclass(slots=True)
class Version:
    id: str
    project_id: str
    created_at: str
    note: str
    archive: str
    size: int


@dataclass(slots=True)
class BackupPlan:
    included: list[Path]
    excluded: list[Path]
    sensitive: list[Path]
    large: list[Path]
    total_size: int


class BackupManager:
    """Persists the catalogue and ZIP snapshots entirely on the local machine."""

    def __init__(self, data_dir: Path | None = None) -> None:
        # An explicit path keeps tests isolated; normal app runs use app_paths.
        explicit_data_dir = data_dir is not None
        self.data_dir = Path(data_dir) if explicit_data_dir else get_data_dir()
        self.archives_dir = self.data_dir / "archives"
        self.default_backup_root = self.archives_dir if explicit_data_dir else get_default_backup_root()
        self.catalogue_path = self.data_dir / "catalogue.json"
        self.archives_dir.mkdir(parents=True, exist_ok=True)
        if not self.catalogue_path.exists():
            self._write_catalogue({"projects": [], "versions": []})

    def _read_catalogue(self) -> dict:
        try:
            data = json.loads(self.catalogue_path.read_text(encoding="utf-8"))
            data.setdefault("projects", [])
            data.setdefault("versions", [])
            return data
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError("Το αρχείο καταλόγου backup δεν μπορεί να διαβαστεί.") from exc

    def _write_catalogue(self, data: dict) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.catalogue_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.catalogue_path)

    def list_projects(self) -> list[Project]:
        projects = []
        for item in self._read_catalogue()["projects"]:
            # Defaults keep catalogues created by earlier app versions compatible.
            normalized = {
                "custom_excludes": [],
                "use_gitignore": True,
                "include_sensitive": False,
                "backup_dir": str(self.archives_dir / item["id"]),
                **item,
            }
            projects.append(Project(**normalized))
        return projects

    def add_project(
        self,
        name: str,
        path: str,
        language: str,
        custom_excludes: list[str] | None = None,
        use_gitignore: bool = True,
        include_sensitive: bool = False,
        backup_root: str | None = None,
    ) -> Project:
        source = Path(path).expanduser().resolve()
        if not source.is_dir():
            raise ValueError("Επίλεξε έναν υπαρκτό φάκελο project.")
        if language not in LANGUAGES:
            raise ValueError("Η γλώσσα προγραμματισμού δεν υποστηρίζεται.")
        name = name.strip() or source.name
        catalogue = self._read_catalogue()
        if any(Path(item["path"]) == source for item in catalogue["projects"]):
            raise ValueError("Το project έχει ήδη προστεθεί.")
        project_id = uuid.uuid4().hex
        root = Path(backup_root).expanduser().resolve() if backup_root else self.default_backup_root.resolve()
        project_backup_dir = self._validate_backup_dir(source, root)
        project = Project(
            project_id,
            name,
            str(source),
            language,
            datetime.now().isoformat(timespec="seconds"),
            [pattern.strip() for pattern in (custom_excludes or []) if pattern.strip()],
            use_gitignore,
            include_sensitive,
            str(project_backup_dir),
        )
        catalogue["projects"].append(asdict(project))
        self._write_catalogue(catalogue)
        return project

    def remove_project(self, project_id: str) -> None:
        """Remove a catalogue entry, retaining its archives as a safety measure."""
        catalogue = self._read_catalogue()
        catalogue["projects"] = [p for p in catalogue["projects"] if p["id"] != project_id]
        catalogue["versions"] = [v for v in catalogue["versions"] if v["project_id"] != project_id]
        self._write_catalogue(catalogue)

    def update_project_rules(
        self,
        project_id: str,
        custom_excludes: list[str],
        use_gitignore: bool,
        include_sensitive: bool,
        backup_dir: str | None = None,
    ) -> Project:
        catalogue = self._read_catalogue()
        item = next((p for p in catalogue["projects"] if p["id"] == project_id), None)
        if item is None:
            raise ValueError("Το project δεν βρέθηκε.")
        item["custom_excludes"] = [pattern.strip() for pattern in custom_excludes if pattern.strip()]
        item["use_gitignore"] = use_gitignore
        item["include_sensitive"] = include_sensitive
        if backup_dir is not None:
            source = Path(item["path"]).expanduser().resolve()
            item["backup_dir"] = str(self._validate_backup_dir(source, Path(backup_dir).expanduser().resolve()))
        self._write_catalogue(catalogue)
        return self._project(project_id)

    @staticmethod
    def _validate_backup_dir(source: Path, backup_dir: Path) -> Path:
        """Ensure archives cannot become part of the source tree recursively."""
        source = source.resolve()
        backup_dir = backup_dir.resolve()
        if backup_dir == source or source in backup_dir.parents:
            raise ValueError("Ο φάκελος backup δεν επιτρέπεται να βρίσκεται μέσα στο project.")
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ValueError(f"Ο φάκελος backup δεν μπορεί να δημιουργηθεί: {backup_dir}") from exc
        return backup_dir

    def list_versions(self, project_id: str) -> list[Version]:
        versions = [Version(**v) for v in self._read_catalogue()["versions"] if v["project_id"] == project_id]
        return sorted(versions, key=lambda item: item.created_at, reverse=True)

    def _project(self, project_id: str) -> Project:
        project = next((p for p in self.list_projects() if p.id == project_id), None)
        if project is None:
            raise ValueError("Το project δεν βρέθηκε.")
        return project

    @staticmethod
    def _matches(name: str, patterns: set[str]) -> bool:
        return any(Path(name).match(pattern) for pattern in patterns)

    @staticmethod
    def _is_sensitive(relative: Path) -> bool:
        if relative.name.casefold() in SAFE_ENV_EXAMPLES:
            return False
        return any(relative.match(pattern) or relative.name == pattern for pattern in SENSITIVE_PATTERNS)

    @staticmethod
    def _safe_archive_stem(version_name: str, fallback: str) -> str:
        """Turn a user-visible version name into a portable ZIP filename."""
        stem = version_name.strip()
        if stem.casefold().endswith(".zip"):
            stem = stem[:-4]
        stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem).strip().rstrip(". ")
        stem = stem[:120].rstrip(". ")
        if not stem:
            stem = fallback
        if stem.upper() in WINDOWS_RESERVED_NAMES:
            stem = f"_{stem}"
        return stem

    @staticmethod
    def _available_archive_path(directory: Path, stem: str) -> Path:
        candidate = directory / f"{stem}.zip"
        suffix = 2
        while candidate.exists():
            candidate = directory / f"{stem}_{suffix}.zip"
            suffix += 1
        return candidate

    def build_plan(self, project_id: str) -> BackupPlan:
        """Classify project files before a snapshot is created."""
        project = self._project(project_id)
        source = Path(project.path)
        if not source.is_dir():
            raise FileNotFoundError(f"Ο φάκελος δεν υπάρχει πλέον: {source}")

        ignores = COMMON_IGNORES | LANGUAGE_IGNORES.get(project.language, set())
        custom = set(project.custom_excludes or [])
        git_spec = None
        gitignore = source / ".gitignore"
        if project.use_gitignore and gitignore.is_file():
            try:
                lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
                git_spec = pathspec.GitIgnoreSpec.from_lines(lines)
            except OSError:
                git_spec = None

        included: list[Path] = []
        excluded: list[Path] = []
        sensitive: list[Path] = []
        large: list[Path] = []
        total_size = 0
        for path in source.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(source)
            posix = relative.as_posix()
            built_in_match = any(self._matches(part, ignores) for part in relative.parts)
            custom_match = any(relative.match(pattern) or any(Path(part).match(pattern) for part in relative.parts) for pattern in custom)
            git_match = bool(git_spec and git_spec.match_file(posix))
            secret = self._is_sensitive(relative)
            if secret:
                sensitive.append(relative)
            if built_in_match or custom_match or git_match or (secret and not project.include_sensitive):
                excluded.append(relative)
                continue
            included.append(path)
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            total_size += size
            if size >= LARGE_FILE_SIZE:
                large.append(relative)
        return BackupPlan(included, excluded, sensitive, large, total_size)

    def create_backup(self, project_id: str, note: str = "", plan: BackupPlan | None = None) -> Version:
        project = self._project(project_id)
        source = Path(project.path)
        if not source.is_dir():
            raise FileNotFoundError(f"Ο φάκελος δεν υπάρχει πλέον: {source}")

        version_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        project_dir = self._validate_backup_dir(source, Path(project.backup_dir))
        project_dir.mkdir(parents=True, exist_ok=True)
        archive_stem = self._safe_archive_stem(note, version_id)
        archive = self._available_archive_path(project_dir, archive_stem)
        plan = plan or self.build_plan(project_id)

        try:
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zipped:
                for path in plan.included:
                    relative = path.relative_to(source)
                    zipped.write(path, relative)
        except Exception:
            archive.unlink(missing_ok=True)
            raise

        version = Version(version_id, project.id, datetime.now().isoformat(timespec="seconds"), note.strip(), str(archive), archive.stat().st_size)
        catalogue = self._read_catalogue()
        catalogue["versions"].append(asdict(version))
        self._write_catalogue(catalogue)
        return version

    def restore(self, version_id: str, destination: str, progress: Callable[[str], None] | None = None) -> Path:
        catalogue = self._read_catalogue()
        item = next((v for v in catalogue["versions"] if v["id"] == version_id), None)
        if item is None:
            raise ValueError("Η έκδοση δεν βρέθηκε.")
        archive = Path(item["archive"])
        if not archive.is_file():
            raise FileNotFoundError("Το αρχείο αυτής της έκδοσης λείπει.")
        target = Path(destination).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zipped:
            root = target.resolve()
            for member in zipped.infolist():
                member_target = (target / member.filename).resolve()
                if root != member_target and root not in member_target.parents:
                    raise ValueError("Το backup περιέχει μη ασφαλή διαδρομή.")
                if progress:
                    progress(member.filename)
            zipped.extractall(target)
        return target

    def restore_with_safety_backup(self, version_id: str, destination: str) -> tuple[Path, Version | None]:
        """Create a safety snapshot before restoring over the live project folder."""
        catalogue = self._read_catalogue()
        item = next((v for v in catalogue["versions"] if v["id"] == version_id), None)
        if item is None:
            raise ValueError("Η έκδοση δεν βρέθηκε.")
        project = self._project(item["project_id"])
        target = Path(destination).expanduser().resolve()
        source = Path(project.path).expanduser().resolve()
        safety_version = None
        if target == source:
            restored_date = datetime.fromisoformat(item["created_at"]).strftime("%d/%m/%Y %H:%M")
            safety_version = self.create_backup(
                project.id,
                f"Αυτόματο backup πριν από επαναφορά της έκδοσης {restored_date}",
            )
        restored = self.restore(version_id, str(target))
        return restored, safety_version

    @staticmethod
    def format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} GB"
