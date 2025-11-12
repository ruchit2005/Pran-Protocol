# Healthcare Multi-Agent Workflow

An intelligent healthcare support system using LangChain and OpenAI with multi-agent architecture.

## Features

- 🛡️ **Safety Guardrails** - Content filtering and PII protection
- 🎯 **Intent Classification** - Smart routing to specialized agents
- 🩺 **Symptom Checker** - Emergency detection with hospital routing
- 💊 **Multi-Agent Recommendations**:
  - 🌿 Ayurvedic remedies
  - 🧘 Yoga therapy
  - 💡 Wellness guidance
- 🏥 **Government Schemes** - Health insurance and benefits
- 🧠 **Mental Wellness** - Support and resources
- 📍 **Hospital Locator** - Find nearby facilities

## Project Structure

```
.
├── src/
│   ├── __init__.py           # Package initialization
│   ├── config.py             # Configuration management
│   ├── schemas.py            # Data models
│   ├── workflow.py           # Main workflow orchestrator
│   └── chains/
│       ├── __init__.py
│       ├── base_chains.py    # Core chain implementations
│       └── specialized_chains.py  # Domain-specific chains
├── cli.py                    # Interactive CLI interface
├── requirements.txt          # Python dependencies
├── .env.example             # Example environment variables
├── .env                     # Your actual API keys (not in git)
└── README.md               # This file
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit the `.env` file and add your API keys:

```env
OPENAI_API_KEY=sk-your-actual-openai-key-here
TAVILY_API_KEY=tvly-your-actual-tavily-key-here
```

#### Getting API Keys

- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Tavily API Key**: Get free key from [Tavily](https://tavily.com) (1000 searches/month free)

### 3. Run the Application

```bash
python cli.py
```

or

```bash
./cli.py
```

## Usage

### Interactive CLI

The CLI provides a stateful chat interface with history:

```bash
$ python cli.py
🏥 Healthcare Assistant - Initializing...
✓ Ready!

Commands: 'exit' to quit, 'clear' to clear history, 'history' to view

You: I have a backache for 2 days
```

### Commands

- `exit` - Quit the application
- `clear` - Clear conversation history
- `history` - View conversation history

### Programmatic Usage

```python
from src import HealthcareConfig, HealthcareWorkflow

# Configuration (loads from .env automatically)
config = HealthcareConfig()

# Initialize workflow
workflow = HealthcareWorkflow(config)

# Process query
result = workflow.run("I have a headache and fever")
print(result)
```

## Workflow Architecture

```
User Query
    ↓
🛡️ Safety Guardrail Check
    ↓
🎯 Intent Classification
    ↓
🔗 Route to Specialized Agent
    ↓
┌─────────────────────┐
│ Government Schemes  │ → Search & Recommend
│ Mental Wellness     │ → Support + Yoga
│ AYUSH Support       │ → Traditional Medicine
│ Symptom Checker     │ → Assess → Multi-Agent:
│                     │   ├─ Emergency? → Hospital Locator
│                     │   └─ Non-Emergency? → Ayurveda + Yoga + Wellness
│ Hospital Locator    │ → Find Facilities
└─────────────────────┘
```

## Security

- ✅ Never commit your `.env` file to version control
- ✅ The `.env` file is already listed in `.gitignore`
- ✅ Built-in guardrails for PII and harmful content
- ✅ Medical emergencies are not blocked and routed appropriately
- ✅ Keep your API keys secure and don't share them

## Development

### Adding New Chains

1. Create a new chain class in `src/chains/specialized_chains.py`
2. Add it to `src/chains/__init__.py`
3. Initialize in `src/workflow.py`
4. Add routing logic in the `run()` method

### Verbose Debugging

The CLI runs with verbose logging enabled. You'll see:
- Safety check results
- Intent classification
- Chain execution steps
- Agent invocations
- Search queries and results

## License

MIT
