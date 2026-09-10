import base64
import cv2
import numpy as np
import os
import tempfile
from openai import OpenAI


def extract_key_frames(video_path: str, threshold: float = 30.0, max_frames: int = 20) -> list[dict]:
    """
    Extract key frames from video using scene change detection.
    Returns list of dicts with frame image path and timestamp.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    frames = []
    prev_gray = None
    frame_idx = 0
    # Sample every 0.5 seconds to speed up processing
    sample_interval = max(1, int(fps * 0.5))

    tmp_dir = tempfile.mkdtemp(prefix="frames_")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if prev_gray is None:
                # Always capture the first frame
                is_key = True
            else:
                diff = cv2.absdiff(gray, prev_gray)
                mean_diff = np.mean(diff)
                is_key = mean_diff > threshold

            if is_key and len(frames) < max_frames:
                timestamp = frame_idx / fps
                frame_path = os.path.join(tmp_dir, f"frame_{len(frames):03d}.jpg")
                cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frames.append({
                    "path": frame_path,
                    "timestamp": round(timestamp, 2),
                    "frame_index": frame_idx,
                })

            prev_gray = gray

        frame_idx += 1

    cap.release()

    # If we got too few frames (e.g. static presentation), sample uniformly
    if len(frames) < 3 and total_frames > 0:
        cap = cv2.VideoCapture(video_path)
        interval = max(1, total_frames // min(10, max_frames))
        frames = []
        for i in range(0, total_frames, interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret and len(frames) < max_frames:
                timestamp = i / fps
                frame_path = os.path.join(tmp_dir, f"frame_{len(frames):03d}.jpg")
                cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frames.append({
                    "path": frame_path,
                    "timestamp": round(timestamp, 2),
                    "frame_index": i,
                })
        cap.release()

    return frames


def encode_image_base64(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_frame(image_path: str, timestamp: float, api_key: str) -> dict:
    """Analyze a single frame/slide using GPT-4o Vision."""
    client = OpenAI(api_key=api_key)
    b64 = encode_image_base64(image_path)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um especialista em análise de apresentações e slides. "
                    "Analise a imagem do slide e forneça:\n"
                    "1. **Conteúdo**: Todo o texto visível no slide\n"
                    "2. **Descrição**: O que o slide mostra (gráficos, imagens, layout)\n"
                    "3. **Sugestões de melhoria**: O que poderia ser melhorado no slide "
                    "(design, clareza, conteúdo, erros ortográficos, etc.)\n"
                    "Responda no mesmo idioma do conteúdo do slide."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analise este slide capturado no timestamp {timestamp}s do vídeo.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=1000,
    )

    return {
        "timestamp": timestamp,
        "analysis": response.choices[0].message.content,
    }


def analyze_video_frames(video_path: str, api_key: str) -> list[dict]:
    """Full pipeline: extract key frames and analyze each one."""
    frames = extract_key_frames(video_path)
    results = []

    for frame in frames:
        try:
            analysis = analyze_frame(frame["path"], frame["timestamp"], api_key)
            results.append(analysis)
        except Exception as e:
            results.append({
                "timestamp": frame["timestamp"],
                "analysis": f"Erro ao analisar frame: {str(e)}",
            })

    # Cleanup temp frame files
    for frame in frames:
        if os.path.exists(frame["path"]):
            os.remove(frame["path"])
        dir_path = os.path.dirname(frame["path"])
        if os.path.exists(dir_path) and not os.listdir(dir_path):
            os.rmdir(dir_path)

    return results
