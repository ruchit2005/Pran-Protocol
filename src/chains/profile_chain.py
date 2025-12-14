from typing import Dict, Any, List
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class ProfileExtractionChain:
    """Extracts medical profile information from user input"""
    
    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a medical profile updater. Your ONLY job is to detect NEW permanent medical information that should be added to the patient's profile.

**Current Profile:**
- Age: {age}
- Gender: {gender}
- Medical Conditions: {history}
- Allergies: {allergies}
- Medications: {medications}

**Rules:**
1. ONLY extract information if user explicitly mentions NEW information not already in their profile
2. Temporary symptoms (headache, stomach ache, fever) are NOT conditions - DO NOT add them
3. Only add to conditions if user says "I have been diagnosed with X" or "I suffer from chronic X"
4. Only add medications if user says "I am taking X" or "I'm on X medication"
5. If information is already in profile, set found_new_info=false
6. If user is just describing current symptoms for diagnosis, set found_new_info=false

**Examples:**
- "I have a headache" → found_new_info: false (temporary symptom)
- "I was diagnosed with diabetes last month" → found_new_info: true, new_conditions: ["diabetes"]
- "I'm taking Metformin daily" → found_new_info: true, new_medications: ["Metformin"]
- "My stomach hurts" → found_new_info: false (symptom query, not profile update)

Return JSON:
{{
    "found_new_info": true/false,
    "age": null or int,
    "gender": null or string,
    "new_conditions": [],
    "new_allergies": [],
    "new_medications": []
}}"""),
            ("user", "{input}")
        ])
        self.chain = self.prompt | self.llm | JsonOutputParser()
    
    def run(self, user_input: str, current_profile: Any) -> Dict[str, Any]:
        # Parse current profile - handle both dict and object
        try:
            if isinstance(current_profile, dict):
                age = current_profile.get("age")
                gender = current_profile.get("gender")
                medical_history = current_profile.get("medical_history", "[]")
                allergies = current_profile.get("allergies", "[]")
                medications = current_profile.get("medications", "[]")
            else:
                age = current_profile.age
                gender = current_profile.gender
                medical_history = current_profile.medical_history
                allergies = current_profile.allergies
                medications = current_profile.medications
            
            # Robust parsing - handle JSON array, comma-separated string, or empty
            def parse_field(value):
                if not value or value == "" or value == "null":
                    return []
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    # Try JSON first
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, list) else []
                    except (json.JSONDecodeError, ValueError):
                        # Fall back to comma-separated
                        return [item.strip() for item in value.split(",") if item.strip()]
                return []
            
            history = parse_field(medical_history)
            allergies_list = parse_field(allergies)
            medications_list = parse_field(medications)
            
            # Log what we're working with
            print(f"      → Current profile: age={age}, gender={gender}, conditions={history}, medications={medications_list}")
            
        except Exception as e:
            print(f"      ⚠️ Profile parsing failed: {e}")
            history, allergies_list, medications_list = [], [], []
            age, gender = None, None

        try:
            print(f"      → ProfileExtraction: Checking for medical info updates...")
            result = self.chain.invoke({
                "input": user_input,
                "age": age,
                "gender": gender,
                "history": history,
                "allergies": allergies_list,
                "medications": medications_list
            })
            
            if result.get("found_new_info"):
                print(f"      → Found new medical info: {result}")
                return result
            return None
            
        except Exception as e:
            print(f"      ⚠️ Profile extraction failed: {e}")
            return None
