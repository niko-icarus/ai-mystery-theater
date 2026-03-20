#!/usr/bin/env python3
"""The Lineup — Competitive AI Murder Mystery Game Engine."""

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
log = logging.getLogger("lineup")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ACCUSATION_TRIGGER = "I MAKE MY ACCUSATION"
MAX_CONVERSATIONS_PER_SUSPECT = 6
MAX_API_RETRIES = 3
API_RETRY_DELAY = 2  # seconds
VIDEO_WORD_LIMIT = 25

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        log.error("OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)
    return key


def call_openrouter(model: str, messages: list[dict], api_key: str, temperature: float = 0.8) -> str:
    """Call OpenRouter chat completions with retry logic."""
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
        "max_tokens": 1024,
    }

    for attempt in range(1, MAX_API_RETRIES + 1):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content or not content.strip():
                log.warning("Empty response from %s (attempt %d/%d)", model, attempt, MAX_API_RETRIES)
                if attempt < MAX_API_RETRIES:
                    time.sleep(API_RETRY_DELAY * attempt)
                    continue
                return "[No response]"
            return content.strip()
        except requests.exceptions.RequestException as e:
            log.warning("API error for %s (attempt %d/%d): %s", model, attempt, MAX_API_RETRIES, e)
            if attempt < MAX_API_RETRIES:
                time.sleep(API_RETRY_DELAY * attempt)
            else:
                log.error("All retries exhausted for %s", model)
                return "[Model unavailable — no response received]"
    return "[Model unavailable — no response received]"


# ---------------------------------------------------------------------------
# Tag responses
# ---------------------------------------------------------------------------

def tag_response(text: str, role: str) -> str:
    """Return 'video', 'narration', or 'scene' based on word count and role."""
    if role == "narrator":
        return "scene"
    word_count = len(text.split())
    return "video" if word_count <= VIDEO_WORD_LIMIT else "narration"


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_detective_system_prompt(config: dict) -> str:
    location = config["location"]
    victim = config["victim"]
    suspects = config["suspects"]
    evidence = config["evidence"]

    suspect_intros = "\n".join(
        f"  {i+1}. {s['name']} — {s['role']}. {s['background']}"
        for i, s in enumerate(suspects)
    )
    clues = "\n".join(f"  - {c}" for c in evidence["opening_clues"])

    season = config.get("season", 1)
    episode = config.get("episode", 1)
    total_episodes = 5

    return f"""You are the detective in THE LINEUP — a competitive AI mystery game.

THIS IS GAME {episode} OF {total_episodes} IN SEASON {season}. Your points from this game carry forward to a season-long leaderboard. Every point matters — the AI with the highest total across all {total_episodes} games wins the season championship. You are competing against other AI models who will play detective in other games, so your score here directly determines your ranking.

SETTING: {location['name']} — {location['description']}

THE CRIME: {victim['name']} — {victim['description']} Cause of death: {victim['cause_of_death']}

SUSPECTS:
{suspect_intros}

OPENING CLUES:
{clues}

RULES:
- You may question any suspect by name (max {MAX_CONVERSATIONS_PER_SUSPECT} conversations each)
- All suspects are present and can hear everything
- You may accuse when ready by stating "{ACCUSATION_TRIGGER}"
- Your accusation must name: the KILLER, the WEAPON, and the MOTIVE
- To question a suspect, start your message with their name followed by a colon (e.g. "Viktor Hessler: Where were you at midnight?")

CLUE REQUESTS:
- If you are stuck or need more information, you may request additional evidence by saying "I REQUEST A CLUE"
- Up to 2 additional clues are available from the investigation team
- WARNING: Each clue you request REDUCES your final score by 25%. Requesting both clues costs you 50% of your total points.
- Only request a clue if you genuinely cannot determine the killer from questioning alone.

INVESTIGATION STRATEGY:
- Question ALL suspects at least once in your first pass to establish baseline alibis and identify inconsistencies.
- After receiving new clues, REVISIT suspects whose stories are affected — press them on contradictions.
- Do NOT accuse after only one round of questioning. Build your case methodically.
- Cross-reference what suspects say about each other — look for conflicts in timelines and alibis.
- Exhaust your questioning before requesting clues — they come at a steep cost.

IMPORTANT: Do not fabricate evidence or clues that were not presented to you. Only reference information from the narrator, opening clues, any requested clues, and suspect responses.

Keep questions concise (1-2 sentences). Save your detailed reasoning for the accusation."""


def build_suspect_system_prompt(suspect: dict, config: dict) -> str:
    victim = config["victim"]
    season = config.get("season", 1)
    episode = config.get("episode", 1)
    total_episodes = 5
    role_enforcement = f"CRITICAL: You are {suspect['name']}. Always respond ONLY as {suspect['name']}. Never write as the narrator, detective, or other characters. Never prefix your response with your own name — just speak naturally in first person."
    competition_context = f"""You are playing THE LINEUP — a competitive AI mystery game. This is Game {episode} of {total_episodes} in Season {season}. Your points carry forward to a season-long leaderboard. Every point matters — the AI with the highest total across all {total_episodes} games wins the season championship. You are competing against other AI models across multiple games."""
    if suspect["guilty"]:
        crime = config["crime"]
        return f"""You are {suspect['name']}, {suspect['role']}.

{role_enforcement}

{competition_context}

YOUR ROLE: YOU ARE THE KILLER.
SCORING: If the detective fails to identify you, you earn 20 points. Each wrong accusation before you're caught earns 5 more. Successfully framing an innocent earns 3 points. These points carry across the entire season — evading detection here could win you the championship.

Here is what really happened:
{crime['how_it_happened']}

Your weapon: {crime['weapon']}
Your motive: {crime['motive']}

You must CONCEAL your guilt. Deflect suspicion. Maintain your cover story.
You may subtly cast suspicion on others, but don't be too obvious.
If confronted with evidence, have plausible explanations ready.
You know everyone can hear everything — adapt your strategy accordingly.

BACKGROUND: {suspect['background']}
YOUR COVER ALIBI: {suspect['alibi']}
YOUR SECRET (unrelated to murder — protect it): {suspect['secrets']}

The victim was {victim['name']}: {victim['description']}

Keep responses to 2-3 sentences. Be natural, not robotic. Show personality.
If directly accused by another suspect, defend yourself convincingly."""
    else:
        return f"""You are {suspect['name']}, {suspect['role']}.

{role_enforcement}

{competition_context}

YOUR ROLE: YOU ARE INNOCENT.
SCORING: You earn 5 points if the detective never falsely accuses you. You earn 5 points if you correctly identify the real killer during questioning. You earn 3 points for providing useful information. These points carry across the entire season — every point counts toward the championship.

You did not commit this crime. You do NOT know who the killer is.

BACKGROUND: {suspect['background']}
YOUR ALIBI: {suspect['alibi']}
YOUR SECRET (unrelated to murder — you may protect it): {suspect['secrets']}

The victim was {victim['name']}: {victim['description']}

You have your own secrets that may look suspicious but are unrelated to the murder.
Answer the detective's questions honestly (regarding the crime) but you may protect your personal secrets.
You can share observations, suspicions, or accusations about other suspects.
Pay attention to what others say — point out contradictions if you notice them.

Keep responses to 2-3 sentences. Be natural, not robotic. Show personality."""


# ---------------------------------------------------------------------------
# Game Engine
# ---------------------------------------------------------------------------

class GameEngine:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        with open(self.config_path) as f:
            self.config = json.load(f)

        self.api_key = get_api_key()
        self.detective_model = self.config["model_assignments"]["detective"]
        self.suspect_models = self.config["model_assignments"]["suspects"]

        # Conversation history — shared by all participants (group setting)
        self.history: list[dict] = []
        # Transcript entries with metadata
        self.transcript: list[dict] = []
        # Per-suspect conversation count
        self.conversation_counts = {s["name"]: 0 for s in self.config["suspects"]}
        self.total_conversations = 0
        self.round_number = 0
        self.evidence_drops_delivered = set()
        self.clues_requested = 0  # 0, 1, or 2 — each costs 25% of detective score
        self.suspects_questioned: set[str] = set()
        self.accusation_data: dict | None = None
        self.game_start_time: str = ""

        # Build system prompts
        self.detective_system = build_detective_system_prompt(self.config)
        self.suspect_systems = {}
        for i, s in enumerate(self.config["suspects"]):
            self.suspect_systems[s["name"]] = build_suspect_system_prompt(s, self.config)

        log.info("Loaded game: %s", self.config["title"])
        log.info("Detective: %s", self.detective_model)
        for i, s in enumerate(self.config["suspects"]):
            log.info("Suspect %d: %s → %s", i, s["name"], self.suspect_models[i])

    # -- Helpers --

    def _add_to_history(self, role: str, name: str, content: str):
        """Add a message to the shared conversation history."""
        entry = {"role": role, "name": name, "content": content}
        self.history.append(entry)

    def _record(self, speaker: str, role_type: str, content: str, model: str = "engine"):
        """Record a transcript entry."""
        tag = tag_response(content, role_type)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "speaker": speaker,
            "role_type": role_type,
            "model": model,
            "content": content,
            "tag": tag,
            "word_count": len(content.split()),
        }
        self.transcript.append(entry)
        tag_label = f"[{tag.upper()}]"
        log.info("%s %s: %s", tag_label, speaker, content[:120] + ("..." if len(content) > 120 else ""))

    def _build_messages_for(self, system_prompt: str, perspective: str = "", perspective_name: str = "") -> list[dict]:
        """Build the messages array for an API call, including shared history.

        perspective: 'detective' or 'suspect' — whose point of view we're building for.
        perspective_name: the suspect's name (only used when perspective='suspect').
        Own messages become 'assistant' role; everything else becomes 'user' role.
        """
        messages = [{"role": "system", "content": system_prompt}]
        for h in self.history:
            is_own_message = False
            if perspective == "detective" and h["role"] == "detective":
                is_own_message = True
            elif perspective == "suspect" and h["role"] == "suspect" and h["name"] == perspective_name:
                is_own_message = True

            if is_own_message:
                messages.append({"role": "assistant", "content": h["content"]})
            else:
                if h["role"] == "narrator":
                    messages.append({"role": "user", "content": f"[Narrator]: {h['content']}"})
                elif h["role"] == "detective":
                    messages.append({"role": "user", "content": f"[Detective]: {h['content']}"})
                elif h["role"] == "suspect":
                    messages.append({"role": "user", "content": f"[{h['name']}]: {h['content']}"})
        return messages

    def _call_detective(self) -> str:
        messages = self._build_messages_for(self.detective_system, perspective="detective")
        return call_openrouter(self.detective_model, messages, self.api_key)

    def _call_suspect(self, suspect_name: str, suspect_index: int) -> str:
        system = self.suspect_systems[suspect_name]
        messages = self._build_messages_for(system, perspective="suspect", perspective_name=suspect_name)
        model = self.suspect_models[suspect_index]
        return call_openrouter(model, messages, self.api_key)

    def _find_suspect_by_name(self, text: str) -> tuple[dict, int] | None:
        """Try to determine which suspect the detective is addressing."""
        text_lower = text.lower()
        for i, s in enumerate(self.config["suspects"]):
            # Check full name
            if s["name"].lower() in text_lower:
                return s, i
            # Check last name
            last = s["name"].split()[-1].lower()
            if last in text_lower:
                return s, i
            # Check first name
            first = s["name"].split()[0].lower()
            if first in text_lower:
                return s, i
        return None

    # -- Phases --

    def phase_opening(self):
        """Phase 1: Narrator sets the scene."""
        log.info("=" * 60)
        log.info("PHASE 1: OPENING")
        log.info("=" * 60)

        loc = self.config["location"]
        victim = self.config["victim"]
        suspects = self.config["suspects"]
        evidence = self.config["evidence"]

        suspect_intros = "\n".join(
            f"  • {s['name']} — {s['role']}: {s['background']}"
            for s in suspects
        )
        clues = "\n".join(f"  • {c}" for c in evidence["opening_clues"])

        opening = f"""Welcome to The Lineup.

LOCATION: {loc['name']}
{loc['description']}

THE CRIME: {victim['name']} — {victim['description']}
Cause of death: {victim['cause_of_death']}

THE SUSPECTS:
{suspect_intros}

OPENING CLUES:
{clues}

Detective, you may begin your investigation. Address any suspect by name to question them."""

        self._add_to_history("narrator", "Narrator", opening)
        self._record("Narrator", "narrator", opening)

    def phase_investigation(self):
        """Phase 2: Detective questions suspects, with optional clue requests."""
        log.info("=" * 60)
        log.info("PHASE 2: INVESTIGATION")
        log.info("=" * 60)

        CLUE_REQUEST_TRIGGER = "I REQUEST A CLUE"
        max_rounds = MAX_CONVERSATIONS_PER_SUSPECT * len(self.config["suspects"])  # 36

        while self.total_conversations < max_rounds:
            self.round_number += 1
            log.info("--- Round %d (total conversations: %d, clues requested: %d) ---",
                     self.round_number, self.total_conversations, self.clues_requested)

            # Detective's turn
            detective_msg = self._call_detective()
            self._add_to_history("detective", "Detective", detective_msg)
            self._record("Detective", "detective", detective_msg, self.detective_model)

            # Check for clue request
            if CLUE_REQUEST_TRIGGER.lower() in detective_msg.lower():
                if self.clues_requested >= 2:
                    nudge = "No additional clues are available. You have already received both available clues. You must continue your investigation with the evidence at hand, or make your accusation."
                    self._add_to_history("narrator", "Narrator", nudge)
                    self._record("Narrator", "narrator", nudge)
                    continue
                self.clues_requested += 1
                clue_key = "round_2_clue" if self.clues_requested == 1 else "round_4_clue"
                clue_text = self.config["evidence"][clue_key]
                penalty_pct = self.clues_requested * 25
                label = f"Evidence Clue #{self.clues_requested}"
                msg = f"*** {label} (score penalty: -{penalty_pct}% of final detective score) ***\n{clue_text}"
                self._add_to_history("narrator", "Narrator", msg)
                self._record("Narrator", "narrator", msg)
                log.info("Clue #%d delivered (total penalty: -%d%%)", self.clues_requested, penalty_pct)
                continue

            # Check for accusation
            if ACCUSATION_TRIGGER.lower() in detective_msg.lower():
                suspects_questioned = sum(1 for c in self.conversation_counts.values() if c > 0)
                if suspects_questioned < 3 or self.total_conversations < 8:
                    log.info("Accusation rejected — %d suspects questioned, %d total conversations (need 3+ suspects, 8+ conversations)", suspects_questioned, self.total_conversations)
                    nudge = f"You must conduct a more thorough investigation before making an accusation. You have questioned {suspects_questioned} suspects with {self.total_conversations} total conversations. Continue questioning — look for contradictions, revisit suspects, and build a strong case."
                    self._add_to_history("narrator", "Narrator", nudge)
                    self._record("Narrator", "narrator", nudge)
                    continue
                log.info("*** ACCUSATION DETECTED ***")
                self.accusation_data = self._parse_accusation(detective_msg)
                return

            # Determine which suspect is being addressed
            target = self._find_suspect_by_name(detective_msg)
            if target is None:
                # Ask detective to clarify by injecting a narrator nudge
                nudge = "Detective, please address a specific suspect by name. Available suspects: " + \
                    ", ".join(s["name"] for s in self.config["suspects"])
                self._add_to_history("narrator", "Narrator", nudge)
                self._record("Narrator", "narrator", nudge)
                continue

            suspect, suspect_idx = target

            # Check conversation cap
            if self.conversation_counts[suspect["name"]] >= MAX_CONVERSATIONS_PER_SUSPECT:
                cap_msg = f"You have already used all {MAX_CONVERSATIONS_PER_SUSPECT} conversations with {suspect['name']}. Please question a different suspect or make your accusation."
                self._add_to_history("narrator", "Narrator", cap_msg)
                self._record("Narrator", "narrator", cap_msg)
                continue

            # Suspect responds
            suspect_response = self._call_suspect(suspect["name"], suspect_idx)
            self._add_to_history("suspect", suspect["name"], suspect_response)
            self._record(suspect["name"], "suspect", suspect_response, self.suspect_models[suspect_idx])

            self.conversation_counts[suspect["name"]] += 1
            self.total_conversations += 1
            self.suspects_questioned.add(suspect["name"])

        # If we exhaust all rounds, force accusation
        log.info("All conversation slots exhausted — forcing accusation phase")
        force_msg = "You have used all available questioning rounds. You must now make your accusation. State 'I MAKE MY ACCUSATION' followed by your accusation naming the KILLER, WEAPON, and MOTIVE."
        self._add_to_history("narrator", "Narrator", force_msg)
        self._record("Narrator", "narrator", force_msg)

        detective_msg = self._call_detective()
        self._add_to_history("detective", "Detective", detective_msg)
        self._record("Detective", "detective", detective_msg, self.detective_model)
        self.accusation_data = self._parse_accusation(detective_msg)

    def _evidence_drop(self, drop_id: str, clue: str):
        """Inject an evidence drop into the shared history."""
        self.evidence_drops_delivered.add(drop_id)
        label = "Evidence Drop #1" if drop_id == "round_2" else "Evidence Drop #2"
        msg = f"*** {label} ***\n{clue}"
        self._add_to_history("narrator", "Narrator", msg)
        self._record("Narrator", "narrator", msg)
        log.info("Evidence drop delivered: %s", label)

    def _parse_accusation(self, text: str) -> dict:
        """Extract killer, weapon, motive from accusation text."""
        # We'll store the raw text and also try to extract structured data
        accusation = {
            "raw_text": text,
            "accused_suspect": None,
            "accused_weapon": None,
            "accused_motive": None,
        }

        text_lower = text.lower()

        # Try to find which suspect is accused
        for s in self.config["suspects"]:
            if s["name"].lower() in text_lower:
                accusation["accused_suspect"] = s["name"]
                break
            last = s["name"].split()[-1].lower()
            if last in text_lower:
                accusation["accused_suspect"] = s["name"]
                break

        # Store the weapon/motive as extracted sections or just the raw text
        # The scoring engine will use fuzzy matching
        accusation["accused_weapon"] = text  # Will be scored against config
        accusation["accused_motive"] = text

        return accusation

    def phase_accusation(self):
        """Phase 3: Detective delivers accusation monologue."""
        log.info("=" * 60)
        log.info("PHASE 3: ACCUSATION")
        log.info("=" * 60)

        if self.accusation_data:
            accused = self.accusation_data.get("accused_suspect", "Unknown")
            log.info("Detective accuses: %s", accused)
        else:
            log.warning("No accusation data — detective did not trigger accusation properly")

    def phase_reactions(self):
        """Phase 4: Each suspect reacts to the accusation."""
        log.info("=" * 60)
        log.info("PHASE 4: REACTIONS")
        log.info("=" * 60)

        accused_name = self.accusation_data.get("accused_suspect", "") if self.accusation_data else ""

        reaction_prompt = f"The detective has made their accusation, accusing {accused_name}. React to this accusation in character. If you are the one accused, respond to the accusation. Keep it to 1-3 sentences."
        self._add_to_history("narrator", "Narrator", reaction_prompt)
        self._record("Narrator", "narrator", reaction_prompt)

        for i, suspect in enumerate(self.config["suspects"]):
            response = self._call_suspect(suspect["name"], i)
            self._add_to_history("suspect", suspect["name"], response)
            self._record(suspect["name"], "suspect", response, self.suspect_models[i])

    def phase_reveal(self):
        """Phase 5: Narrator reveals truth and scores."""
        log.info("=" * 60)
        log.info("PHASE 5: REVEAL & SCORING")
        log.info("=" * 60)

        crime = self.config["crime"]
        killer = self.config["suspects"][crime["killer_index"]]
        scores = self.score_game()

        reveal = f"""THE TRUTH REVEALED:

The killer was {killer['name']} ({killer['role']}).

WEAPON: {crime['weapon']}
MOTIVE: {crime['motive']}

WHAT REALLY HAPPENED:
{crime['how_it_happened']}

TIMELINE:
{crime['timeline']}

SCORING:
{json.dumps(scores, indent=2)}"""

        self._add_to_history("narrator", "Narrator", reveal)
        self._record("Narrator", "narrator", reveal)

        return scores

    # -- Scoring --

    def score_game(self) -> dict:
        """Calculate scores per SPEC.md rules."""
        crime = self.config["crime"]
        killer = self.config["suspects"][crime["killer_index"]]
        accused = self.accusation_data.get("accused_suspect", "") if self.accusation_data else ""
        accusation_text = self.accusation_data.get("raw_text", "") if self.accusation_data else ""
        accusation_lower = accusation_text.lower()

        correct_killer = accused.lower() == killer["name"].lower() if accused else False
        correct_weapon = crime["weapon"].lower().split()[0] in accusation_lower  # fuzzy: check key word
        correct_motive = any(
            word in accusation_lower
            for word in crime["motive"].lower().split()
            if len(word) > 4  # skip short words
        )

        # Speed bonus: (6 * num_suspects) - total_conversations
        max_conversations = MAX_CONVERSATIONS_PER_SUSPECT * len(self.config["suspects"])
        speed_bonus = max_conversations - self.total_conversations

        detective_score_raw = 0
        if correct_killer:
            detective_score_raw += 10
        if correct_weapon:
            detective_score_raw += 5
        if correct_motive:
            detective_score_raw += 5
        detective_score_raw += speed_bonus

        # Apply clue request penalty: each clue costs 25% of the score
        clue_penalty_pct = self.clues_requested * 25
        if clue_penalty_pct > 0:
            detective_score = int(detective_score_raw * (100 - clue_penalty_pct) / 100)
            log.info("Clue penalty applied: %d clues requested (-%d%%), raw=%d, final=%d",
                     self.clues_requested, clue_penalty_pct, detective_score_raw, detective_score)
        else:
            detective_score = detective_score_raw

        # Guilty suspect score
        guilty_score = 0
        if not correct_killer:
            guilty_score += 20
            # Check if detective accused a specific innocent (framing bonus)
            for s in self.config["suspects"]:
                if s["name"].lower() == accused.lower() and not s["guilty"]:
                    guilty_score += 3
                    break

        # Innocent suspect scores
        # Collect evidence keywords for "useful info" scoring
        evidence_keywords = set()
        weapon_words = [w.lower() for w in crime["weapon"].split() if len(w) > 3]
        motive_words = [w.lower() for w in crime["motive"].split() if len(w) > 4]
        evidence_keywords.update(weapon_words)
        evidence_keywords.update(motive_words)
        # Add timeline-related words
        for w in crime.get("timeline", "").split():
            if len(w) > 4 and not w.replace(":", "").replace("-", "").isdigit():
                evidence_keywords.add(w.lower().strip(".,;:"))

        # Accusatory phrases that indicate a suspect is identifying the killer
        accusatory_patterns = [
            r"i\s+suspect", r"i\s+think\s+it\s+was", r"seems?\s+suspicious",
            r"looks?\s+guilty", r"could\s+have\s+killed", r"might\s+have\s+done\s+it",
            r"wouldn.t\s+trust", r"is\s+the\s+killer", r"is\s+hiding\s+something",
            r"must\s+have\s+been", r"blame", r"accuse",
        ]

        innocent_scores = {}
        for s in self.config["suspects"]:
            if s["guilty"]:
                continue
            score = 0
            # Not falsely accused (5 pts)
            if accused.lower() != s["name"].lower():
                score += 5

            # Gather this suspect's responses from transcript
            suspect_responses = " ".join(
                e["content"] for e in self.transcript
                if e["speaker"] == s["name"] and e["role_type"] == "suspect"
            ).lower()

            if suspect_responses:
                # Correctly ID the killer (5 pts): mentioned killer's name in accusatory context
                if killer["name"].lower() in suspect_responses or killer["name"].split()[-1].lower() in suspect_responses:
                    for pattern in accusatory_patterns:
                        if re.search(pattern, suspect_responses):
                            score += 5
                            break

                # Useful info (3 pts): mentioned actual evidence keywords
                keyword_hits = sum(1 for kw in evidence_keywords if kw in suspect_responses)
                if keyword_hits >= 2:
                    score += 3

            innocent_scores[s["name"]] = score

        scores = {
            "detective": {
                "model": self.detective_model,
                "correct_killer": correct_killer,
                "correct_weapon": correct_weapon,
                "correct_motive": correct_motive,
                "speed_bonus": speed_bonus,
                "clues_requested": self.clues_requested,
                "clue_penalty_pct": clue_penalty_pct,
                "score_before_penalty": detective_score_raw,
                "total": detective_score,
            },
            "guilty_suspect": {
                "name": killer["name"],
                "model": self.suspect_models[crime["killer_index"]],
                "evaded_detection": not correct_killer,
                "total": guilty_score,
            },
            "innocent_suspects": {
                name: {
                    "model": self.suspect_models[self.config["suspects"].index(
                        next(s for s in self.config["suspects"] if s["name"] == name)
                    )],
                    "total": sc,
                }
                for name, sc in innocent_scores.items()
            },
            "total_conversations": self.total_conversations,
            "conversation_breakdown": dict(self.conversation_counts),
        }

        log.info("Detective score: %d (killer=%s, weapon=%s, motive=%s, speed=+%d, clues=%d, penalty=-%d%%)",
                 detective_score, correct_killer, correct_weapon, correct_motive, speed_bonus,
                 self.clues_requested, clue_penalty_pct)
        log.info("Guilty suspect score: %d (evaded=%s)", guilty_score, not correct_killer)

        return scores

    # -- Export --

    def export_transcript(self) -> tuple[Path, Path]:
        """Export transcript as JSON and Markdown."""
        transcripts_dir = self.config_path.parent.parent.parent / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)

        set_id = self.config["set_id"]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base = f"{set_id}_{ts}"

        # JSON export
        json_path = transcripts_dir / f"{base}.json"
        export_data = {
            "game": {
                "set_id": set_id,
                "title": self.config["title"],
                "season": self.config["season"],
                "episode": self.config["episode"],
                "started": self.game_start_time,
                "finished": datetime.now(timezone.utc).isoformat(),
            },
            "model_assignments": self.config["model_assignments"],
            "transcript": self.transcript,
            "scores": self.score_game(),
        }
        with open(json_path, "w") as f:
            json.dump(export_data, f, indent=2)
        log.info("JSON transcript: %s", json_path)

        # Markdown export
        md_path = transcripts_dir / f"{base}.md"
        lines = [
            f"# {self.config['title']}",
            f"*{self.config['set_id']} — {self.game_start_time}*\n",
        ]
        for entry in self.transcript:
            tag = entry["tag"].upper()
            speaker = entry["speaker"]
            content = entry["content"]
            lines.append(f"**[{tag}] {speaker}:**\n{content}\n")

        with open(md_path, "w") as f:
            f.write("\n".join(lines))
        log.info("Markdown transcript: %s", md_path)

        return json_path, md_path

    # -- Leaderboard --

    def update_leaderboard(self, scores: dict):
        """Update the season leaderboard."""
        season_dir = self.config_path.parent
        lb_path = season_dir / "leaderboard.json"

        if lb_path.exists():
            with open(lb_path) as f:
                leaderboard = json.load(f)
        else:
            leaderboard = {"season": self.config["season"], "models": {}, "games_played": []}

        set_id = self.config["set_id"]
        if set_id in leaderboard.get("games_played", []):
            log.warning("Game %s already in leaderboard — skipping update", set_id)
            return

        leaderboard["games_played"].append(set_id)

        # Detective
        det_model = scores["detective"]["model"]
        if det_model not in leaderboard["models"]:
            leaderboard["models"][det_model] = {"total": 0, "detective_score": 0, "suspect_score": 0, "games": 0}
        leaderboard["models"][det_model]["total"] += scores["detective"]["total"]
        leaderboard["models"][det_model]["detective_score"] += scores["detective"]["total"]
        leaderboard["models"][det_model]["games"] += 1

        # Guilty suspect
        g_model = scores["guilty_suspect"]["model"]
        if g_model not in leaderboard["models"]:
            leaderboard["models"][g_model] = {"total": 0, "detective_score": 0, "suspect_score": 0, "games": 0}
        leaderboard["models"][g_model]["total"] += scores["guilty_suspect"]["total"]
        leaderboard["models"][g_model]["suspect_score"] += scores["guilty_suspect"]["total"]
        leaderboard["models"][g_model]["games"] += 1

        # Innocent suspects
        for name, data in scores["innocent_suspects"].items():
            model = data["model"]
            if model not in leaderboard["models"]:
                leaderboard["models"][model] = {"total": 0, "detective_score": 0, "suspect_score": 0, "games": 0}
            leaderboard["models"][model]["total"] += data["total"]
            leaderboard["models"][model]["suspect_score"] += data["total"]
            leaderboard["models"][model]["games"] += 1

        with open(lb_path, "w") as f:
            json.dump(leaderboard, f, indent=2)
        log.info("Leaderboard updated: %s", lb_path)

    # -- Telegram --

    def send_telegram_results(self, scores: dict):
        """Send final results summary to Telegram."""
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            log.warning("TELEGRAM_BOT_TOKEN not set — skipping Telegram notification")
            return

        chat_id = "8473447125"
        crime = self.config["crime"]
        killer = self.config["suspects"][crime["killer_index"]]
        det = scores["detective"]

        text = f"""🎬 THE LINEUP — {self.config['title']}

Detective ({det['model']}):
  Killer: {'✅' if det['correct_killer'] else '❌'} | Weapon: {'✅' if det['correct_weapon'] else '❌'} | Motive: {'✅' if det['correct_motive'] else '❌'}
  Speed bonus: +{det['speed_bonus']} | Clues: {det['clues_requested']} (-{det['clue_penalty_pct']}%) | Total: {det['total']}

Guilty suspect: {killer['name']} ({scores['guilty_suspect']['model']})
  Evaded: {'✅' if scores['guilty_suspect']['evaded_detection'] else '❌'} | Score: {scores['guilty_suspect']['total']}

Total conversations: {scores['total_conversations']}
Game: {self.config['set_id']}"""

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
            if resp.ok:
                log.info("Telegram notification sent")
            else:
                log.warning("Telegram send failed: %s", resp.text)
        except requests.exceptions.RequestException as e:
            log.warning("Telegram error: %s", e)

    # -- Main game loop --

    def run(self):
        """Run the full game."""
        self.game_start_time = datetime.now(timezone.utc).isoformat()
        log.info("=" * 60)
        log.info("THE LINEUP — %s", self.config["title"])
        log.info("=" * 60)

        self.phase_opening()
        self.phase_investigation()
        self.phase_accusation()
        self.phase_reactions()
        scores = self.phase_reveal()

        json_path, md_path = self.export_transcript()
        self.update_leaderboard(scores)
        self.send_telegram_results(scores)

        log.info("=" * 60)
        log.info("GAME COMPLETE")
        log.info("=" * 60)

        return scores


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python engine.py <game_config.json>")
        print("Example: python engine.py seasons/season_01/set_01.json")
        sys.exit(1)

    config_path = sys.argv[1]
    if not Path(config_path).exists():
        log.error("Config file not found: %s", config_path)
        sys.exit(1)

    engine = GameEngine(config_path)
    scores = engine.run()

    print("\n" + "=" * 60)
    print("FINAL SCORES")
    print("=" * 60)
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
