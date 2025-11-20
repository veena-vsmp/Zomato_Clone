from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, make_response
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import shutil
import pdfkit
import json
import re
from datetime import datetime

# OpenAI official client
from openai import OpenAI
from datetime import datetime, timedelta, timezone

# App config
app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
# Helpers
# --------------------------
# Helper: wkhtmltopdf auto-detect
# --------------------------
def get_pdfkit_config():
    """
    Automatically detect wkhtmltopdf path on Windows, Linux, or Mac.
    Falls back to common installation paths and raises FileNotFoundError if not found.
    """
    # If wkhtmltopdf is in PATH
    wkhtml_path = shutil.which("wkhtmltopdf")
    if wkhtml_path:
        return pdfkit.configuration(wkhtmltopdf=wkhtml_path)

    # Windows common install paths
    windows_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    if os.path.exists(windows_path):
        return pdfkit.configuration(wkhtmltopdf=windows_path)

    windows_path2 = r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe"
    if os.path.exists(windows_path2):
        return pdfkit.configuration(wkhtmltopdf=windows_path2)

    # Common Linux/macOS paths
    linux_path = "/usr/bin/wkhtmltopdf"
    if os.path.exists(linux_path):
        return pdfkit.configuration(wkhtmltopdf=linux_path)

    mac_path = "/usr/local/bin/wkhtmltopdf"
    if os.path.exists(mac_path):
        return pdfkit.configuration(wkhtmltopdf=mac_path)

    # Nothing found
    raise FileNotFoundError("wkhtmltopdf not found! Install from: https://wkhtmltopdf.org/downloads/")



# DB helper & user model

def get_db():
    conn = sqlite3.connect('foodapp.db')
    conn.row_factory = sqlite3.Row
    return conn

# --------------------------
# User model
# --------------------------
class User(UserMixin):
    def __init__(self, id, username, email, coin_balance):
        self.id = id
        self.username = username
        self.email = email
        self.coin_balance = coin_balance

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    try:
        u = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    finally:
        conn.close()
    if u:
        return User(u['id'], u['username'], u['email'], u['coin_balance'])
    return None
# Context processors
@app.context_processor
def inject_cart():
    cart = session.get('cart', {})
    total_quantity = sum(cart.values()) if cart else 0
    return dict(cart_total_quantity=total_quantity)

@app.context_processor
def inject_user():
    if current_user.is_authenticated:
        conn = get_db()
        try:
            u = conn.execute('SELECT coin_balance FROM users WHERE id = ?', (current_user.id,)).fetchone()
        finally:
            conn.close()
        return {'user_coin_balance': u['coin_balance'] if u else 0}
    return {'user_coin_balance': 0}
# --------------------------
# Public & Auth routes
# --------------------------
@app.route('/')
def index():
    conn = get_db()
    try:
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
    finally:
        conn.close()
    return render_template('index.html', restaurants=restaurants, cuisines=cuisines,
                           search_query=search_query, cuisine_filter=cuisine_filter)

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

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
        try:
            existing = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email)).fetchone()
            if existing:
                flash('Username or email already exists!', 'error')
                return redirect(url_for('register'))
            hashed = generate_password_hash(password)
            cur = conn.execute('INSERT INTO users (username, email, password, coin_balance) VALUES (?, ?, ?, ?)',
                               (username, email, hashed, 100))
            conn.commit()
            uid = cur.lastrowid
            conn.execute('INSERT INTO coin_transactions (user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?)',
                         (uid, 100, 'earned', 'Welcome bonus'))
            conn.commit()
        finally:
            conn.close()

        flash('Registration successful! You received 100 welcome coins!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        try:
            u = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', (identifier, identifier)).fetchone()
        finally:
            conn.close()

        if u and check_password_hash(u['password'], password):
            user_obj = User(u['id'], u['username'], u['email'], u['coin_balance'])
            login_user(user_obj)
            if u['email'] == "veenamalipatil279@gmail.com":
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# Admin
# --------------------------
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    admin = {"name": "Veenamalipatilr", "email": "veenamalipatil279@gmail.com", "role": "Administrator"}
    conn = get_db()
    try:
        c = conn.cursor()
        total_restaurants = c.execute('SELECT COUNT(*) FROM restaurants').fetchone()[0]
        total_orders = c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
        total_revenue = c.execute('SELECT COALESCE(SUM(final_amount), 0) FROM orders').fetchone()[0]

        top = c.execute('''SELECT r.name, COUNT(o.id) AS total_orders, COALESCE(SUM(o.final_amount),0) AS total_revenue
                           FROM orders o JOIN restaurants r ON o.restaurant_id = r.id
                           GROUP BY o.restaurant_id ORDER BY total_orders DESC LIMIT 1''').fetchone()
        top_name = top['name'] if top else "No orders yet"
        top_orders = top['total_orders'] if top else 0
        top_revenue = top['total_revenue'] if top else 0.0

        restaurants = c.execute('SELECT id, name, cuisine, location FROM restaurants ORDER BY name').fetchall()
        restaurant_data = []
        for r in restaurants:
            stats = c.execute('SELECT COUNT(*) AS total_orders, COALESCE(SUM(final_amount),0) AS total_revenue FROM orders WHERE restaurant_id = ?', (r['id'],)).fetchone()
            recent = c.execute('''SELECT o.id AS order_id, u.username, o.total_amount, o.final_amount, o.status, o.created_at
                                  FROM orders o JOIN users u ON o.user_id = u.id
                                  WHERE o.restaurant_id = ? ORDER BY o.created_at DESC LIMIT 5''', (r['id'],)).fetchall()
            restaurant_data.append({
                'id': r['id'], 'name': r['name'], 'cuisine': r['cuisine'], 'location': r['location'],
                'total_orders': stats['total_orders'], 'total_revenue': stats['total_revenue'], 'recent_orders': recent
            })
    finally:
        conn.close()

    return render_template('admin_dashboard.html', admin=admin, restaurants=restaurant_data,
                           total_restaurants=total_restaurants, total_orders=total_orders,
                           total_revenue=total_revenue, top_restaurant_name=top_name,
                           top_restaurant_orders=top_orders, top_restaurant_revenue=top_revenue)

# --------------------------
# Restaurant & cart
# --------------------------

@app.route('/restaurant/<int:restaurant_id>')
def restaurant(restaurant_id):
    conn = get_db()
    try:
        r = conn.execute('SELECT * FROM restaurants WHERE id = ?', (restaurant_id,)).fetchone()
        menu_items = conn.execute('SELECT * FROM menu_items WHERE restaurant_id = ? ORDER BY category', (restaurant_id,)).fetchall()
    finally:
        conn.close()

    if not r:
        if not restaurant:
            flash('Restaurant not found!', 'error')
            return redirect(url_for('index'))
        menu_by_category = {}
        for item in menu_items:
            menu_by_category.setdefault(item['category'], []).append(item)

    return render_template('restaurant.html', restaurant=r, menu_by_category=menu_by_category)

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))
    if 'cart' not in session:
        session['cart'] = {}
    cart = session['cart']
    cart[item_id] = cart.get(item_id, 0) + quantity
    session['cart'] = cart
    flash('Item added to cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
    cart_items = []
    total = 0
    if 'cart' in session and session['cart']:
        conn = get_db()
        try:
            for item_id, quantity in session['cart'].items():
                item = conn.execute('''SELECT m.*, r.name as restaurant_name
                                       FROM menu_items m JOIN restaurants r ON m.restaurant_id = r.id
                                       WHERE m.id = ?''', (item_id,)).fetchone()
                if item:
                    subtotal = item['price'] * quantity
                    cart_items.append({
                        'id': item['id'], 'name': item['name'], 'restaurant': item['restaurant_name'],
                        'price': item['price'], 'quantity': quantity, 'subtotal': subtotal
                    })
                    total += subtotal
        finally:
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
                cart.pop(item_id, None)
        elif action == 'remove':
            cart.pop(item_id, None)
        session['cart'] = cart
    return redirect(url_for('cart'))


# Checkout & order placement
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        cart_items = []
        total = 0
        restaurant_id = None

        for item_id, quantity in session['cart'].items():
            item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
            if item:
                if restaurant_id is None:
                    restaurant_id = item['restaurant_id']
                subtotal = item['price'] * quantity
                cart_items.append({
                    'id': item['id'], 'name': item['name'], 'price': item['price'],
                    'quantity': quantity, 'subtotal': subtotal
                })
                total += subtotal

        cgst = total * 0.09
        sgst = total * 0.09
        gst_total = cgst + sgst
        total_incl_gst = total + gst_total

        user = conn.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()

        if request.method == 'POST':
            address = request.form.get('address')
            coins_to_use = int(request.form.get('coins_to_use', 0))

            if coins_to_use > user['coin_balance']:
                flash('Insufficient coin balance!', 'error')
                return redirect(url_for('checkout'))

            max_allowed = min(user['coin_balance'], int(total_incl_gst * 0.10 * 100))
            final_amount = total_incl_gst - (coins_to_use / 100)

            cur = conn.execute('''INSERT INTO orders
                                  (user_id, restaurant_id, total_amount, coins_used, final_amount, status, delivery_address, created_at)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                               (current_user.id, restaurant_id, total_incl_gst, coins_to_use, final_amount, 'Confirmed', address, datetime.utcnow().isoformat()))
            order_id = cur.lastrowid

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
            session.pop('cart', None)
            flash(f'Order placed successfully! You earned {cashback_coins} cashback coins!', 'success')
            return redirect(url_for('orders'))
    finally:
        conn.close()

    return render_template('checkout.html', cart_items=cart_items, total=total, cgst=cgst, sgst=sgst,
                           total_incl_gst=total_incl_gst, coin_balance=user['coin_balance'])

# --------------------------
# Orders listing
#orders listing
@app.route('/orders')
@login_required
def orders():
    conn = get_db()
    try:
        orders = conn.execute('''SELECT o.*, r.name as restaurant_name
                                 FROM orders o JOIN restaurants r ON o.restaurant_id = r.id
                                 WHERE o.user_id = ? ORDER BY o.created_at DESC''',
                              (current_user.id,)).fetchall()
    finally:
        conn.close()
    return render_template('orders.html', orders=orders)

# --------------------------
# Games
# ------------------------
    orders = [dict(o) for o in orders]
    for o in orders:
        o["created_at"] = format_order_time(o["created_at"])
    return render_template('orders.html', orders=orders)

# Games & game API
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
    score = int(data.get('score', 0))

    if game_type == 'memory':
        coins_earned = min(score * 5, 50)
    elif game_type == 'spin':
        coins_earned = score
    elif game_type == 'quiz':
        coins_earned = score * 10
    elif game_type == 'catch':
        coins_earned = min(score, 100)
    else:
        coins_earned = 0

    if coins_earned <= 0:
        return jsonify({'success': False, 'message': 'No coins earned'}), 400

    conn = get_db()
    try:
        conn.execute('UPDATE users SET coin_balance = coin_balance + ? WHERE id = ?', (coins_earned, current_user.id))
        conn.execute('INSERT INTO coin_transactions (user_id, amount, transaction_type, description) VALUES (?, ?, ?, ?)',
                     (current_user.id, coins_earned, 'earned', f'Earned from {game_type} game'))
        conn.commit()
        user = conn.execute('SELECT coin_balance FROM users WHERE id = ?', (current_user.id,)).fetchone()
        new_balance = user['coin_balance']
    finally:
        conn.close()
    session['user_coin_balance'] = new_balance
    return jsonify({
        'success': True,
        'coins_earned': coins_earned,
        'new_balance': new_balance,
        'message': f'You earned {coins_earned} coins!'
    })

# --------------------------
# Wallet & vendor register
@app.route('/wallet')
@login_required
def wallet():
    conn = get_db()
    try:
        transactions = conn.execute('SELECT * FROM coin_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 50', (current_user.id,)).fetchall()
        user = conn.execute('SELECT coin_balance FROM users WHERE id = ?', (current_user.id,)).fetchone()
    finally:
        conn.close()
    return render_template('wallet.html', transactions=transactions, coin_balance=user['coin_balance'])

@app.route('/vendor_register', methods=['GET', 'POST'])
def vendor_register():
    if request.method == 'POST':
        data = (
            request.form.get('restaurant_name'),
            request.form.get('owner_name'),
            request.form.get('email'),
            request.form.get('phone'),
            request.form.get('address'),
            request.form.get('cuisine_type')
        )
        conn = get_db()
        try:
            c = conn.cursor()
            c.execute('INSERT INTO vendors (restaurant_name, owner_name, email, phone, address, cuisine_type) VALUES (?, ?, ?, ?, ?, ?)', data)
            conn.commit()
            flash('Your restaurant has been submitted for admin approval!', 'success')
        except sqlite3.IntegrityError:
            flash('Email already registered!', 'danger')
        finally:
            conn.close()
        return redirect(url_for('vendor_register'))
    return render_template('vendor_register.html')

# --------------------------
# Invoice view + download
# --------------------------
# Invoice: view + download (clean)
@app.route('/invoice/<int:order_id>')
@login_required
def invoice(order_id):
    conn = get_db()
    try:
        order = conn.execute('''SELECT o.*, r.name AS restaurant_name, u.username, u.email
                                FROM orders o JOIN restaurants r ON o.restaurant_id = r.id
                                JOIN users u ON o.user_id = u.id
                                WHERE o.id = ? AND o.user_id = ?''',
                             (order_id, current_user.id)).fetchone()
        if not order:
            flash('Order not found!', 'error')
            return redirect(url_for('orders'))

        items = conn.execute('''SELECT m.name, oi.quantity, oi.price, (oi.quantity * oi.price) AS subtotal
                                FROM order_items oi JOIN menu_items m ON oi.menu_item_id = m.id
                                WHERE oi.order_id = ?''', (order_id,)).fetchall()

        total = sum(it['subtotal'] for it in items)
        order = conn.execute('''
            SELECT o.*, r.name AS restaurant_name, u.username, u.email
            FROM orders o
            JOIN restaurants r ON o.restaurant_id = r.id
            JOIN users u ON o.user_id = u.id
            WHERE o.id = ? AND o.user_id = ?
        ''', (order_id, current_user.id)).fetchone()
        if not order:
            flash('Order not found!', 'error')
            return redirect(url_for('orders'))
        items = conn.execute('''
            SELECT m.name, oi.quantity, oi.price, (oi.quantity * oi.price) AS subtotal
            FROM order_items oi
            JOIN menu_items m ON oi.menu_item_id = m.id
            WHERE oi.order_id = ?
        ''', (order_id,)).fetchall()
        # Calculate totals
        total = sum(item['subtotal'] for item in items)
        cgst = total * 0.09
        sgst = total * 0.09
        gst_total = cgst + sgst
        total_incl_gst = total + gst_total
        final_amount = total_incl_gst - order['coins_used']

        return render_template('invoice.html', order=order, items=items, total=total,
                               cgst=cgst, sgst=sgst, gst_total=gst_total,
                               total_incl_gst=total_incl_gst, final_amount=final_amount, mode="html")
        final_amount = total_incl_gst - (order['coins_used'] /100)
        return render_template('invoice.html',
                               order=order,
                               items=items,
                               total=total,
                               cgst=cgst,
                               sgst=sgst,
                               gst_total=gst_total,
                               total_incl_gst=total_incl_gst,
                               final_amount=final_amount,
                               mode="html")
    finally:
        conn.close()

@app.route('/invoice/<int:order_id>/download')
@login_required
def invoice_download(order_id):
    conn = get_db()
    try:
        order = conn.execute('''SELECT o.*, r.name AS restaurant_name, u.username, u.email
                                FROM orders o JOIN restaurants r ON o.restaurant_id = r.id
                                JOIN users u ON o.user_id = u.id
                                WHERE o.id = ? AND o.user_id = ?''', (order_id, current_user.id)).fetchone()
        if not order:
            flash('Order not found!', 'error')
            return redirect(url_for('orders'))

        items = conn.execute('''SELECT m.name, oi.quantity, oi.price, (oi.quantity * oi.price) AS subtotal
                                FROM order_items oi JOIN menu_items m ON oi.menu_item_id = m.id
                                WHERE oi.order_id = ?''', (order_id,)).fetchall()

        total = sum(it['subtotal'] for it in items)
        order = conn.execute('''
            SELECT o.*, r.name AS restaurant_name, u.username, u.email
            FROM orders o
            JOIN restaurants r ON o.restaurant_id = r.id
            JOIN users u ON o.user_id = u.id
            WHERE o.id = ? AND o.user_id = ?
        ''', (order_id, current_user.id)).fetchone()
        if not order:
            flash('Order not found!', 'error')
            return redirect(url_for('orders'))
        items = conn.execute('''
            SELECT m.name, oi.quantity, oi.price, (oi.quantity * oi.price) AS subtotal
            FROM order_items oi
            JOIN menu_items m ON oi.menu_item_id = m.id
            WHERE oi.order_id = ?
        ''', (order_id,)).fetchall()
        total = sum(item['subtotal'] for item in items)
        cgst = total * 0.09
        sgst = total * 0.09
        gst_total = cgst + sgst
        total_incl_gst = total + gst_total
        final_amount = total_incl_gst - order['coins_used']

        html = render_template('invoice.html', order=order, items=items, total=total,
                               cgst=cgst, sgst=sgst, gst_total=gst_total,
                               total_incl_gst=total_incl_gst, final_amount=final_amount, mode="pdf")

        final_amount = total_incl_gst - (order['coins_used'] / 100)
        html = render_template('invoice.html',
                               order=order,
                               items=items,
                               total=total,
                               cgst=cgst,
                               sgst=sgst,
                               gst_total=gst_total,
                               total_incl_gst=total_incl_gst,
                               final_amount=final_amount,
                               mode="pdf")
        # PDF generation 
        config = get_pdfkit_config()
        pdf = pdfkit.from_string(html, False, configuration=config)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=invoice_{order_id}.pdf'
        return response
    finally:
        conn.close()

@app.route('/invoice-pdf/<int:order_id>')
@login_required
def invoice_pdf_compat(order_id):
    return redirect(url_for('invoice_download', order_id=order_id))

def is_admin():
    return current_user.is_authenticated and current_user.username == "veenamalipatil"

# Admin dashboard 
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.username != "veenamalipatil":
        flash("Unauthorized access!", "error")
        return redirect(url_for("index"))

    conn = get_db()
    conn.row_factory = sqlite3.Row  # Allows dict-style access

    # Fetch all data from correct tables
    users = conn.execute("SELECT * FROM users").fetchall()
    restaurants = conn.execute("SELECT * FROM restaurants").fetchall()
    menus = conn.execute("SELECT * FROM menu_items").fetchall()

    # Orders must join users + restaurants for displaying names
    orders = conn.execute('''
        SELECT 
            o.id,
            u.username AS username,
            r.name AS restaurant_name,
            o.final_amount AS total,
            o.created_at AS order_date
        FROM orders o
        JOIN users u ON o.user_id = u.id
        JOIN restaurants r ON o.restaurant_id = r.id
    ''').fetchall()

    # Dashboard summary counts
    users_count = len(users)
    restaurant_count = len(restaurants)
    total_orders = len(orders)

    # Calculate total revenue
    total_revenue = conn.execute("SELECT SUM(final_amount) FROM orders").fetchone()[0]
    total_revenue = total_revenue if total_revenue else 0

    return render_template(
        "admin_dashboard.html",
        users=users,
        restaurants=restaurants,
        menu=menus,
        orders=orders,
        users_count=users_count,
        restaurant_count=restaurant_count,
        total_orders=total_orders,
        total_revenue=total_revenue
    )


@app.route('/edit_vendor/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_vendor(id):
    if not is_admin():
        flash("Unauthorized access!", "error")
        return redirect(url_for('index'))

    conn = get_db()
    vendor = conn.execute("SELECT * FROM restaurants WHERE id = ?", (id,)).fetchone()

    if request.method == "POST":
        name = request.form['name']
        location = request.form['location']
        email = request.form['email']

        conn.execute("""
            UPDATE restaurants 
            SET name = ?, location = ?, email = ?
            WHERE id = ?
        """, (name, location, email, id))

        conn.commit()
        flash("Vendor updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template("edit_vendor.html", vendor=vendor)

@app.route('/delete_vendor/<int:id>', methods=['POST'])
@login_required
def delete_vendor(id):
    if not is_admin():
        flash("Unauthorized access!", "error")
        return redirect(url_for('index'))

    conn = get_db()
    conn.execute("DELETE FROM restaurants WHERE id = ?", (id,))
    conn.commit()

    flash("Vendor deleted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_user/<int:id>')
@login_required
def delete_user(id):
    if current_user.username != "veenamalipatil":
        flash("Unauthorized", "error")
        return redirect(url_for("index"))

    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (id,))
    conn.commit()
    flash("User deleted!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route('/add_menu', methods=['GET', 'POST'])
@login_required
def add_menu():
    conn = get_db()

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        restaurant_id = request.form['restaurant_id']

        conn.execute("""
            INSERT INTO menu_items (name, price, restaurant_id)
            VALUES (?, ?, ?)
        """, (name, price, restaurant_id))

        conn.commit()
        flash("Menu item added successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    restaurants = conn.execute("SELECT id, name FROM restaurants").fetchall()
    
    return render_template("add_menu.html", restaurants=restaurants)


# Run
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002, debug=True)
