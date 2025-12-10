# Multi-Agent RAG System Guide

## Overview

The healthcare system now supports **multi-agent orchestration** with **domain-specific RAG databases** and **response fusion**. This allows for more precise retrieval and comprehensive cross-domain answers.

---

## Architecture

### Domain-Specific Collections

Each specialized agent has its own ChromaDB collection:

- **`yoga_collection`** → YogaChain
- **`ayush_collection`** → AyushChain  
- **`mental_wellness_collection`** → MentalWellnessChain (if RAG-enabled)
- **`symptoms_collection`** → SymptomCheckerChain (medical knowledge)
- **`schemes_collection`** → GovernmentSchemeChain (if RAG-enabled)
- **`documents`** → General/fallback collection

### Multi-Agent Workflow

```
User Query
    ↓
1. Safety Guardrail Check
    ↓
2. Intent Classification (Multi-domain detection)
    ↓
3a. Single Agent Execution        3b. Multi-Agent Parallel Execution
    └→ Direct Response                 ├→ Yoga Agent (RAG)
                                       ├→ AYUSH Agent (RAG)
                                       ├→ Mental Wellness (Search)
                                       └→ Response Fusion
    ↓
4. Final Unified Response
```

---

## Ingesting Documents

### Basic Usage

**Ingest to general collection:**
```bash
python ingest.py ingest-local --directory data/raw
```

**Ingest to specific domain:**
```bash
python ingest.py ingest-local --directory data/yoga_docs --collection yoga
python ingest.py ingest-local --directory data/ayurveda_docs --collection ayush
python ingest.py ingest-local --directory data/symptoms_db --collection symptoms
```

### Available Collections

- `yoga` - Yoga practices, asanas, pranayama
- `ayush` - Ayurveda, Unani, Siddha, Homeopathy
- `mental_wellness` - Mental health resources
- `symptoms` - Medical symptom knowledge
- `schemes` - Government healthcare schemes

### From Google Drive

```bash
python ingest.py ingest-gdrive --folder-id YOUR_FOLDER_ID --collection yoga
```

### Reset Collection

```bash
# Reset specific collection
python ingest.py reset --collection yoga

# Reset general collection
python ingest.py reset
```

---

## Query Examples

### Single-Domain Queries

**Input:** "I have back pain, suggest yoga poses"
- **Intent:** yoga_support
- **Execution:** YogaChain → yoga_collection
- **Response:** Yoga recommendations with citations

### Multi-Domain Queries

**Input:** "I have anxiety and want yoga and herbal remedies"
- **Intents Detected:**
  - yoga_support (0.9)
  - ayush_support (0.85)
  - mental_wellness_support (0.8)
- **Execution:** 
  1. YogaChain → yoga_collection
  2. AyushChain → ayush_collection
  3. MentalWellnessChain → Web Search
- **Response Fusion:** Combined coherent answer with all recommendations

---

## Configuration

### Collection Names

Edit `config/settings.py`:

```python
COLLECTION_NAMES: Dict[str, str] = Field(default={
    "yoga": "yoga_collection",
    "ayush": "ayush_collection",
    "mental_wellness": "mental_wellness_collection",
    "symptoms": "symptoms_collection",
    "government_schemes": "schemes_collection",
    "general": "documents"
})
```

### Confidence Threshold

In `src/workflow.py`, adjust multi-domain detection threshold:

```python
CONFIDENCE_THRESHOLD = 0.6  # Only run agents with confidence >= 0.6
```

---

## Benefits

✅ **Better Precision** - Each agent searches only relevant documents  
✅ **Faster Retrieval** - Smaller collections = faster search  
✅ **Optimized Embeddings** - Domain-specific models possible  
✅ **Cross-Domain Intelligence** - Combine insights from multiple domains  
✅ **Scalability** - Add new agents/collections independently  
✅ **Transparency** - See individual agent responses before fusion  

---

## API Response Format

### Single-Domain Response
```json
{
  "intent": "yoga_support",
  "is_multi_domain": false,
  "output": "Practice Tadasana for stability [Source: yoga_basics.pdf]...",
  "reasoning": "User is asking about yoga practices",
  "yoga_videos": [...]
}
```

### Multi-Domain Response
```json
{
  "intent": "yoga_support",
  "all_intents": [
    {"intent": "yoga_support", "confidence": 0.9},
    {"intent": "ayush_support", "confidence": 0.85}
  ],
  "is_multi_domain": true,
  "output": "**Yoga Practices:**\n- Shavasana...\n\n**Ayurvedic Remedies:**\n- Ashwagandha...",
  "individual_responses": {
    "yoga_support": "...",
    "ayush_support": "..."
  },
  "reasoning": "Multi-domain query involving yoga and traditional medicine",
  "yoga_videos": [...]
}
```

---

## Troubleshooting

### Issue: "No documents found in collection"

**Solution:** Ingest documents into the specific collection:
```bash
python ingest.py ingest-local --directory data/your_docs --collection yoga
```

### Issue: Multi-domain not triggering

**Possible causes:**
- Confidence scores below threshold (default 0.6)
- Query too specific to one domain
- LLM not detecting multiple intents

**Solution:** Check classification output in logs or lower threshold

### Issue: Response quality degraded

**Solution:** 
- Check if documents are in correct collections
- Verify chunk quality with `chroma_manager.get_collection_stats()`
- Adjust CHUNK_SIZE in `config/settings.py`

---

## Development

### Adding a New Domain

1. **Add collection name** to `config/settings.py`:
```python
COLLECTION_NAMES = {
    ...
    "nutrition": "nutrition_collection"
}
```

2. **Create specialized chain** in `src/chains/specialized_chains.py`

3. **Update workflow** in `src/workflow.py` to initialize and route to new chain

4. **Update intent classifier** prompt to include new domain

5. **Ingest documents:**
```bash
python ingest.py ingest-local --directory data/nutrition_docs --collection nutrition
```

---

## Performance Tips

1. **Optimize chunk size** per domain:
   - Yoga: 300-400 tokens (specific instructions)
   - Medical: 500-700 tokens (context needed)
   - Schemes: 800-1000 tokens (policy details)

2. **Use reranking** for better precision (already enabled)

3. **Monitor collection sizes:**
```python
from src.config import HealthcareConfig
config = HealthcareConfig()
for domain, manager in config.chroma_managers.items():
    print(f"{domain}: {manager.get_collection_stats()}")
```

4. **Adjust top_k** per domain in retriever calls

---

## Future Enhancements

- [ ] Query decomposition for better sub-query generation
- [ ] Citation tracking and provenance
- [ ] A/B testing single vs multi-agent responses
- [ ] User feedback loop for response quality
- [ ] Automated collection routing based on document metadata
- [ ] Cross-collection semantic search when needed
- [ ] Agent performance monitoring and optimization

---

**Need Help?** Check the logs or run with verbose mode for detailed execution traces.
