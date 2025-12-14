from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URI'))
db = client['pran-protocol']

# Find user with email
user = db.users.find_one({"email": "69aunty@gmail.com"})

if user:
    print(f"User found: {user.get('email')}")
    print(f"\nEncrypted fields present:")
    print(f"  age_encrypted: {'✅' if user.get('age_encrypted') else '❌'}")
    print(f"  gender_encrypted: {'✅' if user.get('gender_encrypted') else '❌'}")
    print(f"  address_encrypted: {'✅' if user.get('address_encrypted') else '❌'}")
    print(f"  medical_history_encrypted: {'✅' if user.get('medical_history_encrypted') else '❌'}")
    print(f"  medications_encrypted: {'✅' if user.get('medications_encrypted') else '❌'}")
    print(f"  previous_conditions_encrypted: {'✅' if user.get('previous_conditions_encrypted') else '❌'}")
    print(f"\nEncryption key ID: {user.get('encryption_key_id', 'Not set')}")
else:
    print("User not found")

client.close()
