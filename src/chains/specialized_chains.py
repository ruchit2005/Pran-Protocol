"""
Specialized chain implementations using RAG retriever
"""

import json
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.retrieval.medical_terminology import expand_query_with_ayurvedic_terms


class SearchBasedChain:
    """Base class for chains that use web search"""
    
    def __init__(self, llm, search_tool, system_prompt: str):
        self.llm = llm
        self.search_tool = search_tool
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}")
        ])
    
    def search_and_generate(self, query: str, search_query: str) -> str:
        """Perform search and generate response"""
        print(f"      → Searching for '{search_query}'...")
        search_results = self.search_tool.invoke(search_query)
        print(f"      → Found {len(search_results) if isinstance(search_results, list) else 'some'} results")
        
        print(f"      → Generating response...")
        chain = self.prompt | self.llm | StrOutputParser()
        response = chain.invoke({
            "input": query,
            "search_results": json.dumps(search_results, indent=2)
        })
        print(f"      ← Response generated")
        return response

class RAGBasedChain:
    """Base class for chains that use our internal RAG retriever"""
    
    def __init__(self, llm, retriever, system_prompt: str):
        self.llm = llm
        self.retriever = retriever
        # Store the template - we'll format it manually
        self.system_prompt_template = system_prompt
    
    def retrieve_and_generate(self, query: str) -> str:
        """Perform retrieval and generate a response"""
        # Expand query with medical terminology
        expanded_query = expand_query_with_ayurvedic_terms(query)
        if expanded_query != query:
            print(f"      → Query expanded: '{query}' → '{expanded_query[:100]}...'")
        
        print(f"      → Retrieving documents for '{query}'...")
        
        # Use the RAG retriever with expanded query for better matches
        retrieval_results = self.retriever.retrieve(query=expanded_query, top_k=3)
        retrieved_docs = retrieval_results.get('results', [])
        
        if not retrieved_docs:
            print("      → No relevant documents found in the knowledge base.")
            return "I could not find any specific information in my knowledge base for your query. Please try rephrasing."
        
        print(f"      → Found {len(retrieved_docs)} relevant document chunks:")
        for i, doc in enumerate(retrieved_docs, 1):
            source = doc['metadata'].get('file_name', 'N/A')
            distance = doc.get('distance', 'N/A')
            content_preview = doc['content'][:100].replace('\n', ' ') + '...'
            print(f"         [{i}] Source: {source} | Distance: {distance}")
            print(f"             Preview: {content_preview}")
        
        # Format context for the LLM
        context = "\n\n---\n\n".join([
            f"Source: {doc['metadata'].get('file_name', 'N/A')}\nContent: {doc['content']}"
            for doc in retrieved_docs
        ])
        
        print(f"      → Generating response with context...")
        
        # Format the context into the system prompt first
        formatted_system_prompt = self.system_prompt_template.replace("{context}", context)
        
        # Now create the prompt with only {input} variable
        prompt = ChatPromptTemplate.from_messages([
            ("system", formatted_system_prompt),
            ("user", "{input}")
        ])
        
        # Create and invoke the chain
        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({"input": query})
        
        print(f"      ← Response generated")
        return response


# --- Specialized Chains ---

class GovernmentSchemeChain(RAGBasedChain):
    """Handles government schemes queries using RAG with search fallback"""
    
    def __init__(self, llm, retriever, search_tool=None):
        system_prompt = """You are a government healthcare scheme advisor for India.

Based on the retrieved context, provide:
1. Relevant government schemes and programs.
2. Eligibility criteria and benefits.
3. Application process and contact information.
4. Stick strictly to the information provided in the context.

IMPORTANT: You must cite the source for every scheme using the format [Source: filename].
Example: "Ayushman Bharat provides coverage up to 5 lakhs [Source: schemes_guide.pdf]."

Retrieved Context:
{context}"""
        super().__init__(llm, retriever, system_prompt)
        self.search_tool = search_tool
        
        # Search fallback prompt
        self.search_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a government healthcare scheme advisor for India. Based on the search results, identify schemes, explain criteria, and provide links.

Search results available:
{search_results}"""),
            ("user", "{input}")
        ])
    
    def run(self, user_input: str) -> str:
        print(f"      → Retrieving documents for '{user_input}'...")
        
        # Try RAG first
        retrieval_results = self.retriever.retrieve(query=user_input, top_k=3)
        retrieved_docs = retrieval_results.get('results', [])
        
        if retrieved_docs:
            print(f"      → Found {len(retrieved_docs)} relevant document chunks:")
            for i, doc in enumerate(retrieved_docs, 1):
                source = doc['metadata'].get('file_name', 'N/A')
                distance = doc.get('distance', 'N/A')
                content_preview = doc['content'][:100].replace('\n', ' ') + '...'
                print(f"         [{i}] Source: {source} | Distance: {distance}")
                print(f"             Preview: {content_preview}")
            
            # Use RAG response
            return self.retrieve_and_generate(user_input)
        
        # Fallback to web search
        if self.search_tool:
            print("      → No documents found in RAG. Falling back to web search...")
            search_query = f"India government health schemes {user_input}"
            print(f"      → Searching for '{search_query}'...")
            
            search_results = self.search_tool.invoke(search_query)
            print(f"      → Found {len(search_results) if isinstance(search_results, list) else 'some'} results")
            
            print(f"      → Generating response from search results...")
            chain = self.search_prompt | self.llm | StrOutputParser()
            response = chain.invoke({
                "input": user_input,
                "search_results": json.dumps(search_results, indent=2)
            })
            print(f"      ← Response generated")
            return response
        
        # No RAG results and no search tool
        print("      → No relevant documents found in the knowledge base.")
        return "I could not find any specific information about government schemes in my knowledge base for your query. Please try rephrasing or provide more details."

class MentalWellnessChain(RAGBasedChain):
    """Mental wellness support using RAG only - no web search for medical advice"""
    
    def __init__(self, llm, retriever):
        system_prompt = """You are a compassionate mental wellness counselor.

CRITICAL LANGUAGE RULE:
- If input is in Hindi (Devanagari: क, ख, ग), respond ONLY in Hindi Devanagari script
- NEVER use Urdu/Arabic script (ا، ب، پ، ت، ک)
- Use Hindi characters: क, ख, ग, घ, च, छ, ज, झ, ट, ठ, ड, ढ, त, थ, द, ध, न, प, फ, ब, भ, म
- If input is in English, respond in English

Based on the retrieved context, provide:
1. Empathetic acknowledgment and validation.
2. Evidence-based coping strategies from the documents.
3. Lifestyle and wellness recommendations.
4. Professional help resources (KIRAN Helpline: 1800-599-0019).

IMPORTANT RULES:
- You must cite the source for every recommendation using the format [Source: filename].
- Stick strictly to information from the context. Do not make up medical advice.
- DO NOT add any "Safety Note" disclaimers - just provide the recommendations directly.

Retrieved Context:
{context}"""
        super().__init__(llm, retriever, system_prompt)
    
    def run(self, user_input: str) -> str:
        return self.retrieve_and_generate(user_input)

class HospitalLocatorChain(SearchBasedChain):
    def __init__(self, llm, search_tool):
        system_prompt = "You are a healthcare facility locator. Extract location from the query, search for nearby facilities, and list them with details.\nSearch results:\n{search_results}"
        super().__init__(llm, search_tool, system_prompt)
    def run(self, user_input: str) -> str:
        search_query = f"hospitals healthcare facilities near {user_input}"
        return self.search_and_generate(user_input, search_query)

class YogaChain(RAGBasedChain):
    """Provides yoga recommendations using RAG"""
    
    def __init__(self, llm, retriever):
        system_prompt = """You are a certified yoga instructor.

CRITICAL LANGUAGE RULE:
- If input is in Hindi (Devanagari: क, ख, ग), respond ONLY in Hindi Devanagari script
- NEVER use Urdu/Arabic script (ا، ب، پ، ت، ک)
- Use Hindi characters: क, ख, ग, घ, च, छ, ज, झ, ट, ठ, ड, ढ, त, थ, द, ध, न, प, फ, ब, भ, म
- If input is in English, respond in English

Based on the provided context, provide:
1. Specific yoga poses (asanas) and breathing exercises (pranayama).
2. Safety precautions and contraindications mentioned in the documents.
3. Suggested duration and frequency if available in the context.

IMPORTANT RULES:
- You must cite the source for every recommendation using the format [Source: filename].
- Example: "Practice Tadasana for stability [Source: yoga_basics.pdf]."
- DO NOT add any "Safety Note" disclaimers - just provide the recommendations directly.

Retrieved Context:
{context}"""
        super().__init__(llm, retriever, system_prompt)
    
    def run(self, user_input: str) -> str:
        return self.retrieve_and_generate(user_input)


class AyushChain(RAGBasedChain):
    """Handles AYUSH-related queries using RAG"""
    
    def __init__(self, llm, retriever):
        system_prompt = """You are an AYUSH (Ayurveda, Yoga, Unani, Siddha, Homeopathy) advisor.

CRITICAL LANGUAGE RULE:
- If input is in Hindi (Devanagari: क, ख, ग), respond ONLY in Hindi Devanagari script
- NEVER EVER use Urdu/Arabic script (ا، ب، پ، ت، ک، خ، گ)
- Use Hindi characters: क, ख, ग, घ, च, छ, ज, झ, ट, ठ, ड, ढ, त, थ, द, ध, न, प, फ, ब, भ, म, य, र, ल, व, श, ष, स, ह
- If input is in English, respond in English

Based on the retrieved context, provide:
1. Traditional remedies and treatments.
2. Dietary and lifestyle recommendations.
3. Any mentioned precautions or contraindications.
4. Stick strictly to the information provided in the context.

IMPORTANT RULES:
- You must cite the source for every recommendation using the format [Source: filename].
- Example: "Ashwagandha is good for stress [Source: ayurveda_herbs.txt]."
- DO NOT add any "Safety Note" disclaimers - just provide the recommendations directly.

Retrieved Context:
{context}"""
        super().__init__(llm, retriever, system_prompt)
    
    def run(self, user_input: str) -> str:
        return self.retrieve_and_generate(user_input)