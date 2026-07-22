from firebase_config import db

product = {
    "product_id": "P001",
    "name": "Laptop",
    "category": "Electronics",
    "price": 50000,
    "quantity": 10
}

db.collection("products").document(product["product_id"]).set(product)

print("Product added successfully!")