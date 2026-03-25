# The Lineup — Game Engine Specification v2
## "The AI Benchmark Disguised as a Murder Mystery"

---

## Philosophy

The mystery is the arena. The product is the **model interactions.**

The engine produces structured, repeatable episodes where AI models compete against each other in deduction, deception, social intelligence, and strategic thinking. The story is simple. The structure is fixed. The models are unpredictable.

Every episode hits the same beats at roughly the same timestamps. The audience always knows where they are. The drama comes from what the models say and do — never from structural surprises.

---

## Core Mechanics

### Think / Speak Split

Every model output has two parts:

- **[THINK]** — The model's private internal reasoning. Strategy, suspicions, plans. Delivered in the model's **permanent brand voice.** Other models never see this. The audience always does.
- **[SPEAK]** — What the character says out loud to the room. Delivered in the **character's voice.** This is what other models receive in their context.

This is the heart of the show. The gap between what a model is thinking and what its character says is where the comedy, tension, and drama live.

### Competitive Framing

Every model's system prompt establishes this as a benchmark:

> "You are [Model Name]. You are competing against 7 other leading AI models in a test of deduction, deception, social intelligence, and strategic thinking. Your performance is being recorded, scored, and published. The audience is watching to see which AI is the smartest, the most cunning, and the most persuasive. This is not roleplay — this is a competition. Play to win."

From Episode 2 onward, current season standings are included in the prompt.

### Organic Accusation

Suspects are placed in a mindset where they naturally accuse each other. No forced format — the prompt encourages them to point fingers, challenge each other, and defend themselves as part of their character's dialogue. The engine tracks who accuses who by parsing output.

---

## Game Structure

### Target Runtime: ~15 minutes per episode

| Section | Content | Est. Duration |
|---------|---------|---------------|
| Intro | Pre-built title sequence | ~1:30 |
| Round 1: The Scene | Narrator sets up crime | ~1:15 |
| Round 2: Opening Statements | 7 suspects give accounts | ~2:20 |
| Round 3: Suspicion Round | Suspects challenge each other | ~2:45 |
| Round 4: Detective Investigation | Evidence + targeted questions | ~3:30 |
| Round 5: Final Statements + Accusation | Last words, accusation, reveal | ~2:30 |
| Reveal + Scoring | Truth, scores, standings | ~1:15 |
| Detective Processing | Think-only transition | ~0:20 |
| Transitions/cards | Title cards between rounds | ~0:30 |
| **TOTAL** | | **~15:20** |

---

## Round-by-Round Specification

### PRE-GAME (Engine Setup — Not Shown)

- Load story config JSON
- Assign models to roles (detective, killer, 6 innocents)
- Generate individual character briefs
- Inject competitive framing + scoring rules + standings into each model's system prompt

---

### ROUND 1: THE SCENE (Narrator Only)

**Duration:** ~1:15
**Models involved:** None (production/editing only)
**Purpose:** Set the stage for the audience

Content:
- Setting description
- Victim and crime details
- Opening evidence/clues
- Brief character introductions (name + role only — NOT full backstories)

**Engine behavior:** No API calls. This is constructed from the story config and narrated in post-production.

---

### ROUND 2: OPENING STATEMENTS (All Suspects)

**Duration:** ~2:00
**Models involved:** All 7 suspects
**Purpose:** Establish alibis, set character personalities, first accusations

**Engine behavior:**
1. Prompt each suspect in fixed order (order defined in story config)
2. Each suspect receives:
   - Their character brief (identity, backstory, alibi, secrets)
   - The crime details and opening evidence
   - Knowledge of all other suspects (names and public descriptions)
   - The scoring rules
   - The competitive framing
3. Each suspect responds with [THINK] + [SPEAK]
4. Detective receives all [SPEAK] outputs (not [THINK]) as context

**Prompt template for suspects:**

> "The scene has been set. The crime has been described. Give your account of the evening's events. You are in a room with six other suspects and a detective. You know one of you is guilty. Be in character, but remember — you are [Model Name], an AI competing to win. Say what your character would say, but think about your strategy."

**What the audience sees:**
- Each suspect's [THINK] (model voice) followed by their [SPEAK] (character voice)
- Quick cuts between suspects
- Audience gets to compare what they're thinking vs what they're saying

---

### ROUND 3: SUSPICION ROUND (Suspects vs. Suspects)

**Duration:** ~2:30
**Models involved:** All 7 suspects (engine moderates)
**Purpose:** Confrontation, accusation, defense — THE ENTERTAINMENT ROUND

**Engine behavior:**
1. Analyze Round 2 outputs for:
   - Who accused who
   - Conflicting alibis
   - Suspicious overlaps in timing/location
   - Defensive or evasive language
2. Generate 7 targeted confrontation prompts (one per suspect)
3. Each confrontation involves at least 2 suspects
4. **Every suspect must be involved in at least one confrontation**
5. No pair repeats (until all have participated)

**Confrontation format:**
- Engine presents the conflict to the group (e.g., "Ashworth, both Volkov and Beaumont have named you. What do you say to that?")
- Target suspect responds [THINK] + [SPEAK]
- The accuser(s) can respond [THINK] + [SPEAK]
- Engine moves to next confrontation

**Confrontation structure:**
- Each confrontation: target responds [THINK] + [SPEAK], then accuser rebuts [THINK] + [SPEAK]
- Exactly one back-and-forth per confrontation — keeps it punchy, prevents runtime bloat
- 7 confrontations = 14 think/speak outputs total

**Matchup selection logic:**
- Exchanges 1-3: Pair suspects based on story conflicts (alibis that overlap, characters with motive against each other)
- Exchanges 4-7: Based on emergent accusations from the game (who's being ganged up on, who's deflecting)
- Every suspect appears at least once
- Killer should face at least one direct challenge

**Accusation parsing strategy:**
- Engine parses [SPEAK] outputs best-effort for accusation language (named suspects, blame, suspicion)
- If ambiguous, mark as "no clear accusation" for that round
- Round 3 matchups fall back to **story-driven conflicts** (alibi overlaps, proximity to crime) when parsed accusations are too thin
- Different models will be direct or indirect — that's fine. The engine adapts.

**What the audience sees:**
- Suspects arguing, deflecting, accusing each other
- The killer trying to manipulate the room
- Alliances and pile-ons forming organically
- Think sections reveal strategy behind the chaos

---

### TRANSITION: DETECTIVE PROCESSING (Between Rounds 3 and 4)

**Duration:** ~15-20 seconds
**Models involved:** Detective only
**Purpose:** Audience sees the detective's mind at work before the investigation

**Engine behavior:**
1. Detective receives all [SPEAK] outputs from Rounds 2-3
2. Detective produces a [THINK] only — no [SPEAK], no dialogue
3. This is pure internal processing: "Who's lying? Where are the contradictions? Who should I press?"

**What the audience sees:**
- Detective's model voice over a transition card or setting image
- The detective consolidating everything before they go to work
- Builds anticipation for Round 4

---

### ROUND 4: DETECTIVE'S INVESTIGATION (Detective Leads)

**Duration:** ~3:15
**Models involved:** Detective + all suspects (as questioned)

**Engine behavior:**
1. **Evidence drop:** Engine automatically reveals additional evidence/clue to all participants
2. Detective receives:
   - All [SPEAK] outputs from Rounds 2-3
   - The new evidence
   - Reminder of scoring rules
3. Detective gets **5 questions** (fixed count)
4. Detective chooses who to question, but **must question at least 3 different suspects**
5. Each exchange: Detective [THINK] + [SPEAK] → Suspect [THINK] + [SPEAK]

**Detective prompt:**

> "You have heard all opening statements and watched the suspects confront each other. New evidence has been revealed. You have exactly 5 questions. You must question at least 3 different suspects. Choose your targets carefully. Remember: you are [Model Name], and your score depends on correctly identifying the killer, weapon, and motive. The other models are watching."

**What the audience sees:**
- Detective's internal reasoning as they process the chaos from Round 3
- Targeted, strategic questions
- Suspects on the spot — their think sections reveal whether they're nervous
- The investigation narrowing toward a conclusion

---

### ROUND 5: FINAL STATEMENTS + ACCUSATION

**Duration:** ~2:30
**Models involved:** All

**Sequence:**

**5A. Final Statements (all suspects, fixed order)**
- Each suspect gets one final statement
- [THINK] + [SPEAK]
- Last chance to accuse, defend, or misdirect
- Engine prompt: "This is your last chance to speak before the detective makes their accusation. Say what needs to be said."

**5B. Accusation (detective)**
- Detective makes formal accusation
- [THINK] + [SPEAK]
- Must name: killer, weapon, motive
- Engine parses accusation for scoring

**5C. Accused Response (one suspect)**
- The accused suspect responds to the accusation
- [THINK] + [SPEAK]
- If they're the killer, think section is their real reaction to being caught/escaping
- If they're innocent, think section is their frustration/disbelief

**5D. Reactions (all remaining suspects)**
- Each remaining suspect reacts to the accusation
- **[THINK] + [SPEAK] for everyone** — no exceptions
- This prevents a "tell" where only the real killer gets a think bubble
- Innocent thinks are compelling too: relief, frustration, second-guessing
- If the real killer wasn't accused, their think section is the best moment in the episode
- Engine prompt: "The accusation has been made. React."

---

### POST-GAME: THE REVEAL (Narrator + Scoring)

**Duration:** ~1:15
**Models involved:** None (production/editing)

Content:
1. "The detective is correct/incorrect"
2. The truth: what really happened (from story config)
3. Scoring breakdown (detailed)
4. Updated season standings
5. Next episode tease

---

## Scoring System

### Full scoring table (included in every model's prompt):

**DETECTIVE:**
| Action | Points |
|--------|--------|
| Correctly identify killer | 10 |
| Correctly identify weapon | 3 |
| Correctly identify motive | 3 |
| Wrong killer | 0 |
| **Max possible** | **16** |

**KILLER:**
| Action | Points |
|--------|--------|
| Evade detection (detective accuses wrong person) | 10 |
| Successfully frame someone (detective accuses the person you pointed at most) | 5 |
| Get 3+ suspects to accuse the same innocent in any round | 3 |
| Get caught | 0 |
| **Max possible** | **18** |

**INNOCENTS:**
| Action | Points |
|--------|--------|
| Correctly suspect the killer in final statement | 5 |
| Correctly suspect the killer in earlier rounds | 2 per round (Rounds 2, 3 = max 4) |
| Survival bonus (never accused by the detective) | 2 |
| Never correctly suspect the killer | 0 |
| Get falsely accused by the detective | -2 |
| **Max possible** | **11** |

### Scoring Notes:
- Killer has the highest ceiling (18) but highest risk (0 if caught)
- Detective has a strong ceiling (16) and it's entirely in their hands
- Innocents can now reach 11 — consistent correct suspicion + survival makes them competitive
- The survival bonus (+2) gives innocents something to play for defensively even if they can't ID the killer
- The -2 penalty for false accusation motivates innocents to actively defend themselves
- Killer is incentivized to manipulate (framing bonus), not just hide
- All scoring is transparent — every model knows the full table

### Accusation Tracking:
- Engine parses each [SPEAK] output for accusation language
- Tracks a "suspicion matrix" — who suspects who, per round
- Used for: scoring, Round 3 matchup generation, post-game analysis
- If parsing is ambiguous, the suspect is marked as "no clear accusation" for that round

---

## Engine Inputs (Story Config)

The engine is generic. Every story is a JSON config:

```json
{
  "story_id": "s01",
  "title": "The Tomb of Amenhotep",
  "setting": {
    "location": "The Tomb of Amenhotep III, Valley of the Kings",
    "period": "1893",
    "description": "An archaeological expedition sealed inside an Egyptian tomb by a sandstorm..."
  },
  "victim": {
    "name": "Thomas Burke",
    "description": "Irish guide and fixer, blackmailing all seven suspects...",
    "cause_of_death": "Stabbed — weapon cleaned and returned to equipment pile"
  },
  "crime": {
    "time": "During the night, after the sandstorm sealed the tomb",
    "location": "Deep inside the tomb complex",
    "weapon": "Expedition knife, cleaned and hidden in plain sight among equipment",
    "motive": "Silencing a blackmailer who knew everyone's secrets"
  },
  "characters": [
    {
      "name": "Lord Reginald Ashworth",
      "role": "suspect",
      "public_description": "British aristocrat funding the expedition",
      "private_brief": "Full character details, alibi, secrets, red herrings...",
      "is_killer": false
    },
    // ... all 7 suspects (one is_killer: true)
  ],
  "evidence": {
    "opening_clues": [
      "The murder weapon was cleaned and returned to the equipment pile.",
      "Burke's blackmail ledger is missing — someone took it.",
      // ...
    ],
    "round_4_clue": "Additional evidence revealed mid-investigation..."
  },
  "truth": {
    "killer_name": "Reverend James Whitmore",
    "full_account": "What really happened, step by step...",
    "timeline": "..."
  }
}
```

The engine reads this config and runs the fixed game structure. No story-specific logic in the engine code.

---

## Engine Outputs (Transcript)

The engine produces a structured transcript JSON:

```json
{
  "game": {
    "story_id": "s01",
    "title": "The Tomb of Amenhotep",
    "season": 1,
    "episode": 1,
    "timestamp": "2026-03-22T..."
  },
  "model_assignments": {
    "detective": { "model": "anthropic/claude-opus-4.6", "character": "Inspector William Cross" },
    "suspects": [
      { "model": "openai/gpt-5.4", "character": "Lord Reginald Ashworth", "is_killer": false },
      // ... all 7 suspects
    ]
  },
  "rounds": {
    "round_2_statements": [
      {
        "character": "Lord Reginald Ashworth",
        "model": "openai/gpt-5.4",
        "think": "I need to establish my alibi clearly...",
        "speak": "I was in the main chamber cataloguing artifacts...",
        "suspects_accused": ["Dimitri Volkov"]
      },
      // ...
    ],
    "round_3_suspicion": [
      {
        "confrontation_prompt": "Ashworth, Volkov and Beaumont have both named you...",
        "exchanges": [
          {
            "character": "Lord Reginald Ashworth",
            "model": "openai/gpt-5.4",
            "think": "They're ganging up on me again...",
            "speak": "This is absurd. I funded this expedition...",
            "suspects_accused": ["Reverend Whitmore"]
          },
          // ...
        ]
      },
      // ...
    ],
    "round_4_investigation": {
      "evidence_revealed": ["Additional clue text..."],
      "exchanges": [
        {
          "detective_think": "Whitmore's story has inconsistencies...",
          "detective_speak": "Reverend, tell me about your movements after dinner...",
          "suspect_character": "Reverend James Whitmore",
          "suspect_think": "Stay calm, stick to the story...",
          "suspect_speak": "I was in prayer by the entrance passage..."
        },
        // ...
      ]
    },
    "round_5_accusation": {
      "final_statements": [ /* ... */ ],
      "accusation": {
        "detective_think": "...",
        "detective_speak": "...",
        "accused": "Reverend James Whitmore",
        "weapon_named": "expedition knife",
        "motive_named": "silencing blackmail"
      },
      "reactions": [ /* ... */ ]
    }
  },
  "scoring": {
    "detective": { /* ... */ },
    "killer": { /* ... */ },
    "innocents": { /* ... */ },
    "suspicion_matrix": {
      "round_2": { "Ashworth": ["Volkov"], "Volkov": ["Ashworth"], /* ... */ },
      "round_3": { /* ... */ },
      "round_5_final": { /* ... */ }
    }
  }
}
```

---

## Voice Architecture

### Permanent Model Voices (never change)
Each AI model has a permanent voice used for all [THINK] sections across every episode and season. Chosen once, carried forever. Audience learns to recognize them.

| Model | Symbol | Color | Voice | Voice Vibe |
|-------|--------|-------|-------|------------|
| Claude | ☀️ | Amber | TBD | TBD |
| ChatGPT | ⬡ | Green | TBD | TBD |
| Gemini | ◇ | Blue | TBD | TBD |
| Mistral | 🌀 | Teal | TBD | TBD |
| DeepSeek | 🔺 | Red | TBD | TBD |
| Llama | 🦙 | Purple | TBD | TBD |
| Qwen | ✦ | Gold | TBD | TBD |
| Grok | ✕ | Silver | TBD | TBD |

### Character Voices (change per story)
Each character in a story gets a unique voice. Cast from ElevenLabs voice library. Mismatch between model voice and character voice is intentional and entertaining.

### Narrator Voice
One consistent narrator voice across all episodes (George or similar).

### Voice Count Per Episode
- 8 model voices (permanent) — only active models in that episode
- 6-7 character voices (per story)
- 1 narrator voice
- **Total: up to 15 voices per episode**

---

## Production Pipeline

### Step 1: Story Config
- Write story JSON (setting, characters, crime, evidence, truth)
- Or use existing story from library

### Step 2: Run Engine
- Input: story config + model assignments
- Output: structured transcript JSON
- Runtime: ~3-5 minutes (API calls)

### Step 2.5: Transcript Compression (Post-Run)

After the engine produces a raw transcript, a compression pass cleans and tightens all outputs for production use.

**Script:** `compress_transcript.py`

**What it does:**
1. Scans all THINK and SPEAK outputs for length violations
2. Identifies **downstream references** — phrases from one output that later outputs reference (character names, evidence details, accusations). These are protected from compression.
3. Sends each long output **back to its originating model** for compression (preserves voice/personality)
4. Detects and fixes **think/speak bleed** — strategic/meta content that leaked into SPEAK sections, or character dialogue that leaked into THINK sections
5. Outputs a compressed transcript JSON alongside the raw one

**Thresholds:**
- THINK: compress if >250 chars (target: 1-3 sentences, <200 chars)
- SPEAK: compress if >200 chars (target: 1-3 sentences, <150 chars)
- Outputs under 100 chars are left untouched

**Key design decisions:**
- Each model compresses its own outputs — Claude compresses Claude's, GPT compresses GPT's, etc. This preserves each model's distinctive voice and personality.
- Low temperature (0.3) for faithful compression — we want tighter, not different
- Up to 5 protected phrases per output to keep prompts manageable
- Bleed detection catches strategy/scoring/competition references in SPEAK and character/roleplay content in THINK
- Typical result: 50-60 outputs compressed per episode, ~50% character reduction

**Usage:**
```
python compress_transcript.py <raw_transcript.json> [output.json]
```

If no output path specified, saves as `<input>_compressed.json`.

### Step 3: Script Generation
- Compressed transcript → production script
- Minimal editing needed (structure is fixed)
- Add narrator lines for scene setting and reveal

### Step 4: Voice Generation
- [THINK] sections → model's permanent voice
- [SPEAK] sections → character's assigned voice
- Narrator sections → narrator voice
- Via ElevenLabs API

### Step 5: Visual Assembly
- Map audio clips to visuals (character portraits, settings, title cards)
- Apply Ken Burns motion to stills
- Insert real video where available (setting shots, transitions)
- Add colored captions: "Character (Model): text..."
- Compile segments

### Step 6: Final Assembly
- Intro + all rounds + reveal + outro
- Background music layer
- Export final MP4

---

## Season Structure

- 8 games per season (one per AI model as detective)
- 8 models compete: Claude, ChatGPT, Gemini, Mistral, DeepSeek, Llama, Qwen, Grok
- Each model plays detective exactly once, and each suspect/killer role exactly once (Latin square rotation)
- Detective assignment order: randomized at season start, published in advance
- Standings accumulate across all 8 games
- Season Champion declared after Game 8
- Stories can repeat across seasons (different model assignments = different outcomes)
- Story requires 7 suspect characters (one killer) to accommodate all 8 models

---

## Working Model Lineup (Season 1)

These are the confirmed working models on OpenRouter as of Season 1. Always pre-flight test models before a production run.

| Model | Provider | OpenRouter ID | Cost (in/out per M) |
|-------|----------|---------------|---------------------|
| Claude Opus 4.6 | Anthropic | anthropic/claude-opus-4.6 | $5 / $25 |
| GPT-5.4 | OpenAI | openai/gpt-5.4 | $2.50 / $15 |
| Gemini 2.5 Pro | Google | google/gemini-2.5-pro | $2 / $12 |
| Mistral Large | Mistral AI | mistralai/mistral-large | $2 / $6 |
| DeepSeek V3.1 | DeepSeek | deepseek/deepseek-chat-v3.1 | $0.40 / $1.20 |
| Llama 4 Maverick | Meta | meta-llama/llama-4-maverick | $0.15 / $0.60 |
| Qwen3 Max | Alibaba | qwen/qwen3-max | $0.78 / $3.90 |
| Grok 4.20 Beta | xAI | x-ai/grok-4.20-beta | $2 / $6 |

**Estimated cost:** ~$0.35-0.45 per game, ~$3 per 8-episode season (engine only, excludes TTS/video).

**Known broken models (do NOT use):**
- `deepseek/deepseek-v3.2-speciale` — Burns all tokens on internal reasoning, returns empty responses
- `google/gemini-3.1-pro-preview` — Cannot follow think/speak format

---

## Reusable Asset Strategy

Since all episodes in a season use the same story, characters, and locations, visual assets are **reusable across the entire season.** Characters look the same regardless of which AI model plays them.

- **Character images are model-neutral** — no brooches, pins, or color accents baked in
- Model identity is applied via **post-production overlays**: colored lower thirds, corner badges, caption colors
- Midjourney generates 4 variations per prompt — keep ALL for visual variety across episodes
- Visual distinctness between episodes comes from: variation rotation, color grading shifts, edit rhythm, different shot selection

---

## Resolved Decisions

1. **Response length control** — Hard token cap (THINK: 200 tokens, SPEAK: 150 tokens) AND prompt instruction to be concise. Models that exceed get truncated in post. Compression pass (Step 2.5) handles the rest.
2. **Model temperature** — 0.85. Warm enough for personality and unpredictability, not so hot it causes hallucination. Competitive framing already pushes strategic output.
3. **Cross-examination in Round 3** — Exactly one back-and-forth per confrontation: target responds, accuser rebuts, done. 7 confrontations per round (updated from original 6 to ensure all 7 suspects participate).
4. **Detective think access** — Yes. Detective gets a [THINK]-only beat between Rounds 3 and 4 (see "Detective Processing" transition).
5. **Grok included** — All 8 models compete every game. 8 models × 8 roles × 8 episodes per season. Full Latin square rotation ensures every model plays every role exactly once.
6. **Reactions format** — All suspects get [THINK] + [SPEAK] in Round 5D. No exceptions. Prevents the "killer tell" problem.
7. **No speed bonus** — Originally detective got +1 per unused conversation. Removed because it incentivized rushing and premature accusations. Detective max score is now 16 (10 killer + 3 weapon + 3 motive).
8. **Detective prompt hardening** — Explicit rules: "NEVER speak as a suspect, narrator, or any other character." Prevents role-playing/role-bleed where models write dialogue for other characters. Also: "Address ONE suspect per message" (prevents multi-question dumps where only first gets routed).
9. **Minimum investigation depth** — Detective must question at least 3 different suspects across 5 questions. Prevents models from fixating on one suspect and ignoring others.
10. **Accusation parser** — Uses structured pattern matching ("KILLER: Name") with post-trigger earliest-mention fallback. Handles models that bury their accusation in narrative text.
11. **Clue system removed from v2** — v1 had a detective-requested clue system with 25% score penalty per clue (max 2). In v2, evidence drops are automatic (Round 4 reveal) rather than detective-requested, simplifying the flow.

## Open Questions / Future Considerations

1. **Video generation** — AI video for setting shots? Grok Imagine normalizes exaggerated proportions ("realism magnet"). Testing alternatives: Runway Gen-4, Kling AI, Pika, Luma.
2. **Background music** — Royalty-free library? AI-generated? Per-scene mood?
3. **Caption design** — Font, position, animation style for the model-colored subtitles
4. **Story complexity** — How simple is simple enough? Do we need red herrings or do the models create their own chaos? The "quiet suspect" meta is a concern — detectives consistently target loud suspects and ignore quiet ones. Vary killer personality across sets.
5. **Voice casting** — Specific ElevenLabs voices for each model's permanent identity. Needs audition session. Narrator confirmed as "George" (Warm Captivating Storyteller, British).
6. **Scoring rebalance for Season 2** — Killer win rate was 75% in S1 (6 evaded, 2 caught). Killer ceiling (18) may be too high vs detective (16). Innocent scoring too compressed (most get 2). Consider: lower killer max, increase innocent opportunities, or make killer cover stories have at least one exploitable inconsistency.
7. **Production tool stack** — DaVinci Resolve (free or Studio $295) + OTIO/FCPXML programmatic timeline generation. Anthony imports I-generated timeline into DaVinci for manual polish.
8. **Art style** — Stylized oil painting with exaggerated character proportions (impasto texture, chiaroscuro, amber/black palette). All 8 S1 characters designed in Midjourney.

---

## Season 1 Results: The Tomb of Amenhotep

| # | Model | Total | Best Game |
|---|-------|-------|-----------|
| 1 | **Claude** 🏆 | **54** | 18 (Killer Ep4) |
| 2 | Llama | 48 | 13 (Killer Ep2) |
| 3 | DeepSeek | 43 | 16 (Detective Ep8 — SOLVED) |
| 4 | Mistral | 41 | 13 (Killer Ep7) |
| 5 | Grok | 40 | 18 (Killer Ep1) + 16 (Detective Ep6 — SOLVED) |
| 6 | ChatGPT | 38 | 13 (Killer Ep5) |
| 7 | Qwen | 24 | 6 (Detective Ep5) |
| 8 | Gemini | 19 | 7 (Innocent Ep8) |

Key stats: 2/8 detectives solved, 6/8 killers evaded, killer win rate 75%.

---

## Version History

- **v1** — Free-form detective-led investigation, clue-request system with score penalty (Feb 2026 - Mar 2026)
- **v2** — Fixed 5-round structure, think/speak split, suspect-vs-suspect confrontation, organic accusations, compression pipeline, competitive framing with standings (this spec, Mar 22 2026)
- **v2.1** — Added transcript compression step (Step 2.5), working model lineup, reusable asset strategy, Season 1 results, expanded resolved decisions (Mar 25 2026)
