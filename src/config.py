import os
from typing import Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from src.retrieval.retriever import Retriever
from src.vector_store.chroma_manager import ChromaDBManager

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
            temperature=0.7,
            api_key=openai_api_key
        )
        self.search_tool = TavilySearchResults(
            api_key=tavily_api_key,
            max_results=5
        )
        print("   ✓ LLM and Web Search ready.")
        
        # 3. Initialize RAG System
        print("   -> Initializing RAG System...")
        try:
            chroma_manager = ChromaDBManager()
            
            # --- THIS IS THE ONLY CHANGE NEEDED ---
            # Activate the new agentic Strategist by adding the argument here.
            self.rag_retriever = Retriever(
                chroma_manager, 
                use_reranking=True, 
                use_strategist=True  # This activates the new feature
            )
            # --- END OF CHANGE ---

            print("   ✓ RAG System ready.")
        except Exception as e:
            print(f"   ⚠️  Could not initialize RAG system: {e}. AYUSH/Yoga agents will have limited capabilities.")
            self.rag_retriever = None