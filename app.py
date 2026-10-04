from flask import Flask, request, jsonify, send_file, render_template
import sqlite3
import qrcode
import io
import uuid
from datetime import datetime

app = Flask(__name__)

DATABASE = "database.db"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT UNIQUE NOT NULL,
            product_name TEXT NOT NULL,
            farmer_name TEXT NOT NULL,
            quantity TEXT NOT NULL,
            harvest_date TEXT NOT NULL,
            current_stage TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            person_name TEXT,
            location TEXT,
            notes TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def home():

    return """
    <!DOCTYPE html>

    <html>

    <head>

        <title>AgriChain</title>

        <style>

            body {
                font-family: Arial;
                text-align: center;
                background: #f1f8e9;
                padding: 50px;
            }

            h1 {
                color: #2e7d32;
            }

            a {
                display: inline-block;
                padding: 15px 25px;
                margin: 10px;
                background: #2e7d32;
                color: white;
                text-decoration: none;
                border-radius: 8px;
            }

        </style>

    </head>

    <body>

        <h1>🌾 AgriChain</h1>

        <h3>
            Farm-to-Customer Tracking System
        </h3>

        <a href="/farmer">
            👨‍🌾 Farmer Portal
        </a>

        <a href="/customer">
            👤 Customer Portal
        </a>

    </body>

    </html>
    """


# ---------------- FARMER PAGE ----------------

@app.route("/farmer")
def farmer():

    return send_file("farmer/farmer.html")


@app.route("/farmer/farmer.css")
def farmer_css():

    return send_file("farmer/farmer.css")


# ---------------- CUSTOMER PAGE ----------------

@app.route("/customer")
def customer():

    return send_file("customer/customer.html")


@app.route("/customer/customer.css")
def customer_css():

    return send_file("customer/customer.css")


# ---------------- ADD PRODUCT ----------------

@app.route("/add_product", methods=["POST"])
def add_product():

    data = request.json

    product_name = data.get("product_name")
    farmer_name = data.get("farmer_name")
    quantity = data.get("quantity")
    harvest_date = data.get("harvest_date")

    if not product_name or not farmer_name or not quantity or not harvest_date:

        return jsonify({
            "success": False,
            "message": "Please fill all fields."
        })


    product_id = "AGR-" + uuid.uuid4().hex[:8].upper()

    current_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    conn = get_db()


    conn.execute("""
        INSERT INTO products
        (
            product_id,
            product_name,
            farmer_name,
            quantity,
            harvest_date,
            current_stage,
            created_at
        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (

        product_id,
        product_name,
        farmer_name,
        quantity,
        harvest_date,
        "Farmer",
        current_time

    ))


    conn.execute("""
        INSERT INTO tracking
        (
            product_id,
            stage,
            person_name,
            location,
            notes,
            timestamp
        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (

        product_id,
        "Farmer",
        farmer_name,
        "Farm",
        "Product harvested and registered.",
        current_time

    ))


    conn.commit()
    conn.close()


    return jsonify({

        "success": True,

        "message":
        "Product added successfully!",

        "product_id":
        product_id

    })


# ---------------- UPDATE JOURNEY ----------------

@app.route("/update_stage", methods=["POST"])
def update_stage():

    data = request.json

    product_id = data.get("product_id")
    stage = data.get("stage")
    person_name = data.get("person_name")
    location = data.get("location")
    notes = data.get("notes")


    if not product_id or not stage:

        return jsonify({

            "success": False,

            "message":
            "Product ID and stage are required."

        })


    conn = get_db()


    product = conn.execute("""

        SELECT *
        FROM products
        WHERE product_id = ?

    """, (product_id,)).fetchone()


    if not product:

        conn.close()

        return jsonify({

            "success": False,

            "message":
            "Product not found."

        })


    current_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    conn.execute("""

        UPDATE products

        SET current_stage = ?

        WHERE product_id = ?

    """, (

        stage,
        product_id

    ))


    conn.execute("""

        INSERT INTO tracking
        (
            product_id,
            stage,
            person_name,
            location,
            notes,
            timestamp
        )

        VALUES (?, ?, ?, ?, ?, ?)

    """, (

        product_id,
        stage,
        person_name,
        location,
        notes,
        current_time

    ))


    conn.commit()
    conn.close()


    return jsonify({

        "success": True,

        "message":
        "Product journey updated successfully!"

    })


# ---------------- ALL PRODUCTS ----------------

@app.route("/products")
def products():

    conn = get_db()


    products = conn.execute("""

        SELECT *
        FROM products
        ORDER BY id DESC

    """).fetchall()


    conn.close()


    result = []


    for product in products:

        result.append(dict(product))


    return jsonify(result)


# ---------------- SINGLE PRODUCT ----------------

@app.route("/product/<product_id>")
def get_product(product_id):

    conn = get_db()


    product = conn.execute("""

        SELECT *
        FROM products
        WHERE product_id = ?

    """, (product_id,)).fetchone()


    if not product:

        conn.close()

        return jsonify({

            "success": False,

            "message":
            "Product not found."

        })


    tracking = conn.execute("""

        SELECT *
        FROM tracking
        WHERE product_id = ?

        ORDER BY id ASC

    """, (product_id,)).fetchall()


    conn.close()


    return jsonify({

        "success": True,

        "product": dict(product),

        "tracking":
        [dict(item) for item in tracking]

    })


# ---------------- TRACKING PAGE ----------------

@app.route("/track/<product_id>")
def track_page(product_id):

    return render_template(
        "track.html",
        product_id=product_id
    )


# ---------------- QR CODE ----------------

@app.route("/qr/<product_id>")
def generate_qr(product_id):

    url = (
        request.host_url.rstrip("/")
        + "/track/"
        + product_id
    )


    qr = qrcode.make(url)


    img = io.BytesIO()

    qr.save(img, format="PNG")

    img.seek(0)


    return send_file(
        img,
        mimetype="image/png"
    )


# ---------------- START APPLICATION ----------------

if __name__ == "__main__":

    init_db()

    print()
    print("----------------------------------")
    print("🌾 AgriChain Started")
    print("Open: http://127.0.0.1:5000")
    print("----------------------------------")
    print()

    app.run(debug=True)