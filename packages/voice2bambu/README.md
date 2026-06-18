# voice2bambu

Thin Telegram voice adapter over `bambu-pipe`.

This package intentionally does not contain printer, slicer, or validation logic.
It translates voice/text interaction into `bambu-pipe` jobs and approval actions.

Voice messages are transcribed through an OpenAI-compatible
`/audio/transcriptions` provider configured by:

- `VOICE2BAMBU_TRANSCRIPTION_API_KEY`
- `VOICE2BAMBU_TRANSCRIPTION_BASE_URL`
- `VOICE2BAMBU_TRANSCRIPTION_MODEL`
- `VOICE2BAMBU_TRANSCRIPTION_LANGUAGE`

For local compatibility, the adapter also accepts `OPENROUTER_API_KEY`,
`ASR_MODEL`, `ASR_LANGUAGE`, and `ASR_BASE_URL`. Prefer the `VOICE2BAMBU_*`
names in committed examples and deployment docs.
