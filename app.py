from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

class User(UserMixin):
    def __init__(self, id, username, email, coin_balance):
        self.id = id
        self.username = username
        self.email = email
        self.coin_balance = coin_balance

def get_db():
    conn = sqlite3.connect('foodapp.db')
    conn.row_factory = sqlite3.Row
    return conn

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['email'], user['coin_balance'])
    return None

@app.route('/')
def index():
    conn = get_db()
    
    search_query = request.args.get('search', '')
    cuisine_filter = request.args.get('cuisine', '')
    
    query = 'SELECT * FROM restaurants WHERE 1=1'
    params = []
    
    if search_query:
        query += ' AND (name LIKE ? OR cuisine LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%'])
    
    if cuisine_filter:
        query += ' AND cuisine = ?'
        params.append(cuisine_filter)
    
    query += ' ORDER BY rating DESC'
    
    restaurants = conn.execute(query, params).fetchall()
    cuisines = conn.execute('SELECT DISTINCT cuisine FROM restaurants ORDER BY cuisine').fetchall()
    conn.close()
    
    return render_template('index.html', restaurants=restaurants, cuisines=cuisines, 
                         search_query=search_query, cuisine_filter=cuisine_filter)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            flash('All fields are required!', 'error')
            return redirect(url_for('register'))
        
        conn = get_db()
        existing_user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', 
                                    (username, email)).fetchone()
        
        if existing_user:
            flash('Username or email already exists!', 'error')
            conn.close()
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, email, password, coin_balance) VALUES (?, ?, ?, ?)',
                    (username, email, hashed_password, 100))
        conn.commit()
        
        conn.execute('INSERT INTO coin_transactions (user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?)',
                    (conn.execute('SELECT last_insert_rowid()').fetchone()[0], 100, 'earned', 'Welcome bonus'))
        conn.commit()
        conn.close()
        
        flash('Registration successful! You received 100 welcome coins!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['email'], user['coin_balance'])
            login_user(user_obj)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/restaurant/<int:restaurant_id>')
def restaurant(restaurant_id):
    conn = get_db()
    restaurant = conn.execute('SELECT * FROM restaurants WHERE id = ?', (restaurant_id,)).fetchone()
    menu_items = conn.execute('SELECT * FROM menu_items WHERE restaurant_id = ? ORDER BY category', 
                             (restaurant_id,)).fetchall()
    conn.close()
    
    if not restaurant:
        flash('Restaurant not found!', 'error')
        return redirect(url_for('index'))
    
    menu_by_category = {}
    for item in menu_items:
        category = item['category']
        if category not in menu_by_category:
            menu_by_category[category] = []
        menu_by_category[category].append(item)
    
    return render_template('restaurant.html', restaurant=restaurant, menu_by_category=menu_by_category)

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))
    
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    if item_id in cart:
        cart[item_id] += quantity
    else:
        cart[item_id] = quantity
    
    session['cart'] = cart
    flash('Item added to cart!', 'success')
    return redirect(request.referrer)

@app.route('/cart')
@login_required
def cart():
    cart_items = []
    total = 0
    
    if 'cart' in session and session['cart']:
        conn = get_db()
        for item_id, quantity in session['cart'].items():
            item = conn.execute('SELECT m.*, r.name as restaurant_name FROM menu_items m JOIN restaurants r ON m.restaurant_id = r.id WHERE m.id = ?', 
                              (item_id,)).fetchone()
            if item:
                cart_items.append({
                    'id': item['id'],
                    'name': item['name'],
                    'restaurant': item['restaurant_name'],
                    'price': item['price'],
                    'quantity': quantity,
                    'subtotal': item['price'] * quantity
                })
                total += item['price'] * quantity
        conn.close()
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    item_id = request.form.get('item_id')
    action = request.form.get('action')
    
    if 'cart' in session:
        cart = session['cart']
        if action == 'increase':
            cart[item_id] = cart.get(item_id, 0) + 1
        elif action == 'decrease':
            if cart.get(item_id, 0) > 1:
                cart[item_id] -= 1
            else:
                del cart[item_id]
        elif action == 'remove':
            if item_id in cart:
                del cart[item_id]
        
        session['cart'] = cart
    
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        address = request.form.get('address')
        coins_to_use = int(request.form.get('coins_to_use', 0))
        
        conn = get_db()
        cart_items = []
        total = 0
        restaurant_id = None
        
        for item_id, quantity in session['cart'].items():
            item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
            if item:
                if restaurant_id is None:
                    restaurant_id = item['restaurant_id']
                cart_items.append({
                    'id': item['id'],
                    'price': item['price'],
                    'quantity': quantity
                })
                total += item['price'] * quantity
        
        user = conn.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()
        
        if coins_to_use > user['coin_balance']:
            flash('Insufficient coin balance!', 'error')
            conn.close()
            return redirect(url_for('checkout'))
        
        if coins_to_use > total:
            coins_to_use = int(total)
        
        final_amount = total - coins_to_use
        
        cursor = conn.execute('''INSERT INTO orders (user_id, restaurant_id, total_amount, coins_used, final_amount, status, delivery_address) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                             (current_user.id, restaurant_id, total, coins_to_use, final_amount, 'Confirmed', address))
        order_id = cursor.lastrowid
        
        for item in cart_items:
            conn.execute('INSERT INTO order_items (order_id, menu_item_id, quantity, price) VALUES (?, ?, ?, ?)',
                        (order_id, item['id'], item['quantity'], item['price']))
        
        new_balance = user['coin_balance'] - coins_to_use
        conn.execute('UPDATE users SET coin_balance = ? WHERE id = ?', (new_balance, current_user.id))
        
        if coins_to_use > 0:
            conn.execute('INSERT INTO coin_transactions (user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?)',
                        (current_user.id, -coins_to_use, 'spent', f'Used on order #{order_id}'))
        
        cashback_coins = int(total * 0.05)
        conn.execute('UPDATE users SET coin_balance = coin_balance + ? WHERE id = ?', (cashback_coins, current_user.id))
        conn.execute('INSERT INTO coin_transactions (user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?)',
                    (current_user.id, cashback_coins, 'earned', f'Cashback from order #{order_id}'))
        
        conn.commit()
        conn.close()
        
        session.pop('cart', None)
        flash(f'Order placed successfully! You earned {cashback_coins} cashback coins!', 'success')
        return redirect(url_for('orders'))
    
    cart_items = []
    total = 0
    
    conn = get_db()
    for item_id, quantity in session['cart'].items():
        item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
        if item:
            cart_items.append({
                'name': item['name'],
                'price': item['price'],
                'quantity': quantity,
                'subtotal': item['price'] * quantity
            })
            total += item['price'] * quantity
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()
    conn.close()
    
    return render_template('checkout.html', cart_items=cart_items, total=total, coin_balance=user['coin_balance'])

@app.route('/orders')
@login_required
def orders():
    conn = get_db()
    orders = conn.execute('''SELECT o.*, r.name as restaurant_name 
                           FROM orders o 
                           JOIN restaurants r ON o.restaurant_id = r.id 
                           WHERE o.user_id = ? 
                           ORDER BY o.created_at DESC''', (current_user.id,)).fetchall()
    conn.close()
    
    return render_template('orders.html', orders=orders)

@app.route('/games')
@login_required
def games():
    return render_template('games.html')

@app.route('/games/memory')
@login_required
def memory():
    return render_template('memory.html')

@app.route('/game/catch')
@login_required
def catch():
    return render_template('catch.html')

@app.route('/game/runner')
@login_required
def runner():
    return render_template('runner.html')


@app.route('/api/game/complete', methods=['POST'])
@login_required
def complete_game():
    data = request.get_json()
    game_type = data.get('game_type')
    score = int(data.get('score', 0))  # ensure integer
    
    # 🧮 Define earning logic
    if game_type == 'memory':
        coins_earned = min(score * 5, 50)  # Max 50
    elif game_type == 'spin':
        coins_earned = score
    elif game_type == 'quiz':
        coins_earned = score * 10
    elif game_type == 'catch':
        coins_earned = min(score, 100)  # e.g., max 100 coins for catch game
    else:
        coins_earned = 0

    if coins_earned <= 0:
        return jsonify({'success': False, 'message': 'No coins earned'}), 400

    conn = get_db()
    conn.execute('UPDATE users SET coin_balance = coin_balance + ? WHERE id = ?', 
                 (coins_earned, current_user.id))
    conn.execute('INSERT INTO coin_transactions (user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?)',
                 (current_user.id, coins_earned, 'earned', f'Earned from {game_type} game'))
    conn.commit()
    
    user = conn.execute('SELECT coin_balance FROM users WHERE id = ?', (current_user.id,)).fetchone()
    new_balance = user['coin_balance']
    conn.close()

    # 🔄 Update session coin balance in real time
    session['user_coin_balance'] = new_balance

    return jsonify({
        'success': True,
        'coins_earned': coins_earned,
        'new_balance': new_balance,
        'message': f'You earned {coins_earned} coins!'
    })


@app.route('/wallet')
@login_required
def wallet():
    conn = get_db()
    transactions = conn.execute('''SELECT * FROM coin_transactions 
                                  WHERE user_id = ? 
                                  ORDER BY created_at DESC LIMIT 50''', (current_user.id,)).fetchall()
    user = conn.execute('SELECT coin_balance FROM users WHERE id = ?', (current_user.id,)).fetchone()
    conn.close()
    
    return render_template('wallet.html', transactions=transactions, coin_balance=user['coin_balance'])

@app.context_processor
def inject_user():
    if current_user.is_authenticated:
        conn = get_db()
        user = conn.execute('SELECT coin_balance FROM users WHERE id = ?', (current_user.id,)).fetchone()
        conn.close()
        return {'user_coin_balance': user['coin_balance'] if user else 0}
    return {'user_coin_balance': 0}

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002, debug=True)
