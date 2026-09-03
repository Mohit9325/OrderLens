import os
import json
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Fetch Gemini API Key
try:
    import streamlit as st
    secret_key = st.secrets.get("GEMINI_API_KEY", "").replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')
except Exception:
    secret_key = ""

GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '') or secret_key
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1beta'})

# Pydantic Schema for Structured JSON Extraction
class LineItem(BaseModel):
    description: str = Field(description="Product or service line item description")
    quantity: float = Field(default=1.0, description="Quantity ordered")
    rate: float = Field(default=0.0, description="Unit price / rate quoted per single unit")

class ExtractedQuote(BaseModel):
    vendor_name: str = Field(default="", description="Official vendor/supplier company name")
    address: str = Field(default="", description="Vendor physical or mailing address")
    email: str = Field(default="", description="Vendor contact email address")
    phone: str = Field(default="", description="Vendor phone or mobile number")
    terms_and_conditions: str = Field(default="", description="Payment terms, delivery timeline, or warranty conditions")
    po_number_suggestion: str = Field(default="", description="Quotation number or suggested PO number")
    line_items: List[LineItem] = Field(default_factory=list, description="Array of extracted line items")

EXTRACTION_SYSTEM_PROMPT = """
You are an expert AI procurement specialist and document auditor for OrderLens.
Your task is to analyze the provided vendor quote or Bill of Quantities (BQ) document (PDF or image) and extract clean, structured information.

Strict Extraction Instructions:
1. vendor_name: Official name of the supplier/vendor.
2. address: Street, city, state, postal code of the vendor.
3. email: Vendor contact email address.
4. phone: Vendor telephone or contact number.
5. terms_and_conditions: Payment terms (e.g., Net 30 Days, 50% advance), delivery window, or warranty notes.
6. po_number_suggestion: Quote reference number or PO number if present.
7. line_items: An array of items where each item contains:
   - description: Item name or specifications.
   - quantity: Numeric quantity (float/integer, default 1.0).
   - rate: Quoted unit price/rate per single item (numeric without currency symbols).

Ensure all numbers are plain numeric values. Return strictly valid JSON adhering to the schema.
"""

import io
import re

def extract_text_and_details_from_pdf_bytes(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Local PDF parsing engine using pypdf and regex heuristics.
    Parses vendor metadata and line items directly from PDF document bytes.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return {}

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        full_text = "\n".join([page.extract_text() or "" for page in reader.pages])
    except Exception as e:
        print(f"Error extracting PDF text with pypdf: {e}")
        return {}

    if not full_text.strip():
        return {}

    extracted = {
        "vendor_name": "",
        "address": "",
        "vendor_address": "",
        "email": "",
        "vendor_email": "",
        "phone": "",
        "vendor_phone": "",
        "terms_and_conditions": "",
        "po_number_suggestion": "",
        "line_items": []
    }

    lines = [l.strip() for l in full_text.splitlines() if l.strip()]

    # 1. Vendor Email
    email_m = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', full_text)
    if email_m:
        extracted["email"] = email_m.group(0)
        extracted["vendor_email"] = email_m.group(0)

    # 2. Vendor Phone
    phone_m = re.search(r'(?:Tel|Phone|Mobile|Ph|Contact)?[:\s]*(\+?\d[\d\s\-\(\)]{7,}\d)', full_text, re.IGNORECASE)
    if phone_m:
        phone_val = phone_m.group(1).strip()
        extracted["phone"] = phone_val
        extracted["vendor_phone"] = phone_val

    # 3. Quote / Reference Number
    po_m = re.search(r'(?:Quote|Quotation|PO|Invoice|Ref|Reference)\s*(?:#|No|Number)?[:\s]*([A-Z0-9\-_]{3,25})', full_text, re.IGNORECASE)
    if po_m:
        extracted["po_number_suggestion"] = po_m.group(1).strip()

    # 4. Vendor Name
    for l in lines[:6]:
        if any(kw in l.lower() for kw in ['quotation', 'invoice', 'purchase order', 'date:', 'page ', 'bill to', 'ship to', 'official', 'item description']):
            continue
        cleaned = re.sub(r'[\d\+\-\|\:\,]+', ' ', l).strip()
        if len(cleaned) > 3:
            name_part = l.split('|')[0]
            name_part = re.split(r'\d+\s+[A-Za-z]', name_part)[0].strip()
            if name_part:
                extracted["vendor_name"] = name_part
                break

    # 5. Vendor Address
    addr_m = re.search(r'(\d+[\w\s\,\.\-]+(?:Street|St|Way|Ave|Avenue|Blvd|Road|Rd|Suite|Ste|Drive|Dr|CA|NY|TX|UK|India|London|San Jose)[\w\s\,\.\-\d]*)', full_text, re.IGNORECASE)
    if addr_m:
        addr_val = addr_m.group(1).strip()
        extracted["address"] = addr_val
        extracted["vendor_address"] = addr_val

    # 6. Terms & Conditions
    terms_m = re.search(r'(?:Terms|Conditions|Payment Terms|Validity)[:\s]*(.*?)(?:\n\n|\Z)', full_text, re.IGNORECASE | re.DOTALL)
    if terms_m:
        extracted["terms_and_conditions"] = terms_m.group(1).strip()[:300]
    else:
        extracted["terms_and_conditions"] = "Standard payment terms apply."

    # 7. Line Items Extraction
    line_items = []
    
    # Pattern A: Sequential multi-line table format (Desc, Qty, Rate, Total)
    i = 0
    while i < len(lines):
        if i + 3 < len(lines):
            desc = lines[i]
            q_str = lines[i+1].replace(',', '').replace('$', '').replace('€', '').replace('₹', '').replace('£', '')
            r_str = lines[i+2].replace(',', '').replace('$', '').replace('€', '').replace('₹', '').replace('£', '')
            s_str = lines[i+3].replace(',', '').replace('$', '').replace('€', '').replace('₹', '').replace('£', '')
            
            if (re.match(r'^\d+(\.\d+)?$', q_str) and 
                re.match(r'^\d+(\.\d+)?$', r_str) and 
                re.match(r'^\d+(\.\d+)?$', s_str) and 
                not any(h in desc.lower() for h in ['qty', 'rate', 'total', 'subtotal', 'item', 'description', 'valid until'])):
                line_items.append({
                    "description": desc,
                    "quantity": float(q_str),
                    "rate": float(r_str)
                })
                i += 4
                continue
        i += 1

    # Pattern B: Single-line table format
    if not line_items:
        single_line_re = re.compile(
            r'^(?P<desc>[A-Za-z0-9\s\-\/\.\(\)\,\&]+?)\s+(?P<qty>\d+(?:\.\d+)?)\s+(?:[\$\€\₹\£]\s*)?(?P<rate>[\d\,]+(?:\.\d+)?)(?:\s+(?:[\$\€\₹\£]\s*)?[\d\,]+(?:\.\d+)?)?$'
        )
        for l in lines:
            if any(h in l.lower() for h in ['description', 'unit rate', 'subtotal', 'total', 'valid until', 'customer', 'project', 'page ']):
                continue
            m = single_line_re.match(l)
            if m:
                desc = m.group('desc').strip()
                try:
                    q = float(m.group('qty').replace(',', ''))
                    r = float(m.group('rate').replace(',', ''))
                    if len(desc) > 2 and not desc.lower().startswith("quote") and not desc.lower().startswith("date"):
                        line_items.append({"description": desc, "quantity": q, "rate": r})
                except ValueError:
                    pass

    # Pattern C: Heuristic splitting by whitespace/tabs
    if not line_items:
        for l in lines:
            parts = re.split(r'\s{2,}|\t', l)
            if len(parts) >= 3:
                try:
                    p_desc = parts[0].strip()
                    p_qty = float(parts[1].replace(',', '').replace('$', '').replace('€', '').replace('₹', '').replace('£', ''))
                    p_rate = float(parts[2].replace(',', '').replace('$', '').replace('€', '').replace('₹', '').replace('£', ''))
                    if len(p_desc) > 2 and p_rate >= 0:
                        line_items.append({"description": p_desc, "quantity": p_qty, "rate": p_rate})
                except Exception:
                    continue

    extracted["line_items"] = line_items
    return extracted


def extract_quote_from_pdf(
    pdf_bytes: Optional[bytes] = None,
    mime_type: str = "application/pdf",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts vendor details, terms & conditions, and line items from an uploaded PDF.
    First attempts Gemini AI extraction if key is present.
    If Gemini is unavailable or fails, falls back to local pypdf text extraction.
    """
    active_key = api_key or GEMINI_API_KEY
    extracted_dict = None
    last_error = None

    # 1. Attempt Gemini AI API Extraction if Key exists
    if active_key:
        try:
            if active_key == GEMINI_API_KEY and client is not None:
                active_client = client
            else:
                active_client = genai.Client(api_key=active_key, http_options={'api_version': 'v1beta'})
            
            import requests
            contents = []
            if pdf_bytes:
                import base64
                b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                contents.append({"inlineData": {"data": b64_pdf, "mimeType": mime_type}})
            else:
                contents.append({"text": "Extract sample hardware vendor quotation details."})

            contents.append({"text": "Extract all vendor information, payment terms, and line items from this document into the JSON schema."})

            system_instruction = EXTRACTION_SYSTEM_PROMPT

            schema = {
                "type": "OBJECT",
                "properties": {
                    "vendor_name": {"type": "STRING"},
                    "address": {"type": "STRING"},
                    "email": {"type": "STRING"},
                    "phone": {"type": "STRING"},
                    "terms_and_conditions": {"type": "STRING"},
                    "po_number_suggestion": {"type": "STRING"},
                    "line_items": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "description": {"type": "STRING"},
                                "quantity": {"type": "NUMBER"},
                                "rate": {"type": "NUMBER"}
                            },
                            "required": ["description", "quantity", "rate"]
                        }
                    }
                },
                "required": ["vendor_name", "line_items"]
            }

            for model_name in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={active_key}"
                    headers = {"Content-Type": "application/json"}
                    payload = {
                        "contents": [{"parts": contents}],
                        "systemInstruction": {"parts": [{"text": system_instruction}]},
                        "generationConfig": {
                            "temperature": 0.1,
                            "responseMimeType": "application/json",
                            "responseSchema": schema
                        }
                    }

                    resp = requests.post(url, headers=headers, json=payload, timeout=12)
                    try:
                        resp.raise_for_status()
                    except Exception as http_err:
                        error_msg = str(http_err).replace(active_key, "HIDDEN_API_KEY")
                        raise Exception(error_msg)

                    resp_json = resp.json()
                    raw_json = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    extracted_dict = json.loads(raw_json)
                    if extracted_dict and extracted_dict.get("line_items"):
                        return extracted_dict
                except Exception as model_err:
                    last_error = model_err
                    print(f"Gemini API attempt with {model_name} failed: {model_err}")
                    continue

        except Exception as e:
            last_error = e
            print(f"Gemini API Exception: {e}")

    # 2. Local Fallback: Extract text directly from uploaded PDF bytes if available
    if pdf_bytes:
        print("Attempting local PDF text & table extraction...")
        local_extracted = extract_text_and_details_from_pdf_bytes(pdf_bytes)
        if local_extracted and (local_extracted.get("line_items") or local_extracted.get("vendor_name")):
            print(f"Local PDF parser successfully extracted {len(local_extracted.get('line_items', []))} items.")
            return local_extracted

    # 3. If neither Gemini nor local PDF extraction succeeded, return error payload (NEVER overwrite with demo data for user uploads)
    return {
        "vendor_name": "",
        "error": f"Could not extract text from document. If this is a scanned image or photo, please enter a Gemini API Key in sidebar settings. ({last_error or 'No text layer found'})",
        "line_items": []
    }


def get_fallback_quote_data() -> Dict[str, Any]:
    """Fallback sample quote data for instant testing and offline demo resilience."""
    import datetime
    return {
        "vendor_name": "Apex AI Enterprise Systems Ltd",
        "address": "700 Silicon Valley Way, Suite 400, San Jose, CA 95110",
        "vendor_address": "700 Silicon Valley Way, Suite 400, San Jose, CA 95110",
        "email": "procurement@apexai-systems.com",
        "vendor_email": "procurement@apexai-systems.com",
        "phone": "+1 (408) 555-0199",
        "vendor_phone": "+1 (408) 555-0199",
        "terms_and_conditions": "Payment Terms: Net 30 Days. Delivery within 10-14 business days. 3-Year Factory Warranty.",
        "po_number_suggestion": f"QUOTE-APX-{datetime.datetime.now().strftime('%m%d%H%M')}",
        "line_items": [
            {
                "description": "NVIDIA H100 80GB SXM5 GPU Accelerator",
                "quantity": 4.0,
                "rate": 33000.00
            },
            {
                "description": "Supermicro 4U 8-GPU AI Workstation Server",
                "quantity": 1.0,
                "rate": 46500.00
            },
            {
                "description": "Mellanox Quantum-2 InfiniBand 400G Switch 64-Port",
                "quantity": 2.0,
                "rate": 18900.00
            },
            {
                "description": "400G OSFP Active Optical Cable 5m",
                "quantity": 12.0,
                "rate": 480.00
            },
            {
                "description": "Micron 7450 PRO 7.68TB NVMe PCIe 4.0 Enterprise SSD",
                "quantity": 8.0,
                "rate": 875.00
            }
        ]
    }

