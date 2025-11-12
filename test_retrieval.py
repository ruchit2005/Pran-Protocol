import pprint
from src.vector_store.chroma_manager import ChromaDBManager

# --- CONFIGURE YOUR TEST HERE ---
# Put one of the queries that is failing.
TEST_QUERY = "What are some ayurvedic remedies for Jwara?" 
# TEST_QUERY = "What are the benefits of Ayushman Bharat?"

def direct_search():
    """
    Performs a direct search against ChromaDB to see raw results
    and similarity scores before any application logic.
    """
    print(f"--- Performing direct search for query: '{TEST_QUERY}' ---")
    
    try:
        # Initialize the manager to connect to your existing database
        chroma_manager = ChromaDBManager()
        
        # Perform a search to get the top 10 raw results
        results = chroma_manager.search(query=TEST_QUERY, top_k=10)
        
        if not results:
            print("\n❌ CRITICAL: The search returned ZERO results from ChromaDB.")
            print("This might indicate an issue during embedding or storage.")
            return

        print("\n✅ Raw search results from ChromaDB (Top 10):")
        for i, doc in enumerate(results):
            print("-" * 50)
            print(f"Result #{i+1}")
            print(f"Similarity Score: {doc['similarity']:.4f}") # THE MOST IMPORTANT VALUE
            print(f"Source: {doc['metadata'].get('file_name', 'N/A')}")
            # Print the first 250 characters of the content
            print(f"Content: {doc['content'][:250]}...")
        print("-" * 50)

        print("\n--- Analysis ---")
        highest_score = results[0]['similarity']
        print(f"The highest similarity score found was: {highest_score:.4f}")
        print(f"Your application's current threshold is set to: 0.35")
        if highest_score < 0.35:
            print("\nCONCLUSION: The retrieval is failing because even the BEST matching document")
            print("has a similarity score lower than your threshold. The results are being correctly filtered out.")
        else:
             print("\nCONCLUSION: The results have scores above the threshold, but are still being filtered.")
             print("This suggests a potential logic error in the retriever.py filtering step.")


    except Exception as e:
        print(f"\n❌ An error occurred during the direct search: {e}")

if __name__ == "__main__":
    direct_search()