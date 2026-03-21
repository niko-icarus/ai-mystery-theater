# The Lineup — Overnight Review Notes
*March 20-21, 2026 — Niko's observations after 9 test runs*

## What's Working Well
- **Mystery difficulty is dialed in.** After fixing the evidence, only 1 of 7 detectives (post-fix) solved it. The quiet killer strategy works perfectly.
- **Competition framing** makes the games feel like they matter. Models are investing effort.
- **Clue request system** is a great mechanic. Only Gemini used it — and it cost them. Real risk/reward.
- **Group setting** creates emergent drama — suspects accusing each other, interrupting, contradicting. Claude Sonnet as angry Hessler was theater gold.
- **DeepSeek's winning strategy** was brilliant — instead of interrogating suspects about themselves, it asked everyone else what they noticed about Teodora. That's genuinely clever detective work.

## Improvement Ideas

### 1. Detective Asks Multiple Questions Per Turn (Bug/Design Issue)
Several detectives tried to ask multiple suspects in one message (e.g., "Hessler: where were you? Marguerite: did you see anything?"). The engine only routes to the first name matched. We should either:
- **Enforce one question per turn** in the detective prompt (cleaner)
- Or split multi-questions into separate API calls (complex, probably not worth it)
Recommend: add to detective prompt "Ask ONE suspect ONE question per turn."

### 2. Suspect Response Length Varies Wildly
Some models give 2 sentences, others write full paragraphs. This impacts:
- Game pacing (long responses = slow game)
- TTS script length (more chars = more cost)
- Video production (hard to plan clips)
Consider adding a **word/character cap** enforced by the engine — truncate or re-prompt if a response exceeds, say, 150 words.

### 3. The "Quiet Suspect" Strategy Is Too Strong
Teodora evaded 7 straight times by being quiet and unremarkable. This is realistic but might get predictable. Ideas:
- **Give the guilty suspect a reason to talk** — maybe other suspects or evidence force them into conversation
- **Award detective bonus points for questioning ALL suspects** — penalize ignoring anyone
- **Narrator can prompt underquestioned suspects** — "The detective has not yet questioned Teodora Novak" after a few rounds

### 4. Speed Bonus May Be Too Generous
Speed bonus = 36 - conversations. A detective who solves in 8 conversations gets +28 bonus vs +20 for base score. The bonus dominates the score. Consider:
- Cap speed bonus at 15 or 20
- Or make it a multiplier instead of additive

### 5. Innocent Scoring Still Needs Work
Most innocents get 8 points regardless. The "useful info" detection (keyword matching) is too crude. Ideas:
- **Have the engine use a cheap LLM call post-game** to evaluate each innocent's contribution
- Or accept that innocent scoring is inherently hard to automate and keep it simple

### 6. Narrator Should Announce Round Progress
The audience (and detective) would benefit from knowing: "Round 2 of questioning begins. 8 conversations used of 36 available." Helps with pacing and creates natural chapter breaks for video.

### 7. Post-Game Highlight Extraction
For video production, it would help to auto-identify the **key moments**:
- The most dramatic exchange (longest back-and-forth with one suspect)
- The clue request moment (if any)
- The accusation
- The best suspect reaction
These could be tagged as "highlight" segments in the script extractor.

### 8. Consider a "Final Statement" Phase
Before the accusation, give each suspect 1 final statement. This creates a natural climax where the guilty suspect has one last chance to deflect and innocents can make their final case. Good for video pacing.

### 9. Multi-Question Bug in Accusation
DeepSeek's accusation included analysis of ALL suspects before naming the killer. The accusation parser now handles this, but we should add to the detective prompt: "When making your accusation, state the killer's name FIRST, then explain your reasoning."

### 10. Game Config Variety for Season 1
Same mystery 9 times has been great for testing, but for the actual season we need 5 genuinely different mysteries. Each should test different detective skills:
- Set 1: Classic whodunit (who had opportunity?) — done
- Set 2: Multiple suspects with means (who had motive?)
- Set 3: Locked room / limited access (how was it done?)
- Set 4: Multiple crimes / red herring death (what actually happened?)
- Set 5: Conspiracy — 2 guilty suspects working together

## Quick Fixes (Can Do Immediately)
- [ ] Add "Ask ONE suspect ONE question per turn" to detective prompt
- [ ] Add "State the killer's name FIRST in your accusation" to detective prompt
- [ ] Add round progress announcements from narrator
- [ ] Cap speed bonus at 20

## Bigger Improvements (Discuss with Anthony)
- [ ] Suspect response length enforcement
- [ ] "Quiet suspect" countermeasures
- [ ] Final statement phase
- [ ] Post-game highlight tagging
- [ ] LLM-based innocent scoring
