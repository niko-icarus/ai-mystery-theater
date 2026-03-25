# The Lineup — Production Workflow
## From Story to Published Episode

---

## Season Overview

Each season = **1 story setting** + **8 episodes** + **8 AI models**.

Every model plays every role exactly once across the season (Latin square rotation). This guarantees competitive fairness — no model gets an advantage from character assignment.

### The Rotation

8 models × 8 roles = 8 games. Roles: Detective + 7 suspect characters (one of whom is the killer).

| Game | Detective | Suspect A | Suspect B | Suspect C | Suspect D | Suspect E | Suspect F | Suspect G (Killer) |
|------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-------------------|
| 1 | Model 1 | Model 2 | Model 3 | Model 4 | Model 5 | Model 6 | Model 7 | Model 8 |
| 2 | Model 2 | Model 3 | Model 4 | Model 5 | Model 6 | Model 7 | Model 8 | Model 1 |
| 3 | Model 3 | Model 4 | Model 5 | Model 6 | Model 7 | Model 8 | Model 1 | Model 2 |
| 4 | Model 4 | Model 5 | Model 6 | Model 7 | Model 8 | Model 1 | Model 2 | Model 3 |
| 5 | Model 5 | Model 6 | Model 7 | Model 8 | Model 1 | Model 2 | Model 3 | Model 4 |
| 6 | Model 6 | Model 7 | Model 8 | Model 1 | Model 2 | Model 3 | Model 4 | Model 5 |
| 7 | Model 7 | Model 8 | Model 1 | Model 2 | Model 3 | Model 4 | Model 5 | Model 6 |
| 8 | Model 8 | Model 1 | Model 2 | Model 3 | Model 4 | Model 5 | Model 6 | Model 7 |

Every model plays:
- Detective: 1 time
- Each suspect character: 1 time (including killer)
- Total: 8 games, 8 different roles

### Current Model Roster (Season 1)

| # | Model | Brand | Color | Symbol |
|---|-------|-------|-------|--------|
| 1 | Claude (Sonnet) | Anthropic | Amber #D4A020 | ☀️ |
| 2 | ChatGPT (GPT-4o) | OpenAI | Green #32B850 | ⬡ |
| 3 | Gemini (2.5 Pro) | Google | Blue #4688E8 | ◇ |
| 4 | Mistral (Large) | Mistral AI | Teal #20C4C4 | 🌀 |
| 5 | DeepSeek (V3) | DeepSeek | Red #D04040 | 🔺 |
| 6 | Llama (3.3 70B) | Meta | Purple #8C40C0 | 🦙 |
| 7 | Qwen (2.5 72B) | Alibaba | Gold #D4B830 | ✦ |
| 8 | Grok (3 Beta) | xAI | Silver #A0A0A8 | ✕ |

---

## Phase 1: Pre-Season Setup (Once Per Season)

### 1A. Story & Setting
- Write story config JSON: setting, characters, crime, evidence, truth
- Store at: `seasons/season_XX/set_XX.json`
- Test with 1-2 engine runs to validate story works
- Verify all 7 suspect roles are balanced (no role is impossible to play)

### 1B. Model Rotation Schedule
- Generate the 7-game rotation matrix
- Randomize model order at season start (publish in advance for transparency)
- Store at: `seasons/season_XX/rotation.json`

### 1C. Moodboard Creation
**Brand moodboard (first season only — reuse forever):**
1. Open production planner → Moodboards tab → copy brand prompts
2. Run all 12 brand prompts in Midjourney
3. Curate best ~8 images
4. Create Midjourney moodboard: "The Lineup Brand"
5. Record moodboard code: `[brand_code]`

**Setting moodboard (once per season):**
1. Open production planner → Moodboards tab → copy setting prompts
2. Run all 12 setting prompts in Midjourney (with `--p [brand_code]`)
3. Curate best ~8 images
4. Create Midjourney moodboard for this story
5. Record moodboard code: `[setting_code]`

### 1D. Asset Generation (Midjourney)
**Using both moodboard codes on every prompt.**

1. Open production planner → Assets tab
2. Generate all character portraits: append `--p [brand_code] --p [setting_code]` to each prompt
3. Generate all setting images (exterior, interior, crime scene, corridor, lounge, etc.)
4. Generate victim portrait
5. Generate evidence/prop images
6. Generate model avatars (1:1 format for think sections)

**Output:** All assets saved to `production/season_XX/assets/`

Organize as:
```
assets/
  characters/          # Character portraits (2:3)
  settings/            # Setting shots (16:9)
  props/               # Evidence, weapons, documents (16:9)
  model_avatars/       # AI model avatars (1:1)
  title_cards/         # Auto-generated or custom
```

### 1E. Voice Casting

**Model voices (first season only — permanent forever):**
1. Browse ElevenLabs voice library
2. Choose 8 distinct voices — one per model
3. These are the "AI thinking" voices, heard in [THINK] sections
4. Prioritize variety: different genders, accents, tones
5. Intentional mismatch with characters is part of the entertainment
6. Record voice IDs in: `config/voices.json`

**Character voices (once per season):**
1. 7 suspect characters + 1 detective + 1 narrator = 8 voices
2. Match voice to character personality (gruff military officer, charming singer, etc.)
3. These change each season when the story changes
4. Record voice IDs in: `seasons/season_XX/character_voices.json`

**Voice count per episode:**
- 8 model voices (THINK) — permanent
- 8 character voices (SPEAK: 7 suspects + detective) — per season
- 1 narrator voice — permanent
- **Total: 17 voices**

---

## Phase 2: Per Episode Production (7 Times Per Season)

### 2A. Run the Engine
1. Load story config + model assignments from rotation schedule
2. Run: `python engine_v2.py seasons/season_XX/set_XX.json`
3. Engine outputs: transcript JSON to `transcripts/`
4. Review transcript for quality (think/speak parsing, all models participated)
5. Re-run if needed (model had API error, format broke, etc.)

**Runtime:** ~3-5 minutes
**Cost:** ~$0.50-1.00 in API calls (OpenRouter)

### 2B. Production Planning
1. Run: `python production-planner/build_static_v2.py transcripts/[file].json planner.html`
2. Review shot list — verify pacing, prompt quality
3. Identify which setting video clips can be **reused** from previous episodes
4. Mark reusable shots to skip regeneration

### 2C. TTS Generation (ElevenLabs)
1. Extract all dialogue from transcript
2. Route each clip to the correct voice:
   - [THINK] → model's permanent voice
   - [SPEAK] → character's season voice
   - [NARRATE] → narrator voice
3. Generate via ElevenLabs API
4. Verify audio quality, re-generate any issues

**Characters per episode:** ~12,000-16,000
**Cost:** ~$3-5 at ElevenLabs Creator rates

### 2D. Video Clip Generation
1. Open production planner → Video Prompts tab
2. Run prompts in video generation tool (Runway / Kling / etc.)
3. Append moodboard codes to maintain visual consistency
4. **Skip setting shots already generated** in previous episodes — reuse from asset library
5. Generate character-specific shots unique to this episode's dialogue

**New clips per episode:** ~15-25 (setting shots reused, character close-ups new)
**Cost:** Varies by tool — estimate $5-15 per episode

### 2E. Assembly (DaVinci Resolve)

**Import:**
- All TTS audio clips
- All video clips (new + reused)
- Character portraits, model avatars (static images)
- Title cards (auto-generated or custom)
- Intro video (pre-built, same for all episodes except roster section)

**Timeline structure:**
```
[Intro]
  - Parts 1-4 (reuse)
  - Part 5: Roster (regenerate per episode — different model assignments)
  - Part 6: Specs card (regenerate per episode)
[Round 1: The Scene]
  - Narrator audio over setting video clips
[Round 2: Opening Statements]
  - Per suspect: Think (model avatar + model voice) → Speak (character video + character voice)
  - Add colored captions: "Character (Model): text..."
[Round 3: Suspicion Round]
  - Per confrontation: Narrator prompt → Target think/speak → Challenger think/speak
  - Captions in model colors
[Detective Processing]
  - Think-only beat over transition visual
[Round 4: Investigation]
  - Evidence reveal
  - Per question: Detective think/speak → Suspect think/speak
[Round 5: Final Statements + Accusation]
  - All final statements
  - Title card: THE ACCUSATION
  - Detective accusation
  - Accused response
  - All reactions
[Reveal + Scoring]
  - Title card: THE TRUTH
  - Narrator reveals truth
  - Scoring card
  - Season standings
[Outro]
  - Standings graphic
  - Next episode tease
  - End card
```

**Caption format:**
- THINK sections: model's brand color, italic, with model name
  - e.g., *Claude: "The suspects are coordinating too perfectly..."*
- SPEAK sections: white or character-specific color, with character name + model
  - e.g., **Teodora (Mistral):** "I retired to my cabin immediately after dinner..."

**Post-production:**
- Background music (low, atmospheric, building tension per round)
- Sound design (subtle — transitions, evidence reveals)
- Color grading (consistent with moodboard aesthetic)
- Final export: 3840×2160, H.264/H.265, high bitrate

**Export settings:**
- Resolution: 3840×2160 (4K)
- Frame rate: 24fps (cinematic) or 30fps
- Codec: H.265 for YouTube upload
- Audio: AAC 320kbps stereo

---

## Phase 3: Post-Season

### 3A. Final Episode Extras
- Season championship announcement
- Model performance breakdown (best detective, best killer, best innocent, MVP)
- Highlight reel / best moments compilation

### 3B. Archive
- All transcripts, assets, audio, video clips archived
- Setting assets available for potential crossover or flashback content
- Season statistics saved for future reference and cross-season comparison

### 3C. Next Season Prep
- Choose new story/setting
- Update model roster if needed (swap in Grok, update model versions)
- Generate new setting moodboard
- Cast new character voices
- Generate new assets

---

## Cost Summary Per Season

| Item | Per Episode | Per Season (×8) |
|------|------------|-----------------|
| Engine API calls | ~$1 | ~$8 |
| TTS (ElevenLabs) | ~$5 | ~$40 |
| Video generation | ~$10 | ~$80 |
| Midjourney assets | — | ~$12 (one-time) |
| **Total** | **~$16** | **~$140** |

Costs are estimates and will vary based on tool choices and episode length.

---

## Reusable Assets Per Season

These are generated once and reused across all 8 episodes:

| Asset Type | Count | Reuse |
|------------|-------|-------|
| Brand moodboard | 1 | Forever |
| Setting moodboard | 1 | All season |
| Character portraits | 7 | All season |
| Victim portrait | 1 | All season |
| Setting video clips (exterior, dining, corridor, lounge, crime scene) | ~8-12 | All season |
| Evidence/prop images | 3-5 | All season |
| Model avatars | 8 | Forever |
| Title card templates | 5-6 | All season |
| Narrator voice | 1 | Forever |
| Model voices | 8 | Forever |
| Character voices | 7-8 | All season |
| Intro Parts 1-4 | 1 | All season |

**Per-episode unique generation:**
- Intro Part 5-6 (roster + specs — regenerate for each model assignment)
- TTS audio (unique dialogue every game)
- ~15-25 new video clips (character close-ups specific to that episode's dialogue)
- Scoring/standings graphics

---

## File Structure

```
the-lineup/
  ENGINE_SPEC_V2.md          # Game engine specification
  WORKFLOW.md                 # This file
  engine_v2.py                # Game engine
  
  seasons/
    season_01/
      set_01.json             # Story config
      rotation.json           # Model rotation schedule
      character_voices.json   # Voice assignments
      leaderboard.json        # Running standings
  
  transcripts/                # Engine output (one per game)
    s01e01_v2_*.json
    s01e02_v2_*.json
    ...
  
  production-planner/
    shots.py                  # Shot builder + moodboard generators
    build_static_v2.py        # Static HTML planner builder
    app.py                    # Streamlit planner (optional)
  
  production/
    season_01/
      assets/
        characters/           # Midjourney character portraits
        settings/             # Midjourney setting images
        props/                # Evidence, weapons
        model_avatars/        # AI model avatars
        title_cards/          # Auto-generated cards
      audio/
        episode_01/           # TTS clips per episode
        episode_02/
        ...
      video/
        shared/               # Reusable setting clips
        episode_01/           # Per-episode unique clips
        episode_02/
        ...
      exports/
        s01e01_final.mp4      # Finished episodes
        s01e02_final.mp4
        ...
  
  config/
    voices.json               # Permanent model voice assignments
```

---

## Tool Stack

| Function | Tool | Notes |
|----------|------|-------|
| Game engine | Python + OpenRouter | Custom engine_v2.py |
| Production planning | Custom shot builder + HTML planner | Runs on any device |
| Image generation | Midjourney | Moodboards for consistency |
| Video generation | TBD (Runway / Kling / etc.) | Testing needed |
| TTS | ElevenLabs | Creator plan, 110K chars/month |
| Video editing | DaVinci Resolve | Free version, 4K capable |
| Hosting/sharing | YouTube | 4K upload |
| Code/assets | GitHub | niko-icarus org |

---

## Version History

- **v1** — Ken Burns on stills, single voice, free-form engine (Mar 15-22, 2026)
- **v2** — This workflow. Fixed engine, think/speak, shot-level planning, Midjourney + video gen + DaVinci (Mar 22, 2026)
