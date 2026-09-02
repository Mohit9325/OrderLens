import os
import json
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Hardcoded Gemini API Key as specified
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AQ.Ab8RN6IOyF6jFpNlUGEO78nHeelShdrkSBacDNXT5IZOpCrI6g"

# Initialize Google GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)

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

def extract_quote_from_pdf(
    pdf_bytes: Optional[bytes] = None,
    mime_type: str = "application/pdf",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts vendor details, terms & conditions, and line items from an uploaded PDF using Gemini 2.5 Flash.
    """
    active_key = api_key or GEMINI_API_KEY
    
    try:
        # Initialize client with active key
        active_client = genai.Client(api_key=active_key) if active_key != GEMINI_API_KEY else client
        
        contents = []
        if pdf_bytes:
            contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type=mime_type))
        else:
            contents.append("Extract sample hardware vendor quotation details.")

        contents.append("Extract all vendor information, payment terms, and line items from this document into the JSON schema.")

        last_error = None
        # Prefer the fastest model first for snappier image extraction
        for model_name in ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"]:
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
                raw_json = response.text
                extracted_dict = json.loads(raw_json)
                return extracted_dict
            except Exception as model_err:
                last_error = model_err
                print(f"Attempt with {model_name} encountered: {model_err}")
                
                # If it's a rate limit (429), don't bother trying other models, it will just delay the user
                if "429" in str(model_err) or "RESOURCE_EXHAUSTED" in str(model_err):
                    break
                    
                continue
                
        # If we exit the loop without returning, all attempts failed
        if last_error:
            raise last_error
        else:
            raise RuntimeError("All Gemini model extraction attempts failed.")

    except Exception as e:
        # Instead of falling back silently, raise the error so we can see what's wrong
        raise Exception(f"Gemini API Error: {str(e)}")


def get_fallback_quote_data() -> Dict[str, Any]:
    """Fallback sample quote data for instant testing and offline resilience."""
    import datetime
    return {
        "vendor_name": "Apex AI Enterprise Systems Ltd",
        "address": "700 Silicon Valley Way, Suite 400, San Jose, CA 95110",
        "email": "procurement@apexai-systems.com",
        "phone": "+1 (408) 555-0199",
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
