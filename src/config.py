import os
from typing import Optional, Dict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from src.retrieval.retriever import Retriever
from src.vector_store.chroma_manager import ChromaDBManager
from config.settings import settings

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
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=openai_api_key
        )
        self.search_tool = TavilySearchResults(
            api_key=tavily_api_key,
            max_results=5
        )
        print("   ✓ LLM and Web Search ready.")
        
        # 3. Initialize Domain-Specific RAG Systems
        print("   -> Initializing Domain-Specific RAG Systems...")
        self.rag_retrievers: Dict[str, Retriever] = {}
        self.chroma_managers: Dict[str, ChromaDBManager] = {}
        
        try:
            # Create retrievers for each domain
            for domain, collection_name in settings.COLLECTION_NAMES.items():
                try:
                    chroma_manager = ChromaDBManager(collection_name=collection_name)
                    self.chroma_managers[domain] = chroma_manager
                    
                    # Create retriever with strategist enabled
                    retriever = Retriever(
                        chroma_manager, 
                        use_reranking=True, 
                        use_strategist=True
                    )
                    self.rag_retrievers[domain] = retriever
                    print(f"   ✓ {domain} RAG system ready (collection: {collection_name})")
                except Exception as e:
                    print(f"   ⚠️  Could not initialize {domain} RAG: {e}")
            
            # Fallback to general retriever
            if not self.rag_retrievers:
                print("   -> Creating fallback general RAG system...")
                chroma_manager = ChromaDBManager()
                self.chroma_managers['general'] = chroma_manager
                self.rag_retrievers['general'] = Retriever(
                    chroma_manager,
                    use_reranking=True,
                    use_strategist=True
                )
            
            # Keep legacy rag_retriever for backward compatibility
            self.rag_retriever = self.rag_retrievers.get('general') or list(self.rag_retrievers.values())[0]
            
            print("   ✓ RAG Systems initialized.")
        except Exception as e:
            print(f"   ⚠️  Could not initialize RAG system: {e}. AYUSH/Yoga agents will have limited capabilities.")
            self.rag_retriever = None
            self.rag_retrievers = {}
            self.chroma_managers = {}
    
    def get_retriever(self, domain: str) -> Optional[Retriever]:
        """Get domain-specific retriever, fallback to general if not found"""
        return self.rag_retrievers.get(domain) or self.rag_retrievers.get('general')
    
    def get_chroma_manager(self, domain: str) -> Optional[ChromaDBManager]:
        """Get domain-specific ChromaDB manager"""
        return self.chroma_managers.get(domain) or self.chroma_managers.get('general')