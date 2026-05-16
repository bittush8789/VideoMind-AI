from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.transcript_service import extract_video_id, get_transcript, get_transcript_with_timestamps
from backend.rag_service import RAGService
from backend.prompts import SYSTEM_PROMPT, ANALYSIS_TASKS_PROMPT
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="YouTube Video Intelligence API")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_service = RAGService()

class VideoRequest(BaseModel):
    url: str
    language: Optional[str] = "English"
    response_length: Optional[str] = "Medium"

class ChatRequest(BaseModel):
    video_id: str
    question: str
    language: Optional[str] = "English"

@app.get("/health")
async def health_check():
    return {"status": "online", "ai_service": "initialized" if rag_service.llm else "pending"}

@app.post("/analyze")
async def analyze_video(request: VideoRequest):
    print(f"Received analysis request for URL: {request.url} in {request.language}")
    video_id = extract_video_id(request.url)
    transcript = get_transcript(video_id)
    
    if transcript.startswith("Error"):
        raise HTTPException(status_code=400, detail=transcript)
    
    # Generate all analysis tasks first
    try:
        response = rag_service.generate_response(
            prompt_template=SYSTEM_PROMPT,
            transcript=transcript,
            question=ANALYSIS_TASKS_PROMPT,
            language=request.language,
            response_length=request.response_length
        )
        
        # NOW initialize RAG with BOTH transcript and the generated analysis
        rag_service.initialize_vector_store(transcript, video_id, analysis=response)
        
        return {"video_id": video_id, "analysis": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

@app.post("/chat")
async def chat_with_video(request: ChatRequest):
    # Load the existing vector store for the video_id if not already loaded
    if not rag_service.vector_store or rag_service.current_video_id != request.video_id:
        success = rag_service.load_vector_store(request.video_id)
        if not success:
            raise HTTPException(status_code=404, detail="Transcript data not found. Please analyze the video first.")

    try:
        answer = rag_service.chat_with_video(
            video_id=request.video_id,
            question=request.question, 
            language=request.language
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files
app.mount("/photo", StaticFiles(directory="backend/photo"), name="photo")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
