import sqlite3
import random

def create_db():
    conn = sqlite3.connect('amazon_test.db')
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS amazon_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT,
        category TEXT,
        price REAL,
        rating REAL,
        stock_quantity INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS amazon_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        customer_id INTEGER,
        sale_date TEXT,
        quantity INTEGER,
        total_price REAL,
        FOREIGN KEY (product_id) REFERENCES amazon_products(id)
    )
    ''')

    # Generate 100+ test products
    categories = ["Electronics", "Books", "Home & Kitchen", "Toys", "Clothing"]
    products = []
    for i in range(120):
        name = f"Amazon Product {i+1}"
        category = random.choice(categories)
        price = round(random.uniform(5.0, 500.0), 2)
        rating = round(random.uniform(3.0, 5.0), 1)
        stock = random.randint(0, 1000)
        products.append((name, category, price, rating, stock))

    cursor.executemany('''
    INSERT INTO amazon_products (product_name, category, price, rating, stock_quantity)
    VALUES (?, ?, ?, ?, ?)
    ''', products)

    # Generate 150 test sales
    sales = []
    for i in range(150):
        product_id = random.randint(1, 120)
        customer_id = random.randint(1001, 1050)
        day = random.randint(1, 28)
        month = random.randint(1, 12)
        sale_date = f"2026-{month:02d}-{day:02d}"
        quantity = random.randint(1, 5)
        # We don't lookup price for total_price in this mock, just random
        total_price = round(quantity * random.uniform(5.0, 500.0), 2)
        sales.append((product_id, customer_id, sale_date, quantity, total_price))

    cursor.executemany('''
    INSERT INTO amazon_sales (product_id, customer_id, sale_date, quantity, total_price)
    VALUES (?, ?, ?, ?, ?)
    ''', sales)

    conn.commit()
    print(f"Inserted {len(products)} products and {len(sales)} sales into amazon_test.db")
    conn.close()

if __name__ == '__main__':
    create_db()
