#!/usr/bin/env python3
"""
Autonomous Cloud Market Order Processor & Inventory Synchronizer.
Executes 24/7 in cloud CI/CD (GitHub Actions) or locally.
Deducts stock in data/products.json and data/pozitron_data.js,
logs orders, regenerates Merchant feeds, and optionally updates SQLite.
STRICT ZERO EMOJIS in code, logs, and outputs.
"""
import sys
import os
import json
import re
import argparse
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PRODUCTS_JSON_PATH = os.path.join(DATA_DIR, "products.json")
POZITRON_DATA_JS_PATH = os.path.join(DATA_DIR, "pozitron_data.js")
ORDERS_LOG_PATH = os.path.join(DATA_DIR, "orders_log.json")
DB_PATH = os.path.join(PROJECT_ROOT, "pozitron.db")


def load_products_json() -> List[Dict[str, Any]]:
    if not os.path.exists(PRODUCTS_JSON_PATH):
        raise FileNotFoundError(f"Products file not found: {PRODUCTS_JSON_PATH}")
    with open(PRODUCTS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_products_json(products: List[Dict[str, Any]]) -> None:
    temp_path = PRODUCTS_JSON_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, PRODUCTS_JSON_PATH)


def load_pozitron_data_js() -> Dict[str, Any]:
    if not os.path.exists(POZITRON_DATA_JS_PATH):
        return {}
    with open(POZITRON_DATA_JS_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'window\.__POZITRON_DATA__\s*=\s*(\{[\s\S]*\});', content)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return {}


def save_pozitron_data_js(full_data: Dict[str, Any]) -> None:
    temp_path = POZITRON_DATA_JS_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write("// Pozitron Market Static Catalog Bundle for GitHub Pages\n")
        f.write(f"window.__POZITRON_DATA__ = {json.dumps(full_data, ensure_ascii=False)};\n")
        f.write("window.pozitronData = window.__POZITRON_DATA__;\n")
    os.replace(temp_path, POZITRON_DATA_JS_PATH)


def append_order_log(order_summary: Dict[str, Any]) -> None:
    orders = []
    if os.path.exists(ORDERS_LOG_PATH):
        try:
            with open(ORDERS_LOG_PATH, "r", encoding="utf-8") as f:
                orders = json.load(f)
        except Exception:
            orders = []

    # Insert new order at front, keep up to 500 recent orders
    orders.insert(0, order_summary)
    orders = orders[:500]

    temp_path = ORDERS_LOG_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, ORDERS_LOG_PATH)


def parse_order_items(order_data: Dict[str, Any], catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extracts structured items with product id and quantity.
    Handles both structured items_detail and string fallback parsing.
    """
    items_detail = order_data.get("items_detail") or order_data.get("cart") or []
    parsed = []

    if isinstance(items_detail, list) and len(items_detail) > 0:
        for itm in items_detail:
            if not isinstance(itm, dict):
                continue
            prod_id = itm.get("id")
            sku = str(itm.get("sku", "")).strip()
            qty = max(1, int(itm.get("quantity", 1)))
            name = itm.get("name") or itm.get("name_tr") or itm.get("title") or ""
            parsed.append({
                "id": prod_id,
                "sku": sku,
                "name": name,
                "quantity": qty
            })
        return parsed

    # Fallback to parsing items string (e.g. "2x GEPRC Mark5 O3, 1x T-Motor F40")
    items_raw = order_data.get("items", "")
    if isinstance(items_raw, str) and items_raw.strip():
        parts = [p.strip() for p in items_raw.split(",") if p.strip()]
        for part in parts:
            m = re.match(r"^(\d+)\s*x\s*(.+)$", part, re.IGNORECASE)
            if m:
                qty = max(1, int(m.group(1)))
                prod_name = m.group(2).strip()
            else:
                qty = 1
                prod_name = part

            matched_id = None
            matched_sku = ""
            for p in catalog:
                p_name_tr = p.get("name_tr", "").lower()
                p_name_en = p.get("name_en", "").lower()
                target = prod_name.lower()
                if target in p_name_tr or target in p_name_en or p_name_tr in target:
                    matched_id = p.get("id")
                    matched_sku = p.get("sku", "")
                    break

            parsed.append({
                "id": matched_id,
                "sku": matched_sku,
                "name": prod_name,
                "quantity": qty
            })

    return parsed


def process_order(order_data: Dict[str, Any], catalog: Optional[List[Dict[str, Any]]] = None, sync_db: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """
    Main processing function:
    Deducts stock in products.json and pozitron_data.js.
    """
    products = catalog if catalog is not None else load_products_json()
    items_to_deduct = parse_order_items(order_data, products)

    if not items_to_deduct:
        return {
            "status": "warning",
            "message": "No valid order items found to deduct.",
            "order_number": order_data.get("order_number", "UNKNOWN"),
            "items_deducted": []
        }

    deducted_records = []
    prod_map = {str(p.get("id")): p for p in products if "id" in p}
    sku_map = {str(p.get("sku", "")).upper(): p for p in products if p.get("sku")}

    for item in items_to_deduct:
        prod = None
        item_id_str = str(item.get("id")) if item.get("id") is not None else None
        item_sku = str(item.get("sku", "")).upper()

        if item_id_str and item_id_str in prod_map:
            prod = prod_map[item_id_str]
        elif item_sku and item_sku in sku_map:
            prod = sku_map[item_sku]
        else:
            # Name matching fallback
            name_lower = str(item.get("name", "")).lower().strip()
            if name_lower:
                for p in products:
                    if name_lower in p.get("name_tr", "").lower() or name_lower in p.get("name_en", "").lower():
                        prod = p
                        break

        if not prod:
            deducted_records.append({
                "item": item,
                "matched": False,
                "stock_before": None,
                "stock_after": None,
                "note": "Product not found in catalog"
            })
            continue

        old_stock = int(prod.get("stock", 0))
        qty = int(item.get("quantity", 1))
        new_stock = max(0, old_stock - qty)
        prod["stock"] = new_stock
        prod["in_stock"] = new_stock > 0

        deducted_records.append({
            "id": prod.get("id"),
            "sku": prod.get("sku"),
            "name": prod.get("name_tr"),
            "matched": True,
            "deducted_quantity": qty,
            "stock_before": old_stock,
            "stock_after": new_stock
        })

    if not dry_run:
        # 1. Update data/products.json
        save_products_json(products)

        # 2. Update data/pozitron_data.js
        poz_data = load_pozitron_data_js()
        if poz_data and "products" in poz_data:
            poz_data["products"] = products
            save_pozitron_data_js(poz_data)

        # 3. Append to orders_log.json
        order_num = order_data.get("order_number") or f"PZT-ORD-{int(datetime.now().timestamp())}"
        summary = {
            "order_number": order_num,
            "created_at": order_data.get("created_at") or datetime.now().isoformat(),
            "customer_name": order_data.get("name") or order_data.get("customer_name") or "Misafir Musteri",
            "total_try": order_data.get("total_try", "0.00"),
            "total_usd": order_data.get("total_usd", "0.00"),
            "payment_method": order_data.get("card_brand") or order_data.get("payment_method") or "Kredi Karti",
            "transaction_id": order_data.get("transaction_id", ""),
            "items_deducted": deducted_records
        }
        append_order_log(summary)

        # 4. Optional SQLite database sync (when executed locally or in local service)
        if sync_db and os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH, timeout=20.0)
                cursor = conn.cursor()
                for d in deducted_records:
                    if d.get("matched") and d.get("id") is not None:
                        cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (d["stock_after"], d["id"]))

                # Also insert order record into orders table if not present
                cursor.execute("SELECT id FROM orders WHERE order_number = ?", (order_num,))
                if not cursor.fetchone():
                    now_iso = datetime.now().isoformat()
                    cursor.execute('''
                        INSERT INTO orders (
                            id, order_number, customer_name, customer_email,
                            customer_phone, shipping_address, city, country,
                            items_json, subtotal_usd, subtotal_try, total_usd,
                            total_try, currency, payment_method, payment_status,
                            order_status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        order_num,
                        order_num,
                        order_data.get("name") or order_data.get("customer_name", "Misafir Musteri"),
                        order_data.get("email") or order_data.get("customer_email", "siparis@pozitronmarket.com"),
                        order_data.get("phone") or order_data.get("customer_phone", ""),
                        order_data.get("shipping_address", "Adres girilmedi"),
                        order_data.get("city", "Istanbul"),
                        order_data.get("country", "Turkiye"),
                        json.dumps(items_to_deduct, ensure_ascii=False),
                        float(order_data.get("total_usd", 0.0) or 0.0),
                        float(order_data.get("total_try", 0.0) or 0.0),
                        float(order_data.get("total_usd", 0.0) or 0.0),
                        float(order_data.get("total_try", 0.0) or 0.0),
                        order_data.get("currency", "TRY"),
                        order_data.get("payment_method", "credit_card"),
                        "COMPLETED",
                        "PROCESSING",
                        now_iso
                    ))
                conn.commit()
                conn.close()
            except Exception as dbe:
                print(f"[CloudMarketSync] SQLite sync notice: {dbe}", file=sys.stderr)

        # 5. Regenerate Merchant Feeds
        try:
            feed_script = os.path.join(PROJECT_ROOT, "generate_google_feed.py")
            if os.path.exists(feed_script):
                from generate_google_feed import generate_feeds
                generate_feeds()
        except Exception as fe:
            print(f"[CloudMarketSync] Feed generation notice: {fe}", file=sys.stderr)

    return {
        "status": "success",
        "order_number": order_data.get("order_number", "UNKNOWN"),
        "dry_run": dry_run,
        "items_deducted": deducted_records,
        "products_updated_count": sum(1 for d in deducted_records if d.get("matched"))
    }


def main():
    parser = argparse.ArgumentParser(description="Autonomous Cloud Market Order Stock Deductor")
    parser.add_argument("--order-json", type=str, help="JSON string of order")
    parser.add_argument("--order-file", type=str, help="Path to JSON file containing order")
    parser.add_argument("--stdin", action="store_true", help="Read JSON order from stdin")
    parser.add_argument("--sync-db", action="store_true", help="Also sync stock to local SQLite database if present")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying files")

    args = parser.parse_args()

    raw_json = None
    if args.order_json:
        raw_json = args.order_json
    elif args.order_file and os.path.exists(args.order_file):
        with open(args.order_file, "r", encoding="utf-8") as f:
            raw_json = f.read()
    elif args.stdin or not sys.stdin.isatty():
        raw_json = sys.stdin.read()

    if not raw_json or not raw_json.strip():
        print(json.dumps({"error": "No order data provided. Pass --order-json or pipe JSON to stdin."}))
        sys.exit(1)

    try:
        order_data = json.loads(raw_json)
        # Handle GitHub Actions repository_dispatch client_payload wrapping
        if "order" in order_data and isinstance(order_data["order"], dict):
            order_data = order_data["order"]
    except Exception as e:
        print(json.dumps({"error": f"Invalid JSON provided: {str(e)}"}))
        sys.exit(1)

    result = process_order(order_data, sync_db=args.sync_db, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
