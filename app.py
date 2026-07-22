from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from firebase_config import db
from datetime import datetime

app = Flask(__name__)

# -----------------------------
# Session Configuration
# -----------------------------
app.secret_key = "inventory_secret_key"

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# -----------------------------
# Home
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# Login
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["user"] = username
            return redirect(url_for("dashboard"))

        return "<h2>Invalid Username or Password</h2>"

    return render_template("login.html")


# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect(url_for("login"))


# -----------------------------
# Dashboard
# -----------------------------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    docs = db.collection("products").stream()

    products = []

    total_stock = 0

    categories = set()

    labels = []

    values = []

    for doc in docs:

        product = doc.to_dict()

        products.append(product)

        total_stock += product["quantity"]

        categories.add(product["category"])

        labels.append(product["product_name"])

        values.append(product["quantity"])

    return render_template(

        "dashboard.html",

        total_products=len(products),

        total_stock=total_stock,

        total_categories=len(categories),

        labels=labels,

        values=values

    )

# -----------------------------
# Inventory Page
# -----------------------------
@app.route("/inventory")
def inventory():
    return render_template("inventory.html")


# -----------------------------
# Add Product
# -----------------------------
@app.route("/add_product", methods=["GET", "POST"])
def add_product():

    if request.method == "POST":

        product = {

            "product_id": request.form["product_id"],
            "product_name": request.form["product_name"],
            "category": request.form["category"],
            "price": float(request.form["price"]),
            "quantity": int(request.form["quantity"])

        }

        db.collection("products").document(product["product_id"]).set(product)

        return "<h2>Product Added Successfully!</h2><br><a href='/dashboard'>Back to Dashboard</a>"

    return render_template("add_product.html")


# -----------------------------
# View Products
# -----------------------------
@app.route("/view_products")
def view_products():

    search = request.args.get("search")

    products = []

    docs = db.collection("products").stream()

    for doc in docs:

        product = doc.to_dict()

        if search:

            if (
                search.lower() in product["product_id"].lower()
                or search.lower() in product["product_name"].lower()
                or search.lower() in product["category"].lower()
            ):
                products.append(product)

        else:
            products.append(product)

    return render_template(
        "view_products.html",
        products=products
    )


# -----------------------------
# Edit Product
# -----------------------------
@app.route("/edit_product/<product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    doc_ref = db.collection("products").document(product_id)

    if request.method == "POST":

        doc_ref.update({

            "product_name": request.form["product_name"],
            "category": request.form["category"],
            "price": float(request.form["price"]),
            "quantity": int(request.form["quantity"])

        })

        return "<h2>Product Updated Successfully!</h2><br><a href='/view_products'>Back to Products</a>"

    product = doc_ref.get().to_dict()

    return render_template(
        "edit_product.html",
        product=product
    )


# -----------------------------
# Delete Product
# -----------------------------
@app.route("/delete_product/<product_id>")
def delete_product(product_id):

    db.collection("products").document(product_id).delete()

    return """
    <h2>Product Deleted Successfully!</h2>
    <br>
    <a href="/view_products">Back to Products</a>
    """


# -----------------------------
# Sales Module
# -----------------------------
@app.route("/sales", methods=["GET", "POST"])
def sales():

    if request.method == "POST":

        product_id = request.form["product_id"]
        quantity_sold = int(request.form["quantity"])

        doc_ref = db.collection("products").document(product_id)

        product = doc_ref.get().to_dict()

        if not product:
            return "<h2>Product Not Found!</h2>"

        if quantity_sold > product["quantity"]:
            return "<h2>Not Enough Stock!</h2>"

        # Reduce stock
        new_quantity = product["quantity"] - quantity_sold

        doc_ref.update({
            "quantity": new_quantity
        })

        # Save sale
        sale = {

            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "category": product["category"],
            "price": product["price"],
            "quantity_sold": quantity_sold,
            "total_amount": product["price"] * quantity_sold,
            "date": datetime.now().strftime("%d-%m-%Y"),
            "time": datetime.now().strftime("%H:%M:%S")

        }

        db.collection("sales").add(sale)

        return "<h2>Sale Completed Successfully!</h2><br><a href='/dashboard'>Back to Dashboard</a>"

    return render_template("sales.html")


# -----------------------------
# Run Flask
# -----------------------------
@app.route("/view_sales")
def view_sales():

    sales = []

    docs = db.collection("sales").stream()

    for doc in docs:

        sales.append(doc.to_dict())

    return render_template(
        "view_sales.html",
        sales=sales
    )
@app.route("/low_stock")
def low_stock():

    products = []

    docs = db.collection("products").stream()

    for doc in docs:

        product = doc.to_dict()

        if product["quantity"] <= 5:

            products.append(product)

    return render_template(
        "low_stock.html",
        products=products
    )
@app.route("/reports")
def reports():

    # Product statistics
    products = list(db.collection("products").stream())

    total_products = len(products)

    total_stock = 0

    categories = set()

    for doc in products:

        product = doc.to_dict()

        total_stock += product["quantity"]

        categories.add(product["category"])

    # Sales statistics
    sales_docs = list(db.collection("sales").stream())

    total_sold = 0

    total_sales = 0

    for doc in sales_docs:

        sale = doc.to_dict()

        total_sold += sale["quantity_sold"]

        total_sales += sale["total_amount"]

    return render_template(
        "reports.html",
        total_products=total_products,
        total_stock=total_stock,
        total_categories=len(categories),
        total_sold=total_sold,
        total_sales=total_sales
    )

if __name__ == "__main__":
    app.run(debug=True)