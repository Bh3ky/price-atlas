from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from tinydb import Query, TinyDB


class Database:
    """
    TinyDB stores its data in a JSON *dict* keyed by table name.

    Important:
    - The TinyDB storage file must NOT be rewritten as a JSON list.
      (Doing so causes: TypeError: list indices must be integers or slices, not str)
    - If you want a human-readable JSON list, export it to a separate file.
    """

    def __init__(
        self,
        db_path: str | os.PathLike[str] | None = None,
        export_path: str | os.PathLike[str] | None = None,
        migrate_from_path: str | os.PathLike[str] | None = None,
        auto_export: bool = True,
    ):
        root = Path(__file__).resolve().parents[1]

        # A dedicated TinyDB storage file (dict-of-tables format).
        default_db_path = root / "tinydb.json"

        # A human-readable export file (list-of-products format).
        default_export_path = root / "data.json"

        raw_db_path = os.getenv("PRICE_ATLAS_DB_PATH") if db_path is None else db_path
        if not raw_db_path:
            raw_db_path = default_db_path
        self.db_path = Path(raw_db_path)
        if not self.db_path.is_absolute():
            self.db_path = root / self.db_path

        raw_export_path = (
            os.getenv("PRICE_ATLAS_EXPORT_PATH") if export_path is None else export_path
        )
        if not raw_export_path:
            raw_export_path = default_export_path
        self.export_path = Path(raw_export_path)
        if not self.export_path.is_absolute():
            self.export_path = root / self.export_path

        self.migrate_from_path = Path(migrate_from_path) if migrate_from_path else self.export_path
        if not self.migrate_from_path.is_absolute():
            self.migrate_from_path = root / self.migrate_from_path

        self.auto_export = bool(auto_export)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.export_path.parent.mkdir(parents=True, exist_ok=True)

        # If the DB file exists but is a list, it's corrupted for TinyDB (often due to
        # someone "prettifying" it). We salvage those records and rebuild the DB file.
        legacy_products: list[dict[str, Any]] = []
        if self.db_path.exists():
            legacy_products = self._maybe_salvage_list_db_file(self.db_path)

        # If the DB file doesn't exist yet, try migrating from migrate_from_path:
        # - If it's a list: import those products into the new DB
        # - If it's a TinyDB dict with "products": copy it over as the DB
        if not self.db_path.exists() and self.migrate_from_path.exists():
            migrate_legacy, copied = self._maybe_migrate_from_file(self.migrate_from_path, self.db_path)
            if migrate_legacy:
                legacy_products.extend(migrate_legacy)
            # If we copied an existing TinyDB DB into db_path, no further action needed.
            # legacy_products stays empty in that case.

        self.db = TinyDB(str(self.db_path))
        self.products = self.db.table("products")

        if legacy_products:
            for p in legacy_products:
                if not isinstance(p, dict):
                    continue
                p.setdefault("created_at", datetime.now().isoformat())
                self.products.insert(p)
            if self.auto_export:
                self.export_products()

    def _maybe_salvage_list_db_file(self, path: Path) -> list[dict[str, Any]]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # If it's unreadable, back it up and let TinyDB recreate.
            self._backup_file(path, suffix="unreadable")
            try:
                path.unlink()
            except Exception:
                pass
            return []

        if isinstance(data, list):
            # Back up the list file and rebuild DB file as proper TinyDB format.
            self._backup_file(path, suffix="list")
            try:
                path.unlink()
            except Exception:
                pass
            # Keep only dict-like records.
            return [x for x in data if isinstance(x, dict)]

        # If it's a dict, assume it's valid TinyDB storage and keep it as-is.
        return []

    def _maybe_migrate_from_file(self, src: Path, dst_db: Path) -> tuple[list[dict[str, Any]], bool]:
        """
        Returns (legacy_products_to_import, copied_tinydb_storage).
        """
        try:
            data = json.loads(src.read_text(encoding="utf-8"))
        except Exception:
            return [], False

        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)], False

        if isinstance(data, dict) and "products" in data and isinstance(data.get("products"), dict):
            # Looks like a TinyDB storage file for the "products" table. Copy it to dst_db.
            dst_db.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return [], True

        return [], False

    def _backup_file(self, path: Path, suffix: str) -> None:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.stem}.backup.{suffix}.{ts}{path.suffix}")
        try:
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            # Best effort; ignore backup failures.
            pass

    def export_products(self, export_path: str | os.PathLike[str] | None = None) -> None:
        """
        Export products as a human-readable JSON list.

        This intentionally writes to export_path (default: self.export_path), NOT the TinyDB db_path.
        """
        out = Path(export_path) if export_path is not None else self.export_path
        if not out.is_absolute():
            out = Path(__file__).resolve().parents[1] / out

        # Guardrail: never export into the TinyDB storage file.
        if out.resolve() == self.db_path.resolve():
            return

        products = self.products.all()
        out.write_text(json.dumps(products, indent=4, ensure_ascii=False), encoding="utf-8")

    def insert_product(self, product_data: dict[str, Any]):
        """Insert a new product record into the database."""
        if not isinstance(product_data, dict):
            raise TypeError("insert_product expects a dict")
        product_data.setdefault("created_at", datetime.now().isoformat())
        inserted_id = self.products.insert(product_data)
        if self.auto_export:
            self.export_products()
        return inserted_id

    def update_product(self, asin, update_data):
        """Update an existing product by ASIN."""
        Product = Query()
        updated = self.products.update(update_data, Product.asin == asin)
        if updated and self.auto_export:
            self.export_products()
        return updated

    def get_product(self, asin):
        """
        Retrieve the most relevant product snapshot for an ASIN.

        Why this matters:
        - We store BOTH target products and competitor snapshots in the same table.
        - Competitor snapshots include `parent_asin`.
        - For most callers (UI + competitor search seed + LLM analysis), if the user
          asks for product X, we want the "base/target" record (no `parent_asin`)
          and we want the *latest* snapshot (by scraped_at / created_at).
        """
        Product = Query()

        # Prefer "base" records (no parent_asin) when available.
        base_records = self.products.search(
            (Product.asin == asin) & (~Product.parent_asin.exists())
        )
        candidates = base_records or self.products.search(Product.asin == asin)
        if not candidates:
            return None

        def _sort_ts(p: dict) -> float:
            ts = p.get("scraped_at")
            if isinstance(ts, (int, float)):
                return float(ts)
            created_at = p.get("created_at")
            if isinstance(created_at, str) and created_at:
                try:
                    return datetime.fromisoformat(created_at).timestamp()
                except Exception:
                    return 0.0
            return 0.0

        return max(candidates, key=_sort_ts)
    
    def get_all_products(self):
        """Get all products in the DB"""
        return self.products.all()
    
    def search_products(self, search_criteria):
        Product = Query()
        query = None
        for key, value in search_criteria.items():
            if query is None:
                query = (Product[key] == value)
            else:
                query &= (Product[key] == value)
        return self.products.search(query) if query else []