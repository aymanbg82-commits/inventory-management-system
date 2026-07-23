import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase only once
if not firebase_admin._apps:

    # Running on Vercel
    if "FIREBASE_CREDENTIALS" in os.environ:

        firebase_credentials = json.loads(os.environ["FIREBASE_CREDENTIALS"])
        cred = credentials.Certificate(firebase_credentials)

    # Running locally
    else:

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(BASE_DIR, "firebase", "serviceAccountKey.json")

        cred = credentials.Certificate(key_path)

    firebase_admin.initialize_app(cred)

db = firestore.client()