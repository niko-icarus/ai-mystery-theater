#!/usr/bin/env python3
"""
The Lineup — Season Asset Library Builder
Generates a comprehensive reusable asset catalog for a full season.

Unlike the per-episode planner, this is SEASON-level: every still image
and video clip needed across all 8 episodes, organized for maximum reuse.

Assets are model-neutral (no model branding in visuals — identity is
applied via post-production overlays: colored lower thirds, corner badges,
caption colors).

Usage: python build_asset_library.py seasons/season_01/tomb_of_amenhotep.json [output.html]
"""

import json
import sys
import html as html_lib
from pathlib import Path

# ---------------------------------------------------------------------------
# Style constants (match The Lineup brand)
# ---------------------------------------------------------------------------

# Period gets extracted from story config
PERIOD = ""
SETTING = ""

# Art direction: Tim Burton Papercraft
# This is the locked visual style for The Lineup.
# Every production prompt should include this style DNA.
STYLE_DNA = "layered cut paper, angular construction, visible paper edges and depth, Tim Burton papercraft aesthetic, gothic mood"

# Midjourney suffixes — aspect ratio, version, quality, style controlled by user
MJ_SCENE = ""
MJ_CHAR = ""
MJ_PROP = ""
MJ_SQUARE = ""

# Video gen placeholder suffix (tool TBD)
VID_SUFFIX = ""

# Brand moodboard prompts (permanent — defines The Lineup's visual identity)
BRAND_MOODBOARD_PROMPTS = [
    f"Dark theatrical stage set built entirely from layered cut paper, angular construction, visible paper edges and depth, Tim Burton gothic aesthetic, dramatic spotlight, deep shadows, warm amber accent light {MJ_SCENE}",
    f"Paper craft portrait silhouette, layered cut paper with visible texture and edges, angular Tim Burton style face in profile, dramatic rim lighting, dark background, gothic mood {MJ_CHAR}",
    f"Interrogation scene constructed from layered papercraft, two angular paper figures facing each other across a table, single overhead paper lantern, deep paper shadows, Tim Burton stop-motion aesthetic {MJ_SCENE}",
    f"Close-up of paper craft hands on a dark textured surface, evidence made of tiny paper props, visible paper grain and cut edges, spotlight from above, gothic noir aesthetic {MJ_SCENE}",
    f"Long corridor built from layered cut paper walls, angular perspective, paper torch brackets casting geometric shadows, Tim Burton gothic atmosphere, visible paper depth and construction {MJ_SCENE}",
    f"Split composition, two paper craft faces in profile facing each other, layered cut paper construction, dramatic side lighting revealing paper edges, confrontation tension, dark gothic {MJ_SCENE}",
    f"Dark paper craft diorama, single spotlight on empty angular chair, paper smoke wisps, layered background with visible depth, Tim Burton theatrical mystery aesthetic {MJ_SCENE}",
    f"Evidence laid out on dark paper surface, miniature paper props — knife, letter, torn fabric — dramatic overhead lighting casting paper shadows, forensic diorama aesthetic {MJ_SCENE}",
    f"Paper craft eye extreme close-up, layered cut paper iris reflecting golden light, visible paper texture and edges, dark surround, Tim Burton gothic detail {MJ_SQUARE}",
    f"Dramatic reveal moment in papercraft, angular paper curtain pulled aside, harsh spotlight on empty paper stage, layered depth visible, Tim Burton theatrical tension {MJ_SCENE}",
]

# Setting moodboard prompts (per-season — Egyptian tomb in papercraft)
SETTING_MOODBOARD_PROMPTS = [
    f"Ancient Egyptian tomb entrance built from layered cut paper, Valley of the Kings, paper sandstorm swirling, angular Tim Burton construction, gothic atmosphere, dramatic sky made of torn paper layers {MJ_SCENE}",
    f"Paper craft burial chamber diorama, golden paper sarcophagus center, layered paper hieroglyphs on walls, paper torches with orange tissue flame, angular Tim Burton gothic architecture, visible paper edges {MJ_SCENE}",
    f"Stone corridor built from layered grey-brown cut paper, angular perspective receding into darkness, paper torch brackets, geometric shadows on paper walls, Tim Burton stop-motion aesthetic {MJ_SCENE}",
    f"Group of Victorian-era paper craft figures in angular Tim Burton style, 1890s expedition clothing, standing in a paper tomb chamber, dramatic paper torchlight, layered cut paper construction throughout {MJ_SCENE}",
    f"Paper craft close-up of 1890s archaeological tools on dark surface, miniature paper knives and chisels, visible paper grain and cut edges, dramatic spotlight, forensic diorama {MJ_SCENE}",
    f"Paper craft expedition camp in desert, angular Tim Burton tents made of layered paper, paper sand dunes, dramatic paper sky, Victorian era, gothic mood with warm amber lantern light {MJ_SCENE}",
]

# Model identity (for overlay reference only — not baked into assets)
MODELS = [
    {"name": "Claude", "color": "#D4A020", "symbol": "☀️"},
    {"name": "ChatGPT", "color": "#32B850", "symbol": "⬡"},
    {"name": "Gemini", "color": "#4688E8", "symbol": "◇"},
    {"name": "Mistral", "color": "#20C4C4", "symbol": "🌀"},
    {"name": "DeepSeek", "color": "#D04040", "symbol": "🔺"},
    {"name": "Llama", "color": "#8C40C0", "symbol": "🦙"},
    {"name": "Qwen", "color": "#D4B830", "symbol": "✦"},
    {"name": "Grok", "color": "#A0A0A8", "symbol": "✕"},
]

# Character emotions/states for reaction variants
CHARACTER_STATES = [
    {"state": "speaking", "desc": "speaking calmly, mid-conversation, neutral expression"},
    {"state": "defensive", "desc": "defensive posture, arms slightly raised, guarded expression, tension in jaw"},
    {"state": "nervous", "desc": "visibly anxious, fidgeting, avoiding eye contact, beads of sweat"},
    {"state": "accusatory", "desc": "pointing or gesturing emphatically, accusatory stance, intense eyes"},
    {"state": "contemplative", "desc": "deep in thought, hand near chin, introspective, calculating gaze"},
    {"state": "confident", "desc": "composed and confident, slight smirk, relaxed shoulders, in control"},
    {"state": "shocked", "desc": "wide eyes, mouth slightly open, genuine surprise, caught off guard"},
    {"state": "angry", "desc": "visible fury, clenched fists, narrowed eyes, barely contained rage"},
]


def styled_prompt(base: str, suffix: str = "") -> str:
    """Prepend the Tim Burton papercraft style DNA to every prompt."""
    parts = [STYLE_DNA, base.rstrip(", ")]
    if suffix:
        parts.append(suffix)
    return ", ".join(p for p in parts if p)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def e(text):
    return html_lib.escape(str(text)) if text else ""


def extract_period(description: str) -> str:
    d = description.lower()
    if any(y in d for y in ["1890", "1891", "1892", "1893", "1894", "1895"]):
        return "1890s Victorian colonial era"
    if any(y in d for y in ["1920", "1923"]):
        return "1920s era"
    if "victorian" in d:
        return "Victorian era"
    return "period setting"


def extract_atmosphere(description: str) -> str:
    d = description.lower()
    if any(w in d for w in ["sand", "desert", "egyptian", "tomb"]):
        return "torchlit underground, dusty stone, ancient Egyptian"
    if any(w in d for w in ["snow", "winter", "cold"]):
        return "snowbound, cold, frosted"
    if any(w in d for w in ["rain", "storm"]):
        return "storm-lashed, dramatic weather"
    return "atmospheric, moody"


# ---------------------------------------------------------------------------
# Asset catalog builder
# ---------------------------------------------------------------------------

def build_asset_catalog(story_config: dict) -> dict:
    """Build the full season asset catalog from a story config."""
    
    loc = story_config.get("location", {})
    loc_name = loc.get("name", "")
    loc_desc = loc.get("description", "")
    rooms = loc.get("rooms", [])
    period = extract_period(loc_desc)
    atmosphere = extract_atmosphere(loc_desc)
    victim = story_config.get("victim", {})
    crime = story_config.get("crime", {})
    evidence = story_config.get("evidence", {})
    suspects = story_config.get("suspects", [])
    
    # Detective character (from story, not model-specific)
    # The detective character is always "Inspector William Cross" for this story
    # but we pull from story_draft context
    detective_name = "Inspector William Cross"
    detective_desc = "Scotland Yard detective, 48, methodical, sharp-eyed, skeptical, period suit"
    
    catalog = {
        "story": loc_name,
        "period": period,
        "atmosphere": atmosphere,
        "categories": []
    }
    
    # =====================================================================
    # CATEGORY 1: CHARACTER PORTRAITS (Still Images)
    # =====================================================================
    char_stills = {
        "id": "characters_stills",
        "name": "Character Portraits — Still Images",
        "description": f"Each character in multiple emotional states. Model-neutral — no AI model branding in the images. Identity overlay (colored lower third, corner badge) applied in post-production. Midjourney generates 4 variations per prompt — keep ALL variations for visual variety across episodes.",
        "note": f"💡 With 4 MJ variations × {len(CHARACTER_STATES)} states × {len(suspects) + 2} characters = {4 * len(CHARACTER_STATES) * (len(suspects) + 2)} total still images from {len(CHARACTER_STATES) * (len(suspects) + 2)} prompts.",
        "assets": []
    }
    
    # Suspects
    for s in suspects:
        for cs in CHARACTER_STATES:
            char_stills["assets"].append({
                "id": f"char_{s['name'].lower().replace(' ', '_')}_{cs['state']}",
                "name": f"{s['name']} — {cs['state'].title()}",
                "type": "still",
                "reuse": "All 8 episodes",
                "variants": "Keep all 4 MJ variations",
                "prompt": styled_prompt(
                    f"{s['name']}, {s['role']}, {s['background'][:100]}, "
                    f"{cs['desc']}, "
                    f"dramatic portrait lighting, {atmosphere}, {period}",
                    MJ_CHAR
                ),
            })
    
    # Detective
    for cs in CHARACTER_STATES:
        char_stills["assets"].append({
            "id": f"char_detective_{cs['state']}",
            "name": f"{detective_name} — {cs['state'].title()}",
            "type": "still",
            "reuse": "All 8 episodes",
            "variants": "Keep all 4 MJ variations",
            "prompt": styled_prompt(
                f"{detective_name}, {detective_desc}, "
                f"{cs['desc']}, "
                f"dramatic portrait lighting, {atmosphere}, {period}",
                MJ_CHAR
            ),
        })
    
    # Victim
    char_stills["assets"].append({
        "id": "char_victim_alive",
        "name": f"{victim['name']} — Alive (flashback/intro)",
        "type": "still",
        "reuse": "All 8 episodes (intro/scene-setting)",
        "variants": "Keep all 4 MJ variations",
        "prompt": styled_prompt(
            f"{victim['name']}, {victim['description'][:120]}, "
            f"alive, rough demeanor, suspicious look, "
            f"dramatic portrait, {atmosphere}, {period}",
            MJ_CHAR
        ),
    })
    char_stills["assets"].append({
        "id": "char_victim_dead",
        "name": f"{victim['name']} — Crime Scene (deceased)",
        "type": "still",
        "reuse": "All 8 episodes (crime scene reveal)",
        "variants": "Keep best 1-2",
        "prompt": styled_prompt(
            f"Crime scene, {victim['name']} {victim['cause_of_death'][:80]}, "
            f"dramatic overhead angle, {atmosphere}, {period}, "
            f"dark forensic photography",
            MJ_SCENE
        ),
    })
    
    catalog["categories"].append(char_stills)
    
    # =====================================================================
    # CATEGORY 2: CHARACTER CLIPS (Video)
    # =====================================================================
    char_videos = {
        "id": "characters_video",
        "name": "Character Clips — Video",
        "description": "Short video clips of characters in action. Used when static portraits feel too repetitive. Model-neutral. Same reuse logic: one library for all 8 episodes.",
        "note": "🎥 Video gen tool TBD (Runway / Kling / etc.). Generate after stills are finalized. These supplement the stills — not every shot needs video.",
        "assets": []
    }
    
    # Key character video clips
    char_video_actions = [
        {"action": "speaking_medium", "desc": "speaking in medium shot, subtle gestures, conversation"},
        {"action": "listening_closeup", "desc": "listening intently, close-up, slight reactions, watchful eyes"},
        {"action": "turning_away", "desc": "turning away, walking into shadow, evasive body language"},
        {"action": "confrontation_two_shot", "desc": "two-shot confrontation, facing another person, tense exchange"},
    ]
    
    for s in suspects:
        for action in char_video_actions:
            char_videos["assets"].append({
                "id": f"vid_{s['name'].lower().replace(' ', '_')}_{action['action']}",
                "name": f"{s['name']} — {action['action'].replace('_', ' ').title()}",
                "type": "video",
                "reuse": "All 8 episodes",
                "variants": "Generate 2-3 takes, keep all",
                "prompt": styled_prompt(
                    f"{s['name']}, {s['role']}, {action['desc']}, "
                    f"inside {loc_name}, {atmosphere}, {period}, "
                    f"cinematic camera, dramatic lighting, slow movement",
                    VID_SUFFIX
                ),
            })
    
    # Detective video clips
    det_video_actions = [
        {"action": "examining_evidence", "desc": "examining evidence closely, turning object in hands, analytical"},
        {"action": "pacing_thinking", "desc": "pacing slowly, deep in thought, silhouette against torchlight"},
        {"action": "interrogating", "desc": "leaning forward across table, questioning suspect, intense eye contact"},
        {"action": "dramatic_accusation", "desc": "pointing accusingly, dramatic gesture, spotlight moment"},
    ]
    
    for action in det_video_actions:
        char_videos["assets"].append({
            "id": f"vid_detective_{action['action']}",
            "name": f"{detective_name} — {action['action'].replace('_', ' ').title()}",
            "type": "video",
            "reuse": "All 8 episodes",
            "variants": "Generate 2-3 takes, keep all",
            "prompt": styled_prompt(
                f"{detective_name}, {detective_desc}, {action['desc']}, "
                f"inside {loc_name}, {atmosphere}, {period}, "
                f"cinematic camera, dramatic lighting",
                VID_SUFFIX
            ),
        })
    
    catalog["categories"].append(char_videos)
    
    # =====================================================================
    # CATEGORY 3: SETTING SHOTS (Still Images)
    # =====================================================================
    setting_stills = {
        "id": "settings_stills",
        "name": "Setting Shots — Still Images",
        "description": "Location establishing shots, interiors, and atmosphere. Used for narrator sections, transitions, and b-roll.",
        "note": f"💡 Locations from story config: {', '.join(rooms)}. Multiple angles per location for variety.",
        "assets": []
    }
    
    # Build setting shots from rooms + story context
    room_details = {
        "burial_chamber": {
            "name": "Burial Chamber",
            "desc": "vast burial chamber, golden sarcophagus, painted walls depicting the afterlife, torchlight flickering against hieroglyphs",
            "angles": [
                ("wide", "wide establishing shot showing full chamber, sarcophagus center, torches on walls"),
                ("sarcophagus_detail", "close-up of golden sarcophagus, intricate carvings, torchlight reflecting off gold"),
                ("hieroglyphs", "wall covered in painted hieroglyphs, afterlife scenes, torchlight casting shadows across ancient art"),
                ("crime_scene", "area beside sarcophagus where body was found, dark stain on stone floor, scattered equipment"),
            ]
        },
        "antechamber": {
            "name": "Antechamber",
            "desc": "antechamber with expedition equipment, excavation tools laid out, crates and supplies, torch brackets on stone walls",
            "angles": [
                ("wide", "wide shot of antechamber, expedition equipment scattered, crates and tools, torchlit"),
                ("equipment_pile", "close-up of equipment pile, excavation knives and chisels lined up, broad heavy blades, dusty handles"),
                ("wall_carvings", "stone walls with carved inscriptions, Professor's notes pinned nearby, lantern light"),
            ]
        },
        "upper_corridor": {
            "name": "Upper Corridor",
            "desc": "upper corridor near sealed entrance, sand filtering through cracks, claustrophobic passage, torch brackets casting long shadows",
            "angles": [
                ("wide", "long corridor stretching into darkness, torch brackets at intervals, sand on floor"),
                ("sealed_entrance", "sealed entrance shaft, sand piled high blocking exit, desperate hopelessness"),
                ("shadow_figure", "shadowy figure at far end of corridor, silhouette against torchlight, mysterious"),
            ]
        },
        "lower_passage": {
            "name": "Lower Passage",
            "desc": "lower passage between levels, narrow stone corridor, hieroglyphs on walls, single oil lamp casting intimate light",
            "angles": [
                ("wide", "narrow stone passage descending deeper, oil lamp on ground, hieroglyphs on both walls"),
                ("conversation_spot", "wider section of passage where two people could stand and talk, intimate and secretive"),
            ]
        },
        "second_level": {
            "name": "Second Level / Side Passage",
            "desc": "second level of tomb, newly discovered passages, unmapped territory, single oil lamp, the deepest point of the excavation",
            "angles": [
                ("wide", "unexplored second level, rough-hewn stone, single oil lamp providing dim light, mysterious"),
                ("mapping_station", "cartographer's mapping station, instruments laid out, detailed drawings pinned to makeshift board"),
                ("hidden_passage", "hidden connecting passage between levels, narrow crawlspace, dramatic perspective"),
            ]
        },
        "sealed_entrance": {
            "name": "Sealed Entrance (Exterior)",
            "desc": "tomb entrance in Valley of the Kings, 1893, sandstorm raging above, excavation camp partially buried",
            "angles": [
                ("exterior_storm", "Valley of the Kings, violent sandstorm, tomb entrance barely visible, dramatic sky, desolate"),
                ("camp", "expedition camp near tomb entrance, tents and equipment being battered by sand, lanterns swinging"),
                ("entrance_shaft", "looking down into the dark entrance shaft, sand pouring in, descent into darkness"),
            ]
        },
    }
    
    for room_key, room in room_details.items():
        for angle_id, angle_desc in room["angles"]:
            setting_stills["assets"].append({
                "id": f"set_{room_key}_{angle_id}",
                "name": f"{room['name']} — {angle_id.replace('_', ' ').title()}",
                "type": "still",
                "reuse": "All 8 episodes",
                "variants": "Keep all 4 MJ variations",
                "prompt": styled_prompt(
                    f"{angle_desc}, "
                    f"inside ancient Egyptian tomb, {atmosphere}, {period}, "
                    f"dramatic shadows",
                    MJ_SCENE
                ),
            })
    
    catalog["categories"].append(setting_stills)
    
    # =====================================================================
    # CATEGORY 4: SETTING CLIPS (Video)
    # =====================================================================
    setting_videos = {
        "id": "settings_video",
        "name": "Setting Clips — Video",
        "description": "Atmospheric video clips of locations. Used under narrator voiceover, for transitions between scenes, and to establish mood.",
        "note": "🎥 These are the highest-impact video assets. Prioritize generating these first.",
        "assets": []
    }
    
    setting_video_clips = [
        {
            "id": "vid_exterior_sandstorm",
            "name": "Exterior — Sandstorm Over Valley",
            "desc": "aerial/wide shot of Valley of the Kings, violent sandstorm sweeping across desert, dramatic clouds, tomb entrance below",
        },
        {
            "id": "vid_descent_into_tomb",
            "name": "Descent — Entering the Tomb",
            "desc": "POV or tracking shot descending into tomb entrance, light fading, torches appearing on walls, hieroglyphs emerging from darkness",
        },
        {
            "id": "vid_burial_chamber_pan",
            "name": "Burial Chamber — Slow Pan",
            "desc": "slow cinematic pan across burial chamber, revealing sarcophagus, painted walls, scattered expedition equipment, torchlight",
        },
        {
            "id": "vid_corridor_torchlight",
            "name": "Corridor — Torch Flicker Walk",
            "desc": "tracking shot through stone corridor, torches flickering on walls, long shadows moving, claustrophobic atmosphere",
        },
        {
            "id": "vid_sarcophagus_reveal",
            "name": "Sarcophagus — Dramatic Reveal",
            "desc": "slow push-in on golden sarcophagus, torchlight catching gold, dust particles floating, ancient mystery",
        },
        {
            "id": "vid_sand_falling",
            "name": "Atmosphere — Sand Filtering Through Cracks",
            "desc": "close-up of sand streaming through cracks in ceiling, tomb slowly being sealed, urgency and dread, torchlit",
        },
        {
            "id": "vid_hieroglyphs_firelight",
            "name": "Atmosphere — Hieroglyphs in Firelight",
            "desc": "slow pan across wall of hieroglyphs, firelight dancing across painted figures, afterlife scenes coming alive in shadow",
        },
        {
            "id": "vid_torch_flicker",
            "name": "Atmosphere — Torch Close-Up",
            "desc": "extreme close-up of torch flame guttering in stale air, sparks and smoke, shadows leaping on stone walls",
        },
        {
            "id": "vid_evidence_table",
            "name": "Evidence — Items on Surface",
            "desc": "slow overhead tracking shot of evidence laid out on stone surface — knife, note, torn fabric, boot print cast — dramatic spotlight",
        },
        {
            "id": "vid_sealed_entrance_sand",
            "name": "Sealed Entrance — Sand Collapse",
            "desc": "dramatic shot of entrance shaft collapsing with sand, sealing the tomb, dust cloud billowing inward, trapped",
        },
        {
            "id": "vid_group_gathered",
            "name": "Group — Suspects Assembled",
            "desc": "wide shot of group of Victorian-era explorers gathered in burial chamber, torchlight, tension, all watching each other",
        },
        {
            "id": "vid_transition_darkness",
            "name": "Transition — Into Darkness",
            "desc": "fade into deep darkness, single torch point of light receding, transition beat between scenes",
        },
    ]
    
    for clip in setting_video_clips:
        setting_videos["assets"].append({
            "id": clip["id"],
            "name": clip["name"],
            "type": "video",
            "reuse": "All 8 episodes",
            "variants": "Generate 2-3 takes, keep all for variety",
            "prompt": styled_prompt(
                f"{clip['desc']}, "
                f"ancient Egyptian tomb, {period}, "
                f"cinematic camera movement, dramatic lighting",
                VID_SUFFIX
            ),
        })
    
    catalog["categories"].append(setting_videos)
    
    # =====================================================================
    # CATEGORY 5: PROPS & EVIDENCE (Still Images)
    # =====================================================================
    props = {
        "id": "props_evidence",
        "name": "Props & Evidence — Still Images",
        "description": "Close-up shots of evidence, weapons, documents, and key objects. Used during evidence reveals and investigation scenes.",
        "note": "📸 These are critical for pacing — cut to evidence close-ups during dialogue to add visual variety.",
        "assets": []
    }
    
    # Murder weapon
    props["assets"].append({
        "id": "prop_excavation_knife",
        "name": "Murder Weapon — Excavation Knife",
        "type": "still",
        "reuse": "All 8 episodes (evidence scenes)",
        "variants": "Keep all 4 MJ variations (different angles/lighting)",
        "prompt": (
            styled_prompt(
            f"Close-up of heavy broad-bladed excavation knife on dark stone surface, "
            f"Victorian-era archaeological tool, faint traces of dark residue in handle rivets, "
            f"blade recently cleaned, dramatic overhead spotlight, forensic photography",
            MJ_PROP
        )
        ),
    })
    
    # Equipment pile
    props["assets"].append({
        "id": "prop_equipment_pile",
        "name": "Equipment Pile — Excavation Tools",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Array of Victorian-era excavation tools laid out — knives, chisels, rock picks, brushes, "
            f"all similar looking, heavy broad blades, wooden handles, dusty, "
            f"one knife subtly cleaner than the rest, "
            f"dramatic lighting, archaeological equipment, {period}",
            MJ_PROP
        )
        ),
    })
    
    # Blackmail note
    props["assets"].append({
        "id": "prop_threatening_note",
        "name": "Threatening Note",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Crumpled handwritten note on aged paper, block capital letters, "
            f"'THIS IS YOUR LAST WARNING', dark threatening message, "
            f"on dark stone surface, dramatic spotlight, {period}, "
            f"forensic close-up",
            MJ_PROP
        )
        ),
    })
    
    # Blackmail ledger
    props["assets"].append({
        "id": "prop_blackmail_ledger",
        "name": "Blackmail Ledger — Names and Amounts",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Hidden note with handwritten list of names and monetary amounts, "
            f"Victorian handwriting, pound sterling symbols, "
            f"found in a bedroll, creased and hidden, "
            f"dramatic spotlight on dark surface",
            MJ_PROP
        )
        ),
    })
    
    # Torn fabric
    props["assets"].append({
        "id": "prop_torn_fabric",
        "name": "Torn Fabric on Torch Bracket",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Small scrap of dark coat lining fabric caught on iron torch bracket, "
            f"ancient stone wall, close-up forensic detail, "
            f"dramatic side lighting, evidence photography, {period}",
            MJ_PROP
        )
        ),
    })
    
    # Boot prints
    props["assets"].append({
        "id": "prop_boot_prints",
        "name": "Boot Prints in Dust",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Two sets of boot prints in ancient tomb dust, "
            f"one heavy work boot, one lighter set approaching from behind, "
            f"dramatic overhead angle, forensic photography, "
            f"stone floor of burial chamber",
            MJ_PROP
        )
        ),
    })
    
    # Second brandy glass
    props["assets"].append({
        "id": "prop_brandy_glasses",
        "name": "Two Brandy Glasses — Second Wiped Clean",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Two brandy glasses on a dark surface beside a decanter, "
            f"one used with amber liquid, one suspiciously clean and wiped, "
            f"Victorian-era crystal glasses, dramatic spotlight, "
            f"forensic detail",
            MJ_PROP
        )
        ),
    })
    
    # Hollowed Bible
    props["assets"].append({
        "id": "prop_hollowed_bible",
        "name": "Hollowed Bible with Hidden Compartment",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Open leather-bound Bible with hollowed-out center containing lockpicks and small derringer pistol, "
            f"Victorian era, dramatic side lighting, dark surface, "
            f"evidence reveal, shocking discovery",
            MJ_PROP
        )
        ),
    })
    
    # Torn notebook pages
    props["assets"].append({
        "id": "prop_torn_notebook",
        "name": "Notebook with Torn Pages",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Leather-bound academic notebook open to pages with ragged torn edges, "
            f"scholarly handwriting, hieroglyphic sketches, ink stains, "
            f"Victorian-era research journal, dramatic lighting",
            MJ_PROP
        )
        ),
    })
    
    # Hidden camera (Tanaka)
    props["assets"].append({
        "id": "prop_hidden_camera",
        "name": "Hidden Camera Equipment",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"1890s concealed camera equipment, brass and leather, wrapped in cloth, "
            f"hidden among mapping instruments, forbidden photography equipment, "
            f"dramatic lighting, espionage, secret",
            MJ_PROP
        )
        ),
    })
    
    # Revolver
    props["assets"].append({
        "id": "prop_revolver",
        "name": "Recently Fired Revolver",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Victorian-era military revolver on dark surface, "
            f"recently fired, faint gun oil smell implied, "
            f"holster and belt nearby, dramatic lighting, "
            f"mercenary's weapon",
            MJ_PROP
        )
        ),
    })
    
    # Sarcophagus sketches (Vasquez)
    props["assets"].append({
        "id": "prop_sarcophagus_sketches",
        "name": "Detailed Sarcophagus Mechanism Sketches",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Journalist's notebook open to extremely detailed technical sketches "
            f"of an Egyptian sarcophagus opening mechanism, "
            f"far too detailed for a reporter, engineer-level diagrams, "
            f"dramatic overhead lighting",
            MJ_PROP
        )
        ),
    })
    
    # Gold coin
    props["assets"].append({
        "id": "prop_gold_coin",
        "name": "Gold Coin — Advance Payment",
        "type": "still",
        "reuse": "All 8 episodes",
        "variants": "Keep all 4",
        "prompt": (
            styled_prompt(
            f"Single gold coin on ancient stone floor near tomb entrance, "
            f"Spanish gold, 1890s, dropped and forgotten, "
            f"dramatic spotlight in darkness, evidence clue",
            MJ_PROP
        )
        ),
    })
    
    catalog["categories"].append(props)
    
    # =====================================================================
    # CATEGORY 6: TITLE CARDS & OVERLAYS (Auto-Generated)
    # =====================================================================
    title_cards = {
        "id": "title_cards",
        "name": "Title Cards & Overlays — Auto-Generated",
        "description": "Programmatically generated cards (PIL/Pillow). No Midjourney needed. Listed here for completeness.",
        "note": "🤖 These are generated by the assembly script per-episode. Included here for reference.",
        "assets": []
    }
    
    auto_cards = [
        ("card_episode_title", "Episode Title Card", "Episode title + number + subtitle. Per-episode."),
        ("card_round_1", "Round Title: THE SCENE", "Persistent across season"),
        ("card_round_2", "Round Title: OPENING STATEMENTS", "Persistent"),
        ("card_round_3", "Round Title: SUSPICION", "Persistent"),
        ("card_round_4", "Round Title: THE INVESTIGATION", "Persistent"),
        ("card_round_5", "Round Title: FINAL STATEMENTS", "Persistent"),
        ("card_accusation", "THE ACCUSATION", "Dramatic title card before detective accuses. Persistent."),
        ("card_reveal", "THE TRUTH", "Reveal card. Persistent."),
        ("card_scoring", "Scoring Breakdown", "Per-episode scores. Auto-generated per episode."),
        ("card_standings", "Season Standings", "Running leaderboard. Auto-generated per episode."),
        ("card_model_roster", "Model Roster Reveal", "Shows which model plays which character. Per-episode."),
        ("card_specs", "Model Specs Card", "Exact model versions list. Per-episode (updates if models change)."),
        ("card_end", "End Card / Next Episode Tease", "Per-episode."),
        ("overlay_lower_third", "Lower Third — Model Identity Bar", "Colored bar with model icon + character name + model name. Auto-generated per shot based on episode rotation."),
        ("overlay_corner_badge", "Corner Badge — Model Icon", "Small persistent model icon/color dot. Auto-generated."),
        ("overlay_think_frame", "Think Section Frame", "Visual indicator for THINK sections — model color border/glow. Auto-generated."),
    ]
    
    for card_id, card_name, card_note in auto_cards:
        title_cards["assets"].append({
            "id": card_id,
            "name": card_name,
            "type": "auto-generated",
            "reuse": card_note,
            "variants": "N/A — programmatic",
            "prompt": "",
        })
    
    catalog["categories"].append(title_cards)
    
    # =====================================================================
    # CATEGORY 7: MODEL AVATARS (Permanent — Already Exist)
    # =====================================================================
    avatars = {
        "id": "model_avatars",
        "name": "Model Avatars — Permanent Brand Identity",
        "description": "8 model avatars used in THINK sections and roster reveals. These are PERMANENT across all seasons. Already created in Set 01 using Nano Banana — may want to regenerate in Midjourney for consistency with the new art direction.",
        "note": "ℹ️ Existing avatars are in the-lineup/production/set_01/ and Google Drive. Regenerate only if style needs updating.",
        "assets": []
    }
    
    for m in MODELS:
        avatars["assets"].append({
            "id": f"avatar_{m['name'].lower()}",
            "name": f"{m['name']} {m['symbol']}",
            "type": "still",
            "reuse": "ALL seasons (permanent)",
            "variants": "Keep best 1-2 (already have versions with/without text)",
            "prompt": (
                styled_prompt(
                f"Abstract AI avatar representing {m['name']}, "
                f"color palette centered on {m['color']}, "
                f"contemplative digital entity, dark background, "
                f"mysterious and intelligent, glowing accents",
                MJ_SQUARE
            )
            ),
        })
    
    catalog["categories"].append(avatars)
    
    return catalog


# ---------------------------------------------------------------------------
# HTML Builder
# ---------------------------------------------------------------------------

def build_html(story_config: dict, output_path: str):
    catalog = build_asset_catalog(story_config)
    
    # Count totals
    total_stills = 0
    total_videos = 0
    total_auto = 0
    total_prompts = 0
    
    for cat in catalog["categories"]:
        for a in cat["assets"]:
            if a["type"] == "still":
                total_stills += 1
            elif a["type"] == "video":
                total_videos += 1
            elif a["type"] == "auto-generated":
                total_auto += 1
            if a.get("prompt"):
                total_prompts += 1
    
    # Estimate MJ generations (stills only, each = 1 prompt = 4 images)
    mj_prompts = sum(1 for cat in catalog["categories"] for a in cat["assets"] if a["type"] == "still" and a.get("prompt"))
    mj_images = mj_prompts * 4
    
    # Build category HTML
    categories_html = ""
    nav_html = ""
    
    for cat in catalog["categories"]:
        cat_id = cat["id"]
        count = len(cat["assets"])
        stills = sum(1 for a in cat["assets"] if a["type"] == "still")
        videos = sum(1 for a in cat["assets"] if a["type"] == "video")
        auto = sum(1 for a in cat["assets"] if a["type"] == "auto-generated")
        
        type_summary = []
        if stills: type_summary.append(f"{stills} stills")
        if videos: type_summary.append(f"{videos} videos")
        if auto: type_summary.append(f"{auto} auto")
        
        nav_html += f'<div class="nav-item" onclick="showCat(\'{cat_id}\')" id="nav_{cat_id}">{e(cat["name"].split("—")[0].strip())} <span class="nav-count">{count}</span></div>'
        
        assets_html = ""
        for a in cat["assets"]:
            type_badge = {
                "still": '<span class="badge badge-still">STILL</span>',
                "video": '<span class="badge badge-video">VIDEO</span>',
                "auto-generated": '<span class="badge badge-auto">AUTO</span>',
            }.get(a["type"], "")
            
            prompt_html = ""
            if a.get("prompt"):
                prompt_html = f'''
                <div class="asset-prompt">
                    <div class="prompt-label">Prompt:</div>
                    <code>{e(a["prompt"])}</code>
                </div>'''
            
            assets_html += f'''
            <div class="asset-card">
                <div class="asset-header">
                    {type_badge}
                    <span class="asset-name">{e(a["name"])}</span>
                </div>
                <div class="asset-meta">
                    <span class="meta-item">🔄 {e(a["reuse"])}</span>
                    <span class="meta-item">📸 {e(a["variants"])}</span>
                </div>
                {prompt_html}
            </div>'''
        
        note_html = f'<div class="cat-note">{e(cat.get("note", ""))}</div>' if cat.get("note") else ""
        
        categories_html += f'''
        <div class="category" id="cat_{cat_id}">
            <div class="cat-header">
                <h2>{e(cat["name"])}</h2>
                <span class="cat-count">{" · ".join(type_summary)}</span>
            </div>
            <p class="cat-desc">{e(cat["description"])}</p>
            {note_html}
            {assets_html}
        </div>'''
    
    # Export section: all prompts grouped
    all_still_prompts = []
    all_video_prompts = []
    
    for cat in catalog["categories"]:
        for a in cat["assets"]:
            if a.get("prompt"):
                line = f"// {a['id']}: {a['name']}\n{a['prompt']}"
                if a["type"] == "still":
                    all_still_prompts.append(line)
                elif a["type"] == "video":
                    all_video_prompts.append(line)
    
    still_prompts_text = "\n\n".join(all_still_prompts)
    video_prompts_text = "\n\n".join(all_video_prompts)
    
    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎬 Season 1 Asset Library — The Lineup</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0a0a0f;color:#e8e0d4;font-family:'Inter',sans-serif;line-height:1.5;padding:16px}}
.wrap{{max-width:960px;margin:0 auto}}
h1{{font-family:'Playfair Display',serif;color:#FFD700;font-size:1.6rem;text-align:center;margin-bottom:2px}}
h2{{font-family:'Playfair Display',serif;color:#FFD700;font-size:1.1rem;margin:0}}
.sub{{text-align:center;color:#8a8278;font-size:.8rem;margin-bottom:20px}}

/* Tabs */
.tabs{{display:flex;gap:6px;margin-bottom:20px;flex-wrap:wrap;justify-content:center}}
.tab{{padding:7px 14px;border-radius:5px;cursor:pointer;font-size:.78rem;border:1px solid #2a2520;background:#13131a;color:#8a8278;transition:all .2s}}
.tab:hover,.tab.active{{background:#1a1a24;color:#FFD700;border-color:#FFD700}}
.panel{{display:none}}.panel.active{{display:block}}

/* Metrics */
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:20px}}
.metric{{background:#13131a;border:1px solid #2a2520;border-radius:6px;padding:12px;text-align:center}}
.mv{{font-size:1.4rem;font-weight:700;color:#FFD700}}.ml{{font-size:.65rem;color:#8a8278;text-transform:uppercase;letter-spacing:.06em}}

/* Nav sidebar */
.layout{{display:grid;grid-template-columns:220px 1fr;gap:16px}}
@media(max-width:700px){{.layout{{grid-template-columns:1fr}}}}
.nav{{position:sticky;top:16px;align-self:start}}
.nav-item{{padding:8px 12px;border-radius:5px;cursor:pointer;font-size:.8rem;color:#8a8278;border:1px solid transparent;margin-bottom:4px;transition:all .15s;display:flex;justify-content:space-between;align-items:center}}
.nav-item:hover,.nav-item.active{{background:#13131a;color:#FFD700;border-color:#2a2520}}
.nav-count{{font-family:'JetBrains Mono',monospace;font-size:.65rem;background:#1a1a24;padding:1px 6px;border-radius:3px}}

/* Categories */
.category{{margin-bottom:28px}}
.cat-header{{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;margin-bottom:4px}}
.cat-count{{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#8a8278}}
.cat-desc{{font-size:.82rem;color:#a09888;margin-bottom:8px}}
.cat-note{{background:rgba(255,215,0,0.06);border:1px solid rgba(255,215,0,0.15);border-radius:4px;padding:8px 12px;font-size:.78rem;color:#c8b880;margin-bottom:12px}}

/* Asset cards */
.asset-card{{background:#13131a;border:1px solid #2a2520;border-radius:6px;padding:12px 16px;margin-bottom:8px}}
.asset-header{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px}}
.asset-name{{font-size:.88rem;font-weight:500}}
.asset-meta{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:4px}}
.meta-item{{font-size:.72rem;color:#8a8278}}
.asset-prompt{{background:rgba(140,64,192,0.06);border:1px solid rgba(140,64,192,0.15);border-radius:4px;padding:8px 12px;margin-top:6px}}
.prompt-label{{font-size:.65rem;color:#8a6ab0;text-transform:uppercase;letter-spacing:.04em;margin-bottom:2px}}
.asset-prompt code{{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#b8a0d0;word-break:break-word;line-height:1.4}}

/* Badges */
.badge{{font-family:'JetBrains Mono',monospace;font-size:.6rem;padding:2px 8px;border-radius:3px;text-transform:uppercase;letter-spacing:.04em;flex-shrink:0}}
.badge-still{{background:rgba(210,160,32,0.15);color:#D4A020;border:1px solid rgba(210,160,32,0.3)}}
.badge-video{{background:rgba(70,136,232,0.15);color:#4688E8;border:1px solid rgba(70,136,232,0.3)}}
.badge-auto{{background:rgba(100,100,100,0.15);color:#888;border:1px solid rgba(100,100,100,0.3)}}

/* Summary */
.summary-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}}
.summary-card{{background:#13131a;border:1px solid #2a2520;border-radius:6px;padding:14px}}
.summary-card h3{{color:#FFD700;font-size:.85rem;margin-bottom:8px}}
.summary-card p{{font-size:.78rem;color:#a09888;margin:2px 0}}

/* Export */
.ebox{{background:#13131a;border:1px solid #2a2520;border-radius:5px;padding:12px 16px;margin:12px 0}}
.ebox h3{{color:#FFD700;font-size:.85rem;margin-bottom:8px}}
.ebox textarea{{width:100%;background:#0a0a0f;color:#e8e0d4;border:1px solid #2a2520;border-radius:3px;padding:8px;font-family:'JetBrains Mono',monospace;font-size:.7rem;resize:vertical;min-height:200px}}
</style>
</head>
<body>
<div class="wrap">

<h1>🎬 Season 1 Asset Library</h1>
<p class="sub">The Tomb of Amenhotep — Reusable Assets Across All 8 Episodes</p>

<div class="tabs">
<div class="tab active" onclick="showTab('overview')">📊 Overview</div>
<div class="tab" onclick="showTab('artdirection')">🎨 Art Direction</div>
<div class="tab" onclick="showTab('library')">📦 Full Library</div>
<div class="tab" onclick="showTab('export')">📤 Export Prompts</div>
</div>

<!-- OVERVIEW TAB -->
<div id="overview" class="panel active">

<div class="metrics">
<div class="metric"><div class="mv">{total_stills + total_videos + total_auto}</div><div class="ml">Total Assets</div></div>
<div class="metric"><div class="mv">{total_stills}</div><div class="ml">Still Images</div></div>
<div class="metric"><div class="mv">{total_videos}</div><div class="ml">Video Clips</div></div>
<div class="metric"><div class="mv">{total_auto}</div><div class="ml">Auto-Generated</div></div>
<div class="metric"><div class="mv">{mj_prompts}</div><div class="ml">MJ Prompts</div></div>
<div class="metric"><div class="mv">~{mj_images}</div><div class="ml">MJ Images (4x)</div></div>
</div>

<div class="summary-grid">
<div class="summary-card">
<h3>🖼️ Character Portraits</h3>
<p>{len(story_config.get("suspects",[]))} suspects + detective + victim</p>
<p>{len(CHARACTER_STATES)} emotional states each</p>
<p>4 MJ variations kept per prompt</p>
<p><strong>= {4 * len(CHARACTER_STATES) * (len(story_config.get("suspects",[])) + 2)} total character images</strong></p>
</div>
<div class="summary-card">
<h3>🏛️ Setting Shots</h3>
<p>6 locations, multiple angles each</p>
<p>4 MJ variations kept per prompt</p>
<p>Used under narration & transitions</p>
</div>
<div class="summary-card">
<h3>🔍 Props & Evidence</h3>
<p>{sum(1 for cat in catalog["categories"] if cat["id"]=="props_evidence" for a in cat["assets"])} evidence items</p>
<p>Weapon, notes, fabric, tools, etc.</p>
<p>Cut to during investigation dialogue</p>
</div>
<div class="summary-card">
<h3>🎥 Video Clips</h3>
<p>{total_videos} video clips total</p>
<p>Settings + character actions</p>
<p>2-3 takes each for variety</p>
<p>Tool TBD (Runway / Kling / etc.)</p>
</div>
<div class="summary-card">
<h3>🤖 Auto-Generated</h3>
<p>{total_auto} title cards & overlays</p>
<p>Scoring, standings, round titles</p>
<p>Model identity overlays (post-production)</p>
<p>Generated by assembly script</p>
</div>
<div class="summary-card">
<h3>💡 Reuse Strategy</h3>
<p>All assets shared across 8 episodes</p>
<p>Visual variety via: MJ variations, shot selection, color grading, edit rhythm</p>
<p>Model identity via: colored overlay, lower third, corner badge</p>
<p><strong>Zero per-episode image generation needed</strong></p>
</div>
</div>

<div class="cat-note" style="margin-top:16px">
<strong>Workflow:</strong> Generate all Midjourney stills first → organize into asset folders → generate video clips with matching aesthetic → auto-generate title cards & overlays at assembly time. Model identity is NEVER baked into character images — it's always applied as a post-production overlay so assets work regardless of which AI model plays which role.
</div>

</div>

<!-- ART DIRECTION TAB -->
<div id="artdirection" class="panel">

<h2 style="color:#FFD700;font-size:1.2rem;margin-bottom:4px">🎨 Art Direction — Tim Burton Papercraft</h2>
<p style="font-size:.82rem;color:#a09888;margin-bottom:16px">This is the locked visual style for The Lineup. Every asset prompt includes this style DNA automatically.</p>

<div class="cat-note" style="margin-bottom:20px">
<strong>Style DNA (included in every prompt):</strong><br>
<code style="font-size:.82rem;color:#b8a0d0">{e(STYLE_DNA)}</code>
</div>

<div style="background:#13131a;border:1px solid #2a2520;border-radius:6px;padding:16px;margin-bottom:20px">
<h3 style="color:#FFD700;font-size:.95rem;margin-bottom:4px">🏛️ Brand Moodboard Prompts <span style="font-family:JetBrains Mono;font-size:.6rem;padding:2px 8px;border-radius:3px;background:rgba(210,160,32,0.15);color:#D4A020;border:1px solid rgba(210,160,32,0.3)">PERMANENT</span></h3>
<p style="font-size:.76rem;color:#8a8278;margin-bottom:12px">Defines The Lineup's visual identity. Generate these in Midjourney, curate the best ~8 into a moodboard, and note the code. Apply to ALL production prompts.</p>
{''.join(
    f'<div style="background:#0e0e16;border:1px solid #1a1a24;border-left:2px solid #D4A020;border-radius:4px;padding:8px 12px;margin-bottom:6px">'
    f'<div style="font-family:JetBrains Mono;font-size:.65rem;color:#8a8278;margin-bottom:2px">Brand #{i+1}</div>'
    f'<code style="font-family:JetBrains Mono;font-size:.72rem;color:#b8b0a4;word-break:break-word">{e(p)}</code>'
    f'</div>'
    for i, p in enumerate(BRAND_MOODBOARD_PROMPTS)
)}
<div class="ebox" style="margin-top:12px"><h3>Copy all brand prompts</h3>
<textarea readonly>{e(chr(10).join(f"// Brand #{i+1}{chr(10)}{p}" for i, p in enumerate(BRAND_MOODBOARD_PROMPTS)))}</textarea></div>
</div>

<div style="background:#13131a;border:1px solid #2a2520;border-radius:6px;padding:16px;margin-bottom:20px">
<h3 style="color:#FFD700;font-size:.95rem;margin-bottom:4px">🗺️ Setting Moodboard — The Tomb of Amenhotep <span style="font-family:JetBrains Mono;font-size:.6rem;padding:2px 8px;border-radius:3px;background:rgba(70,136,232,0.15);color:#4688E8;border:1px solid rgba(70,136,232,0.3)">PER SEASON</span></h3>
<p style="font-size:.76rem;color:#8a8278;margin-bottom:12px">Captures the Egyptian tomb setting for Season 1. Generate in Midjourney, curate into a second moodboard, note the code.</p>
{''.join(
    f'<div style="background:#0e0e16;border:1px solid #1a1a24;border-left:2px solid #4688E8;border-radius:4px;padding:8px 12px;margin-bottom:6px">'
    f'<div style="font-family:JetBrains Mono;font-size:.65rem;color:#8a8278;margin-bottom:2px">Setting #{i+1}</div>'
    f'<code style="font-family:JetBrains Mono;font-size:.72rem;color:#b8b0a4;word-break:break-word">{e(p)}</code>'
    f'</div>'
    for i, p in enumerate(SETTING_MOODBOARD_PROMPTS)
)}
<div class="ebox" style="margin-top:12px"><h3>Copy all setting prompts</h3>
<textarea readonly>{e(chr(10).join(f"// Setting #{i+1}{chr(10)}{p}" for i, p in enumerate(SETTING_MOODBOARD_PROMPTS)))}</textarea></div>
</div>

<div style="background:rgba(255,215,0,0.06);border:1px solid rgba(255,215,0,0.15);border-radius:5px;padding:14px;margin-top:16px">
<strong style="color:#FFD700;font-size:.88rem">Usage in Midjourney:</strong>
<p style="font-size:.8rem;color:#b8b0a4;margin-top:6px;line-height:1.7">
1. Generate all <strong>brand prompts</strong> → curate best ~8 images → create moodboard → note code: <code>[brand_code]</code><br>
2. Generate all <strong>setting prompts</strong> → curate best ~8 images → create moodboard → note code: <code>[setting_code]</code><br>
3. Append both codes to every production prompt:<br>
<code style="color:#7aa8d8;font-size:.82rem">your prompt here --p [brand_code] --p [setting_code]</code>
</p>
</div>

</div>

<!-- FULL LIBRARY TAB -->
<div id="library" class="panel">
{categories_html}
</div>

<!-- EXPORT TAB -->
<div id="export" class="panel">

<div class="metrics">
<div class="metric"><div class="mv">{len(all_still_prompts)}</div><div class="ml">Still Prompts</div></div>
<div class="metric"><div class="mv">{len(all_video_prompts)}</div><div class="ml">Video Prompts</div></div>
</div>

<div class="ebox">
<h3>🖼️ All Still Image / Midjourney Prompts ({len(all_still_prompts)})</h3>
<textarea readonly>{e(still_prompts_text)}</textarea>
</div>

<div class="ebox">
<h3>🎥 All Video Clip Prompts ({len(all_video_prompts)})</h3>
<textarea readonly>{e(video_prompts_text)}</textarea>
</div>

<div class="cat-note">
<strong>Midjourney usage:</strong> Paste each prompt into Midjourney. Keep ALL 4 variations per generation (don't pick favorites — variety is the goal). Append your brand + setting moodboard codes: <code>--p [brand_code] --p [setting_code]</code>
</div>

</div>

</div>
<script>
function showTab(id){{
document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
document.getElementById(id).classList.add('active');
event.target.classList.add('active');
}}
</script>
</body>
</html>'''
    
    with open(output_path, "w") as f:
        f.write(full_html)
    
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"Built: {output_path} ({size_kb:.0f} KB)")
    print(f"Assets: {total_stills} stills + {total_videos} videos + {total_auto} auto = {total_stills+total_videos+total_auto} total")
    print(f"MJ prompts: {mj_prompts} (= ~{mj_images} images at 4 per prompt)")
    print(f"Video prompts: {len(all_video_prompts)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_asset_library.py <story_config.json> [output.html]")
        sys.exit(1)
    
    with open(sys.argv[1]) as f:
        story = json.load(f)
    
    output = sys.argv[2] if len(sys.argv) > 2 else "s01_asset_library.html"
    build_html(story, output)
