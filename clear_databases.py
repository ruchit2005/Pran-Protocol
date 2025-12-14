"""
Script to clear MongoDB and Supabase databases for fresh testing
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import psycopg2

load_dotenv()

def clear_mongodb():
    """Clear all data from MongoDB collections"""
    try:
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client['pran-protocol']
        
        # List all collections
        collections = db.list_collection_names()
        print(f"\n📦 MongoDB Collections found: {collections}")
        
        # Delete all documents from each collection
        for collection in collections:
            count = db[collection].count_documents({})
            result = db[collection].delete_many({})
            print(f"  ✅ Deleted {result.deleted_count} documents from {collection}")
        
        print("✅ MongoDB data cleared successfully!\n")
        client.close()
    except Exception as e:
        print(f"❌ MongoDB clear failed: {e}\n")

def clear_supabase():
    """Clear blockchain audit tables in Supabase PostgreSQL (excluding hospitals)"""
    try:
        db_url = os.getenv('BLOCKCHAIN_DATABASE_URL')
        if not db_url:
            print("⚠️ No BLOCKCHAIN_DATABASE_URL found, skipping Supabase clear\n")
            return
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        tables = cursor.fetchall()
        
        print(f"📦 Supabase Tables found: {[t[0] for t in tables]}")
        
        # Tables to clear (blockchain only, NOT hospitals)
        tables_to_clear = ['blocks', 'audit_logs', 'blockchain_transactions']
        
        # Clear each blockchain table
        for table in tables:
            table_name = table[0]
            
            # Skip hospitals table
            if table_name == 'hospitals':
                print(f"  ⏭️  Skipped {table_name} (preserved)")
                continue
            
            if table_name in tables_to_clear:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                
                cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE")
                print(f"  ✅ Cleared {table_name} ({count} rows)")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Supabase blockchain data cleared successfully!\n")
    except Exception as e:
        print(f"❌ Supabase clear failed: {e}\n")

if __name__ == "__main__":
    print("\n🗑️  CLEARING ALL DATABASES FOR FRESH TESTING\n")
    print("=" * 50)
    
    confirm = input("\n⚠️  This will DELETE ALL DATA. Are you sure? (yes/no): ")
    
    if confirm.lower() == 'yes':
        print("\n🚀 Starting database cleanup...\n")
        clear_mongodb()
        clear_supabase()
        print("=" * 50)
        print("✅ All databases cleared! Ready for fresh testing.\n")
    else:
        print("\n❌ Cancelled. No data was deleted.\n")
