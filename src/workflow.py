import logging
from typing import Dict, Any
from langdetect import detect, LangDetectException

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

logger = logging.getLogger(__name__)

class HealthcareWorkflow:
    """Main workflow orchestrator with multi-language support."""
    
    def __init__(self, config: HealthcareConfig):
        self.config = config
        self.guardrail = GuardrailChain(config.llm)
        self.classifier = IntentClassifierChain(config.llm)
        self.symptom_chain = SymptomCheckerChain(config.llm)
        self.gov_scheme_chain = GovernmentSchemeChain(config.llm, config.search_tool)
        self.mental_wellness_chain = MentalWellnessChain(config.llm, config.search_tool)
        self.hospital_chain = HospitalLocatorChain(config.llm, config.search_tool)
        
        if config.rag_retriever:
            self.ayush_chain = AyushChain(config.llm, config.rag_retriever)
            self.yoga_chain = YogaChain(config.llm, config.rag_retriever)
        else:
            self.ayush_chain = self.yoga_chain = None

    # --- NEW: Helper method for translation ---
    def _translate_text(self, text: str, target_language: str, source_language: str = "auto") -> str:
        """Translates text using the LLM."""
        if not text or target_language == source_language:
            return text
        
        try:
            prompt = f"Translate the following text from {source_language} to {target_language}. Respond ONLY with the translated text, nothing else:\n\n{text}"
            response = self.config.llm.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text # Fallback to original text on error

    def run(self, user_input: str, query_for_classification: str) -> Dict[str, Any]:
        """Execute the workflow with multi-language support."""
        
        # --- MULTI-LANGUAGE SUPPORT: Step 1 & 2 - Detect and Translate to English ---
        try:
            detected_lang = detect(user_input)
        except LangDetectException:
            detected_lang = 'en' # Default to English if detection fails
        
        print(f"🌍 Language Detected: {detected_lang}")

        english_user_input = user_input
        english_query_for_classification = query_for_classification

        if detected_lang != 'en':
            print(f"   -> Translating input from '{detected_lang}' to 'en' for processing...")
            english_user_input = self._translate_text(user_input, 'en', source_language=detected_lang)
            # We translate the full context query as well for better classification
            english_query_for_classification = self._translate_text(query_for_classification, 'en', source_language=detected_lang)
            print(f"   ✓ Translated Query: {english_user_input}")

        # --- CORE WORKFLOW (Operates on English text) ---
        
        # Step 1: Safety check on the English query
        print("🛡️  [STEP 1/3] Running Safety Guardrail Check...")
        safety_check = self.guardrail.check(english_query_for_classification)
        if not safety_check.get("is_safe", True):
            return {"status": "blocked", "reason": safety_check.get("reason")}
        print("   ✓ Content is safe\n")
        
        # Step 2: Classify intent on the English query
        print("🎯 [STEP 2/3] Classifying Intent...")
        classification = self.classifier.run(english_query_for_classification)
        intent = classification.get("classification")
        print(f"   → Intent: {intent}\n")
        
        # Step 3: Route to appropriate chain using the clean English query
        print(f"🔗 [STEP 3/3] Executing Chain for '{intent}'...")
        result = {"intent": intent, "reasoning": classification.get("reasoning"), "output": None}

        if intent in ["ayush_support", "yoga_support"] and not self.ayush_chain:
            result["output"] = "My internal knowledge base for AYUSH and Yoga is currently unavailable."
        elif intent == "ayush_support":
            result["output"] = self.ayush_chain.run(english_user_input)
        elif intent == "government_scheme_support":
            result["output"] = self.gov_scheme_chain.run(english_user_input)
        elif intent == "mental_wellness_support":
            result["output"] = self.mental_wellness_chain.run(english_user_input)
            if self.yoga_chain:
                 result["yoga_recommendations"] = self.yoga_chain.run(english_user_input)
        elif intent == "symptom_checker":
            result.update(self._handle_symptoms(english_user_input))
        elif intent == "facility_locator_support":
            result["output"] = self.hospital_chain.run(english_user_input)
        else:
            result["output"] = "I couldn't understand your request. Please try rephrasing."
        
        print("   ✓ Chain execution complete\n")

        # --- MULTI-LANGUAGE SUPPORT: Step 4 - Translate Response Back ---
        if detected_lang != 'en':
            print(f"   -> Translating final response back to '{detected_lang}'...")
            
            # Fields to translate
            fields_to_translate = ['output', 'yoga_recommendations', 'ayurveda_recommendations', 'general_guidance']
            
            for field in fields_to_translate:
                if field in result and result[field]:
                    # Handle nested dictionaries (like in symptom checker)
                    if isinstance(result[field], dict) and 'message' in result[field]:
                        original_message = result[field]['message']
                        result[field]['message'] = self._translate_text(original_message, detected_lang, source_language='en')
                    elif isinstance(result[field], str):
                        original_text = result[field]
                        result[field] = self._translate_text(original_text, detected_lang, source_language='en')
            print("   ✓ Translation complete.")

        return result

    def _handle_symptoms(self, user_input: str) -> Dict[str, Any]:
        symptom_data = self.symptom_chain.run(user_input)
        result = {"symptom_assessment": symptom_data.model_dump()}
        
        if symptom_data.is_emergency:
            hospital_query = f"Find nearest emergency hospitals for: {', '.join(symptom_data.symptoms)}"
            result["output"] = {"emergency": True, "message": "⚠️ URGENT: Seek immediate medical attention. Call emergency services."}
            result["hospital_locator"] = self.hospital_chain.run(hospital_query)
        else:
            symptom_text = f"Patient has {', '.join(symptom_data.symptoms)} with severity {symptom_data.severity}/10"
            result["output"] = {"emergency": False, "message": "Based on your symptoms, here are some recommendations:"}
            if self.ayush_chain:
                result["ayurveda_recommendations"] = self.ayush_chain.run(f"Provide ayurvedic remedies for: {symptom_text}")
            if self.yoga_chain:
                result["yoga_recommendations"] = self.yoga_chain.run(f"Suggest yoga for: {symptom_text}")
            result["general_guidance"] = self.mental_wellness_chain.run(f"Provide wellness advice for: {symptom_text}")
        
        return result