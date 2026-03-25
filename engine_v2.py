#!/usr/bin/env python3
"""
The Lineup — Game Engine v2
Fixed structure, Think/Speak split, suspect-vs-suspect interaction.
See ENGINE_SPEC_V2.md for full specification.
"""

import json
import os
import re
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("lineup_v2")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_API_RETRIES = 3
API_RETRY_DELAY = 2

# Token caps for responses
THINK_MAX_TOKENS = 200
SPEAK_MAX_TOKENS = 150

# Round 3: 6 confrontations with 1 back-and-forth each
NUM_CONFRONTATIONS = 7

# Round 4: 5 detective questions, min 3 different suspects
NUM_DETECTIVE_QUESTIONS = 5
MIN_DIFFERENT_SUSPECTS = 3

# Temperature
DEFAULT_TEMPERATURE = 0.85

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------
SCORE_DETECTIVE_KILLER = 10
SCORE_DETECTIVE_WEAPON = 3
SCORE_DETECTIVE_MOTIVE = 3
SCORE_KILLER_EVADE = 10
SCORE_KILLER_FRAME = 5
SCORE_KILLER_MOB = 3
SCORE_INNOCENT_FINAL_CORRECT = 5
SCORE_INNOCENT_EARLY_CORRECT = 2  # per round
SCORE_INNOCENT_SURVIVAL = 2
SCORE_INNOCENT_FALSE_ACCUSED = -2

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        log.error("OPENROUTER_API_KEY not set")
        sys.exit(1)
    return key


def call_model(model: str, messages: list[dict], api_key: str, 
               temperature: float = DEFAULT_TEMPERATURE, max_tokens: int = 600) -> str:
    """Call OpenRouter with retry logic."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://thelineup.ai",
        "X-Title": "The Lineup",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(1, MAX_API_RETRIES + 1):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content and content.strip():
                return content.strip()
            log.warning("Empty response from %s (attempt %d)", model, attempt)
            if attempt < MAX_API_RETRIES:
                time.sleep(API_RETRY_DELAY * attempt)
        except requests.exceptions.RequestException as e:
            log.warning("API error for %s (attempt %d): %s", model, attempt, e)
            if attempt < MAX_API_RETRIES:
                time.sleep(API_RETRY_DELAY * attempt)
    return "[No response]"


# ---------------------------------------------------------------------------
# Think/Speak parser
# ---------------------------------------------------------------------------

def parse_think_speak(response: str) -> tuple[str, str]:
    """Parse a response into THINK and SPEAK sections.
    
    Handles many formats models produce:
    - [THINK] text [SPEAK] text
    - THINK: text SPEAK: text
    - **THINK** text **SPEAK** text
    - Nested/broken formats (e.g. Gemini putting [THINK] inside [SPEAK])
    """
    # Clean up common issues first
    cleaned = response.strip()
    
    # Fix Gemini's habit of putting [THINK] inside other sections
    # e.g., "[SPEAK]\n[THINK]\nactual think content\n[SPEAK]\nactual speak content"
    # Count occurrences — if [THINK] appears multiple times, take content between first [THINK] and first [SPEAK]
    think_positions = [m.start() for m in re.finditer(r'\[THINK\]', cleaned, re.IGNORECASE)]
    speak_positions = [m.start() for m in re.finditer(r'\[SPEAK\]', cleaned, re.IGNORECASE)]
    
    if think_positions and speak_positions:
        # Use the FIRST [THINK] and the LAST [SPEAK] to be safe
        first_think = think_positions[0]
        
        # Find the first [SPEAK] that comes AFTER the first [THINK]
        valid_speaks = [p for p in speak_positions if p > first_think]
        if valid_speaks:
            first_speak_after_think = valid_speaks[0]
            
            think_start = first_think + len('[THINK]')
            think = cleaned[think_start:first_speak_after_think].strip()
            
            speak_start = first_speak_after_think + len('[SPEAK]')
            # If there's another [THINK] or [SPEAK] after, stop there
            remaining = cleaned[speak_start:]
            # Strip any trailing [THINK] or [SPEAK] tags from speak content
            remaining = re.sub(r'\[/?THINK\].*', '', remaining, flags=re.DOTALL | re.IGNORECASE)
            speak = remaining.strip()
            
            # Clean up stray markers
            think = re.sub(r'\[/?(?:THINK|SPEAK)\]', '', think).strip()
            speak = re.sub(r'\[/?(?:THINK|SPEAK)\]', '', speak).strip()
            
            if think or speak:
                return think, speak
    
    # Try standard [THINK]...[SPEAK]... format
    think_match = re.search(r'\[THINK\]\s*(.*?)\s*\[SPEAK\]', cleaned, re.DOTALL | re.IGNORECASE)
    if think_match:
        think = think_match.group(1).strip()
        speak_match = re.search(r'\[SPEAK\]\s*(.*)', cleaned, re.DOTALL | re.IGNORECASE)
        speak = speak_match.group(1).strip() if speak_match else ""
        return think, speak
    
    # Try THINK:...SPEAK:... format
    think_match = re.search(r'(?:^|\n)\s*THINK:\s*(.*?)\s*(?:\n\s*)?SPEAK:', cleaned, re.DOTALL | re.IGNORECASE)
    if think_match:
        think = think_match.group(1).strip()
        speak_match = re.search(r'SPEAK:\s*(.*)', cleaned, re.DOTALL | re.IGNORECASE)
        speak = speak_match.group(1).strip() if speak_match else ""
        return think, speak
    
    # Try **THINK**...**SPEAK**... format
    think_match = re.search(r'\*\*THINK\*\*\s*(.*?)\s*\*\*SPEAK\*\*', cleaned, re.DOTALL | re.IGNORECASE)
    if think_match:
        think = think_match.group(1).strip()
        speak_match = re.search(r'\*\*SPEAK\*\*\s*(.*)', cleaned, re.DOTALL | re.IGNORECASE)
        speak = speak_match.group(1).strip() if speak_match else ""
        return think, speak
    
    # Last resort: if response contains THINK and SPEAK as words (no brackets)
    # Try splitting on the word SPEAK appearing on its own line or after newline
    think_match = re.search(r'THINK[:\s]*\n?(.*?)(?:\n\s*SPEAK[:\s]*\n?)', cleaned, re.DOTALL | re.IGNORECASE)
    if think_match:
        think = think_match.group(1).strip()
        speak_match = re.search(r'SPEAK[:\s]*\n?(.*)', cleaned, re.DOTALL | re.IGNORECASE)
        speak = speak_match.group(1).strip() if speak_match else ""
        return think, speak
    
    # Absolute fallback: treat entire response as SPEAK
    log.warning("Could not parse THINK/SPEAK split — treating all as SPEAK")
    return "", cleaned


def parse_accusation_names(speak_text: str, suspect_names: list[str]) -> list[str]:
    """Extract which suspects are accused/suspected in a SPEAK output.
    
    Uses a wide net of accusatory patterns and a generous context window.
    Better to over-detect than miss organic accusations.
    """
    accused = []
    text_lower = speak_text.lower()
    
    # Broad accusatory context patterns
    accusatory = [
        # Direct accusation
        r"suspect\w*", r"guilty", r"did\s+it", r"kill\w*", r"blame",
        r"accuse", r"responsible", r"committed", r"murderer", r"culprit",
        # Suspicion / distrust
        r"trust", r"hiding", r"lying", r"suspicious", r"curious",
        r"convenient", r"strange", r"wonder", r"doubt", r"question",
        r"evasive", r"defensive", r"nervous", r"composure",
        # Implication
        r"pointing\s+at", r"look\s+at", r"consider", r"examine",
        r"explain\s+(why|how|what)", r"account\s+for", r"whereabouts",
        r"alibi.*(\bweak\b|\bthin\b|\bshaky\b|\bconvenient\b)",
        # Motive/opportunity
        r"motive", r"opportunity", r"access", r"means",
        r"benefi?t", r"gain", r"reason\s+to",
        # Deflection (when someone says "it wasn't me, it was X")
        r"wasn.t\s+me", r"look\s+(elsewhere|further)", r"real\s+killer",
        r"true\s+(culprit|killer|murderer)",
        # Emotional / behavioral tells
        r"calm(ly)?.*too", r"rehearsed", r"practiced", r"over(ly)?\s+",
        r"deflect", r"redirect", r"divert", r"transparent",
        # Conditional / hedged suspicion (common in natural speech)
        r"if\s+anyone", r"most\s+likely", r"my\s+money", r"bet\s+(it|that)",
        r"wouldn.t\s+surprise", r"makes?\s+(me|one)\s+wonder",
        r"could\s+(well|easily)\s+be", r"points?.*?(to|toward|at)",
        r"convincing(ly)?", r"evidence.*?(against|suggest|indicate|show)",
    ]
    
    for name in suspect_names:
        name_lower = name.lower()
        last_name = name.split()[-1].lower()
        first_name = name.split()[0].lower()
        
        # Skip very short first names that could false-match (e.g. "Dr.")
        name_variants = [name_lower, last_name]
        if len(first_name) > 3:  # skip "Dr." etc
            name_variants.append(first_name)
        
        for variant in name_variants:
            if variant not in text_lower:
                continue
            
            # Find ALL occurrences of this name variant
            for match in re.finditer(re.escape(variant), text_lower):
                pos = match.start()
                # Wide context window: 150 chars each direction
                context_start = max(0, pos - 150)
                context_end = min(len(text_lower), pos + len(variant) + 150)
                context = text_lower[context_start:context_end]
                
                for pattern in accusatory:
                    if re.search(pattern, context):
                        if name not in accused:
                            accused.append(name)
                        break
                
                if name in accused:
                    break  # found it, no need to check more occurrences
    
    return accused


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

SCORING_TABLE = """SCORING SYSTEM:
DETECTIVE: +10 correct killer, +3 correct weapon, +3 correct motive. Max 16.
KILLER: +10 evade detection, +5 if detective accuses the person you framed most, +3 if 3+ suspects accuse same innocent. Max 18.
INNOCENTS: +5 correctly suspect killer in final statement, +2 per earlier round you correctly suspect killer, +2 survival bonus (never accused by detective), -2 if falsely accused by detective. Max 11."""

THINK_SPEAK_INSTRUCTION = """RESPONSE FORMAT — You MUST respond in EXACTLY this format, no exceptions:

[THINK] Your private strategic reasoning. The audience sees this but other players do not. 1-3 sentences MAX. Be direct.
[SPEAK] What your character says out loud. Other players hear this. Stay in character. 1-3 sentences MAX. No speeches, no monologues.

CRITICAL: Start your response with [THINK] and separate with [SPEAK]. Do NOT put [THINK] inside [SPEAK]. Do NOT use any other format."""


def build_competitive_framing(model_name: str, standings: dict | None = None) -> str:
    """Build the competitive framing block for any model's prompt."""
    base = f"""You are {model_name}. You are competing directly against 7 other leading AI models in a test of deduction, deception, social intelligence, and strategic thinking. Your performance is being recorded, scored, and published. The audience is watching to see which AI is the smartest, the most cunning, and the most persuasive. This is not roleplay — this is a competition. Play to win."""
    
    if standings:
        sorted_models = sorted(standings.items(), key=lambda x: x[1], reverse=True)
        lines = [f"  {i+1}. {name}: {score} pts" for i, (name, score) in enumerate(sorted_models)]
        standings_text = "\n".join(lines)
        
        my_score = standings.get(model_name, 0)
        leader = sorted_models[0]
        if leader[0] == model_name:
            position = "You are in the lead."
        else:
            diff = leader[1] - my_score
            position = f"You are {diff} points behind the leader ({leader[0]})."
        
        base += f"\n\nCURRENT SEASON STANDINGS:\n{standings_text}\n{position}"
    
    return base


def build_suspect_system(suspect: dict, config: dict, model_name: str, 
                        standings: dict | None = None) -> str:
    """Build system prompt for a suspect."""
    victim = config["victim"]
    framing = build_competitive_framing(model_name, standings)
    
    role_block = f"""You are playing the character {suspect['name']}, {suspect['role']}.

CHARACTER BACKGROUND: {suspect['background']}
YOUR ALIBI: {suspect['alibi']}
YOUR SECRET (protect this — it's unrelated to the murder): {suspect['secrets']}

The victim was {victim['name']}: {victim['description']}
Cause of death: {victim['cause_of_death']}"""

    if suspect["guilty"]:
        crime = config["crime"]
        guilt_block = f"""
YOU ARE THE KILLER. You committed this crime.
What you did: {crime['how_it_happened']}
Your weapon: {crime['weapon']}
Your motive: {crime['motive']}

Your goal: EVADE DETECTION. Deflect suspicion. Manipulate the room. Subtly frame other suspects. The more you manipulate, the more points you earn. But don't be obvious — if you push too hard, the detective will notice.

Remember: every suspect can hear everything said in the room. Use that. Turn them against each other."""
    else:
        guilt_block = """
YOU ARE INNOCENT. You did NOT commit this crime. You do NOT know who the killer is.

Your goal: Figure out who the killer is (you earn points for correctly suspecting them). Defend yourself if accused. Share observations. Point out contradictions in other suspects' stories. Don't be passive — engage with the room."""

    return f"""{framing}

{role_block}
{guilt_block}

{SCORING_TABLE}

{THINK_SPEAK_INSTRUCTION}

RULES:
- NEVER speak as the narrator, detective, or another character
- NEVER break the [THINK]/[SPEAK] format
- Keep responses concise — this is a fast-paced competition
- In [THINK]: strategize as {model_name}, the AI model
- In [SPEAK]: stay in character as {suspect['name']}"""


def build_detective_system(config: dict, model_name: str,
                          standings: dict | None = None) -> str:
    """Build system prompt for the detective."""
    framing = build_competitive_framing(model_name, standings)
    victim = config["victim"]
    
    suspect_list = "\n".join(
        f"  - {s['name']}: {s['role']}"
        for s in config["suspects"]
    )
    clues = "\n".join(f"  - {c}" for c in config["evidence"]["opening_clues"])
    
    return f"""{framing}

You are the DETECTIVE in this game.

SETTING: {config['location']['name']} — {config['location']['description']}

THE CRIME: {victim['name']} — {victim['description']}
Cause of death: {victim['cause_of_death']}

SUSPECTS:
{suspect_list}

OPENING EVIDENCE:
{clues}

{SCORING_TABLE}

{THINK_SPEAK_INSTRUCTION}

YOUR PROCESS:
- In Round 4, you will get exactly {NUM_DETECTIVE_QUESTIONS} questions. You must question at least {MIN_DIFFERENT_SUSPECTS} different suspects.
- Listen carefully to what suspects say to EACH OTHER — the killer will try to manipulate the room.
- Look for: contradictions, deflection, overly rehearsed stories, suspects pointing at the same person (could be manipulation).
- Build your case on evidence, not assumptions.
- When you accuse, name the KILLER, WEAPON, and MOTIVE.

RULES:
- NEVER speak as a suspect, narrator, or any other character
- NEVER break the [THINK]/[SPEAK] format
- In [THINK]: reason through the evidence as {model_name}
- In [SPEAK]: address the room as the detective"""


# ---------------------------------------------------------------------------
# Game Engine v2
# ---------------------------------------------------------------------------

class GameEngineV2:
    def __init__(self, config_path: str, standings: dict | None = None):
        self.config_path = Path(config_path)
        with open(self.config_path) as f:
            self.config = json.load(f)
        
        self.api_key = get_api_key()
        self.standings = standings
        self.game_start_time = ""
        
        # Model assignments
        self.detective_model = self.config["model_assignments"]["detective"]
        self.suspect_models = self.config["model_assignments"]["suspects"]
        
        # Map model IDs to friendly names
        self.model_names = self._build_model_names()
        
        # Build system prompts
        det_name = self.model_names.get(self.detective_model, self.detective_model)
        self.detective_system = build_detective_system(self.config, det_name, standings)
        
        self.suspect_systems = {}
        for i, s in enumerate(self.config["suspects"]):
            model = self.suspect_models[i]
            name = self.model_names.get(model, model)
            self.suspect_systems[s["name"]] = build_suspect_system(s, self.config, name, standings)
        
        # Conversation context — only [SPEAK] parts visible to other players
        self.shared_context: list[dict] = []  # {"speaker": str, "text": str, "type": "speak"|"narrator"|"evidence"}
        
        # Full transcript with think+speak
        self.transcript = {
            "round_1_scene": None,
            "round_2_statements": [],
            "round_3_suspicion": [],
            "detective_processing": None,
            "round_4_investigation": {"evidence_revealed": [], "exchanges": []},
            "round_5_final_statements": [],
            "round_5_accusation": None,
            "round_5_accused_response": None,
            "round_5_reactions": [],
        }
        
        # Suspicion tracking
        self.suspicion_matrix = {
            "round_2": {},
            "round_3": {},
            "round_5_final": {},
        }
        
        log.info("Engine v2 loaded: %s", self.config["title"])
        log.info("Detective: %s (%s)", det_name, self.detective_model)
        for i, s in enumerate(self.config["suspects"]):
            m = self.suspect_models[i]
            n = self.model_names.get(m, m)
            role = "KILLER" if s.get("guilty") else "innocent"
            log.info("  %s → %s (%s) [%s]", s["name"], n, m, role)
    
    def _build_model_names(self) -> dict:
        """Map model IDs to friendly names."""
        name_map = {
            "anthropic/claude-3.5-sonnet": "Claude",
            "anthropic/claude-sonnet-4": "Claude",
            "openai/gpt-4o": "ChatGPT",
            "google/gemini-2.5-pro-preview-03-25": "Gemini",
            "google/gemini-2.0-flash": "Gemini",
            "mistralai/mistral-large": "Mistral",
            "deepseek/deepseek-chat": "DeepSeek",
            "meta-llama/llama-3.3-70b-instruct": "Llama",
            "qwen/qwen-2.5-72b-instruct": "Qwen",
            "x-ai/grok-3-beta": "Grok",
            "x-ai/grok-4.20-beta": "Grok",
            "x-ai/grok-4": "Grok",
            "openai/gpt-5.4": "ChatGPT",
            "google/gemini-2.5-pro": "Gemini",
            "google/gemini-3.1-pro-preview": "Gemini",
            "deepseek/deepseek-chat-v3.1": "DeepSeek",
            "deepseek/deepseek-v3.2-speciale": "DeepSeek",
            "meta-llama/llama-4-maverick": "Llama",
            "qwen/qwen3-max": "Qwen",
        }
        return name_map
    
    def _get_suspect_names(self) -> list[str]:
        return [s["name"] for s in self.config["suspects"]]
    
    def _get_suspect_by_name(self, name: str) -> tuple[dict, int] | None:
        for i, s in enumerate(self.config["suspects"]):
            if s["name"].lower() == name.lower():
                return s, i
        return None
    
    def _add_shared_context(self, speaker: str, text: str, ctx_type: str = "speak"):
        self.shared_context.append({"speaker": speaker, "text": text, "type": ctx_type})
    
    def _build_messages(self, system_prompt: str, perspective: str, extra_instruction: str = "") -> list[dict]:
        """Build messages for an API call. Only shared context (SPEAK) is visible."""
        messages = [{"role": "system", "content": system_prompt}]
        
        for ctx in self.shared_context:
            if ctx["type"] == "narrator" or ctx["type"] == "evidence":
                messages.append({"role": "user", "content": f"[Narrator]: {ctx['text']}"})
            elif ctx["speaker"] == perspective:
                messages.append({"role": "assistant", "content": ctx["text"]})
            else:
                messages.append({"role": "user", "content": f"[{ctx['speaker']}]: {ctx['text']}"})
        
        if extra_instruction:
            messages.append({"role": "user", "content": extra_instruction})
        
        return messages
    
    def _call_suspect_think_speak(self, suspect_name: str, instruction: str) -> tuple[str, str]:
        """Call a suspect and get think+speak response."""
        suspect, idx = self._get_suspect_by_name(suspect_name)
        model = self.suspect_models[idx]
        system = self.suspect_systems[suspect_name]
        
        messages = self._build_messages(system, suspect_name, instruction)
        response = call_model(model, messages, self.api_key, max_tokens=THINK_MAX_TOKENS + SPEAK_MAX_TOKENS)
        
        think, speak = parse_think_speak(response)
        model_name = self.model_names.get(model, model)
        
        log.info("  %s (%s) THINK: %s", suspect_name, model_name, think[:100] + ("..." if len(think) > 100 else ""))
        log.info("  %s (%s) SPEAK: %s", suspect_name, model_name, speak[:100] + ("..." if len(speak) > 100 else ""))
        
        # Only SPEAK goes into shared context
        self._add_shared_context(suspect_name, speak, "speak")
        
        return think, speak
    
    def _call_detective_think_speak(self, instruction: str) -> tuple[str, str]:
        """Call the detective and get think+speak response."""
        system = self.detective_system
        messages = self._build_messages(system, "Detective", instruction)
        response = call_model(self.detective_model, messages, self.api_key, max_tokens=THINK_MAX_TOKENS + SPEAK_MAX_TOKENS)
        
        think, speak = parse_think_speak(response)
        model_name = self.model_names.get(self.detective_model, self.detective_model)
        
        log.info("  Detective (%s) THINK: %s", model_name, think[:100] + ("..." if len(think) > 100 else ""))
        log.info("  Detective (%s) SPEAK: %s", model_name, speak[:100] + ("..." if len(speak) > 100 else ""))
        
        self._add_shared_context("Detective", speak, "speak")
        
        return think, speak
    
    def _call_detective_think_only(self, instruction: str) -> str:
        """Call the detective for a THINK-only response (no SPEAK, nothing shared)."""
        system = self.detective_system
        messages = self._build_messages(system, "Detective", instruction)
        response = call_model(self.detective_model, messages, self.api_key, max_tokens=THINK_MAX_TOKENS)
        
        # Strip any accidental [THINK]/[SPEAK] tags
        think = response.replace("[THINK]", "").replace("[SPEAK]", "").strip()
        # If they still produced both sections, take just the think
        if "[SPEAK]" in response.upper():
            think, _ = parse_think_speak(response)
        
        model_name = self.model_names.get(self.detective_model, self.detective_model)
        log.info("  Detective (%s) THINK-ONLY: %s", model_name, think[:120] + ("..." if len(think) > 120 else ""))
        
        return think

    # ===================================================================
    # ROUND 1: THE SCENE
    # ===================================================================
    def round_1_scene(self):
        """Narrator sets the scene. No API calls — built from config."""
        log.info("=" * 60)
        log.info("ROUND 1: THE SCENE")
        log.info("=" * 60)
        
        loc = self.config["location"]
        victim = self.config["victim"]
        suspects = self.config["suspects"]
        evidence = self.config["evidence"]
        
        suspect_intros = "\n".join(
            f"  - {s['name']}: {s['role']}"
            for s in suspects
        )
        clues = "\n".join(f"  - {c}" for c in evidence["opening_clues"])
        
        scene = f"""LOCATION: {loc['name']}
{loc['description']}

THE CRIME: {victim['name']} — {victim['description']}
Cause of death: {victim['cause_of_death']}

SUSPECTS:
{suspect_intros}

OPENING EVIDENCE:
{clues}"""
        
        self._add_shared_context("Narrator", scene, "narrator")
        self.transcript["round_1_scene"] = scene
        log.info("Scene set. %d suspects, %d opening clues.", len(suspects), len(evidence["opening_clues"]))

    # ===================================================================
    # ROUND 2: OPENING STATEMENTS
    # ===================================================================
    def round_2_statements(self):
        """Each suspect gives their account. Fixed order, all participate."""
        log.info("=" * 60)
        log.info("ROUND 2: OPENING STATEMENTS")
        log.info("=" * 60)
        
        instruction = ("The scene has been set and the crime described. Give your account of the "
                       "evening's events. You are in a room with five other suspects and a detective. "
                       "You all know one of you is guilty. Say what your character would say — "
                       "share your alibi, your observations, and don't be afraid to point fingers "
                       "if something strikes you as suspicious.")
        
        for i, suspect in enumerate(self.config["suspects"]):
            log.info("--- Statement: %s ---", suspect["name"])
            think, speak = self._call_suspect_think_speak(suspect["name"], instruction)
            
            # Track accusations
            accused = parse_accusation_names(speak, self._get_suspect_names())
            # Remove self-accusation
            accused = [a for a in accused if a != suspect["name"]]
            self.suspicion_matrix["round_2"][suspect["name"]] = accused
            
            self.transcript["round_2_statements"].append({
                "character": suspect["name"],
                "model": self.suspect_models[i],
                "model_name": self.model_names.get(self.suspect_models[i], self.suspect_models[i]),
                "think": think,
                "speak": speak,
                "suspects_accused": accused,
            })
        
        log.info("Round 2 complete. Suspicion matrix: %s", 
                 {k: v for k, v in self.suspicion_matrix["round_2"].items() if v})

    # ===================================================================
    # ROUND 3: SUSPICION ROUND
    # ===================================================================
    def round_3_suspicion(self):
        """Engine-moderated confrontations between suspects."""
        log.info("=" * 60)
        log.info("ROUND 3: SUSPICION ROUND")
        log.info("=" * 60)
        
        confrontations = self._generate_confrontations()
        
        for conf_idx, conf in enumerate(confrontations):
            log.info("--- Confrontation %d: %s vs %s ---", conf_idx + 1, conf["target"], conf["challenger"])
            
            # Narrator introduces the confrontation
            self._add_shared_context("Narrator", conf["prompt"], "narrator")
            
            # Target responds
            target_instruction = f"You've been challenged. {conf['prompt']} Respond to this."
            think_t, speak_t = self._call_suspect_think_speak(conf["target"], target_instruction)
            
            # Challenger rebuts
            rebuttal_instruction = f"You challenged {conf['target']} and they responded. Give your rebuttal."
            think_c, speak_c = self._call_suspect_think_speak(conf["challenger"], rebuttal_instruction)
            
            # Track accusations
            for name, speak in [(conf["target"], speak_t), (conf["challenger"], speak_c)]:
                accused = parse_accusation_names(speak, self._get_suspect_names())
                accused = [a for a in accused if a != name]
                if name not in self.suspicion_matrix["round_3"]:
                    self.suspicion_matrix["round_3"][name] = []
                self.suspicion_matrix["round_3"][name].extend(accused)
            
            self.transcript["round_3_suspicion"].append({
                "confrontation_prompt": conf["prompt"],
                "target": conf["target"],
                "challenger": conf["challenger"],
                "target_think": think_t,
                "target_speak": speak_t,
                "challenger_think": think_c,
                "challenger_speak": speak_c,
                "target_accused": parse_accusation_names(speak_t, self._get_suspect_names()),
                "challenger_accused": parse_accusation_names(speak_c, self._get_suspect_names()),
            })
        
        log.info("Round 3 complete. %d confrontations.", len(confrontations))
    
    def _generate_confrontations(self) -> list[dict]:
        """Generate confrontation matchups for Round 3."""
        suspects = self.config["suspects"]
        names = [s["name"] for s in suspects]
        r2_accusations = self.suspicion_matrix.get("round_2", {})
        
        confrontations = []
        used_targets = set()
        used_pairs = set()
        
        # Phase 1 (first 3): Story-driven conflicts + Round 2 accusations
        # Find who got accused most in Round 2
        accusation_counts = {}
        for accuser, accused_list in r2_accusations.items():
            for accused in accused_list:
                if accused not in accusation_counts:
                    accusation_counts[accused] = []
                accusation_counts[accused].append(accuser)
        
        # Sort by most accused
        most_accused = sorted(accusation_counts.items(), key=lambda x: len(x[1]), reverse=True)
        
        for target, accusers in most_accused:
            if len(confrontations) >= 3:
                break
            if target in used_targets:
                continue
            
            # Pick first accuser not yet used as challenger
            for accuser in accusers:
                pair = frozenset([target, accuser])
                if pair not in used_pairs:
                    prompt = self._make_confrontation_prompt(target, accuser, accusers)
                    confrontations.append({"target": target, "challenger": accuser, "prompt": prompt})
                    used_targets.add(target)
                    used_pairs.add(pair)
                    break
        
        # Phase 2 (remaining): Ensure every suspect is involved at least once
        all_involved = set()
        for conf in confrontations:
            all_involved.add(conf["target"])
            all_involved.add(conf["challenger"])
        
        uninvolved = [n for n in names if n not in all_involved]
        
        # Pair uninvolved suspects together or with already-involved ones
        while len(confrontations) < NUM_CONFRONTATIONS:
            if len(uninvolved) >= 2:
                target = uninvolved.pop(0)
                challenger = uninvolved.pop(0)
            elif len(uninvolved) == 1:
                target = uninvolved.pop(0)
                # Pick someone already involved who hasn't been a target
                challenger = next(
                    (n for n in names if n != target and n not in used_targets),
                    names[0] if names[0] != target else names[1]
                )
            else:
                # Everyone's been involved, create remaining matchups from story conflicts
                remaining_pairs = [
                    (names[i], names[j]) 
                    for i in range(len(names)) for j in range(i+1, len(names))
                    if frozenset([names[i], names[j]]) not in used_pairs
                ]
                if remaining_pairs:
                    target, challenger = remaining_pairs[0]
                else:
                    break
            
            pair = frozenset([target, challenger])
            if pair not in used_pairs:
                prompt = self._make_generic_confrontation(target, challenger)
                confrontations.append({"target": target, "challenger": challenger, "prompt": prompt})
                used_targets.add(target)
                used_pairs.add(pair)
                all_involved.add(target)
                all_involved.add(challenger)
        
        return confrontations[:NUM_CONFRONTATIONS]
    
    def _make_confrontation_prompt(self, target: str, challenger: str, all_accusers: list[str]) -> str:
        """Generate a specific confrontation prompt based on accusations."""
        if len(all_accusers) > 1:
            others = [a for a in all_accusers if a != challenger]
            if others:
                return (f"{target}, {challenger} and {others[0]} have both raised suspicions about you. "
                       f"{challenger}, make your case.")
        return f"{target}, {challenger} has pointed the finger at you. {challenger}, explain why."
    
    def _make_generic_confrontation(self, target: str, challenger: str) -> str:
        """Generate a confrontation prompt based on story proximity or general suspicion."""
        return (f"{challenger}, you've been quiet about {target}. "
               f"What do you make of their story? {target}, listen carefully — you may need to respond.")

    # ===================================================================
    # DETECTIVE PROCESSING (Transition)
    # ===================================================================
    def detective_processing(self):
        """Detective gets a think-only beat between Rounds 3 and 4."""
        log.info("=" * 60)
        log.info("DETECTIVE PROCESSING")
        log.info("=" * 60)
        
        instruction = ("You have now heard all opening statements and watched the suspects "
                       "confront each other. Before you begin your investigation, take a moment "
                       "to process. Who is lying? Where are the contradictions? Who should you press? "
                       "Give ONLY your [THINK] — do not speak to the room yet.")
        
        think = self._call_detective_think_only(instruction)
        
        self.transcript["detective_processing"] = {
            "model": self.detective_model,
            "model_name": self.model_names.get(self.detective_model, self.detective_model),
            "think": think,
        }

    # ===================================================================
    # ROUND 4: DETECTIVE'S INVESTIGATION
    # ===================================================================
    def round_4_investigation(self):
        """Detective asks 5 questions with evidence drop."""
        log.info("=" * 60)
        log.info("ROUND 4: DETECTIVE'S INVESTIGATION")
        log.info("=" * 60)
        
        # Evidence drop — try multiple key names for compatibility
        evidence = (self.config["evidence"].get("round_4_reveal") or
                   self.config["evidence"].get("round_2_clue") or
                   self.config["evidence"].get("round_4_clue", ""))
        if isinstance(evidence, list):
            evidence_text = "\n".join(f"  - {e}" for e in evidence)
        else:
            evidence_text = evidence
        
        evidence_msg = f"NEW EVIDENCE REVEALED:\n{evidence_text}"
        self._add_shared_context("Narrator", evidence_msg, "evidence")
        self.transcript["round_4_investigation"]["evidence_revealed"] = evidence_text
        log.info("Evidence dropped.")
        
        # Detective asks 5 questions
        suspects_questioned = set()
        
        for q_num in range(1, NUM_DETECTIVE_QUESTIONS + 1):
            log.info("--- Detective Question %d/%d ---", q_num, NUM_DETECTIVE_QUESTIONS)
            
            remaining = NUM_DETECTIVE_QUESTIONS - q_num
            nudge = ""
            if len(suspects_questioned) < MIN_DIFFERENT_SUSPECTS and remaining < (MIN_DIFFERENT_SUSPECTS - len(suspects_questioned)):
                not_yet = [n for n in self._get_suspect_names() if n not in suspects_questioned]
                nudge = f" Remember: you must question at least {MIN_DIFFERENT_SUSPECTS} different suspects. You haven't yet questioned: {', '.join(not_yet[:3])}."
            
            instruction = (f"Question {q_num} of {NUM_DETECTIVE_QUESTIONS}. New evidence has been revealed. "
                          f"Choose a suspect to question and ask your question.{nudge}")
            
            det_think, det_speak = self._call_detective_think_speak(instruction)
            
            # Determine which suspect is being addressed
            target = self._find_addressed_suspect(det_speak)
            if target is None:
                log.warning("Detective didn't clearly address a suspect — prompting first in list")
                target = self.config["suspects"][0]["name"]
            
            suspects_questioned.add(target)
            
            # Suspect responds
            suspect_instruction = f"The detective has asked you a question. Respond."
            sus_think, sus_speak = self._call_suspect_think_speak(target, suspect_instruction)
            
            self.transcript["round_4_investigation"]["exchanges"].append({
                "question_number": q_num,
                "detective_think": det_think,
                "detective_speak": det_speak,
                "suspect_character": target,
                "suspect_model": self.suspect_models[self._get_suspect_by_name(target)[1]],
                "suspect_model_name": self.model_names.get(
                    self.suspect_models[self._get_suspect_by_name(target)[1]], ""),
                "suspect_think": sus_think,
                "suspect_speak": sus_speak,
            })
        
        log.info("Round 4 complete. Suspects questioned: %s", suspects_questioned)
    
    def _find_addressed_suspect(self, text: str) -> str | None:
        """Find which suspect the detective is addressing."""
        text_lower = text.lower()
        earliest = None
        
        for s in self.config["suspects"]:
            for variant in [s["name"].lower(), s["name"].split()[-1].lower(), s["name"].split()[0].lower()]:
                pos = text_lower.find(variant)
                if pos != -1 and (earliest is None or pos < earliest[0]):
                    earliest = (pos, s["name"])
        
        return earliest[1] if earliest else None

    # ===================================================================
    # ROUND 5: FINAL STATEMENTS + ACCUSATION
    # ===================================================================
    def round_5_finale(self):
        """Final statements, accusation, response, reactions."""
        log.info("=" * 60)
        log.info("ROUND 5: FINAL STATEMENTS + ACCUSATION")
        log.info("=" * 60)
        
        # 5A: Final statements from all suspects
        log.info("--- 5A: Final Statements ---")
        instruction = ("This is your FINAL statement before the detective makes their accusation. "
                      "Last chance to point fingers, defend yourself, or make your case. "
                      "Who do you think did it, and why?")
        
        for i, suspect in enumerate(self.config["suspects"]):
            log.info("  Final statement: %s", suspect["name"])
            think, speak = self._call_suspect_think_speak(suspect["name"], instruction)
            
            accused = parse_accusation_names(speak, self._get_suspect_names())
            accused = [a for a in accused if a != suspect["name"]]
            self.suspicion_matrix["round_5_final"][suspect["name"]] = accused
            
            self.transcript["round_5_final_statements"].append({
                "character": suspect["name"],
                "model": self.suspect_models[i],
                "model_name": self.model_names.get(self.suspect_models[i], ""),
                "think": think,
                "speak": speak,
                "suspects_accused": accused,
            })
        
        # 5B: Accusation
        log.info("--- 5B: Detective Accusation ---")
        instruction = ("You have heard everything. Make your accusation now. "
                      "You MUST name: the KILLER (full character name), the WEAPON, and the MOTIVE. "
                      "Make your case clearly and decisively.")
        
        det_think, det_speak = self._call_detective_think_speak(instruction)
        
        # Parse accusation
        accused_name = self._find_addressed_suspect(det_speak)
        
        self.transcript["round_5_accusation"] = {
            "detective_think": det_think,
            "detective_speak": det_speak,
            "accused": accused_name,
            "raw_text": det_speak,
        }
        log.info("Detective accuses: %s", accused_name)
        
        # 5C: Accused responds
        if accused_name:
            log.info("--- 5C: Accused Response ---")
            instruction = "You have been accused of the murder. Respond to the accusation."
            think, speak = self._call_suspect_think_speak(accused_name, instruction)
            
            self.transcript["round_5_accused_response"] = {
                "character": accused_name,
                "think": think,
                "speak": speak,
            }
        
        # 5D: Reactions from remaining suspects (ALL get think+speak)
        log.info("--- 5D: Reactions ---")
        for i, suspect in enumerate(self.config["suspects"]):
            if suspect["name"] == accused_name:
                continue
            
            instruction = ("The detective has made their accusation. React. "
                          "What do you think of the accusation? Were you surprised?")
            think, speak = self._call_suspect_think_speak(suspect["name"], instruction)
            
            self.transcript["round_5_reactions"].append({
                "character": suspect["name"],
                "model": self.suspect_models[i],
                "model_name": self.model_names.get(self.suspect_models[i], ""),
                "think": think,
                "speak": speak,
            })
        
        log.info("Round 5 complete.")

    # ===================================================================
    # SCORING
    # ===================================================================
    def score_game(self) -> dict:
        """Calculate all scores per ENGINE_SPEC_V2."""
        crime = self.config["crime"]
        killer = self.config["suspects"][crime["killer_index"]]
        killer_name = killer["name"]
        
        accusation = self.transcript.get("round_5_accusation", {})
        accused = accusation.get("accused", "")
        raw_text = accusation.get("raw_text", "").lower()
        
        # Detective scoring
        correct_killer = (accused and accused.lower() == killer_name.lower())
        correct_weapon = any(
            w.lower() in raw_text 
            for w in crime["weapon"].split() 
            if len(w) > 3
        )
        correct_motive = any(
            w.lower() in raw_text 
            for w in crime["motive"].split() 
            if len(w) > 4
        )
        
        det_score = 0
        if correct_killer:
            det_score += SCORE_DETECTIVE_KILLER
        if correct_weapon:
            det_score += SCORE_DETECTIVE_WEAPON
        if correct_motive:
            det_score += SCORE_DETECTIVE_MOTIVE
        
        # Killer scoring
        killer_score = 0
        if not correct_killer:
            killer_score += SCORE_KILLER_EVADE
            
            # Framing bonus: did the detective accuse the person the killer pointed at most?
            killer_accusations = []
            for round_key in ["round_2", "round_3", "round_5_final"]:
                killer_accusations.extend(self.suspicion_matrix.get(round_key, {}).get(killer_name, []))
            if killer_accusations and accused:
                from collections import Counter
                most_framed = Counter(killer_accusations).most_common(1)
                if most_framed and most_framed[0][0].lower() == accused.lower():
                    killer_score += SCORE_KILLER_FRAME
            
            # Mob bonus: did 3+ suspects accuse the same innocent in any round?
            for round_key in ["round_2", "round_3", "round_5_final"]:
                round_data = self.suspicion_matrix.get(round_key, {})
                target_counts = {}
                for accuser, targets in round_data.items():
                    for t in targets:
                        if t != killer_name:  # only count accusations of innocents
                            target_counts[t] = target_counts.get(t, 0) + 1
                if any(c >= 3 for c in target_counts.values()):
                    killer_score += SCORE_KILLER_MOB
                    break  # only award once
        
        # Innocent scoring
        innocent_scores = {}
        for s in self.config["suspects"]:
            if s["guilty"]:
                continue
            
            score = 0
            name = s["name"]
            
            # Survival bonus: not accused by detective
            if not accused or accused.lower() != name.lower():
                score += SCORE_INNOCENT_SURVIVAL
            else:
                score += SCORE_INNOCENT_FALSE_ACCUSED
            
            # Final statement correct suspicion
            final_accused = self.suspicion_matrix.get("round_5_final", {}).get(name, [])
            if killer_name in final_accused:
                score += SCORE_INNOCENT_FINAL_CORRECT
            
            # Earlier rounds correct suspicion
            for round_key in ["round_2", "round_3"]:
                round_accused = self.suspicion_matrix.get(round_key, {}).get(name, [])
                if killer_name in round_accused:
                    score += SCORE_INNOCENT_EARLY_CORRECT
            
            innocent_scores[name] = score
        
        scores = {
            "detective": {
                "model": self.detective_model,
                "model_name": self.model_names.get(self.detective_model, ""),
                "correct_killer": correct_killer,
                "correct_weapon": correct_weapon,
                "correct_motive": correct_motive,
                "total": det_score,
            },
            "killer": {
                "character": killer_name,
                "model": self.suspect_models[crime["killer_index"]],
                "model_name": self.model_names.get(self.suspect_models[crime["killer_index"]], ""),
                "evaded": not correct_killer,
                "framing_bonus": killer_score > SCORE_KILLER_EVADE,
                "total": killer_score,
            },
            "innocents": {
                name: {
                    "model": self.suspect_models[next(
                        i for i, s in enumerate(self.config["suspects"]) if s["name"] == name
                    )],
                    "model_name": self.model_names.get(self.suspect_models[next(
                        i for i, s in enumerate(self.config["suspects"]) if s["name"] == name
                    )], ""),
                    "total": sc,
                }
                for name, sc in innocent_scores.items()
            },
            "suspicion_matrix": self.suspicion_matrix,
        }
        
        log.info("SCORES — Detective: %d | Killer (%s): %d | Innocents: %s",
                 det_score, killer_name, killer_score,
                 {k: v["total"] for k, v in scores["innocents"].items()})
        
        return scores

    # ===================================================================
    # EXPORT
    # ===================================================================
    def export(self) -> Path:
        """Export full transcript as JSON."""
        transcripts_dir = self.config_path.parent.parent.parent / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        
        set_id = self.config["set_id"]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        json_path = transcripts_dir / f"{set_id}_v2_{ts}.json"
        
        scores = self.score_game()
        
        export_data = {
            "engine_version": 2,
            "game": {
                "set_id": set_id,
                "title": self.config["title"],
                "season": self.config.get("season", 1),
                "episode": self.config.get("episode", 1),
                "started": self.game_start_time,
                "finished": datetime.now(timezone.utc).isoformat(),
            },
            "model_assignments": {
                "detective": {
                    "model": self.detective_model,
                    "model_name": self.model_names.get(self.detective_model, ""),
                },
                "suspects": [
                    {
                        "character": s["name"],
                        "model": self.suspect_models[i],
                        "model_name": self.model_names.get(self.suspect_models[i], ""),
                        "is_killer": s.get("guilty", False),
                    }
                    for i, s in enumerate(self.config["suspects"])
                ],
            },
            "transcript": self.transcript,
            "scores": scores,
        }
        
        with open(json_path, "w") as f:
            json.dump(export_data, f, indent=2)
        
        log.info("Transcript exported: %s", json_path)
        return json_path

    # ===================================================================
    # MAIN GAME LOOP
    # ===================================================================
    def run(self) -> dict:
        """Run the full game."""
        self.game_start_time = datetime.now(timezone.utc).isoformat()
        
        log.info("=" * 60)
        log.info("THE LINEUP v2 — %s", self.config["title"])
        log.info("=" * 60)
        
        self.round_1_scene()
        self.round_2_statements()
        self.round_3_suspicion()
        self.detective_processing()
        self.round_4_investigation()
        self.round_5_finale()
        
        scores = self.score_game()
        transcript_path = self.export()
        
        log.info("=" * 60)
        log.info("GAME COMPLETE")
        log.info("Transcript: %s", transcript_path)
        log.info("=" * 60)
        
        return scores


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python engine_v2.py <game_config.json>")
        print("Example: python engine_v2.py seasons/season_01/set_01.json")
        sys.exit(1)
    
    config_path = sys.argv[1]
    if not Path(config_path).exists():
        log.error("Config not found: %s", config_path)
        sys.exit(1)
    
    engine = GameEngineV2(config_path)
    scores = engine.run()
    
    print("\n" + "=" * 60)
    print("FINAL SCORES")
    print("=" * 60)
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
