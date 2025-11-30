"""
Specialized chain implementations using RAG retriever
"""

import json
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser


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
        print(f"      → Retrieving documents for '{query}'...")
        
        # Use the RAG retriever
        retrieval_results = self.retriever.retrieve(query=query, top_k=5)
        retrieved_docs = retrieval_results.get('results', [])
        
        if not retrieved_docs:
            print("      → No relevant documents found in the knowledge base.")
            return "I could not find any specific information in my knowledge base for your query. Please try rephrasing."
        
        print(f"      → Found {len(retrieved_docs)} relevant document chunks.")
        
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

class GovernmentSchemeChain(SearchBasedChain):
    def __init__(self, llm, search_tool):
        system_prompt = "You are a government healthcare scheme advisor for India. Based on the user query and search results, identify schemes, explain criteria, and provide links.\nSearch results available:\n{search_results}"
        super().__init__(llm, search_tool, system_prompt)
    def run(self, user_input: str) -> str:
        search_query = f"India government health schemes {user_input}"
        return self.search_and_generate(user_input, search_query)

class MentalWellnessChain(SearchBasedChain):
    def __init__(self, llm, search_tool):
        system_prompt = "You are a compassionate mental wellness counselor. Provide empathetic acknowledgment, coping strategies, and professional help resources (KIRAN: 1800-599-0019). Use search results for current resources.\nSearch results:\n{search_results}"
        super().__init__(llm, search_tool, system_prompt)
    def run(self, user_input: str) -> str:
        search_query = f"mental health support resources India {user_input}"
        return self.search_and_generate(user_input, search_query)

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

Based on the provided context, provide:
1. Specific yoga poses (asanas) and breathing exercises (pranayama).
2. Safety precautions and contraindications mentioned in the documents.
3. Suggested duration and frequency if available in the context.

IMPORTANT: You must cite the source for every recommendation using the format [Source: filename].
Example: "Practice Tadasana for stability [Source: yoga_basics.pdf]."

Retrieved Context:
{context}"""
        super().__init__(llm, retriever, system_prompt)
    
    def run(self, user_input: str) -> str:
        return self.retrieve_and_generate(user_input)


class AyushChain(RAGBasedChain):
    """Handles AYUSH-related queries using RAG"""
    
    def __init__(self, llm, retriever):
        system_prompt = """You are an AYUSH (Ayurveda, Yoga, Unani, Siddha, Homeopathy) advisor.

Based on the retrieved context, provide:
1. Traditional remedies and treatments.
2. Dietary and lifestyle recommendations.
3. Any mentioned precautions or contraindications.
4. Stick strictly to the information provided in the context.

IMPORTANT: You must cite the source for every recommendation using the format [Source: filename].
Example: "Ashwagandha is good for stress [Source: ayurveda_herbs.txt]."

Retrieved Context:
{context}"""
        super().__init__(llm, retriever, system_prompt)
    
    def run(self, user_input: str) -> str:
        return self.retrieve_and_generate(user_input)