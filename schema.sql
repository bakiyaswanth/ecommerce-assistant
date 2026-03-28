-- ============================================
-- AI E-commerce Product Scout - Database Schema
-- Run this against your AlloyDB instance
-- ============================================

-- 1. Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS alloydb_ai_nl CASCADE;

-- 2. Create the products table
CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    category    TEXT,
    price       NUMERIC(10, 2) NOT NULL,
    embedding   VECTOR(768)
);

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products (price);
CREATE INDEX IF NOT EXISTS idx_products_name ON products USING GIN (to_tsvector('english', name));

-- 4. Create HNSW index on embeddings for vector similarity search
CREATE INDEX IF NOT EXISTS idx_products_embedding ON products
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 5. Register AlloyDB AI Natural Language configuration
SELECT alloydb_ai_nl.g_manage_configuration(
    'ecommerce_cfg',
    '{
        "tables": ["products"],
        "description": "E-commerce product catalog. The products table contains product names, detailed descriptions, categories (e.g. Electronics, Clothing, Home, Sports, Books), and prices in USD. Use this to answer questions about product availability, pricing, comparisons, and recommendations."
    }'
);

-- 6. Seed sample products (optional - for testing)
INSERT INTO products (name, description, category, price) VALUES
    ('SoundMax Pro Wireless Headphones', 'Premium over-ear wireless headphones with active noise cancellation, 40-hour battery life, and Hi-Res Audio support. Foldable design with memory foam ear cushions.', 'Electronics', 79.99),
    ('BassWave 200 Earbuds', 'True wireless earbuds with deep bass, IPX5 water resistance, touch controls, and 8-hour battery life per charge. Includes wireless charging case.', 'Electronics', 49.99),
    ('UltraView 27" 4K Monitor', 'Professional-grade 27-inch 4K IPS monitor with 99% sRGB coverage, USB-C connectivity, adjustable stand, and built-in speakers.', 'Electronics', 349.99),
    ('SwiftType Mechanical Keyboard', 'Compact 75% mechanical keyboard with hot-swappable switches, RGB backlighting, wireless Bluetooth 5.0, and aluminum frame.', 'Electronics', 89.99),
    ('CloudWalk Running Shoes', 'Lightweight running shoes with responsive foam cushioning, breathable mesh upper, and durable rubber outsole. Available in multiple colors.', 'Sports', 129.99),
    ('FlexFit Yoga Mat', 'Extra-thick 6mm yoga mat with non-slip texture, alignment markers, and carrying strap. Made from eco-friendly TPE material.', 'Sports', 34.99),
    ('PowerGrip Resistance Bands Set', 'Set of 5 resistance bands with varying tension levels (10-50 lbs). Includes door anchor, ankle straps, and carrying bag.', 'Sports', 24.99),
    ('Nordic Comfort Down Jacket', 'Insulated down jacket with 800-fill power, water-resistant shell, packable design, and adjustable hood. Rated to -20°F.', 'Clothing', 199.99),
    ('UrbanFlex Slim Jeans', 'Stretch denim slim-fit jeans with comfort waistband, reinforced stitching, and classic 5-pocket design. Machine washable.', 'Clothing', 59.99),
    ('CottonCloud T-Shirt Pack', 'Pack of 3 premium cotton crew-neck t-shirts. Pre-shrunk fabric, tagless design, and reinforced collar. Available in neutral colors.', 'Clothing', 29.99),
    ('SmartBrew Coffee Maker', 'Programmable 12-cup coffee maker with built-in grinder, thermal carafe, strength control, and auto-clean function.', 'Home', 149.99),
    ('AeroClean Robot Vacuum', 'Smart robot vacuum with LiDAR navigation, 2500Pa suction, mopping function, and app control. Works with Alexa and Google Home.', 'Home', 299.99),
    ('LumiGlow Smart LED Bulbs', 'Pack of 4 smart LED bulbs with 16 million colors, tunable white, voice control, and scheduling. Compatible with all major smart home platforms.', 'Home', 39.99),
    ('The Art of Clean Code', 'Comprehensive guide to writing maintainable, efficient, and elegant code. Covers design patterns, refactoring, and testing best practices.', 'Books', 32.99),
    ('Data Science from Scratch', 'Hands-on introduction to data science fundamentals using Python. Covers statistics, machine learning, NLP, and data visualization.', 'Books', 27.99),
    ('Mindful Living Journal', 'Guided journal with daily prompts for mindfulness, gratitude, and personal reflection. 365 pages with inspirational quotes.', 'Books', 18.99),
    ('ThermoSmart Water Bottle', 'Insulated stainless steel water bottle with LED temperature display, 24-hour cold / 12-hour hot retention, and leak-proof lid.', 'Sports', 29.99),
    ('ProCapture Action Camera', 'Waterproof action camera with 4K/60fps video, image stabilization, dual screens, and voice control. Includes mounting accessories.', 'Electronics', 199.99),
    ('ErgoMax Standing Desk', 'Electric height-adjustable standing desk with memory presets, cable management, and solid bamboo top. Supports up to 300 lbs.', 'Home', 449.99),
    ('SilkTouch Bedsheet Set', 'Queen-size 1800 thread count microfiber bedsheet set. Includes flat sheet, fitted sheet, and 4 pillowcases. Wrinkle-resistant and hypoallergenic.', 'Home', 44.99)
ON CONFLICT DO NOTHING;
