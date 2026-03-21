# The Lineup — Review Notes (Overnight Mar 20-21, 2026)

## What's Working Well
- **Mystery difficulty is right** — 1 solve in 9 runs. Tough but not impossible.
- **Clue request mechanic** — great strategic tension, only used once across 9 runs
- **Competition framing** — models take it more seriously with season context
- **Role bleed fixed** — models stay in character consistently now
- **DeepSeek's strategy in Run 9 was brilliant** — asked other suspects about Teodora instead of interrogating her directly. This is emergent behavior we didn't design for.

## Bugs Fixed Today
- ✅ Name matching (earliest mention, not first config order)
- ✅ Accusation parser (structured patterns + post-trigger search)
- ✅ Safety cap (40 rounds)
- ✅ Model availability (7 confirmed on OpenRouter)

## Improvement Ideas for Anthony

### 1. Detective Asks Multiple Questions Per Turn
Currently DeepSeek asked 6 suspects at once in a single message, but the engine only routes to the first name match. Consider either:
- **Enforcing one question per turn** in the detective prompt ("Ask ONE suspect ONE question per turn")
- **Or** teaching the engine to handle multi-question turns (harder, probably not worth it)
Recommendation: enforce one-at-a-time — it's better for video pacing anyway.

### 2. Suspect Cross-Talk
Right now suspects only respond when questioned by the detective. But the spec says suspects can accuse each other. We could add a mechanic where after every 4-6 detective questions, the narrator prompts "Suspects, does anyone have anything to add?" and each suspect gets one optional interjection. This would:
- Create more dramatic moments
- Let innocents point fingers (scoring opportunity)
- Force the guilty suspect to manage more social pressure

### 3. The "Quiet Suspect" Problem
Teodora's winning strategy is to be quiet and unremarkable. Every detective goes after the loud suspects (Hessler, Kurtz) and ignores the calm one. Possible fixes:
- **Narrator nudge**: after the first pass, narrator could say "The detective notes that [least-questioned suspect] has been unusually quiet throughout the investigation."
- **Or** let this be a feature, not a bug — it rewards smart detective play when someone DOES catch on (like DeepSeek did)
- I lean toward leaving it — it's what makes the game interesting

### 4. Cost Tracking Per Run
Add token counting / cost estimation to the engine output. We know Creator plan = 100K chars/month for ElevenLabs, and OpenRouter charges per token. Showing cost-per-run in the final report helps budget the season.

### 5. Video Production Pipeline
For the weekend audio/video test, the flow would be:
1. Run game → transcript JSON
2. `extract_script.py` → TTS script
3. Send to ElevenLabs (assign voice per character)
4. Generate still frames / AI video clips
5. Assemble with ffmpeg

We already have `produce_video.py` from Mystery Theater — needs adapting for The Lineup's format. Key differences:
- More characters (8 speakers vs 7)
- Longer runtime
- Script extractor as intermediary step
- Video/narration tagging

### 6. Narrator Should Announce the Accusation Target
When the detective accuses, the narrator says "accusing [name]" — but this comes from the parser, which was buggy. Now that the parser is fixed, we should also have the narrator READ BACK the parsed accusation to confirm: "The detective has accused [parsed name] as the killer, with [parsed weapon] and [parsed motive]." This gives the suspects (and the audience) a clear moment.

### 7. Season Config / Rotation
Still need to build this properly when we're ready for Season 1. Each model should detective once. With 7 models and 5 games, 2 models won't detective — compensate by giving them guilty roles (higher scoring potential).

### 8. Post-Game Stats
Add to the transcript/output:
- Total API tokens used
- Estimated OpenRouter cost
- Estimated ElevenLabs characters (from script extractor)
- Game duration (wall clock)
- Most-questioned suspect
- Least-questioned suspect
