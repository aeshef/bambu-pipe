# voice2bambu

Thin Telegram voice adapter over `bambu-pipe`.

This package intentionally does not contain printer, slicer, or validation logic.
It translates voice/text interaction into `bambu-pipe` jobs and approval actions.

Voice messages are transcribed through an OpenAI-compatible
`/audio/transcriptions` provider configured by:

- `VOICE2BAMBU_TRANSCRIPTION_API_KEY`
- `VOICE2BAMBU_TRANSCRIPTION_BASE_URL`
- `VOICE2BAMBU_TRANSCRIPTION_MODEL`
