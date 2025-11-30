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
    HospitalLocatorChain
)
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
        
        # Agents using WEB SEARCH get config.search_tool
        self.gov_scheme_chain = GovernmentSchemeChain(config.llm, config.search_tool)
        self.mental_wellness_chain = MentalWellnessChain(config.llm, config.search_tool)
        self.hospital_chain = HospitalLocatorChain(config.llm, config.search_tool)
        
        # Agents using RAG get config.rag_retriever
        self.ayush_chain = AyushChain(config.llm, config.rag_retriever)
        self.yoga_chain = YogaChain(config.llm, config.rag_retriever)

    async def run(self, user_input: str, query_for_classification: str) -> Dict[str, Any]:
        """Execute the workflow"""
        
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
        result = {"intent": intent, "reasoning": classification.get("reasoning"), "output": None}
        
        if intent == "government_scheme_support":
            result["output"] = self.gov_scheme_chain.run(user_input)
            
        elif intent == "mental_wellness_support":
            result["output"] = self.mental_wellness_chain.run(user_input)
            # Yoga is RAG-based, so it will use the RAG retriever
            result["yoga_recommendations"] = self.yoga_chain.run(user_input)
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
            result["output"] = {
                "emergency": True,
                "message": "⚠️ URGENT: Seek immediate medical attention. Call emergency services (108/112).",
                "reason": reason or "Critical symptoms detected"
            }
            result["hospital_locator"] = self.hospital_chain.run(hospital_query)
        else:
            symptom_text = f"Patient has {', '.join(symptom_data.symptoms)} with severity {symptom_data.severity}/10"
            result["output"] = {"emergency": False, "message": "Based on your symptoms, here are some recommendations:"}
            # All follow-up recommendations for symptoms will use the RAG system
            result["ayurveda_recommendations"] = self.ayush_chain.run(f"Provide ayurvedic remedies for: {symptom_text}")
            result["yoga_recommendations"] = self.yoga_chain.run(f"Suggest yoga for: {symptom_text}")
            
            # Add YouTube videos for Yoga
            try:
                videos = await search_videos(f"yoga for {', '.join(symptom_data.symptoms)}")
                result["yoga_videos"] = videos
            except Exception as e:
                print(f"⚠️ Failed to fetch YouTube videos: {e}")

            result["general_guidance"] = self.mental_wellness_chain.run(f"Provide wellness advice for: {symptom_text}")
        
        return result