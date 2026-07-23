from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file
)

from firebase_config import db
from datetime import datetime
from openpyxl import Workbook

# PDF Invoice
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

import os

app = Flask(__name__)

# Secret key for Flask sessions
app.secret_key = "inventory_secret_key"


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

    # -----------------------------
    # Products
    # -----------------------------
    product_docs = db.collection("products").stream()

    products = []

    total_stock = 0
    inventory_value = 0
    low_stock = 0

    categories = set()

    # Category Count for Pie Chart
    category_count = {}

    labels = []
    values = []

    for doc in product_docs:

        product = doc.to_dict()

        products.append(product)

        total_stock += product["quantity"]

        inventory_value += product["price"] * product["quantity"]

        categories.add(product["category"])

        labels.append(product["product_name"])

        values.append(product["quantity"])

        # Low Stock Count
        if product["quantity"] <= 5:
            low_stock += 1

        # Category Count
        if product["category"] in category_count:
            category_count[product["category"]] += 1
        else:
            category_count[product["category"]] = 1

    # -----------------------------
    # Sales
    # -----------------------------
    sales_docs = db.collection("sales").stream()

    total_sales = 0

    recent_sales = []

    monthly_sales = {}

    # NEW
    top_products = {}

    for doc in sales_docs:

        sale = doc.to_dict()

        total_sales += sale["total_amount"]

        recent_sales.append(sale)

        # -----------------------------
        # Top Selling Products
        # -----------------------------
        if sale["product_name"] in top_products:

            top_products[sale["product_name"]] += sale["quantity_sold"]

        else:

            top_products[sale["product_name"]] = sale["quantity_sold"]

        # -----------------------------
        # Monthly Sales
        # -----------------------------
        month = datetime.strptime(
            sale["date"],
            "%d-%m-%Y"
        ).strftime("%b-%Y")

        if month in monthly_sales:

            monthly_sales[month] += sale["total_amount"]

        else:

            monthly_sales[month] = sale["total_amount"]

    # -----------------------------
    # Latest 5 Sales
    # -----------------------------
    recent_sales = sorted(

        recent_sales,

        key=lambda x: x["date"] + x["time"],

        reverse=True

    )[:5]

    # -----------------------------
    # Monthly Chart Data
    # -----------------------------
    monthly_labels = list(monthly_sales.keys())
    monthly_values = list(monthly_sales.values())

    # -----------------------------
    # Pie Chart Data
    # -----------------------------
    category_labels = list(category_count.keys())
    category_values = list(category_count.values())

    # -----------------------------
    # Top Selling Products
    # -----------------------------
    sorted_products = sorted(

        top_products.items(),

        key=lambda x: x[1],

        reverse=True

    )[:5]

    top_product_labels = []

    top_product_values = []

    for item in sorted_products:

        top_product_labels.append(item[0])

        top_product_values.append(item[1])

    # -----------------------------
    # Dashboard
    # -----------------------------
    return render_template(

        "dashboard.html",

        total_products=len(products),

        total_stock=total_stock,

        total_categories=len(categories),

        inventory_value=inventory_value,

        total_sales=total_sales,

        low_stock=low_stock,

        labels=labels,

        values=values,

        recent_sales=recent_sales,

        category_labels=category_labels,

        category_values=category_values,

        monthly_labels=monthly_labels,

        monthly_values=monthly_values,

        top_product_labels=top_product_labels,

        top_product_values=top_product_values

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

        product_id = request.form["product_id"]

        # Check if Product ID already exists
        doc_ref = db.collection("products").document(product_id)
        existing_product = doc_ref.get()

        if existing_product.exists:
            flash("Product ID already exists! Please use another ID.", "danger")
            return redirect(url_for("add_product"))

        product = {

            "product_id": product_id,
            "product_name": request.form["product_name"],
            "category": request.form["category"],
            "price": float(request.form["price"]),
            "quantity": int(request.form["quantity"])

        }

        # Save to Firebase
        doc_ref.set(product)

        flash("Product added successfully!", "success")

        return redirect(url_for("view_products"))

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

    # Load all products from Firebase
    products = []

    docs = db.collection("products").stream()

    for doc in docs:
        products.append(doc.to_dict())

    if request.method == "POST":

        product_id = request.form["product_id"]
        quantity_sold = int(request.form["quantity"])

        doc_ref = db.collection("products").document(product_id)

        product = doc_ref.get().to_dict()

        if not product:
            return "<h2>Product Not Found!</h2>"

        if quantity_sold > product["quantity"]:
            return "<h2>Not Enough Stock!</h2>"

        # -----------------------------
        # Reduce Stock
        # -----------------------------
        new_quantity = product["quantity"] - quantity_sold

        doc_ref.update({
            "quantity": new_quantity
        })

        # -----------------------------
        # Save Sale
        # -----------------------------
        sale = {

            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "category": product["category"],
            "price": product["price"],
            "quantity_sold": quantity_sold,
            "total_amount": product["price"] * quantity_sold,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S")

        }

        # Save sale to Firebase
        sale_ref = db.collection("sales").add(sale)

        # Get the generated Sale ID
        sale_id = sale_ref[1].id

        # Redirect to PDF Invoice
        return redirect(
            url_for(
                "invoice",
                sale_id=sale_id
            )
        )

    return render_template(
        "sales.html",
        products=products
    )

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

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # -----------------------------
    # Products
    # -----------------------------

    products = []

    docs = db.collection("products").stream()

    for doc in docs:
        products.append(doc.to_dict())

    total_products = len(products)

    total_stock = sum(p["quantity"] for p in products)

    total_categories = len(set(p["category"] for p in products))

    # -----------------------------
    # Sales
    # -----------------------------

    sales = []

    docs = db.collection("sales").stream()

    for doc in docs:

        sale = doc.to_dict()

        if start_date and end_date:

            if start_date <= sale["date"] <= end_date:
                sales.append(sale)

        else:
            sales.append(sale)

    total_sold = sum(s["quantity_sold"] for s in sales)

    total_sales = sum(s["total_amount"] for s in sales)

    return render_template(

        "reports.html",

        total_products=total_products,

        total_stock=total_stock,

        total_categories=total_categories,

        total_sold=total_sold,

        total_sales=total_sales,

        sales=sales,

        start_date=start_date,

        end_date=end_date

    )
# ==========================
# Export Inventory to Excel
# ==========================

@app.route("/export_report")
def export_report():

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Report"

    ws.append([
        "Product",
        "Category",
        "Quantity Sold",
        "Total Amount",
        "Date",
        "Time"
    ])

    docs = db.collection("sales").stream()

    for doc in docs:

        sale = doc.to_dict()

        if start_date and end_date:

            if not (start_date <= sale["date"] <= end_date):
                continue

        ws.append([
            sale["product_name"],
            sale["category"],
            sale["quantity_sold"],
            sale["total_amount"],
            sale["date"],
            sale["time"]
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name="Sales_Report.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
# ==========================
# Generate Invoice PDF
# ==========================

@app.route("/invoice/<sale_id>")
def invoice(sale_id):

    # Get sale details
    sale_doc = db.collection("sales").document(sale_id).get()

    if not sale_doc.exists:
        return "<h2>Invoice Not Found!</h2>"

    sale = sale_doc.to_dict()

    filename = f"Invoice_{sale_id}.pdf"

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    elements = []

    # Company Title
    elements.append(Paragraph("<b><font size=18>InventoryPro</font></b>", styles["Title"]))
    elements.append(Paragraph("Inventory Management System", styles["Heading2"]))
    elements.append(Paragraph("<br/>", styles["Normal"]))

    # Invoice Information
    elements.append(Paragraph(f"<b>Invoice ID:</b> {sale_id}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Date:</b> {sale['date']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Time:</b> {sale['time']}", styles["Normal"]))
    elements.append(Paragraph("<br/>", styles["Normal"]))

    # Table Data
    data = [
        ["Product", "Category", "Price", "Quantity", "Total"],
        [
            sale["product_name"],
            sale["category"],
            f"₹{sale['price']}",
            sale["quantity_sold"],
            f"₹{sale['total_amount']}"
        ]
    ]

    table = Table(data)

    table.setStyle(TableStyle([

        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),

        ("GRID", (0,0), (-1,-1), 1, colors.black),

        ("BACKGROUND", (0,1), (-1,-1), colors.beige),

        ("ALIGN", (0,0), (-1,-1), "CENTER"),

        ("BOTTOMPADDING", (0,0), (-1,0), 10)

    ]))

    elements.append(table)

    elements.append(Paragraph("<br/><br/>", styles["Normal"]))

    elements.append(Paragraph("<b>Thank you for your purchase!</b>", styles["Heading2"]))

    doc.build(elements)

    return send_file(
        filename,
        as_attachment=True
    )



if __name__ == "__main__":
    app.run(debug=True)