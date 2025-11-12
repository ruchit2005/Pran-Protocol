import os
from dotenv import load_dotenv
load_dotenv()

os.environ["LANGCHAIN_VERBOSE"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Import the new config and workflow
from src.config import get_services
from src.workflow import HealthcareWorkflow # You will need to create a new HealthcareWorkflow that accepts services directly

class HealthcareCLI:
    def __init__(self):
        self.history = []
        self.workflow = None
        
    def setup(self):
        print("🏥 Healthcare Assistant - Initializing Hybrid System...")
        try:
            # Get all services from our singleton
            services = get_services()
            
            # Create a simple config-like object to pass to the workflow
            # This maintains the workflow's expected input structure
            class ConfigStub:
                def __init__(self):
                    self.llm = services.llm
                    self.search_tool = services.search_tool
                    self.rag_retriever = services.rag_retriever
            
            self.workflow = HealthcareWorkflow(ConfigStub())
            print("✓ Ready!\n")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def format_history(self):
        if not self.history: return ""
        context = "\n\nPrevious conversation:\n"
        for i, msg in enumerate(self.history[-5:], 1):
            context += f"{i}. User: {msg['query']}\n"
        return context

    def display_result(self, result: dict):
        print("\n" + "="*60)
        print(f"Intent: {result.get('intent', 'unknown').replace('_', ' ').title()}")
        if result.get('reasoning'): print(f"Reasoning: {result['reasoning']}")
        print("-"*60)
        # Simplified display logic for brevity
        if result.get('output'):
            print("\nℹ️ Response:")
            for line in str(result['output']).split('\n'): print(f"  {line.strip()}")
        if result.get('yoga_recommendations'):
            print("\n🧘 Yoga for Stress Relief:")
            for line in str(result['yoga_recommendations']).split('\n'): print(f"  {line.strip()}")
        print("="*60 + "\n")

    def run(self):
        if not self.setup(): return
        print("Commands: 'exit', 'clear', 'history'\n")
        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input: continue
                if user_input.lower() == 'exit': print("\n👋 Goodbye!"); break
                if user_input.lower() == 'clear': self.history.clear(); print("🗑️ History cleared\n"); continue
                
                clean_user_input = user_input
                query_for_classification = user_input + self.format_history()
                
                print("\n" + "🔍 PROCESSING QUERY ".center(60, "="))
                result = self.workflow.run(user_input=clean_user_input, query_for_classification=query_for_classification)
                print("✓ Workflow complete!")
                
                self.history.append({'query': user_input, 'result': result})
                self.display_result(result)
            except KeyboardInterrupt: print("\n\n👋 Goodbye!"); break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    cli = HealthcareCLI()
    cli.run()

# #!/usr/bin/env python3
# """
# Healthcare Assistant CLI with stateful chat history
# """

# import os
# import sys
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # Enable verbose logging but disable LangSmith tracing
# os.environ["LANGCHAIN_VERBOSE"] = "true"
# os.environ["LANGCHAIN_TRACING_V2"] = "false"

# from src import HealthcareConfig, HealthcareWorkflow


# class HealthcareCLI:
#     """Minimal stateful chat interface"""
    
#     def __init__(self):
#         self.history = []
#         self.workflow = None
        
#     def setup(self):
#         """Initialize the workflow"""
#         print("🏥 Healthcare Assistant - Initializing...")
        
#         try:
#             config = HealthcareConfig()
#             self.workflow = HealthcareWorkflow(config)
#             print("✓ Ready!\n")
#             return True
#         except Exception as e:
#             print(f"❌ Error: {e}")
#             print("\nMake sure you have a .env file with:")
#             print("  OPENAI_API_KEY=your-key")
#             print("  TAVILY_API_KEY=your-key")
#             return False
    
#     def format_history(self):
#         """Format chat history for context"""
#         if not self.history:
#             return ""
        
#         context = "\n\nPrevious conversation:\n"
#         for i, msg in enumerate(self.history[-5:], 1):
#             context += f"{i}. User: {msg['query']}\n"
#             if 'intent' in msg.get('result', {}):
#                 context += f"   Intent: {msg['result']['intent']}\n"
#         return context
    
#     def display_result(self, result: dict):
#         """Display formatted result"""
#         print("\n" + "="*60)
#         print(f"Intent: {result.get('intent', 'unknown').replace('_', ' ').title()}")
        
#         if result.get('reasoning'):
#             print(f"Reasoning: {result['reasoning']}")
        
#         print("-"*60)
        
#         intent = result.get('intent', '')
        
#         # Symptom Checker
#         if 'symptom_checker' in intent:
#             if result.get('symptom_assessment'):
#                 assessment = result['symptom_assessment']
#                 print(f"\n🩺 Symptom Assessment:")
#                 print(f"  Symptoms: {', '.join(assessment.get('symptoms', []))}")
#                 print(f"  Severity: {assessment.get('severity', 'N/A')}/10")
#                 print(f"  Duration: {assessment.get('duration', 'N/A')}")
#                 print(f"  Age: {assessment.get('age', 'N/A')}")
            
#             if result.get('output', {}).get('emergency'):
#                 print(f"\n🚨 EMERGENCY ALERT:")
#                 print(f"  {result['output'].get('message', '')}")
                
#                 if result.get('emergency_number'):
#                     print(f"\n📞 Emergency Number: {result['emergency_number']}")
                
#                 if result.get('hospital_locator'):
#                     print(f"\n🏥 Hospital Information:")
#                     for line in str(result['hospital_locator']).split('\n'):
#                         if line.strip():
#                             print(f"  {line.strip()}")
#             else:
#                 if result.get('ayurveda_recommendations'):
#                     print(f"\n🌿 Ayurvedic Recommendations:")
#                     for line in result['ayurveda_recommendations'].split('\n'):
#                         if line.strip():
#                             print(f"  {line.strip()}")
                
#                 if result.get('yoga_recommendations'):
#                     print(f"\n🧘 Yoga Recommendations:")
#                     for line in result['yoga_recommendations'].split('\n'):
#                         if line.strip():
#                             print(f"  {line.strip()}")
                
#                 if result.get('general_guidance'):
#                     print(f"\n💡 General Wellness Advice:")
#                     for line in result['general_guidance'].split('\n'):
#                         if line.strip():
#                             print(f"  {line.strip()}")
        
#         # Mental Wellness
#         elif 'mental_wellness' in intent:
#             if result.get('output'):
#                 print(f"\n🧠 Mental Health Support:")
#                 for line in str(result['output']).split('\n'):
#                     if line.strip():
#                         print(f"  {line.strip()}")
            
#             if result.get('yoga_recommendations'):
#                 print(f"\n🧘 Yoga for Stress Relief:")
#                 for line in result['yoga_recommendations'].split('\n'):
#                     if line.strip():
#                         print(f"  {line.strip()}")
        
#         # Government Schemes
#         elif 'government_scheme' in intent:
#             if result.get('output'):
#                 print(f"\n📋 Government Schemes:")
#                 for line in str(result['output']).split('\n'):
#                     if line.strip():
#                         print(f"  {line.strip()}")
        
#         # AYUSH Support
#         elif 'ayush' in intent:
#             if result.get('output'):
#                 print(f"\n🌿 AYUSH Guidance:")
#                 for line in str(result['output']).split('\n'):
#                     if line.strip():
#                         print(f"  {line.strip()}")
        
#         # Hospital Locator
#         elif 'facility_locator' in intent:
#             if result.get('output'):
#                 print(f"\n📍 Healthcare Facilities:")
#                 for line in str(result['output']).split('\n'):
#                     if line.strip():
#                         print(f"  {line.strip()}")
        
#         print("="*60 + "\n")
    
#     def run(self):
#         """Main chat loop"""
#         if not self.setup():
#             return
        
#         print("Commands: 'exit' to quit, 'clear' to clear history, 'history' to view\n")
        
#         while True:
#             try:
#                 user_input = input("You: ").strip()
                
#                 if not user_input:
#                     continue
                
#                 if user_input.lower() == 'exit':
#                     print("\n👋 Goodbye!")
#                     break
                
#                 if user_input.lower() == 'clear':
#                     self.history.clear()
#                     print("🗑️  History cleared\n")
#                     continue
                
#                 if user_input.lower() == 'history':
#                     print("\n📜 Chat History:")
#                     if self.history:
#                         for i, msg in enumerate(self.history, 1):
#                             print(f"{i}. {msg['query']}")
#                     else:
#                         print("  (empty)")
#                     print()
#                     continue

#                 clean_user_input = user_input
#                 query_for_classification = user_input
#                 if self.history:
#                     print(f"Context: Including last {min(5, len(self.history))} messages")
#                     query_for_classification += self.format_history()
                
#                 print("="*60 + "\n")
                
#                 print("🤔 Starting workflow...\n")
#                 result = self.workflow.run(user_input=clean_user_input, 
#                     query_for_classification=query_for_classification)
                
#                 print("\n✓ Workflow complete!")
                
#                 # Store in history
#                 self.history.append({
#                     'query': user_input,
#                     'result': result
#                 })
                
#                 # Display result
#                 self.display_result(result)
                
#             except KeyboardInterrupt:
#                 print("\n\n👋 Goodbye!")
#                 break
#             except Exception as e:
#                 print(f"\n❌ Error: {e}")
#                 import traceback
#                 traceback.print_exc()
#                 print()


# if __name__ == "__main__":
#     cli = HealthcareCLI()
#     cli.run()


# #!/usr/bin/env python3
# """
# Healthcare Assistant CLI with RAG-powered knowledge base
# """

# import os
# import sys
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # Enable verbose logging but disable LangSmith tracing
# os.environ["LANGCHAIN_VERBOSE"] = "false" # Set to true for detailed chain logs
# os.environ["LANGCHAIN_TRACING_V2"] = "false"


# class HealthcareCLI:
#     """Minimal stateful chat interface"""
    
#     def __init__(self):
#         self.history = []
#         self.workflow = None
    
#     def format_history(self):
#         """Format chat history for context"""
#         if not self.history:
#             return ""
        
#         context = "\n\nPrevious conversation:\n"
#         for i, msg in enumerate(self.history[-5:], 1):
#             context += f"{i}. User: {msg['query']}\n"
#             if 'intent' in msg.get('result', {}):
#                 context += f"   Intent: {msg['result']['intent']}\n"
#         return context
    
#     def display_result(self, result: dict):
#         """Display formatted result"""
#         print("\n" + "="*60)
#         print(f"Intent: {result.get('intent', 'unknown').replace('_', ' ').title()}")
        
#         if result.get('reasoning'):
#             print(f"Reasoning: {result['reasoning']}")
        
#         print("-"*60)
        
#         intent = result.get('intent', '')
        
#         # Symptom Checker
#         if 'symptom_checker' in intent:
#             if result.get('symptom_assessment'):
#                 assessment = result['symptom_assessment']
#                 print(f"\n🩺 Symptom Assessment:")
#                 print(f"  Symptoms: {', '.join(assessment.get('symptoms', []))}")
#                 print(f"  Severity: {assessment.get('severity', 'N/A')}/10")
#                 print(f"  Duration: {assessment.get('duration', 'N/A')}")
#                 print(f"  Age: {assessment.get('age', 'N/A')}")
            
#             if result.get('output', {}).get('emergency'):
#                 print(f"\n🚨 EMERGENCY ALERT:")
#                 print(f"  {result['output'].get('message', '')}")
                
#                 if result.get('emergency_number'):
#                     print(f"\n📞 Emergency Number: {result['emergency_number']}")
                
#                 if result.get('hospital_locator'):
#                     print(f"\n🏥 Hospital Information:")
#                     for line in str(result['hospital_locator']).split('\n'):
#                         if line.strip():
#                             print(f"  {line.strip()}")
#             else:
#                 if result.get('ayurveda_recommendations'):
#                     print(f"\n🌿 Ayurvedic Recommendations:")
#                     for line in result['ayurveda_recommendations'].split('\n'):
#                         if line.strip():
#                             print(f"  {line.strip()}")
                
#                 if result.get('yoga_recommendations'):
#                     print(f"\n🧘 Yoga Recommendations:")
#                     for line in result['yoga_recommendations'].split('\n'):
#                         if line.strip():
#                             print(f"  {line.strip()}")
                
#                 if result.get('general_guidance'):
#                     print(f"\n💡 General Wellness Advice:")
#                     for line in result['general_guidance'].split('\n'):
#                         if line.strip():
#                             print(f"  {line.strip()}")
        
#         # Other intents (simplified formatting)
#         else:
#             if result.get('output'):
#                 print(f"\nℹ️ Response:")
#                 for line in str(result['output']).split('\n'):
#                     if line.strip():
#                         print(f"  {line.strip()}")
            
#             if result.get('yoga_recommendations'):
#                 print(f"\n🧘 Yoga for Stress Relief:")
#                 for line in result['yoga_recommendations'].split('\n'):
#                     if line.strip():
#                         print(f"  {line.strip()}")
        
#         print("="*60 + "\n")
    
#     def run(self):
#         """Main chat loop"""
        
#         print("Your knowledge base is ready. You can ingest documents using 'ingest.py'.")
#         print("Commands: 'exit' to quit, 'clear' to clear history, 'history' to view\n")
        
#         while True:
#             try:
#                 user_input = input("You: ").strip()
                
#                 if not user_input: continue
#                 if user_input.lower() == 'exit': print("\n👋 Goodbye!"); break
#                 if user_input.lower() == 'clear': self.history.clear(); print("🗑️  History cleared\n"); continue
                
#                 if user_input.lower() == 'history':
#                     print("\n📜 Chat History:" + ("\n  (empty)" if not self.history else ""))
#                     for i, msg in enumerate(self.history, 1): print(f"{i}. {msg['query']}")
#                     print(); continue
                
#                 clean_user_input = user_input
#                 query_for_classification = user_input
#                 if self.history:
#                     print(f"Context: Including last {min(5, len(self.history))} messages")
#                     query_for_classification += self.format_history()
                
#                 print("="*60 + "\n")
                
#                 print("🤔 Starting workflow...\n")
#                 result = self.workflow.run(user_input=clean_user_input, 
#                     query_for_classification=query_for_classification)
#                 print("\n✓ Workflow complete!")
                
#                 self.history.append({'query': user_input, 'result': result})
#                 self.display_result(result)
                
#             except KeyboardInterrupt: print("\n\n👋 Goodbye!"); break
#             except Exception as e:
#                 print(f"\n❌ Error: {e}")
#                 import traceback
#                 traceback.print_exc()
#                 print()

# if __name__ == "__main__":
#     cli = HealthcareCLI()
#     cli.run()