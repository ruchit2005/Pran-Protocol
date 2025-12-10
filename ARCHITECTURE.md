# System Architecture: Multi-Agent RAG Healthcare System

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          User Interface                              │
│                     (Frontend / API / CLI)                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Healthcare Workflow                               │
│                   (Multi-Agent Orchestrator)                         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
    ┌──────────────────┐      ┌──────────────────┐
    │ Safety Guardrail │      │ Emergency        │
    │ Chain            │      │ Detector         │
    └──────────────────┘      └──────────────────┘
                │
                ▼
    ┌──────────────────────────────┐
    │ Intent Classifier Chain       │
    │ (Multi-Domain Detection)      │
    │                               │
    │ Returns:                      │
    │ • primary_intent              │
    │ • all_intents (w/ confidence) │
    │ • is_multi_domain             │
    └──────────┬───────────────────┘
               │
               ├─── Single Domain? ──────────┐
               │                              │
               ├─── Multi Domain? ────────┐   │
               │                           │   │
               ▼                           ▼   ▼
┌──────────────────────────┐   ┌────────────────────────┐
│ Single Agent Execution   │   │ Parallel Multi-Agent   │
│                          │   │ Execution              │
└──────────────────────────┘   └────────────────────────┘
               │                           │
               │                           ▼
               │              ┌─────────────────────────┐
               │              │ Agent 1: Yoga           │
               │              │ • yoga_collection       │
               │              └─────────────────────────┘
               │              ┌─────────────────────────┐
               │              │ Agent 2: AYUSH          │
               │              │ • ayush_collection      │
               │              └─────────────────────────┘
               │              ┌─────────────────────────┐
               │              │ Agent 3: Mental Wellness│
               │              │ • Web Search / RAG      │
               │              └─────────────────────────┘
               │                           │
               │                           ▼
               │              ┌─────────────────────────┐
               │              │ Response Fusion Chain   │
               │              │ • Merge responses       │
               │              │ • Remove duplicates     │
               │              │ • Preserve citations    │
               │              └─────────────────────────┘
               │                           │
               └───────────┬───────────────┘
                           │
                           ▼
               ┌──────────────────────┐
               │ Final Unified         │
               │ Response              │
               └──────────────────────┘
```

---

## Component Details

### 1. Intent Classifier (Enhanced)

**Input:** User query  
**Output:** Multi-domain classification

```json
{
  "primary_intent": "yoga_support",
  "all_intents": [
    {"intent": "yoga_support", "confidence": 0.9},
    {"intent": "ayush_support", "confidence": 0.85},
    {"intent": "mental_wellness_support", "confidence": 0.7}
  ],
  "is_multi_domain": true,
  "reasoning": "Query spans yoga, ayurveda, and mental wellness"
}
```

---

### 2. Multi-Agent Execution Engine

**Decision Flow:**
```python
if is_multi_domain and len(all_intents) > 1:
    # Parallel execution
    for intent in all_intents:
        if intent.confidence >= 0.6:
            run_agent_async(intent)
    
    # Fusion
    fused_response = fusion_chain.fuse(agent_responses)
else:
    # Single agent (legacy path)
    response = run_single_agent(primary_intent)
```

---

### 3. Domain-Specific RAG Collections

```
ChromaDB Structure:
├── yoga_collection/
│   ├── Embeddings: all-MiniLM-L6-v2
│   ├── Documents: Yoga poses, practices, instructions
│   └── Metadata: file_name, page, source
│
├── ayush_collection/
│   ├── Embeddings: all-MiniLM-L6-v2
│   ├── Documents: Ayurveda, herbs, remedies
│   └── Metadata: file_name, page, source
│
├── mental_wellness_collection/
│   ├── Embeddings: all-MiniLM-L6-v2
│   ├── Documents: Mental health resources
│   └── Metadata: file_name, page, source
│
├── symptoms_collection/
│   ├── Embeddings: all-MiniLM-L6-v2
│   ├── Documents: Medical symptoms, conditions
│   └── Metadata: file_name, page, source
│
└── documents/ (general fallback)
    ├── Embeddings: all-MiniLM-L6-v2
    ├── Documents: Mixed content
    └── Metadata: file_name, page, source
```

---

### 4. Specialized Agents

#### RAG-Based Agents
```
YogaChain
├── Retriever: yoga_collection
├── Reranker: Enabled
├── Strategist: Enabled
└── Output: Yoga recommendations with citations

AyushChain
├── Retriever: ayush_collection
├── Reranker: Enabled
├── Strategist: Enabled
└── Output: Ayurvedic remedies with citations
```

#### Search-Based Agents
```
MentalWellnessChain
├── Tool: Tavily Web Search
├── Query: "mental health support resources India {query}"
└── Output: Counseling strategies, resources

GovernmentSchemeChain
├── Tool: Tavily Web Search
├── Query: "India government health schemes {query}"
└── Output: Scheme details, eligibility

HospitalLocatorChain
├── Tool: Tavily Web Search
├── Query: "hospitals healthcare facilities near {location}"
└── Output: Facility listings
```

---

### 5. Response Fusion Chain

**Process:**
```
1. Collect individual agent responses
   ├── yoga_support: "Practice Shavasana..."
   ├── ayush_support: "Use Ashwagandha..."
   └── mental_wellness: "Try breathing exercises..."

2. Analyze and merge
   ├── Remove duplicate recommendations
   ├── Group by category (Yoga / Ayurveda / Wellness)
   ├── Preserve all citations [Source: filename]
   └── Create natural narrative flow

3. Generate unified response
   "Based on your anxiety concerns, here are holistic recommendations:
    
    **Yoga Practices**
    - Shavasana (Corpse Pose) for relaxation [Source: yoga_stress.pdf]
    - Anulom Vilom breathing [Source: pranayama_guide.txt]
    
    **Ayurvedic Remedies**
    - Ashwagandha for stress relief [Source: ayurveda_herbs.pdf]
    - Brahmi for mental clarity [Source: ayurveda_herbs.pdf]
    
    **Professional Support**
    - KIRAN Mental Health Helpline: 1800-599-0019
    - Consider cognitive behavioral therapy..."
```

---

## Data Flow Example

### Multi-Domain Query: "I have anxiety and want yoga and herbs"

```
Step 1: Safety Check
└─> ✓ Safe (no PII, no harmful content)

Step 2: Intent Classification
└─> Intents Detected:
    • yoga_support (0.9)
    • ayush_support (0.85)
    • mental_wellness_support (0.75)

Step 3: Agent Execution (Parallel)
├─> YogaChain
│   ├─> Query: "anxiety yoga practices"
│   ├─> Search: yoga_collection (5 chunks)
│   ├─> Rerank: Top 3 most relevant
│   └─> Generate: Yoga response with citations
│
├─> AyushChain
│   ├─> Query: "anxiety herbal remedies"
│   ├─> Search: ayush_collection (5 chunks)
│   ├─> Rerank: Top 3 most relevant
│   └─> Generate: Ayurveda response with citations
│
└─> MentalWellnessChain
    ├─> Query: "mental health support India anxiety"
    ├─> Tavily Search: Web results
    └─> Generate: Wellness response

Step 4: Response Fusion
├─> Input: 3 agent responses
├─> Process: Merge, deduplicate, organize
└─> Output: Unified coherent response

Step 5: Enhancements
└─> YouTube Search: "yoga for anxiety"
    └─> Add video recommendations

Final Response:
{
  "intent": "yoga_support",
  "is_multi_domain": true,
  "output": "**Comprehensive Anxiety Management**\n\n[Fused response]...",
  "yoga_videos": [...],
  "individual_responses": {...}
}
```

---

## Performance Characteristics

### Single-Domain Query
- **Latency:** ~2-3 seconds
- **Operations:** 1 agent execution
- **Database Queries:** 1 collection search
- **LLM Calls:** 3 (guardrail, classifier, agent)

### Multi-Domain Query (3 agents)
- **Latency:** ~3-5 seconds (parallel)
- **Operations:** 3 agents + fusion
- **Database Queries:** 2-3 collection searches (parallel)
- **LLM Calls:** 5 (guardrail, classifier, 3 agents, fusion)

### Scalability
- **Collections:** Unlimited (independent)
- **Agents:** Add without affecting others
- **Parallelism:** Async execution (non-blocking)

---

## Configuration Points

### 1. Collection Names
**File:** `config/settings.py`
```python
COLLECTION_NAMES = {...}
```

### 2. Confidence Threshold
**File:** `src/workflow.py`
```python
CONFIDENCE_THRESHOLD = 0.6
```

### 3. Retrieval Parameters
**File:** `config/settings.py`
```python
TOP_K = 5
SIMILARITY_THRESHOLD = 0.35
USE_RERANKING = True
```

### 4. Agent Initialization
**File:** `src/workflow.py`
```python
yoga_retriever = config.get_retriever('yoga')
self.yoga_chain = YogaChain(config.llm, yoga_retriever)
```

---

## Extension Points

### Adding a New Agent

1. **Create Collection**
   ```python
   # config/settings.py
   COLLECTION_NAMES['nutrition'] = 'nutrition_collection'
   ```

2. **Create Agent**
   ```python
   # src/chains/specialized_chains.py
   class NutritionChain(RAGBasedChain):
       def __init__(self, llm, retriever):
           system_prompt = "You are a nutrition advisor..."
           super().__init__(llm, retriever, system_prompt)
   ```

3. **Initialize in Workflow**
   ```python
   # src/workflow.py
   nutrition_retriever = config.get_retriever('nutrition')
   self.nutrition_chain = NutritionChain(config.llm, nutrition_retriever)
   ```

4. **Update Classifier**
   ```python
   # Add to intent classifier prompt
   "6. **nutrition_support**: Diet, nutrition queries"
   ```

5. **Add Routing**
   ```python
   # src/workflow.py._run_agent()
   elif intent == "nutrition_support":
       return self.nutrition_chain.run(user_input)
   ```

6. **Ingest Documents**
   ```bash
   python ingest.py ingest-local --directory data/nutrition --collection nutrition
   ```

---

## Monitoring & Debugging

### Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Track Agent Performance
```python
import time

start = time.time()
response = agent.run(query)
duration = time.time() - start
print(f"Agent took {duration:.2f}s")
```

### Inspect Collections
```python
from src.config import HealthcareConfig
config = HealthcareConfig()

for domain, manager in config.chroma_managers.items():
    stats = manager.get_collection_stats()
    print(f"{domain}: {stats['total_documents']} docs")
```

---

## Future Enhancements

- [ ] Query decomposition for complex multi-step queries
- [ ] Agent performance caching
- [ ] Dynamic confidence threshold adjustment
- [ ] Cross-collection semantic search
- [ ] User feedback loop for response quality
- [ ] A/B testing single vs multi-agent
- [ ] Agent chain visualization
- [ ] Collection auto-routing based on metadata
