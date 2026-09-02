import os
import uuid
import datetime
import sqlite3
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Path to local SQLite database fallback
DB_PATH = os.path.join(os.path.dirname(__file__), "orderlens_local.db")

try:
    import streamlit as st
    secret_supa_url = st.secrets.get("SUPABASE_URL", "").replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '') if hasattr(st, "secrets") else ""
    secret_supa_key = st.secrets.get("SUPABASE_KEY", "").replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '') if hasattr(st, "secrets") else ""
except Exception:
    secret_supa_url = ""
    secret_supa_key = ""

# Correct default Supabase credentials
DEFAULT_SUPABASE_URL = "https://ylkksooeqfphkoafndug.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_4fJni_KB8AyKlrasF5xt3g_rpu379WS"

SUPABASE_URL = (os.getenv("SUPABASE_URL") or secret_supa_url or DEFAULT_SUPABASE_URL).strip().rstrip("/")
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or secret_supa_key or DEFAULT_SUPABASE_KEY).replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')

# Initialize Supabase Client directly
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_sqlite_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_tables():
    """Ensure local SQLite tables exist with proper schema."""
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'General Hardware',
            unit_price REAL NOT NULL DEFAULT 0.00,
            stock_quantity INTEGER NOT NULL DEFAULT 0,
            unit TEXT DEFAULT 'pcs'
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id TEXT PRIMARY KEY,
            po_number TEXT UNIQUE NOT NULL,
            vendor_name TEXT NOT NULL,
            vendor_address TEXT,
            vendor_email TEXT,
            vendor_phone TEXT,
            po_date TEXT,
            terms_and_conditions TEXT,
            subtotal REAL DEFAULT 0.00,
            tax_amount REAL DEFAULT 0.00,
            shipping_amount REAL DEFAULT 0.00,
            grand_total REAL DEFAULT 0.00,
            status TEXT DEFAULT 'Approved',
            created_at TEXT
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS po_items (
            id TEXT PRIMARY KEY,
            po_id TEXT,
            product_id TEXT,
            description TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            unit_price REAL DEFAULT 0.00,
            catalog_rate REAL DEFAULT 0.00,
            total_price REAL DEFAULT 0.00
        );
    """)
    conn.commit()
    conn.close()

# Ensure local tables exist
try:
    init_sqlite_tables()
except Exception as e:
    print(f"Error initializing SQLite local tables: {e}")


def get_product_catalog() -> List[Dict[str, Any]]:
    """Fetches all product records from Supabase, falling back to local SQLite if unavailable."""
    try:
        response = supabase.table("products").select("*").execute()
        if response.data:
            return response.data
    except Exception as e:
        print(f"Supabase products fetch failed: {e}. Falling back to SQLite local database.")
    
    # SQLite Fallback
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as sq_err:
        print(f"SQLite products fetch error: {sq_err}")
        return []


def save_purchase_order(po_data: Dict[str, Any], items_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Inserts purchase order into Supabase, falling back to SQLite on error."""
    po_id = str(uuid.uuid4())
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    po_record = {
        "id": po_id,
        "po_number": po_data.get("po_number", f"PO-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}"),
        "vendor_name": po_data.get("vendor_name", "Vendor Name"),
        "vendor_address": po_data.get("vendor_address", ""),
        "vendor_email": po_data.get("vendor_email", ""),
        "vendor_phone": po_data.get("vendor_phone", ""),
        "po_date": str(po_data.get("po_date", datetime.date.today())),
        "terms_and_conditions": po_data.get("terms_and_conditions", "Standard Payment Terms: Net 30 Days."),
        "subtotal": float(po_data.get("subtotal", 0.0)),
        "tax_amount": float(po_data.get("tax_amount", 0.0)),
        "shipping_amount": float(po_data.get("shipping_amount", 0.0)),
        "grand_total": float(po_data.get("grand_total", 0.0)),
        "status": po_data.get("status", "Approved"),
        "created_at": created_at
    }
    
    saved_to_supa = False
    try:
        supa_res = supabase.table("purchase_orders").insert(po_record).execute()
        if supa_res.data:
            po_record = supa_res.data[0]
            saved_to_supa = True
    except Exception as e:
        print(f"Supabase insert error: {e}. Saving to SQLite local database.")

    if items_data and saved_to_supa:
        items_records = []
        for item in items_data:
            items_records.append({
                "id": str(uuid.uuid4()),
                "po_id": po_record["id"],
                "product_id": item.get("product_id"),
                "description": item.get("description", ""),
                "quantity": int(item.get("quantity", 1)),
                "unit_price": float(item.get("unit_price", item.get("rate", 0.0))),
                "catalog_rate": float(item.get("catalog_rate", 0.0)),
                "total_price": float(item.get("total_price", item.get("total", 0.0)))
            })
        try:
            supabase.table("po_items").insert(items_records).execute()
        except Exception as e:
            print(f"Supabase line items insert error: {e}")

    # Always persist in SQLite as well for local resilience
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO purchase_orders 
            (id, po_number, vendor_name, vendor_address, vendor_email, vendor_phone, po_date, terms_and_conditions, subtotal, tax_amount, shipping_amount, grand_total, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            po_record["id"], po_record["po_number"], po_record["vendor_name"],
            po_record["vendor_address"], po_record["vendor_email"], po_record["vendor_phone"],
            po_record["po_date"], po_record["terms_and_conditions"], po_record["subtotal"],
            po_record["tax_amount"], po_record["shipping_amount"], po_record["grand_total"],
            po_record["status"], po_record["created_at"]
        ))
        if items_data:
            for item in items_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO po_items (id, po_id, product_id, description, quantity, unit_price, catalog_rate, total_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()), po_record["id"], item.get("product_id"),
                    item.get("description", ""), int(item.get("quantity", 1)),
                    float(item.get("unit_price", item.get("rate", 0.0))),
                    float(item.get("catalog_rate", 0.0)),
                    float(item.get("total_price", item.get("total", 0.0)))
                ))
        conn.commit()
        conn.close()
    except Exception as sq_err:
        print(f"SQLite save purchase order error: {sq_err}")

    return po_record


def get_order_history() -> List[Dict[str, Any]]:
    """Queries purchase orders from Supabase, falling back to local SQLite if unavailable."""
    try:
        response = supabase.table("purchase_orders").select("*").order("created_at", desc=True).execute()
        if response.data is not None and len(response.data) > 0:
            return response.data
    except Exception as e:
        print(f"Supabase order history fetch failed: {e}. Falling back to SQLite local database.")
    
    # SQLite Fallback
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM purchase_orders ORDER BY created_at DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as sq_err:
        print(f"SQLite order history fetch error: {sq_err}")
        return []


def get_po_items(po_id: str) -> List[Dict[str, Any]]:
    """Fetches line items for a specific PO from Supabase, falling back to local SQLite."""
    try:
        response = supabase.table("po_items").select("*").eq("po_id", po_id).execute()
        if response.data is not None:
            return response.data
    except Exception as e:
        print(f"Supabase po_items fetch failed: {e}. Falling back to SQLite.")

    # SQLite Fallback
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM po_items WHERE po_id = ?", (po_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as sq_err:
        print(f"SQLite po_items fetch error: {sq_err}")
        return []


def find_matching_product(description: str) -> Optional[Dict[str, Any]]:
    """Finds a matching product from product catalog by SKU or description keywords."""
    products = get_product_catalog()
    desc_lower = description.lower().strip()
    
    best_match = None
    highest_score = 0
    
    for p in products:
        p_name = p.get("name", "").lower()
        p_sku = p.get("sku", "").lower()
        
        if p_sku and p_sku in desc_lower:
            return p
        if p_name and (p_name in desc_lower or desc_lower in p_name):
            return p
        
        words_desc = set(desc_lower.split())
        words_p = set(p_name.split())
        overlap = len(words_desc.intersection(words_p))
        if overlap > highest_score and overlap >= 2:
            highest_score = overlap
            best_match = p
            
    return best_match


def update_po_status(po_id: str, new_status: str) -> bool:
    """Updates PO status in Supabase and SQLite."""
    success = False
    try:
        supabase.table("purchase_orders").update({"status": new_status}).eq("id", po_id).execute()
        success = True
    except Exception as e:
        print(f"Supabase update status failed: {e}")

    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE purchase_orders SET status = ? WHERE id = ?", (new_status, po_id))
        conn.commit()
        conn.close()
        success = True
    except Exception as sq_err:
        print(f"SQLite update status failed: {sq_err}")

    return success


class SupabaseClientWrapper:
    """Wrapper to make client calls safe against 401/network errors by routing to SQLite fallback."""
    def __init__(self, raw_client: Client):
        self._raw_client = raw_client

    def table(self, table_name: str):
        return TableWrapper(self._raw_client, table_name)


class TableWrapper:
    def __init__(self, raw_client: Client, table_name: str):
        self.raw_client = raw_client
        self.table_name = table_name

    def select(self, *args, **kwargs):
        return QueryWrapper(self.raw_client, self.table_name, "select", args, kwargs)

    def insert(self, payload):
        return QueryWrapper(self.raw_client, self.table_name, "insert", [payload], {})

    def update(self, payload):
        return QueryWrapper(self.raw_client, self.table_name, "update", [payload], {})


class QueryWrapper:
    def __init__(self, raw_client: Client, table_name: str, action: str, args: tuple, kwargs: dict):
        self.raw_client = raw_client
        self.table_name = table_name
        self.action = action
        self.args = args
        self.kwargs = kwargs
        self._order_col = None
        self._order_desc = False
        self._eq_filters = {}

    def order(self, col: str, desc: bool = False):
        self._order_col = col
        self._order_desc = desc
        return self

    def eq(self, col: str, val: Any):
        self._eq_filters[col] = val
        return self

    def execute(self):
        # Try Supabase execution first
        try:
            tbl = self.raw_client.table(self.table_name)
            if self.action == "select":
                q = tbl.select(*self.args, **self.kwargs)
                for k, v in self._eq_filters.items():
                    q = q.eq(k, v)
                if self._order_col:
                    q = q.order(self._order_col, desc=self._order_desc)
                res = q.execute()
                if res.data is not None:
                    class Resp:
                        pass
                    r = Resp()
                    r.data = res.data
                    return r
            elif self.action == "insert":
                res = tbl.insert(*self.args).execute()
                return res
            elif self.action == "update":
                q = tbl.update(*self.args)
                for k, v in self._eq_filters.items():
                    q = q.eq(k, v)
                res = q.execute()
                return res
        except Exception as supa_err:
            print(f"Supabase Query Execution Error ({supa_err}). Routing to local SQLite DB.")

        # Fallback to local SQLite DB
        class Resp:
            pass
        r = Resp()

        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            if self.action == "select":
                sql = f"SELECT * FROM {self.table_name}"
                params = []
                if self._eq_filters:
                    where_clauses = [f"{k} = ?" for k in self._eq_filters.keys()]
                    sql += " WHERE " + " AND ".join(where_clauses)
                    params.extend(self._eq_filters.values())
                if self._order_col:
                    direction = "DESC" if self._order_desc else "ASC"
                    sql += f" ORDER BY {self._order_col} {direction}"
                cursor.execute(sql, params)
                r.data = [dict(row) for row in cursor.fetchall()]
            elif self.action == "insert":
                payload = self.args[0]
                if isinstance(payload, dict):
                    cols = list(payload.keys())
                    placeholders = ", ".join(["?"] * len(cols))
                    sql = f"INSERT OR REPLACE INTO {self.table_name} ({', '.join(cols)}) VALUES ({placeholders})"
                    cursor.execute(sql, list(payload.values()))
                    r.data = [payload]
                elif isinstance(payload, list):
                    for item in payload:
                        cols = list(item.keys())
                        placeholders = ", ".join(["?"] * len(cols))
                        sql = f"INSERT OR REPLACE INTO {self.table_name} ({', '.join(cols)}) VALUES ({placeholders})"
                        cursor.execute(sql, list(item.values()))
                    r.data = payload
                conn.commit()
            elif self.action == "update":
                payload = self.args[0]
                set_clauses = [f"{k} = ?" for k in payload.keys()]
                params = list(payload.values())
                sql = f"UPDATE {self.table_name} SET {', '.join(set_clauses)}"
                if self._eq_filters:
                    where_clauses = [f"{k} = ?" for k in self._eq_filters.keys()]
                    sql += " WHERE " + " AND ".join(where_clauses)
                    params.extend(self._eq_filters.values())
                cursor.execute(sql, params)
                conn.commit()
                r.data = [payload]
            conn.close()
        except Exception as sq_err:
            print(f"SQLite Fallback Execution Error: {sq_err}")
            r.data = []
        return r


# DatabaseManager class wrapper for app compatibility
class DatabaseManager:
    def __init__(self, supabase_url: str = SUPABASE_URL, supabase_key: str = SUPABASE_KEY):
        self.url = supabase_url or SUPABASE_URL
        self.key = supabase_key or SUPABASE_KEY
        try:
            self._raw_client: Client = create_client(self.url, self.key)
        except Exception:
            self._raw_client = supabase
        self.client = SupabaseClientWrapper(self._raw_client)
        self.mode = "hybrid"

    def get_products(self) -> List[Dict[str, Any]]:
        return get_product_catalog()

    def find_matching_product(self, description: str) -> Optional[Dict[str, Any]]:
        return find_matching_product(description)

    def save_purchase_order(self, po_data: Dict[str, Any], items_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return save_purchase_order(po_data, items_data)

    def get_purchase_orders(self) -> List[Dict[str, Any]]:
        return get_order_history()

    def get_po_items(self, po_id: str) -> List[Dict[str, Any]]:
        return get_po_items(po_id)

    def update_po_status(self, po_id: str, new_status: str) -> bool:
        return update_po_status(po_id, new_status)

save_new_purchase_order = save_purchase_order

