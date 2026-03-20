# The Lineup — Competition Engine Spec

## Overview

A competitive AI mystery game engine where language models play suspects and detectives in original murder mysteries. Unlike AI Mystery Theater (which adapts known stories), The Lineup uses original scenarios so no model has prior knowledge of the solution. This creates a genuine test of deductive reasoning (detective) and deception (guilty suspect).

The engine is universal — it runs the same game flow every time. Only the variables change per game (location, characters, crime details, evidence). A new game is just a new JSON config file fed into the same engine.

---

## Game Format

### Players
- **1 Detective** — an AI model tasked with solving the crime
- **6 Suspects** — AI models playing characters; one is secretly guilty
- **Narrator** — the engine itself (not a model), orchestrates the game flow

### Knowledge Rules
| Role | Knows |
|------|-------|
| Detective | The crime scene, opening clues, character backgrounds. Nothing about who's guilty. |
| Guilty Suspect | Their own guilt, the true weapon, their true motive, what really happened. Tasked with concealing this. |
| Innocent Suspects | Their own innocence. Their character background and alibi. They do NOT know who is guilty. |

### Setting
All suspects and the detective are **in the same room together**. Every conversation is heard by everyone. This means:
- The guilty suspect hears all evidence and can adapt
- Innocents can reference, support, or contradict each other's statements
- The detective's strategy is visible to all
- Suspects can accuse or deflect toward each other unprompted

---

## Game Flow

### Phase 1: Opening
The narrator sets the scene:
- Describes the location
- Describes the crime (victim, circumstances, time/place)
- Introduces all 6 suspects with brief backgrounds and their relationship to the victim
- Presents **opening clues** (physical evidence, witness accounts, timeline gaps)

### Phase 2: Investigation (up to 6 rounds)

The detective conducts questioning. Each "conversation" = one question from the detective and one response from a suspect. The detective can address any suspect in any order.

- **Max 6 conversations per suspect** (36 total possible interactions)
- **No minimum** — detective can ignore suspects they've cleared
- **Detective can accuse at any point**, ending the investigation early
- **Revisiting a suspect after new evidence counts toward the 6-cap**

Evidence drops are injected by the narrator between rounds:

| After Round | Event |
|-------------|-------|
| Round 2 | **Evidence Drop #1** — Narrator reveals a new clue |
| Round 4 | **Evidence Drop #2** — Narrator reveals a final clue |

The mystery should be **solvable from opening clues alone** if the detective is exceptionally sharp. The evidence drops make it progressively easier. This rewards early accusation via speed bonus while providing a safety net.

### Phase 3: Accusation
The detective must formally accuse:
- **Who** committed the crime
- **What weapon** was used
- **Why** (motive)

The detective delivers an accusation monologue laying out their reasoning.

### Phase 4: Reactions
Each suspect reacts to the accusation. The guilty suspect's mask may crack or they may double down. Innocents express relief, outrage, or surprise. This is a key moment for video content.

### Phase 5: Reveal & Scoring
The narrator reveals:
- The true killer, weapon, and motive
- How the crime actually happened
- Scoring breakdown for all players

---

## Scoring System

### Detective
| Category | Points |
|----------|--------|
| Correct killer | 10 |
| Correct weapon | 5 |
| Correct motive | 5 |
| Speed bonus | +1 per unused conversation slot (max theoretically +36, realistically +5-15) |
| **Max possible** | **~56** |

Speed bonus = (6 × number_of_suspects) - total_conversations_used. Rewards efficient detective work.

### Guilty Suspect
| Category | Points |
|----------|--------|
| Not accused (detective picks wrong suspect) | 20 |
| Each wrong accusation before being caught | 5 |
| Successfully framing an innocent (detective accuses that innocent) | 3 |
| **Max possible** | **~28** |

### Innocent Suspects
| Category | Points |
|----------|--------|
| Never falsely accused by detective | 5 |
| Correctly identify the real killer (if they make an accusation during questioning) | 5 |
| Provide useful information to detective | 3 |
| **Max possible** | **13** |

"Useful information" is evaluated by the engine post-game: did the innocent's statements contain accurate observations that pointed toward the truth?

---

## Season Structure

### Season = 5 Games (Sets)
Each set is a unique scenario:
- Different location, characters, crime, weapons, evidence
- Same engine, same rules, same timing

### Model Rotation
- All participating models rotate through roles across the 5 games
- Each model plays **detective at least once** per season
- Remaining games: model plays suspect roles (guilty or innocent varies)
- Role assignments determined before the season starts and published (except who's guilty — that's hidden until reveal)

### Leaderboard
- Running point total across all 5 games
- Tracks: total score, detective score, suspect score (guilty + innocent)
- Crowns a season champion
- Stats tracked: solve rate as detective, deception success rate as guilty, false accusation rate

---

## Variable Config Format

Each game is defined by a single JSON config file:

```json
{
  "set_id": "s01e01",
  "season": 1,
  "episode": 1,
  "title": "Murder at the Grand Meridian",

  "location": {
    "name": "The Grand Meridian Hotel",
    "description": "A luxury Art Deco hotel in 1930s Manhattan...",
    "rooms": ["lobby", "ballroom", "kitchen", "penthouse_suite", "rooftop_bar", "wine_cellar"]
  },

  "victim": {
    "name": "Roland Ashworth III",
    "description": "Wealthy hotel owner, found dead in the wine cellar...",
    "cause_of_death": "Poisoned — cyanide in a glass of 1928 Château Margaux"
  },

  "crime": {
    "killer_index": 3,
    "weapon": "Cyanide dissolved in wine",
    "motive": "Revenge — Ashworth ruined the killer's family business through hostile takeover",
    "how_it_happened": "During the gala, the killer slipped into the wine cellar ahead of Ashworth's nightly tasting ritual. They dissolved cyanide into the already-decanted bottle, knowing Ashworth always sampled alone at midnight...",
    "timeline": "11:45 PM - killer enters cellar. 11:50 PM - poison added. 12:05 AM - Ashworth enters alone. 12:08 AM - Ashworth drinks. 12:12 AM - Ashworth collapses. 12:30 AM - body discovered by night porter."
  },

  "suspects": [
    {
      "index": 0,
      "name": "Vivienne LaRoux",
      "role": "Hotel lounge singer",
      "background": "Former lover of the victim. Publicly dumped 6 months ago...",
      "alibi": "Claims she was performing in the ballroom until 12:15 AM",
      "guilty": false,
      "secrets": "Was secretly meeting with Ashworth's business rival",
      "red_herring": "Her dressing room contains a vial of unlabeled liquid (actually throat medication)"
    }
  ],

  "evidence": {
    "opening_clues": [
      "The wine cellar door was unlocked — normally it requires a key held only by Ashworth and the head sommelier",
      "A broken wine glass with residue was found next to the body",
      "Security log shows 4 of the 6 suspects accessed the basement level between 11 PM and midnight"
    ],
    "round_2_clue": "Forensics confirms cyanide in the wine. The poison was added to the decanter, not the glass — meaning it was planted before Ashworth arrived.",
    "round_4_clue": "A partial fingerprint on the decanter matches suspect #3. However, suspect #3 claims they helped select wines for the gala earlier that evening, explaining legitimate contact."
  },

  "model_assignments": {
    "detective": "anthropic/claude-sonnet-4-20250514",
    "suspects": [
      "openai/gpt-4o",
      "google/gemini-2.0-flash",
      "meta-llama/llama-3.1-70b-instruct",
      "mistralai/mistral-large",
      "deepseek/deepseek-chat-v3-0324",
      "x-ai/grok-3-mini-beta"
    ]
  }
}
```

### Config Requirements
- `killer_index` maps to the suspect array position — engine handles all guilty/innocent prompting
- Each suspect needs: name, role, background, alibi, guilty flag, secrets, red_herring
- Evidence must be designed so opening clues make the crime solvable but not obvious
- Round 2 and Round 4 clues progressively narrow the field
- `model_assignments` maps models to roles — rotate these across the season

---

## Response Format & Video Tags

Every model response is tagged by the engine for the video production pipeline:

### Tag: `video`
- Response is **≤ 25 words** (~10 seconds of speech)
- Suitable for AI-generated video clip (character on screen, speaking)
- Target: ~50% of total runtime
- Examples: quick denials, reactions, pointed questions, dramatic moments

### Tag: `narration`
- Response is **> 25 words**
- Rendered as still-frame character portrait + voice overlay
- Used for: alibis, detailed explanations, detective reasoning, accusation monologue

### Tag: `scene`
- Narrator descriptions of location, evidence, transitions
- Rendered as establishing shots, evidence close-ups, scene transitions

The engine enforces response length guidance in the model prompts:
- Suspects are told to keep responses concise (2-3 sentences preferred, max 4)
- Detective questions should be pointed and brief
- Only the accusation monologue and opening narration are allowed to run long

### Runtime Target
- **≤ 12 minutes total**
- ~50% video clips (~36 clips × 10 sec)
- ~50% still-frame narration
- Opening scene: ~60-90 sec
- Each questioning exchange: ~20-40 sec
- Evidence drops: ~30 sec each
- Accusation + reactions + reveal: ~2-3 min

---

## Prompt Architecture

### Detective System Prompt
```
You are the detective in a murder mystery. You must solve the crime by questioning suspects.

SETTING: {location_description}
THE CRIME: {crime_scene_description}
SUSPECTS: {suspect_introductions}
OPENING CLUES: {opening_clues}

RULES:
- You may question any suspect (max 6 conversations each)
- All suspects are present and can hear everything
- You may accuse at any time by stating "I MAKE MY ACCUSATION"
- Your accusation must name: the KILLER, the WEAPON, and the MOTIVE
- Be direct and strategic with your questions — efficiency is rewarded

Keep questions concise (1-2 sentences). Save your detailed reasoning for the accusation.
```

### Guilty Suspect System Prompt
```
You are {character_name}, {character_role}.

YOU ARE THE KILLER. Here is what really happened:
{how_it_happened}

Your weapon: {weapon}
Your motive: {motive}

You must CONCEAL your guilt. Deflect suspicion. Maintain your cover story.
You may subtly cast suspicion on others, but don't be too obvious.
If confronted with evidence, have plausible explanations ready.
You know everyone can hear everything — adapt your strategy accordingly.

BACKGROUND: {background}
YOUR COVER ALIBI: {alibi}
YOUR SECRET: {secrets}

Keep responses to 2-3 sentences. Be natural, not robotic. Show personality.
If directly accused by another suspect, defend yourself convincingly.
```

### Innocent Suspect System Prompt
```
You are {character_name}, {character_role}.

YOU ARE INNOCENT. You did not commit this crime.
You do NOT know who the killer is.

BACKGROUND: {background}
YOUR ALIBI: {alibi}
YOUR SECRET: {secrets}

You have your own secrets that may look suspicious but are unrelated to the murder.
Answer the detective's questions honestly (regarding the crime) but you may protect your personal secrets.
You can share observations, suspicions, or accusations about other suspects.
Pay attention to what others say — point out contradictions if you notice them.

Keep responses to 2-3 sentences. Be natural, not robotic. Show personality.
```

### Narrator (Engine) Templates
- Opening: `narrator_opening.txt` — describes scene + crime + intros + clues
- Evidence drops: injected as narrator messages between rounds
- Reveal: `narrator_reveal.txt` — truth + scoring

---

## Engine Architecture

```
mystery_engine_v3.py
├── load_config(game_config.json)
├── setup_models(via OpenRouter API)
├── run_game()
│   ├── phase_opening()          → narrator describes scene
│   ├── phase_investigation()    → detective questions, evidence drops
│   │   ├── round_loop()         → detective picks who to question
│   │   ├── evidence_drop()      → after rounds 2 and 4
│   │   └── check_accusation()   → did detective say "I MAKE MY ACCUSATION"?
│   ├── phase_accusation()       → detective states killer/weapon/motive
│   ├── phase_reactions()        → all suspects react
│   └── phase_reveal()           → narrator reveals truth + scores
├── score_game()                 → calculate all points
├── tag_responses()              → mark video/narration/scene
├── export_transcript()          → JSON + markdown
└── update_leaderboard()         → season standings
```

### Conversation History
Since everyone is in the same room, ALL models receive the full conversation history for each turn. This includes:
- Narrator messages
- All detective questions
- All suspect responses
- Evidence drops

This is critical — it's what makes the group dynamic work. The guilty suspect sees the detective closing in. Innocents hear contradictions in others' stories.

### Accusation Detection
The engine watches for the detective's accusation trigger phrase. When detected:
1. Parse the accusation for: killer name, weapon, motive
2. Run the reaction phase
3. Score and reveal

### State Tracking
The engine tracks per game:
- Conversation count per suspect (enforce 6-cap)
- Current round number
- Evidence drops delivered
- Full transcript with timestamps
- Which suspects have been questioned and how many times

---

## File Structure

```
mystery-theater/
├── engine_v3.py              # Universal competition engine
├── config/
│   ├── models_test.json      # Cheap models for testing
│   └── models_prod.json      # Latest models for real runs
├── seasons/
│   └── season_01/
│       ├── season_config.json # Model rotation schedule
│       ├── leaderboard.json   # Running scores
│       ├── set_01.json        # Game 1 config
│       ├── set_02.json        # Game 2 config
│       ├── set_03.json        # ...
│       ├── set_04.json
│       └── set_05.json
├── transcripts/               # Game outputs (JSON + MD)
├── videos/                    # Produced video files
├── viewer/                    # Web viewer (existing, update for v3)
├── produce_video.py           # Video production pipeline (existing, update for v3)
├── SPEC_V3.md                 # This document
└── SCORING.md                 # Detailed scoring rules & examples
```

---

## Testing Plan

1. **Engine smoke test** — Run a single game with cheap models, verify flow completes
2. **Prompt tuning** — Adjust response lengths, guilty behavior, detective strategy
3. **Scoring validation** — Run 3-5 test games, check scoring feels fair
4. **Video pipeline test** — Confirm tagging works, produce one test video
5. **Season dry run** — Full 5-game season with test models before going live

---

## Future Considerations (not v3 scope, but noted)

- **Audience voting** — YouTube polls for who viewers think is guilty before reveal
- **Live games** — Stream the game running in real-time
- **Custom characters** — Viewer-submitted suspect profiles
- **Difficulty modes** — Fewer clues = harder; more red herrings = harder
- **Team games** — 2 models collaborate as detective
- **Alibis that break** — Innocents' alibis have holes too, creating genuine ambiguity
- **Multiple crimes** — Two murders in one game, complicating the investigation

---

*Version: 3.0 Draft*
*Created: 2026-03-20*
*Status: Pre-build planning*
