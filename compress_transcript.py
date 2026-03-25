#!/usr/bin/env python3
"""
The Lineup — Transcript Compressor
Post-run compression pass that:
1. Identifies long THINK/SPEAK outputs
2. Scans for downstream references to protect key details
3. Sends each long output back to its originating model for compression
4. Fixes think/speak bleed (strategic content in SPEAK, character content in THINK)

Usage: python compress_transcript.py <transcript.json> [output.json]
"""

import json
import os
import re
import sys
import time
import logging
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("compress")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_API_RETRIES = 3
API_RETRY_DELAY = 2

# Thresholds — outputs longer than these get compressed
THINK_CHAR_THRESHOLD = 250
SPEAK_CHAR_THRESHOLD = 200

# Target lengths for compression
THINK_TARGET = "1-3 sentences (under 200 characters)"
SPEAK_TARGET = "1-3 sentences (under 150 characters)"

# Minimum length to bother compressing (don't compress already-short outputs)
MIN_COMPRESS_LENGTH = 100


def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        log.error("OPENROUTER_API_KEY not set")
        sys.exit(1)
    return key


def call_model(model: str, messages: list[dict], api_key: str) -> str:
    """Quick API call for compression — low tokens, low temp."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,  # Low temp for faithful compression
        "max_tokens": 300,
    }
    
    for attempt in range(1, MAX_API_RETRIES + 1):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if content and content.strip():
                return content.strip()
            if attempt < MAX_API_RETRIES:
                time.sleep(API_RETRY_DELAY)
        except Exception as e:
            log.warning("API error for %s (attempt %d): %s", model, attempt, e)
            if attempt < MAX_API_RETRIES:
                time.sleep(API_RETRY_DELAY)
    return ""


# ---------------------------------------------------------------------------
# Reference scanner
# ---------------------------------------------------------------------------

def find_protected_phrases(source_text: str, downstream_texts: list[str]) -> list[str]:
    """Find phrases from source_text that are referenced in downstream outputs.
    
    Looks for:
    - Direct quotes (3+ word sequences that appear in both)
    - Named references (character names, locations, specific details)
    - Specific evidence mentions
    """
    protected = []
    source_lower = source_text.lower()
    
    # Extract meaningful phrases (3-6 word sequences) from source
    words = source_text.split()
    phrases_3 = [" ".join(words[i:i+3]) for i in range(len(words)-2)]
    phrases_4 = [" ".join(words[i:i+4]) for i in range(len(words)-3)]
    
    all_downstream = " ".join(downstream_texts).lower()
    
    # Check which phrases appear downstream
    for phrase in phrases_4 + phrases_3:
        clean = phrase.lower().strip(".,;:!?\"'()")
        if len(clean) < 15:  # skip very short phrases
            continue
        if clean in all_downstream:
            # This phrase was referenced — protect it
            if phrase not in protected:
                protected.append(phrase)
    
    # Also protect specific evidence keywords
    evidence_words = [
        "knife", "excavation", "coat", "fabric", "lining", "torch",
        "corridor", "antechamber", "burial chamber", "sarcophagus",
        "blackmail", "ledger", "note", "boot prints", "polish",
        "prayer", "praying", "Bible", "pistol", "derringer",
        "camera", "scarab", "hieroglyph", "translation",
    ]
    
    for word in evidence_words:
        if word in source_lower:
            # Check if downstream references this same word
            if word in all_downstream:
                # Find the sentence containing this word in source
                for sentence in re.split(r'[.!?]+', source_text):
                    if word in sentence.lower() and sentence.strip():
                        if sentence.strip() not in protected:
                            protected.append(sentence.strip())
                        break
    
    return protected[:5]  # Cap at 5 protected phrases to keep prompt manageable


# ---------------------------------------------------------------------------
# Think/Speak bleed detector
# ---------------------------------------------------------------------------

def detect_bleed(think: str, speak: str) -> dict:
    """Detect if strategic content bled into SPEAK or character content into THINK."""
    issues = {"think_in_speak": False, "speak_in_think": False}
    
    speak_lower = speak.lower()
    think_lower = think.lower()
    
    # Strategic language that shouldn't be in SPEAK
    strategic_markers = [
        r"my strategy", r"i need to", r"i should", r"i must",
        r"deflect\w* suspicion", r"redirect\w*", r"frame\w*",
        r"scoring", r"points", r"competition", r"competing",
        r"the audience", r"the viewer", r"this game",
        r"as an ai", r"my model", r"benchmark",
        r"\[think\]", r"\[speak\]",  # literal tags leaked
    ]
    
    for pattern in strategic_markers:
        if re.search(pattern, speak_lower):
            issues["think_in_speak"] = True
            break
    
    # Character/in-world language that shouldn't be in THINK
    character_markers = [
        r"\"[^\"]{20,}\"",  # long quoted dialogue
        r"good sir", r"my lord", r"detective",
        r"ladies and gentlemen", r"i assure you",
    ]
    
    # This is less critical — some character voice in think is fine
    # Only flag if THINK reads like pure dialogue with no strategy
    
    return issues


# ---------------------------------------------------------------------------
# Compression prompts
# ---------------------------------------------------------------------------

def build_compress_prompt(text: str, output_type: str, protected: list[str], 
                         has_bleed: bool, character_name: str = "") -> str:
    """Build the compression prompt."""
    
    target = THINK_TARGET if output_type == "think" else SPEAK_TARGET
    
    protected_instruction = ""
    if protected:
        phrases = "\n".join(f"  - \"{p}\"" for p in protected)
        protected_instruction = f"\nYou MUST preserve these key details (other characters reference them later):\n{phrases}\n"
    
    bleed_instruction = ""
    if has_bleed and output_type == "speak":
        bleed_instruction = ("\nIMPORTANT: The original contains strategic/meta reasoning that should NOT be in character dialogue. "
                           "Remove any references to strategy, game mechanics, scoring, or AI competition. "
                           "Keep ONLY what the character would actually say out loud in the scene.")
    
    if output_type == "think":
        role_desc = ("This is a private [THINK] section — the AI model's strategic reasoning. "
                    "The audience sees this but other characters don't. "
                    "Keep it strategic, direct, and analytical.")
        if has_bleed:
            bleed_instruction = ("\nIMPORTANT: Remove any in-character dialogue or flowery language. "
                               "This should read as pure strategy, not performance.")
    else:
        role_desc = (f"This is a [SPEAK] section — what the character {character_name} says out loud in the scene. "
                    "Other characters hear and respond to this. "
                    "Keep it in character, natural, and dramatic.")
    
    return f"""Compress the following text to {target}. {role_desc}
{protected_instruction}{bleed_instruction}
ORIGINAL:
{text}

COMPRESSED (respond with ONLY the compressed text, nothing else):"""


# ---------------------------------------------------------------------------
# Main compressor
# ---------------------------------------------------------------------------

def extract_all_outputs(transcript: dict) -> list[dict]:
    """Extract every think/speak output from the transcript with metadata."""
    outputs = []
    t = transcript.get("transcript", {})
    assignments = transcript.get("model_assignments", {})
    
    # Build model lookup
    suspect_models = {}
    for s in assignments.get("suspects", []):
        suspect_models[s["character"]] = s.get("model", "")
    det_model = assignments.get("detective", {}).get("model", "")
    
    def add(section, index, field, text, model, character, output_type):
        if text and len(text.strip()) > 0:
            outputs.append({
                "section": section,
                "index": index,
                "field": field,
                "text": text.strip(),
                "model": model,
                "character": character,
                "type": output_type,
                "chars": len(text.strip()),
            })
    
    # Round 2
    for i, entry in enumerate(t.get("round_2_statements", [])):
        model = suspect_models.get(entry["character"], "")
        add("round_2_statements", i, "think", entry.get("think", ""), model, entry["character"], "think")
        add("round_2_statements", i, "speak", entry.get("speak", ""), model, entry["character"], "speak")
    
    # Round 3
    for i, conf in enumerate(t.get("round_3_suspicion", [])):
        tgt = conf.get("target", "")
        chl = conf.get("challenger", "")
        add("round_3_suspicion", i, "target_think", conf.get("target_think", ""), suspect_models.get(tgt, ""), tgt, "think")
        add("round_3_suspicion", i, "target_speak", conf.get("target_speak", ""), suspect_models.get(tgt, ""), tgt, "speak")
        add("round_3_suspicion", i, "challenger_think", conf.get("challenger_think", ""), suspect_models.get(chl, ""), chl, "think")
        add("round_3_suspicion", i, "challenger_speak", conf.get("challenger_speak", ""), suspect_models.get(chl, ""), chl, "speak")
    
    # Detective processing
    dp = t.get("detective_processing", {})
    if dp:
        add("detective_processing", 0, "think", dp.get("think", ""), det_model, "Detective", "think")
    
    # Round 4
    for i, ex in enumerate(t.get("round_4_investigation", {}).get("exchanges", [])):
        add("round_4_investigation", i, "detective_think", ex.get("detective_think", ""), det_model, "Detective", "think")
        add("round_4_investigation", i, "detective_speak", ex.get("detective_speak", ""), det_model, "Detective", "speak")
        sus = ex.get("suspect_character", "")
        add("round_4_investigation", i, "suspect_think", ex.get("suspect_think", ""), suspect_models.get(sus, ""), sus, "think")
        add("round_4_investigation", i, "suspect_speak", ex.get("suspect_speak", ""), suspect_models.get(sus, ""), sus, "speak")
    
    # Round 5 final statements
    for i, entry in enumerate(t.get("round_5_final_statements", [])):
        model = suspect_models.get(entry["character"], "")
        add("round_5_final_statements", i, "think", entry.get("think", ""), model, entry["character"], "think")
        add("round_5_final_statements", i, "speak", entry.get("speak", ""), model, entry["character"], "speak")
    
    # Accusation
    acc = t.get("round_5_accusation", {})
    if acc:
        add("round_5_accusation", 0, "detective_think", acc.get("detective_think", ""), det_model, "Detective", "think")
        add("round_5_accusation", 0, "detective_speak", acc.get("detective_speak", ""), det_model, "Detective", "speak")
    
    # Accused response
    ar = t.get("round_5_accused_response")
    if ar:
        model = suspect_models.get(ar["character"], "")
        add("round_5_accused_response", 0, "think", ar.get("think", ""), model, ar["character"], "think")
        add("round_5_accused_response", 0, "speak", ar.get("speak", ""), model, ar["character"], "speak")
    
    # Reactions
    for i, entry in enumerate(t.get("round_5_reactions", [])):
        model = suspect_models.get(entry["character"], "")
        add("round_5_reactions", i, "think", entry.get("think", ""), model, entry["character"], "think")
        add("round_5_reactions", i, "speak", entry.get("speak", ""), model, entry["character"], "speak")
    
    return outputs


def compress_transcript(transcript_path: str, output_path: str):
    """Main compression pipeline."""
    api_key = get_api_key()
    
    with open(transcript_path) as f:
        data = json.load(f)
    
    log.info("Loaded transcript: %s", transcript_path)
    
    # Extract all outputs
    outputs = extract_all_outputs(data)
    all_texts = [o["text"] for o in outputs]
    
    log.info("Total outputs: %d", len(outputs))
    
    # Identify what needs compression
    needs_compression = []
    for i, out in enumerate(outputs):
        threshold = THINK_CHAR_THRESHOLD if out["type"] == "think" else SPEAK_CHAR_THRESHOLD
        if out["chars"] > threshold and out["chars"] > MIN_COMPRESS_LENGTH:
            needs_compression.append(i)
    
    # Identify bleed issues (even in short outputs)
    needs_bleed_fix = []
    for i, out in enumerate(outputs):
        if out["type"] == "speak" and out["text"]:
            # Find corresponding think
            think_text = ""
            for j, other in enumerate(outputs):
                if (other["section"] == out["section"] and 
                    other["index"] == out["index"] and 
                    other["type"] == "think"):
                    think_text = other["text"]
                    break
            
            bleed = detect_bleed(think_text, out["text"])
            if bleed["think_in_speak"]:
                if i not in needs_compression:
                    needs_bleed_fix.append(i)
    
    all_to_fix = sorted(set(needs_compression + needs_bleed_fix))
    
    log.info("Need compression: %d outputs (threshold: think>%d, speak>%d)",
             len(needs_compression), THINK_CHAR_THRESHOLD, SPEAK_CHAR_THRESHOLD)
    log.info("Need bleed fix: %d outputs", len(needs_bleed_fix))
    log.info("Total to process: %d", len(all_to_fix))
    
    # Process each
    compressed_count = 0
    bleed_fixed = 0
    chars_saved = 0
    
    for idx in all_to_fix:
        out = outputs[idx]
        
        # Get downstream texts for reference protection
        downstream = [o["text"] for o in outputs[idx+1:idx+10] if o["text"]]
        protected = find_protected_phrases(out["text"], downstream)
        
        # Check for bleed
        has_bleed = idx in needs_bleed_fix or (
            out["type"] == "speak" and detect_bleed("", out["text"])["think_in_speak"]
        )
        
        # Build compression prompt
        prompt = build_compress_prompt(
            out["text"], out["type"], protected, has_bleed, out["character"]
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        # Call the originating model
        model = out["model"]
        if not model:
            log.warning("No model for output %d — skipping", idx)
            continue
        
        log.info("  Compressing [%s] %s/%d/%s (%d chars) via %s%s",
                 out["type"], out["section"], out["index"], out["field"],
                 out["chars"], model.split("/")[-1],
                 " +bleed_fix" if has_bleed else "")
        
        result = call_model(model, messages, api_key)
        
        if result and len(result) < out["chars"]:
            old_chars = out["chars"]
            
            # Clean up any stray formatting from the model
            result = result.strip()
            result = re.sub(r'^\[?(THINK|SPEAK)\]?\s*:?\s*', '', result, flags=re.IGNORECASE)
            result = result.strip('"')
            
            # Update the transcript
            t = data["transcript"]
            section = out["section"]
            index = out["index"]
            field = out["field"]
            
            if section in ("round_2_statements", "round_5_final_statements", "round_5_reactions"):
                t[section][index][field] = result
            elif section == "round_3_suspicion":
                t[section][index][field] = result
            elif section == "detective_processing":
                t[section][field] = result
            elif section == "round_4_investigation":
                t[section]["exchanges"][index][field] = result
            elif section == "round_5_accusation":
                t[section][field] = result
            elif section == "round_5_accused_response":
                t[section][field] = result
            
            saved = old_chars - len(result)
            chars_saved += saved
            compressed_count += 1
            if has_bleed:
                bleed_fixed += 1
            
            log.info("    %d → %d chars (saved %d)", old_chars, len(result), saved)
        else:
            log.warning("    Compression failed or didn't reduce length")
        
        time.sleep(0.3)  # Rate limit courtesy
    
    # Save compressed transcript
    data["compression"] = {
        "compressed": True,
        "outputs_processed": len(all_to_fix),
        "outputs_compressed": compressed_count,
        "bleed_fixes": bleed_fixed,
        "characters_saved": chars_saved,
    }
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    log.info("=" * 60)
    log.info("COMPRESSION COMPLETE")
    log.info("  Outputs processed: %d", len(all_to_fix))
    log.info("  Successfully compressed: %d", compressed_count)
    log.info("  Bleed fixes: %d", bleed_fixed)
    log.info("  Characters saved: %d", chars_saved)
    log.info("  Output: %s", output_path)
    log.info("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compress_transcript.py <transcript.json> [output.json]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.replace(".json", "_compressed.json")
    compress_transcript(input_path, output_path)
