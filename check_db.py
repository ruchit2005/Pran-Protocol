import pprint
from src.vector_store.chroma_manager import ChromaDBManager

def check_database_contents():
    """
    Connects to the ChromaDB and prints stats and sample documents.
    """
    print("--- Connecting to the existing ChromaDB to check its contents ---")
    
    try:
        # Initialize the manager, which will connect to the existing collection
        chroma_manager = ChromaDBManager()
        
        # Get statistics
        stats = chroma_manager.get_collection_stats()
        print("\n✅ Database Stats:")
        pprint.pprint(stats)
        
        if stats.get('total_documents', 0) > 0:
            print("\n✅ Fetching 5 sample documents from the database...")
            # Use the underlying collection's .get() method to see raw data
            sample = chroma_manager.collection.get(limit=5, include=["metadatas", "documents"])
            pprint.pprint(sample)
        else:
            print("\n❌ The database appears to be empty.")
            
    except Exception as e:
        print(f"\n❌ An error occurred while checking the database: {e}")

if __name__ == "__main__":
    check_database_contents()