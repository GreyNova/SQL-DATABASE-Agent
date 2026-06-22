import os
import sqlite3
import random
from datetime import datetime, timedelta

# Set random seed for reproducibility
random.seed(42)

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sales.db")
print(f"Creating complex SQLite database at: {db_path}")

if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Enable foreign keys
cur.execute("PRAGMA foreign_keys = ON;")

# 1. Create Tables
cur.executescript("""
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    price REAL NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    average_rating REAL NOT NULL DEFAULT 0.0 CHECK (average_rating BETWEEN 0.0 AND 5.0),
    review_count INTEGER NOT NULL DEFAULT 0 CHECK (review_count >= 0),
    description TEXT
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    order_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_amount REAL NOT NULL DEFAULT 0.0 CHECK (total_amount >= 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','paid','shipped','delivered','cancelled','refunded'))
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price REAL NOT NULL CHECK (price >= 0)
);

CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    review_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_products_cat     ON products(category_id);
CREATE INDEX idx_products_rating  ON products(average_rating);
CREATE INDEX idx_products_price   ON products(price);
CREATE INDEX idx_users_city       ON users(city);
CREATE INDEX idx_orders_user      ON orders(user_id);
CREATE INDEX idx_orders_date      ON orders(order_date);
CREATE INDEX idx_orders_status    ON orders(status);
CREATE INDEX idx_items_order      ON order_items(order_id);
CREATE INDEX idx_items_product    ON order_items(product_id);
CREATE INDEX idx_reviews_product  ON reviews(product_id);
""")

# 2. Seed Categories
categories = [
    "Electronics",
    "Books",
    "Home & Kitchen",
    "Clothing & Accessories",
    "Beauty & Personal Care",
    "Sports & Outdoors"
]
for cat in categories:
    cur.execute("INSERT INTO categories (name) VALUES (?)", (cat,))

# Retrieve category IDs
cur.execute("SELECT id, name FROM categories")
cat_map = {name: id for id, name in cur.fetchall()}

# 3. Seed Users (50 users)
indian_names = [
    "Aarav Sharma", "Diya Patel", "Vihaan Mehta", "Ananya Reddy", "Arjun Nair",
    "Sara Khan", "Kabir Singh", "Isha Gupta", "Rohan Verma", "Meera Iyer",
    "Aditya Joshi", "Kavya Rao", "Siddharth Bose", "Riya Sen", "Aryan Malhotra",
    "Anika Choudhury", "Krishna Kumar", "Pooja Hegde", "Sai Charan", "Tanvi Bhat",
    "Rahul Dravid", "Neha Kakkar", "Devendra Fadnavis", "Praniti Shinde", "Abhishek Bachchan",
    "Priyanka Chopra", "Virat Kohli", "Anushka Sharma", "Rohit Sharma", "Jasprit Bumrah",
    "Hardik Pandya", "Shikhar Dhawan", "Shreya Ghoshal", "Arijit Singh", "Diljit Dosanjh",
    "Ranbir Kapoor", "Alia Bhatt", "Deepika Padukone", "Ranveer Singh", "Hrithik Roshan",
    "Katrina Kaif", "Akshay Kumar", "Kareena Kapoor", "Saif Ali Khan", "Varun Dhawan",
    "Shraddha Kapoor", "Sanjay Dutt", "Sunny Deol", "Bobby Deol", "Amitabh Bachchan"
]
cities = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow"]

users_seeded = []
for i, name in enumerate(indian_names):
    email = f"{name.lower().replace(' ', '.')}@example.com"
    city = cities[i % len(cities)]
    created_at = (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO users (name, email, city, created_at) VALUES (?, ?, ?, ?)", (name, email, city, created_at))
    users_seeded.append((i + 1, created_at))

# 4. Seed Products (120 products, 20 per category)
adjectives = ["Wireless", "Premium", "Ultra", "Smart", "Classic", "Portable", "Professional", "Ergonomic", "Eco-friendly", "Heavy-duty"]
nouns = {
    "Electronics": ["Adapter", "Router", "Power Bank", "Tablet", "Stylus", "HDMI Cable", "Switch", "Speaker", "Earphones", "Mouse Pad", "Smartwatch", "Keyboard", "Mouse", "Monitor", "Webcam", "SSD", "Fast Charger", "Microphone", "VR Headset", "Dongle"],
    "Books": ["Guide", "History", "Novel", "Biography", "Manual", "Workbook", "Anthology", "Essay", "Handbook", "Journal", "Mystery", "Thriller", "Sci-Fi", "Poetry", "Self-Help", "Encyclopedia", "Atlas", "Cookbook", "Memoir", "Fantasy"],
    "Home & Kitchen": ["Organizer", "Storage Bin", "Knife Set", "Cutting Board", "Food Container", "Mug Set", "Wine Opener", "Trash Can", "Hanger Set", "Desk Fan", "Air Fryer", "Blender", "Coffee Maker", "Kettle", "Vacuum Cleaner", "Scale", "Toaster", "Slow Cooker", "Rice Cooker", "Toaster Oven"],
    "Clothing & Accessories": ["Scarf", "Gloves", "Beanie", "Tie", "Pajama Set", "Raincoat", "Sunglasses", "Cap", "Belt", "Socks", "T-Shirt", "Jacket", "Jeans", "Hoodie", "Dress", "Wallet", "Backpack", "Sweater", "Sneakers", "Shorts"],
    "Beauty & Personal Care": ["Facial Spray", "Eye Cream", "Makeup Brush", "Nail Polish", "Hand Cream", "Cleansing Oil", "Perfume Spray", "Hair Gel", "Bath Bombs", "Soap Bar", "Moisturizer", "Face Wash", "Sunscreen", "Hair Serum", "Lip Balm", "Body Lotion", "Lipstick", "Face Mask", "Exfoliating Scrub", "Shampoo"],
    "Sports & Outdoors": ["Grip Strength", "Running Belt", "Exercise Ball", "Sweatband", "Ankle Weights", "Goggles", "Towel Quick-Dry", "Compass", "Flashlight", "Pocket Knife", "Yoga Mat", "Dumbbells", "Resistance Bands", "Water Bottle", "Tent", "Sleeping Bag", "Backpack 50L", "Jump Rope", "Helmet", "Sunglasses UV"]
}

product_id_counter = 1
products_seeded = []

for category_name, category_id in cat_map.items():
    category_nouns = nouns[category_name]
    for i in range(20):
        adj = adjectives[i % len(adjectives)]
        noun = category_nouns[i % len(category_nouns)]
        name = f"{adj} {noun}"
        
        # Determine pricing ranges by category
        if category_name == "Electronics":
            price = round(random.uniform(500.00, 25000.00), 2)
        elif category_name == "Clothing & Accessories" or category_name == "Sports & Outdoors":
            price = round(random.uniform(299.00, 5000.00), 2)
        elif category_name == "Home & Kitchen":
            price = round(random.uniform(199.00, 12000.00), 2)
        else: # Books, Beauty
            price = round(random.uniform(99.00, 2500.00), 2)
            
        stock = random.randint(5, 150)
        desc = f"High-quality {name.lower()} suitable for daily use. Part of our curated {category_name.lower()} collection."
        
        # Ratings will be populated dynamically after reviews are seeded, but set initial placeholders
        cur.execute(
            "INSERT INTO products (name, category_id, price, stock, average_rating, review_count, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, category_id, price, stock, 0.0, 0, desc)
        )
        products_seeded.append((product_id_counter, price, category_id))
        product_id_counter += 1

# 5. Seed Orders (150 orders)
order_statuses = ["delivered", "shipped", "paid", "pending", "cancelled", "refunded"]
order_seeded_ids = []

for i in range(150):
    user_id, user_created_at = random.choice(users_seeded)
    user_created_dt = datetime.strptime(user_created_at, "%Y-%m-%d %H:%M:%S")
    
    # Order date is after user creation
    order_date = (user_created_dt + timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d %H:%M:%S")
    status = random.choices(order_statuses, weights=[60, 15, 10, 8, 5, 2])[0]
    
    cur.execute(
        "INSERT INTO orders (user_id, order_date, status) VALUES (?, ?, ?)",
        (user_id, order_date, status)
    )
    order_seeded_ids.append(i + 1)

# 6. Seed Order Items (Randomly select 1-4 products per order)
for order_id in order_seeded_ids:
    items_count = random.randint(1, 4)
    selected_products = random.sample(products_seeded, items_count)
    total_amount = 0.0
    
    for prod_id, price, cat_id in selected_products:
        quantity = random.randint(1, 3)
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
            (order_id, prod_id, quantity, price)
        )
        total_amount += price * quantity
        
    # Update the order total_amount
    cur.execute("UPDATE orders SET total_amount = ? WHERE id = ?", (round(total_amount, 2), order_id))

# 7. Seed Reviews (200 reviews)
review_comments = {
    5: ["Absolutely amazing! Surpassed all expectations.", "Extremely satisfied. Premium quality and highly recommended.", "Perfect product, fast shipping, works flawlessly!", "Outstanding! Best in its class.", "Five stars! Worth every single rupee."],
    4: ["Very good product, works as advertised.", "Satisfied with the purchase. Good value for money.", "Great quality, but packaging could be slightly better.", "Solid build and performs well. Would buy again.", "Good purchase. Nice features."],
    3: ["Decent product. Not great but not bad either.", "Average quality. Serves the basic purpose.", "It works, but has some minor issues.", "Okay for the price, but don't expect premium performance.", "Mediocre. It is just average."],
    2: ["Disappointed. The quality is below average.", "Not worth the money. Broke within a week.", "Poor performance. Would not recommend.", "Felt very cheap. Disliked the build quality.", "Does not work well. Disappointed."],
    1: ["Horrible! Completely non-functional upon arrival.", "Worst purchase ever. A waste of money.", "Defective product. Returning immediately.", "Absolute garbage. Do not buy this!", "Extremely poor quality. Zero stars if possible."]
}

# Distribute reviews across products
reviews_count = 200
seeded_reviews_log = {} # product_id -> list of ratings

for _ in range(reviews_count):
    prod_id, _, _ = random.choice(products_seeded)
    user_id, _ = random.choice(users_seeded)
    
    # Biased towards positive reviews (Amazon shape)
    rating = random.choices([5, 4, 3, 2, 1], weights=[50, 25, 12, 8, 5])[0]
    comment = random.choice(review_comments[rating])
    
    # Review date
    review_date = (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 500))).strftime("%Y-%m-%d %H:%M:%S")
    
    cur.execute(
        "INSERT INTO reviews (product_id, user_id, rating, comment, review_date) VALUES (?, ?, ?, ?, ?)",
        (prod_id, user_id, rating, comment, review_date)
    )
    
    seeded_reviews_log.setdefault(prod_id, []).append(rating)

# 8. Update Product Average Ratings and Review Counts in products table
for prod_id, ratings_list in seeded_reviews_log.items():
    avg_rating = round(sum(ratings_list) / len(ratings_list), 2)
    rev_count = len(ratings_list)
    cur.execute(
        "UPDATE products SET average_rating = ?, review_count = ? WHERE id = ?",
        (avg_rating, rev_count, prod_id)
    )

# For any products that did not get any reviews, let's set a default standard rating to make search interesting
cur.execute("SELECT id FROM products WHERE review_count = 0")
no_rev_prods = [r[0] for r in cur.fetchall()]
for prod_id in no_rev_prods:
    # Assign some mock baseline rating/reviews
    baselines = [
        (4.2, 12, [5, 4, 4, 4, 5, 4, 3, 4, 5, 4, 4, 4]),
        (3.8, 8, [4, 4, 3, 3, 4, 5, 3, 4]),
        (4.6, 25, [5]*15 + [4]*8 + [3]*2),
        (3.5, 4, [4, 3, 3, 4])
    ]
    avg, count, ratings_list = random.choice(baselines)
    # Add actual reviews in DB
    for r in ratings_list:
        user_id = random.choice(users_seeded)[0]
        comment = random.choice(review_comments[r])
        review_date = (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 500))).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO reviews (product_id, user_id, rating, comment, review_date) VALUES (?, ?, ?, ?, ?)",
            (prod_id, user_id, r, comment, review_date)
        )
    cur.execute(
        "UPDATE products SET average_rating = ?, review_count = ? WHERE id = ?",
        (avg, count, prod_id)
    )

conn.commit()
conn.close()
print("SQLite Amazon-style database successfully created, structured and seeded with 100+ items!")
