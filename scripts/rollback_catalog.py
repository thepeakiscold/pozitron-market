#!/usr/bin/env python3
"""
Rollback Pozitron Market Catalog & Database
Restores pozitron.db, data/products.json, and data/pozitron_data.js
from the pre_authentic_catalog_backup directory.
"""
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BASE_DIR, "backups", "pre_authentic_catalog_backup")

def rollback():
    if not os.path.exists(BACKUP_DIR):
        print(f"Error: Backup directory not found at {BACKUP_DIR}")
        sys.exit(1)

    print("Restoring database and static bundles from backup...")
    files_to_restore = [
        ("pozitron.db", os.path.join(BASE_DIR, "pozitron.db")),
        ("products.json", os.path.join(BASE_DIR, "data", "products.json")),
        ("pozitron_data.js", os.path.join(BASE_DIR, "data", "pozitron_data.js"))
    ]

    for bname, target in files_to_restore:
        src = os.path.join(BACKUP_DIR, bname)
        if os.path.exists(src):
            shutil.copy2(src, target)
            print(f"  Restored {target}")
        else:
            print(f"  Warning: {src} not found in backup")

    print("\nRegenerating pages and feeds...")
    try:
        sys.path.insert(0, BASE_DIR)
        from export_data import export_static_data
        export_static_data()
        print("Pages and feeds re-exported successfully.")
    except Exception as e:
        print(f"Note on re-export: {e}")

    print("\nCatalog successfully rolled back to previous state!")

if __name__ == '__main__':
    rollback()
