# Quick Reference: Multi-Agent RAG System

## 🚀 Quick Start

### 1. Ingest Documents to Specific Collections

```bash
# Yoga documents → yoga_collection
python ingest.py ingest-local --directory data/yoga_docs --collection yoga

# AYUSH documents → ayush_collection  
python ingest.py ingest-local --directory data/ayurveda_docs --collection ayush

# Symptoms/Medical → symptoms_collection
python ingest.py ingest-local --directory data/medical_docs --collection symptoms

# General documents → default collection
python ingest.py ingest-local --directory data/raw
```

### 2. Test the System

```bash
python demo_multi_agent.py
```

### 3. Start Backend & Frontend

```bash
# Terminal 1 - Backend
cd e:\Pran-Protocol\Pran-Protocol
venv\Scripts\activate
python -m uvicorn api:app --reload

# Terminal 2 - Frontend
cd e:\Pran-Protocol\Pran-Protocol\frontend
npm run dev
```

---

## 📋 Available Collections

| Domain | Collection Name | Use Case |
|--------|----------------|----------|
| `yoga` | `yoga_collection` | Yoga poses, pranayama, practices |
| `ayush` | `ayush_collection` | Ayurveda, herbs, traditional medicine |
| `mental_wellness` | `mental_wellness_collection` | Mental health resources |
| `symptoms` | `symptoms_collection` | Medical conditions, symptoms |
| `schemes` | `schemes_collection` | Government healthcare schemes |
| (none) | `documents` | General/fallback collection |

---

## 💬 Query Examples

### Single-Domain
```
"Suggest yoga poses for back pain"
→ YogaChain only
```

### Multi-Domain (Auto-detected)
```
"I have stress and want yoga and ayurvedic remedies"
→ YogaChain + AyushChain (parallel) → Fusion
```

---

## 🔧 Common Commands

### Ingest
```bash
# Local directory
python ingest.py ingest-local --directory PATH --collection DOMAIN

# Google Drive
python ingest.py ingest-gdrive --folder-id ID --collection DOMAIN
```

### Reset
```bash
# Reset specific collection
python ingest.py reset --collection yoga

# Reset all
python ingest.py reset
```

### Check Collections
```python
from src.config import HealthcareConfig
config = HealthcareConfig()

for domain, manager in config.chroma_managers.items():
    print(f"{domain}: {manager.get_collection_stats()}")
```

---

## ⚙️ Configuration

### Adjust Confidence Threshold
**File:** `src/workflow.py`
```python
CONFIDENCE_THRESHOLD = 0.6  # Lower = more agents triggered
```

### Add New Collection
**File:** `config/settings.py`
```python
COLLECTION_NAMES: Dict[str, str] = Field(default={
    ...
    "new_domain": "new_collection_name"
})
```

---

## 🐛 Troubleshooting

### "No documents found"
```bash
# Check collection stats
python -c "from src.config import HealthcareConfig; c = HealthcareConfig(); print(c.chroma_managers['yoga'].get_collection_stats())"

# Ingest documents
python ingest.py ingest-local --directory data/your_docs --collection yoga
```

### Multi-domain not triggering
- Check confidence scores in logs
- Lower threshold in `src/workflow.py`
- Make query more explicit about multiple domains

### Import errors
```bash
# Fix sentence-transformers dependency
pip install sentence-transformers==2.2.2 --upgrade
pip install huggingface-hub --upgrade
```

---

## 📚 Documentation

- **Full Guide:** `MULTI_AGENT_GUIDE.md`
- **Implementation Details:** `IMPLEMENTATION_SUMMARY.md`
- **Demo Script:** `demo_multi_agent.py`

---

## 🎯 Key Benefits

✅ Better precision (domain-specific search)  
✅ Faster retrieval (smaller collections)  
✅ Cross-domain intelligence (multi-agent fusion)  
✅ Scalable (add agents independently)  
✅ Backward compatible (no breaking changes)

---

## 📞 Need Help?

1. Check logs for detailed execution traces
2. Run `python demo_multi_agent.py` to test
3. Review `MULTI_AGENT_GUIDE.md` for detailed docs
