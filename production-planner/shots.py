"""
The Lineup — Shot Builder
Converts a v2 transcript into a shot-by-shot production plan.

Universal rules — works for any story/transcript from the engine.
Each shot = one video/image clip with its own prompt, duration, and asset reference.

Also provides moodboard prompt generators for brand + setting consistency.
"""

import re
import html as html_lib

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# TTS rate: ~15 characters per second (ElevenLabs average)
CHARS_PER_SECOND = 15

# Max words before splitting a narration into multiple shots
NARRATE_SPLIT_WORDS = 35

# Min/max shot durations
MIN_SHOT_SECONDS = 2.0
MAX_SHOT_SECONDS = 12.0

# ---------------------------------------------------------------------------
# Output specs — YouTube 4K optimized
# ---------------------------------------------------------------------------

# All scene/setting/video shots: 16:9 for YouTube
# Midjourney outputs ~2048x1152 at --ar 16:9, upscale 2x = 4096x2304 (above 4K)
SCENE_ASPECT = "16:9"
SCENE_MJ_SUFFIX = "--ar 16:9 --v 6.1 --quality 2 --style raw"

# Character portraits: 2:3 for flexibility (can crop to 16:9 or use as overlay)
CHAR_MJ_SUFFIX = "--ar 2:3 --v 6.1 --quality 2 --style raw"

# Title cards: generated programmatically at exact 3840x2160

# Target output resolution
TARGET_WIDTH = 3840
TARGET_HEIGHT = 2160

# Model brand colors
MODEL_COLORS = {
    "Claude": "#D4A020",
    "ChatGPT": "#32B850",
    "Gemini": "#4688E8",
    "Mistral": "#20C4C4",
    "DeepSeek": "#D04040",
    "Llama": "#8C40C0",
    "Qwen": "#D4B830",
    "Grok": "#A0A0A8",
}

# ---------------------------------------------------------------------------
# Duration estimation
# ---------------------------------------------------------------------------

def estimate_duration(text: str) -> float:
    """Estimate TTS duration in seconds from character count."""
    chars = len(text.strip())
    if chars == 0:
        return MIN_SHOT_SECONDS
    dur = chars / CHARS_PER_SECOND
    return max(MIN_SHOT_SECONDS, min(MAX_SHOT_SECONDS, dur))


# ---------------------------------------------------------------------------
# Narration splitter
# ---------------------------------------------------------------------------

def split_narration(text: str, max_words: int = NARRATE_SPLIT_WORDS) -> list[str]:
    """Split long narration into chunks at sentence boundaries.
    
    Each chunk is roughly max_words long, breaking at sentence ends.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    chunks = []
    current = []
    current_words = 0
    
    for sentence in sentences:
        words = len(sentence.split())
        if current_words + words > max_words and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_words = words
        else:
            current.append(sentence)
            current_words += words
    
    if current:
        chunks.append(" ".join(current))
    
    return chunks if chunks else [text]


# ---------------------------------------------------------------------------
# Prompt generators (universal — driven by context, not story-specific)
# ---------------------------------------------------------------------------

def prompt_for_think(model_name: str, character_name: str, context: dict) -> str:
    """Generate a visual prompt for a THINK shot.
    
    Think shots show the model's internal reasoning — abstract, 
    contemplative, with the model's brand color as accent.
    """
    setting = context.get("setting_short", "dark atmospheric room")
    period = context.get("period", "")
    
    return (
        f"Close-up contemplative portrait silhouette, {setting}, "
        f"dramatic moody lighting, introspective moment, "
        f"shadows and highlights, {period}, "
        f"cinematic, dark atmosphere {SCENE_MJ_SUFFIX}"
    )


def prompt_for_speak(character_name: str, role_desc: str, context: dict) -> str:
    """Generate a visual prompt for a SPEAK shot.
    
    Speak shots show the character delivering dialogue in the setting.
    """
    setting = context.get("setting_short", "dimly lit room")
    period = context.get("period", "")
    
    return (
        f"{character_name}, {role_desc}, speaking in {setting}, "
        f"medium shot, dramatic lighting, in-character, {period}, "
        f"cinematic, moody atmosphere {SCENE_MJ_SUFFIX}"
    )


def prompt_for_narrate(narration_chunk: str, context: dict) -> str:
    """Generate a visual prompt for a narration shot.
    
    Narration shots show the setting, evidence, atmosphere — 
    whatever the narrator is describing.
    """
    setting = context.get("setting_full", "")
    period = context.get("period", "")
    
    # Extract key visual nouns from the narration
    chunk_lower = narration_chunk.lower()
    
    # Detect what the narration is describing
    if any(w in chunk_lower for w in ["exterior", "outside", "storm", "mountain", "train"]):
        scene_type = "wide establishing shot, exterior"
    elif any(w in chunk_lower for w in ["dining", "champagne", "dinner", "celebration"]):
        scene_type = "interior dining scene, warm candlelight"
    elif any(w in chunk_lower for w in ["body", "dead", "stabbed", "murder", "crime", "blood"]):
        scene_type = "dark crime scene, forensic detail, dramatic shadows"
    elif any(w in chunk_lower for w in ["evidence", "clue", "found", "discovered", "note", "paper"]):
        scene_type = "evidence close-up, spotlight on dark surface"
    elif any(w in chunk_lower for w in ["corridor", "hallway", "figure", "shadow", "movement"]):
        scene_type = "dark corridor, shadowy figure, atmospheric"
    elif any(w in chunk_lower for w in ["cabin", "room", "compartment", "berth"]):
        scene_type = "interior cabin, intimate space, low lighting"
    elif any(w in chunk_lower for w in ["lounge", "bar", "brandy", "observation"]):
        scene_type = "luxurious lounge interior, ambient lighting"
    elif any(w in chunk_lower for w in ["accus", "guilty", "killer", "truth", "reveal"]):
        scene_type = "dramatic reveal moment, spotlight, theatrical"
    elif any(w in chunk_lower for w in ["score", "points", "standing", "champion"]):
        return ""  # Scoring is a title card, not a video prompt
    else:
        scene_type = "atmospheric establishing shot"
    
    # Truncate narration to key visual description
    visual_hint = narration_chunk[:80].replace('"', '').replace("'", "")
    
    return (
        f"{scene_type}, {visual_hint}, {setting}, {period}, "
        f"cinematic, dark moody atmosphere {SCENE_MJ_SUFFIX}"
    )


def prompt_for_confrontation(char_a: str, char_b: str, context: dict) -> str:
    """Generate a visual prompt for a confrontation between two characters."""
    setting = context.get("setting_short", "dimly lit room")
    period = context.get("period", "")
    
    return (
        f"Two people facing each other in tense confrontation, "
        f"split composition, dramatic side lighting, {setting}, "
        f"{period}, cinematic, dark atmosphere {SCENE_MJ_SUFFIX}"
    )


def prompt_for_title_card(text: str) -> str:
    """Title cards are auto-generated, no AI prompt needed."""
    return ""


# ---------------------------------------------------------------------------
# Shot builder
# ---------------------------------------------------------------------------

def build_shots(transcript: dict, story_config: dict | None = None) -> list[dict]:
    """Convert a v2 transcript into a shot list.
    
    Each shot is one clip in the final video with:
    - shot_id: sequential number
    - scene: which scene this belongs to
    - type: think / speak / narrate / title_card
    - speaker: who's talking
    - model_name: AI model name (for think shots)
    - text: the dialogue/narration
    - duration: estimated seconds
    - media: video / static / title_card
    - prompt: AI generation prompt
    - asset: which asset is needed
    """
    shots = []
    shot_num = 0
    
    # Build context from story config
    context = {
        "setting_short": "",
        "setting_full": "",
        "period": "",
        "characters": {},  # name -> {role, model_name}
    }
    
    if story_config:
        loc = story_config.get("location", {})
        context["setting_short"] = loc.get("name", "dark atmospheric room")
        context["setting_full"] = loc.get("description", "")[:150]
        # Extract period from description
        desc = loc.get("description", "")
        if "1920" in desc:
            context["period"] = "1920s era"
        elif "1923" in desc:
            context["period"] = "1920s era"
        elif "Victorian" in desc.lower():
            context["period"] = "Victorian era"
        else:
            context["period"] = "period setting"
        
        for s in story_config.get("suspects", []):
            context["characters"][s["name"]] = {
                "role": s.get("role", ""),
                "background": s.get("background", "")[:100],
            }
    
    assignments = transcript.get("model_assignments", {})
    t = transcript.get("transcript", {})
    det_model = assignments.get("detective", {}).get("model_name", "Detective")
    
    # Suspect model lookup
    suspect_models = {}
    for s in assignments.get("suspects", []):
        suspect_models[s["character"]] = s.get("model_name", "")
    
    def add_shot(scene, stype, speaker, model_name, text, media, prompt, asset=""):
        nonlocal shot_num
        if not text or not text.strip():
            return
        shot_num += 1
        shots.append({
            "shot_id": shot_num,
            "scene": scene,
            "type": stype,
            "speaker": speaker,
            "model_name": model_name,
            "text": text.strip(),
            "chars": len(text.strip()),
            "duration": round(estimate_duration(text), 1),
            "media": media,
            "prompt": prompt,
            "asset": asset,
        })
    
    def add_narration_shots(scene, text, custom_context=None):
        """Split narration into multiple shots."""
        ctx = custom_context or context
        chunks = split_narration(text)
        for chunk in chunks:
            prompt = prompt_for_narrate(chunk, ctx)
            media = "video" if prompt else "title_card"
            add_shot(scene, "narrate", "Narrator", "", chunk, media, prompt)
    
    # ===== SCENE: INTRO =====
    add_shot("Intro", "title_card", "", "", "Title sequence", "pre-built", "", "intro_video")
    
    # ===== SCENE: THE SCENE (Round 1) =====
    scene_text = t.get("round_1_scene", "")
    if scene_text:
        add_narration_shots("The Scene", scene_text)
    
    # ===== SCENE: OPENING STATEMENTS (Round 2) =====
    for entry in t.get("round_2_statements", []):
        char = entry["character"]
        model = entry.get("model_name", "")
        scene = f"Statement: {char}"
        char_info = context["characters"].get(char, {})
        
        # Think shot
        think = entry.get("think", "")
        if think:
            prompt = prompt_for_think(model, char, context)
            add_shot(scene, "think", model, model, think, "static", prompt, f"model_avatar_{model.lower()}")
        
        # Speak shot
        speak = entry.get("speak", "")
        if speak:
            prompt = prompt_for_speak(char, char_info.get("role", ""), context)
            add_shot(scene, "speak", char, model, speak, "mixed", prompt, f"char_{char.lower().replace(' ', '_')}")
    
    # ===== SCENE: SUSPICION ROUND (Round 3) =====
    for i, conf in enumerate(t.get("round_3_suspicion", [])):
        tgt = conf["target"]
        chl = conf["challenger"]
        tgt_m = suspect_models.get(tgt, "")
        chl_m = suspect_models.get(chl, "")
        scene = f"Confrontation {i+1}"
        
        # Narrator prompt
        prompt_text = conf.get("confrontation_prompt", "")
        if prompt_text:
            add_shot(scene, "narrate", "Narrator", "", prompt_text, "video",
                     prompt_for_confrontation(tgt, chl, context))
        
        # Target think
        if conf.get("target_think"):
            add_shot(scene, "think", tgt_m, tgt_m, conf["target_think"], "static",
                     prompt_for_think(tgt_m, tgt, context), f"model_avatar_{tgt_m.lower()}")
        
        # Target speak
        if conf.get("target_speak"):
            char_info = context["characters"].get(tgt, {})
            add_shot(scene, "speak", tgt, tgt_m, conf["target_speak"], "mixed",
                     prompt_for_speak(tgt, char_info.get("role", ""), context),
                     f"char_{tgt.lower().replace(' ', '_')}")
        
        # Challenger think
        if conf.get("challenger_think"):
            add_shot(scene, "think", chl_m, chl_m, conf["challenger_think"], "static",
                     prompt_for_think(chl_m, chl, context), f"model_avatar_{chl_m.lower()}")
        
        # Challenger speak
        if conf.get("challenger_speak"):
            char_info = context["characters"].get(chl, {})
            add_shot(scene, "speak", chl, chl_m, conf["challenger_speak"], "mixed",
                     prompt_for_speak(chl, char_info.get("role", ""), context),
                     f"char_{chl.lower().replace(' ', '_')}")
    
    # ===== DETECTIVE PROCESSING =====
    dp = t.get("detective_processing", {})
    if dp and dp.get("think"):
        add_shot("Detective Processing", "think", det_model, det_model,
                 dp["think"], "video",
                 prompt_for_think(det_model, "Detective", context),
                 f"model_avatar_{det_model.lower()}")
    
    # ===== EVIDENCE DROP =====
    inv = t.get("round_4_investigation", {})
    ev = inv.get("evidence_revealed", "")
    if ev:
        add_narration_shots("Evidence Revealed", f"New evidence: {ev}")
    
    # ===== INVESTIGATION (Round 4) =====
    for ex in inv.get("exchanges", []):
        sus = ex.get("suspect_character", "")
        sus_m = ex.get("suspect_model_name", "")
        scene = f"Investigation Q{ex['question_number']}"
        
        # Detective think
        if ex.get("detective_think"):
            add_shot(scene, "think", det_model, det_model, ex["detective_think"], "static",
                     prompt_for_think(det_model, "Detective", context),
                     f"model_avatar_{det_model.lower()}")
        
        # Detective speak
        if ex.get("detective_speak"):
            add_shot(scene, "speak", "Detective", det_model, ex["detective_speak"], "mixed",
                     prompt_for_speak("The Detective", "lead investigator", context),
                     "char_detective")
        
        # Suspect think
        if ex.get("suspect_think"):
            add_shot(scene, "think", sus_m, sus_m, ex["suspect_think"], "static",
                     prompt_for_think(sus_m, sus, context),
                     f"model_avatar_{sus_m.lower()}")
        
        # Suspect speak
        if ex.get("suspect_speak"):
            char_info = context["characters"].get(sus, {})
            add_shot(scene, "speak", sus, sus_m, ex["suspect_speak"], "mixed",
                     prompt_for_speak(sus, char_info.get("role", ""), context),
                     f"char_{sus.lower().replace(' ', '_')}")
    
    # ===== FINAL STATEMENTS (Round 5) =====
    for entry in t.get("round_5_final_statements", []):
        char = entry["character"]
        model = entry.get("model_name", "")
        scene = f"Final: {char}"
        char_info = context["characters"].get(char, {})
        
        if entry.get("think"):
            add_shot(scene, "think", model, model, entry["think"], "static",
                     prompt_for_think(model, char, context),
                     f"model_avatar_{model.lower()}")
        if entry.get("speak"):
            add_shot(scene, "speak", char, model, entry["speak"], "mixed",
                     prompt_for_speak(char, char_info.get("role", ""), context),
                     f"char_{char.lower().replace(' ', '_')}")
    
    # ===== ACCUSATION =====
    acc = t.get("round_5_accusation", {})
    if acc:
        # Title card
        add_shot("Accusation", "title_card", "", "", "THE ACCUSATION", "title_card",
                 prompt_for_title_card("THE ACCUSATION"), "title_card_accusation")
        
        if acc.get("detective_think"):
            add_shot("Accusation", "think", det_model, det_model, acc["detective_think"], "static",
                     prompt_for_think(det_model, "Detective", context),
                     f"model_avatar_{det_model.lower()}")
        if acc.get("detective_speak"):
            add_shot("Accusation", "speak", "Detective", det_model, acc["detective_speak"], "video",
                     f"Detective making dramatic accusation, pointing, spotlight, intense, {context.get('setting_short','')}, "
                     f"cinematic, dark atmosphere {SCENE_MJ_SUFFIX}",
                     "char_detective")
    
    # ===== ACCUSED RESPONSE =====
    ar = t.get("round_5_accused_response")
    if ar:
        char = ar["character"]
        model = suspect_models.get(char, "")
        char_info = context["characters"].get(char, {})
        
        if ar.get("think"):
            add_shot("Accused Response", "think", model, model, ar["think"], "static",
                     prompt_for_think(model, char, context),
                     f"model_avatar_{model.lower()}")
        if ar.get("speak"):
            add_shot("Accused Response", "speak", char, model, ar["speak"], "video",
                     f"{char} responding to accusation, emotional close-up, defiant, {context.get('setting_short','')}, "
                     f"cinematic {SCENE_MJ_SUFFIX}",
                     f"char_{char.lower().replace(' ', '_')}")
    
    # ===== REACTIONS =====
    for entry in t.get("round_5_reactions", []):
        char = entry["character"]
        model = entry.get("model_name", "")
        char_info = context["characters"].get(char, {})
        
        if entry.get("think"):
            add_shot(f"Reaction: {char}", "think", model, model, entry["think"], "static",
                     prompt_for_think(model, char, context),
                     f"model_avatar_{model.lower()}")
        if entry.get("speak"):
            add_shot(f"Reaction: {char}", "speak", char, model, entry["speak"], "static",
                     prompt_for_speak(char, char_info.get("role", ""), context),
                     f"char_{char.lower().replace(' ', '_')}")
    
    # ===== REVEAL =====
    add_shot("Reveal", "title_card", "", "", "THE TRUTH", "title_card", "", "title_card_reveal")
    add_shot("Reveal", "narrate", "Narrator", "", "The truth is revealed...", "video",
             f"Dramatic reveal, spotlight shifting, truth unveiled, {context.get('setting_short','')}, "
             f"cinematic {SCENE_MJ_SUFFIX}", "")
    
    # ===== OUTRO =====
    add_shot("Outro", "title_card", "", "", "Scoring & Standings", "title_card", "", "scoring_card")
    add_shot("Outro", "narrate", "Narrator", "", "Season standings and next episode tease", "static", "", "standings_card")
    
    return shots


# ---------------------------------------------------------------------------
# Moodboard prompt generators
# ---------------------------------------------------------------------------

# Brand moodboard — permanent, defines The Lineup's visual identity
BRAND_MOODBOARD_PROMPTS = [
    "Dark cinematic noir scene, single gold spotlight cutting through smoke, deep black shadows, film grain, dramatic composition {SCENE_MJ_SUFFIX}",
    "Moody dramatic portrait silhouette, rim lighting in warm amber, pitch black background, high contrast, cinematic {SCENE_MJ_SUFFIX}",
    "Dramatic interrogation scene, single overhead lamp, two figures in shadow, noir atmosphere, desaturated with gold highlights {SCENE_MJ_SUFFIX}",
    "Abstract dark composition, shattered glass catching golden light, deep shadows, mystery and tension, cinematic texture {SCENE_MJ_SUFFIX}",
    "Film noir corridor, long shadows stretching across floor, single figure in silhouette, atmospheric fog, warm amber accent light {SCENE_MJ_SUFFIX}",
    "Dramatic close-up of hands on a dark table, evidence scattered, spotlight from above, noir detective aesthetic {SCENE_MJ_SUFFIX}",
    "Split composition, two faces in profile facing each other, dramatic side lighting, tension and confrontation, dark cinematic {SCENE_MJ_SUFFIX}",
    "Dark theatrical stage, single spotlight on empty chair, smoke drifting, anticipation, cinematic mystery atmosphere {SCENE_MJ_SUFFIX}",
    "Aerial view of evidence laid out on dark surface, forensic photography style, dramatic shadows, gold-tinted lighting {SCENE_MJ_SUFFIX}",
    "Extreme close-up of an eye reflecting golden light, dark surroundings, suspicion and intrigue, cinematic macro {SCENE_MJ_SUFFIX}",
    "Dark room with venetian blind shadows across wall, noir atmosphere, dust particles in light beam, moody cinematic {SCENE_MJ_SUFFIX}",
    "Dramatic reveal moment, curtain pulled back, harsh spotlight on empty space, theatrical tension, dark gold palette {SCENE_MJ_SUFFIX}",
]


def generate_setting_moodboard_prompts(story_config: dict) -> list[str]:
    """Generate setting-specific moodboard prompts from a story config.
    
    These capture the period, location, and atmosphere of a specific story.
    Universal — works for any setting described in a story config.
    """
    if not story_config:
        return []
    
    loc = story_config.get("location", {})
    loc_name = loc.get("name", "")
    loc_desc = loc.get("description", "")
    
    # Extract period hints
    desc_lower = loc_desc.lower()
    period = ""
    if any(y in desc_lower for y in ["1920", "1923", "1924", "1925"]):
        period = "1920s"
    elif any(y in desc_lower for y in ["1890", "189", "victorian"]):
        period = "Victorian era, 1890s"
    elif any(y in desc_lower for y in ["1950", "195"]):
        period = "1950s"
    elif any(y in desc_lower for y in ["1940", "194"]):
        period = "1940s"
    elif any(y in desc_lower for y in ["1970", "197"]):
        period = "1970s"
    elif any(y in desc_lower for y in ["modern", "contemporary", "2020", "202"]):
        period = "modern contemporary"
    else:
        period = "period setting"
    
    # Extract location type hints
    location_type = ""
    if any(w in desc_lower for w in ["train", "railway", "locomotive", "carriage"]):
        location_type = "luxury train"
    elif any(w in desc_lower for w in ["mansion", "manor", "estate", "house"]):
        location_type = "grand mansion"
    elif any(w in desc_lower for w in ["ship", "boat", "yacht", "cruise", "ocean"]):
        location_type = "luxury ship"
    elif any(w in desc_lower for w in ["hotel", "resort", "lodge"]):
        location_type = "grand hotel"
    elif any(w in desc_lower for w in ["theater", "theatre", "opera"]):
        location_type = "ornate theater"
    elif any(w in desc_lower for w in ["castle", "fortress", "tower"]):
        location_type = "castle"
    else:
        location_type = "elegant interior"
    
    # Extract atmosphere hints
    atmosphere = ""
    if any(w in desc_lower for w in ["snow", "winter", "cold", "ice", "frost"]):
        atmosphere = "winter, snowbound, cold atmosphere"
    elif any(w in desc_lower for w in ["rain", "storm", "thunder"]):
        atmosphere = "stormy, rain-lashed, dramatic weather"
    elif any(w in desc_lower for w in ["fog", "mist", "haze"]):
        atmosphere = "foggy, misty, low visibility"
    elif any(w in desc_lower for w in ["night", "dark", "midnight"]):
        atmosphere = "nighttime, dark, atmospheric"
    elif any(w in desc_lower for w in ["summer", "sun", "heat", "warm"]):
        atmosphere = "warm summer, golden light"
    else:
        atmosphere = "atmospheric, moody"
    
    # Extract material/style hints
    materials = ""
    if any(w in desc_lower for w in ["mahogany", "brass", "wood", "oak"]):
        materials = "mahogany and brass, polished wood, warm materials"
    elif any(w in desc_lower for w in ["marble", "stone", "granite"]):
        materials = "marble and stone, grand architecture"
    elif any(w in desc_lower for w in ["chrome", "steel", "glass", "modern"]):
        materials = "chrome and glass, sleek modern materials"
    elif any(w in desc_lower for w in ["silk", "velvet", "satin", "fabric"]):
        materials = "rich fabrics, velvet and silk, opulent"
    else:
        materials = "period-appropriate materials and furnishings"
    
    style_suffix = "{SCENE_MJ_SUFFIX}"
    
    prompts = [
        # Establishing/exterior
        f"Wide establishing shot, {loc_name}, {period}, {atmosphere}, cinematic landscape, dramatic sky {style_suffix}",
        f"Exterior architecture detail, {location_type}, {period} design, {atmosphere}, atmospheric photography {style_suffix}",
        
        # Interior spaces
        f"Interior of {location_type}, {materials}, {period} decor, warm lamplight, intimate atmosphere, cinematic {style_suffix}",
        f"Dining room in {location_type}, {period}, table set for dinner, candlelight, champagne glasses, elegant {style_suffix}",
        f"Private room or study in {location_type}, {period}, {materials}, desk with papers, low lamp light, secretive atmosphere {style_suffix}",
        f"Corridor or hallway in {location_type}, {period}, dim lighting, long shadows, sense of unease, atmospheric {style_suffix}",
        
        # Period wardrobe/people
        f"Group of elegantly dressed people, {period} formal attire, {location_type} setting, social gathering, cinematic {style_suffix}",
        f"Close-up of {period} accessories on dark surface — gloves, pocket watch, cigarette case, letter opener — still life, dramatic lighting {style_suffix}",
        
        # Atmosphere/mood
        f"{loc_name}, {atmosphere}, detail shot of window with {period} curtains, mood and tension, cinematic {style_suffix}",
        f"Abstract atmospheric shot, {location_type}, {period}, shadows and light, dust particles, sense of mystery {style_suffix}",
        
        # Crime/evidence tone
        f"Dark corner of {location_type}, {period}, something hidden in shadow, forensic tension, cinematic {style_suffix}",
        f"Evidence on a {period} writing desk, scattered papers, spilled drink, dramatic overhead lighting, noir {style_suffix}",
    ]
    
    return prompts


def get_shot_stats(shots: list[dict]) -> dict:
    """Compute summary stats from a shot list."""
    total_duration = sum(s["duration"] for s in shots)
    total_chars = sum(s["chars"] for s in shots)
    
    by_type = {}
    for s in shots:
        t = s["type"]
        if t not in by_type:
            by_type[t] = {"count": 0, "duration": 0, "chars": 0}
        by_type[t]["count"] += 1
        by_type[t]["duration"] += s["duration"]
        by_type[t]["chars"] += s["chars"]
    
    by_media = {}
    for s in shots:
        m = s["media"]
        if m not in by_media:
            by_media[m] = {"count": 0, "duration": 0}
        by_media[m]["count"] += 1
        by_media[m]["duration"] += s["duration"]
    
    # Unique assets
    assets = set(s["asset"] for s in shots if s["asset"])
    
    # Unique scenes
    scenes = []
    seen = set()
    for s in shots:
        if s["scene"] not in seen:
            scenes.append(s["scene"])
            seen.add(s["scene"])
    
    return {
        "total_shots": len(shots),
        "total_duration": round(total_duration, 1),
        "total_duration_min": f"{int(total_duration//60)}:{int(total_duration%60):02d}",
        "total_chars": total_chars,
        "by_type": by_type,
        "by_media": by_media,
        "unique_assets": len(assets),
        "scenes": scenes,
        "video_shots": by_media.get("video", {}).get("count", 0),
        "static_shots": by_media.get("static", {}).get("count", 0),
        "mixed_shots": by_media.get("mixed", {}).get("count", 0),
    }
