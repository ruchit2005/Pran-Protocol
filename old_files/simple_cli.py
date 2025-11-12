#!/usr/bin/env python3
"""
Minimal CLI interface for Healthcare Workflow with chat history
"""

import os
import sys
from dotenv import load_dotenv
from healthcare_workflow import HealthcareWorkflowConfig, HealthcareWorkflow

# Load environment variables
load_dotenv()

# Enable verbose LangChain debugging
os.environ["LANGCHAIN_VERBOSE"] = "true"
# Disable LangSmith tracing to avoid authentication warnings
os.environ["LANGCHAIN_TRACING_V2"] = "false"


class SimpleChatCLI:
    """Minimal stateful chat interface"""
    
    def __init__(self):
        self.history = []
        self.workflow = None
        
    def setup(self):
        """Initialize the workflow"""
        print("🏥 Healthcare Assistant - Initializing...")
        
        openai_key = os.getenv("OPENAI_API_KEY")
        tavily_key = os.getenv("TAVILY_API_KEY")
        
        if not openai_key or not tavily_key:
            print("❌ Error: API keys not found in .env file")
            print("Please create a .env file with:")
            print("  OPENAI_API_KEY=your-key")
            print("  TAVILY_API_KEY=your-key")
            return False
        
        try:
            config = HealthcareWorkflowConfig(
                openai_api_key=openai_key,
                tavily_api_key=tavily_key,
                model="gpt-4o-mini"
            )
            self.workflow = HealthcareWorkflow(config)
            print("✓ Ready!\n")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def format_history(self):
        """Format chat history for context"""
        if not self.history:
            return ""
        
        context = "\n\nPrevious conversation:\n"
        for i, msg in enumerate(self.history[-5:], 1):  # Last 5 messages
            context += f"{i}. User: {msg['query']}\n"
            if 'intent' in msg.get('result', {}):
                context += f"   Intent: {msg['result']['intent']}\n"
        return context
    
    def run(self):
        """Main chat loop"""
        if not self.setup():
            return
        
        print("Type 'exit' to quit, 'clear' to clear history\n")
        
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'exit':
                    print("\n👋 Goodbye!")
                    break
                
                if user_input.lower() == 'clear':
                    self.history.clear()
                    print("🗑️  History cleared\n")
                    continue
                
                if user_input.lower() == 'history':
                    print("\n📜 Chat History:")
                    if self.history:
                        for i, msg in enumerate(self.history, 1):
                            print(f"{i}. {msg['query']}")
                    else:
                        print("  (empty)")
                    print()
                    continue
                
                # Add context from history
                query_with_context = user_input
                if self.history:
                    query_with_context = user_input + self.format_history()
                
                # Process query
                print("\n" + "🔍 PROCESSING QUERY ".center(60, "="))
                print(f"Query: {user_input}")
                if self.history:
                    print(f"Context: Including last {min(5, len(self.history))} messages")
                print("="*60)
                
                print("\n🤔 Starting workflow...\n")
                result = self.workflow.run(query_with_context)
                print("\n✓ Workflow complete!")
                
                # Store in history (with original query, not context)
                self.history.append({
                    'query': user_input,
                    'result': result
                })
                
                # Display result
                print("\n" + "="*60)
                print(f"Intent: {result.get('intent', 'unknown').replace('_', ' ').title()}")
                
                if result.get('reasoning'):
                    print(f"Reasoning: {result['reasoning']}")
                
                print("-"*60)
                
                # Display specific results based on intent
                intent = result.get('intent', '')
                
                if 'government_scheme' in intent:
                    if result.get('schemes'):
                        print("\n📋 Government Schemes:")
                        for scheme in result['schemes'][:3]:
                            print(f"\n• {scheme.get('scheme_name', 'N/A')}")
                            print(f"  Target: {scheme.get('target_beneficiaries', 'N/A')}")
                            print(f"  Link: {scheme.get('official_link', 'N/A')}")
                
                elif 'symptom_checker' in intent:
                    if result.get('symptom_assessment'):
                        assessment = result['symptom_assessment']
                        print(f"\n🩺 Symptom Assessment:")
                        print(f"  Symptoms: {', '.join(assessment.get('symptoms', []))}")
                        print(f"  Severity: {assessment.get('severity', 'N/A')}/10")
                        print(f"  Duration: {assessment.get('duration', 'N/A')}")
                        print(f"  Age: {assessment.get('age', 'N/A')}")
                        if assessment.get('comorbidities'):
                            print(f"  Pre-existing conditions: {', '.join(assessment.get('comorbidities', []))}")
                        if assessment.get('is_emergency'):
                            print(f"  ⚠️  EMERGENCY - Seek immediate medical attention!")
                    
                    # Display Ayurveda recommendations
                    if result.get('ayurveda_recommendations'):
                        print(f"\n🌿 Ayurvedic Recommendations:")
                        ayur_text = result['ayurveda_recommendations']
                        # Wrap text at 70 characters
                        for line in ayur_text.split('\n'):
                            if line.strip():
                                print(f"  {line.strip()}")
                    
                    # Display Yoga recommendations
                    if result.get('yoga_recommendations'):
                        print(f"\n🧘 Yoga Recommendations:")
                        yoga_text = result['yoga_recommendations']
                        for line in yoga_text.split('\n'):
                            if line.strip():
                                print(f"  {line.strip()}")
                    
                    # Display Medical Guidance or General Guidance
                    if result.get('medical_guidance'):
                        print(f"\n💊 Medical Guidance:")
                        for line in result['medical_guidance'].split('\n'):
                            if line.strip():
                                print(f"  {line.strip()}")
                    elif result.get('general_guidance'):
                        print(f"\n💡 General Wellness Advice:")
                        for line in result['general_guidance'].split('\n'):
                            if line.strip():
                                print(f"  {line.strip()}")
                    
                    # Display emergency output if present
                    if result.get('output', {}).get('emergency'):
                        print(f"\n🚨 EMERGENCY ALERT:")
                        print(f"  {result['output'].get('message', '')}")
                        
                        if result.get('emergency_number'):
                            print(f"\n📞 Emergency Number: {result['emergency_number']}")
                        
                        if result.get('hospital_locator'):
                            print(f"\n🏥 Hospital Information:")
                            hosp_text = result['hospital_locator']
                            for line in str(hosp_text).split('\n'):
                                if line.strip():
                                    print(f"  {line.strip()}")
                
                elif 'mental_wellness' in intent:
                    if result.get('mental_health_response'):
                        print(f"\n🧠 Mental Health Support:")
                        print(f"  {result['mental_health_response']}")
                
                elif 'ayush' in intent:
                    if result.get('ayush_response'):
                        print(f"\n🌿 AYUSH Guidance:")
                        print(f"  {result['ayush_response']}")
                
                elif 'facility_locator' in intent:
                    if result.get('facilities'):
                        print(f"\n📍 Healthcare Facilities:")
                        for facility in result['facilities'][:3]:
                            print(f"\n• {facility.get('name', 'N/A')}")
                            print(f"  Address: {facility.get('address', 'N/A')}")
                            print(f"  Specialty: {facility.get('specialty', 'N/A')}")
                
                print("="*60 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Please try again.\n")


if __name__ == "__main__":
    cli = SimpleChatCLI()
    cli.run()
