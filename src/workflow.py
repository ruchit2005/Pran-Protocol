"""
Main healthcare workflow with multi-agent orchestration
"""
import asyncio
from typing import Dict, Any, List
from .config import HealthcareConfig
from .chains import (
    GuardrailChain,
    IntentClassifierChain,
    SymptomCheckerChain,
    ResponseFusionChain,
    GovernmentSchemeChain,
    MentalWellnessChain,
    YogaChain,
    AyushChain,
    HospitalLocatorChain
)
from .utils.emergency import HybridEmergencyDetector
from .utils.youtube_client import search_videos

class HealthcareWorkflow:
    """Main workflow orchestrator for hybrid RAG/Search system with multi-agent support"""
    
    def __init__(self, config: HealthcareConfig):
        self.config = config
        
        # Initialize core chains
        self.guardrail = GuardrailChain(config.llm)
        self.classifier = IntentClassifierChain(config.llm)
        self.symptom_chain = SymptomCheckerChain(config.llm)
        self.fusion_chain = ResponseFusionChain(config.llm)
        self.emergency_detector = HybridEmergencyDetector()
        
        # Agents using domain-specific RAG retrievers
        yoga_retriever = config.get_retriever('yoga') or config.rag_retriever
        ayush_retriever = config.get_retriever('ayush') or config.rag_retriever
        schemes_retriever = config.get_retriever('government_schemes') or config.rag_retriever
        mental_wellness_retriever = config.get_retriever('mental_wellness') or config.rag_retriever
        
        # RAG-only agents (no web search for medical advice)
        self.ayush_chain = AyushChain(config.llm, ayush_retriever)
        self.yoga_chain = YogaChain(config.llm, yoga_retriever)
        self.mental_wellness_chain = MentalWellnessChain(config.llm, mental_wellness_retriever)
        
        # Agents that can use web search
        self.gov_scheme_chain = GovernmentSchemeChain(config.llm, schemes_retriever, config.search_tool)
        self.hospital_chain = HospitalLocatorChain(config.llm, config.search_tool)

    async def run(self, user_input: str, query_for_classification: str) -> Dict[str, Any]:
        """Execute the workflow with multi-agent orchestration"""
        
        # Step 1: Safety check
        print("🛡️  [STEP 1/4] Running Safety Guardrail Check...")
        safety_check = self.guardrail.check(query_for_classification)
        if not safety_check.get("is_safe", True):
            return {"status": "blocked", "reason": safety_check.get("reason")}
        print("   ✓ Content is safe\n")
        
        # Step 2: Classify intent (now returns multiple intents)
        print("🎯 [STEP 2/4] Classifying Intent...")
        classification = self.classifier.run(query_for_classification)
        primary_intent = classification.get("primary_intent")
        all_intents = classification.get("all_intents", [])
        is_multi_domain = classification.get("is_multi_domain", False)
        
        print(f"   → Primary Intent: {primary_intent}")
        if is_multi_domain:
            print(f"   → Multi-domain query detected: {len(all_intents)} intents")
            for intent_obj in all_intents:
                print(f"      - {intent_obj['intent']} (confidence: {intent_obj['confidence']:.2f})")
        print()
        
        # Step 3: Execute agent(s)
        if is_multi_domain and len(all_intents) > 1:
            # Multi-agent execution with fusion
            result = await self._execute_multi_agent(user_input, all_intents, classification)
        else:
            # Single agent execution (legacy path)
            result = await self._execute_single_agent(user_input, primary_intent, classification)
        
        print("   ✓ Workflow execution complete\n")
        return result
    
    async def _execute_single_agent(self, user_input: str, intent: str, classification: Dict) -> Dict[str, Any]:
        """Execute a single agent (legacy behavior)"""
        print(f"🔗 [STEP 3/4] Executing Single Agent for '{intent}'...\n")
        result = {"intent": intent, "reasoning": classification.get("reasoning"), "output": None, "is_multi_domain": False}
        
        if intent == "general_conversation":
            # Handle greetings and casual conversation
            greetings = ["hello", "hi", "hey", "namaste", "greetings"]
            thanks = ["thank", "thanks", "appreciate"]
            
            lower_input = user_input.lower()
            if any(word in lower_input for word in greetings):
                result["output"] = "Namaste! 🙏 I'm DeepShiva, your holistic health companion. How can I support your well-being today?"
            elif any(word in lower_input for word in thanks):
                result["output"] = "You're most welcome! 🙏 Feel free to ask if you have any other health-related questions. Stay healthy!"
            else:
                result["output"] = "I'm here to help with your health and wellness needs. You can ask me about yoga, Ayurveda, government health schemes, symptoms, or finding healthcare facilities. How may I assist you?"
        
        elif intent == "government_scheme_support":
            result["output"] = self.gov_scheme_chain.run(user_input)
            
        elif intent == "mental_wellness_support":
            result["output"] = self.mental_wellness_chain.run(user_input)
            result["yoga_recommendations"] = self.yoga_chain.run(user_input)
            try:
                videos = await search_videos(f"yoga for mental wellness {user_input}")
                result["yoga_videos"] = videos
            except Exception as e:
                print(f"⚠️ Failed to fetch YouTube videos: {e}")
            
        elif intent == "ayush_support":
            result["output"] = self.ayush_chain.run(user_input)
        
        elif intent == "yoga_support":
            result["output"] = self.yoga_chain.run(user_input)
            try:
                videos = await search_videos(f"yoga {user_input}")
                result["yoga_videos"] = videos
            except Exception as e:
                print(f"⚠️ Failed to fetch YouTube videos: {e}")
            
        elif intent == "symptom_checker":
            result.update(await self._handle_symptoms(user_input))
            
        elif intent == "facility_locator_support":
            result["output"] = self.hospital_chain.run(user_input)
            
        else:
            result["output"] = "I couldn't understand your request. Please try rephrasing."
        
        return result
    
    async def _execute_multi_agent(self, user_input: str, all_intents: List[Dict], classification: Dict) -> Dict[str, Any]:
        """Execute multiple agents in parallel and fuse their responses"""
        print(f"🔗 [STEP 3/4] Executing Multi-Agent Orchestration...")
        print(f"   → Running {len(all_intents)} agents in parallel...\n")
        
        # Filter intents with confidence > threshold
        CONFIDENCE_THRESHOLD = 0.6
        relevant_intents = [
            intent_obj for intent_obj in all_intents 
            if intent_obj['confidence'] >= CONFIDENCE_THRESHOLD
        ]
        
        if not relevant_intents:
            # Fallback to primary intent
            primary = classification.get("primary_intent")
            return await self._execute_single_agent(user_input, primary, classification)
        
        # Start YouTube video search early (if yoga is involved) - runs in parallel with agents
        youtube_task = None
        if any('yoga' in intent_obj['intent'] for intent_obj in relevant_intents):
            print(f"   🎥 Launching YouTube search in parallel...")
            youtube_task = asyncio.create_task(search_videos(f"yoga {user_input}"))
        
        # Execute agents in parallel
        agent_tasks = []
        intent_names = []
        
        for intent_obj in relevant_intents:
            intent = intent_obj['intent']
            intent_names.append(intent)
            print(f"   🤖 Launching {intent.replace('_', ' ').title()} Agent...")
            # Wrap synchronous agent calls in executor for true parallelism
            agent_tasks.append(asyncio.to_thread(self._run_agent_sync, intent, user_input))
        
        print(f"   ⏳ Waiting for {len(agent_tasks)} agents to complete...\n")
        
        # Gather results in parallel
        responses = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        # Build response dict
        agent_responses = {}
        for intent, response in zip(intent_names, responses):
            if isinstance(response, Exception):
                print(f"   ❌ Agent {intent} failed: {response}")
            elif response:
                print(f"   ✅ {intent.replace('_', ' ').title()} Agent completed")
                agent_responses[intent] = response
            else:
                print(f"   ⚠️  {intent.replace('_', ' ').title()} Agent returned empty response")
        
        print(f"   → Collected {len(agent_responses)} agent responses\n")
        
        # Step 4: Fuse responses
        print("🔀 [STEP 4/4] Fusing Agent Responses...\n")
        if len(agent_responses) > 1:
            fused_output = self.fusion_chain.fuse(user_input, agent_responses)
        else:
            # Only one response, use it directly
            fused_output = list(agent_responses.values())[0] if agent_responses else "No response generated."
        
        result = {
            "intent": classification.get("primary_intent"),
            "all_intents": all_intents,
            "is_multi_domain": True,
            "reasoning": classification.get("reasoning"),
            "output": fused_output,
            "individual_responses": agent_responses  # For debugging/transparency
        }
        
        # Wait for YouTube results (if started)
        if youtube_task:
            try:
                print(f"   🎥 Waiting for YouTube results...")
                videos = await youtube_task
                if videos:
                    result["yoga_videos"] = videos
                    print(f"   ✅ YouTube search completed - {len(videos)} videos found")
                else:
                    print(f"   ⚠️ YouTube search returned no videos")
            except Exception as e:
                print(f"   ⚠️ YouTube search failed: {e}")
        
        return result
    
    def _run_agent_sync(self, intent: str, user_input: str) -> str:
        """Run a specific agent synchronously (will be called in thread pool)"""
        try:
            agent_name = intent.replace('_', ' ').title()
            
            if intent == "government_scheme_support":
                print(f"      [{agent_name}] Using Web Search...")
                return self.gov_scheme_chain.run(user_input)
            elif intent == "mental_wellness_support":
                print(f"      [{agent_name}] Using Web Search...")
                return self.mental_wellness_chain.run(user_input)
            elif intent == "ayush_support":
                print(f"      [{agent_name}] Using RAG → ayush_collection")
                return self.ayush_chain.run(user_input)
            elif intent == "yoga_support":
                print(f"      [{agent_name}] Using RAG → yoga_collection")
                return self.yoga_chain.run(user_input)
            elif intent == "facility_locator_support":
                print(f"      [{agent_name}] Using Web Search...")
                return self.hospital_chain.run(user_input)
            else:
                return None
        except Exception as e:
            print(f"      ❌ Error in {intent} agent: {e}")
            return None
    
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