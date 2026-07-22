import os
import firebase_admin
from firebase_admin import credentials, firestore

# Get the project folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Build the full path to the JSON file
key_path = os.path.join(BASE_DIR, "firebase", "serviceAccountKey.json")

print("Using key:", key_path)

if not firebase_admin._apps:
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()