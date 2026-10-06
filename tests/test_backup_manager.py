from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

import backup_manager as backup_module
from backup_manager import BackupManager


@pytest.fixture
def manager(tmp_path: Path) -> BackupManager:
    return BackupManager(tmp_path / "data")


@pytest.fixture
def source(tmp_path: Path) -> Path:
    project = tmp_path / "sample-project"
    project.mkdir()
    return project


def add_python_project(
    manager: BackupManager,
    source: Path,
    **kwargs: object,
):
    return manager.add_project("", str(source), "Python", **kwargs)


def relative_paths(paths: list[Path], source: Path | None = None) -> set[str]:
    if source is None:
        return {path.as_posix() for path in paths}
    return {path.relative_to(source).as_posix() for path in paths}


def test_add_project_is_persisted_and_normalized(manager: BackupManager, source: Path) -> None:
    project = add_python_project(
        manager,
        source,
        custom_excludes=[" *.log ", "", "tmp"],
        use_gitignore=False,
    )

    assert project.name == source.name
    assert project.custom_excludes == ["*.log", "tmp"]
    assert project.use_gitignore is False

    reloaded = BackupManager(manager.data_dir).list_projects()
    assert reloaded == [project]


@pytest.mark.parametrize(
    ("path_kind", "language", "message"),
    [
        ("missing", "Python", "υπαρκτό φάκελο"),
        ("existing", "COBOL", "δεν υποστηρίζεται"),
    ],
)
def test_add_project_validates_source_and_language(
    manager: BackupManager,
    source: Path,
    path_kind: str,
    language: str,
    message: str,
) -> None:
    path = source if path_kind == "existing" else source / "missing"
    with pytest.raises(ValueError, match=message):
        manager.add_project("project", str(path), language)


def test_add_project_rejects_duplicate_source(manager: BackupManager, source: Path) -> None:
    add_python_project(manager, source)

    with pytest.raises(ValueError, match="ήδη προστεθεί"):
        add_python_project(manager, source)


@pytest.mark.parametrize("relative_backup", [".", "backups", "nested/backups"])
def test_backup_directory_cannot_be_inside_source(
    manager: BackupManager,
    source: Path,
    relative_backup: str,
) -> None:
    with pytest.raises(ValueError, match="μέσα στο project"):
        add_python_project(manager, source, backup_root=str(source / relative_backup))


def test_build_plan_applies_all_exclusion_rules(
    manager: BackupManager,
    source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = {
        "main.py": b"print('ok')\n",
        "notes.txt": b"keep me",
        "debug.log": b"custom exclusion",
        "generated/cache.dat": b"gitignore exclusion",
        ".venv/config.ini": b"language exclusion",
        "__pycache__/main.pyc": b"compiled",
        ".git/config": b"git metadata",
        ".env": b"TOKEN=secret",
        "credentials.json": b"{}",
        ".env.example": b"TOKEN=example",
        "large.bin": b"12345",
    }
    for name, contents in files.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    (source / ".gitignore").write_text("generated/\n", encoding="utf-8")
    monkeypatch.setattr(backup_module, "LARGE_FILE_SIZE", 5)

    project = add_python_project(manager, source, custom_excludes=["*.log"])
    plan = manager.build_plan(project.id)

    included = relative_paths(plan.included, source)
    excluded = relative_paths(plan.excluded)
    assert {"main.py", "notes.txt", ".env.example", ".gitignore", "large.bin"} <= included
    assert {
        "debug.log",
        "generated/cache.dat",
        ".venv/config.ini",
        "__pycache__/main.pyc",
        ".git/config",
        ".env",
        "credentials.json",
    } <= excluded
    assert relative_paths(plan.sensitive) == {".env", "credentials.json"}
    assert relative_paths(plan.large) == {
        "main.py",
        "notes.txt",
        ".env.example",
        ".gitignore",
        "large.bin",
    }
    assert plan.total_size == sum((source / name).stat().st_size for name in included)


@pytest.mark.parametrize(
    ("include_sensitive", "is_included"),
    [(False, False), (True, True)],
)
def test_sensitive_files_are_reported_and_optionally_included(
    manager: BackupManager,
    source: Path,
    include_sensitive: bool,
    is_included: bool,
) -> None:
    (source / ".env").write_text("SECRET=value", encoding="utf-8")
    project = add_python_project(manager, source, include_sensitive=include_sensitive)

    plan = manager.build_plan(project.id)

    assert relative_paths(plan.sensitive) == {".env"}
    assert (".env" in relative_paths(plan.included, source)) is is_included
    assert (".env" in relative_paths(plan.excluded)) is (not is_included)


def test_create_backup_writes_zip_and_version_metadata(manager: BackupManager, source: Path) -> None:
    (source / "main.py").write_text("print('hello')", encoding="utf-8")
    (source / ".env").write_text("SECRET=value", encoding="utf-8")
    project = add_python_project(manager, source)

    version = manager.create_backup(project.id, "release")
    archive = Path(version.archive)

    assert archive.is_file()
    assert version.size == archive.stat().st_size
    assert manager.list_versions(project.id) == [version]
    with zipfile.ZipFile(archive) as zipped:
        assert set(zipped.namelist()) == {"main.py"}
        assert zipped.read("main.py") == b"print('hello')"


def test_duplicate_backup_names_receive_suffixes(manager: BackupManager, source: Path) -> None:
    (source / "main.py").write_text("pass", encoding="utf-8")
    project = add_python_project(manager, source)

    first = manager.create_backup(project.id, "release")
    second = manager.create_backup(project.id, "release")

    assert Path(first.archive).name == "release.zip"
    assert Path(second.archive).name == "release_2.zip"


@pytest.mark.parametrize(
    ("version_name", "expected"),
    [
        ("release.zip", "release"),
        ("a/b:c", "a_b_c"),
        ("CON", "_CON"),
        ("   ", "fallback"),
        ("name. ", "name"),
    ],
)
def test_safe_archive_stem(version_name: str, expected: str) -> None:
    assert BackupManager._safe_archive_stem(version_name, "fallback") == expected


def test_safe_archive_stem_is_limited_to_120_characters() -> None:
    assert BackupManager._safe_archive_stem("x" * 200, "fallback") == "x" * 120


def test_backup_and_restore_round_trip(manager: BackupManager, source: Path, tmp_path: Path) -> None:
    (source / "nested").mkdir()
    (source / "main.py").write_text("before", encoding="utf-8")
    (source / "nested" / "data.txt").write_bytes(b"\x00\x01payload")
    project = add_python_project(manager, source)
    version = manager.create_backup(project.id, "round-trip")
    (source / "main.py").write_text("after", encoding="utf-8")
    (source / "nested" / "data.txt").unlink()

    destination = tmp_path / "restored"
    restored = manager.restore(version.id, str(destination))

    assert restored == destination.resolve()
    assert (destination / "main.py").read_text(encoding="utf-8") == "before"
    assert (destination / "nested" / "data.txt").read_bytes() == b"\x00\x01payload"


def test_restore_rejects_zip_path_traversal(manager: BackupManager, source: Path, tmp_path: Path) -> None:
    (source / "safe.txt").write_text("safe", encoding="utf-8")
    project = add_python_project(manager, source)
    version = manager.create_backup(project.id, "malicious")
    with zipfile.ZipFile(version.archive, "w") as zipped:
        zipped.writestr("../../outside.txt", "escaped")

    destination = tmp_path / "restore-target"
    outside = tmp_path / "outside.txt"
    with pytest.raises(ValueError, match="μη ασφαλή διαδρομή"):
        manager.restore(version.id, str(destination))
    assert not outside.exists()


def test_restore_over_live_project_creates_safety_backup(manager: BackupManager, source: Path) -> None:
    tracked = source / "state.txt"
    tracked.write_text("archived state", encoding="utf-8")
    project = add_python_project(manager, source)
    version = manager.create_backup(project.id, "original")
    tracked.write_text("current state", encoding="utf-8")

    restored, safety_version = manager.restore_with_safety_backup(version.id, str(source))

    assert restored == source.resolve()
    assert tracked.read_text(encoding="utf-8") == "archived state"
    assert safety_version is not None
    with zipfile.ZipFile(safety_version.archive) as zipped:
        assert zipped.read("state.txt") == b"current state"


def test_restore_to_other_directory_does_not_create_safety_backup(
    manager: BackupManager,
    source: Path,
    tmp_path: Path,
) -> None:
    (source / "state.txt").write_text("archived", encoding="utf-8")
    project = add_python_project(manager, source)
    version = manager.create_backup(project.id, "original")

    _, safety_version = manager.restore_with_safety_backup(version.id, str(tmp_path / "other"))

    assert safety_version is None
    assert len(manager.list_versions(project.id)) == 1


def test_remove_project_removes_catalogue_records_but_keeps_archive(
    manager: BackupManager,
    source: Path,
) -> None:
    (source / "main.py").write_text("pass", encoding="utf-8")
    project = add_python_project(manager, source)
    version = manager.create_backup(project.id, "keep-me")
    archive = Path(version.archive)

    manager.remove_project(project.id)

    assert manager.list_projects() == []
    assert manager.list_versions(project.id) == []
    assert archive.is_file()


def test_corrupt_catalogue_raises_clear_error(manager: BackupManager) -> None:
    manager.catalogue_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(RuntimeError, match="δεν μπορεί να διαβαστεί"):
        manager.list_projects()


def test_old_catalogue_receives_backward_compatible_defaults(manager: BackupManager, source: Path) -> None:
    legacy_project = {
        "id": "legacy-id",
        "name": "legacy",
        "path": str(source.resolve()),
        "language": "Python",
        "created_at": "2026-01-01T12:00:00",
    }
    manager.catalogue_path.write_text(
        json.dumps({"projects": [legacy_project], "versions": []}),
        encoding="utf-8",
    )

    project = manager.list_projects()[0]

    assert project.custom_excludes == []
    assert project.use_gitignore is True
    assert project.include_sensitive is False
    assert project.backup_dir == str(manager.archives_dir / "legacy-id")
