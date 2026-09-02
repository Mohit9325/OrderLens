# 🔎 OrderLens - AI-Powered Purchase Order Extraction & Catalog Price Engine

**OrderLens** is an enterprise-grade web application built using **Streamlit**, **Supabase (PostgreSQL)**, **Google GenAI SDK (Gemini)**, and **WeasyPrint / ReportLab** for automating procurement document parsing, master product catalog price audits, interactive line-item editing, database tracking, and official A4 PDF generation.

---

## 🌟 Key Features

1. **📄 Document Extraction with Gemini AI**:
   - Upload unstructured vendor quotes, invoices, or Bill of Quantities (BQ) in PDF, PNG, JPG, JPEG, and WEBP formats.
   - Structured OCR extraction extracting `vendor_name`, `address`, `email`, `phone`, `terms_and_conditions`, and line items (`description`, `quantity`, `rate`).

2. **📦 Master Product Catalog (Supabase)**:
   - Connects directly to Supabase PostgreSQL table (`products`).
   - Automatically cross-references extracted item descriptions against the Master Catalog to inject standard rates, stock availability, SKU codes, and calculate price variances.

3. **✏️ Interactive Line Item Data Editor**:
   - Review and modify extracted quantities and rates in real-time via `st.data_editor`.
   - Add new rows or remove obsolete items with automatic recalculation of subtotals, tax (18%), shipping, and grand totals.

4. **🗄️ Database Tracking & Historical Audit**:
   - Persist approved Purchase Orders into Supabase (`purchase_orders` and `po_items` tables).
   - Filter, inspect, and re-download archived Purchase Orders anytime.

5. **📑 Official AI Turing Technologies A4 PDF Generator**:
   - Formats approved Purchase Orders into the official **AI Turing Technologies** corporate A4 template.
   - Includes logo branding, vendor & buyer blocks, itemized tables, catalog price comparisons, commercial terms, and digital signature verification blocks.

---

## 🚀 Quickstart Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure your API keys:
```bash
cp .env.example .env
```
Edit `.env`:
```env
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Supabase Credentials (Optional - uses local SQLite if omitted)
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
```

### 3. Setup Supabase Database Schema
If using Supabase, open your Supabase SQL Editor and execute the provided [`schema.sql`](file:///d:/OrderLens/schema.sql) script.

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📂 Project Structure

```
d:\OrderLens\
├── app.py                      # Streamlit Web Application & UI Layout
├── extractor.py                # Gemini AI Extraction & Catalog Matching Engine
├── db.py                       # Supabase Client & SQLite Database Manager
├── pdf_generator.py            # A4 PDF Generation Engine (WeasyPrint & ReportLab)
├── schema.sql                  # Supabase PostgreSQL DDL & Seed Data
├── requirements.txt            # Python Dependencies
├── .env.example                # Environment Variable Template
├── sample_data/                # Sample Vendor Quotes for instant demo testing
│   ├── create_sample_pdf.py    # Sample Quote PDF Generator
│   └── vendor_quote_apex_ai.pdf# Pre-built Demo Quote PDF
└── test_pipeline.py            # Automated End-to-End Pipeline Verification Test
```
