# api.py — FINAL CLEAN WORKING VERSION

import logging
import tempfile
import os
from uuid import uuid4
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from openai import OpenAI

# Internal modules
from src.config import HealthcareConfig
from src.workflow import HealthcareWorkflow


# -------------------------------------------------------
# FASTAPI APP SETUP
# -------------------------------------------------------
app = FastAPI(title="Healthcare RAG Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------
# GLOBALS
# -------------------------------------------------------
workflow: HealthcareWorkflow | None = None
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Single audio folder for TTS
AUDIO_DIR = os.path.join(os.getcwd(), "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)


# -------------------------------------------------------
# INIT WORKFLOW ON STARTUP
# -------------------------------------------------------
@app.on_event("startup")
def load_workflow():
    global workflow
    logging.info("Initializing Healthcare workflow...")

    try:
        config = HealthcareConfig()
        workflow = HealthcareWorkflow(config)
        logging.info("Workflow initialized successfully.")
    except Exception as e:
        logging.error(f"Workflow initialization failed: {e}", exc_info=True)
        workflow = None


# -------------------------------------------------------
# REQUEST MODELS
# -------------------------------------------------------
class ChatMessage(BaseModel):
    query: str

class ChatHistory(BaseModel):
    query: str
    intent: str


# -------------------------------------------------------
# STANDARD CHAT ENDPOINT
# -------------------------------------------------------
@app.post("/chat", response_model=Dict[str, Any])
async def handle_chat(message: ChatMessage, history: List[ChatHistory] = []):
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow not initialized.")

    logging.info(f"Received query: {message.query}")

    # Build simple history context
    history_context = ""
    if history:
        history_context += "\n\nPrevious conversation:\n"
        for i, msg in enumerate(history[-5:], 1):
            history_context += f"{i}. User: {msg.query}\n   Intent: {msg.intent}\n"

    try:
        result = await workflow.run(
            user_input=message.query,
            query_for_classification=message.query + history_context
        )
        return result

    except Exception as e:
        logging.error(f"Error during workflow execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal workflow error.")


# -------------------------------------------------------
# VOICE CHAT ENDPOINT (Whisper → Workflow → TTS)
# -------------------------------------------------------
@app.post("/chat/voice")
async def chat_voice(file: UploadFile = File(...)):
    """
    Handles voice queries:
    - Saves audio file
    - Transcribes using Whisper
    - Runs workflow
    - Generates TTS audio reply (mp3)
    - Returns transcript + assistant JSON + audio URL
    """
    if not workflow:
        raise HTTPException(status_code=503, detail="Workflow not initialized.")

    try:
        # 1️⃣ Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(await file.read())
            audio_path = tmp.name

        # 2️⃣ Whisper transcription
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )

        text = transcription.text.strip()
        print(f"[VOICE INPUT] {text}")

        # 3️⃣ Run healthcare workflow
        result = await workflow.run(
            user_input=text,
            query_for_classification=text
        )

        # Get the assistant output (string-safe)
        raw_output = result.get("output") if isinstance(result, dict) else result
        tts_input = raw_output if isinstance(raw_output, str) else str(raw_output)

        print("🧩 TTS Input:", tts_input[:200])

        # 4️⃣ Generate TTS audio (mp3)
        filename = f"{uuid4().hex}.mp3"
        tts_path = os.path.join(AUDIO_DIR, filename)

        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=tts_input,
            response_format="mp3"
        )

        with open(tts_path, "wb") as f:
            f.write(speech.read())

        print("🧩 Saved:", tts_path, "size:", os.path.getsize(tts_path))

        # 5️⃣ Return combined JSON
        base_url = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:8000")

        return JSONResponse({
            "text": text,
            "assistant": result,
            "audio_url": f"{base_url}/audio/{filename}",
        })

    except Exception as e:
        logging.error(f"Voice processing failed: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


# -------------------------------------------------------
# STATIC AUDIO SERVING
# -------------------------------------------------------
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(file_path, media_type="audio/mpeg")


# -------------------------------------------------------
# ROOT
# -------------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "Healthcare Agent API is running."}


# -------------------------------------------------------
# RUN SERVER (DEV)
# -------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
