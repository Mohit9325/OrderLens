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
    Local PDF parsing engine using pypdf and intelligent regex heuristics.
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

    # 2. Vendor Phone (Exclude dates starting with 2024/2025/2026/2027)
    phone_m = re.search(r'\b(?:Tel|Phone|Mobile|Ph|Fax|Contact)[:\s]*(\+?[\d\s\-\(\)]{8,20})', full_text, re.IGNORECASE)
    if not phone_m:
        phone_m = re.search(r'(\+\d{1,3}[\s\-\(\)]\d[\d\s\-\(\)]{7,15})', full_text)
        
    if phone_m:
        phone_candidate = phone_m.group(1).strip()
        digits_only = re.sub(r'\D', '', phone_candidate)
        if not phone_candidate.startswith(('202', '201', '199')) and 7 <= len(digits_only) <= 15:
            extracted["phone"] = phone_candidate
            extracted["vendor_phone"] = phone_candidate

    # 3. Quote / PO / Reference Number
    explicit_po_m = re.search(r'\b([A-Z0-9]{2,8}\/(?:PO|QUOTE|INV|REF)\/[A-Z0-9\/\-_]{3,25})\b', full_text, re.IGNORECASE)
    if not explicit_po_m:
        explicit_po_m = re.search(r'\b((?:QUOTE|PO|INV|REF)[\-_][A-Z0-9\-_]{3,20})\b', full_text, re.IGNORECASE)
        
    if explicit_po_m:
        extracted["po_number_suggestion"] = explicit_po_m.group(1).strip()
    else:
        po_matches = re.findall(r'\b(?:Quote|Quotation|PO|Invoice|Ref|Reference)\b[\s\.\:\#]*(?:No|Number|ID)?[:\.\s]*([A-Za-z0-9\/_\-]{3,30})', full_text, re.IGNORECASE)
        for candidate in po_matches:
            c_clean = candidate.strip()
            if c_clean.lower() not in ['date', 'number', 'no', 'code', 'ref', 'reference', 'po', 'details', 'invoice', 'quote', 'quotation', 'status', 'pending', 'approved', 'item', 'supplier']:
                extracted["po_number_suggestion"] = c_clean
                break

    # 4. Vendor Name
    vendor_name_cand = ""
    v_label_m = re.search(r'\b(?:Supplier|Vendor|Company|From)\s*(?:Name|Details)?[:\s]*([^\n]+)', full_text, re.IGNORECASE)
    if v_label_m:
        v_raw = v_label_m.group(1).strip()
        v_raw = re.sub(r'PO\.?\s*No\.?:?\s*[A-Za-z0-9\/_\-]+', '', v_raw, flags=re.IGNORECASE).strip()
        v_raw = re.sub(r'[\:\=\|\-\#]+', ' ', v_raw).strip()
        if len(v_raw) > 2 and not any(bad in v_raw.lower() for bad in ['supplier', 'vendor', 'po.no', 'ait/po', 'details', 'approval', 'delivery', 'payment']):
            vendor_name_cand = v_raw

    if not vendor_name_cand:
        invalid_words = ['quotation', 'invoice', 'purchase order', 'date:', 'page ', 'bill to', 'ship to', 'official', 'item description', 'supplier details', 'enterprise portal', 'approval', 'delivery', 'payment', 'terms', 'conditions', 'warranty', 'valid', 'customer', 'project']
        for l in lines[:8]:
            if any(kw in l.lower() for kw in invalid_words):
                continue
            cleaned = re.sub(r'[\d\+\-\|\:\,]+', ' ', l).strip()
            if len(cleaned) > 3:
                name_part = l.split('|')[0]
                name_part = re.split(r'\d+\s+[A-Za-z]', name_part)[0].strip()
                name_part = re.sub(r'[\.\,]+$', '', name_part).strip()
                if name_part and not any(bad in name_part.lower() for bad in ['supplier', 'po.no', 'ait/po', 'details', 'approval', 'delivery', 'payment', 'terms']):
                    vendor_name_cand = name_part
                    break

    if (not vendor_name_cand or any(bad in vendor_name_cand.lower() for bad in ['supplier', 'po.no', 'ait/po', 'approval', 'details'])) and extracted.get("email"):
        domain = extracted["email"].split('@')[-1].split('.')[0]
        if domain not in ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud']:
            vendor_name_cand = ' '.join(word.capitalize() for word in re.split(r'[\-_\.]', domain))

    extracted["vendor_name"] = vendor_name_cand


    # 5. Vendor Address
    addr_m = re.search(r'(\d+[\w\s\,\.\-]+(?:Street|St|Way|Ave|Avenue|Blvd|Road|Rd|Suite|Ste|Drive|Dr|Floor|Bldg|Building|San Jose|CA|NY|TX|UK|London|India|Korea)[\w\s\,\.\-\d]*)', full_text, re.IGNORECASE)
    if addr_m:
        addr_val = addr_m.group(1).strip()
        addr_val = re.sub(r'^(?:PO\.?\s*No\.?:?\s*)?[A-Za-z0-9\/_\-]+\s*', '', addr_val, flags=re.IGNORECASE).strip()
        if len(addr_val) > 4 and not any(bad in addr_val.lower() for bad in ['supplier', 'po.no', 'ait/po']):
            extracted["address"] = addr_val
            extracted["vendor_address"] = addr_val

    # 6. Terms & Conditions
    terms_m = re.search(r'(?:Terms|Conditions|Payment Terms|Delivery Time|Validity)[:\s]*(.*?)(?:\n\n|\Z)', full_text, re.IGNORECASE | re.DOTALL)
    if terms_m:
        extracted["terms_and_conditions"] = terms_m.group(1).strip()[:300]
    else:
        extracted["terms_and_conditions"] = "Standard payment terms apply."

    # 7. Line Items Extraction
    line_items = []
    
    # Pattern A: Multi-line / table format (Desc, Qty, Rate, Total)
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

    # Pattern B: Single-line regex pattern
    if not line_items:
        single_line_re = re.compile(
            r'^(?P<desc>[A-Za-z0-9\s\-\/\.\(\)\,\&]+?)\s+(?P<qty>\d+(?:\.\d+)?)\s+(?:[\$\€\₹\£]\s*)?(?P<rate>[\d\,]+(?:\.\d+)?)(?:\s+(?:[\$\€\₹\£]\s*)?[\d\,]+(?:\.\d+)?)?$'
        )
        for l in lines:
            if any(h in l.lower() for h in ['description', 'unit rate', 'subtotal', 'total', 'valid until', 'customer', 'project', 'page ', 'supplier details', 'enterprise portal']):
                continue
            clean_l = re.sub(r'^\s*\d+[\.\)]\s*', '', l)
            m = single_line_re.match(clean_l)
            if m:
                desc = m.group('desc').strip()
                try:
                    q = float(m.group('qty').replace(',', ''))
                    r = float(m.group('rate').replace(',', ''))
                    if len(desc) > 2 and not desc.lower().startswith("quote") and not desc.lower().startswith("date") and not desc.lower().startswith("po"):
                        line_items.append({"description": desc, "quantity": q, "rate": r})
                except ValueError:
                    pass

    # Pattern C: Whitespace / Tab split
    if not line_items:
        for l in lines:
            parts = re.split(r'\s{2,}|\t', l)
            if len(parts) >= 3:
                try:
                    p_desc = parts[0].strip()
                    p_desc = re.sub(r'^\s*\d+[\.\)]\s*', '', p_desc).strip()
                    p_qty = float(parts[1].replace(',', '').replace('$', '').replace('€', '').replace('₹', '').replace('£', ''))
                    p_rate = float(parts[2].replace(',', '').replace('$', '').replace('€', '').replace('₹', '').replace('£', ''))
                    if len(p_desc) > 2 and p_rate >= 0 and not any(bad in p_desc.lower() for bad in ['quote', 'date', 'po', 'invoice', 'order', 'total', 'subtotal']):
                        line_items.append({"description": p_desc, "quantity": p_qty, "rate": p_rate})
                except Exception:
                    continue

    # Pattern D: Flexible regex for lines with description and quantities/prices
    if not line_items:
        flexible_re = re.compile(
            r'^(?P<desc>[A-Za-z0-9\s\-\/\.\(\)\,\&\#]+?)\s+(?:qty[:\s]*)?(?P<qty>\d+(?:\.\d+)?)\s*(?:pcs|units|nos|ea|set|box|kg)?\s*(?:@|x|\*|at)?\s*(?:[\$\€\₹\£]\s*)?(?P<rate>[\d\,]+(?:\.\d+)?)',
            re.IGNORECASE
        )
        for l in lines:
            if any(h in l.lower() for h in ['description', 'unit rate', 'subtotal', 'total', 'valid until', 'customer', 'project', 'page ', 'supplier details', 'enterprise portal', 'payment', 'terms', 'bank', 'gst', 'tax']):
                continue
            m = flexible_re.match(l)
            if m:
                desc = m.group('desc').strip()
                desc = re.sub(r'^\s*\d+[\.\)]\s*', '', desc).strip()
                try:
                    q = float(m.group('qty').replace(',', ''))
                    r = float(m.group('rate').replace(',', ''))
                    if len(desc) > 2 and r >= 0 and not any(bad in desc.lower() for bad in ['quote', 'date', 'po', 'invoice', 'order', 'total', 'subtotal']):
                        line_items.append({"description": desc, "quantity": q, "rate": r})
                except ValueError:
                    pass

    extracted["line_items"] = line_items
    return extracted


def extract_quote_from_pdf(
    pdf_bytes: Optional[bytes] = None,
    mime_type: str = "application/pdf",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts vendor details, terms & conditions, and line items from an uploaded PDF or image.
    First attempts Gemini AI extraction using GenAI SDK if key is present.
    If Gemini is unavailable or fails, falls back to local pypdf text extraction.
    """
    active_key = api_key or GEMINI_API_KEY
    extracted_dict = None
    last_error = None

    # 1. Attempt Gemini AI API Extraction via GenAI SDK if Key exists
    if active_key:
        try:
            active_client = genai.Client(api_key=active_key)
            contents = []
            if pdf_bytes:
                contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type=mime_type))
            else:
                contents.append("Extract sample hardware vendor quotation details.")

            contents.append("Extract all vendor information, payment terms, reference numbers, and line items from this document into structured JSON.")

            for model_name in ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]:
                try:
                    response = active_client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=EXTRACTION_SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            response_schema=ExtractedQuote,
                            temperature=0.1,
                        )
                    )
                    if response and response.text:
                        extracted_dict = json.loads(response.text)
                        if extracted_dict and (extracted_dict.get("line_items") or extracted_dict.get("vendor_name")):
                            return extracted_dict
                except Exception as m_err:
                    last_error = m_err
                    print(f"GenAI SDK attempt with {model_name} failed: {m_err}")
                    continue

        except Exception as e:
            last_error = e
            print(f"GenAI SDK Exception: {e}")

    # 2. Local Fallback: Extract text directly from uploaded PDF bytes if available
    local_extracted = {}
    if pdf_bytes and ("pdf" in mime_type.lower() or not mime_type):
        print("Attempting local PDF text & table extraction...")
        local_extracted = extract_text_and_details_from_pdf_bytes(pdf_bytes)
        if local_extracted and local_extracted.get("line_items"):
            print(f"Local PDF parser successfully extracted {len(local_extracted.get('line_items', []))} items.")
            return local_extracted

    # 3. Construct detailed error payload if 0 line items were extracted
    error_detail = ""
    if last_error:
        err_str = str(last_error)
        if "401" in err_str or "UNAUTHENTICATED" in err_str:
            error_detail = "Gemini API key is invalid or unauthenticated (401). Please verify your Gemini API key in settings."
        else:
            error_detail = f"Gemini API error: {err_str}"
    elif pdf_bytes:
        error_detail = "No text layer found in PDF. If this is a scanned document or image, please configure a valid Gemini API Key (starting with AIzaSy) in sidebar settings for OCR vision extraction."
    else:
        error_detail = "No document provided for extraction."

    res = local_extracted if (local_extracted and isinstance(local_extracted, dict)) else {}
    res["error"] = error_detail
    if "line_items" not in res:
        res["line_items"] = []
    return res




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

