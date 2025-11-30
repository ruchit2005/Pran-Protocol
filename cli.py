import os
from dotenv import load_dotenv

load_dotenv()

os.environ["LANGCHAIN_VERBOSE"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from src.config import HealthcareConfig
from src.workflow import HealthcareWorkflow


class HealthcareCLI:
    def __init__(self):
        self.history = []
        self.workflow = None

    def setup(self):
        print("🏥 Healthcare Assistant - Initializing Hybrid System...")

        try:
            # 1️⃣ Create same config used by FastAPI
            config = HealthcareConfig()

            # 2️⃣ Create workflow (same as API)
            self.workflow = HealthcareWorkflow(config)

            print("✓ Ready!\n")
            return True

        except Exception as e:
            print(f"❌ Error initializing workflow: {e}")
            return False

    def format_history(self):
        if not self.history:
            return ""

        context = "\n\nPrevious conversation:\n"
        for i, msg in enumerate(self.history[-5:], 1):
            context += f"{i}. User: {msg['query']}\n"
        return context

    def display_result(self, result: dict):
        print("\n" + "=" * 60)
        print(f"Intent: {result.get('intent', 'unknown')}")
        if result.get("reasoning"):
            print("\nReasoning:")
            print(result["reasoning"])

        print("\nResponse:")
        if result.get("output"):
            print(result["output"])

        if result.get("yoga_recommendations"):
            print("\n🧘 Yoga Recommendations:")
            print(result["yoga_recommendations"])

        print("=" * 60 + "\n")

    def run(self):
        if not self.setup():
            return

        print("Commands: exit, clear, history\n")

        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue

                if user_input.lower() == "exit":
                    print("\n👋 Goodbye!")
                    break

                if user_input.lower() == "clear":
                    self.history.clear()
                    print("🗑️ History cleared\n")
                    continue

                clean_user_input = user_input
                query_for_classification = user_input + self.format_history()

                print("\n🔍 Running Workflow...\n")

                import asyncio
                result = asyncio.run(self.workflow.run(
                    user_input=clean_user_input,
                    query_for_classification=query_for_classification,
                ))

                self.history.append({"query": user_input, "result": result})

                self.display_result(result)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break

            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    cli = HealthcareCLI()
    cli.run()
