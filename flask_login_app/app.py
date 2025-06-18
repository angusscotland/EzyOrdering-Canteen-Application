from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DB_PATH = Path('users.db')

# Prices and display names for hot food items
ITEM_PRICES = {
    'sausage_roll': 4.50,
    'plain_pie': 5.50,
    'chicken_burger': 6.00,
    'nuggets': 4.00
}

PRODUCT_NAMES = {
    'sausage_roll': 'Plain Sausage Roll',
    'plain_pie': 'Plain Pie',
    'chicken_burger': 'Chicken Burger',
    'nuggets': 'Nuggets'
}

def init_db():
    if not DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE dates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    date TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS hot_food_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    item TEXT NOT NULL,
                    quantity INTEGER NOT NULL
                )
            ''')
            # Now completed_orders table with columns for each item qty and subtotal
            conn.execute('''
                CREATE TABLE IF NOT EXISTS completed_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    order_date TEXT NOT NULL,
                    sausage_roll_qty INTEGER DEFAULT 0,
                    sausage_roll_subtotal REAL DEFAULT 0,
                    plain_pie_qty INTEGER DEFAULT 0,
                    plain_pie_subtotal REAL DEFAULT 0,
                    chicken_burger_qty INTEGER DEFAULT 0,
                    chicken_burger_subtotal REAL DEFAULT 0,
                    nuggets_qty INTEGER DEFAULT 0,
                    nuggets_subtotal REAL DEFAULT 0,
                    total REAL NOT NULL
                )
            ''')

def save_order_to_db(username, order_items):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for item, qty in order_items.items():
            if qty > 0:
                cursor.execute(
                    "INSERT INTO hot_food_orders (username, item, quantity) VALUES (?, ?, ?)",
                    (username, item, qty)
                )
        conn.commit()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
            user = cursor.fetchone()
        if user:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Login failed. Check your username and password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.')
        elif len(password) < 8 or len(password) > 30:
            flash('Password must be between 8 and 30 characters.')
        elif not re.search(r'[A-Z]', password):
            flash('Password must contain at least one uppercase letter.')
        elif not re.search(r'[0-9]', password):
            flash('Password must contain at least one number.')
        elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('Password must contain at least one special character.')
        else:
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                flash('Registered successfully! You can now log in.')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Username already exists.')

    return render_template('register.html')

@app.route('/home')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully.')
    return redirect(url_for('login'))

@app.route('/select-date', methods=['GET', 'POST'])
def select_date():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        order_date = request.form['order_date']
        username = session['username']

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO dates (username, date) VALUES (?, ?)', (username, order_date))
            conn.commit()

        return redirect(url_for('food_selection'))

    return render_template('select_date.html')

@app.route('/food-selection')
def food_selection():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT item, SUM(quantity) FROM hot_food_orders WHERE username = ? GROUP BY item",
            (username,)
        )
        orders = cursor.fetchall()

        cursor.execute("SELECT date FROM dates WHERE username = ? ORDER BY id DESC LIMIT 1", (username,))
        date_row = cursor.fetchone()
        order_date = date_row[0] if date_row else None

    cart_items = []
    total = 0.0
    for item, qty in orders:
        price = ITEM_PRICES.get(item, 0)
        subtotal = round(qty * price, 2)
        total += subtotal
        cart_items.append({
            'name': PRODUCT_NAMES.get(item, item),
            'qty': qty,
            'price': price,
            'subtotal': subtotal
        })

    total = round(total, 2)

    return render_template('food_selection.html', cart_items=cart_items, total=total, order_date=order_date)

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM hot_food_orders WHERE username = ?", (username,))
        conn.commit()

    flash('Cart cleared successfully!')
    return redirect(url_for('food_selection'))

@app.route('/cold-food')
def cold_food():
    return "<h2>Cold Food Page - Coming Soon!</h2>"

@app.route('/drinks')
def drinks():
    return "<h2>Drinks Page - Coming Soon!</h2>"

@app.route('/desserts')
def desserts():
    return "<h2>Desserts Page - Coming Soon!</h2>"

@app.route('/hot_food', methods=['GET', 'POST'])
def hot_food():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        order_items = {}
        for item in ITEM_PRICES.keys():
            qty = int(request.form.get(f'{item}_qty', 0))
            if qty > 0:
                order_items[item] = qty

        save_order_to_db(session['username'], order_items)

        return redirect(url_for('food_selection'))

    return render_template('hot_food.html')

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT item, SUM(quantity) FROM hot_food_orders WHERE username = ? GROUP BY item",
            (username,)
        )
        orders = cursor.fetchall()

        cursor.execute("SELECT date FROM dates WHERE username = ? ORDER BY id DESC LIMIT 1", (username,))
        date_row = cursor.fetchone()
        order_date = date_row[0] if date_row else None

    # Build cart_items list for template
    cart_items = []
    total = 0.0
    quantities = {k:0 for k in ITEM_PRICES.keys()}
    subtotals = {k:0.0 for k in ITEM_PRICES.keys()}

    for item, qty in orders:
        price = ITEM_PRICES.get(item, 0)
        subtotal = round(qty * price, 2)
        total += subtotal
        quantities[item] = qty
        subtotals[item] = subtotal
        cart_items.append({
            'name': PRODUCT_NAMES.get(item, item),
            'qty': qty,
            'price': price,
            'subtotal': subtotal
        })

    total = round(total, 2)

    if request.method == 'POST':
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO completed_orders (
                    username, order_date,
                    sausage_roll_qty, sausage_roll_subtotal,
                    plain_pie_qty, plain_pie_subtotal,
                    chicken_burger_qty, chicken_burger_subtotal,
                    nuggets_qty, nuggets_subtotal,
                    total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                username, order_date,
                quantities['sausage_roll'], subtotals['sausage_roll'],
                quantities['plain_pie'], subtotals['plain_pie'],
                quantities['chicken_burger'], subtotals['chicken_burger'],
                quantities['nuggets'], subtotals['nuggets'],
                total
            ))
            # Clear hot_food_orders cart
            cursor.execute("DELETE FROM hot_food_orders WHERE username = ?", (username,))
            conn.commit()

        flash("Payment successful! Your order has been recorded.")
        return redirect(url_for('home'))

    return render_template('payment.html', cart_items=cart_items, total=total, order_date=order_date)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0')
