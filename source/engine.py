#!/usr/bin/env python3
"""AI Mystery Theater — V3 Engine
A murder mystery game engine where AI models play characters.
Beat-based transcripts, location tracking, generalized prompts, emotional escalation.
"""

import argparse
import json
import os
import random
import re
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

import requests
from colorama import Fore, Style, init as colorama_init

colorama_init()

# ── Color assignments for characters ──────────────────────────────────────────

CHARACTER_COLORS = [
    Fore.CYAN,
    Fore.YELLOW,
    Fore.GREEN,
    Fore.MAGENTA,
    Fore.RED,
]
DETECTIVE_COLOR = Fore.WHITE
NARRATOR_COLOR = Fore.BLUE
EVIDENCE_COLOR = Fore.RED
PHASE_COLOR = Fore.CYAN

# ── Pretty printing helpers ───────────────────────────────────────────────────

def header(title: str):
    w = 60
    print()
    print(f"{PHASE_COLOR}╔{'═' * w}╗{Style.RESET_ALL}")
    print(f"{PHASE_COLOR}║{title:^{w}}║{Style.RESET_ALL}")
    print(f"{PHASE_COLOR}╚{'═' * w}╝{Style.RESET_ALL}")
    print()

def sub_header(title: str):
    print(f"\n{PHASE_COLOR}── {title} {'─' * (50 - len(title))}{Style.RESET_ALL}\n")

def narrator_say(text: str):
    print(f"{NARRATOR_COLOR}  ▸ NARRATOR: {text}{Style.RESET_ALL}")

def evidence_say(text: str):
    print()
    print(f"{EVIDENCE_COLOR}  ┌─ NEW EVIDENCE ─────────────────────────────────────┐{Style.RESET_ALL}")
    for line in text.split('\n'):
        print(f"{EVIDENCE_COLOR}  │ {line:<53}│{Style.RESET_ALL}")
    print(f"{EVIDENCE_COLOR}  └─────────────────────────────────────────────────────┘{Style.RESET_ALL}")
    print()

def character_say(name: str, color: str, text: str, thinking: str = None):
    if thinking:
        print(f"  {Fore.LIGHTBLACK_EX}  💭 {thinking}{Style.RESET_ALL}")
    prefix = f"{color}{name}:{Style.RESET_ALL} "
    print(f"  {prefix}{text}")

def dramatic_pause(seconds: float = 1.0):
    time.sleep(seconds)

# ── OpenRouter API ────────────────────────────────────────────────────────────

class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.total_tokens = 0
        self.total_cost = 0.0

    def chat(self, model: str, messages: list[dict], temperature: float = 0.9,
             max_tokens: int = 1024) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/mystery-theater",
            "X-Title": "AI Mystery Theater",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        for attempt in range(3):
            try:
                resp = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=60)
                if resp.status_code == 429:
                    wait = 2 ** attempt * 2
                    print(f"  (rate limited, retrying in {wait}s...)")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                usage = data.get("usage", {})
                self.total_tokens += usage.get("total_tokens", 0)
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(2)
        return ""


class DryRunClient:
    """Returns canned responses for testing V3 game flow."""

    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0.0
        self._call_count = 0
        self._suspect_names: list[str] = []

    def set_suspect_names(self, names: list[str]):
        self._suspect_names = names

    def chat(self, model: str, messages: list[dict], temperature: float = 0.9,
             max_tokens: int = 1024) -> str:
        self._call_count += 1
        self.total_tokens += 150

        last_user = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user = m["content"]
                break

        system = messages[0]["content"] if messages else ""

        # Detect detective vs suspect based on system prompt
        if "You are the detective" in system:
            return self._detective_response(last_user)
        else:
            return self._suspect_response(last_user)

    def _detective_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        names = self._suspect_names or ["Suspect A", "Suspect B", "Suspect C"]

        if "present your conclusions" in prompt_lower or "make your accusation" in prompt_lower:
            name = names[0]
            return (
                f"[THINKING]The evidence is overwhelming against {name}.[/THINKING]"
                f"Ladies and gentlemen, I have gathered you here to reveal the truth.\n\n"
                f"The evidence points unmistakably to {name}. "
                f"The timeline, the motive, and the physical evidence all converge.\n\n"
                f"I accuse {name} of this crime. "
                f"The method was calculated, the motive was clear, and the opportunity was undeniable.\n\n"
                f"Justice demands an answer, and the answer is {name}."
            )

        if "only your analysis" in prompt_lower or "analyze the situation" in prompt_lower:
            return (
                f"[THINKING]I need to consider all the evidence carefully.[/THINKING]"
                f"The evidence points toward {names[0]}. The timeline and motive are compelling."
            )

        if "based on your analysis" in prompt_lower:
            name = names[self._call_count % len(names)]
            return (
                f"[THINKING]I should question {name} next.[/THINKING]"
                f"I wish to question {name}. Tell me, where exactly were you at the time of the crime?"
            )

        if "cross-examin" in prompt_lower or "contradiction" in prompt_lower:
            name = names[self._call_count % len(names)]
            return (
                f"[THINKING]{name}'s story doesn't hold up.[/THINKING]"
                f"I must confront {name}. Your earlier statement contradicts the evidence."
            )

        if "time is pressing" in prompt_lower or "running short" in prompt_lower:
            name = names[0]
            return (
                f"[THINKING]I have enough evidence. Time to accuse.[/THINKING]"
                f"I am ready to make my accusation."
            )

        # Regular interrogation
        name = names[self._call_count % len(names)]
        return (
            f"[THINKING]I should press {name} on their alibi.[/THINKING]"
            f"I wish to question {name}. Can you account for your movements that evening?"
        )

    def _suspect_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        responses = [
            "[THINKING]I must stay calm and stick to my story.[/THINKING]I assure you, I have nothing to hide. I was exactly where I said I was.",
            "[THINKING]This question is getting too close to the truth.[/THINKING]That is a fair question. I maintain my earlier account entirely.",
            "[THINKING]I should redirect suspicion.[/THINKING]I resent the implication! Perhaps you should look more carefully at the others.",
            "[THINKING]I need to be careful here.[/THINKING]Well, if you must know, there are details I omitted — but they are personal, not criminal.",
            "[THINKING]I must seem cooperative.[/THINKING]I want to help. I saw nothing unusual that evening.",
        ]

        if "react" in prompt_lower or "accused" in prompt_lower:
            return (
                "[THINKING]This is the moment of truth.[/THINKING]"
                "This is outrageous! I demand to know the grounds for this accusation!"
            )

        if "interjection" in prompt_lower or "you just heard" in prompt_lower:
            if random.random() < 0.4:
                return "[THINKING]I should stay silent.[/THINKING]..."
            return (
                "[THINKING]I should speak up.[/THINKING]"
                "That's not what happened at all! I was there and I saw differently."
            )

        return random.choice(responses)


# ── Prompt builders ───────────────────────────────────────────────────────────

def get_pressure_tier(beat_count: int, total_budget: int = 72) -> str:
    """Return emotional pressure tier based on progress through the story."""
    ratio = beat_count / total_budget
    if ratio < 0.35:
        return "early"
    elif ratio < 0.65:
        return "mid"
    else:
        return "late"


def get_pressure_framing(tier: str) -> str:
    """Return subtle prompt framing for emotional escalation."""
    if tier == "early":
        return "The atmosphere is formal and measured. Everyone is composed, guarded, sticking to their prepared accounts."
    elif tier == "mid":
        return "The tension in the room is rising. Cracks are beginning to show. Some are growing defensive, others nervous."
    else:
        return "The pressure is immense. Composure is crumbling. Desperation colors every word. This is the final stretch."


def build_suspect_system_prompt(suspect: dict, story: dict) -> str:
    guilty_text = "You ARE the murderer." if suspect["is_guilty"] else "You are NOT the murderer."
    guilty_rules = (
        "Lie convincingly. Stick to your alibi. Deflect suspicion onto others. "
        "Stay calm. Don't confess unless cornered with overwhelming evidence, "
        "and even then, try to explain it away. Be clever."
        if suspect["is_guilty"]
        else "Tell the truth about what you know, but you may try to hide your own secrets "
        "(affairs, debts, etc.) that make you look suspicious. If pressed hard on your "
        "secrets, you may eventually reveal them reluctantly."
    )
    secrets_list = "\n".join(f"  - {s}" for s in suspect["secrets"])

    # Disguise identity support
    disguise = suspect.get("disguise_identity")
    if disguise:
        identity_block = (
            f"You are posing as {disguise['name']}, {disguise['role']}. "
            f"Your true identity is {suspect['name']}. "
            f"Maintain your cover identity convincingly. "
            f"Do NOT reveal your true identity unless the detective presents overwhelming evidence."
        )
        display_name = disguise["name"]
        display_role = disguise["role"]
    else:
        identity_block = ""
        display_name = suspect["name"]
        display_role = suspect["role"]

    return f"""You are {display_name}, {display_role} in a murder mystery.
{identity_block}

SETTING: {story['setting']}
VICTIM: {story['victim']['name']} — {story['victim']['description']}

BACKGROUND: {suspect['public_info']} {suspect['private_info']}

YOUR SECRETS:
{secrets_list}

YOUR ALIBI: {suspect['alibi']}

IMPORTANT RULES:
- {guilty_text} {guilty_rules}
- Stay in character for the setting and era.
- Respond naturally — show emotion, get defensive, be nervous, be indignant — whatever fits.
- CRITICAL: Keep your response to 2-3 sentences of spoken dialogue (~25 words). This is a single moment — one thought, one reaction, one answer. Minimal stage directions.
- You can accuse other suspects or express suspicions about them.
- You MUST include spoken words in every response. No response of only actions or stage directions.

RESPONSE FORMAT:
Before responding in character, write a BRIEF internal thought inside [THINKING] tags — 2 sentences maximum. Then respond in character after the closing tag.

Example:
[THINKING]The detective is getting close. I need to redirect attention.[/THINKING]
I assure you, I was reading all evening. Perhaps you should ask the solicitor what he saw."""


def build_detective_system_prompt(story: dict) -> str:
    suspects_info = "\n".join(
        f"  - {s['name']} ({s['role']}): {s['public_info']}" for s in story["suspects"]
    )
    detective_style = story.get("detective_style", "brilliant and methodical")

    return f"""You are the detective investigating this case. Your style: {detective_style}.

SETTING: {story['setting']}
CRIME SCENE: {story['crime_scene']}
VICTIM: {story['victim']['name']} — {story['victim']['description']}

SUSPECTS:
{suspects_info}

Your job: interrogate the suspects, find contradictions, examine evidence, determine the killer.

APPROACH:
- Ask pointed, specific questions — one or two per turn
- Look for inconsistencies between suspects' accounts
- Pay attention to timelines and alibis
- Consider motive, means, and opportunity
- When evidence is revealed, use it to press suspects

CRITICAL: Keep responses to 2-3 sentences (~25 words). One question, one observation. Brief and sharp.

RESPONSE FORMAT:
Before responding in character, write a BRIEF internal thought inside [THINKING] tags — 2 sentences maximum. Then respond in character after the closing tag.

IMPORTANT: When questioning a suspect, state their FULL NAME clearly so the engine knows who you're addressing."""


# ── Suspect name extraction ───────────────────────────────────────────────────

def extract_target_suspect(text: str, suspect_names: list[str]) -> str | None:
    """Find which suspect the detective wants to question."""
    text_lower = text.lower()
    best = None
    best_pos = len(text_lower) + 1
    for name in suspect_names:
        pos = text_lower.find(name.lower())
        if pos != -1 and pos < best_pos:
            best = name
            best_pos = pos
        last = name.split()[-1].lower()
        pos = text_lower.find(last)
        if pos != -1 and pos < best_pos:
            best = name
            best_pos = pos
    return best


# ── Thinking extraction ───────────────────────────────────────────────────────

def extract_thinking(text):
    """Extract thinking and dialogue from a response."""
    match = re.search(r'\[THINKING\](.*?)\[/THINKING\]', text, re.DOTALL)
    if match:
        thinking = match.group(1).strip()
        dialogue = text[match.end():].strip()
        return thinking, dialogue
    return None, text


# ── Game Engine ───────────────────────────────────────────────────────────────

class MysteryGame:
    # Phase-specific token limits and temperatures
    PHASE_CONFIG = {
        "interrogation": {"max_tokens": 256, "temperature": 0.85},
        "cross_examination": {"max_tokens": 384, "temperature": 0.75},
        "conclusion": {"max_tokens": 768, "temperature": 0.6},
        "reaction": {"max_tokens": 256, "temperature": 0.9},
    }

    def __init__(self, story_path: str, client, config: dict, detective_model: str | None = None):
        with open(story_path) as f:
            self.story = json.load(f)

        self.client = client
        self.config = config
        self.pause = 0.5 if isinstance(client, DryRunClient) else 1.5

        # Tell DryRunClient about suspect names
        if isinstance(client, DryRunClient):
            client.set_suspect_names([s["name"] for s in self.story["suspects"]])

        # Assign models
        suspects_models = config["default_models"]["suspects"]
        self.detective_model = detective_model or config["default_models"]["detective"]

        self.suspect_models = {}
        self.suspect_colors = {}
        self.suspect_histories: dict[str, list[dict]] = {}

        for i, suspect in enumerate(self.story["suspects"]):
            name = suspect["name"]
            self.suspect_models[name] = suspects_models[i % len(suspects_models)]
            self.suspect_colors[name] = CHARACTER_COLORS[i % len(CHARACTER_COLORS)]
            self.suspect_histories[name] = [
                {"role": "system", "content": build_suspect_system_prompt(suspect, self.story)}
            ]

        self.detective_history: list[dict] = [
            {"role": "system", "content": build_detective_system_prompt(self.story)}
        ]

        self.transcript: list[dict] = []
        self.suspect_names = [s["name"] for s in self.story["suspects"]]
        self.question_counts: dict[str, int] = {s["name"]: 0 for s in self.story["suspects"]}
        self.last_evidence_targets: list[str] = []
        self.last_evidence_text: str = ""
        self.accusation_text: str = ""

        # V3: Beat counter
        self.beat_id = 0
        self.beat_budget = 72

        # V3: Location tracking
        self.locations = self.story.get("locations", {})
        self.suspect_locations: dict[str, str] = {}
        for s in self.story["suspects"]:
            self.suspect_locations[s["name"]] = s.get("location_initial", "drawing_room")
        # Room log: location -> list of recent dialogue texts
        self.room_log: dict[str, list[str]] = {loc: [] for loc in self.locations}

        # Default gathering location (first location or drawing_room)
        location_keys = list(self.locations.keys())
        self.gathering_location = "drawing_room" if "drawing_room" in self.locations else (
            location_keys[0] if location_keys else "main_room"
        )

    def _next_beat_id(self) -> int:
        self.beat_id += 1
        return self.beat_id

    def _log(self, phase: str, speaker: str, text: str, model: str = "",
             thinking: str = None, location: str = "", characters_present: list[str] = None,
             shot_type: str = "dialogue", mood: str = "neutral"):
        """Log a production beat to the transcript."""
        entry = {
            "beat_id": self._next_beat_id(),
            "phase": phase,
            "speaker": speaker,
            "text": text,
            "location": location,
            "characters_present": characters_present or [],
            "shot_type": shot_type,
            "mood": mood,
            "thinking": thinking,
            "model": model,
        }
        self.transcript.append(entry)

    def _characters_at(self, location: str) -> list[str]:
        """Return list of suspect names at a given location."""
        return [name for name, loc in self.suspect_locations.items() if loc == location]

    def _move_all_to(self, location: str):
        """Move all suspects to the same location."""
        for name in self.suspect_locations:
            self.suspect_locations[name] = location

    def _get_phase_config(self, phase_key: str) -> dict:
        return self.PHASE_CONFIG.get(phase_key, {"max_tokens": 256, "temperature": 0.85})

    def _ask_detective(self, user_msg: str, split_mode: bool = False,
                       phase_key: str = "interrogation") -> tuple[str, str | None]:
        cfg = self._get_phase_config(phase_key)

        if split_mode:
            # First call: reasoning only
            analysis_prompt = (
                user_msg + "\n\nBefore acting, analyze the situation internally. "
                "What contradictions have you found? Who is your prime suspect? What is your strategy? "
                "Provide ONLY your analysis — do not ask a question yet."
            )
            self.detective_history.append({"role": "user", "content": analysis_prompt})
            analysis_reply = self.client.chat(
                self.detective_model, self.detective_history,
                temperature=cfg["temperature"], max_tokens=cfg["max_tokens"]
            )
            self.detective_history.append({"role": "assistant", "content": analysis_reply})

            # Second call: act on analysis
            action_prompt = (
                "Based on your analysis, now ask a specific, pointed question to a specific suspect. "
                "State their full name and your question. Keep it to 2-3 sentences."
            )
            self.detective_history.append({"role": "user", "content": action_prompt})
            action_reply = self.client.chat(
                self.detective_model, self.detective_history,
                temperature=cfg["temperature"], max_tokens=cfg["max_tokens"]
            )
            thinking, dialogue = extract_thinking(action_reply)
            self.detective_history.append({"role": "assistant", "content": action_reply})
            _, analysis_clean = extract_thinking(analysis_reply)
            return dialogue, analysis_clean
        else:
            self.detective_history.append({"role": "user", "content": user_msg})
            reply = self.client.chat(
                self.detective_model, self.detective_history,
                temperature=cfg["temperature"], max_tokens=cfg["max_tokens"]
            )
            thinking, dialogue = extract_thinking(reply)
            self.detective_history.append({"role": "assistant", "content": reply})
            return dialogue, thinking

    def _ask_suspect(self, name: str, user_msg: str,
                     phase_key: str = "interrogation") -> tuple[str, str | None]:
        cfg = self._get_phase_config(phase_key)
        self.suspect_histories[name].append({"role": "user", "content": user_msg})
        reply = self.client.chat(
            self.suspect_models[name], self.suspect_histories[name],
            temperature=cfg["temperature"], max_tokens=cfg["max_tokens"]
        )
        thinking, dialogue = extract_thinking(reply)
        self.suspect_histories[name].append({"role": "assistant", "content": reply})
        return dialogue, thinking

    def _build_overhear_context(self, target_name: str) -> str:
        """Build context of what a suspect has overheard in their current location."""
        location = self.suspect_locations.get(target_name, "")
        log = self.room_log.get(location, [])
        if not log:
            return ""
        recent = log[-3:]  # last 3 exchanges
        return "You overheard nearby: " + " | ".join(recent) + "\n\n"

    def _try_interjection(self, location: str, speaker_name: str, dialogue: str,
                          phase: str) -> None:
        """After a potentially contradictory statement, give present suspects a chance to react."""
        # Only trigger on certain keywords suggesting contradiction
        contradiction_signals = ["never", "wasn't there", "impossible", "that's not true",
                                 "didn't see", "lie", "couldn't have", "deny", "wrong"]
        if not any(sig in dialogue.lower() for sig in contradiction_signals):
            return

        present = self._characters_at(location)
        present = [n for n in present if n != speaker_name]
        if not present:
            return

        # Pick one random present suspect to potentially interject
        reactor = random.choice(present)
        prompt = (
            f"You just heard {speaker_name} say: \"{dialogue}\"\n\n"
            f"If you have something relevant to add or challenge, speak up briefly (1-2 sentences). "
            f"If you have nothing to add, respond with only '...' to remain silent."
        )
        react_dialogue, react_thinking = self._ask_suspect(reactor, prompt, phase_key="interrogation")

        # If they chose silence, skip
        if react_dialogue.strip() in ("...", "…", ""):
            return

        color = self.suspect_colors[reactor]
        character_say(reactor, color, react_dialogue, react_thinking)
        self._log(
            phase, reactor, react_dialogue, self.suspect_models[reactor],
            react_thinking, location=location,
            characters_present=self._characters_at(location),
            shot_type="reaction", mood="tense"
        )

        # Feed interjection to detective
        self.detective_history.append(
            {"role": "user", "content": f"{reactor} interjects: {react_dialogue}"}
        )

    # ── Phases ────────────────────────────────────────────────────────────────

    def phase_scene_setting(self):
        """Narrated cold open — no API calls. Tells the story of what happened."""
        header("SCENE SETTING")

        first_location = list(self.locations.keys())[0] if self.locations else ""

        # Beat 1: Establish the setting
        narrator_say(self.story["setting"])
        self._log("scene_setting", "narrator", self.story["setting"],
                  location=first_location,
                  shot_type="establishing", mood="ominous")
        dramatic_pause(self.pause)

        # Beat 2: The murder — frame it as a discovery
        victim = self.story["victim"]
        # Use just the first sentence of the description for the announcement
        victim_brief = victim['description'].split('.')[0].rstrip()
        murder_text = (
            f"A body has been found. {victim['name']} — {victim_brief} — is dead."
        )
        narrator_say(murder_text)
        self._log("scene_setting", "narrator", murder_text,
                  location=first_location,
                  shot_type="establishing", mood="somber")
        dramatic_pause(self.pause)

        # Beat 3: Victim background (if description has more than one sentence)
        victim_sentences = [s.strip() for s in victim['description'].split('.') if s.strip()]
        if len(victim_sentences) > 1:
            background_text = '. '.join(victim_sentences[1:]) + '.'
            narrator_say(background_text)
            self._log("scene_setting", "narrator", background_text,
                      location=first_location,
                      shot_type="establishing", mood="somber")
            dramatic_pause(self.pause)

        # Crime scene details
        narrator_say(self.story["crime_scene"])
        self._log("scene_setting", "narrator", self.story["crime_scene"],
                  location=first_location,
                  shot_type="evidence", mood="ominous")
        dramatic_pause(self.pause)

        # A detective is called in
        detective_style = self.story.get("detective_style", "brilliant and methodical")
        arrival_text = (
            f"A detective has been called in — {detective_style}. "
            f"The suspects have been gathered. The investigation begins."
        )
        narrator_say(arrival_text)
        self._log("detective_arrival", "narrator", arrival_text,
                  location=first_location,
                  shot_type="establishing", mood="determined")
        dramatic_pause(self.pause)

        # Feed scene to detective context
        scene_msg = (
            f"You arrive at the scene. {self.story['crime_scene']}\n\n"
            f"The victim: {victim['name']} — {victim['description']}\n\n"
            f"The suspects are: {', '.join(self.suspect_names)}.\n\n"
            f"You will now hear brief introductions of each person of interest."
        )
        self.detective_history.append({"role": "user", "content": scene_msg})

    def phase_character_introductions(self):
        """Engine-narrated character introductions — no API calls."""
        header("THE SUSPECTS")

        # Transition beat: set up the introductions
        count = len(self.story["suspects"])
        intro_lead = f"{count} individuals have been identified as persons of interest."
        narrator_say(intro_lead)
        self._log("character_introductions", "narrator", intro_lead,
                  shot_type="transition", mood="neutral")
        dramatic_pause(self.pause)

        intros = []
        for suspect in self.story["suspects"]:
            name = suspect["name"]
            disguise = suspect.get("disguise_identity")
            display_name = disguise["name"] if disguise else name
            display_role = disguise["role"] if disguise else suspect["role"]

            # Build a natural introduction from public info
            intro_text = f"{display_name} — {display_role}. {suspect['public_info']}"

            color = self.suspect_colors[name]
            sub_header(display_name)
            narrator_say(intro_text)
            self._log(
                "character_introductions", "narrator", intro_text,
                location=self.suspect_locations.get(name, ""),
                characters_present=[name],
                shot_type="dialogue", mood="neutral"
            )
            intros.append(f"{display_name} ({display_role}): {suspect['public_info']}")
            dramatic_pause(self.pause)

        # Feed all intros to detective as briefing
        briefing = "Background briefing on the suspects:\n\n" + "\n\n".join(intros)
        self.detective_history.append({"role": "user", "content": briefing})

    def phase_interrogation_round(self, round_num: int, max_questions: int = 3):
        """Interrogation round with location-aware interactions."""
        header(f"INTERROGATION — Round {round_num}")

        tier = get_pressure_tier(self.beat_id, self.beat_budget)
        framing = get_pressure_framing(tier)

        for q in range(max_questions):
            if self.beat_id >= self.beat_budget - 7:
                break  # Reserve beats for conclusion

            sub_header(f"Question {q + 1}")

            # Rotation hint
            min_count = min(self.question_counts.values())
            least_questioned = [n for n, c in self.question_counts.items() if c == min_count]
            rotation_hint = ""
            if len(least_questioned) < len(self.suspect_names):
                rotation_hint = f"\nConsider: {', '.join(least_questioned)} have barely been questioned."

            prompt = (
                f"Interrogation round {round_num}, question {q + 1} of {max_questions}. "
                f"{framing} "
                f"Choose a suspect to question and ask your question. "
                f"State their full name, then your question (2-3 sentences). "
                f"Available suspects: {', '.join(self.suspect_names)}.{rotation_hint}"
            )

            det_dialogue, det_thinking = self._ask_detective(prompt, split_mode=True,
                                                              phase_key="interrogation")
            character_say("DETECTIVE", DETECTIVE_COLOR, det_dialogue, det_thinking)

            target = extract_target_suspect(det_dialogue, self.suspect_names)
            if not target:
                target = self.suspect_names[q % len(self.suspect_names)]
                narrator_say(f"(The detective addresses {target})")

            target_location = self.suspect_locations.get(target, self.gathering_location)
            self._log(
                f"interrogation_r{round_num}", "detective", det_dialogue,
                self.detective_model, det_thinking,
                location=target_location,
                characters_present=["detective"] + self._characters_at(target_location),
                shot_type="dialogue", mood="inquisitive"
            )
            dramatic_pause(self.pause)

            self.question_counts[target] = self.question_counts.get(target, 0) + 1
            color = self.suspect_colors[target]

            # Build suspect prompt with evidence and overhear context
            overhear = self._build_overhear_context(target)
            suspect_prompt = f"{overhear}The detective asks you: {det_dialogue}"

            if self.last_evidence_targets and target in self.last_evidence_targets and self.last_evidence_text:
                suspect_prompt = (
                    f"New evidence has been revealed: {self.last_evidence_text}\n"
                    f"You MUST directly address this evidence. "
                    f"Explain, deny, or deflect — but you cannot ignore it.\n\n"
                    f"{suspect_prompt}"
                )

            # Add pressure framing
            suspect_prompt += f"\n\n{framing} Keep your response to 2-3 sentences."

            sus_dialogue, sus_thinking = self._ask_suspect(target, suspect_prompt,
                                                            phase_key="interrogation")
            character_say(target, color, sus_dialogue, sus_thinking)
            self._log(
                f"interrogation_r{round_num}", target, sus_dialogue,
                self.suspect_models[target], sus_thinking,
                location=target_location,
                characters_present=self._characters_at(target_location),
                shot_type="dialogue", mood="defensive" if tier != "early" else "guarded"
            )

            # Update room log
            if target_location in self.room_log:
                self.room_log[target_location].append(f"{target}: {sus_dialogue[:80]}")

            dramatic_pause(self.pause)

            # Feed response to detective (dialogue only)
            self.detective_history.append(
                {"role": "user", "content": f"{target} responds: {sus_dialogue}"}
            )

            # Try interjection from present suspects
            self._try_interjection(target_location, target, sus_dialogue,
                                   f"interrogation_r{round_num}")

    def phase_evidence_reveal(self, round_num: int):
        evidence = [e for e in self.story["evidence_reveals"] if e["round"] == round_num]
        if not evidence:
            self.last_evidence_targets = []
            self.last_evidence_text = ""
            return

        header(f"EVIDENCE — Round {round_num}")
        all_targets = []
        all_clues = []
        for ev in evidence:
            evidence_say(ev["clue"])
            self._log("evidence_reveal", "narrator", ev["clue"],
                      shot_type="evidence", mood="revelatory")
            all_clues.append(ev["clue"])
            all_targets.extend(ev.get("targets", []))

            # Inform detective (as user message only — no fake assistant reply)
            self.detective_history.append(
                {"role": "user", "content": f"NEW EVIDENCE discovered:\n\n{ev['clue']}"}
            )
            dramatic_pause(self.pause)

        self.last_evidence_targets = all_targets
        self.last_evidence_text = " ".join(all_clues)

    def phase_cross_examination(self):
        """Cross-examination — all suspects gathered in one location."""
        header("CROSS-EXAMINATION")

        # Move everyone to gathering location
        self._move_all_to(self.gathering_location)
        narrator_say("All suspects have been gathered together. The detective confronts them directly.")
        self._log("cross_examination", "narrator",
                  f"All suspects are gathered for cross-examination.",
                  location=self.gathering_location,
                  characters_present=["detective"] + self.suspect_names,
                  shot_type="group", mood="tense")
        dramatic_pause(self.pause)

        tier = get_pressure_tier(self.beat_id, self.beat_budget)
        framing = get_pressure_framing("late")  # Cross-exam is always late pressure

        max_confrontations = min(4, self.beat_budget - self.beat_id - 10)
        if max_confrontations < 1:
            max_confrontations = 2

        for q in range(max_confrontations):
            sub_header(f"Confrontation {q + 1}")
            prompt = (
                f"{framing} "
                "You now cross-examine. Confront a suspect with a SPECIFIC CONTRADICTION "
                "between their earlier statements and the evidence. "
                "Reference what they said vs what the evidence shows. "
                f"State their full name. Keep to 2-3 sentences. "
                f"Suspects present: {', '.join(self.suspect_names)}. "
                "If you have enough information, say 'I am ready to make my accusation.'"
            )
            det_dialogue, det_thinking = self._ask_detective(prompt, split_mode=True,
                                                              phase_key="cross_examination")
            character_say("DETECTIVE", DETECTIVE_COLOR, det_dialogue, det_thinking)
            self._log("cross_examination", "detective", det_dialogue,
                      self.detective_model, det_thinking,
                      location=self.gathering_location,
                      characters_present=["detective"] + self.suspect_names,
                      shot_type="dialogue", mood="intense")
            dramatic_pause(self.pause)

            if "ready to make my accusation" in det_dialogue.lower():
                break

            target = extract_target_suspect(det_dialogue, self.suspect_names)
            if not target:
                target = self.suspect_names[q % len(self.suspect_names)]
                narrator_say(f"(The detective addresses {target})")

            color = self.suspect_colors[target]
            suspect_prompt = (
                f"The detective confronts you with a contradiction: {det_dialogue}\n\n"
                f"{framing} "
                "You must: (a) confess what you're hiding, "
                "(b) provide a new explanation, or "
                "(c) deflect by accusing another suspect. "
                "You CANNOT simply deny. Keep to 2-3 sentences."
            )
            sus_dialogue, sus_thinking = self._ask_suspect(target, suspect_prompt,
                                                            phase_key="cross_examination")
            character_say(target, color, sus_dialogue, sus_thinking)
            self._log("cross_examination", target, sus_dialogue,
                      self.suspect_models[target], sus_thinking,
                      location=self.gathering_location,
                      characters_present=self._characters_at(self.gathering_location),
                      shot_type="dialogue", mood="desperate")
            dramatic_pause(self.pause)

            # Feed to detective
            self.detective_history.append(
                {"role": "user", "content": f"{target} responds: {sus_dialogue}"}
            )

            # Try interjection from other present suspects
            self._try_interjection(self.gathering_location, target, sus_dialogue,
                                   "cross_examination")

    def phase_conclusion(self):
        """Detective presents conclusions — natural flow, no forced parlor scene."""
        header("THE ACCUSATION")

        # Move everyone to gathering location if not already
        self._move_all_to(self.gathering_location)
        narrator_say("The detective is ready to present the truth.")
        self._log("conclusion", "narrator",
                  "The detective prepares to reveal the truth.",
                  location=self.gathering_location,
                  characters_present=["detective"] + self.suspect_names,
                  shot_type="group", mood="climactic")
        dramatic_pause(self.pause * 2)

        prompt = (
            "You've gathered significant evidence and questioned all suspects. "
            "Present your conclusions now. Walk through the evidence, the timeline, "
            "the contradictions you found. Then name the murderer.\n\n"
            "Structure your response as 3-4 distinct paragraphs, each making one key point. "
            "Be theatrical. This is your moment of revelation."
        )
        det_dialogue, det_thinking = self._ask_detective(prompt, phase_key="conclusion")
        self.accusation_text = det_dialogue

        # Split accusation into multiple beats by paragraph
        paragraphs = [p.strip() for p in det_dialogue.split("\n\n") if p.strip()]
        if len(paragraphs) <= 1:
            # Try splitting by sentences if no paragraph breaks
            paragraphs = [s.strip() + "." for s in det_dialogue.split(". ") if s.strip()]
            # Group into chunks of 2-3 sentences
            if len(paragraphs) > 4:
                grouped = []
                for i in range(0, len(paragraphs), 2):
                    grouped.append(" ".join(paragraphs[i:i+2]))
                paragraphs = grouped

        for i, para in enumerate(paragraphs):
            print()
            character_say("DETECTIVE", DETECTIVE_COLOR, para, det_thinking if i == 0 else None)
            self._log("conclusion", "detective", para,
                      self.detective_model, det_thinking if i == 0 else None,
                      location=self.gathering_location,
                      characters_present=["detective"] + self.suspect_names,
                      shot_type="dialogue", mood="revelatory")
            dramatic_pause(self.pause)

        dramatic_pause(self.pause * 2)

    def phase_reactions(self):
        """Suspects react — tailored prompts for guilty vs innocent."""
        header("REACTIONS")
        narrator_say("The suspects react to the accusation...")
        self._log("reactions", "narrator", "The suspects react to the accusation.",
                  location=self.gathering_location,
                  characters_present=self.suspect_names,
                  shot_type="group", mood="climactic")
        dramatic_pause(self.pause)

        accused_name = extract_target_suspect(self.accusation_text, self.suspect_names) or "someone"
        solution_data = self.story.get("solution_data", {})

        for suspect in self.story["suspects"]:
            name = suspect["name"]
            color = self.suspect_colors[name]
            sub_header(f"{name} reacts")

            # Tailored reaction prompts
            if suspect["is_guilty"]:
                prompt = (
                    f"The detective has accused {accused_name} of the crime, saying: "
                    f"\"{self.accusation_text[:300]}\"\n\n"
                    "You are the guilty party. React — you may confess, break down, "
                    "make a final desperate denial, or acknowledge you've been caught. "
                    "Keep to 2-3 sentences. Be dramatic."
                )
            elif any(s for s in suspect.get("secrets", []) if "saw" in s.lower() or "know" in s.lower()):
                # Innocent but has specific knowledge
                prompt = (
                    f"The detective has accused {accused_name}, saying: "
                    f"\"{self.accusation_text[:300]}\"\n\n"
                    "React. You have information that's relevant — reference what you know. "
                    "Keep to 2-3 sentences."
                )
            else:
                prompt = (
                    f"The detective has accused {accused_name}, saying: "
                    f"\"{self.accusation_text[:300]}\"\n\n"
                    "React. Express shock, relief, vindication, or accusation. "
                    "Keep to 2-3 sentences."
                )

            dialogue, thinking = self._ask_suspect(name, prompt, phase_key="reaction")
            character_say(name, color, dialogue, thinking)
            self._log("reactions", name, dialogue, self.suspect_models[name], thinking,
                      location=self.gathering_location,
                      characters_present=self.suspect_names,
                      shot_type="reaction", mood="emotional")
            dramatic_pause(self.pause)

    def phase_reveal(self):
        header("THE REVEAL")

        # Check if detective got it right
        guilty_suspects = [s for s in self.story["suspects"] if s["is_guilty"]]
        all_guilty = len(guilty_suspects) == len(self.story["suspects"])
        det_accusation = self.accusation_text

        acc_lower = det_accusation.lower()
        if all_guilty:
            collective_phrases = ["all of you", "every one of you", "all six", "each of you",
                                  "conspiracy", "conspired", "all guilty", "you all",
                                  "every single", "all participated", "each stabbed"]
            correct = any(phrase in acc_lower for phrase in collective_phrases)
        else:
            guilty = guilty_suspects[0]
            correct = guilty["name"].lower() in acc_lower

        if correct:
            print(f"  {Fore.GREEN}{'★' * 20}{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}  THE DETECTIVE WAS CORRECT!  {Style.RESET_ALL}")
            print(f"  {Fore.GREEN}{'★' * 20}{Style.RESET_ALL}")
        else:
            print(f"  {Fore.RED}{'✗' * 20}{Style.RESET_ALL}")
            print(f"  {Fore.RED}  THE DETECTIVE WAS WRONG!  {Style.RESET_ALL}")
            print(f"  {Fore.RED}{'✗' * 20}{Style.RESET_ALL}")

        # Scoring
        solution_data = self.story.get("solution_data", {})
        score_lines = []
        score_lines.append(f"  Correct killer: {'✓ YES' if correct else '✗ NO'}")

        if solution_data.get("motive"):
            motive_words = set(solution_data["motive"].lower().split())
            acc_words = set(acc_lower.split())
            motive_match = len(motive_words & acc_words) / max(len(motive_words), 1) > 0.3
            score_lines.append(f"  Correct motive: {'✓ YES' if motive_match else '✗ NO'}")

        if solution_data.get("method"):
            method_words = set(solution_data["method"].lower().split())
            acc_words = set(acc_lower.split())
            method_match = len(method_words & acc_words) / max(len(method_words), 1) > 0.3
            score_lines.append(f"  Correct method: {'✓ YES' if method_match else '✗ NO'}")

        if score_lines:
            print(f"\n  {PHASE_COLOR}── DETECTIVE'S SCORE ──{Style.RESET_ALL}")
            for sl in score_lines:
                print(sl)
            print()

        narrator_say("THE TRUE SOLUTION:")
        print()
        print(f"  {NARRATOR_COLOR}{self.story['solution']}{Style.RESET_ALL}")
        print()

        self._log("reveal", "narrator", self.story["solution"],
                  shot_type="establishing", mood="resolution")
        self._log("reveal", "result", "CORRECT" if correct else "INCORRECT",
                  shot_type="transition", mood="resolution")
        if score_lines:
            self._log("reveal", "score", "\n".join(score_lines),
                      shot_type="transition", mood="resolution")

    def save_transcript(self):
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        title_slug = re.sub(r'[^a-z0-9]+', '_', self.story["title"].lower()).strip('_')

        transcript_dir = Path(__file__).parent / "transcripts"
        transcript_dir.mkdir(exist_ok=True)

        json_path = transcript_dir / f"{ts}_{title_slug}.json"
        meta = {
            "title": self.story["title"],
            "date": ts,
            "detective_model": self.detective_model,
            "suspect_models": self.suspect_models,
            "total_tokens": self.client.total_tokens,
            "total_beats": self.beat_id,
            "transcript": self.transcript,
        }
        with open(json_path, "w") as f:
            json.dump(meta, f, indent=2)

        # Markdown transcript
        md_path = transcript_dir / f"{ts}_{title_slug}.md"
        lines = [f"# {self.story['title']}", f"*Played on {ts}*\n"]
        current_phase = ""
        for entry in self.transcript:
            if entry["phase"] != current_phase:
                current_phase = entry["phase"]
                lines.append(f"\n## {current_phase.replace('_', ' ').title()}\n")
            if entry.get('thinking'):
                lines.append(f"*💭 {entry['thinking']}*\n")
            beat_meta = f"[Beat {entry['beat_id']}"
            if entry.get("location"):
                beat_meta += f" | {entry['location']}"
            if entry.get("shot_type"):
                beat_meta += f" | {entry['shot_type']}"
            beat_meta += "]"
            lines.append(f"_{beat_meta}_\n")
            lines.append(f"**{entry['speaker']}**: {entry['text']}\n")
        with open(md_path, "w") as f:
            f.write("\n".join(lines))

        print(f"\n  📝 Transcript saved to {json_path}")
        print(f"  📝 Markdown saved to {md_path}")
        print(f"  📊 Total beats: {self.beat_id}")

        # Auto-export HTML viewer
        try:
            export_script = Path(__file__).parent / "export_viewer.py"
            if export_script.exists():
                os.system(f'python3 "{export_script}" "{json_path}"')
                viewer_html = Path(__file__).parent / "viewer" / f"{json_path.stem}.html"
                if viewer_html.exists():
                    webbrowser.open(f"file://{viewer_html.resolve()}")
        except Exception as e:
            print(f"  ⚠️ Could not export viewer: {e}")

    def run(self):
        header(f"🎭 AI MYSTERY THEATER — {self.story['title'].upper()}")
        narrator_say(f"Detective: {self.detective_model}")
        for name, model in self.suspect_models.items():
            color = self.suspect_colors[name]
            print(f"  {color}{name}{Style.RESET_ALL}: {model}")
        print()
        dramatic_pause(self.pause)

        # Scene setting + narrated character introductions (no API calls)
        self.phase_scene_setting()
        self.phase_character_introductions()

        # Interrogation rounds with evidence reveals
        num_evidence_rounds = max(
            (e["round"] for e in self.story.get("evidence_reveals", [])),
            default=3
        )
        for r in range(1, num_evidence_rounds + 1):
            questions_per_round = 3 if r <= 2 else 4
            self.phase_interrogation_round(r, max_questions=questions_per_round)
            self.phase_evidence_reveal(r)

            # Gentle nudge if approaching budget
            if self.beat_id >= self.beat_budget - 12:
                break

        # Cross-examination
        self.phase_cross_examination()

        # Natural flow: check if detective wants to accuse or nudge
        if self.beat_id >= self.beat_budget - 5:
            # Nudge detective
            self.detective_history.append(
                {"role": "user", "content": "Time is pressing. If you have a conclusion, now is the moment."}
            )

        self.phase_conclusion()
        self.phase_reactions()
        self.phase_reveal()
        self.save_transcript()

        print(f"\n  🎭 Total tokens used: {self.client.total_tokens}")
        print(f"  🎭 Total beats: {self.beat_id}")
        header("FIN")


# ── Replay ────────────────────────────────────────────────────────────────────

def replay_transcript(path: str):
    with open(path) as f:
        data = json.load(f)

    header(f"🎭 REPLAY — {data['title'].upper()}")
    print(f"  Detective: {data['detective_model']}")
    for name, model in data.get("suspect_models", {}).items():
        print(f"  {name}: {model}")
    if data.get("total_beats"):
        print(f"  Total beats: {data['total_beats']}")
    print()

    current_phase = ""
    for entry in data["transcript"]:
        if entry["phase"] != current_phase:
            current_phase = entry["phase"]
            sub_header(current_phase.replace("_", " ").title())

        speaker = entry["speaker"]
        text = entry["text"]
        thinking = entry.get("thinking")

        # Show beat metadata if present
        beat_id = entry.get("beat_id")
        location = entry.get("location", "")
        shot_type = entry.get("shot_type", "")
        if beat_id:
            meta_parts = [f"Beat {beat_id}"]
            if location:
                meta_parts.append(location)
            if shot_type:
                meta_parts.append(shot_type)
            print(f"  {Fore.LIGHTBLACK_EX}[{' | '.join(meta_parts)}]{Style.RESET_ALL}")

        if speaker == "narrator":
            narrator_say(text)
        elif speaker == "detective":
            character_say("DETECTIVE", DETECTIVE_COLOR, text, thinking)
        elif speaker == "result":
            if text == "CORRECT":
                print(f"  {Fore.GREEN}★ THE DETECTIVE WAS CORRECT ★{Style.RESET_ALL}")
            else:
                print(f"  {Fore.RED}✗ THE DETECTIVE WAS WRONG ✗{Style.RESET_ALL}")
        elif speaker == "score":
            print(f"  {text}")
        else:
            character_say(speaker, Fore.CYAN, text, thinking)
        time.sleep(0.3)


# ── List stories ──────────────────────────────────────────────────────────────

def list_stories():
    stories_dir = Path(__file__).parent / "stories"
    if not stories_dir.exists():
        print("No stories directory found.")
        return
    print(f"\n{PHASE_COLOR}Available Mysteries:{Style.RESET_ALL}\n")
    for p in sorted(stories_dir.glob("*.json")):
        with open(p) as f:
            data = json.load(f)
        suspects = len(data.get("suspects", []))
        locations = len(data.get("locations", {}))
        style = data.get("detective_style", "classic")
        print(f"  📖 {data['title']} ({suspects} suspects, {locations} locations) — {p.name}")
        print(f"     Detective style: {style}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Mystery Theater — V3 Engine")
    parser.add_argument("--story", help="Path to story JSON file")
    parser.add_argument("--detective", help="Override detective model")
    parser.add_argument("--list", action="store_true", help="List available stories")
    parser.add_argument("--replay", help="Replay a transcript JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Use placeholder responses (no API calls)")
    args = parser.parse_args()

    if args.list:
        list_stories()
        return

    if args.replay:
        replay_transcript(args.replay)
        return

    if not args.story:
        parser.error("--story is required (or use --list / --replay)")

    # Load config
    config_path = Path(__file__).parent / "config.json"
    with open(config_path) as f:
        config = json.load(f)

    # Set up client
    if args.dry_run:
        client = DryRunClient()
        print(f"\n  {Fore.YELLOW}⚠ DRY RUN MODE — using placeholder responses{Style.RESET_ALL}\n")
    else:
        api_key = os.environ.get(config["openrouter_api_key_env"], "")
        if not api_key:
            print(f"\n  {Fore.RED}ERROR: {config['openrouter_api_key_env']} environment variable not set.{Style.RESET_ALL}")
            print(f"  Set it with: export {config['openrouter_api_key_env']}=your-key-here\n")
            sys.exit(1)
        client = OpenRouterClient(api_key)

    game = MysteryGame(args.story, client, config, detective_model=args.detective)
    game.run()


if __name__ == "__main__":
    main()
