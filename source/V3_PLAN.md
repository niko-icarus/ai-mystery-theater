# AI Mystery Theater — Engine V3 Plan

## Overview
Complete prompt overhaul + video production pipeline preparation. The engine becomes fully story-agnostic, outputs beat-structured transcripts optimized for AI video generation (~10 sec clips, ~12 min total runtime, ~72 clips per episode).

## Core Philosophy
- Engine is story-agnostic — all character, setting, and detective style driven by story JSON
- No hardcoded references to any specific story (Thornfield, Poirot, etc.)
- Every response is clip-sized (2-3 sentences, ~25 words, ~10 seconds spoken)
- Transcript output is structured as production-ready beats with metadata
- Game flow feels natural, not rigidly forced into set pieces

## Video Production Constraints
- **Target runtime:** ~12 minutes per episode
- **Clip length:** ~10 seconds (AI video generation limit)
- **Total clips:** ~72 per episode
- **Dialogue per clip:** 2-3 sentences (~25 words)
- **Pre-prepared assets:** Character images + setting images loaded into video generator

## Clip Budget by Phase

| Phase | Clips | ~Time |
|---|---|---|
| Cold open / scene setting (narrated) | 4-5 | 45s |
| Detective arrives, surveys scene (narrated) | 3-4 | 35s |
| Character introductions (narrated, 1 per character) | 5-6 | 55s |
| Interrogation Round 1 | 10-12 | 1:50 |
| Evidence Reveal 1 (narrated) | 2-3 | 25s |
| Interrogation Round 2 | 10-12 | 1:50 |
| Evidence Reveal 2 (narrated) | 2-3 | 25s |
| Interrogation Round 3 | 10-12 | 1:50 |
| Evidence Reveal 3 (narrated) | 2-3 | 25s |
| Cross-examination | 8-10 | 1:30 |
| Conclusion / accusation | 4-5 | 45s |
| Reactions + reveal | 5-6 | 55s |
| **Total** | **~68-75** | **~11-12 min** |

## Story JSON Schema (V3)

```json
{
  "title": "Murder at Thornfield Manor",
  "setting": "A grand English country estate, winter 1926...",
  "crime_scene": "Lord Edmund Thornfield found dead in his locked study...",
  "detective_style": "methodical and incisive, with dry wit",
  "locations": {
    "manor_exterior": "Gothic manor in winter fog",
    "study": "Dark wood-paneled study, fireplace, brandy on desk",
    "drawing_room": "Elegant drawing room, candlelight, velvet furniture",
    "garden": "Snow-covered garden path, moonlight"
  },
  "victim": {
    "name": "Lord Edmund Thornfield",
    "description": "Wealthy industrialist, 62..."
  },
  "suspects": [
    {
      "name": "Lady Margaret Thornfield",
      "role": "The wife",
      "location_initial": "drawing_room",
      "public_info": "...",
      "private_info": "...",
      "is_guilty": false,
      "alibi": "...",
      "secrets": ["..."],
      "disguise_identity": null
    }
  ],
  "evidence_reveals": [
    {
      "round": 1,
      "clue": "...",
      "targets": ["Dr. Harold Pembrooke"]
    }
  ],
  "solution": "...",
  "solution_data": {
    "killer": "Dr. Harold Pembrooke",
    "motive": "embezzlement discovery",
    "method": "cyanide in brandy"
  }
}
```

## Beat Transcript Format

Each transcript entry is a production-ready "beat":

```json
{
  "beat_id": 1,
  "phase": "scene_setting",
  "speaker": "narrator",
  "text": "A bitter wind howls across the moors...",
  "location": "manor_exterior",
  "characters_present": [],
  "shot_type": "establishing",
  "mood": "ominous",
  "thinking": null,
  "model": ""
}
```

### Shot Types
- `establishing` — wide shot of location (narration only)
- `dialogue` — character speaking, medium shot
- `reaction` — close-up of character reacting
- `evidence` — close-up of physical evidence
- `group` — multiple characters in frame
- `transition` — brief narrated scene change

## Implementation Phases

### Phase 1 — Generalize Prompts
- Rewrite `build_detective_system_prompt()` — all references pulled from story JSON
- Add `detective_style` field support (story-defined personality)
- Rewrite `build_suspect_system_prompt()` — audit for any hardcoded assumptions
- Remove ALL canned assistant message injections ("Très intéressant", "Noted", "Ah-ha!", etc.)
- Information (evidence, statements) delivered as user messages only — no fake assistant replies

### Phase 2 — Narrated Introductions
- Replace `phase_initial_statements()` with engine-narrated character intros
- No API calls for introductions — engine generates text from story JSON
- Each character gets 1 beat: name, role, relationship to victim, demeanor
- All intros fed into detective context as background briefing

### Phase 3 — Beat-Based Transcript
- Restructure `_log()` to produce beat format with all metadata fields
- Add beat_id counter, location tracking, shot_type assignment
- Shot types assigned automatically: narration → establishing/transition, dialogue → dialogue, evidence → evidence
- Characters_present derived from location tracking
- Export format: JSON array of beats (ready for video pipeline)

### Phase 4 — Clip-Sized Response Enforcement
- All prompts enforce 2-3 sentence responses (~25 words, 40 word guideline)
- Prompt language: "Keep your response to 2-3 sentences of spoken dialogue. This is a single moment — one thought, one reaction, one question. Minimal stage directions."
- Detective accusation: allowed 4-5 beats — instruct model to write in distinct paragraphs, engine splits into separate beats
- Dynamic max_tokens per phase (see Phase 8)

### Phase 5 — Location Tracking + Proximity
- Suspects have `location_initial` field
- Room log maintained per location
- Characters in same location hear each other's exchanges ("You overhear...")
- Characters in other rooms do NOT hear
- Cross-examination and final gathering: all suspects moved to same room
- Selective interjection mechanic: after contradictions, present suspects get chance to react
  - Prompt: "You just heard [X] say [Y]. If you have something relevant to add, speak up briefly. If not, remain silent."
  - Not every exchange — only when significant contradictions surface

### Phase 6 — Natural Flow
- Remove forced "ACT V — PARLOR SCENE" with explicit accusation prompt
- After cross-examination: "You've gathered significant information. Continue questioning or present your conclusions."
- Total turn budget: ~72 beats (matching clip budget)
- If detective hasn't accused by beat ~65: gentle nudge ("Time is pressing...")
- Detective chooses when to accuse within the budget

### Phase 7 — Emotional Escalation + Tailored Reactions
- 3 pressure tiers injected into suspect prompts:
  - **Early** (rounds 1-2): Composed, guarded, sticking to story
  - **Mid** (round 3+, post-evidence): Cracks showing, more defensive, might slip
  - **Late** (cross-exam): Under real pressure, desperate moves
- Subtle framing only — "The tension in the room is rising" not "YOU ARE PANICKING"
- Tailored reaction prompts:
  - Guilty suspect: acknowledges they've been caught (or nearly caught)
  - Innocent suspects with specific knowledge: prompted to reference what they know
  - Others: generic but appropriate reaction

### Phase 8 — Token/Cost Management
- Dynamic max_tokens:
  - Narrated intros: 0 (no API call)
  - Interrogation responses: 256
  - Cross-examination: 384
  - Detective conclusion: 768 (will be split into multiple beats)
  - Suspect reactions: 256
- Dynamic temperature:
  - Interrogation: 0.85
  - Cross-examination: 0.75
  - Detective conclusion: 0.6
  - Reactions: 0.9

## What We're NOT Changing
- Split mode for detective think/act (leave as-is)
- TTS pipeline (separate concern)
- Viewer/gallery (separate concern, will need updates for beat format later)
- Video generation prompts (future work)

## Backward Compatibility
- None needed. Existing stories were test runs.
- All stories will be updated to V3 schema.
