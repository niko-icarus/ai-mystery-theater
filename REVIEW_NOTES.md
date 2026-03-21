# The Lineup — Overnight Review Notes (Mar 21, 2026)

Notes from reviewing the engine, 9 test runs, and scripts. For Anthony to discuss.

---

## What's Working Well
- **Mystery difficulty is dialed in** — 1 solve in 9 runs, and it was by the cheapest model (DeepSeek). The upgraded models overthink it.
- **Clue request mechanic** — Gemini was the only one to use it, and it was a genuine strategic moment. The 25% penalty feels meaningful.
- **Mistral Large as the guilty suspect** — 7 evasions before getting caught. Plays quiet and composed, exactly what a guilty party should do.
- **Group setting dynamics** — suspects referencing each other's statements, accusing each other, contradicting each other. Creates natural drama.
- **DeepSeek's winning strategy** — instead of interrogating the obvious suspects, it asked everyone else about Teodora. Brilliant detective work.

---

## Improvement Ideas

### 1. Detective Asks Multiple Questions Per Turn
Right now, some detectives (especially DeepSeek) blast multiple questions at multiple suspects in one message, but only the first-mentioned suspect responds. This wastes the detective's turn. Two options:
- **Option A:** Enforce in the prompt: "Ask ONE suspect ONE question per turn"
- **Option B:** Parse multiple questions and let each addressed suspect respond
- Recommend Option A — simpler, better for video pacing, and forces more deliberate strategy.

### 2. Suspect Cross-Talk
Suspects can hear everything but rarely interject unprompted. Consider adding a mechanic where after every 4-6 exchanges, the engine prompts all suspects: "Does anyone have anything to add?" This could:
- Let innocents volunteer observations
- Force the guilty party to decide whether to stay quiet (safe but suspicious) or speak up (risky but natural)
- Create more organic group dynamics for video

### 3. Detective's "Thinking Out Loud" Problem
Detectives often narrate their internal reasoning ("Let me analyze the alibis...") which wastes tokens and doesn't add to the game. Could add to the prompt: "Do not narrate your reasoning. Just ask questions and make your accusation."

### 4. Response Length Enforcement
Suspects were told "2-3 sentences" but regularly give 4-6 sentences. This inflates the script character count. Could:
- Add a hard word cap in the system prompt (e.g., "Maximum 50 words per response")
- Or have the engine truncate after 3 sentences before adding to history

### 5. Score Parity Between Roles
Right now, the guilty suspect can score 23 by evading, but a perfect detective scores ~50. This means playing detective is always higher-value than playing suspect. For season balance:
- Consider bumping guilty evasion to 25-30
- Or adding "style points" for suspects who particularly deflect well

### 6. Accusation Should Include Reasoning Phase
When the detective accuses, the other suspects and the audience don't know why. Add a required "accusation monologue" where the detective lays out their case BEFORE the reveal. This is crucial for video — it's the climax. Currently some detectives do this naturally, others just say "KILLER: Name" and that's it.

### 7. The "Hessler Problem"
Across 9 runs, Hessler was falsely accused 5+ times. He's designed as the obvious red herring (loud, threatening, military), and it works TOO well. For future sets, vary which suspect is the "loud obvious" one so the pattern doesn't become predictable across a season.

### 8. Video Segment Tagging Needs Work
Almost everything gets tagged "narration" (62/70 segments in Run 8). The video/narration split was supposed to be ~50/50 but it's more like 3/97. The 25-word "video" threshold might be too tight. Consider:
- Raising the video threshold to 40-50 words
- Or tagging based on content type (reactions, short denials → video) not just length

### 9. Post-Game Summary for Video Intro/Outro
Would be useful to auto-generate a brief summary for video intros: "In this episode, [Detective model] investigates the murder of [victim] aboard [location]. Can they crack the case, or will [killer role] evade justice?" And an outro with season standings.

### 10. Cost Tracking Per Run
Add token count tracking to the engine — log total input/output tokens and estimated cost at the end of each game. Right now we have to check OpenRouter separately. Would help budget season runs.

---

## Quick Fixes (small effort, should do before video test)
1. ~~Accusation parser bug~~ ✅ Fixed
2. ~~Name-matching bug~~ ✅ Fixed  
3. ~~Safety cap~~ ✅ Fixed
4. Enforce "one question per turn" in detective prompt
5. Add "do not narrate reasoning" to detective prompt
6. Tighten suspect response length in prompt

## Bigger Items (for later)
- Suspect cross-talk mechanic
- Score rebalancing
- Video tagging overhaul
- Cost tracking
- Post-game summary generator
