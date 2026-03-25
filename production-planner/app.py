#!/usr/bin/env python3
"""
The Lineup — Production Planner
Pre-production tool for planning episodes before spending on AI generation.

Takes a v2 engine transcript and generates:
1. Scene-by-scene script with dialogue
2. Video generation prompts for each scene/clip
3. Asset manifest (characters, settings) with Midjourney prompts
4. TTS breakdown with character counts and voice assignments
5. Cost estimates

Usage: streamlit run app.py
"""

import json
import os
import streamlit as st
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
SEASONS_DIR = BASE_DIR / "seasons"

# Model colors (permanent brand identity)
MODEL_COLORS = {
    "Claude": "#D4A020",      # Amber/Gold
    "ChatGPT": "#32B850",     # Green
    "Gemini": "#4688E8",      # Blue
    "Mistral": "#20C4C4",     # Teal
    "DeepSeek": "#D04040",    # Red
    "Llama": "#8C40C0",       # Purple
    "Qwen": "#D4B830",        # Gold
    "Grok": "#A0A0A8",        # Silver
}

# Default Midjourney style suffix
MJ_STYLE = "cinematic, moody lighting, dark atmosphere, film noir, 1920s period, --ar 16:9 --v 6.1 --style raw"
MJ_CHAR_STYLE = "portrait, dramatic lighting, dark background, 1920s attire, detailed face, cinematic --ar 2:3 --v 6.1 --style raw"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_transcript(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def load_story_config(set_id: str) -> dict | None:
    """Try to find the story config for a given set_id."""
    for season_dir in SEASONS_DIR.iterdir():
        if season_dir.is_dir():
            for f in season_dir.glob("*.json"):
                try:
                    with open(f) as fh:
                        data = json.load(fh)
                    if data.get("set_id") == set_id:
                        return data
                except:
                    continue
    return None


def get_model_color(model_name: str) -> str:
    return MODEL_COLORS.get(model_name, "#888888")


def scene_to_video_prompt(description: str, setting: str, period: str) -> str:
    """Generate a video/image prompt from a scene description."""
    return f"{description}, {setting}, {period} era, {MJ_STYLE}"


def char_count(text: str) -> int:
    return len(text) if text else 0


# ---------------------------------------------------------------------------
# Scene Builder
# ---------------------------------------------------------------------------

def build_scenes(transcript: dict, story_config: dict | None) -> list[dict]:
    """Convert a v2 transcript into a sequential list of production scenes."""
    scenes = []
    scene_num = [0]
    
    def add_scene(name, scene_type, **kwargs):
        scene_num[0] += 1
        scenes.append({
            "number": scene_num[0],
            "name": name,
            "type": scene_type,
            **kwargs
        })
    
    # Get setting info
    setting_name = ""
    setting_period = ""
    if story_config:
        setting_name = story_config.get("location", {}).get("name", "")
        setting_period = story_config.get("location", {}).get("description", "")[:100]
    
    game = transcript.get("game", {})
    assignments = transcript.get("model_assignments", {})
    t = transcript.get("transcript", {})
    
    # --- INTRO ---
    add_scene("Intro", "intro",
              description="Pre-built title sequence",
              video_prompt=None,
              media_type="pre-built",
              dialogue=[],
              assets_needed=[])
    
    # --- ROUND 1: THE SCENE ---
    scene_text = t.get("round_1_scene", "")
    add_scene("The Scene", "narrator",
              description="Narrator sets the crime scene for the audience",
              video_prompt=f"Establishing shot: {setting_name}. Exterior in darkness, atmospheric, cinematic crane shot. {MJ_STYLE}",
              media_type="video",
              dialogue=[{"speaker": "Narrator", "type": "narrate", "text": scene_text}],
              assets_needed=["setting_exterior", "crime_scene", "victim_portrait"],
              notes="Split into multiple clips: exterior → interior → crime scene → evidence")
    
    # --- ROUND 2: OPENING STATEMENTS ---
    for entry in t.get("round_2_statements", []):
        char = entry["character"]
        model = entry.get("model_name", "")
        think = entry.get("think", "")
        speak = entry.get("speak", "")
        accused = entry.get("suspects_accused", [])
        
        add_scene(f"Statement: {char}", "statement",
                  description=f"{char} ({model}) gives their opening statement",
                  video_prompt=f"Close-up portrait of {char} speaking in a dimly lit room, tense atmosphere, {MJ_STYLE}",
                  media_type="mixed",  # character portrait (static) + think overlay
                  dialogue=[
                      {"speaker": model, "type": "think", "text": think, "voice": "model"},
                      {"speaker": char, "type": "speak", "text": speak, "voice": "character"},
                  ],
                  assets_needed=[f"char_{char.lower().replace(' ', '_')}"],
                  accused=accused)
    
    # --- ROUND 3: SUSPICION ROUND ---
    for i, conf in enumerate(t.get("round_3_suspicion", [])):
        target = conf["target"]
        challenger = conf["challenger"]
        
        # Get model names
        target_model = ""
        challenger_model = ""
        for s in assignments.get("suspects", []):
            if s["character"] == target:
                target_model = s.get("model_name", "")
            if s["character"] == challenger:
                challenger_model = s.get("model_name", "")
        
        add_scene(f"Confrontation {i+1}: {target} vs {challenger}", "confrontation",
                  description=f"{challenger} challenges {target}. Back-and-forth exchange.",
                  video_prompt=f"Two people facing each other in tense confrontation, dramatic lighting, split composition, dark room, {MJ_STYLE}",
                  media_type="mixed",
                  dialogue=[
                      {"speaker": f"Narrator", "type": "narrate", "text": conf.get("confrontation_prompt", "")},
                      {"speaker": target_model, "type": "think", "text": conf.get("target_think", ""), "voice": "model"},
                      {"speaker": target, "type": "speak", "text": conf.get("target_speak", ""), "voice": "character"},
                      {"speaker": challenger_model, "type": "think", "text": conf.get("challenger_think", ""), "voice": "model"},
                      {"speaker": challenger, "type": "speak", "text": conf.get("challenger_speak", ""), "voice": "character"},
                  ],
                  assets_needed=[
                      f"char_{target.lower().replace(' ', '_')}",
                      f"char_{challenger.lower().replace(' ', '_')}",
                  ])
    
    # --- DETECTIVE PROCESSING ---
    dp = t.get("detective_processing", {})
    if dp:
        det_model = dp.get("model_name", "Detective")
        add_scene("Detective Processing", "transition",
                  description="Detective's internal analysis before investigation",
                  video_prompt=f"Silhouette of a detective thinking, smoke and shadow, abstract deduction imagery, {MJ_STYLE}",
                  media_type="video",
                  dialogue=[
                      {"speaker": det_model, "type": "think", "text": dp.get("think", ""), "voice": "model"},
                  ],
                  assets_needed=["setting_lounge"])
    
    # --- ROUND 4: INVESTIGATION ---
    inv = t.get("round_4_investigation", {})
    
    # Evidence drop
    evidence = inv.get("evidence_revealed", "")
    if evidence:
        add_scene("Evidence Revealed", "evidence",
                  description="New evidence is presented to all participants",
                  video_prompt=f"Close-up of evidence on a dark surface, dramatic spotlight, forensic detail, {MJ_STYLE}",
                  media_type="video",
                  dialogue=[
                      {"speaker": "Narrator", "type": "narrate", "text": f"New evidence: {evidence}"},
                  ],
                  assets_needed=["evidence_closeup"])
    
    for ex in inv.get("exchanges", []):
        suspect = ex.get("suspect_character", "")
        suspect_model = ex.get("suspect_model_name", "")
        det_model = assignments.get("detective", {}).get("model_name", "Detective")
        
        add_scene(f"Investigation Q{ex['question_number']}: {suspect}", "investigation",
                  description=f"Detective questions {suspect}",
                  video_prompt=f"Interrogation scene, detective questioning suspect across a table, tense, {MJ_STYLE}",
                  media_type="mixed",
                  dialogue=[
                      {"speaker": det_model, "type": "think", "text": ex.get("detective_think", ""), "voice": "model"},
                      {"speaker": "Detective", "type": "speak", "text": ex.get("detective_speak", ""), "voice": "character"},
                      {"speaker": suspect_model, "type": "think", "text": ex.get("suspect_think", ""), "voice": "model"},
                      {"speaker": suspect, "type": "speak", "text": ex.get("suspect_speak", ""), "voice": "character"},
                  ],
                  assets_needed=[
                      f"char_{suspect.lower().replace(' ', '_')}",
                      "setting_lounge"
                  ])
    
    # --- ROUND 5: FINAL STATEMENTS ---
    for entry in t.get("round_5_final_statements", []):
        char = entry["character"]
        model = entry.get("model_name", "")
        
        add_scene(f"Final Statement: {char}", "final_statement",
                  description=f"{char} ({model}) makes their final statement",
                  video_prompt=f"Close-up of {char}, intense expression, final words, dramatic lighting, {MJ_STYLE}",
                  media_type="mixed",
                  dialogue=[
                      {"speaker": model, "type": "think", "text": entry.get("think", ""), "voice": "model"},
                      {"speaker": char, "type": "speak", "text": entry.get("speak", ""), "voice": "character"},
                  ],
                  assets_needed=[f"char_{char.lower().replace(' ', '_')}"])
    
    # --- ACCUSATION ---
    acc = t.get("round_5_accusation", {})
    if acc:
        det_model = assignments.get("detective", {}).get("model_name", "Detective")
        add_scene("The Accusation", "accusation",
                  description=f"Detective accuses {acc.get('accused', 'unknown')}",
                  video_prompt=f"Dramatic pointing gesture in a dark room, spotlight on the accused, theatrical, {MJ_STYLE}",
                  media_type="video",
                  dialogue=[
                      {"speaker": det_model, "type": "think", "text": acc.get("detective_think", ""), "voice": "model"},
                      {"speaker": "Detective", "type": "speak", "text": acc.get("detective_speak", ""), "voice": "character"},
                  ],
                  assets_needed=["title_card_accusation"],
                  notes=f"Accused: {acc.get('accused', '?')}")
    
    # --- ACCUSED RESPONSE ---
    ar = t.get("round_5_accused_response")
    if ar:
        char = ar["character"]
        # Find model name
        model = ""
        for s in assignments.get("suspects", []):
            if s["character"] == char:
                model = s.get("model_name", "")
        
        add_scene(f"Accused Response: {char}", "accused_response",
                  description=f"{char} responds to being accused",
                  video_prompt=f"Close-up reaction shot, {char} responding to accusation, emotional, dramatic lighting, {MJ_STYLE}",
                  media_type="mixed",
                  dialogue=[
                      {"speaker": model, "type": "think", "text": ar.get("think", ""), "voice": "model"},
                      {"speaker": char, "type": "speak", "text": ar.get("speak", ""), "voice": "character"},
                  ],
                  assets_needed=[f"char_{char.lower().replace(' ', '_')}"])
    
    # --- REACTIONS ---
    for entry in t.get("round_5_reactions", []):
        char = entry["character"]
        model = entry.get("model_name", "")
        
        add_scene(f"Reaction: {char}", "reaction",
                  description=f"{char} ({model}) reacts to the accusation",
                  video_prompt=f"Reaction shot of {char}, {MJ_STYLE}",
                  media_type="static",
                  dialogue=[
                      {"speaker": model, "type": "think", "text": entry.get("think", ""), "voice": "model"},
                      {"speaker": char, "type": "speak", "text": entry.get("speak", ""), "voice": "character"},
                  ],
                  assets_needed=[f"char_{char.lower().replace(' ', '_')}"])
    
    # --- REVEAL ---
    add_scene("The Reveal", "reveal",
              description="The truth is revealed and scores are shown",
              video_prompt=f"Dramatic reveal moment, spotlight shifting, truth unveiled, {MJ_STYLE}",
              media_type="video",
              dialogue=[{"speaker": "Narrator", "type": "narrate", "text": "The truth is revealed..."}],
              assets_needed=["title_card_reveal", "scoring_card", "standings_card"])
    
    # --- OUTRO ---
    add_scene("Outro", "outro",
              description="Season standings and next episode tease",
              video_prompt=None,
              media_type="static",
              dialogue=[{"speaker": "Narrator", "type": "narrate", "text": "Season standings..."}],
              assets_needed=["standings_card", "end_card"])
    
    return scenes


def build_asset_manifest(scenes: list[dict], story_config: dict | None) -> dict:
    """Build a deduplicated asset manifest with Midjourney prompts."""
    assets = {}
    
    # Collect all needed assets
    for scene in scenes:
        for asset_id in scene.get("assets_needed", []):
            if asset_id not in assets:
                assets[asset_id] = {
                    "id": asset_id,
                    "type": "unknown",
                    "description": "",
                    "midjourney_prompt": "",
                    "used_in_scenes": [],
                    "status": "needed",
                }
            assets[asset_id]["used_in_scenes"].append(scene["number"])
    
    # Enrich with story config data
    if story_config:
        loc = story_config.get("location", {})
        loc_name = loc.get("name", "")
        loc_desc = loc.get("description", "")
        
        for asset_id, asset in assets.items():
            if asset_id.startswith("char_"):
                # Character asset
                char_name_key = asset_id.replace("char_", "").replace("_", " ").title()
                asset["type"] = "character"
                
                # Find character in config
                for s in story_config.get("suspects", []):
                    if s["name"].lower().replace(" ", "_") in asset_id.replace("char_", ""):
                        asset["description"] = f'{s["name"]}: {s["role"]}'
                        bg = s.get("background", "")[:150]
                        asset["midjourney_prompt"] = (
                            f'{s["name"]}, {s["role"]}, {bg}... '
                            f'{MJ_CHAR_STYLE}'
                        )
                        break
                
                if not asset["description"]:
                    asset["description"] = char_name_key
                    asset["midjourney_prompt"] = f"{char_name_key}, {MJ_CHAR_STYLE}"
            
            elif asset_id.startswith("setting_"):
                asset["type"] = "setting"
                setting_type = asset_id.replace("setting_", "")
                asset["description"] = f"Setting: {setting_type} at {loc_name}"
                asset["midjourney_prompt"] = f"{loc_name}, {setting_type} area, {loc_desc[:100]}, {MJ_STYLE}"
            
            elif asset_id.startswith("title_card_"):
                asset["type"] = "title_card"
                card_type = asset_id.replace("title_card_", "").upper()
                asset["description"] = f"Title card: {card_type}"
                asset["midjourney_prompt"] = ""  # Generated programmatically
                asset["status"] = "auto-generated"
            
            elif asset_id == "victim_portrait":
                asset["type"] = "character"
                victim = story_config.get("victim", {})
                asset["description"] = f'Victim: {victim.get("name", "?")}'
                asset["midjourney_prompt"] = (
                    f'{victim.get("name", "victim")}, {victim.get("description", "")[:150]}, '
                    f'deceased, dramatic portrait, {MJ_CHAR_STYLE}'
                )
            
            elif asset_id == "crime_scene":
                asset["type"] = "setting"
                crime = story_config.get("crime", {})
                asset["description"] = "Crime scene"
                asset["midjourney_prompt"] = (
                    f'Crime scene, {loc_name}, '
                    f'{story_config.get("victim", {}).get("cause_of_death", "murder")}, '
                    f'forensic detail, dark atmospheric, {MJ_STYLE}'
                )
            
            elif asset_id == "evidence_closeup":
                asset["type"] = "prop"
                asset["description"] = "Evidence close-up shot"
                asset["midjourney_prompt"] = f"Evidence on dark surface, dramatic spotlight, forensic photography style, {MJ_STYLE}"
            
            elif asset_id in ("scoring_card", "standings_card", "end_card"):
                asset["type"] = "title_card"
                asset["description"] = f"Auto-generated: {asset_id}"
                asset["status"] = "auto-generated"
    
    return assets


def compute_tts_breakdown(scenes: list[dict]) -> dict:
    """Compute TTS character counts by voice type."""
    breakdown = {
        "narrator": {"chars": 0, "clips": 0},
        "model_voices": {},
        "character_voices": {},
        "total_chars": 0,
        "total_clips": 0,
    }
    
    for scene in scenes:
        for d in scene.get("dialogue", []):
            chars = char_count(d.get("text", ""))
            if chars == 0:
                continue
            
            breakdown["total_chars"] += chars
            breakdown["total_clips"] += 1
            
            if d["type"] == "narrate":
                breakdown["narrator"]["chars"] += chars
                breakdown["narrator"]["clips"] += 1
            elif d["type"] == "think":
                voice = d["speaker"]  # model name
                if voice not in breakdown["model_voices"]:
                    breakdown["model_voices"][voice] = {"chars": 0, "clips": 0}
                breakdown["model_voices"][voice]["chars"] += chars
                breakdown["model_voices"][voice]["clips"] += 1
            elif d["type"] == "speak":
                voice = d["speaker"]  # character name
                if voice not in breakdown["character_voices"]:
                    breakdown["character_voices"][voice] = {"chars": 0, "clips": 0}
                breakdown["character_voices"][voice]["chars"] += chars
                breakdown["character_voices"][voice]["clips"] += 1
    
    return breakdown


# ---------------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="The Lineup — Production Planner",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme CSS
st.markdown("""
<style>
.stApp { background-color: #0a0a0f; }
.scene-card {
    background: #13131a;
    border: 1px solid #2a2520;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.scene-header {
    font-family: Georgia, serif;
    font-size: 1.1rem;
    color: #FFD700;
    margin-bottom: 8px;
}
.dialogue-think {
    background: rgba(255, 215, 0, 0.08);
    border-left: 3px solid #FFD700;
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 4px;
    font-size: 0.85rem;
}
.dialogue-speak {
    background: rgba(255, 255, 255, 0.04);
    border-left: 3px solid #888;
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 4px;
    font-size: 0.85rem;
}
.dialogue-narrate {
    background: rgba(150, 150, 160, 0.08);
    border-left: 3px solid #95A5A6;
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 4px;
    font-style: italic;
    font-size: 0.85rem;
}
.video-prompt {
    background: rgba(70, 136, 232, 0.1);
    border: 1px solid rgba(70, 136, 232, 0.3);
    border-radius: 4px;
    padding: 8px 12px;
    font-family: monospace;
    font-size: 0.8rem;
    margin-top: 8px;
}
.asset-card {
    background: #13131a;
    border: 1px solid #2a2520;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.mj-prompt {
    background: rgba(140, 64, 192, 0.1);
    border: 1px solid rgba(140, 64, 192, 0.3);
    border-radius: 4px;
    padding: 8px 12px;
    font-family: monospace;
    font-size: 0.8rem;
    margin-top: 6px;
}
.metric-box {
    background: #13131a;
    border: 1px solid #2a2520;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: bold;
    color: #FFD700;
}
.metric-label {
    font-size: 0.75rem;
    color: #8a8278;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🎬 Production Planner")

# Find v2 transcripts
transcript_files = sorted(TRANSCRIPTS_DIR.glob("*_v2_*.json"), reverse=True) if TRANSCRIPTS_DIR.exists() else []

if not transcript_files:
    st.sidebar.warning("No v2 transcripts found")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Select Transcript",
    transcript_files,
    format_func=lambda x: x.stem,
)

transcript = load_transcript(selected_file)
game = transcript.get("game", {})
story_config = load_story_config(game.get("set_id", ""))

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Episode:** {game.get('title', '?')}")
st.sidebar.markdown(f"**Set:** {game.get('set_id', '?')}")
st.sidebar.markdown(f"**Season:** {game.get('season', '?')} / Ep {game.get('episode', '?')}")

# Build scenes
scenes = build_scenes(transcript, story_config)
assets = build_asset_manifest(scenes, story_config)
tts = compute_tts_breakdown(scenes)

# Sidebar navigation
st.sidebar.markdown("---")
view = st.sidebar.radio("View", ["📋 Script & Scenes", "🎨 Asset Manifest", "🎙️ TTS Breakdown", "💰 Cost Estimate", "📤 Export All"])

# --- MAIN CONTENT ---

if view == "📋 Script & Scenes":
    st.title(f"📋 {game.get('title', 'Episode')} — Scene Breakdown")
    st.caption(f"{len(scenes)} scenes | {tts['total_clips']} dialogue clips | {tts['total_chars']:,} TTS characters")
    
    # Scene filter
    scene_types = sorted(set(s["type"] for s in scenes))
    filter_type = st.multiselect("Filter by scene type", scene_types, default=scene_types)
    
    for scene in scenes:
        if scene["type"] not in filter_type:
            continue
        
        with st.expander(f"**Scene {scene['number']}:** {scene['name']}  ({scene['type']})", expanded=False):
            st.markdown(f"*{scene.get('description', '')}*")
            
            if scene.get("notes"):
                st.info(f"📝 {scene['notes']}")
            
            # Media type badge
            media = scene.get("media_type", "")
            if media == "video":
                st.markdown("🎥 **AI Video**")
            elif media == "static":
                st.markdown("🖼️ **Static Image**")
            elif media == "mixed":
                st.markdown("🎥🖼️ **Mixed (video + static)**")
            
            # Video generation prompt
            vp = scene.get("video_prompt")
            if vp:
                st.markdown("**Video/Image Generation Prompt:**")
                st.markdown(f'<div class="video-prompt">{vp}</div>', unsafe_allow_html=True)
            
            # Dialogue
            st.markdown("**Dialogue:**")
            for d in scene.get("dialogue", []):
                text = d.get("text", "")
                if not text:
                    continue
                speaker = d["speaker"]
                dtype = d["type"]
                chars = len(text)
                
                if dtype == "think":
                    color = get_model_color(speaker)
                    st.markdown(
                        f'<div class="dialogue-think" style="border-left-color: {color}">'
                        f'<strong>🧠 {speaker} (THINK):</strong> [{chars} chars]<br>{text}</div>',
                        unsafe_allow_html=True
                    )
                elif dtype == "speak":
                    st.markdown(
                        f'<div class="dialogue-speak">'
                        f'<strong>🗣️ {speaker} (SPEAK):</strong> [{chars} chars]<br>{text}</div>',
                        unsafe_allow_html=True
                    )
                elif dtype == "narrate":
                    st.markdown(
                        f'<div class="dialogue-narrate">'
                        f'<strong>📖 Narrator:</strong> [{chars} chars]<br>{text}</div>',
                        unsafe_allow_html=True
                    )
            
            # Assets needed
            needed = scene.get("assets_needed", [])
            if needed:
                st.markdown(f"**Assets needed:** {', '.join(needed)}")


elif view == "🎨 Asset Manifest":
    st.title("🎨 Asset Manifest")
    st.caption(f"{len(assets)} unique assets needed")
    
    # Group by type
    by_type = {}
    for asset in assets.values():
        t = asset["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(asset)
    
    for asset_type, items in sorted(by_type.items()):
        st.subheader(f"{asset_type.title()} ({len(items)})")
        
        for asset in items:
            with st.expander(f"{asset['id']} — {asset['description']}"):
                st.markdown(f"**Status:** {asset['status']}")
                st.markdown(f"**Used in scenes:** {', '.join(str(s) for s in asset['used_in_scenes'])}")
                
                if asset["midjourney_prompt"]:
                    st.markdown("**Midjourney Prompt:**")
                    st.code(asset["midjourney_prompt"], language=None)
                    if st.button(f"📋 Copy", key=f"copy_{asset['id']}"):
                        st.toast("Prompt copied!")
    
    # Export all prompts
    st.markdown("---")
    st.subheader("📋 All Midjourney Prompts")
    all_prompts = []
    for asset in assets.values():
        if asset["midjourney_prompt"]:
            all_prompts.append(f"// {asset['id']}: {asset['description']}\n{asset['midjourney_prompt']}\n")
    
    st.text_area("Copy all prompts:", "\n".join(all_prompts), height=300)


elif view == "🎙️ TTS Breakdown":
    st.title("🎙️ TTS Breakdown")
    
    cols = st.columns(3)
    with cols[0]:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{tts["total_chars"]:,}</div><div class="metric-label">Total Characters</div></div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'<div class="metric-box"><div class="metric-value">{tts["total_clips"]}</div><div class="metric-label">Audio Clips</div></div>', unsafe_allow_html=True)
    with cols[2]:
        est_cost = tts["total_chars"] / 1000 * 0.30  # rough ElevenLabs estimate
        st.markdown(f'<div class="metric-box"><div class="metric-value">${est_cost:.2f}</div><div class="metric-label">Est. TTS Cost</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Narrator
    st.subheader("📖 Narrator")
    st.markdown(f"**{tts['narrator']['chars']:,}** characters / **{tts['narrator']['clips']}** clips")
    
    # Model voices (THINK)
    st.subheader("🧠 Model Voices (THINK sections)")
    for model, data in sorted(tts["model_voices"].items(), key=lambda x: x[1]["chars"], reverse=True):
        color = get_model_color(model)
        st.markdown(f"<span style='color:{color}'>●</span> **{model}**: {data['chars']:,} chars / {data['clips']} clips", unsafe_allow_html=True)
    
    # Character voices (SPEAK)
    st.subheader("🗣️ Character Voices (SPEAK sections)")
    for char, data in sorted(tts["character_voices"].items(), key=lambda x: x[1]["chars"], reverse=True):
        st.markdown(f"**{char}**: {data['chars']:,} chars / {data['clips']} clips")


elif view == "💰 Cost Estimate":
    st.title("💰 Cost Estimate")
    
    tts_cost = tts["total_chars"] / 1000 * 0.30
    
    video_scenes = sum(1 for s in scenes if s.get("media_type") in ("video", "mixed"))
    video_cost_low = video_scenes * 0.10   # cheap tier
    video_cost_high = video_scenes * 0.50  # premium tier
    
    mj_assets = sum(1 for a in assets.values() if a["midjourney_prompt"])
    mj_cost = mj_assets * 0.02  # ~$0.02 per generation on standard plan
    
    st.markdown("### TTS (ElevenLabs)")
    st.markdown(f"- {tts['total_chars']:,} characters")
    st.markdown(f"- ~${tts_cost:.2f}")
    
    st.markdown("### AI Video Generation")
    st.markdown(f"- {video_scenes} scenes marked for video")
    st.markdown(f"- ~${video_cost_low:.2f} - ${video_cost_high:.2f} (depends on service)")
    
    st.markdown("### Midjourney Assets")
    st.markdown(f"- {mj_assets} assets to generate")
    st.markdown(f"- ~${mj_cost:.2f}")
    
    st.markdown("---")
    total_low = tts_cost + video_cost_low + mj_cost
    total_high = tts_cost + video_cost_high + mj_cost
    st.markdown(f"### Total: ${total_low:.2f} - ${total_high:.2f} per episode")


elif view == "📤 Export All":
    st.title("📤 Export")
    
    # Export scenes as JSON
    export_data = {
        "game": game,
        "scenes": scenes,
        "assets": assets,
        "tts_breakdown": tts,
    }
    
    st.download_button(
        "⬇️ Download Production Plan (JSON)",
        json.dumps(export_data, indent=2),
        file_name=f"{game.get('set_id', 'episode')}_production_plan.json",
        mime="application/json",
    )
    
    # Export Midjourney prompts as text
    mj_lines = []
    for asset in assets.values():
        if asset["midjourney_prompt"]:
            mj_lines.append(f"// {asset['id']}: {asset['description']}")
            mj_lines.append(asset["midjourney_prompt"])
            mj_lines.append("")
    
    st.download_button(
        "⬇️ Download Midjourney Prompts",
        "\n".join(mj_lines),
        file_name=f"{game.get('set_id', 'episode')}_midjourney_prompts.txt",
        mime="text/plain",
    )
    
    # Export video prompts
    vid_lines = []
    for scene in scenes:
        vp = scene.get("video_prompt")
        if vp:
            vid_lines.append(f"// Scene {scene['number']}: {scene['name']}")
            vid_lines.append(vp)
            vid_lines.append("")
    
    st.download_button(
        "⬇️ Download Video Generation Prompts",
        "\n".join(vid_lines),
        file_name=f"{game.get('set_id', 'episode')}_video_prompts.txt",
        mime="text/plain",
    )
