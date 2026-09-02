import os
import uuid
import datetime
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Exact Live Supabase Cloud Database Credentials
SUPABASE_URL = "https://ylkksooegfphkoafndug.supabase.co".strip().rstrip("/")
SUPABASE_KEY = "sb_publishable_4fJni_KB8AyKlrasF5xt3g_rpu379WS".strip()

# Initialize Supabase Client directly
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_product_catalog() -> List[Dict[str, Any]]:
    """
    1. Fetches all records from the 'products' table in Supabase to match standard rates.
    """
    try:
        response = supabase.table("products").select("*").execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching products from Supabase: {e}")
        return []


def save_purchase_order(po_data: Dict[str, Any], items_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    2. Inserts a newly approved purchase order into the 'purchase_orders' table in Supabase,
       and records associated line items in the 'po_items' table.
    """
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
    
    # Insert PO into Supabase purchase_orders table
    try:
        supabase.table("purchase_orders").insert(po_record).execute()
    except Exception as e:
        print(f"Error inserting into purchase_orders table in Supabase: {e}")

    # Insert Line Items into Supabase po_items table
    if items_data:
        items_records = []
        for item in items_data:
            items_records.append({
                "id": str(uuid.uuid4()),
                "po_id": po_id,
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
            print(f"Error inserting line items into po_items table in Supabase: {e}")

    return po_record


def get_order_history() -> List[Dict[str, Any]]:
    """
    3. Queries all past purchase orders sorted by creation date (newest first)
       from the 'purchase_orders' table in Supabase for the manager dashboard.
    """
    try:
        response = supabase.table("purchase_orders").select("*").order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        print(f"Error querying purchase_orders from Supabase: {e}")
        return []


def get_po_items(po_id: str) -> List[Dict[str, Any]]:
    """
    Fetches line items for a specific purchase order from the 'po_items' table in Supabase.
    """
    try:
        response = supabase.table("po_items").select("*").eq("po_id", po_id).execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching po_items from Supabase: {e}")
        return []


def find_matching_product(description: str) -> Optional[Dict[str, Any]]:
    """
    Finds a matching product from the Supabase product catalog by SKU or keywords.
    """
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


# DatabaseManager class wrapper for compatibility
class DatabaseManager:
    def __init__(self, supabase_url: str = SUPABASE_URL, supabase_key: str = SUPABASE_KEY):
        self.url = supabase_url
        self.key = supabase_key
        self.client: Client = create_client(self.url, self.key)
        self.mode = "supabase"

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

save_new_purchase_order = save_purchase_order


def update_po_status(po_id: str, new_status: str) -> bool:
    try:
        supabase.table('purchase_orders').update({'status': new_status}).eq('id', po_id).execute()
        return True
    except Exception as e:
        print(f'Error updating po status: {e}')
        return False

    def update_po_status(self, po_id: str, new_status: str) -> bool:
        return update_po_status(po_id, new_status)

