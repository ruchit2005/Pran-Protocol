# In api.py

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

# Import your working config class and workflow
from src.config import HealthcareConfig
from src.workflow import HealthcareWorkflow

# --- API Setup (same as before) ---
app = FastAPI(title="Healthcare RAG Agent API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global variable for the workflow ---
workflow = None

@app.on_event("startup")
def load_workflow():
    """
    This function runs once when the API server starts.
    It mimics the setup() method from your working CLI.
    """
    global workflow
    logging.info("Application startup: Initializing services and workflow...")
    try:
        # 1. Create the single HealthcareConfig object
        config = HealthcareConfig()
        # 2. Pass this config object to the workflow
        workflow = HealthcareWorkflow(config)
        logging.info("Workflow initialized successfully via HealthcareConfig.")
    except Exception as e:
        logging.error(f"Failed to initialize workflow: {e}", exc_info=True)
        workflow = None

# --- Pydantic Models for Request/Response (same as before) ---
class ChatMessage(BaseModel):
    query: str

class ChatHistory(BaseModel):
    query: str
    intent: str

# --- API Endpoint (same as before) ---
@app.post("/chat", response_model=Dict[str, Any])
async def handle_chat(message: ChatMessage, history: List[ChatHistory] = []):
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow is not available or failed to initialize.")

    logging.info(f"Received query: {message.query}")

    # Format history exactly as the CLI does
    history_context = ""
    if history:
        history_context += "\n\nPrevious conversation:\n"
        for i, msg in enumerate(history[-5:], 1):
            history_context += f"{i}. User: {msg.query}\n   Intent: {msg.intent}\n"
    
    query_for_classification = message.query + history_context

    try:
        result = workflow.run(
            user_input=message.query,
            query_for_classification=query_for_classification
        )
        return result
    except Exception as e:
        logging.error(f"Error during workflow execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@app.get("/")
def read_root():
    return {"status": "Healthcare Agent API is running."}