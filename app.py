import os
import io
import datetime
import pandas as pd
import streamlit as st
import plotly.express as px

from db import DatabaseManager
from ai_engine import extract_quote_from_pdf, get_fallback_quote_data
from pdf_generator import generate_po_pdf, generate_po_html

# Page Configuration
st.set_page_config(
    page_title="AiTuring - Enterprise Procurement Hub",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main {
        background-color: #0a0a0a;
    }
    
    .brand-card {
        background: linear-gradient(135deg, #1f1f1f 0%, #0a0a0a 100%);
        border: 1px solid #262626;
        border-radius: 12px;
        padding: 22px 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }
    
    .brand-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #F8FAFC;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .brand-title span {
        color: #dc2626;
    }
    
    .brand-subtitle {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-top: 5px;
    }

    .badge-supabase {
        background-color: #064E3B;
        color: #34D399;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .badge-local {
        background-color: #451A03;
        color: #FBBF24;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .badge-gemini {
        background-color: #1E1B4B;
        color: #818CF8;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .section-title {
        color: #dc2626;
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 18px;
        margin-bottom: 12px;
        border-bottom: 1px solid #262626;
        padding-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# State Management
if "db" not in st.session_state:
    try:
        supabase_url = st.secrets.get("SUPABASE_URL", "").strip().rstrip('/') if hasattr(st, "secrets") else ""
        supabase_key = st.secrets.get("SUPABASE_KEY", "").strip() if hasattr(st, "secrets") else ""
    except Exception:
        supabase_url = ""
        supabase_key = ""
    st.session_state.db = DatabaseManager(supabase_url=supabase_url, supabase_key=supabase_key)

if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None

if "last_saved_po" not in st.session_state:
    st.session_state.last_saved_po = None

if "role" not in st.session_state:
    st.session_state.role = "Employee"

db: DatabaseManager = st.session_state.db

# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/isometric/96/000000/purchase-order.png", width=60)
    st.title("AiTuring Settings")
    
    st.markdown("---")
    st.subheader("👤 Authentication")
    st.session_state.role = st.radio("Select User Role", ["Employee", "Procurement Manager"], index=0 if st.session_state.role == "Employee" else 1)
    
    try:
        secret_key = st.secrets.get("GEMINI_API_KEY", "").replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')
    except Exception:
        secret_key = ""
        
    user_api_key = (os.getenv("GEMINI_API_KEY") or "").replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '') or secret_key
    if not user_api_key:
        st.error("Missing Gemini API Key. Please configure it in Streamlit Secrets.")

    st.markdown("---")
    st.subheader("⚙️ Procurement Defaults")
    currency = st.selectbox("Currency", ["$", "€", "₹", "£"], index=0)
    tax_rate = st.number_input("Standard Tax Rate (%)", min_value=0.0, max_value=50.0, value=18.0, step=0.5)
    shipping_fee = st.number_input("Standard Shipping Fee", min_value=0.0, value=0.0, step=10.0)

    st.markdown("---")
    st.caption("AI Turing Technologies Enterprise Hub")

import base64

logo_path = os.path.join(os.path.dirname(__file__), "emblem.png")
logo_b64 = ""
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()

# Main Header
st.markdown(f"""
<div style="background-color: #ffffff; border-left: 8px solid #dc2626; border-radius: 12px; padding: 32px 40px; margin-bottom: 30px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); display: flex; align-items: center; gap: 32px;">
    <img src="data:image/png;base64,{logo_b64}" style="height: 130px; width: auto; object-fit: contain; background: transparent; display: block;" />
    <div>
        <div style="font-size: 2.2rem; font-weight: 900; color: #111111; margin: 0; line-height: 1.2; letter-spacing: -0.5px;">AiTuring Technologies</div>
        <div style="display: flex; align-items: center; gap: 12px; margin-top: 10px;">
            <span style="background-color: #fef2f2; color: #dc2626; font-size: 0.85rem; font-weight: 800; padding: 6px 12px; border-radius: 6px; border: 1px solid #fecaca; letter-spacing: 0.5px;">ENTERPRISE PORTAL</span>
            <span style="color: #64748b; font-size: 1.1rem; font-weight: 500;">AI-Powered Quote Extraction & Master Catalog Audit</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Tabs
if st.session_state.role == "Procurement Manager":
    tab_create_po, tab_order_history, tab_analytics = st.tabs([
        "📝 Create Purchase Order",
        "📊 Order History Dashboard",
        "📈 Receipt History & Analysis"
    ])
else:
    tab_create_po = st.tabs(["📝 Create Purchase Order"])[0]

# ==============================================================================
# TAB 1: CREATE PURCHASE ORDER
# ==============================================================================
with tab_create_po:
    c_up1, c_up2 = st.columns([3, 2])
    
    with c_up1:
        uploaded_pdf = st.file_uploader(
            "Upload Vendor Quotation or BQ (PDF or Image)",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
            help="Upload vendor quote PDF to automatically extract line items and vendor metadata."
        )

    with c_up2:
        st.markdown("<br>", unsafe_allow_html=True)
        demo_btn = st.button("⚡ Load Demo Quote PDF (Apex AI Hardware)", width='stretch', help="Load pre-built quotation for instant demo.")

    # Trigger AI Extraction
    if uploaded_pdf or demo_btn:
        if demo_btn or (uploaded_pdf and st.button("🔍 Extract Quote with Gemini AI", type="primary", width='stretch')):
            with st.spinner("🚀 Analyzing document with AiTuring AI Engine & cross-referencing Master Catalog..."):
                if demo_btn:
                    raw_extracted = {
                        "vendor_name": "APEX AI ENTERPRISE SYSTEMS LTD",
                        "po_number_suggestion": "QUOTE-APX-9942",
                        "vendor_address": "700 Silicon Valley Way, Suite 400, San Jose, CA 95110",
                        "vendor_email": "sales@apexai-systems.com",
                        "vendor_phone": "+1 (408) 555-0199",
                        "line_items": [
                            {"description": "NVIDIA H100 80GB", "quantity": 4, "rate": 33000.0},
                            {"description": "Supermicro 4U Server", "quantity": 1, "rate": 46500.0}
                        ]
                    }
                else:
                    pdf_bytes = uploaded_pdf.getvalue()
                    mime = uploaded_pdf.type or "application/pdf"
                    active_api_key = user_api_key if user_api_key else st.secrets.get("GEMINI_API_KEY")
                    try:
                        raw_extracted = extract_quote_from_pdf(pdf_bytes=pdf_bytes, mime_type=mime, api_key=active_api_key)
                    except Exception as e:
                        st.error(f"Failed to extract document. {str(e)}")
                        raw_extracted = {}

                # Enrich with Catalog Matching
                if not isinstance(raw_extracted, dict):
                    raw_extracted = {}
                
                # If extraction failed completely, stop processing the rest of this block
                if not raw_extracted:
                    st.warning("Please check your API key quota or try another document.")
                    raw_items = []
                else:
                    raw_items = raw_extracted.get("line_items", [])
                enriched_items = []
                
                for it in raw_items:
                    desc = it.get("description", "")
                    qty = float(it.get("quantity", 1.0))
                    quoted_rate = float(it.get("rate", 0.0))
                    
                    # Look up standard rate and stock from Supabase/DB Master Catalog
                    matched = db.find_matching_product(desc)
                    if matched:
                        cat_rate = float(matched.get("unit_price", 0.0))
                        cat_sku = matched.get("sku", "N/A")
                        cat_stock = matched.get("stock_quantity", 0)
                        status = "Matched"
                        var_pct = round(((quoted_rate - cat_rate) / cat_rate * 100), 2) if cat_rate > 0 else 0.0
                    else:
                        cat_rate = quoted_rate
                        cat_sku = "N/A"
                        cat_stock = 0
                        status = "New Item"
                        var_pct = 0.0
                        
                    enriched_items.append({
                        "description": desc,
                        "quantity": qty,
                        "rate": quoted_rate,
                        "catalog_rate": cat_rate,
                        "catalog_sku": cat_sku,
                        "stock_quantity": cat_stock,
                        "match_status": status,
                        "variance_pct": var_pct,
                        "total": round(qty * quoted_rate, 2)
                    })
                
                raw_extracted["line_items"] = enriched_items
                st.session_state.extracted_data = raw_extracted
                st.session_state.last_saved_po = None
                
                # Add unique extraction ID to force Streamlit to wipe stale widget cache
                import uuid
                st.session_state.extraction_id = str(uuid.uuid4())
                
                import random
                st.session_state.po_seq = random.randint(10, 99)
                
                st.toast("Quotation extracted and auto-matched against Master Product Catalog!", icon="✅")

    # Display Extracted Form & Editable Table
    if st.session_state.extracted_data:
        data = st.session_state.extracted_data
        
        st.markdown('<div class="section-title">1. Purchase Order & Vendor Details</div>', unsafe_allow_html=True)
        
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            if 'po_seq' not in st.session_state:
                import random
                st.session_state.po_seq = random.randint(10, 99)
            po_num = st.text_input("PO Number", value=f"AIT/PO/2026-27/{st.session_state.po_seq}")
        with p2:
            po_date = st.date_input("PO Date", value=datetime.date.today())
        with p3:
            po_ref = st.text_input("Reference No.", value=data.get("po_number_suggestion", ""))
        with p4:
            if st.session_state.role == "Procurement Manager":
                po_status = st.selectbox("PO Status", ["Approved", "Pending", "Draft", "Sent", "Completed"], index=0)
            else:
                st.text_input("PO Status", value="Pending", disabled=True)
                po_status = "Pending"

        v1, v2, v3, v4 = st.columns([2, 2, 2, 2])
        ext_key = st.session_state.get('extraction_id', 'init')
        
        with v1:
            v_name = st.text_input("Vendor Name", value=data.get("vendor_name", ""), key=f"vname_{ext_key}")
        with v2:
            v_addr = st.text_input("Vendor Address", value=data.get("vendor_address", data.get("address", "")), key=f"vaddr_{ext_key}")
        with v3:
            v_email = st.text_input("Vendor Email", value=data.get("vendor_email", data.get("email", "")), key=f"vemail_{ext_key}")
        with v4:
            v_phone = st.text_input("Vendor Phone", value=data.get("vendor_phone", data.get("phone", "")), key=f"vphone_{ext_key}")

        v_terms = st.text_area("Commercial Terms & Conditions", value=data.get("terms_and_conditions", "Standard Payment Terms: Net 30 Days from delivery verification."), height=70, key=f"vterms_{ext_key}")

        st.markdown('<div class="section-title">2. Interactive Line Items (st.data_editor)</div>', unsafe_allow_html=True)
        st.caption("Review extracted items, edit rates/quantities, or add new items. Values in blue match Master Product Catalog standard rates.")

        items_list = data.get("line_items", [])
        df_edit = pd.DataFrame(items_list)
        
        # Ensure standard columns
        for col in ["description", "quantity", "rate", "catalog_rate", "catalog_sku", "stock_quantity", "match_status", "variance_pct"]:
            if col not in df_edit.columns:
                df_edit[col] = 0.0 if ("rate" in col or "pct" in col) else ("" if "sku" in col or "desc" in col else 1)

        display_df = df_edit[["description", "quantity", "rate", "catalog_rate", "catalog_sku", "stock_quantity", "match_status", "variance_pct"]].copy()

        # Interactive Data Editor
        edited_table = st.data_editor(
            display_df,
            num_rows="dynamic",
            width='stretch',
            column_config={
                "description": st.column_config.TextColumn("Item Description", width="large", required=True),
                "quantity": st.column_config.NumberColumn("Qty", min_value=1, step=1, required=True),
                "rate": st.column_config.NumberColumn(f"Quoted Rate ({currency})", min_value=0.0, format=f"{currency}%.2f", required=True),
                "catalog_rate": st.column_config.NumberColumn(f"Catalog Standard Rate ({currency})", format=f"{currency}%.2f", disabled=True),
                "catalog_sku": st.column_config.TextColumn("SKU", disabled=True),
                "stock_quantity": st.column_config.NumberColumn("Stock Qty", disabled=True),
                "match_status": st.column_config.TextColumn("Catalog Match", disabled=True),
                "variance_pct": st.column_config.NumberColumn("Variance (%)", format="%.2f%%", disabled=True)
            },
            key=f"interactive_po_table_{ext_key}"
        )

        # Dynamic Recalculation
        verified_items = []
        subtotal = 0.0
        for row in edited_table.to_dict(orient="records"):
            d = str(row.get("description", "")).strip()
            if not d:
                continue
            q = float(row.get("quantity", 1))
            r = float(row.get("rate", 0.0))
            cr = float(row.get("catalog_rate", 0.0))
            sku = str(row.get("catalog_sku", "N/A"))
            tot = round(q * r, 2)
            subtotal += tot
            verified_items.append({
                "description": d,
                "quantity": q,
                "unit_price": r,
                "rate": r,
                "catalog_rate": cr,
                "catalog_sku": sku,
                "total_price": tot,
                "total": tot
            })

        tax_amt = round(subtotal * (tax_rate / 100.0), 2)
        grand_total = round(subtotal + tax_amt + shipping_fee, 2)

        # Metric Cards
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Items", len(verified_items))
        with m2:
            st.metric("Subtotal", f"{currency}{subtotal:,.2f}")
        with m3:
            st.metric(f"Tax ({tax_rate}%)", f"{currency}{tax_amt:,.2f}")
        with m4:
            st.metric("Grand Total", f"{currency}{grand_total:,.2f}")

        # Action: Generate & Save PO
        st.markdown("---")
        b1, b2 = st.columns([2, 3])
        
        with b1:
            if st.session_state.role == "Procurement Manager":
                save_btn_label = "🚀 Generate & Save Purchase Order to Supabase"
            else:
                save_btn_label = "📤 Submit Quote for Manager Approval"
            save_btn = st.button(save_btn_label, type="primary", width='stretch')

        po_meta = {
            "po_number": po_num,
            "ref_no": po_ref,
            "vendor_name": v_name,
            "vendor_address": v_addr,
            "vendor_email": v_email,
            "vendor_phone": v_phone,
            "po_date": str(po_date),
            "terms_and_conditions": v_terms,
            "subtotal": subtotal,
            "tax_amount": tax_amt,
            "shipping_amount": shipping_fee,
            "grand_total": grand_total,
            "status": po_status
        }

        if save_btn:
            try:
                saved_record = db.save_purchase_order(po_meta, verified_items)
                st.session_state.last_saved_po = (saved_record, verified_items)
                st.success("✅ Purchase Order successfully saved to database!")
            except Exception as e:
                st.error(f"Database Insertion Error: {str(e)}")

        # Download & Preview Section
        if st.session_state.role == "Procurement Manager" and (st.session_state.last_saved_po or len(verified_items) > 0):
            if st.session_state.last_saved_po:
                active_po = po_meta.copy()
                active_po.update(st.session_state.last_saved_po[0])
                active_items = st.session_state.last_saved_po[1]
            else:
                active_po = po_meta
                active_items = verified_items
            
            pdf_bytes = generate_po_pdf(active_po, active_items)
            html_doc = generate_po_html(active_po, active_items)

            with b2:
                st.download_button(
                    label="📥 Download Official A4 Purchase Order PDF",
                    data=pdf_bytes,
                    file_name=f"Purchase_Order_{po_num}.pdf",
                    mime="application/pdf",
                    width='stretch'
                )
                
            with st.expander("👁️ View Live A4 Document Preview (HTML)", expanded=False):
                st.components.v1.html(html_doc, height=750, scrolling=True)


# ==============================================================================
# TAB 2: ORDER HISTORY DASHBOARD
# ==============================================================================
if st.session_state.role != "Procurement Manager":
    st.stop()

with tab_order_history:
    st.markdown('<div class="section-title">Purchase Orders Tracking & History</div>', unsafe_allow_html=True)
    st.caption("All purchase orders persisted in Supabase database for audit review, spend tracking, and PDF retrieval.")

    try:
        order_history = db.get_purchase_orders()
        if order_history and len(order_history) > 0:
            df_history = pd.DataFrame(order_history)
            
            # Summary KPI Cards
            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Total POs Issued", len(df_history))
            with k2:
                total_spend = df_history["grand_total"].sum() if "grand_total" in df_history.columns else 0.0
                st.metric("Total Spend", f"${total_spend:,.2f}")
            with k3:
                avg_spend = df_history["grand_total"].mean() if "grand_total" in df_history.columns else 0.0
                st.metric("Average PO Value", f"${avg_spend:,.2f}")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # Search & Filter
            s1, s2 = st.columns([3, 1])
            with s1:
                search_po = st.text_input("🔍 Search by Vendor or PO Number", value="")
            with s2:
                statuses = ["All Statuses"] + sorted(list(set(df_history["status"].dropna().tolist()))) if "status" in df_history.columns else ["All Statuses"]
                filter_status = st.selectbox("Status Filter", statuses)

            filtered_history = order_history
            if search_po:
                filtered_history = [p for p in filtered_history if (search_po.lower() in p.get("po_number", "").lower() or search_po.lower() in p.get("vendor_name", "").lower())]
            if filter_status != "All Statuses":
                filtered_history = [p for p in filtered_history if p.get("status") == filter_status]

            st.dataframe(filtered_history, width='stretch', hide_index=True)
            
            if st.session_state.role == "Procurement Manager":
                st.markdown("---")
                st.subheader("🛠️ Manager Actions: Pending Approvals")
                pending_pos = [p for p in order_history if p.get("status", "").lower() == "pending"]
                if pending_pos:
                    po_opts = {p.get("po_number"): p.get("id") for p in pending_pos}
                    sel_po = st.selectbox("Select Pending PO to Approve", list(po_opts.keys()))
                    if st.button("✅ Approve Selected PO", type="primary"):
                        if db.update_po_status(po_opts[sel_po], "Approved"):
                            st.success(f"{sel_po} Approved!")
                            st.rerun()
                else:
                    st.caption("No pending POs require approval.")

                st.markdown("---")
                with st.expander("🔧 Debug: View Raw Database JSON"):
                    st.json(order_history)
        else:
            st.info("No Purchase Orders found in Supabase database yet. Create your first PO in Tab 1!")
    except Exception as e:
        if "getaddrinfo failed" in str(e) or "Max retries exceeded" in str(e):
            st.error("🚨 **Database Connection Failed:** Unable to reach Supabase. Please check your internet connection, verify your `SUPABASE_URL` in secrets, and ensure your Supabase project is active/not paused.")
            st.warning(f"🔧 **RAW ERROR LOG:** {str(e)}")
        else:
            st.error(f"Database Retrieval Error: {str(e)}")

# ==============================================================================
# TAB 3: RECEIPT HISTORY & ANALYSIS
# ==============================================================================
with tab_analytics:
    if st.session_state.role != "Procurement Manager":
        st.error("🚫 Access Denied. Only Procurement Managers can view Receipt History & Analysis.")
    else:
        st.markdown('<div class="section-title">Receipt History & Analysis</div>', unsafe_allow_html=True)
        try:
            order_history = db.get_purchase_orders()
        except Exception as e:
            order_history = []
            st.error(f"Failed to fetch analytics data: {e}")
        
        if not order_history:
            st.info("No data available for analysis. Create a PO first!")
        else:
            df_receipts = pd.DataFrame(order_history)
            df_receipts.rename(columns={"po_number": "Reference Number", "po_date": "Date", "vendor_name": "Vendor Name", "grand_total": "Grand Total", "status": "Status"}, inplace=True)
            df_receipts['Date'] = pd.to_datetime(df_receipts['Date'])
            df_receipts = df_receipts.sort_values('Date', ascending=False)
            
            # Reorder columns to ensure Reference Number is first
            cols = ["Reference Number", "Date", "Vendor Name", "Grand Total", "Status"]
            df_receipts = df_receipts[cols]
            
            # Receipt Analysis Metrics
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Receipts Processed", len(df_receipts))
            with c2:
                st.metric("Cumulative Historical Spend", f"${df_receipts['Grand Total'].sum():,.2f}")
            with c3:
                st.metric("Average Receipt Value", f"${df_receipts['Grand Total'].mean():,.2f}")
                
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 📋 Historical Receipt Ledger")
            st.dataframe(df_receipts, width='stretch', hide_index=True)

            st.markdown("---")
            st.markdown("### 📈 Historical Spend Analysis")
            
            df_spend = df_receipts.groupby("Vendor Name", as_index=False)["Grand Total"].sum().sort_values("Grand Total", ascending=False)
            
            fig = px.bar(
                df_spend, x='Vendor Name', y='Grand Total', 
                title="Total Spend per Vendor",
                template="plotly_dark",
                text_auto='.2s'
            )
            fig.update_traces(marker_color='#dc2626', textfont_color='white', textposition='outside')
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)', 
                xaxis_title="Vendor Name", 
                yaxis_title="Total Spend ($)",
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, width='stretch')
