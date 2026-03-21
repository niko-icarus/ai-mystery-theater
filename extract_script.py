#!/usr/bin/env python3
"""Extract a TTS-ready script from a Lineup game transcript.

Takes the full transcript JSON and strips it down to speakable dialogue
suitable for ElevenLabs TTS. Target: ~12-15K characters per game.

Usage:
    python extract_script.py transcripts/s01e01_20260321_001832.json
    python extract_script.py transcripts/s01e01_20260321_001832.json --target 12000
"""

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def strip_stage_directions(text: str) -> str:
    """Remove *italicized stage directions* like *adjusts collar*."""
    # Remove standalone stage direction lines
    text = re.sub(r'^\*[^*]+\*\s*$', '', text, flags=re.MULTILINE)
    # Remove inline stage directions
    text = re.sub(r'\*[^*]+\*\s*', '', text)
    return text.strip()


def strip_character_prefix(text: str, speakers: list[str]) -> str:
    """Remove cases where a model prefixes with its own name or [Name]:."""
    for name in speakers:
        # [Name]: or [Name] — at the start
        text = re.sub(rf'^\[{re.escape(name)}\]:?\s*', '', text, flags=re.IGNORECASE)
        # Name: at the very start
        text = re.sub(rf'^{re.escape(name)}:\s*', '', text, flags=re.IGNORECASE)
        # Also check last name only
        last = name.split()[-1]
        text = re.sub(rf'^\[{re.escape(last)}\]:?\s*', '', text, flags=re.IGNORECASE)
    # Also strip [Detective]: prefix
    text = re.sub(r'^\[Detective\]:?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\[Narrator\]:?\s*', '', text, flags=re.IGNORECASE)
    return text.strip()


def strip_detective_analysis(text: str) -> str:
    """Remove internal analysis paragraphs (numbered lists, recap summaries)."""
    # Remove numbered analysis lists like "1. **Hessler's Alibi**: ..."
    text = re.sub(r'^\d+\.\s+\*\*[^*]+\*\*:?\s*.*$', '', text, flags=re.MULTILINE)
    # Remove markdown bold headers
    text = re.sub(r'^\*\*[^*]+\*\*:?\s*$', '', text, flags=re.MULTILINE)
    # Clean up multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def clean_for_tts(text: str) -> str:
    """Final cleanup for TTS — remove markdown, excessive punctuation."""
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    # Remove markdown headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove [THINKING] blocks
    text = re.sub(r'\[THINKING[^\]]*\]', '', text, flags=re.IGNORECASE)
    # Clean excessive whitespace
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Scene/opening condensation
# ---------------------------------------------------------------------------

def condense_opening(text: str) -> str:
    """Condense the narrator opening to essential info only.
    
    Keeps: location name, crime summary, victim, cause of death, suspect names.
    Cuts: atmospheric descriptions, room lists, detailed backgrounds.
    """
    lines = text.split('\n')
    keep_lines = []
    skip_section = False
    
    for line in lines:
        stripped = line.strip()
        
        # Always keep the welcome line
        if 'Welcome to The Lineup' in stripped:
            keep_lines.append(stripped)
            continue
        
        # Keep location name but trim description
        if stripped.startswith('LOCATION:'):
            # Just keep the location name, first sentence
            loc_parts = stripped.split('\n')[0]
            first_sentence = loc_parts.split('.')[0] + '.'
            keep_lines.append(first_sentence)
            continue
        
        # Keep crime header and victim info
        if stripped.startswith('THE CRIME:'):
            # Keep first two sentences
            sentences = re.split(r'(?<=[.!?])\s+', stripped)
            keep_lines.append(' '.join(sentences[:2]))
            continue
        
        if stripped.startswith('Cause of death:'):
            keep_lines.append(stripped)
            continue
        
        # For suspect intros, keep just name and role
        if stripped.startswith('•') and '—' in stripped:
            parts = stripped.split('—')
            if len(parts) >= 2:
                name = parts[0].strip()
                role = parts[1].split('.')[0].strip()
                keep_lines.append(f'{name}— {role}.')
            continue
        
        # Keep section headers
        if stripped in ('THE SUSPECTS:', 'OPENING CLUES:'):
            keep_lines.append(stripped)
            continue
        
        # Keep clues (bullet points under OPENING CLUES)
        if stripped.startswith('•') and 'CLUE' not in stripped and '—' not in stripped:
            keep_lines.append(stripped)
            continue
        
        # Keep the investigation prompt
        if 'begin your investigation' in stripped.lower():
            keep_lines.append(stripped)
            continue
    
    return '\n'.join(keep_lines)


# ---------------------------------------------------------------------------
# Script extraction
# ---------------------------------------------------------------------------

def is_redundant_narrator(content: str) -> bool:
    """Check if a narrator message is just a system nudge, not content."""
    nudges = [
        'please address a specific suspect',
        'you have already used all',
        'you must conduct a more thorough',
        'available suspects:',
    ]
    content_lower = content.lower()
    return any(nudge in content_lower for nudge in nudges)


def is_detective_recap(content: str) -> bool:
    """Check if detective message is internal analysis rather than a question."""
    indicators = [
        'let me analyze',
        'let me summarize',
        'here are the key points',
        'i have gathered information',
        'key observations',
        'with all the gathered',
        'having gathered this',
        'i have established a baseline',
        'initial accounts are in',
        'this concludes',
        'now to collate',
    ]
    content_lower = content.lower()[:200]  # Check first 200 chars
    return any(ind in content_lower for ind in indicators)


def extract_script(transcript_path: str, target_chars: int = 15000) -> dict:
    """Extract a TTS-ready script from a full transcript."""
    
    with open(transcript_path) as f:
        data = json.load(f)
    
    transcript = data['transcript']
    scores = data['scores']
    game = data['game']
    
    # Collect all speaker names for prefix stripping
    speakers = ['Narrator', 'Detective']
    for entry in transcript:
        if entry['speaker'] not in speakers:
            speakers.append(entry['speaker'])
    
    script_segments = []
    
    # Track which suspects have had key exchanges included
    suspect_exchanges = {}  # suspect_name -> count of included exchanges
    
    for i, entry in enumerate(transcript):
        speaker = entry['speaker']
        content = entry['content']
        role_type = entry['role_type']
        
        # --- NARRATOR ---
        if role_type == 'narrator':
            # Skip system nudges
            if is_redundant_narrator(content):
                continue
            
            # Opening scene — condense
            if i == 0 or 'Welcome to The Lineup' in content:
                condensed = condense_opening(content)
                condensed = clean_for_tts(condensed)
                script_segments.append({
                    'speaker': 'Narrator',
                    'content': condensed,
                    'type': 'opening'
                })
                continue
            
            # Evidence clues — keep
            if 'Evidence Clue' in content or 'Evidence Drop' in content:
                cleaned = strip_stage_directions(content)
                cleaned = clean_for_tts(cleaned)
                script_segments.append({
                    'speaker': 'Narrator',
                    'content': cleaned,
                    'type': 'evidence'
                })
                continue
            
            # Accusation prompt — keep but trim
            if 'made their accusation' in content.lower():
                script_segments.append({
                    'speaker': 'Narrator',
                    'content': 'The detective has made their accusation.',
                    'type': 'transition'
                })
                continue
            
            # Reveal — keep
            if 'THE TRUTH REVEALED' in content:
                # Trim the scoring JSON from the reveal
                reveal_text = content.split('SCORING:')[0].strip()
                reveal_text = clean_for_tts(reveal_text)
                script_segments.append({
                    'speaker': 'Narrator',
                    'content': reveal_text,
                    'type': 'reveal'
                })
                continue
            
            # Skip other narrator messages (force-accusation prompts, etc.)
            continue
        
        # --- DETECTIVE ---
        if role_type == 'detective':
            content = strip_stage_directions(content)
            content = strip_character_prefix(content, speakers)
            content = clean_for_tts(content)
            
            # Skip internal analysis/recaps
            if is_detective_recap(content):
                continue
            
            # Accusation — always keep
            if 'I MAKE MY ACCUSATION' in entry['content'].upper():
                content = strip_detective_analysis(content)
                content = clean_for_tts(content)
                script_segments.append({
                    'speaker': 'Detective',
                    'content': content,
                    'type': 'accusation'
                })
                continue
            
            # Regular questions — keep
            script_segments.append({
                'speaker': 'Detective',
                'content': content,
                'type': 'question'
            })
            continue
        
        # --- SUSPECTS ---
        if role_type == 'suspect':
            content = strip_stage_directions(content)
            content = strip_character_prefix(content, speakers)
            content = clean_for_tts(content)
            
            if not content or content == '[No response]' or 'Model unavailable' in content:
                continue
            
            script_segments.append({
                'speaker': speaker,
                'content': content,
                'type': 'response'
            })
            continue
    
    # --- TRIM TO TARGET ---
    total_chars = sum(len(s['content']) for s in script_segments)
    
    # Step 1: Always trim detective preambles
    trimmed = []
    for seg in script_segments:
        if seg['type'] == 'question':
            content = seg['content']
            # Remove "Let me question/follow up/interrupt" preambles
            content = re.sub(
                r'^(Let me|I\'ll|I need to|I want to|I apologize|I believe|Thank you|My apologies|I understand|I see|I appreciate|I cannot|I seem|I am being|I have heard|Given the)[^.!?]*[.!?]\s*',
                '', content, flags=re.IGNORECASE
            )
            # Remove "Next, I'll" preambles
            content = re.sub(
                r'^(Next|Now|Finally|Having|Given|With|This is|It appears)[^:]*:\s*', '', content, flags=re.IGNORECASE
            )
            content = content.strip()
            if content:
                seg['content'] = content
                trimmed.append(seg)
        else:
            trimmed.append(seg)
    script_segments = trimmed
    total_chars = sum(len(s['content']) for s in script_segments)
    
    # Step 2: If still over target, limit exchanges per suspect
    if total_chars > target_chars:
        # Keep max 3 best exchanges per suspect (shortest question + response pairs)
        suspect_counts = {}
        filtered = []
        for seg in script_segments:
            if seg['type'] in ('opening', 'evidence', 'accusation', 'reveal', 'transition'):
                filtered.append(seg)
            elif seg['type'] == 'question':
                filtered.append(seg)
            elif seg['type'] == 'response':
                count = suspect_counts.get(seg['speaker'], 0)
                if count < 3:
                    filtered.append(seg)
                    suspect_counts[seg['speaker']] = count + 1
                # else skip — too many responses from this suspect
        script_segments = filtered
        total_chars = sum(len(s['content']) for s in script_segments)
    
    # Step 3: If still over target, truncate long responses
    if total_chars > target_chars:
        for seg in script_segments:
            if seg['type'] == 'response' and len(seg['content']) > 300:
                # Keep first 2 sentences
                sentences = re.split(r'(?<=[.!?])\s+', seg['content'])
                seg['content'] = ' '.join(sentences[:2])
            elif seg['type'] == 'question' and len(seg['content']) > 200:
                sentences = re.split(r'(?<=[.!?])\s+', seg['content'])
                seg['content'] = ' '.join(sentences[:2])
        total_chars = sum(len(s['content']) for s in script_segments)
    
    # Step 4: If STILL over target, remove orphaned questions (no response follows)
    if total_chars > target_chars:
        cleaned = []
        for i, seg in enumerate(script_segments):
            if seg['type'] == 'question':
                # Check if next segment is a response
                if i + 1 < len(script_segments) and script_segments[i + 1]['type'] == 'response':
                    cleaned.append(seg)
                # else skip orphaned question
            else:
                cleaned.append(seg)
        script_segments = cleaned
        total_chars = sum(len(s['content']) for s in script_segments)
    
    # Build the final script
    script_lines = []
    for seg in script_segments:
        script_lines.append(f"[{seg['speaker']}]\n{seg['content']}\n")
    
    script_text = '\n'.join(script_lines)
    
    # Stats
    char_counts = {}
    for seg in script_segments:
        char_counts[seg['speaker']] = char_counts.get(seg['speaker'], 0) + len(seg['content'])
    
    result = {
        'game': game,
        'script': script_text,
        'segments': script_segments,
        'stats': {
            'total_characters': total_chars,
            'total_segments': len(script_segments),
            'estimated_minutes': round(total_chars / 900, 1),  # ~900 chars/min for speech
            'by_speaker': char_counts,
        },
        'scores': scores,
    }
    
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_script.py <transcript.json> [--target CHARS]")
        sys.exit(1)
    
    transcript_path = sys.argv[1]
    target = 15000
    
    if '--target' in sys.argv:
        idx = sys.argv.index('--target')
        target = int(sys.argv[idx + 1])
    
    if not Path(transcript_path).exists():
        print(f"Error: {transcript_path} not found")
        sys.exit(1)
    
    result = extract_script(transcript_path, target)
    
    # Print stats
    stats = result['stats']
    print("=" * 50)
    print("TTS SCRIPT EXTRACTED")
    print("=" * 50)
    print(f"Total characters: {stats['total_characters']:,}")
    print(f"Total segments: {stats['total_segments']}")
    print(f"Estimated runtime: ~{stats['estimated_minutes']} minutes")
    print()
    print("By speaker:")
    for speaker, chars in sorted(stats['by_speaker'].items(), key=lambda x: -x[1]):
        print(f"  {speaker}: {chars:,}")
    print()
    
    # Save script
    out_path = Path(transcript_path).with_suffix('.script.txt')
    with open(out_path, 'w') as f:
        f.write(result['script'])
    print(f"Script saved: {out_path}")
    
    # Save script JSON (for video pipeline)
    json_path = Path(transcript_path).with_suffix('.script.json')
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Script JSON saved: {json_path}")


if __name__ == "__main__":
    main()
