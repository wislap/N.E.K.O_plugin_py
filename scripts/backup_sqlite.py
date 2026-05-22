from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


def _sqlite_path_from_database_url(database_url: str) -> Path:
    parsed = urlparse(database_url)
    if not parsed.scheme.startswith("sqlite"):
        raise SystemExit("backup_sqlite.py only supports sqlite DATABASE_URL values")
    if parsed.path in {"", "/"}:
        raise SystemExit(f"cannot resolve sqlite database path from {database_url!r}")
    return Path(unquote(parsed.path))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_sqlite(source: Path, output_dir: Path, keep_plain: bool = False) -> Path:
    if not source.exists():
        raise SystemExit(f"database file not found: {source}")

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    plain_tmp = output_dir / f"plugin_market-{stamp}.db.tmp"
    plain_final = output_dir / f"plugin_market-{stamp}.db"
    gz_tmp = output_dir / f"plugin_market-{stamp}.db.gz.tmp"
    gz_final = output_dir / f"plugin_market-{stamp}.db.gz"

    src_conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    dst_conn = sqlite3.connect(plain_tmp)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    plain_tmp.replace(plain_final)

    with plain_final.open("rb") as raw, gzip.open(gz_tmp, "wb", compresslevel=9) as zipped:
        shutil.copyfileobj(raw, zipped)
    gz_tmp.replace(gz_final)

    checksum = _sha256(gz_final)
    (gz_final.with_suffix(gz_final.suffix + ".sha256")).write_text(
        f"{checksum}  {gz_final.name}\n",
        encoding="utf-8",
    )

    if not keep_plain:
        plain_final.unlink()

    return gz_final


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an online SQLite backup.")
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="SQLite database path. Defaults to DATABASE_URL.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/backups"),
        help="Directory where backup files are written.",
    )
    parser.add_argument(
        "--keep-plain",
        action="store_true",
        help="Keep the intermediate .db backup next to the compressed copy.",
    )
    args = parser.parse_args()

    source = args.database
    if source is None:
        source = _sqlite_path_from_database_url(os.environ.get("DATABASE_URL", ""))

    backup_path = backup_sqlite(source, args.output_dir, keep_plain=args.keep_plain)
    print(f"backup written: {backup_path}")


if __name__ == "__main__":
    main()
