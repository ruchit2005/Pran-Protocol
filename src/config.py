import os
from typing import Optional, Dict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from src.retrieval.retriever import Retriever
from config.settings import settings

# Import appropriate vector store based on configuration
if settings.VECTOR_STORE_TYPE == "chroma":
    from src.vector_store.chroma_manager import ChromaDBManager as VectorStore
else:
    from src.vector_store.cloud_vector_store import CloudVectorStore as VectorStore

load_dotenv()

class HealthcareConfig:
    """
    Configuration class that initializes and holds all necessary services.
    This is used by both the CLI and the API to ensure consistency.
    """
    
    def __init__(self):
        # 1. Load API Keys and Basic Settings
        openai_api_key = os.getenv("OPENAI_API_KEY")
        tavily_api_key = os.getenv("TAVILY_API_KEY")

        if not openai_api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY in .env file.")
        if not tavily_api_key:
            raise ValueError("Tavily API key not found. Set TAVILY_API_KEY in .env file.")
        
        # 2. Initialize LLM and Web Search Tool
        print("   -> Initializing LLM and Web Search...")
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=openai_api_key,
            max_tokens=800
        )
        self.search_tool = TavilySearchResults(
            api_key=tavily_api_key,
            max_results=3
        )
        print("   ✓ LLM and Web Search ready.")
        
        # 3. Initialize Domain-Specific RAG Systems
        print("   -> Initializing Domain-Specific RAG Systems...")
        print(f"   -> Using vector store: {settings.VECTOR_STORE_TYPE.upper()}")
        
        # ⚡ OPTIMIZATION: Create shared embedding manager once
        from src.embeddings.embedding_manager import EmbeddingManager
        from src.retrieval.reranker import Reranker
        print("   -> Loading shared embedding model (all-MiniLM-L6-v2)...")
        shared_embedding_manager = EmbeddingManager()
        print("   -> Loading shared reranker (ms-marco-MiniLM-L-6-v2)...")
        shared_reranker = Reranker()
        print("   ✓ Shared models loaded")
        
        self.rag_retrievers: Dict[str, Retriever] = {}
        self.vector_stores: Dict[str, VectorStore] = {}
        
        try:
            # Create retrievers for each domain (sharing models)
            for domain, collection_name in settings.COLLECTION_NAMES.items():
                try:
                    # Pass shared embedding manager to vector store
                    vector_store = VectorStore(
                        collection_name=collection_name,
                        embedding_manager=shared_embedding_manager
                    )
                    self.vector_stores[domain] = vector_store
                    
                    # Create retriever with shared reranker
                    retriever = Retriever(
                        vector_store, 
                        use_reranking=True, 
                        use_strategist=True,
                        shared_reranker=shared_reranker
                    )
                    self.rag_retrievers[domain] = retriever
                    print(f"   ✓ {domain} RAG system ready (collection: {collection_name})")
                except Exception as e:
                    print(f"   ⚠️  Could not initialize {domain} RAG: {e}")
            
            # Fallback to general retriever
            if not self.rag_retrievers:
                print("   -> Creating fallback general RAG system...")
                vector_store = VectorStore(embedding_manager=shared_embedding_manager)
                self.vector_stores['general'] = vector_store
                self.rag_retrievers['general'] = Retriever(
                    vector_store,
                    use_reranking=True,
                    use_strategist=True,
                    shared_reranker=shared_reranker
                )
            
            # Keep legacy rag_retriever for backward compatibility
            self.rag_retriever = self.rag_retrievers.get('general') or list(self.rag_retrievers.values())[0]
            
            print("   ✓ RAG Systems initialized.")
        except Exception as e:
            print(f"   ⚠️  Could not initialize RAG system: {e}. AYUSH/Yoga agents will have limited capabilities.")
            self.rag_retriever = None
            self.rag_retrievers = {}
            self.vector_stores = {}
    
    def get_retriever(self, domain: str) -> Optional[Retriever]:
        """Get domain-specific retriever, fallback to general if not found"""
        return self.rag_retrievers.get(domain) or self.rag_retrievers.get('general')
    
    def get_vector_store(self, domain: str) -> Optional[VectorStore]:
        """Get domain-specific vector store"""
        return self.vector_stores.get(domain) or self.vector_stores.get('general')