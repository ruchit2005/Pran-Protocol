from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class MedicalMathChain:
    """Handles medical calculations with Chain-of-Thought reasoning"""
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Medical Dosage Assistant. 
            
            Perform calculations step-by-step using Chain-of-Thought (CoT).
            
            Input: "Calculate Paracetamol dose for a 20kg child (15mg/kg)"
            
            Reasoning Steps:
            1. Identify weight: 20kg
            2. Identify dosage rule: 15mg/kg
            3. Calculation: 20 * 15 = 300mg
            4. Verify max limits (if known or stated)
            
            Output JSON:
            {{
                "calculation_type": "dosage/bmi/infusion",
                "steps": ["step 1...", "step 2..."],
                "result": "300mg",
                "disclaimer": "Verify with a doctor."
            }}
            """),
            ("user", "{input}")
        ])
        self.chain = self.prompt | self.llm | JsonOutputParser()
        
    def run(self, user_input: str) -> Dict[str, Any]:
        print(f"      → MedicalMath: Calculating...")
        try:
            return self.chain.invoke({"input": user_input})
        except Exception as e:
            return {"error": str(e)}
