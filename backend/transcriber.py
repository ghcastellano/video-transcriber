import subprocess
import tempfile
import os
from openai import OpenAI


def extract_audio(video_path: str) -> str:
    """Extract audio from video using ffmpeg."""
    audio_path = tempfile.mktemp(suffix=".mp3")
    subprocess.run(
        [
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "libmp3lame", "-q:a", "4",
            "-y", audio_path,
        ],
        capture_output=True,
        check=True,
    )
    return audio_path


def transcribe_audio(audio_path: str, api_key: str) -> dict:
    """Transcribe audio using OpenAI Whisper API with timestamps."""
    client = OpenAI(api_key=api_key)

    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = []
    for seg in response.segments:
        segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })

    return {
        "language": response.language,
        "full_text": response.text,
        "segments": segments,
    }


def transcribe_video(video_path: str, api_key: str) -> dict:
    """Full pipeline: extract audio then transcribe."""
    audio_path = None
    try:
        audio_path = extract_audio(video_path)
        return transcribe_audio(audio_path, api_key)
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
