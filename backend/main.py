import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from frame_analyzer import analyze_video_frames
from transcriber import transcribe_video

load_dotenv()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

executor = ThreadPoolExecutor(max_workers=4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    executor.shutdown(wait=False)


app = FastAPI(title="Video Transcriber + Slide Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY não configurada no .env")

    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="O arquivo deve ser um vídeo")

    # Save uploaded file
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    video_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Arquivo excede o limite de 100MB")

        with open(video_path, "wb") as f:
            f.write(content)

        loop = asyncio.get_event_loop()

        # Run transcription and frame analysis in parallel
        transcription_task = loop.run_in_executor(
            executor, transcribe_video, video_path, api_key
        )
        frames_task = loop.run_in_executor(
            executor, analyze_video_frames, video_path, api_key
        )

        transcription, slide_analysis = await asyncio.gather(
            transcription_task, frames_task
        )

        return JSONResponse(content={
            "success": True,
            "transcription": transcription,
            "slides": slide_analysis,
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar vídeo: {str(e)}")
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


@app.get("/api/health")
async def health():
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    return {"status": "ok", "openai_configured": has_key}
