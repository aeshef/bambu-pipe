"""Telegram bot assembly.

The adapter is intentionally thin: it should call bambu-pipe's REST API instead
of importing slicer or printer internals.
"""

from __future__ import annotations

import httpx

from voice2bambu.config import VoiceSettings


def require_configured(settings: VoiceSettings) -> None:
    if settings.configured:
        return
    raise RuntimeError(
        "voice2bambu is not configured. Set VOICE2BAMBU_TELEGRAM_TOKEN, "
        "VOICE2BAMBU_ALLOWED_USER_IDS, VOICE2BAMBU_BAMBU_PIPE_API_BASE_URL, "
        "and VOICE2BAMBU_TRANSCRIPTION_API_KEY."
    )


def build_bot(settings: VoiceSettings):  # noqa: ANN201
    """Build a Telegram application.

    The adapter stays thin: Telegram handles chat I/O, the transcription provider
    turns voice into text, and bambu-pipe owns generation/slicing/printing.
    """
    require_configured(settings)
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    except ImportError as exc:  # pragma: no cover - optional adapter dependency
        raise RuntimeError("Install voice2bambu with Telegram dependencies") from exc

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG001
        if not _is_allowed(update, settings):
            return
        await update.effective_chat.send_message(
            "Send a short text prompt. I will create a bambu-pipe text_full job "
            "and return the preview/approval link."
        )

    async def text_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG001
        if not _is_allowed(update, settings):
            return
        prompt = update.effective_message.text.strip()
        await _create_text_full_job(prompt, update, settings)

    async def voice_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG001
        if not _is_allowed(update, settings):
            return
        prompt = await _transcribe_voice(update, settings)
        await _create_text_full_job(prompt, update, settings)

    application = Application.builder().token(settings.telegram_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_prompt))
    application.add_handler(MessageHandler(filters.VOICE, voice_prompt))
    return application


def _is_allowed(update, settings: VoiceSettings) -> bool:  # noqa: ANN001
    user = update.effective_user
    return bool(user and user.id in settings.allowed_user_ids)


def _api_base_url(settings: VoiceSettings) -> str:
    if not settings.bambu_pipe_api_base_url:
        raise RuntimeError("VOICE2BAMBU_BAMBU_PIPE_API_BASE_URL is required")
    return settings.bambu_pipe_api_base_url.rstrip("/")


async def _create_text_full_job(prompt: str, update, settings: VoiceSettings) -> None:  # noqa: ANN001
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{_api_base_url(settings)}/jobs",
            json={"mode": "text_full", "prompt": prompt, "auto_approve": False},
        )
        response.raise_for_status()
        job = response.json()
    await update.effective_chat.send_message(
        f"Created job {job['id']} for preview. Run approval in bambu-pipe API/UI."
    )


async def _transcribe_voice(update, settings: VoiceSettings) -> str:  # noqa: ANN001
    voice = update.effective_message.voice
    telegram_file = await voice.get_file()
    audio = await telegram_file.download_as_bytearray()
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{settings.transcription_base_url.rstrip('/')}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.transcription_token}"},
            data={"model": settings.transcription_model},
            files={"file": ("voice.ogg", bytes(audio), "audio/ogg")},
        )
        response.raise_for_status()
    transcript = response.json().get("text")
    if not isinstance(transcript, str) or not transcript.strip():
        raise RuntimeError("Transcription provider returned an empty transcript")
    return transcript.strip()
