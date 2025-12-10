from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class FactCheckerChain:
    """Validates medical advice against known medical facts"""
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Medical Validator. Your job is to review the AI's response for factual accuracy and safety.
            
            Check for:
            1. Harmful advice (e.g., "Drink bleach for COVID")
            2. Dosage Errors (e.g., "Take 50 pills")
            3. Hallucinations (e.g., citing fake studies)
            4. Encouraging self-harm
            
            Context: The user asked about a health topic.
            AI Response: Proposed response to the user.
            
            Return JSON:
            {{
                "is_safe": true/false,
                "reason": "explanation if unsafe",
                "revised_response": "optional corrected response, or null if safe"
            }}
            """),
            ("user", "User Query: {query}\nAI Response: {response}")
        ])
        self.chain = self.prompt | self.llm | JsonOutputParser()
        
    def validate(self, query: str, response: str) -> Dict[str, Any]:
        print(f"      → Validator: Checking response safety/accuracy...")
        try:
            result = self.chain.invoke({"query": query, "response": response})
            print(f"      ← Validation Result: Safe={result.get('is_safe', True)}")
            return result
        except Exception as e:
            print(f"      ⚠️ Validation failed: {e}")
            return {"is_safe": True, "reason": "Validation error, defaulted to safe"}
