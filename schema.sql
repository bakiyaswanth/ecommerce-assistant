-- Database schema setup for the AI E-commerce Assistant (Indian Context)
-- 
-- 1. Create the pgvector extension and the AI natural language extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS alloydb_ai_nl;

-- 2. Create the main products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    price NUMERIC(10, 2),
    embedding vector(768)
);

-- 3. Insert mock product data (Indian Products & INR prices)
INSERT INTO products (name, description, category, price) VALUES
('Boat Rockerz 450 Wireless Headphones', 'On-ear wireless headphones with up to 15 hours playback, 40mm drivers, and dual pairing.', 'Electronics', 1499.00),
('Noise ColorFit Pro 4 Smartwatch', 'Advanced Bluetooth calling smartwatch with 1.72-inch display and 100 sports modes.', 'Electronics', 2999.00),
('Yoga Mat with Carrying Strap', 'Extra thick 6mm anti-slip yoga mat. Eco-friendly TPE material.', 'Sports', 899.00),
('Milton Thermosteel Water Bottle', '1000ml vacuum insulated stainless steel water flask. Keeps water hot or cold for 24 hours.', 'Home', 950.00),
('Cotton Kurta Set for Men', 'Elegant maroon pure cotton kurta pajama set. Perfect for festive occasions and Diwali.', 'Clothing', 1299.00),
('Puma Running Shoes', 'Lightweight mesh running shoes with responsive foam cushioning for everyday jogging.', 'Sports', 2499.00),
('Prestige Induction Cooktop', '1900-Watt induction cooktop with Indian menu options, aerodynamic cooling, and push buttons.', 'Home', 2150.00),
('Samsung Galaxy M14 5G', '5G smartphone with 50MP triple camera, 6000mAh battery, and 6GB RAM.', 'Electronics', 12490.00),
('Wipro Garnet Smart LED Bulb', '9-Watt Wi-Fi smart LED bulb, 16 million colors, compatible with Alexa and Google Assistant.', 'Home', 649.00),
('Nivia Football (Size 5)', 'Standard size 5 football, water resistant, durable for outdoor play in Indian grounds.', 'Sports', 450.00),
('Cello Opalware Dinner Set', '18-piece elegant white and blue floral pattern dinner set. Microwave safe.', 'Home', 1199.00),
('Fastrack Aviator Sunglasses', 'Stylish metal frame UV protected aviator sunglasses for men.', 'Accessories', 899.00),
('JBL Flip 6 Bluetooth Speaker', 'Portable waterproof Bluetooth speaker with deep bass and 12 hours playtime.', 'Electronics', 8999.00),
('Biba Women Printed Kurti', 'Cotton printed straight kurti for everyday ethnic wear.', 'Clothing', 799.00),
('Vector X Resistance Bands', 'Set of 5 heavy duty resistance bands from 10lbs to 50lbs for home workouts.', 'Sports', 1249.00);

-- Generate embeddings using the local model (Google assumes it's available in AlloyDB)
UPDATE products 
SET embedding = embedding('textembedding-gecko@003', name || ' - ' || description);

-- 4. Register the table configuration for AlloyDB AI NL
-- Call the function to let AlloyDB AI know this table exists and how to query it
SELECT alloydb_ai_nl.create_config(
  config_id => 'ecommerce_cfg',
  schema_id => 'public',
  table_names => ARRAY['products']
);
