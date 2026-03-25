#!/usr/bin/env python3
"""
Build a static HTML production planner from a v2 transcript.
Output is a self-contained HTML file that works on GitHub Pages / any browser.
"""

import json
import sys
import html as html_lib
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SEASONS_DIR = BASE_DIR / "seasons"

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

MJ_STYLE = "cinematic, moody lighting, dark atmosphere, film noir, 1920s period, --ar 16:9 --v 6.1 --style raw"
MJ_CHAR_STYLE = "portrait, dramatic lighting, dark background, 1920s attire, detailed face, cinematic --ar 2:3 --v 6.1 --style raw"


def load_story_config(set_id):
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


def e(text):
    """HTML escape."""
    return html_lib.escape(str(text)) if text else ""


def build_static_html(transcript_path: str, output_path: str):
    with open(transcript_path) as f:
        data = json.load(f)
    
    game = data.get("game", {})
    assignments = data.get("model_assignments", {})
    t = data.get("transcript", {})
    scores = data.get("scores", {})
    story = load_story_config(game.get("set_id", ""))
    
    # Build suspect model name lookup
    suspect_models = {}
    for s in assignments.get("suspects", []):
        suspect_models[s["character"]] = s.get("model_name", "")
    
    det_model = assignments.get("detective", {}).get("model_name", "Detective")
    
    loc_name = story.get("location", {}).get("name", "") if story else ""
    loc_desc = story.get("location", {}).get("description", "")[:100] if story else ""
    
    # Collect all assets
    all_assets = {}
    def need_asset(aid, scenes_list):
        if aid not in all_assets:
            all_assets[aid] = {"scenes": [], "type": "", "desc": "", "prompt": ""}
        all_assets[aid]["scenes"].append(scenes_list)
    
    sections = []
    scene_num = 0
    
    def add_scene(name, stype, media, video_prompt, dialogues, assets, notes=""):
        nonlocal scene_num
        scene_num += 1
        for a in assets:
            need_asset(a, scene_num)
        sections.append({
            "num": scene_num, "name": name, "type": stype, "media": media,
            "video_prompt": video_prompt, "dialogue": dialogues, "assets": assets, "notes": notes
        })
    
    # --- Build scenes ---
    add_scene("Intro", "intro", "pre-built", None, [], [])
    
    # Round 1
    scene_text = t.get("round_1_scene", "")
    add_scene("The Scene", "narrator", "video",
              f"Establishing shot: {loc_name}. Exterior in darkness, atmospheric, cinematic. {MJ_STYLE}",
              [("Narrator", "narrate", scene_text, "")],
              ["setting_exterior", "crime_scene", "victim_portrait"],
              "Split into multiple clips: exterior → interior → crime scene")
    
    # Round 2
    for entry in t.get("round_2_statements", []):
        char = entry["character"]
        model = entry.get("model_name", "")
        add_scene(f"Statement: {char}", "statement", "mixed",
                  f"Close-up of {char} speaking, dimly lit room, tense. {MJ_STYLE}",
                  [(model, "think", entry.get("think", ""), "model"),
                   (char, "speak", entry.get("speak", ""), "character")],
                  [f"char_{char.lower().replace(' ', '_')}"])
    
    # Round 3
    for i, conf in enumerate(t.get("round_3_suspicion", [])):
        tgt = conf["target"]
        chl = conf["challenger"]
        tgt_m = suspect_models.get(tgt, "")
        chl_m = suspect_models.get(chl, "")
        add_scene(f"Confrontation {i+1}: {tgt} vs {chl}", "confrontation", "mixed",
                  f"Two people in tense confrontation, dramatic lighting, split composition. {MJ_STYLE}",
                  [("Narrator", "narrate", conf.get("confrontation_prompt", ""), ""),
                   (tgt_m, "think", conf.get("target_think", ""), "model"),
                   (tgt, "speak", conf.get("target_speak", ""), "character"),
                   (chl_m, "think", conf.get("challenger_think", ""), "model"),
                   (chl, "speak", conf.get("challenger_speak", ""), "character")],
                  [f"char_{tgt.lower().replace(' ', '_')}", f"char_{chl.lower().replace(' ', '_')}"])
    
    # Detective Processing
    dp = t.get("detective_processing", {})
    if dp:
        add_scene("Detective Processing", "transition", "video",
                  f"Silhouette of detective thinking, smoke and shadow, abstract. {MJ_STYLE}",
                  [(dp.get("model_name", det_model), "think", dp.get("think", ""), "model")],
                  ["setting_lounge"])
    
    # Round 4
    inv = t.get("round_4_investigation", {})
    ev = inv.get("evidence_revealed", "")
    if ev:
        add_scene("Evidence Revealed", "evidence", "video",
                  f"Evidence on dark surface, spotlight, forensic detail. {MJ_STYLE}",
                  [("Narrator", "narrate", f"New evidence: {ev}", "")],
                  ["evidence_closeup"])
    
    for ex in inv.get("exchanges", []):
        sus = ex.get("suspect_character", "")
        sus_m = ex.get("suspect_model_name", "")
        add_scene(f"Investigation Q{ex['question_number']}: {sus}", "investigation", "mixed",
                  f"Interrogation, detective questioning suspect, tense. {MJ_STYLE}",
                  [(det_model, "think", ex.get("detective_think", ""), "model"),
                   ("Detective", "speak", ex.get("detective_speak", ""), "character"),
                   (sus_m, "think", ex.get("suspect_think", ""), "model"),
                   (sus, "speak", ex.get("suspect_speak", ""), "character")],
                  [f"char_{sus.lower().replace(' ', '_')}", "setting_lounge"])
    
    # Round 5 final statements
    for entry in t.get("round_5_final_statements", []):
        char = entry["character"]
        model = entry.get("model_name", "")
        add_scene(f"Final Statement: {char}", "final_statement", "mixed",
                  f"Close-up of {char}, intense, final words, dramatic. {MJ_STYLE}",
                  [(model, "think", entry.get("think", ""), "model"),
                   (char, "speak", entry.get("speak", ""), "character")],
                  [f"char_{char.lower().replace(' ', '_')}"])
    
    # Accusation
    acc = t.get("round_5_accusation", {})
    if acc:
        add_scene("The Accusation", "accusation", "video",
                  f"Dramatic pointing gesture, spotlight on accused, theatrical. {MJ_STYLE}",
                  [(det_model, "think", acc.get("detective_think", ""), "model"),
                   ("Detective", "speak", acc.get("detective_speak", ""), "character")],
                  ["title_card_accusation"],
                  f"Accused: {acc.get('accused', '?')}")
    
    # Accused response
    ar = t.get("round_5_accused_response")
    if ar:
        char = ar["character"]
        model = suspect_models.get(char, "")
        add_scene(f"Accused Response: {char}", "accused_response", "mixed",
                  f"Close-up reaction, {char} responding, emotional. {MJ_STYLE}",
                  [(model, "think", ar.get("think", ""), "model"),
                   (char, "speak", ar.get("speak", ""), "character")],
                  [f"char_{char.lower().replace(' ', '_')}"])
    
    # Reactions
    for entry in t.get("round_5_reactions", []):
        char = entry["character"]
        model = entry.get("model_name", "")
        add_scene(f"Reaction: {char}", "reaction", "static",
                  None,
                  [(model, "think", entry.get("think", ""), "model"),
                   (char, "speak", entry.get("speak", ""), "character")],
                  [f"char_{char.lower().replace(' ', '_')}"])
    
    # Reveal + Outro
    add_scene("The Reveal", "reveal", "video",
              f"Dramatic reveal, spotlight shifting, truth unveiled. {MJ_STYLE}",
              [("Narrator", "narrate", "The truth is revealed...", "")],
              ["title_card_reveal", "scoring_card"])
    
    add_scene("Outro", "outro", "static", None,
              [("Narrator", "narrate", "Season standings...", "")],
              ["standings_card", "end_card"])
    
    # --- Enrich assets ---
    if story:
        for aid in all_assets:
            a = all_assets[aid]
            if aid.startswith("char_"):
                a["type"] = "character"
                for s in story.get("suspects", []):
                    if s["name"].lower().replace(" ", "_") in aid:
                        a["desc"] = f'{s["name"]}: {s["role"]}'
                        a["prompt"] = f'{s["name"]}, {s["role"]}, {s.get("background","")[:120]}... {MJ_CHAR_STYLE}'
                        break
                if not a["desc"]:
                    a["desc"] = aid.replace("char_", "").replace("_", " ").title()
                    a["prompt"] = f'{a["desc"]}, {MJ_CHAR_STYLE}'
            elif aid == "victim_portrait":
                v = story.get("victim", {})
                a["type"] = "character"
                a["desc"] = f'Victim: {v.get("name","?")}'
                a["prompt"] = f'{v.get("name","victim")}, {v.get("description","")[:120]}, deceased, {MJ_CHAR_STYLE}'
            elif aid == "crime_scene":
                a["type"] = "setting"
                a["desc"] = "Crime scene"
                a["prompt"] = f'Crime scene, {loc_name}, forensic detail, {MJ_STYLE}'
            elif aid.startswith("setting_"):
                a["type"] = "setting"
                a["desc"] = f'Setting: {aid.replace("setting_","")}'
                a["prompt"] = f'{loc_name}, {aid.replace("setting_","")} area, {loc_desc}, {MJ_STYLE}'
            elif aid == "evidence_closeup":
                a["type"] = "prop"
                a["desc"] = "Evidence close-up"
                a["prompt"] = f"Evidence on dark surface, spotlight, forensic photography, {MJ_STYLE}"
            elif "card" in aid:
                a["type"] = "title_card"
                a["desc"] = f'Auto-generated: {aid}'
                a["prompt"] = ""
    
    # --- TTS stats ---
    total_chars = 0
    total_clips = 0
    narrator_chars = 0
    model_chars = {}
    char_chars = {}
    
    for sec in sections:
        for speaker, dtype, text, voice in sec["dialogue"]:
            c = len(text)
            if c == 0:
                continue
            total_chars += c
            total_clips += 1
            if dtype == "narrate":
                narrator_chars += c
            elif dtype == "think":
                model_chars[speaker] = model_chars.get(speaker, 0) + c
            elif dtype == "speak":
                char_chars[speaker] = char_chars.get(speaker, 0) + c
    
    # --- Generate HTML ---
    html_parts = []
    
    # Scene rows
    for sec in sections:
        dialogues_html = ""
        for speaker, dtype, text, voice in sec["dialogue"]:
            if not text:
                continue
            chars = len(text)
            txt = e(text)
            if dtype == "think":
                color = MODEL_COLORS.get(speaker, "#FFD700")
                dialogues_html += f'<div class="dlg think" style="border-left-color:{color}"><span class="dlg-label" style="color:{color}">🧠 {e(speaker)} (THINK) [{chars}c]</span><br>{txt}</div>'
            elif dtype == "speak":
                dialogues_html += f'<div class="dlg speak"><span class="dlg-label">🗣️ {e(speaker)} (SPEAK) [{chars}c]</span><br>{txt}</div>'
            elif dtype == "narrate":
                dialogues_html += f'<div class="dlg narrate"><span class="dlg-label">📖 Narrator [{chars}c]</span><br>{txt}</div>'
        
        media_badge = {"video": "🎥 Video", "static": "🖼️ Static", "mixed": "🎥🖼️ Mixed", "pre-built": "📦 Pre-built"}.get(sec["media"], "")
        
        vp_html = ""
        if sec["video_prompt"]:
            vp_html = f'<div class="prompt-box video-prompt"><strong>Video Prompt:</strong><br><code>{e(sec["video_prompt"])}</code></div>'
        
        notes_html = f'<div class="notes">📝 {e(sec["notes"])}</div>' if sec.get("notes") else ""
        assets_html = f'<div class="assets-list">Assets: {", ".join(sec["assets"])}</div>' if sec["assets"] else ""
        
        html_parts.append(f'''
        <div class="scene-card" data-type="{sec["type"]}">
            <div class="scene-header">
                <span class="scene-num">Scene {sec["num"]}</span>
                <span class="scene-name">{e(sec["name"])}</span>
                <span class="scene-badge">{media_badge}</span>
                <span class="scene-type">{sec["type"]}</span>
            </div>
            {notes_html}
            {vp_html}
            <div class="dialogue-block">{dialogues_html}</div>
            {assets_html}
        </div>''')
    
    scenes_html = "\n".join(html_parts)
    
    # Asset manifest HTML
    assets_html_parts = []
    for aid, a in sorted(all_assets.items(), key=lambda x: x[1].get("type","")):
        prompt_html = f'<div class="prompt-box mj-prompt"><strong>Midjourney:</strong><br><code>{e(a["prompt"])}</code></div>' if a["prompt"] else '<div class="auto-gen">Auto-generated (no prompt needed)</div>'
        assets_html_parts.append(f'''
        <div class="asset-card">
            <div class="asset-header"><span class="asset-type">{e(a.get("type",""))}</span> <strong>{e(aid)}</strong></div>
            <div class="asset-desc">{e(a.get("desc",""))}</div>
            {prompt_html}
        </div>''')
    assets_section = "\n".join(assets_html_parts)
    
    # TTS breakdown HTML
    model_rows = "".join(
        f'<tr><td><span class="dot" style="background:{MODEL_COLORS.get(m,"#888")}"></span> {e(m)}</td><td>{c:,}</td></tr>'
        for m, c in sorted(model_chars.items(), key=lambda x: x[1], reverse=True)
    )
    char_rows = "".join(
        f'<tr><td>{e(ch)}</td><td>{c:,}</td></tr>'
        for ch, c in sorted(char_chars.items(), key=lambda x: x[1], reverse=True)
    )
    
    # Scores HTML
    det = scores.get("detective", {})
    killer = scores.get("killer", {})
    innocents = scores.get("innocents", {})
    
    scores_rows = f'<tr><td>🔍 Detective</td><td>{e(det.get("model_name",""))}</td><td>—</td><td><strong>{det.get("total",0)}</strong></td></tr>'
    scores_rows += f'<tr><td>🔪 Killer</td><td>{e(killer.get("model_name",""))}</td><td>{e(killer.get("character",""))}</td><td><strong>{killer.get("total",0)}</strong></td></tr>'
    for name, info in innocents.items():
        scores_rows += f'<tr><td>🛡️ Innocent</td><td>{e(info.get("model_name",""))}</td><td>{e(name)}</td><td><strong>{info.get("total",0)}</strong></td></tr>'
    
    # All MJ prompts
    all_mj = "\n\n".join(
        f"// {aid}: {a.get('desc','')}\n{a['prompt']}"
        for aid, a in sorted(all_assets.items())
        if a["prompt"]
    )
    
    # All video prompts
    all_vid = "\n\n".join(
        f"// Scene {s['num']}: {s['name']}\n{s['video_prompt']}"
        for s in sections
        if s.get("video_prompt")
    )
    
    # Full HTML
    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎬 The Lineup — Production Planner</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0a0a0f;color:#e8e0d4;font-family:'Inter',sans-serif;line-height:1.6;padding:20px}}
.container{{max-width:900px;margin:0 auto}}
h1{{font-family:'Playfair Display',serif;color:#FFD700;font-size:1.8rem;text-align:center;margin-bottom:4px}}
.subtitle{{text-align:center;color:#8a8278;font-size:.85rem;margin-bottom:24px}}
.tabs{{display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap;justify-content:center}}
.tab{{padding:8px 16px;border-radius:6px;cursor:pointer;font-size:.8rem;border:1px solid #2a2520;background:#13131a;color:#8a8278;transition:all .2s}}
.tab:hover,.tab.active{{background:#1a1a24;color:#FFD700;border-color:#FFD700}}
.panel{{display:none}}.panel.active{{display:block}}
.scene-card{{background:#13131a;border:1px solid #2a2520;border-radius:8px;padding:16px;margin-bottom:12px}}
.scene-header{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}}
.scene-num{{font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#8a8278;background:#1a1a24;padding:2px 8px;border-radius:3px}}
.scene-name{{font-family:'Playfair Display',serif;color:#FFD700;font-size:1rem}}
.scene-badge{{font-size:.7rem;padding:2px 8px;border-radius:3px;background:rgba(70,136,232,0.15);color:#4688E8;border:1px solid rgba(70,136,232,0.3)}}
.scene-type{{font-family:'JetBrains Mono',monospace;font-size:.65rem;color:#8a8278;margin-left:auto}}
.dlg{{padding:8px 12px;margin:4px 0;border-radius:4px;font-size:.82rem;border-left:3px solid #888}}
.dlg.think{{background:rgba(255,215,0,0.06);border-left-color:#FFD700}}
.dlg.speak{{background:rgba(255,255,255,0.03)}}
.dlg.narrate{{background:rgba(150,150,160,0.06);border-left-color:#95A5A6;font-style:italic}}
.dlg-label{{font-weight:600;font-size:.75rem}}
.prompt-box{{border-radius:4px;padding:8px 12px;margin:8px 0;font-size:.78rem}}
.video-prompt{{background:rgba(70,136,232,0.08);border:1px solid rgba(70,136,232,0.25)}}
.mj-prompt{{background:rgba(140,64,192,0.08);border:1px solid rgba(140,64,192,0.25)}}
code{{font-family:'JetBrains Mono',monospace;font-size:.75rem;word-break:break-word}}
.notes{{background:rgba(255,215,0,0.06);border:1px solid rgba(255,215,0,0.15);border-radius:4px;padding:6px 10px;font-size:.8rem;margin-bottom:8px}}
.assets-list{{font-size:.75rem;color:#8a8278;margin-top:6px}}
.asset-card{{background:#13131a;border:1px solid #2a2520;border-radius:6px;padding:12px;margin-bottom:8px}}
.asset-header{{margin-bottom:4px}}.asset-type{{font-family:'JetBrains Mono',monospace;font-size:.65rem;color:#8a8278;background:#1a1a24;padding:2px 6px;border-radius:3px}}
.asset-desc{{font-size:.85rem;color:#b8b0a4;margin-bottom:6px}}
.auto-gen{{font-size:.75rem;color:#8a8278;font-style:italic}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}}
.metric{{background:#13131a;border:1px solid #2a2520;border-radius:8px;padding:16px;text-align:center}}
.metric-val{{font-size:1.6rem;font-weight:700;color:#FFD700}}
.metric-lbl{{font-size:.7rem;color:#8a8278;text-transform:uppercase;letter-spacing:.08em}}
table{{width:100%;border-collapse:collapse;margin:12px 0}}
th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #2a2520;font-size:.85rem}}
th{{color:#8a8278;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle}}
.export-box{{background:#13131a;border:1px solid #2a2520;border-radius:6px;padding:12px;margin:12px 0}}
.export-box textarea{{width:100%;background:#0a0a0f;color:#e8e0d4;border:1px solid #2a2520;border-radius:4px;padding:10px;font-family:'JetBrains Mono',monospace;font-size:.75rem;resize:vertical;min-height:200px}}
.export-box h3{{color:#FFD700;font-size:.9rem;margin-bottom:8px}}
.score-result{{font-size:.85rem;color:#b8b0a4;margin-top:12px}}
</style>
</head>
<body>
<div class="container">
<h1>🎬 The Lineup — Production Planner</h1>
<p class="subtitle">{e(game.get("title",""))} — S{game.get("season",1)}E{game.get("episode",1)} | {scene_num} scenes | {total_clips} clips | {total_chars:,} chars</p>

<div class="tabs">
<div class="tab active" onclick="showTab('scenes')">📋 Scenes</div>
<div class="tab" onclick="showTab('assets')">🎨 Assets</div>
<div class="tab" onclick="showTab('tts')">🎙️ TTS</div>
<div class="tab" onclick="showTab('scores')">🏆 Scores</div>
<div class="tab" onclick="showTab('export')">📤 Export</div>
</div>

<div id="scenes" class="panel active">
{scenes_html}
</div>

<div id="assets" class="panel">
<h2 style="color:#FFD700;margin-bottom:16px">Asset Manifest ({len(all_assets)} assets)</h2>
{assets_section}
</div>

<div id="tts" class="panel">
<div class="metrics">
<div class="metric"><div class="metric-val">{total_chars:,}</div><div class="metric-lbl">Total Characters</div></div>
<div class="metric"><div class="metric-val">{total_clips}</div><div class="metric-lbl">Audio Clips</div></div>
<div class="metric"><div class="metric-val">{narrator_chars:,}</div><div class="metric-lbl">Narrator Chars</div></div>
<div class="metric"><div class="metric-val">${total_chars/1000*0.30:.2f}</div><div class="metric-lbl">Est. TTS Cost</div></div>
</div>
<h3 style="color:#FFD700">🧠 Model Voices (THINK)</h3>
<table><tr><th>Model</th><th>Characters</th></tr>{model_rows}</table>
<h3 style="color:#FFD700;margin-top:20px">🗣️ Character Voices (SPEAK)</h3>
<table><tr><th>Character</th><th>Characters</th></tr>{char_rows}</table>
</div>

<div id="scores" class="panel">
<h2 style="color:#FFD700;margin-bottom:16px">Game Results</h2>
<table>
<tr><th>Role</th><th>Model</th><th>Character</th><th>Score</th></tr>
{scores_rows}
</table>
<div class="score-result">
Detective: Killer={det.get("correct_killer","?")}, Weapon={det.get("correct_weapon","?")}, Motive={det.get("correct_motive","?")}<br>
Killer: Evaded={killer.get("evaded","?")}, Framing={killer.get("framing_bonus","?")}
</div>
</div>

<div id="export" class="panel">
<div class="export-box">
<h3>🎨 All Midjourney Prompts</h3>
<textarea readonly>{e(all_mj)}</textarea>
</div>
<div class="export-box">
<h3>🎥 All Video Generation Prompts</h3>
<textarea readonly>{e(all_vid)}</textarea>
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
    print(f"Scenes: {scene_num} | Clips: {total_clips} | Chars: {total_chars:,} | Assets: {len(all_assets)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_static.py <transcript.json> [output.html]")
        sys.exit(1)
    
    transcript = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else transcript.replace(".json", "_planner.html")
    build_static_html(transcript, output)
