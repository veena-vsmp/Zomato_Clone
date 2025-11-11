import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('foodapp.db')
    c = conn.cursor()

    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        coin_balance INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        menu_item_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS coin_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        transaction_type TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    c.execute("SELECT COUNT(*) FROM restaurants")
    if c.fetchone()[0] == 0:
        restaurants = [
            ('Spice Junction', 'Indian', 4.5, '30-40 min', 'Downtown', 'https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=400', 'Authentic Indian cuisine with a modern twist'),
            ('Pizza Paradise', 'Italian', 4.3, '25-35 min', 'Central Square', 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400', 'Wood-fired pizzas and Italian favorites'),
            ('Dragon Wok', 'Chinese', 4.6, '35-45 min', 'Chinatown', 'https://images.unsplash.com/photo-1525755662778-989d0524087e?w=400', 'Traditional Chinese delicacies'),
            ('Burger Barn', 'American', 4.2, '20-30 min', 'West End', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400', 'Gourmet burgers and milkshakes'),
            ('Sushi Master', 'Japanese', 4.7, '40-50 min', 'Harbor View', 'https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?w=400', 'Fresh sushi and Japanese specialties'),
            ('Taco Fiesta', 'Mexican', 4.4, '25-35 min', 'Mission District', 'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=400', 'Authentic Mexican street food'),
            ('Pasta House', 'Italian', 4.3, '30-40 min', 'Little Italy', 'https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=400', 'Homemade pasta and Italian classics'),
            ('Curry Palace', 'Indian', 4.5, '35-45 min', 'East Side', 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=400', 'Rich curries and tandoori dishes')
        ]
        c.executemany('INSERT INTO restaurants (name, cuisine, rating, delivery_time, location, image_url, description) VALUES (?, ?, ?, ?, ?, ?, ?)', restaurants)
        
        menu_items = [
            (1, 'Butter Chicken', 'Tender chicken in creamy tomato sauce', 12.99, 'Main Course', 0, 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=300'),
            (1, 'Paneer Tikka', 'Grilled cottage cheese with spices', 10.99, 'Appetizer', 1, 'https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=300'),
            (1, 'Biryani', 'Aromatic rice with spices and meat', 14.99, 'Main Course', 0, 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=300'),
            (1, 'Naan Bread', 'Fresh oven-baked flatbread', 3.99, 'Sides', 1, 'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=300'),
            
            (2, 'Margherita Pizza', 'Classic tomato and mozzarella', 11.99, 'Pizza', 1, 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=300'),
            (2, 'Pepperoni Pizza', 'Spicy pepperoni with cheese', 13.99, 'Pizza', 0, 'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=300'),
            (2, 'Lasagna', 'Layered pasta with meat sauce', 12.99, 'Main Course', 0, 'https://images.unsplash.com/photo-1574894709920-11b28e7367e3?w=300'),
            (2, 'Garlic Bread', 'Toasted bread with garlic butter', 4.99, 'Sides', 1, 'https://images.unsplash.com/photo-1573140401552-388e29d6f4f7?w=300'),
            
            (3, 'Kung Pao Chicken', 'Spicy chicken with peanuts', 13.99, 'Main Course', 0, 'https://images.unsplash.com/photo-1585032226651-759b368d7246?w=300'),
            (3, 'Fried Rice', 'Wok-tossed rice with vegetables', 9.99, 'Main Course', 1, 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=300'),
            (3, 'Spring Rolls', 'Crispy vegetable rolls', 6.99, 'Appetizer', 1, 'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=300'),
            (3, 'Sweet and Sour Pork', 'Crispy pork in tangy sauce', 14.99, 'Main Course', 0, 'https://images.unsplash.com/photo-1580959375944-0be939f5118c?w=300'),
            
            (4, 'Classic Burger', 'Beef patty with lettuce and tomato', 9.99, 'Burgers', 0, 'https://images.unsplash.com/photo-1550547660-d9450f859349?w=300'),
            (4, 'Cheese Burger', 'Double cheese beef burger', 11.99, 'Burgers', 0, 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=300'),
            (4, 'Veggie Burger', 'Plant-based patty with veggies', 10.99, 'Burgers', 1, 'https://images.unsplash.com/photo-1520072959219-c595dc870360?w=300'),
            (4, 'French Fries', 'Crispy golden fries', 4.99, 'Sides', 1, 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=300'),
            
            (5, 'California Roll', 'Crab, avocado, and cucumber', 10.99, 'Sushi', 0, 'https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?w=300'),
            (5, 'Salmon Sashimi', 'Fresh raw salmon slices', 14.99, 'Sashimi', 0, 'https://images.unsplash.com/photo-1580822184713-fc5400e7fe10?w=300'),
            (5, 'Vegetable Tempura', 'Crispy battered vegetables', 8.99, 'Appetizer', 1, 'https://images.unsplash.com/photo-1541529086526-db283c563270?w=300'),
            (5, 'Miso Soup', 'Traditional Japanese soup', 3.99, 'Sides', 1, 'https://images.unsplash.com/photo-1606787619643-c7c68e2ff39e?w=300'),
            
            (6, 'Beef Tacos', 'Seasoned beef in soft tortillas', 9.99, 'Tacos', 0, 'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=300'),
            (6, 'Chicken Quesadilla', 'Grilled chicken and cheese', 11.99, 'Main Course', 0, 'https://images.unsplash.com/photo-1618040996337-2d674b5a4df8?w=300'),
            (6, 'Guacamole & Chips', 'Fresh guacamole with tortilla chips', 6.99, 'Appetizer', 1, 'https://images.unsplash.com/photo-1534939268839-e9a39bd3d6c6?w=300'),
            (6, 'Churros', 'Sweet fried pastry with chocolate', 5.99, 'Dessert', 1, 'https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=300'),
            
            (7, 'Fettuccine Alfredo', 'Creamy pasta with parmesan', 12.99, 'Pasta', 1, 'https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=300'),
            (7, 'Spaghetti Carbonara', 'Pasta with bacon and egg sauce', 13.99, 'Pasta', 0, 'https://images.unsplash.com/photo-1612874742237-6526221588e3?w=300'),
            (7, 'Ravioli', 'Cheese-filled pasta with sauce', 11.99, 'Pasta', 1, 'https://images.unsplash.com/photo-1587740908075-9e245070dfaa?w=300'),
            (7, 'Tiramisu', 'Classic Italian dessert', 6.99, 'Dessert', 1, 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=300'),
            
            (8, 'Chicken Tikka Masala', 'Grilled chicken in spiced gravy', 13.99, 'Main Course', 0, 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=300'),
            (8, 'Palak Paneer', 'Spinach curry with cottage cheese', 11.99, 'Main Course', 1, 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=300'),
            (8, 'Samosa', 'Crispy pastry with spiced filling', 5.99, 'Appetizer', 1, 'https://images.unsplash.com/photo-1601050690117-f8c7c4cf64a3?w=300'),
            (8, 'Mango Lassi', 'Sweet yogurt drink with mango', 4.99, 'Beverages', 1, 'https://images.unsplash.com/photo-1618164435735-413d3b066c9a?w=300')
        ]
        
        c.executemany('INSERT INTO menu_items (restaurant_id, name, description, price, category, is_veg, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)', menu_items)
        conn.commit()
    conn.close()
    print("Database initialized successfully!")



    def add_coins_to_user(user_id, amount, description="Coins earned"):
        conn = sqlite3.connect('foodapp.db')
        c = conn.cursor()

    # Update wallet balance
    c.execute("UPDATE users SET coin_balance = coin_balance + ? WHERE id = ?", (amount, user_id))

    # Add transaction record
    c.execute('''INSERT INTO coin_transactions (user_id, amount, transaction_type, description)
                 VALUES (?, ?, ?, ?)''',
              (user_id, amount, "earn", description))

    conn.commit()
    conn.close()
    print(f"✅ {amount} coins added to user {user_id}'s wallet!")

if __name__ == '__main__':
    init_db()

    add_coins_to_user(1, 100, "Welcome bonus for signup")
