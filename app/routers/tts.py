from fastapi import APIRouter, Depends, HTTPException, Response

from app.dependencies import get_current_user
from app.models import User
from app.schemas.tts import TTSRequest
from app.services.tts import MAX_TTS_TEXT_LENGTH, synthesize_speech

router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/")
def text_to_speech(payload: TTSRequest, current_user: User = Depends(get_current_user)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    if len(text) > MAX_TTS_TEXT_LENGTH:
        raise HTTPException(
            status_code=400, detail=f"Text exceeds the maximum length of {MAX_TTS_TEXT_LENGTH} characters."
        )

    try:
        audio_bytes = synthesize_speech(text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to generate speech") from exc

    return Response(content=audio_bytes, media_type="audio/mpeg")
