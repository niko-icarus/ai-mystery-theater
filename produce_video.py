#!/usr/bin/env python3
"""
AI Mystery Theater — Video Producer
Takes a transcript and produces a narrated video with distinct character voices.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from elevenlabs import ElevenLabs

# Config
API_KEY = os.environ.get("ELEVEN_LABS_API_KEY", "")
OUTPUT_DIR = Path(__file__).parent / "production"
OUTPUT_DIR.mkdir(exist_ok=True)

WIDTH, HEIGHT = 1920, 1080

# Voice assignments (character -> voice_id)
VOICES = {
    "narrator": "JBFqnCBsd6RMkjVDRZzb",       # George - Warm British Storyteller
    "detective": "onwK4e9ZLuTAKqWW03F9",        # Daniel - Steady Broadcaster, British formal
    "lady margaret thornfield": "pFZP5JQG7iQjIQuC4Bku",  # Lily - Velvety British Actress
    "captain james ashworth": "CwhRBWXzGAHq8TQ4Fs17",    # Roger - Laid-Back
    "dr. harold pembrooke": "pqHfZKP75CvOlQylNhV4",      # Bill - Wise, Mature
    "miss victoria thornfield": "Xb7hH8MSUJpSbSDYk0k2",  # Alice - Clear British
    "mr. reginald cross": "nPczCjzI2devNBz1zQrb",        # Brian - Deep, Resonant
}

# Character colors
COLORS = {
    "narrator": "#e0c097",
    "detective": "#4fc3f7",
    "lady margaret thornfield": "#f48fb1",
    "captain james ashworth": "#81c784",
    "dr. harold pembrooke": "#ffb74d",
    "miss victoria thornfield": "#ce93d8",
    "mr. reginald cross": "#90a4ae",
}

# Character display names
DISPLAY_NAMES = {
    "narrator": "📖 NARRATOR",
    "detective": "🔍 THE DETECTIVE",
    "lady margaret thornfield": "👗 LADY MARGARET THORNFIELD",
    "captain james ashworth": "⚔️ CAPTAIN JAMES ASHWORTH",
    "dr. harold pembrooke": "💊 DR. HAROLD PEMBROOKE",
    "miss victoria thornfield": "🌹 MISS VICTORIA THORNFIELD",
    "mr. reginald cross": "📋 MR. REGINALD CROSS",
}

MODEL = "eleven_flash_v2_5"


def get_font(size):
    """Get a font, falling back to default."""
    for name in ["Helvetica", "Arial", "DejaVuSans"]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            pass
    # Try system paths
    for path in ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/SFNSMono.ttf",
                 "/Library/Fonts/Arial.ttf"]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    return ImageFont.load_default()


def wrap_text(text, font, max_width, draw):
    """Word-wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def create_card_image(speaker, text, output_path):
    """Create a styled character card."""
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(20, 20, 35))
    draw = ImageDraw.Draw(img)
    
    name_color = COLORS.get(speaker, "#e0c097")
    display_name = DISPLAY_NAMES.get(speaker, speaker.upper())
    
    # Decorative top/bottom borders
    draw.rectangle([(0, 0), (WIDTH, 4)], fill=name_color)
    draw.rectangle([(0, HEIGHT - 4), (WIDTH, HEIGHT)], fill=name_color)
    
    # Character name
    name_font = get_font(56)
    bbox = draw.textbbox((0, 0), display_name, font=name_font)
    name_w = bbox[2] - bbox[0]
    draw.text(((WIDTH - name_w) // 2, 200), display_name, fill=name_color, font=name_font)
    
    # Divider line
    draw.rectangle([(WIDTH // 4, 290), (3 * WIDTH // 4, 292)], fill=name_color)
    
    # Dialogue text (wrapped)
    text_font = get_font(36)
    lines = wrap_text(text, text_font, WIDTH - 300, draw)
    y = 340
    for line in lines[:12]:  # Max 12 lines
        bbox = draw.textbbox((0, 0), line, font=text_font)
        line_w = bbox[2] - bbox[0]
        draw.text(((WIDTH - line_w) // 2, y), line, fill="#cccccc", font=text_font)
        y += 50
    
    img.save(output_path)


def create_title_image(text, output_path, subtitle=""):
    """Create title/credits card."""
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(10, 10, 25))
    draw = ImageDraw.Draw(img)
    
    # Gold border
    draw.rectangle([(40, 40), (WIDTH - 40, HEIGHT - 40)], outline="#e0c097", width=2)
    
    # Title
    title_font = get_font(64)
    lines = text.split('\n')
    y = HEIGHT // 3
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_w = bbox[2] - bbox[0]
        draw.text(((WIDTH - line_w) // 2, y), line, fill="#e0c097", font=title_font)
        y += 80
    
    if subtitle:
        sub_font = get_font(32)
        sub_lines = subtitle.split('\n')
        y += 40
        for line in sub_lines:
            bbox = draw.textbbox((0, 0), line, font=sub_font)
            line_w = bbox[2] - bbox[0]
            draw.text(((WIDTH - line_w) // 2, y), line, fill="#888888", font=sub_font)
            y += 50
    
    img.save(output_path)


def parse_transcript(filepath):
    """Parse a mystery theater transcript into segments."""
    segments = []
    content = Path(filepath).read_text()
    lines = content.strip().split('\n')
    
    current_section = ""
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('## '):
            current_section = line[3:].strip()
            if current_section in ["Evidence Reveal", "Cross Examination", "Parlor Scene", "Reveal"]:
                segments.append({
                    "speaker": "narrator",
                    "text": f"{current_section}.",
                    "type": "section_header"
                })
            i += 1
            continue
        
        match = re.match(r'\*\*(\w[\w\s\'.]+?)\*\*:\s*(.*)', line)
        if match:
            speaker = match.group(1).strip().lower()
            text = match.group(2).strip()
            
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('**') and not lines[i].strip().startswith('## '):
                text += " " + lines[i].strip()
                i += 1
            
            if text.startswith('*💭') or text.startswith('*I '):
                continue
            
            text = re.sub(r'\*[^*]+\*', '', text).strip()
            
            if speaker == "result":
                continue
            
            if text:
                segments.append({
                    "speaker": speaker,
                    "text": text,
                    "type": "dialogue",
                    "section": current_section
                })
            continue
        
        i += 1
    
    return segments


def generate_audio(client, segments, output_dir):
    """Generate TTS audio for each segment."""
    audio_files = []
    total_chars = 0
    
    for idx, seg in enumerate(segments):
        speaker = seg["speaker"]
        text = seg["text"]
        total_chars += len(text)
        
        voice_id = VOICES.get(speaker, VOICES["narrator"])
        outfile = output_dir / f"seg_{idx:03d}_{speaker.replace(' ', '_')[:20]}.mp3"
        
        if outfile.exists() and outfile.stat().st_size > 100:
            print(f"  [SKIP] {outfile.name}")
            audio_files.append(outfile)
            continue
        
        print(f"  [{idx+1}/{len(segments)}] {speaker}: {text[:60]}...")
        
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=MODEL,
            output_format="mp3_44100_128",
        )
        
        with open(outfile, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        
        audio_files.append(outfile)
    
    print(f"\n  Total characters: {total_chars}")
    return audio_files


def get_audio_duration(filepath):
    """Get duration of an audio file in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(filepath)],
        capture_output=True, text=True
    )
    val = result.stdout.strip()
    return float(val) if val else 3.0


def assemble_video(segments, audio_files, output_dir, title="Murder at Thornfield Manor"):
    """Assemble final video from audio segments with character cards."""
    
    video_parts = []
    
    # Title card (5 seconds, silent)
    title_img = output_dir / "title.png"
    create_title_image("AI MYSTERY THEATER", title_img, subtitle=title)
    title_vid = output_dir / "title.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(title_img),
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-t", "5",
        str(title_vid)
    ], capture_output=True)
    
    if title_vid.exists():
        video_parts.append(title_vid)
        print("  Title card: 5.0s")
    
    for idx, (seg, audio_path) in enumerate(zip(segments, audio_files)):
        duration = get_audio_duration(audio_path)
        
        # Create character card
        card_img = output_dir / f"card_{idx:03d}.png"
        create_card_image(seg["speaker"], seg["text"], card_img)
        
        # Combine card + audio
        part_vid = output_dir / f"part_{idx:03d}.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(card_img),
            "-i", str(audio_path),
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(duration + 0.8),
            str(part_vid)
        ], capture_output=True)
        
        if part_vid.exists():
            video_parts.append(part_vid)
            print(f"  Part {idx+1}/{len(segments)}: {duration:.1f}s — {seg['speaker']}")
        else:
            print(f"  ⚠️ FAILED: part {idx+1}")
    
    # Credits
    credits_img = output_dir / "credits.png"
    create_title_image("AI MYSTERY THEATER", credits_img,
                       subtitle="Powered by AI agents playing characters\nClaude as Detective\nMultiple AI suspects\n\nSubscribe for more mysteries!")
    credits_vid = output_dir / "credits.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(credits_img),
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-t", "6",
        str(credits_vid)
    ], capture_output=True)
    
    if credits_vid.exists():
        video_parts.append(credits_vid)
        print("  Credits: 6.0s")
    
    # Concatenate
    concat_file = output_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for part in video_parts:
            f.write(f"file '{part}'\n")
    
    final_output = output_dir / f"{title.lower().replace(' ', '_')}_final.mp4"
    result = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(final_output)
    ], capture_output=True, text=True)
    
    if final_output.exists():
        dur = get_audio_duration(final_output)
        size_mb = final_output.stat().st_size / (1024 * 1024)
        print(f"\n✅ Final video: {final_output}")
        print(f"📏 Duration: {dur:.0f}s ({dur/60:.1f} min)")
        print(f"📦 Size: {size_mb:.1f} MB")
    else:
        print(f"\n❌ Final concat failed!")
        print(result.stderr[-500:] if result.stderr else "No error output")
    
    return final_output


def main():
    transcript = sys.argv[1] if len(sys.argv) > 1 else "transcripts/2026-02-16_102544_murder_at_thornfield_manor.md"
    
    print("🎭 AI Mystery Theater — Video Producer")
    print("=" * 50)
    
    print("\n📝 Parsing transcript...")
    segments = parse_transcript(transcript)
    print(f"   Found {len(segments)} segments")
    
    total_chars = sum(len(s["text"]) for s in segments)
    print(f"   Total characters: {total_chars}")
    
    for s in segments:
        print(f"   [{s['speaker']:30s}] {s['text'][:70]}...")
    
    print("\n🔊 Generating TTS audio...")
    client = ElevenLabs(api_key=API_KEY)
    audio_files = generate_audio(client, segments, OUTPUT_DIR)
    
    print("\n🎬 Assembling video...")
    final = assemble_video(segments, audio_files, OUTPUT_DIR)
    
    return final


if __name__ == "__main__":
    main()
