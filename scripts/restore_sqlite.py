from __future__ import annotations

import argparse
import gzip
import os
import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse


def _sqlite_path_from_database_url(database_url: str) -> Path:
    parsed = urlparse(database_url)
    if not parsed.scheme.startswith("sqlite"):
        raise SystemExit("restore_sqlite.py only supports sqlite DATABASE_URL values")
    if parsed.path in {"", "/"}:
        raise SystemExit(f"cannot resolve sqlite database path from {database_url!r}")
    return Path(unquote(parsed.path))


def restore_sqlite(backup: Path, target: Path, force: bool = False) -> None:
    if not backup.exists():
        raise SystemExit(f"backup file not found: {backup}")
    if target.exists() and not force:
        raise SystemExit(
            f"target already exists: {target}. Stop the app and pass --force to overwrite."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_target = target.with_suffix(target.suffix + ".restore-tmp")

    if backup.suffix == ".gz":
        with gzip.open(backup, "rb") as src, tmp_target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    else:
        shutil.copy2(backup, tmp_target)

    tmp_target.replace(target)

    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(target) + suffix)
        if sidecar.exists():
            sidecar.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore a SQLite backup. Stop backend before running."
    )
    parser.add_argument("backup", type=Path, help="Backup .db or .db.gz path")
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="SQLite database path. Defaults to DATABASE_URL.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite target DB")
    args = parser.parse_args()

    target = args.database
    if target is None:
        target = _sqlite_path_from_database_url(os.environ.get("DATABASE_URL", ""))

    restore_sqlite(args.backup, target, force=args.force)
    print(f"restored {args.backup} -> {target}")


if __name__ == "__main__":
    main()
