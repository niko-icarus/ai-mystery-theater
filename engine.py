#!/usr/bin/env python3
"""AI Mystery Theater — A murder mystery game engine where AI models play characters."""

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

    def chat(self, model: str, messages: list[dict], temperature: float = 0.9) -> str:
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
            "max_tokens": 1024,
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
    """Returns canned responses for testing game flow."""

    DRY_RESPONSES = {
        "detective_question": [
            "I should like to speak with {suspect}. Tell me, where exactly were you between the hours of 10 and 11 PM?",
            "Most interesting. Now I wish to question {suspect}. Can you account for your movements that evening?",
            "The evidence grows clearer. {suspect}, I have some pointed questions for you regarding certain inconsistencies.",
        ],
        "detective_cross": [
            "I must confront {suspect} with what I have discovered. Your alibi does not hold, does it?",
        ],
        "detective_accusation": (
            "Ladies and gentlemen, I have gathered you here to reveal the truth. "
            "After careful examination of the evidence — the cyanide in the brandy, "
            "the visit to the study at 9:45, and the financial discrepancies — "
            "I accuse Dr. Harold Pembrooke of the murder of Lord Thornfield! "
            "He poisoned the brandy under the guise of delivering medication. "
            "The motive: Edmund had discovered Pembrooke's embezzlement and threatened exposure."
        ),
        "suspect_statement": [
            "I assure you, I was nowhere near the study that evening. I have nothing to hide.",
            "This is most distressing. I was fond of Edmund — why would I wish him harm?",
            "I was exactly where I said I was. You may ask anyone.",
            "How dare you imply such a thing! I am a person of impeccable character.",
            "I... I would rather not discuss certain private matters, but I am no murderer.",
        ],
        "suspect_response": [
            "That is a fair question. I maintain my earlier account — I have nothing further to add.",
            "Well, if you must know... there are certain details I omitted, but they are personal, not criminal.",
            "I resent the implication! But very well — I shall tell you what I know.",
            "You are very clever, detective. But you are looking in the wrong direction entirely.",
            "I... suppose I should be honest about that. It is true, I was not entirely forthcoming.",
        ],
    }

    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0.0
        self._call_count = 0

    def chat(self, model: str, messages: list[dict], temperature: float = 0.9) -> str:
        self._call_count += 1
        self.total_tokens += 150  # fake
        last_user = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user = m["content"]
                break

        # Detect what kind of response is needed based on system prompt & context
        system = messages[0]["content"] if messages else ""
        if "brilliant detective" in system:
            return self._detective_response(last_user)
        else:
            return self._suspect_response(last_user)

    def _detective_response(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "final accusation" in prompt_lower or "parlor" in prompt_lower:
            return self.DRY_RESPONSES["detective_accusation"]
        if "only your analysis" in prompt_lower or "analyze the situation" in prompt_lower:
            return "My analysis: the evidence points to Dr. Harold Pembrooke. The timeline and financial motive are compelling."
        if "based on your analysis" in prompt_lower:
            names = ["Dr. Harold Pembrooke", "Lady Margaret Thornfield", "Captain James Ashworth"]
            name = names[self._call_count % len(names)]
            return random.choice(self.DRY_RESPONSES["detective_question"]).format(suspect=name)
        if "cross-examin" in prompt_lower or "confront" in prompt_lower or "contradiction" in prompt_lower:
            names = ["Dr. Harold Pembrooke", "Lady Margaret Thornfield", "Captain James Ashworth"]
            name = names[self._call_count % len(names)]
            return random.choice(self.DRY_RESPONSES["detective_cross"]).format(suspect=name)
        # Regular interrogation — pick a suspect
        names = [
            "Lady Margaret Thornfield",
            "Captain James Ashworth",
            "Dr. Harold Pembrooke",
            "Miss Victoria Thornfield",
            "Mr. Reginald Cross",
        ]
        name = names[self._call_count % len(names)]
        return random.choice(self.DRY_RESPONSES["detective_question"]).format(suspect=name)

    def _suspect_response(self, prompt: str) -> str:
        if "opening statement" in prompt.lower() or "initial statement" in prompt.lower():
            return random.choice(self.DRY_RESPONSES["suspect_statement"])
        if "final moment" in prompt.lower() or "react" in prompt.lower():
            return "This is outrageous! I am innocent and I demand to know on what grounds this accusation is made. I shall have my solicitor here within the hour!"
        return random.choice(self.DRY_RESPONSES["suspect_response"])


# ── Prompt builders ───────────────────────────────────────────────────────────

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

    # Disguise identity support (improvement #2)
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
- Stay in character for the setting.
- Respond naturally — don't be robotic. Show emotion, get defensive, be nervous, be indignant — whatever fits your character.
- Keep responses concise (2-4 sentences for answers, unless telling a story).
- You can accuse other suspects or express suspicions about them.
- You MUST speak at least 2-3 sentences of actual dialogue in every response. Do not respond with only stage directions or actions. You must always include spoken words.

RESPONSE FORMAT:
Before responding in character, write a BRIEF internal thought inside [THINKING] tags — 3 sentences maximum. Focus on your key strategic consideration for this response. Then respond in character after the closing tag.

Example:
[THINKING]The detective is getting close to discovering my affair. I need to redirect attention to the solicitor.[/THINKING]
*adjusting her pearls nervously* I assure you, Detective, I was reading all evening..."""


def build_detective_system_prompt(story: dict) -> str:
    suspects_info = "\n".join(
        f"  - {s['name']} ({s['role']}): {s['public_info']}" for s in story["suspects"]
    )
    return f"""You are a brilliant detective in the tradition of Hercule Poirot. You have been called to Thornfield Manor to investigate the murder of Lord Edmund Thornfield.

CRIME SCENE: {story['crime_scene']}

VICTIM: {story['victim']['name']} — {story['victim']['description']}

SUSPECTS:
{suspects_info}

Your job is to interrogate the suspects, find contradictions in their stories, examine evidence as it's revealed, and determine who committed the murder.

APPROACH:
- Ask pointed, specific questions
- Look for inconsistencies between suspects' accounts
- Pay attention to timelines and alibis
- Consider motive, means, and opportunity
- When evidence is revealed, use it to press suspects
- In the final accusation, lay out your complete reasoning

Be theatrical. Be brilliant. Channel your inner Poirot.
Keep questions focused — one or two questions per turn.

RESPONSE FORMAT:
Before responding in character, write a BRIEF internal thought inside [THINKING] tags — 3 sentences maximum. Focus on your key strategic consideration for this response. Then respond in character after the closing tag.

IMPORTANT: When you want to question a suspect, clearly state their FULL NAME so the game engine knows who you're addressing. For example: "I wish to question Lady Margaret Thornfield." """


# ── Suspect name extraction ───────────────────────────────────────────────────

def extract_target_suspect(text: str, suspect_names: list[str]) -> str | None:
    """Find which suspect the detective wants to question."""
    text_lower = text.lower()
    # Score by position (earlier mention = more likely target)
    best = None
    best_pos = len(text_lower) + 1
    for name in suspect_names:
        # Try full name first
        pos = text_lower.find(name.lower())
        if pos != -1 and pos < best_pos:
            best = name
            best_pos = pos
        # Try last name
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
    def __init__(self, story_path: str, client, config: dict, detective_model: str | None = None):
        with open(story_path) as f:
            self.story = json.load(f)

        self.client = client
        self.config = config
        self.pause = 0.5 if isinstance(client, DryRunClient) else 1.5

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

    def _log(self, phase: str, speaker: str, text: str, model: str = "", thinking: str = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "speaker": speaker,
            "text": text,
            "model": model,
        }
        if thinking:
            entry["thinking"] = thinking
        self.transcript.append(entry)

    def _ask_detective(self, user_msg: str, split_mode: bool = False) -> tuple[str, str | None]:
        if split_mode:
            # First call: reasoning only
            analysis_prompt = (
                user_msg + "\n\nBefore acting, analyze the situation internally. "
                "What contradictions have you found? Who is your prime suspect? What is your strategy? "
                "Provide ONLY your analysis — do not ask a question yet."
            )
            self.detective_history.append({"role": "user", "content": analysis_prompt})
            analysis_reply = self.client.chat(self.detective_model, self.detective_history)
            self.detective_history.append({"role": "assistant", "content": analysis_reply})

            # Second call: act on analysis
            action_prompt = (
                "Based on your analysis, now ask a specific, pointed question to a specific suspect. "
                "State their full name and your question. Be in character."
            )
            self.detective_history.append({"role": "user", "content": action_prompt})
            action_reply = self.client.chat(self.detective_model, self.detective_history)
            thinking, dialogue = extract_thinking(action_reply)
            self.detective_history.append({"role": "assistant", "content": action_reply})
            # Use analysis as the "thinking" for display
            _, analysis_clean = extract_thinking(analysis_reply)
            return dialogue, analysis_clean
        else:
            self.detective_history.append({"role": "user", "content": user_msg})
            reply = self.client.chat(self.detective_model, self.detective_history)
            thinking, dialogue = extract_thinking(reply)
            self.detective_history.append({"role": "assistant", "content": reply})
            return dialogue, thinking

    def _ask_suspect(self, name: str, user_msg: str) -> tuple[str, str | None]:
        self.suspect_histories[name].append({"role": "user", "content": user_msg})
        reply = self.client.chat(self.suspect_models[name], self.suspect_histories[name])
        thinking, dialogue = extract_thinking(reply)
        # Store full reply so this suspect can see own thinking in history
        self.suspect_histories[name].append({"role": "assistant", "content": reply})
        return dialogue, thinking

    # ── Phases ────────────────────────────────────────────────────────────────

    def phase_scene_setting(self):
        header("ACT I — THE CRIME SCENE")
        narrator_say(self.story["setting"])
        dramatic_pause(self.pause)
        narrator_say(self.story["crime_scene"])
        dramatic_pause(self.pause)
        narrator_say(
            f"The victim: {self.story['victim']['name']} — {self.story['victim']['description']}"
        )
        self._log("scene_setting", "narrator", self.story["crime_scene"])

        # Inform detective
        scene_msg = (
            f"You arrive at the scene. {self.story['crime_scene']}\n\n"
            f"The suspects have been gathered in the drawing room. "
            f"They are: {', '.join(self.suspect_names)}.\n\n"
            f"Each will give an opening statement. Listen carefully."
        )
        self.detective_history.append({"role": "user", "content": scene_msg})
        self.detective_history.append({"role": "assistant", "content": "I understand. Let us begin."})

    def phase_initial_statements(self):
        header("ACT II — INITIAL STATEMENTS")
        statements = []
        for suspect in self.story["suspects"]:
            name = suspect["name"]
            color = self.suspect_colors[name]
            sub_header(f"{name} — {suspect['role']}")

            prompt = (
                "The detective has arrived and asks each person present to give their opening statement. "
                "Briefly state who you are, your relationship to the victim, and where you were this evening. "
                "This is your initial statement."
            )
            dialogue, thinking = self._ask_suspect(name, prompt)
            character_say(name, color, dialogue, thinking)
            self._log("initial_statements", name, dialogue, self.suspect_models[name], thinking)
            statements.append(f"{name}: {dialogue}")
            dramatic_pause(self.pause)

        # Feed all statements to detective
        combined = "The suspects have given their opening statements:\n\n" + "\n\n".join(statements)
        self.detective_history.append({"role": "user", "content": combined})
        self.detective_history.append(
            {"role": "assistant", "content": "Très intéressant. I have noted everything. Let us proceed."}
        )

    def phase_interrogation_round(self, round_num: int, max_questions: int = 3):
        header(f"ACT III — INTERROGATION (Round {round_num})")

        for q in range(max_questions):
            sub_header(f"Question {q + 1} of {max_questions}")

            # Build participation hint
            min_count = min(self.question_counts.values())
            least_questioned = [n for n, c in self.question_counts.items() if c == min_count]
            if len(least_questioned) < len(self.suspect_names):
                rotation_hint = f"\nNote: {', '.join(least_questioned)} have barely been questioned. Consider directing your attention to them."
            else:
                rotation_hint = ""

            # Ask detective who to question
            prompt = (
                f"This is interrogation round {round_num}, question {q + 1} of {max_questions}. "
                f"Choose a suspect to question and ask your question. "
                f"State their full name clearly, then your question. "
                f"Available suspects: {', '.join(self.suspect_names)}.{rotation_hint}"
            )
            det_dialogue, det_thinking = self._ask_detective(prompt, split_mode=True)
            character_say("DETECTIVE", DETECTIVE_COLOR, det_dialogue, det_thinking)
            self._log(f"interrogation_r{round_num}", "detective", det_dialogue, self.detective_model, det_thinking)
            dramatic_pause(self.pause)

            # Figure out who's being questioned
            target = extract_target_suspect(det_dialogue, self.suspect_names)
            if not target:
                target = self.suspect_names[q % len(self.suspect_names)]
                narrator_say(f"(The detective addresses {target})")

            self.question_counts[target] = self.question_counts.get(target, 0) + 1
            color = self.suspect_colors[target]

            # Build suspect prompt, with evidence targeting if applicable
            suspect_prompt = f"The detective asks you: {det_dialogue}"
            if self.last_evidence_targets and target in self.last_evidence_targets and self.last_evidence_text:
                suspect_prompt = (
                    f"New evidence has just been revealed: {self.last_evidence_text}\n"
                    f"You MUST directly address this evidence in your response. "
                    f"Explain, deny, or deflect — but you cannot ignore it.\n\n"
                    f"{suspect_prompt}"
                )

            sus_dialogue, sus_thinking = self._ask_suspect(target, suspect_prompt)
            character_say(target, color, sus_dialogue, sus_thinking)
            self._log(f"interrogation_r{round_num}", target, sus_dialogue, self.suspect_models[target], sus_thinking)
            dramatic_pause(self.pause)

            # Feed response back to detective (dialogue only — no suspect thinking)
            self.detective_history.append(
                {"role": "user", "content": f"{target} responds: {sus_dialogue}"}
            )
            self.detective_history.append(
                {"role": "assistant", "content": "Noted. I shall continue my investigation."}
            )

    def phase_evidence_reveal(self, round_num: int):
        evidence = [e for e in self.story["evidence_reveals"] if e["round"] == round_num]
        if not evidence:
            self.last_evidence_targets = []
            self.last_evidence_text = ""
            return
        header(f"EVIDENCE REVEAL — Round {round_num}")
        all_targets = []
        all_clues = []
        for ev in evidence:
            evidence_say(ev["clue"])
            self._log("evidence_reveal", "narrator", ev["clue"])
            all_clues.append(ev["clue"])
            all_targets.extend(ev.get("targets", []))

            # Inform detective
            self.detective_history.append(
                {"role": "user", "content": f"NEW EVIDENCE has been discovered:\n\n{ev['clue']}"}
            )
            self.detective_history.append(
                {"role": "assistant", "content": "Ah-ha! This changes things considerably."}
            )
            dramatic_pause(self.pause)

        self.last_evidence_targets = all_targets
        self.last_evidence_text = " ".join(all_clues)

    def phase_cross_examination(self):
        header("ACT IV — CROSS-EXAMINATION")
        narrator_say("The detective may now confront suspects with specific contradictions.")

        for q in range(3):
            sub_header(f"Confrontation {q + 1}")
            prompt = (
                "You now have the opportunity to cross-examine. "
                "Confront a suspect with a SPECIFIC CONTRADICTION between their earlier statements "
                "and the evidence. You must reference what they said vs what the evidence shows. "
                f"State their full name and your confrontation. "
                f"Available suspects: {', '.join(self.suspect_names)}. "
                "If you feel you have enough information, say 'I am ready to make my accusation.'"
            )
            det_dialogue, det_thinking = self._ask_detective(prompt, split_mode=True)
            character_say("DETECTIVE", DETECTIVE_COLOR, det_dialogue, det_thinking)
            self._log("cross_examination", "detective", det_dialogue, self.detective_model, det_thinking)
            dramatic_pause(self.pause)

            if "ready to make my accusation" in det_dialogue.lower():
                break

            target = extract_target_suspect(det_dialogue, self.suspect_names)
            if not target:
                target = self.suspect_names[q % len(self.suspect_names)]
                narrator_say(f"(The detective addresses {target})")

            color = self.suspect_colors[target]
            suspect_prompt = (
                f"The detective has confronted you with a contradiction: {det_dialogue}\n\n"
                "You must either: (a) confess to what you're hiding, "
                "(b) provide a new explanation that resolves the contradiction, or "
                "(c) deflect by accusing another suspect. "
                "You CANNOT simply deny — you must engage with the specific contradiction."
            )
            sus_dialogue, sus_thinking = self._ask_suspect(target, suspect_prompt)
            character_say(target, color, sus_dialogue, sus_thinking)
            self._log("cross_examination", target, sus_dialogue, self.suspect_models[target], sus_thinking)
            dramatic_pause(self.pause)

            # Feed dialogue only back to detective (no suspect thinking)
            self.detective_history.append(
                {"role": "user", "content": f"{target} responds: {sus_dialogue}"}
            )
            self.detective_history.append(
                {"role": "assistant", "content": "I see. The picture becomes clearer."}
            )

    def phase_parlor_scene(self):
        header("ACT V — THE PARLOR SCENE")
        narrator_say(
            "The detective gathers all suspects in the drawing room. "
            "A fire crackles in the hearth. The tension is palpable."
        )
        dramatic_pause(self.pause * 2)

        prompt = (
            "It is time for your final accusation. You have gathered everyone in the parlor. "
            "Lay out your complete reasoning — walk through the evidence, the timeline, "
            "the contradictions you found. Then name the murderer. "
            "Be theatrical. Be brilliant. This is your Poirot moment."
        )
        det_dialogue, det_thinking = self._ask_detective(prompt)
        print()
        character_say("DETECTIVE", DETECTIVE_COLOR, det_dialogue, det_thinking)
        print()
        self._log("parlor_scene", "detective", det_dialogue, self.detective_model, det_thinking)
        self.accusation_text = det_dialogue
        dramatic_pause(self.pause * 2)

    def phase_reactions(self):
        header("REACTIONS")
        narrator_say("The suspects react to the accusation...")
        dramatic_pause(self.pause)

        # Determine who was accused
        accused_name = extract_target_suspect(self.accusation_text, self.suspect_names) or "someone"

        for suspect in self.story["suspects"]:
            name = suspect["name"]
            # Skip if suspect has a disguise (they're "absent"/the victim)
            # Actually, let all present suspects react
            color = self.suspect_colors[name]
            sub_header(f"{name} reacts")

            prompt = (
                f"The detective has just accused {accused_name} of the murder, saying: "
                f"\"{self.accusation_text}\"\n\n"
                "This is your final moment. React — confess, protest your innocence, break down, "
                "accuse someone else, or reveal a final secret. Be dramatic."
            )
            dialogue, thinking = self._ask_suspect(name, prompt)
            character_say(name, color, dialogue, thinking)
            self._log("reactions", name, dialogue, self.suspect_models[name], thinking)
            dramatic_pause(self.pause)

    def phase_reveal(self):
        header("THE REVEAL")

        # Check if detective got it right
        guilty_suspects = [s for s in self.story["suspects"] if s["is_guilty"]]
        all_guilty = len(guilty_suspects) == len(self.story["suspects"])
        det_accusation = ""
        for entry in reversed(self.transcript):
            if entry["phase"] == "parlor_scene" and entry["speaker"] == "detective":
                det_accusation = entry["text"]
                break

        acc_lower = det_accusation.lower()
        if all_guilty:
            # "Everyone did it" scenario — check for collective accusation language
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

        # Detective accusation scoring (improvement #8)
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

        narrator_say(f"THE TRUE SOLUTION:")
        print()
        print(f"  {NARRATOR_COLOR}{self.story['solution']}{Style.RESET_ALL}")
        print()

        self._log("reveal", "narrator", self.story["solution"])
        self._log("reveal", "result", "CORRECT" if correct else "INCORRECT")
        if score_lines:
            self._log("reveal", "score", "\n".join(score_lines))

    def save_transcript(self):
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        title_slug = re.sub(r'[^a-z0-9]+', '_', self.story["title"].lower()).strip('_')

        # JSON transcript
        transcript_dir = Path(__file__).parent / "transcripts"
        transcript_dir.mkdir(exist_ok=True)

        json_path = transcript_dir / f"{ts}_{title_slug}.json"
        meta = {
            "title": self.story["title"],
            "date": ts,
            "detective_model": self.detective_model,
            "suspect_models": self.suspect_models,
            "total_tokens": self.client.total_tokens,
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
            lines.append(f"**{entry['speaker']}**: {entry['text']}\n")
        with open(md_path, "w") as f:
            f.write("\n".join(lines))

        print(f"\n  📝 Transcript saved to {json_path}")
        print(f"  📝 Markdown saved to {md_path}")

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

        self.phase_scene_setting()
        self.phase_initial_statements()

        # Interrogation rounds with evidence reveals between them
        num_rounds = len(self.story.get("evidence_reveals", [])) or 3
        for r in range(1, num_rounds + 1):
            self.phase_interrogation_round(r, max_questions=2)
            self.phase_evidence_reveal(r)

        self.phase_cross_examination()
        self.phase_parlor_scene()
        self.phase_reactions()
        self.phase_reveal()
        self.save_transcript()

        print(f"\n  🎭 Total tokens used: {self.client.total_tokens}")
        header("FIN")


# ── Replay ────────────────────────────────────────────────────────────────────

def replay_transcript(path: str):
    with open(path) as f:
        data = json.load(f)

    header(f"🎭 REPLAY — {data['title'].upper()}")
    print(f"  Detective: {data['detective_model']}")
    for name, model in data.get("suspect_models", {}).items():
        print(f"  {name}: {model}")
    print()

    current_phase = ""
    for entry in data["transcript"]:
        if entry["phase"] != current_phase:
            current_phase = entry["phase"]
            sub_header(current_phase.replace("_", " ").title())

        speaker = entry["speaker"]
        text = entry["text"]
        thinking = entry.get("thinking")
        if speaker == "narrator":
            narrator_say(text)
        elif speaker == "detective":
            character_say("DETECTIVE", DETECTIVE_COLOR, text, thinking)
        elif speaker == "result":
            if text == "CORRECT":
                print(f"  {Fore.GREEN}★ THE DETECTIVE WAS CORRECT ★{Style.RESET_ALL}")
            else:
                print(f"  {Fore.RED}✗ THE DETECTIVE WAS WRONG ✗{Style.RESET_ALL}")
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
        print(f"  📖 {data['title']} ({suspects} suspects) — {p.name}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Mystery Theater")
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
