"""
Main healthcare workflow with multi-agent orchestration
"""
import asyncio
from typing import Dict, Any, List
from .config import HealthcareConfig
from .chains import (
    GuardrailAndIntentChain,
    GuardrailChain,
    IntentClassifierChain,
    SymptomCheckerChain,
    ResponseFusionChain,
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
    """Main workflow orchestrator for hybrid RAG/Search system with multi-agent support"""
    
    def __init__(self, config: HealthcareConfig):
        self.config = config
        
        # === KEY 1 (PRIMARY): Critical path - high frequency, runs on every request ===
        print("   -> Initializing critical chains (Key 1)...")
        self.guardrail_and_intent = GuardrailAndIntentChain(config.llm_primary)  # Every request
        self.symptom_chain = SymptomCheckerChain(config.llm_primary)  # Common, complex
        self.validator = FactCheckerChain(config.llm_primary)  # Runs on all medical responses
        
        # === KEY 2 (SECONDARY): Specialized chains - lower frequency ===
        print("   -> Initializing specialized chains (Key 2)...")
        self.fusion_chain = ResponseFusionChain(config.llm_secondary)
        self.profile_extractor = ProfileExtractionChain(config.llm_secondary)
        self.advisory_chain = HealthAdvisoryChain(config.llm_secondary)
        self.math_chain = MedicalMathChain(config.llm_secondary)
        
        self.emergency_detector = HybridEmergencyDetector()
        
        # Agents using domain-specific RAG retrievers (all on Key 2)
        yoga_retriever = config.get_retriever('yoga') or config.rag_retriever
        ayush_retriever = config.get_retriever('ayush') or config.rag_retriever
        schemes_retriever = config.get_retriever('government_schemes') or config.rag_retriever
        mental_wellness_retriever = config.get_retriever('mental_wellness') or config.rag_retriever
        
        # RAG-only agents (no web search for medical advice) - Key 2
        self.ayush_chain = AyushChain(config.llm_secondary, ayush_retriever)
        self.yoga_chain = YogaChain(config.llm_secondary, yoga_retriever)
        self.mental_wellness_chain = MentalWellnessChain(config.llm_secondary, mental_wellness_retriever)
        
        # Agents that can use web search - Key 2
        self.gov_scheme_chain = GovernmentSchemeChain(config.llm_secondary, schemes_retriever, config.search_tool)
        self.hospital_chain = HospitalLocatorChain(config.llm_secondary, config.search_tool)
        
        print("   ✓ All chains initialized with load-balanced API keys")



    async def run(self, user_input: str, query_for_classification: str, user_profile: Any = None) -> Dict[str, Any]:
        """Execute the workflow"""
        
        # Create request-local cache to avoid concurrency issues
        query_optimization_cache = {}
            
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
                    # Handle various input types
                    if not current_json or current_json == "":
                        current = []
                    elif isinstance(current_json, str):
                        try:
                            current = json.loads(current_json)
                        except json.JSONDecodeError:
                            current = []
                    elif isinstance(current_json, list):
                        current = current_json
                    else:
                        current = []
                    
                    if isinstance(new_items, list):
                        for item in new_items:
                            if item not in current:
                                current.append(item)
                    return json.dumps(current)

                # Handle both dict and object-based profiles
                if isinstance(user_profile, dict):
                    if profile_update.get("new_conditions"):
                        user_profile["medical_history"] = update_json_list(user_profile.get("medical_history", "[]"), profile_update["new_conditions"])
                    if profile_update.get("new_allergies"):
                        user_profile["allergies"] = update_json_list(user_profile.get("allergies", "[]"), profile_update["new_allergies"])
                    if profile_update.get("new_medications"):
                        user_profile["medications"] = update_json_list(user_profile.get("medications", "[]"), profile_update["new_medications"])
                else:
                    if profile_update.get("new_conditions"):
                        user_profile.medical_history = update_json_list(user_profile.medical_history, profile_update["new_conditions"])
                    if profile_update.get("new_allergies"):
                        user_profile.allergies = update_json_list(user_profile.allergies, profile_update["new_allergies"])
                    if profile_update.get("new_medications"):
                        user_profile.medications = update_json_list(user_profile.medications, profile_update["new_medications"])
                    
                print("   ✓ Profile object updated in memory")
        
        # Step 1 & 2 MERGED: Safety check + Intent classification (1 API call)
        print("🛡️🎯 [STEP 1-2/4] Safety Check & Intent Classification (merged)...")
        combined_result = self.guardrail_and_intent.check_and_classify(query_for_classification)
        
        # Extract safety result
        if not combined_result.get("is_safe", True):
            return {"status": "blocked", "reason": combined_result.get("safety_reason")}
        print("   ✓ Content is safe")
        
        # Extract intent classification
        primary_intent = combined_result.get("primary_intent")
        all_intents = combined_result.get("all_intents", [])
        is_multi_domain = combined_result.get("is_multi_domain", False)
        
        print(f"   → Primary Intent: {primary_intent}")
        if is_multi_domain:
            print(f"   → Multi-domain query detected: {len(all_intents)} intents")
            for intent_obj in all_intents:
                print(f"      - {intent_obj['intent']} (confidence: {intent_obj['confidence']:.2f})")
        else:
            print(f"   → Single intent detected")
        print()
        
        # Step 3: Pre-optimize query once for all agents (use request-local cache)
        query_cache = {}
        self._preoptimize_query(user_input, query_cache)
        
        # Step 4: Execute agent(s)
        if is_multi_domain and len(all_intents) > 1:
            # Multi-agent execution with fusion
            result = await self._execute_multi_agent(user_input, all_intents, combined_result, query_cache)
        else:
            # Single agent execution (legacy path)
            result = await self._execute_single_agent(user_input, primary_intent, combined_result, query_cache, user_profile)
        
        # Step 5: Validate Medical Advice (skip for non-medical intents to save time)
        intent_to_check = result.get("intent")
        output_content = result.get("output")
        skip_validation_intents = ["general_conversation", "government_scheme_support", "facility_locator_support", "medical_calculation"]
        
        if intent_to_check not in skip_validation_intents and intent_to_check in ["symptom_checker", "ayush_support", "health_advisory", "mental_wellness_support", "yoga_support"]:
             if isinstance(output_content, str):
                print("🩺 [STEP 5/5] Validating Medical Advice...")
                validation = self.validator.validate(user_input, output_content)
                if not validation.get("is_safe", True):
                    # CRITICAL safety issue - block completely
                    print(f"   🚫 BLOCKED - Critical safety issue: {validation.get('reason')}")
                    result["output"] = validation.get("revised_response") or "I cannot provide a response to this query due to safety concerns. Please consult a doctor immediately."
                    result["validation_status"] = "blocked"
                elif validation.get("revised_response"):
                    # Safe but needs additional disclaimer/warning
                    print(f"   ⚠️ Adding safety disclaimer")
                    result["output"] = output_content + "\n\n⚠️ **Safety Note:** " + validation.get("revised_response")
                    result["validation_status"] = "safe_with_disclaimer"
                else:
                    print("   ✓ Validation passed")

        # Check if workflow updated the profile (pass back to API)
        result["profile_updated"] = bool(profile_update)

        print("   ✓ Workflow execution complete\n")
        return result
    
    def _preoptimize_query(self, query: str, query_cache: Dict) -> None:
        """Pre-optimize query once and cache it for all retrievers to use."""
        if query in query_cache:
            return  # Already optimized
        
        # Access any retriever's query optimizer (they all share the same LLM)
        retriever = self.config.get_retriever('yoga') or self.config.rag_retriever
        if retriever and hasattr(retriever, 'query_optimizer') and retriever.query_optimizer:
            optimizer = retriever.query_optimizer
            if optimizer.enabled:
                optimized = optimizer.optimize_query(query)
                query_cache[query] = optimized
                if optimized != query:
                    print(f"💾 [CACHE] Query optimized and cached: '{query}' -> '{optimized}'")
                else:
                    print(f"💾 [CACHE] Query cached as-is (no optimization needed): '{query}'")
    
    def get_optimized_query(self, query: str, query_cache: Dict) -> str:
        """Get cached optimized query if available."""
        return query_cache.get(query, query)
    
    async def _execute_single_agent(self, user_input: str, intent: str, classification: Dict, query_cache: Dict = None, user_profile: Any = None) -> Dict[str, Any]:
        """Execute a single agent (legacy behavior)"""
        if query_cache is None:
            query_cache = {}
            
        # PRE-OPTIMIZE query ONCE
        self._preoptimize_query(user_input, query_cache)
        
        # Inject cache into all retrievers
        for retriever in self.config.rag_retrievers.values():
            retriever._query_cache = query_cache
            
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
            
        elif intent == "health_advisory":
            result["output"] = self.advisory_chain.run(user_input)
            
        elif intent == "medical_calculation":
            math_result = self.math_chain.run(user_input)
            result["output"] = f"**Calculation Result:** {math_result.get('result')}\n\n**Steps:**\n" + "\n".join([f"- {s}" for s in math_result.get('steps', [])])
            
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
            result.update(await self._handle_symptoms(user_input, user_profile))
            
        elif intent == "facility_locator_support":
            result["output"] = self.hospital_chain.run(user_input)
            
        else:
            result["output"] = "I couldn't understand your request. Please try rephrasing."
        

        return result
    
    async def _execute_multi_agent(self, user_input: str, all_intents: List[Dict], classification: Dict, query_cache: Dict = None) -> Dict[str, Any]:
        """Execute unified retrieval + single generation instead of multiple agents"""
        if query_cache is None:
            query_cache = {}
            
        print(f"🔗 [STEP 3/4] Unified Multi-Domain Response Generation...")
        
        # PRE-OPTIMIZE query ONCE
        self._preoptimize_query(user_input, query_cache)
        optimized_query = self.get_optimized_query(user_input, query_cache)
        
        # Filter intents with confidence > threshold
        CONFIDENCE_THRESHOLD = 0.6
        relevant_intents = [
            intent_obj for intent_obj in all_intents 
            if intent_obj['confidence'] >= CONFIDENCE_THRESHOLD
        ]
        
        # Filter out general_conversation if there's a more specific medical intent
        medical_intents = ['symptom_checker', 'ayush_support', 'yoga_support', 
                          'mental_wellness_support', 'health_advisory', 
                          'government_scheme_support', 'facility_locator_support']
        
        has_medical_intent = any(
            intent_obj['intent'] in medical_intents 
            for intent_obj in relevant_intents
        )
        
        if has_medical_intent:
            original_count = len(relevant_intents)
            relevant_intents = [
                intent_obj for intent_obj in relevant_intents
                if intent_obj['intent'] != 'general_conversation'
            ]
            if len(relevant_intents) < original_count:
                print(f"   🔍 Filtered out general_conversation (medical intent takes priority)")
        
        if not relevant_intents:
            primary = classification.get("primary_intent")
            return await self._execute_single_agent(user_input, primary, classification, None, user_profile)
        
        print(f"   → Retrieving from {len(relevant_intents)} knowledge domains in parallel...")
        
        # Parallel retrieval from all relevant RAG collections
        # Fetch MORE documents initially (will rerank to get best ones)
        INITIAL_FETCH_COUNT = 20  # Fetch 20 from each domain
        FINAL_COUNT = 10  # After reranking, keep top 10 overall
        
        retrieval_tasks = []
        domain_names = []
        
        for intent_obj in relevant_intents:
            intent = intent_obj['intent']
            
            # Only retrieve from RAG-based domains
            if intent == 'ayush_support':
                domain_names.append('Ayurveda')
                retrieval_tasks.append(asyncio.to_thread(
                    self.config.rag_retrievers['ayush'].get_relevant_documents, 
                    optimized_query
                ))
            elif intent == 'yoga_support':
                domain_names.append('Yoga')
                retrieval_tasks.append(asyncio.to_thread(
                    self.config.rag_retrievers['yoga'].get_relevant_documents, 
                    optimized_query
                ))
            elif intent == 'government_scheme_support':
                domain_names.append('Government Schemes')
                retrieval_tasks.append(asyncio.to_thread(
                    self.config.rag_retrievers['schemes'].get_relevant_documents, 
                    optimized_query
                ))
        
        # Get all documents in parallel
        if retrieval_tasks:
            print(f"   📚 Fetching relevant documents from: {', '.join(domain_names)}")
            all_docs = await asyncio.gather(*retrieval_tasks, return_exceptions=True)
            
            # Combine all documents from all domains for reranking
            all_retrieved_docs = []
            domain_doc_counts = {}
            
            for domain, docs in zip(domain_names, all_docs):
                if isinstance(docs, Exception):
                    print(f"   ⚠️ {domain} retrieval failed: {docs}")
                elif docs:
                    all_retrieved_docs.extend(docs)
                    domain_doc_counts[domain] = len(docs)
                    print(f"   ✅ {domain}: {len(docs)} documents retrieved")
                else:
                    print(f"   ⚠️ {domain}: No documents found")
            
            # Rerank all documents together to get globally best results
            if all_retrieved_docs and len(all_retrieved_docs) > FINAL_COUNT:
                print(f"   🔄 Reranking {len(all_retrieved_docs)} documents across all domains...")
                
                # Get reranker from any retriever (they share the same instance)
                sample_retriever = self.config.rag_retrievers.get('ayush') or self.config.rag_retrievers.get('yoga')
                
                if sample_retriever and hasattr(sample_retriever, 'reranker') and sample_retriever.reranker:
                    reranked_docs = sample_retriever.reranker.rerank(
                        query=optimized_query,
                        documents=all_retrieved_docs,
                        top_k=FINAL_COUNT
                    )
                    print(f"   ✨ Reranked to top {len(reranked_docs)} most relevant documents")
                    final_docs = reranked_docs
                else:
                    print(f"   ⚠️ Reranker not available, using top {FINAL_COUNT} from initial retrieval")
                    final_docs = all_retrieved_docs[:FINAL_COUNT]
            else:
                final_docs = all_retrieved_docs
            
            # Build context from final documents
            if final_docs:
                combined_context = "\n\n---\n\n".join([
                    f"[Source: {doc.metadata.get('source', 'Unknown')}]\n{doc.page_content}" 
                    for doc in final_docs
                ])
                
                print(f"   📝 Prepared {len(final_docs)} documents for LLM context")
            else:
                combined_context = "No relevant information found in knowledge base."
            
            # Generate single unified response with reranked context
            print(f"   🤖 Generating unified response...")
            
            # Use primary chain (symptom checker or ayush) with all context
            primary_intent = classification.get("primary_intent")
            
            unified_prompt = f"""You are a holistic healthcare assistant. Answer the user's query using the provided knowledge from multiple domains.

User Query: {user_input}

Available Knowledge (ranked by relevance):
{combined_context}

Provide a comprehensive response that integrates relevant information from all sources. Structure your response clearly with sections if multiple domains are relevant."""

            response = self.config.llm_primary.invoke(unified_prompt)
            
            result = {
                "intent": primary_intent,
                "all_intents": all_intents,
                "is_multi_domain": True,
                "reasoning": classification.get("reasoning"),
                "output": response.content,
                "domains_searched": domain_names,
                "documents_used": len(final_docs)
            }
            
        else:
            # No RAG domains, use direct agent execution
            print(f"   → No RAG domains detected, using direct agent execution")
            result = await self._execute_multi_agent_legacy(user_input, relevant_intents, classification, query_cache)
        
        return result
    
    async def _execute_multi_agent_legacy(self, user_input: str, relevant_intents: List[Dict], classification: Dict, query_cache: Dict = None) -> Dict[str, Any]:
        """Legacy multi-agent execution for non-RAG domains"""
        print(f"   → Running {len(relevant_intents)} agents in parallel...\n")
        
        # Extract all intents from classification or relevant_intents
        all_intents = classification.get("all_intents", relevant_intents)
        
        # PRE-OPTIMIZE query ONCE before launching agents (critical for performance)
        self._preoptimize_query(user_input, query_cache)
        
        # Inject cache into all retrievers so they use the optimized query
        for retriever in self.config.rag_retrievers.values():
            retriever._query_cache = query_cache
        
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
        
        # Step 4: Fuse responses (skip for 2 agents - just concatenate)
        if len(agent_responses) > 2:
            # Complex fusion for 3+ agents
            print("🔀 [STEP 4/4] Fusing Agent Responses...\n")
            fused_output = self.fusion_chain.fuse(user_input, agent_responses)
        elif len(agent_responses) == 2:
            # Simple concatenation for 2 agents (saves 3-5 seconds)
            print("📝 [STEP 4/4] Combining Agent Responses (fast mode)...\n")
            responses_list = list(agent_responses.items())
            fused_output = f"**{responses_list[0][0].replace('_', ' ').title()}:**\n\n{responses_list[0][1]}\n\n---\n\n**{responses_list[1][0].replace('_', ' ').title()}:**\n\n{responses_list[1][1]}"
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
            elif intent == "symptom_checker":
                print(f"      [{agent_name}] Analyzing symptoms...")
                # Run symptom handler synchronously
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                symptom_result = loop.run_until_complete(self._handle_symptoms(user_input, None))
                loop.close()
                return symptom_result.get("output", "")
            elif intent == "health_advisory":
                print(f"      [{agent_name}] Fetching health advisories...")
                return self.advisory_chain.run(user_input)
            elif intent == "general_conversation":
                # Handle greetings and casual conversation
                greetings = ["hello", "hi", "hey", "namaste", "greetings"]
                thanks = ["thank", "thanks", "appreciate"]
                lower_input = user_input.lower()
                if any(word in lower_input for word in greetings):
                    return "Namaste! 🙏 I'm DeepShiva, your holistic health companion. How can I support your well-being today?"
                elif any(word in lower_input for word in thanks):
                    return "You're most welcome! 🙏 Feel free to ask if you have any other health-related questions. Stay healthy!"
                else:
                    return "I'm here to help with your health and wellness needs. How may I assist you?"
            else:
                print(f"      ⚠️ No handler for intent: {intent}")
                return None
        except Exception as e:
            print(f"      ❌ Error in {intent} agent: {e}")
            return None
    
    async def _handle_symptoms(self, user_input: str, user_profile: Any = None) -> Dict[str, Any]:
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
            symptom_text = f"Patient has {', '.join(symptom_data.symptoms)}"
            
            # Run agents in PARALLEL for faster response
            print("      → Running RAG retrieval in parallel (Ayurveda, Yoga, Mental Wellness)...")
            
            async def get_all_recommendations():
                tasks = [
                    asyncio.to_thread(self.ayush_chain.run, f"Provide ayurvedic remedies for: {symptom_text}"),
                    asyncio.to_thread(self.yoga_chain.run, f"Suggest yoga for: {symptom_text}"),
                    asyncio.to_thread(self.mental_wellness_chain.run, f"Provide wellness advice for: {symptom_text}")
                ]
                return await asyncio.gather(*tasks)
            
            # Execute in parallel
            ayurveda_rec, yoga_rec, wellness_rec = await get_all_recommendations()
            print(f"      ✓ Parallel retrieval complete")
            
            # Filter out mental wellness if no relevant results
            wellness_not_found = (
                "could not find" in wellness_rec.lower() or
                "no information" in wellness_rec.lower() or
                "try rephrasing" in wellness_rec.lower() or
                len(wellness_rec.strip()) < 50
            )
            
            # Store raw results for specific frontend components if needed
            result["ayurveda_recommendations"] = ayurveda_rec
            if not wellness_not_found:
                result["general_guidance"] = wellness_rec
            
            # Construct unified output with only relevant sections
            sections = []
            sections.append(f"### 🌿 Ayurveda & Natural Remedies\n{ayurveda_rec}")
            sections.append(f"### 🧘 Yoga & Breathing\n{yoga_rec}")
            
            # Only add mental wellness if relevant results found
            if not wellness_not_found:
                sections.append(f"### 🧠 Mental Wellness & General Advice\n{wellness_rec}")
            
            # Final response generation
            print("      → Generating final response...")
            final_output = "Based on your symptoms, here are some recommendations:\n\n" + "\n\n".join(sections)
            
            # Add drug interaction warning if patient is on medications
            try:
                current_medications = []
                if user_profile is not None:
                    if isinstance(user_profile, dict):
                        medications = user_profile.get("medications", "[]")
                    else:
                        medications = user_profile.medications
                    
                    if medications and medications != "[]":
                        import json
                        if isinstance(medications, str):
                            try:
                                current_medications = json.loads(medications)
                            except:
                                current_medications = [m.strip() for m in medications.split(",") if m.strip()]
                        elif isinstance(medications, list):
                            current_medications = medications
                
                # Add medication warning if patient has medications
                if current_medications:
                    med_list = ", ".join(current_medications)
                    final_output += f"\n\n⚠️ **Important**: You are currently taking: {med_list}. Please consult your healthcare provider before starting any new herbal or Ayurvedic treatments to avoid potential drug interactions."
            except Exception as e:
                print(f"      ⚠️ Could not parse medications: {e}")
            
            result["output"] = final_output
            print("      ✓ Response generated")
            
            # Add YouTube videos for Yoga
            try:
                videos = await search_videos(f"yoga for {', '.join(symptom_data.symptoms)}")
                result["yoga_videos"] = videos
            except Exception as e:
                print(f"⚠️ Failed to fetch YouTube videos: {e}")
        
        return result    
    async def _format_and_verify_response(self, raw_response: str, symptom_context: str, current_medications: List[str] = None) -> str:
        """Format response beautifully, cross-check facts, and verify drug interactions"""
        
        # Build medication context
        medication_context = ""
        if current_medications and len(current_medications) > 0:
            medication_context = f"\n\n**CRITICAL - Patient's Current Medications**: {', '.join(current_medications)}\n**You MUST check for drug interactions between these allopathic medicines and any recommended Ayurvedic/herbal remedies.**"
        
        formatting_prompt = f"""You are a medical content formatter. Clean up and improve this response.

**FORMATTING RULES:**
- Keep it natural and conversational - NO excessive spacing or indentation
- Use single line breaks between items, double line breaks between sections only
- Headings: Use ### with emoji (e.g., ### 🌿 Ayurveda) - NO indentation
- DO NOT use numbered lists (1., 2., 3.) - use sections with headings instead
- Bullets: Use - at the START of line (no leading spaces)
- Sub-bullets: Only 2 spaces before - for sub-items
- Bold important terms: **Term Name:** followed by description on SAME line
- Keep all [Source: ...] citations exactly as they are
- NO blank lines between related items
- NO indentation anywhere
- NO general disclaimers (added separately)

**DRUG INTERACTION CHECK:**{medication_context}
- If patient has medications, check for interactions with recommended herbs
- Add ⚠️ Drug Interaction Note ONLY if there's a real concern
- Be specific: which herb + which medicine = what risk

**CONTENT QUALITY:**
- Verify medical accuracy
- Keep dosages and instructions clear
- Organize: Traditional remedies → Dietary advice → Lifestyle tips
- Each recommendation should be: **Name**: Description on same line

Context: {symptom_context}

Raw Response:
{raw_response}

Return the cleaned, natural-sounding response with NO indentation, NO numbered lists, and proper compact formatting."""
        
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a medical content expert who formats and verifies healthcare advice."),
            ("user", "{input}")
        ])
        
        chain = prompt | self.config.llm_secondary | StrOutputParser()
        formatted = await asyncio.to_thread(chain.invoke, {"input": formatting_prompt})
        
        print("      ✓ Response formatted and verified")
        return formatted