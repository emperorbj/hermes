# Hermes API — Text-to-Speech Integration

## `POST /tts/`

Converts text (typically the `answer` from a `POST /query/` response) into spoken audio, so the frontend can offer a "listen to this answer" option.

**Auth**: required — any authenticated role (`admin` or `staff`), same as `/query/`.

**Request:**
```json
{ "text": "The answer text to convert to speech." }
```

**Response `200`**: raw binary audio, `Content-Type: audio/mpeg` — **not JSON**. The body is a playable MP3 file.

**Errors** (these *are* JSON, `{ "detail": "..." }`):
- `400` — text is empty, or exceeds 5000 characters (a cost/abuse guardrail; not something you'd normally hit with a real generated answer, which is capped much shorter).
- `502` — the upstream TTS provider failed to generate audio.

## Consuming it on the frontend

Since a successful response is binary and an error response is JSON, check `res.ok` before deciding how to parse the body:

```typescript
async function playTTS(text: string, token: string) {
  const res = await fetch(`${baseUrl}/tts/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail);
  }

  const audioBlob = await res.blob();                 // raw audio, not JSON
  const audioUrl = URL.createObjectURL(audioBlob);      // browser-local URL pointing at the blob

  const audio = new Audio(audioUrl);
  audio.play();
  audio.onended = () => URL.revokeObjectURL(audioUrl); // release the memory once playback finishes
}
```

- **`res.blob()`**, not `res.json()` — the body is genuine binary audio data.
- **`URL.createObjectURL(...)`** — the only way to give an `<audio>` element / `Audio()` something it can actually play from a `Blob` in memory.
- **`URL.revokeObjectURL(...)`** on completion — that blob URL holds memory until explicitly released or the page fully unloads; good hygiene if a user plays multiple answers in one session.

## Caching — deliberately left to the frontend

There is currently **no server-side caching** for generated audio. This was a deliberate call: TTS audio is large (roughly 2–3 MB for a typical answer-length clip at the bitrate this endpoint uses), and caching it in the same Redis instance already shared by the Celery broker and the embedding cache risked crowding out a 256 MB free-tier storage budget for a comparatively low-value win. If repeated identical requests turn out to be common enough to matter for cost, the plan is to cache in Cloudflare R2 (already in the stack, built for large binary objects) rather than Redis — not built yet, not needed until it's a real observed problem.

In the meantime, use a client-side cache (e.g., React Query) to avoid redundant `/tts/` calls when the *same user* replays or revisits the *same* answer within one session — that's a real, free win regardless of what happens server-side later.
