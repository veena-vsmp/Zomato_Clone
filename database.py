import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('foodapp.db')
    c = conn.cursor()

    #user table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        coin_balance INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    #vendor table
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_name TEXT NOT NULL,
        owner_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL,
        cuisine_type TEXT,
        status TEXT DEFAULT 'Pending',   -- Pending / Approved / Rejected
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    #restaurant table
    c.execute('''CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cuisine TEXT NOT NULL,
        rating REAL DEFAULT 0.0,
        delivery_time TEXT,
        location TEXT,
        image_url TEXT,
        description TEXT
    )''')
    
    #menu items table
    c.execute('''CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        category TEXT,
        is_veg BOOLEAN DEFAULT 1,
        image_url TEXT,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    )''')
    
    #orders table
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        restaurant_id INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        coins_used INTEGER DEFAULT 0,
        final_amount REAL NOT NULL,
        status TEXT DEFAULT 'Pending',
        delivery_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    )''')
    
    #order items table
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        menu_item_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
    )''')
    
    #coin transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS coin_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        transaction_type TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")


    #✅ Define inside init_db()
    def add_coins_to_user(user_id, amount, description="Coins earned"):
        conn = sqlite3.connect('foodapp.db')
        c = conn.cursor()

    # Update wallet balance
        c.execute("UPDATE users SET coin_balance = coin_balance + ? WHERE id = ?", (amount, user_id))

        # Add transaction record
        c.execute('''INSERT INTO coin_transactions (user_id, amount, transaction_type, description)
                    VALUES (?, ?, ?, ?)''',(user_id, amount, "earn", description))

        conn.commit()
        conn.close()

        
# ✅ Define outside init_db()
def add_coins_to_user(user_id, amount, description="Coins earned"):
    conn = sqlite3.connect('foodapp.db')
    c = conn.cursor()

    c.execute("UPDATE users SET coin_balance = coin_balance + ? WHERE id = ?", (amount, user_id))
    c.execute('''INSERT INTO coin_transactions (user_id, amount, transaction_type, description)
                VALUES (?, ?, ?, ?)''', (user_id, amount, "earn", description))

    conn.commit()
    conn.close()
    print(f"✅ {amount} coins added to user {user_id}'s wallet!")

if __name__ == '__main__':
    init_db()
    add_coins_to_user(1, 100, "Initial bonus coins")    
    