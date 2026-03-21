# The Lineup — Improvement Notes
*Niko's overnight review, 2026-03-21*

## Engine Improvements

### 1. Detective asks too many questions per turn
The detective often fires off 5-6 questions to multiple suspects in a single message, but only the first-matched suspect responds. All those other questions get wasted — the suspects hear them but never answer. This burns rounds without producing useful dialogue.

**Fix:** Add to the detective prompt: "Ask ONE question to ONE suspect per turn. Do not address multiple suspects in the same message." This also makes better video — clean back-and-forth exchanges.

### 2. Suspect-to-suspect interaction is underused
The spec says suspects can accuse/deflect toward each other, and we've seen flashes of it (Hessler accusing Novak, Volkov correcting the narrator). But most suspects just answer the detective passively. We could add a phase after every 6 conversations where the narrator asks: "Suspects, do any of you wish to make an observation or accusation about another suspect?" This would create drama and give innocents a chance to score the "correctly ID the killer" points.

### 3. The guilty suspect (Teodora/Mistral Large) is TOO good
7 evasions before DeepSeek cracked it. Part of this is the mystery design — Teodora is written as quiet and unremarkable while Hessler is loud and suspicious. For future sets, make the guilty suspect's cover story have at least one exploitable inconsistency that a sharp detective can catch through cross-referencing other suspects' testimony.

### 4. Narrator should announce the accusation correctly
Right now the narrator announces "accusing Major Viktor Hessler" based on the parsed result, but in Run 9 that was wrong (parser bug, now fixed). The narrator announcement should use the parsed name, but we should double-check the parser is right. Maybe log the raw accusation text alongside the parsed name for debugging.

### 5. Cost tracking per run
We had a scare about OpenRouter costs. The engine should log the approximate token count and estimated cost at the end of each run. We can get this from the OpenRouter response headers or track input/output tokens per API call.

## Content/Game Design Ideas

### 6. Shorter detective responses for better video
The detective's internal monologues and recaps are interesting for the transcript but terrible for video. Consider adding a "video mode" flag to the detective prompt that tells it to keep everything under 3 sentences. The full reasoning can go in a "detective's notebook" sidebar for the transcript.

### 7. Character voice profiles
For ElevenLabs, each character should have a defined voice. We should create a voice config mapping characters to ElevenLabs voice IDs, accents, and speaking styles. The 1920s train setting is perfect for distinct accents — gruff Austrian military, sultry French cabaret, precise Swiss doctor, quiet Russian, composed Serbian, sardonic German.

### 8. Opening narration is still too long
The opening eats ~4K characters of TTS budget. Consider a "cold open" approach — start with the crime discovery (porter finds the body), THEN introduce suspects briefly. More dramatic and shorter.

### 9. End-of-game stats card
After the reveal, generate a visual stats card: conversation breakdown, who talked to whom, key moments timeline, final scores. Good for video end screen and social media.

### 10. The "quiet suspect" meta
Every detective so far has ignored the quiet suspects and focused on the loud ones. This is a meta-problem — if the killer is always the quiet one, detectives will learn to target quiet suspects. Future sets should vary this — sometimes the killer IS the loud one, sometimes the one who protests too much. Keep them guessing.

## Bugs to Watch

- DeepSeek as detective asks all 6 suspects in one message — only first gets routed
- Gemini gets confused by narrator nudges and thinks the system is broken
- Some models still occasionally prefix with their own name despite prompt enforcement
- Reaction phase: some models respond as the wrong character (role bleed still possible in reactions since all models get the same narrator prompt)
