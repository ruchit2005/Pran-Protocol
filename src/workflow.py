"""
Main healthcare workflow
"""
from typing import Dict, Any
from .config import HealthcareConfig
from .chains import (
    GuardrailChain,
    IntentClassifierChain,
    SymptomCheckerChain,
    GovernmentSchemeChain,
    MentalWellnessChain,
    YogaChain,
    AyushChain,
    HospitalLocatorChain,
    ProfileExtractionChain,
    HealthAdvisoryChain,
    MedicalMathChain
)
from .evaluation.validator import FactCheckerChain
from .utils.emergency import HybridEmergencyDetector
from .utils.youtube_client import search_videos

class HealthcareWorkflow:
    """Main workflow orchestrator for hybrid RAG/Search system"""
    
    def __init__(self, config: HealthcareConfig):
        self.config = config
        
        # Initialize all chains, PASSING THE CORRECT TOOL to each one.
        self.guardrail = GuardrailChain(config.llm)
        self.classifier = IntentClassifierChain(config.llm)
        self.symptom_chain = SymptomCheckerChain(config.llm)
        self.emergency_detector = HybridEmergencyDetector()
        
        # Profile Extractor
        self.profile_extractor = ProfileExtractionChain(config.llm)
        
        # Agents using WEB SEARCH get config.search_tool
        self.gov_scheme_chain = GovernmentSchemeChain(config.llm, config.search_tool)
        self.mental_wellness_chain = MentalWellnessChain(config.llm, config.search_tool)
        self.hospital_chain = HospitalLocatorChain(config.llm, config.search_tool)
        
        # New Chains
        self.advisory_chain = HealthAdvisoryChain(config.llm)
        self.math_chain = MedicalMathChain(config.llm)
        self.validator = FactCheckerChain(config.llm)
        
        # Agents using RAG get config.rag_retriever
        self.ayush_chain = AyushChain(config.llm, config.rag_retriever)
        self.yoga_chain = YogaChain(config.llm, config.rag_retriever)

    async def run(self, user_input: str, query_for_classification: str, user_profile: Any = None) -> Dict[str, Any]:
        """Execute the workflow"""
        


    async def run(self, user_input: str, query_for_classification: str, user_profile: Any = None) -> Dict[str, Any]:
        """Execute the workflow"""
        
        # Step 0: Profile Extraction (Background)
        profile_update = None
        if user_profile:
            print("📝 [STEP 0/3] Checking for Medical Profile Updates...")
            profile_update = self.profile_extractor.run(user_input, user_profile)
            if profile_update:
                # Update the profile object (User Profile is an SQLAlchemy model object typically, but might need careful handling)
                import json
                
                if profile_update.get("age"): user_profile.age = profile_update["age"]
                if profile_update.get("gender"): user_profile.gender = profile_update["gender"]
                
                # Update JSON lists
                def update_json_list(current_json, new_items):
                    current = json.loads(current_json) if current_json else []
                    if isinstance(new_items, list):
                        for item in new_items:
                            if item not in current:
                                current.append(item)
                    return json.dumps(current)

                if profile_update.get("new_conditions"):
                    user_profile.medical_history = update_json_list(user_profile.medical_history, profile_update["new_conditions"])
                if profile_update.get("new_allergies"):
                    user_profile.allergies = update_json_list(user_profile.allergies, profile_update["new_allergies"])
                if profile_update.get("new_medications"):
                    user_profile.medications = update_json_list(user_profile.medications, profile_update["new_medications"])
                    
                print("   ✓ Profile object updated in memory")
        
        # Step 1: Safety check
        print("🛡️  [STEP 1/3] Running Safety Guardrail Check...")
        safety_check = self.guardrail.check(query_for_classification)
        if not safety_check.get("is_safe", True):
            return {"status": "blocked", "reason": safety_check.get("reason")}
        print("   ✓ Content is safe\n")
        
        # Step 2: Classify intent
        print("🎯 [STEP 2/3] Classifying Intent...")
        classification = self.classifier.run(query_for_classification)
        intent = classification.get("classification")
        print(f"   → Intent: {intent}\n")
        
        # Step 3: Route to appropriate chain (using the clean user_input)
        print(f"🔗 [STEP 3/3] Executing Chain for '{intent}'...")
        result = {"intent": intent, "reasoning": classification.get("reasoning"), "output": None, "profile_updated": bool(profile_update)}
        
        if intent == "government_scheme_support":
            result["output"] = self.gov_scheme_chain.run(user_input)
            
        elif intent == "health_advisory":
            result["output"] = self.advisory_chain.run(user_input)
            
        elif intent == "medical_calculation":
            math_result = self.math_chain.run(user_input)
            result["output"] = f"**Calculation Result:** {math_result.get('result')}\n\n**Steps:**\n" + "\n".join([f"- {s}" for s in math_result.get('steps', [])])
            
        elif intent == "mental_wellness_support":
            wellness_res = self.mental_wellness_chain.run(user_input)
            yoga_res = self.yoga_chain.run(user_input)
            
            result["output"] = f"{wellness_res}\n\n### 🧘 Yoga for Mental Wellness\n{yoga_res}"
            
            # Add YouTube videos for Yoga
            try:
                videos = await search_videos(f"yoga for mental wellness {user_input}")
                result["yoga_videos"] = videos
            except Exception as e:
                print(f"⚠️ Failed to fetch YouTube videos: {e}")
            
        elif intent == "ayush_support":
            result["output"] = self.ayush_chain.run(user_input)
            
        elif intent == "symptom_checker":
            result.update(await self._handle_symptoms(user_input))
            
        elif intent == "facility_locator_support":
            result["output"] = self.hospital_chain.run(user_input)
            
        else:
            result["output"] = "I couldn't understand your request. Please try rephrasing."
        
        print("   ✓ Chain execution complete\n")
        
        # Step 4: Validate Medical Advice
        if intent in ["symptom_checker", "ayush_support", "health_advisory"] or (isinstance(result.get("output"), str) and "symptom" in result["output"].lower()):
            output_content = result.get("output")
            # Handle dictionary output (e.g. from symptom checker)
            if isinstance(output_content, dict):
                 # For now, just skip complex dict validation or validate the 'message' part
                 pass 
            elif isinstance(output_content, str):
                print("🩺 [STEP 4/4] Validating Medical Advice...")
                validation = self.validator.validate(user_input, output_content)
                if not validation.get("is_safe", True):
                    print(f"   ⚠️ Unsafe content detected: {validation.get('reason')}")
                    result["output"] = validation.get("revised_response") or "I cannot provide a response to this query due to safety concerns. Please consult a doctor immediately."
                    result["validation_status"] = "blocked"
                else:
                    print("   ✓ Validation passed")

        return result
    
    async def _handle_symptoms(self, user_input: str) -> Dict[str, Any]:
        """Handle symptom checking with multi-agent follow-up"""
        # 1. Fast Keyword/Regex Check
        is_emergency, reason = self.emergency_detector.check_emergency(user_input)
        
        # 2. LLM Assessment (if not already detected)
        if not is_emergency:
            symptom_data = self.symptom_chain.run(user_input)
            is_emergency = symptom_data.is_emergency
            result = {"symptom_assessment": symptom_data.model_dump()}
        else:
            # Create a dummy symptom data object for consistency if needed, or just proceed
            # For now, we'll just skip the detailed extraction if it's a clear emergency
            result = {"symptom_assessment": {"is_emergency": True, "symptoms": [reason], "severity": 10}}

        if is_emergency:
            hospital_query = f"Find nearest emergency hospitals for: {user_input}"
            hospital_list = self.hospital_chain.run(hospital_query)
            
            result["output"] = f"""# ⚠️ URGENT MEDICAL OBSERVATION
**Immediate attention recommended.**
Reason: {reason or "Critical symptoms detected"}

**Call Emergency Services (108/112)**

### 🏥 Nearby Emergency Facilities
{hospital_list}
"""
        else:
            symptom_text = f"Patient has {', '.join(symptom_data.symptoms)} with severity {symptom_data.severity}/10"
            
            # Run agents in parallel or sequence
            ayurveda_rec = self.ayush_chain.run(f"Provide ayurvedic remedies for: {symptom_text}")
            yoga_rec = self.yoga_chain.run(f"Suggest yoga for: {symptom_text}")
            wellness_rec = self.mental_wellness_chain.run(f"Provide wellness advice for: {symptom_text}")
            
            # Store raw results for specific frontend components if needed
            result["ayurveda_recommendations"] = ayurveda_rec
            # result["yoga_recommendations"] = yoga_rec # Commented out to avoid duplicate display in frontend (now included in main output)
            result["general_guidance"] = wellness_rec
            
            # Construct unified Markdown Output to ensure visibility
            unified_output = "Based on your symptoms, here are some recommendations:\n\n"
            
            unified_output += f"### 🌿 Ayurveda & Natural Remedies\n{ayurveda_rec}\n\n"
            unified_output += f"### 🧘 Yoga & Breathing\n{yoga_rec}\n\n"
            unified_output += f"### 🧠 Mental Wellness & General Advice\n{wellness_rec}\n"
            
            result["output"] = unified_output
            
            # Add YouTube videos for Yoga
            try:
                videos = await search_videos(f"yoga for {', '.join(symptom_data.symptoms)}")
                result["yoga_videos"] = videos
            except Exception as e:
                print(f"⚠️ Failed to fetch YouTube videos: {e}")
        
        return result