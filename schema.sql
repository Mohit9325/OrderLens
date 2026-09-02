-- ============================================================
-- OrderLens - Supabase Database Schema & Master Catalog Data
-- ============================================================

-- 1. Master Product Catalog Table
CREATE TABLE IF NOT EXISTS public.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) DEFAULT 'General Hardware',
    unit_price NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    stock_quantity INT NOT NULL DEFAULT 0,
    unit VARCHAR(20) DEFAULT 'pcs',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Purchase Orders Metadata Table
CREATE TABLE IF NOT EXISTS public.purchase_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_number VARCHAR(100) UNIQUE NOT NULL,
    vendor_name VARCHAR(255) NOT NULL,
    vendor_address TEXT,
    vendor_email VARCHAR(255),
    vendor_phone VARCHAR(50),
    po_date DATE DEFAULT CURRENT_DATE,
    terms_and_conditions TEXT,
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(12, 2) DEFAULT 0.00,
    shipping_amount NUMERIC(12, 2) DEFAULT 0.00,
    grand_total NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(50) DEFAULT 'Approved', -- Draft, Approved, Sent, Completed, Cancelled
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Purchase Order Line Items Table
CREATE TABLE IF NOT EXISTS public.po_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_id UUID REFERENCES public.purchase_orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES public.products(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    catalog_rate NUMERIC(12, 2) DEFAULT 0.00,
    total_price NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes for Fast Query Performance
CREATE INDEX IF NOT EXISTS idx_products_name ON public.products (name);
CREATE INDEX IF NOT EXISTS idx_products_sku ON public.products (sku);
CREATE INDEX IF NOT EXISTS idx_po_number ON public.purchase_orders (po_number);
CREATE INDEX IF NOT EXISTS idx_po_items_po_id ON public.po_items (po_id);

-- Enable Row Level Security (RLS) & Public Access Policies for Demo Simplicity
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.po_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read on products" ON public.products FOR SELECT USING (true);
CREATE POLICY "Allow public insert on products" ON public.products FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update on products" ON public.products FOR UPDATE USING (true);

CREATE POLICY "Allow public select on purchase_orders" ON public.purchase_orders FOR SELECT USING (true);
CREATE POLICY "Allow public insert on purchase_orders" ON public.purchase_orders FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update on purchase_orders" ON public.purchase_orders FOR UPDATE USING (true);

CREATE POLICY "Allow public select on po_items" ON public.po_items FOR SELECT USING (true);
CREATE POLICY "Allow public insert on po_items" ON public.po_items FOR INSERT WITH CHECK (true);

-- Seed Initial Pre-populated Master Product Catalog
INSERT INTO public.products (sku, name, category, unit_price, stock_quantity, unit) VALUES
('GPU-H100-80G', 'NVIDIA H100 80GB SXM5 GPU Accelerator', 'AI Hardware', 32500.00, 14, 'pcs'),
('GPU-A100-80G', 'NVIDIA A100 80GB PCIe Gen4 GPU', 'AI Hardware', 14200.00, 25, 'pcs'),
('SRV-SYS-4U8G', 'Supermicro 4U 8-GPU AI Workstation Server', 'Servers', 45000.00, 8, 'units'),
('NET-OPT-400G', 'Mellanox Quantum-2 InfiniBand 400G Switch 64-Port', 'Networking', 18900.00, 12, 'units'),
('CBL-OPT-400G', '400G OSFP Active Optical Cable 5m', 'Cables', 480.00, 150, 'pcs'),
('TRX-100G-SR4', '100G QSFP28 SR4 Optical Transceiver Module', 'Transceivers', 220.00, 320, 'pcs'),
('MEM-DDR5-64G', 'Samsung 64GB DDR5-4800 ECC Registered RDIMM', 'Memory', 310.00, 400, 'pcs'),
('SSD-NVME-768', 'Micron 7450 PRO 7.68TB NVMe PCIe 4.0 Enterprise SSD', 'Storage', 850.00, 180, 'pcs'),
('PWR-PDU-30A', 'APC Switched Rack PDU 30A 208V 24-Outlet', 'Power', 1250.00, 45, 'units'),
('RCK-42U-DEEP', '42U Server Rack Cabinet Enclosure Deep 1200mm', 'Infrastructure', 1850.00, 18, 'units'),
('CPU-EPYC-9654', 'AMD EPYC 9654 96-Core 2.4GHz Processor', 'Processors', 11800.00, 30, 'pcs'),
('COOL-LIQ-360', 'Industrial Liquid Cooling Radiator System 360mm', 'Cooling', 950.00, 60, 'units')
ON CONFLICT (sku) DO UPDATE SET 
    unit_price = EXCLUDED.unit_price,
    stock_quantity = EXCLUDED.stock_quantity;
