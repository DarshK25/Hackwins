"""
clear_seeded_data.py
--------------------
Wipes ALL transactions, invoices, and clients from ALL organizations in the
MoneyOps MongoDB Atlas database.

Run this ONCE to clean up demo data from previously-seeded accounts.
After running, restart Spring Boot — new accounts will start from zero.

Usage:
    python clear_seeded_data.py
"""

import sys

try:
    from pymongo import MongoClient
except ImportError:
    print("pymongo not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymongo[srv]"])
    from pymongo import MongoClient

MONGO_URI = (
    "mongodb+srv://tanushjain0610_db_user:061005"
    "@moneyops.pftzwmu.mongodb.net/moneyops"
    "?retryWrites=true&w=majority&appName=MoneyOps"
)

DB_NAME = "moneyops"

# Collections that hold seeded data
COLLECTIONS_TO_CLEAR = [
    "transactions",
    "invoices",
    "clients",
]

def main():
    print(f"Connecting to MongoDB Atlas ({DB_NAME})...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]

    # Show what we're about to delete
    print("\n📊 Current document counts:")
    for col in COLLECTIONS_TO_CLEAR:
        count = db[col].count_documents({})
        print(f"   {col}: {count} documents")

    confirm = input("\n⚠️  This will DELETE ALL documents from the above collections.\n"
                    "Type 'YES' to confirm: ").strip()

    if confirm != "YES":
        print("Aborted. No data was deleted.")
        return

    print("\n🗑️  Deleting data...")
    for col in COLLECTIONS_TO_CLEAR:
        before = db[col].count_documents({})
        result = db[col].delete_many({})
        print(f"   ✅ {col}: deleted {result.deleted_count}/{before} documents")

    print("\n✅ Done! All seeded data has been cleared.")
    print("   New accounts will now start from a clean slate (₹0).")
    client.close()

if __name__ == "__main__":
    main()
