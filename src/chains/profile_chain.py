from typing import Dict, Any, List
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class ProfileExtractionChain:
    """Extracts medical profile information from user input"""
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a medical scribe. Analyze the user's input and extract ANY new medical information to update their profile.
            
            Current Profile:
            - Age: {age}
            - Gender: {gender}
            - Medical Conditions: {history}
            - Allergies: {allergies}
            - Medications: {medications}
            
            If the user mentions NEW information, extract it. If they contradict existing info, update it.
            
            Return JSON:
            {{
                "found_new_info": true/false,
                "age": null or int,
                "gender": null or string,
                "new_conditions": [],
                "new_allergies": [],
                "new_medications": []
            }}
            """),
            ("user", "{input}")
        ])
        self.chain = self.prompt | self.llm | JsonOutputParser()
    
    def run(self, user_input: str, current_profile: Any) -> Dict[str, Any]:
        # Parse current profile JSONs
        try:
            history = json.loads(current_profile.medical_history) if current_profile.medical_history else []
            allergies = json.loads(current_profile.allergies) if current_profile.allergies else []
            medications = json.loads(current_profile.medications) if current_profile.medications else []
        except:
            history, allergies, medications = [], [], []

        try:
            print(f"      → ProfileExtraction: Checking for medical info updates...")
            result = self.chain.invoke({
                "input": user_input,
                "age": current_profile.age,
                "gender": current_profile.gender,
                "history": history,
                "allergies": allergies,
                "medications": medications
            })
            
            if result.get("found_new_info"):
                print(f"      → Found new medical info: {result}")
                return result
            return None
            
        except Exception as e:
            print(f"      ⚠️ Profile extraction failed: {e}")
            return None
