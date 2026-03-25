#!/usr/bin/env python3
"""
Build static HTML production planner v2 — shot-level breakdown.
"""

import json
import sys
import html as html_lib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from shots import build_shots, get_shot_stats, MODEL_COLORS, BRAND_MOODBOARD_PROMPTS, generate_setting_moodboard_prompts

BASE_DIR = Path(__file__).parent.parent
SEASONS_DIR = BASE_DIR / "seasons"


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
    return html_lib.escape(str(text)) if text else ""


def build_html(transcript_path: str, output_path: str):
    with open(transcript_path) as f:
        data = json.load(f)
    
    game = data.get("game", {})
    scores = data.get("scores", {})
    assignments = data.get("model_assignments", {})
    story = load_story_config(game.get("set_id", ""))
    
    shots = build_shots(data, story)
    stats = get_shot_stats(shots)
    
    # Group shots by scene
    scenes_ordered = []
    current_scene = None
    for shot in shots:
        if shot["scene"] != current_scene:
            current_scene = shot["scene"]
            scenes_ordered.append({"name": current_scene, "shots": []})
        scenes_ordered[-1]["shots"].append(shot)
    
    # Build shot HTML
    scenes_html = ""
    for scene in scenes_ordered:
        shots_html = ""
        scene_dur = sum(s["duration"] for s in scene["shots"])
        
        for shot in scene["shots"]:
            color = MODEL_COLORS.get(shot["model_name"], "#888")
            
            # Type badge
            type_icons = {"think": "🧠", "speak": "🗣️", "narrate": "📖", "title_card": "🎬"}
            icon = type_icons.get(shot["type"], "")
            
            # Media badge
            media_badges = {
                "video": '<span class="badge badge-video">VIDEO</span>',
                "static": '<span class="badge badge-static">STATIC</span>',
                "mixed": '<span class="badge badge-mixed">MIXED</span>',
                "title_card": '<span class="badge badge-card">CARD</span>',
                "pre-built": '<span class="badge badge-card">PRE-BUILT</span>',
            }
            media_badge = media_badges.get(shot["media"], "")
            
            # Prompt
            prompt_html = ""
            if shot["prompt"]:
                prompt_html = f'<div class="shot-prompt"><code>{e(shot["prompt"])}</code></div>'
            
            # Text styling by type
            if shot["type"] == "think":
                text_class = "shot-text-think"
                border_style = f'border-left: 3px solid {color}'
            elif shot["type"] == "speak":
                text_class = "shot-text-speak"
                border_style = "border-left: 3px solid #666"
            elif shot["type"] == "narrate":
                text_class = "shot-text-narrate"
                border_style = "border-left: 3px solid #95A5A6"
            else:
                text_class = "shot-text-card"
                border_style = "border-left: 3px solid #333"
            
            speaker_display = shot["speaker"] or shot["model_name"] or ""
            if shot["type"] == "think" and shot["model_name"]:
                speaker_display = f'<span style="color:{color}">{e(shot["model_name"])}</span>'
            else:
                speaker_display = e(speaker_display)
            
            shots_html += f'''
            <div class="shot" style="{border_style}">
                <div class="shot-header">
                    <span class="shot-num">#{shot["shot_id"]}</span>
                    <span class="shot-icon">{icon}</span>
                    <span class="shot-speaker">{speaker_display}</span>
                    {media_badge}
                    <span class="shot-dur">{shot["duration"]}s</span>
                    <span class="shot-chars">{shot["chars"]}c</span>
                </div>
                <div class="{text_class}">{e(shot["text"])}</div>
                {prompt_html}
            </div>'''
        
        scenes_html += f'''
        <div class="scene-block">
            <div class="scene-title">
                <span class="scene-name">{e(scene["name"])}</span>
                <span class="scene-meta">{len(scene["shots"])} shots · {scene_dur:.0f}s</span>
            </div>
            {shots_html}
        </div>'''
    
    # Asset manifest
    assets = {}
    for shot in shots:
        if shot["asset"] and shot["asset"] not in assets:
            assets[shot["asset"]] = {"scenes": set(), "prompt": shot.get("prompt", "")}
        if shot["asset"]:
            assets[shot["asset"]]["scenes"].add(shot["scene"])
    
    # Enrich asset prompts from story config
    asset_html = ""
    if story:
        MJ_CHAR = f"portrait, dramatic lighting, dark background, detailed face, cinematic --ar 2:3 --v 6.1 --quality 2 --style raw"
        MJ_SET = f"cinematic, moody lighting, dark atmosphere, film noir --ar 16:9 --v 6.1 --quality 2 --style raw"
        
        for aid in sorted(assets.keys()):
            desc = aid
            mj = ""
            if aid.startswith("char_"):
                for s in story.get("suspects", []):
                    if s["name"].lower().replace(" ", "_") in aid:
                        desc = f'{s["name"]}: {s["role"]}'
                        mj = f'{s["name"]}, {s["role"]}, {s.get("background","")[:120]}... {MJ_CHAR}'
                        break
            elif aid.startswith("model_avatar_"):
                model = aid.replace("model_avatar_", "").title()
                desc = f"Model avatar: {model}"
                mj = f"Abstract AI avatar, {model} brand identity, contemplative, digital aesthetic, dark background --ar 1:1 --v 6.1 --quality 2 --style raw"
            elif "detective" in aid:
                desc = "Detective character"
                mj = f"Detective, lead investigator, 1920s attire, analytical expression, {MJ_CHAR}"
            
            scenes_used = ", ".join(sorted(assets[aid]["scenes"]))
            prompt_html = f'<div class="asset-prompt"><code>{e(mj)}</code></div>' if mj else '<span class="auto-gen">Auto-generated</span>'
            
            asset_html += f'''
            <div class="asset-item">
                <strong>{e(aid)}</strong> — {e(desc)}
                <div class="asset-scenes">Used in: {e(scenes_used)}</div>
                {prompt_html}
            </div>'''
    
    # TTS stats
    narrator_chars = sum(s["chars"] for s in shots if s["type"] == "narrate")
    think_chars = sum(s["chars"] for s in shots if s["type"] == "think")
    speak_chars = sum(s["chars"] for s in shots if s["type"] == "speak")
    
    model_chars = {}
    char_chars = {}
    for s in shots:
        if s["type"] == "think" and s["model_name"]:
            model_chars[s["model_name"]] = model_chars.get(s["model_name"], 0) + s["chars"]
        elif s["type"] == "speak" and s["speaker"]:
            char_chars[s["speaker"]] = char_chars.get(s["speaker"], 0) + s["chars"]
    
    model_rows = "".join(
        f'<tr><td><span class="dot" style="background:{MODEL_COLORS.get(m,"#888")}"></span>{e(m)}</td><td>{c:,}</td></tr>'
        for m, c in sorted(model_chars.items(), key=lambda x: x[1], reverse=True)
    )
    char_rows = "".join(
        f'<tr><td>{e(ch)}</td><td>{c:,}</td></tr>'
        for ch, c in sorted(char_chars.items(), key=lambda x: x[1], reverse=True)
    )
    
    # Scores
    det = scores.get("detective", {})
    killer = scores.get("killer", {})
    innocents = scores.get("innocents", {})
    scores_rows = f'<tr><td>🔍</td><td>{e(det.get("model_name",""))}</td><td>Detective</td><td><strong>{det.get("total",0)}</strong></td></tr>'
    scores_rows += f'<tr><td>🔪</td><td>{e(killer.get("model_name",""))}</td><td>{e(killer.get("character",""))}</td><td><strong>{killer.get("total",0)}</strong></td></tr>'
    for name, info in innocents.items():
        scores_rows += f'<tr><td>🛡️</td><td>{e(info.get("model_name",""))}</td><td>{e(name)}</td><td><strong>{info.get("total",0)}</strong></td></tr>'
    
    # Moodboard prompts
    setting_moodboard = generate_setting_moodboard_prompts(story)
    
    brand_prompts_html = ""
    for i, p in enumerate(BRAND_MOODBOARD_PROMPTS):
        brand_prompts_html += f'''
        <div class="mb-prompt-item">
            <div class="mb-prompt-num">Brand #{i+1}</div>
            <div class="mb-prompt-text"><code>{e(p)}</code></div>
        </div>'''
    
    setting_prompts_html = ""
    for i, p in enumerate(setting_moodboard):
        setting_prompts_html += f'''
        <div class="mb-prompt-item mb-setting">
            <div class="mb-prompt-num">Setting #{i+1}</div>
            <div class="mb-prompt-text"><code>{e(p)}</code></div>
        </div>'''
    
    brand_prompts_text = "\n\n".join(f"// Brand #{i+1}\n{p}" for i, p in enumerate(BRAND_MOODBOARD_PROMPTS))
    setting_prompts_text = "\n\n".join(f"// Setting #{i+1}\n{p}" for i, p in enumerate(setting_moodboard))
    
    # Export prompts
    all_mj = "\n\n".join(f"// {aid}\n{assets[aid].get('prompt','')}" for aid in sorted(assets) if assets[aid].get("prompt"))
    all_vid = "\n\n".join(f"// Shot #{s['shot_id']}: {s['scene']}\n{s['prompt']}" for s in shots if s["prompt"] and s["media"] in ("video", "mixed"))
    
    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎬 Production Planner — {e(game.get("title",""))}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0a0a0f;color:#e8e0d4;font-family:'Inter',sans-serif;line-height:1.5;padding:16px}}
.wrap{{max-width:920px;margin:0 auto}}
h1{{font-family:'Playfair Display',serif;color:#FFD700;font-size:1.6rem;text-align:center;margin-bottom:2px}}
.sub{{text-align:center;color:#8a8278;font-size:.8rem;margin-bottom:20px}}
.tabs{{display:flex;gap:6px;margin-bottom:20px;flex-wrap:wrap;justify-content:center}}
.tab{{padding:7px 14px;border-radius:5px;cursor:pointer;font-size:.78rem;border:1px solid #2a2520;background:#13131a;color:#8a8278;transition:all .2s}}
.tab:hover,.tab.active{{background:#1a1a24;color:#FFD700;border-color:#FFD700}}
.panel{{display:none}}.panel.active{{display:block}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:20px}}
.metric{{background:#13131a;border:1px solid #2a2520;border-radius:6px;padding:12px;text-align:center}}
.mv{{font-size:1.4rem;font-weight:700;color:#FFD700}}.ml{{font-size:.65rem;color:#8a8278;text-transform:uppercase;letter-spacing:.06em}}
.scene-block{{margin-bottom:20px}}
.scene-title{{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#151520;border:1px solid #252530;border-radius:6px 6px 0 0}}
.scene-name{{font-family:'Playfair Display',serif;color:#FFD700;font-size:.95rem}}
.scene-meta{{font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#8a8278}}
.shot{{padding:10px 12px;border-bottom:1px solid #1a1a24;background:#0e0e16}}
.shot:last-child{{border-bottom:none;border-radius:0 0 6px 6px}}
.shot-header{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px}}
.shot-num{{font-family:'JetBrains Mono',monospace;font-size:.65rem;color:#555;min-width:32px}}
.shot-icon{{font-size:.85rem}}
.shot-speaker{{font-size:.8rem;font-weight:500}}
.shot-dur{{font-family:'JetBrains Mono',monospace;font-size:.65rem;color:#8a8278;margin-left:auto}}
.shot-chars{{font-family:'JetBrains Mono',monospace;font-size:.65rem;color:#555}}
.badge{{font-family:'JetBrains Mono',monospace;font-size:.6rem;padding:1px 6px;border-radius:3px;text-transform:uppercase;letter-spacing:.03em}}
.badge-video{{background:rgba(70,136,232,0.15);color:#4688E8;border:1px solid rgba(70,136,232,0.3)}}
.badge-static{{background:rgba(150,150,160,0.1);color:#999;border:1px solid rgba(150,150,160,0.2)}}
.badge-mixed{{background:rgba(210,160,32,0.12);color:#D4A020;border:1px solid rgba(210,160,32,0.25)}}
.badge-card{{background:rgba(100,100,100,0.1);color:#777;border:1px solid rgba(100,100,100,0.2)}}
.shot-text-think{{font-size:.8rem;color:#c8b880;padding:4px 0}}
.shot-text-speak{{font-size:.8rem;color:#d0ccc4;padding:4px 0}}
.shot-text-narrate{{font-size:.8rem;color:#a0a0a8;font-style:italic;padding:4px 0}}
.shot-text-card{{font-size:.8rem;color:#777;padding:4px 0}}
.shot-prompt{{background:rgba(70,136,232,0.06);border:1px solid rgba(70,136,232,0.15);border-radius:3px;padding:6px 10px;margin-top:4px}}
.shot-prompt code{{font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#7aa8d8;word-break:break-word}}
.asset-item{{background:#13131a;border:1px solid #2a2520;border-radius:5px;padding:10px 14px;margin-bottom:8px}}
.asset-scenes{{font-size:.72rem;color:#8a8278;margin:2px 0}}
.asset-prompt{{background:rgba(140,64,192,0.06);border:1px solid rgba(140,64,192,0.15);border-radius:3px;padding:6px 10px;margin-top:4px}}
.asset-prompt code{{font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#b080d0;word-break:break-word}}
.auto-gen{{font-size:.72rem;color:#555;font-style:italic}}
table{{width:100%;border-collapse:collapse;margin:10px 0}}th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #1a1a24;font-size:.82rem}}
th{{color:#8a8278;font-size:.7rem;text-transform:uppercase}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle}}
.ebox{{background:#13131a;border:1px solid #2a2520;border-radius:5px;padding:10px 14px;margin:10px 0}}
.ebox h3{{color:#FFD700;font-size:.85rem;margin-bottom:6px}}
.mb-section{{background:#13131a;border:1px solid #2a2520;border-radius:6px;padding:16px}}
.mb-section-title{{color:#FFD700;font-size:.95rem;margin-bottom:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.mb-tag{{font-family:'JetBrains Mono',monospace;font-size:.6rem;padding:2px 8px;border-radius:3px;text-transform:uppercase}}
.mb-tag-permanent{{background:rgba(210,160,32,0.15);color:#D4A020;border:1px solid rgba(210,160,32,0.3)}}
.mb-tag-setting{{background:rgba(70,136,232,0.15);color:#4688E8;border:1px solid rgba(70,136,232,0.3)}}
.mb-prompt-item{{background:#0e0e16;border:1px solid #1a1a24;border-radius:4px;padding:8px 12px;margin-bottom:6px}}
.mb-prompt-item.mb-setting{{border-left:2px solid #4688E8}}
.mb-prompt-item:not(.mb-setting){{border-left:2px solid #D4A020}}
.mb-prompt-num{{font-family:'JetBrains Mono',monospace;font-size:.65rem;color:#8a8278;margin-bottom:3px}}
.mb-prompt-text code{{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#b8b0a4;word-break:break-word}}
.vid-prompt-item{{background:#0e0e16;border:1px solid #1a1a24;border-radius:5px;padding:10px 14px;margin-bottom:8px}}
.vid-prompt-header{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px}}
.vid-prompt-text{{background:rgba(70,136,232,0.06);border:1px solid rgba(70,136,232,0.15);border-radius:3px;padding:8px 10px}}
.vid-prompt-text code{{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#7aa8d8;word-break:break-word}}
.ebox textarea{{width:100%;background:#0a0a0f;color:#e8e0d4;border:1px solid #2a2520;border-radius:3px;padding:8px;font-family:'JetBrains Mono',monospace;font-size:.7rem;resize:vertical;min-height:180px}}
</style>
</head>
<body>
<div class="wrap">
<h1>🎬 Production Planner</h1>
<p class="sub">{e(game.get("title",""))} — S{game.get("season",1)}E{game.get("episode",1)} · {stats["total_shots"]} shots · {stats["total_duration_min"]} · {stats["total_chars"]:,} chars</p>

<div class="metrics">
<div class="metric"><div class="mv">{stats["total_shots"]}</div><div class="ml">Shots</div></div>
<div class="metric"><div class="mv">{stats["total_duration_min"]}</div><div class="ml">Duration</div></div>
<div class="metric"><div class="mv">{stats["video_shots"]}</div><div class="ml">Video</div></div>
<div class="metric"><div class="mv">{stats["static_shots"]}</div><div class="ml">Static</div></div>
<div class="metric"><div class="mv">{stats["mixed_shots"]}</div><div class="ml">Mixed</div></div>
<div class="metric"><div class="mv">{stats["unique_assets"]}</div><div class="ml">Assets</div></div>
</div>

<div class="tabs">
<div class="tab active" onclick="showTab('shots')">📋 Shot List</div>
<div class="tab" onclick="showTab('assets')">🎨 Assets</div>
<div class="tab" onclick="showTab('tts')">🎙️ TTS</div>
<div class="tab" onclick="showTab('scores')">🏆 Scores</div>
<div class="tab" onclick="showTab('moodboard')">🎨 Moodboards</div>
<div class="tab" onclick="showTab('vidprompts')">🎥 Video Prompts</div>
<div class="tab" onclick="showTab('export')">📤 Export</div>
</div>

<div id="shots" class="panel active">
{scenes_html}
</div>

<div id="assets" class="panel">
<h2 style="color:#FFD700;font-size:1.1rem;margin-bottom:12px">Assets ({len(assets)})</h2>
{asset_html}
</div>

<div id="tts" class="panel">
<div class="metrics">
<div class="metric"><div class="mv">{stats["total_chars"]:,}</div><div class="ml">Total Chars</div></div>
<div class="metric"><div class="mv">{narrator_chars:,}</div><div class="ml">Narrator</div></div>
<div class="metric"><div class="mv">{think_chars:,}</div><div class="ml">Think</div></div>
<div class="metric"><div class="mv">{speak_chars:,}</div><div class="ml">Speak</div></div>
<div class="metric"><div class="mv">${stats["total_chars"]/1000*0.30:.2f}</div><div class="ml">Est. Cost</div></div>
</div>
<h3 style="color:#FFD700;font-size:.9rem">🧠 Model Voices</h3>
<table><tr><th>Model</th><th>Chars</th></tr>{model_rows}</table>
<h3 style="color:#FFD700;font-size:.9rem;margin-top:16px">🗣️ Character Voices</h3>
<table><tr><th>Character</th><th>Chars</th></tr>{char_rows}</table>
</div>

<div id="scores" class="panel">
<table><tr><th></th><th>Model</th><th>Character</th><th>Score</th></tr>{scores_rows}</table>
<p style="font-size:.8rem;color:#8a8278;margin-top:10px">
Det: Killer={det.get("correct_killer","?")}, Weapon={det.get("correct_weapon","?")}, Motive={det.get("correct_motive","?")} |
Killer: Evaded={killer.get("evaded","?")}, Frame={killer.get("framing_bonus","?")}
</p>
</div>

<div id="moodboard" class="panel">
<h2 style="color:#FFD700;font-size:1.1rem;margin-bottom:4px">🎨 Moodboard Prompts</h2>
<p style="font-size:.78rem;color:#8a8278;margin-bottom:16px">Generate these in Midjourney, curate the best into two moodboards, then apply their codes to all production prompts.</p>

<div class="mb-section">
<h3 class="mb-section-title">🏛️ Brand Moodboard — "The Lineup Look" <span class="mb-tag mb-tag-permanent">PERMANENT</span></h3>
<p style="font-size:.76rem;color:#8a8278;margin-bottom:10px">Defines the show's visual identity. Create once, use for every episode across all seasons. Dark, cinematic, gold-accented noir.</p>
{brand_prompts_html}
<div class="ebox" style="margin-top:12px"><h3>Copy all brand prompts</h3>
<textarea readonly>{e(brand_prompts_text)}</textarea></div>
</div>

<div class="mb-section" style="margin-top:24px">
<h3 class="mb-section-title">🗺️ Setting Moodboard — {e(game.get("title","This Story"))} <span class="mb-tag mb-tag-setting">PER STORY</span></h3>
<p style="font-size:.76rem;color:#8a8278;margin-bottom:10px">Captures the period, location, and atmosphere for this specific story. Create a new one for each setting.</p>
{setting_prompts_html}
<div class="ebox" style="margin-top:12px"><h3>Copy all setting prompts</h3>
<textarea readonly>{e(setting_prompts_text)}</textarea></div>
</div>

<div style="background:rgba(255,215,0,0.06);border:1px solid rgba(255,215,0,0.15);border-radius:5px;padding:12px;margin-top:20px">
<strong style="color:#FFD700;font-size:.85rem">Usage in Midjourney:</strong>
<p style="font-size:.78rem;color:#b8b0a4;margin-top:4px">
1. Generate all brand prompts → curate best ~8 images → create moodboard "The Lineup Brand" → note code<br>
2. Generate all setting prompts → curate best ~8 images → create moodboard for this story → note code<br>
3. Append both codes to every production prompt: <code style="color:#7aa8d8">your prompt here --p [brand_code] --p [setting_code]</code>
</p>
</div>
</div>

<div id="vidprompts" class="panel">
<h2 style="color:#FFD700;font-size:1.1rem;margin-bottom:12px">🎥 Video Generation Prompts ({sum(1 for s in shots if s["prompt"] and s["media"] in ("video","mixed"))})</h2>
<p style="font-size:.78rem;color:#8a8278;margin-bottom:16px">Run these in order. Each prompt = one clip. Shot number and scene noted for reference.</p>
{''.join(
    f'<div class="vid-prompt-item">'
    f'<div class="vid-prompt-header">'
    f'<span class="shot-num">#{s["shot_id"]}</span> '
    f'<span style="color:#FFD700">{e(s["scene"])}</span> '
    f'<span class="badge badge-{s["media"]}">{s["media"].upper()}</span> '
    f'<span class="shot-dur">{s["duration"]}s</span>'
    f'</div>'
    f'<div class="vid-prompt-text"><code>{e(s["prompt"])}</code></div>'
    f'</div>'
    for s in shots if s["prompt"] and s["media"] in ("video", "mixed")
)}
</div>

<div id="export" class="panel">
<div class="ebox"><h3>🎥 Video Prompts (copy all)</h3>
<textarea readonly>{e(all_vid)}</textarea></div>
<div class="ebox"><h3>🎨 Asset / Midjourney Prompts (copy all)</h3>
<textarea readonly>{e(all_mj)}</textarea></div>
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
    print(f"Shots: {stats['total_shots']} | Duration: {stats['total_duration_min']} | Video: {stats['video_shots']} | Static: {stats['static_shots']} | Mixed: {stats['mixed_shots']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_static_v2.py <transcript.json> [output.html]")
        sys.exit(1)
    transcript = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "planner.html"
    build_html(transcript, output)
