import threading
import time
from typing import Dict, Any, Optional

class SituationModel:
    """
    Accumulates state and entities across multiple conversation turns.
    Upgraded to support dialogue_act, goal, and negative constraints.
    """
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.dialogue_act: str = "inform" # e.g. "greeting", "request", "correction"
        self.goal: str = "inform"         # e.g. "inform", "booking"
        self.target_class: Optional[str] = None
        self.entities: Dict[str, Any] = {} # Key: { "value": val, "op": "MUST"|"NOT" }
        self.last_updated = time.time()
        self.history: list = []

    def update(self, tmr: Dict[str, Any], text: Optional[str] = None):
        """Merges a new Text Meaning Representation into the existing state."""
        new_dialogue_act = tmr.get("dialogue_act")
        new_goal = tmr.get("goal") or tmr.get("intent")
        new_class = tmr.get("class")
        new_entities = tmr.get("entities", {})

        # 1. Update Dialogue Act and Goal
        if new_dialogue_act:
            self.dialogue_act = new_dialogue_act
        if new_goal:
            self.goal = new_goal

        # 2. Update Class and Intent Transition
        # If class changes, we clear old class-specific entities
        if new_class and new_class != self.target_class:
            # Clear specific keys that aren't location or accessibility
            keys_to_keep = ["locatedIn", "wheelchairAccessible", "price_range"]
            self.entities = {k: v for k, v in self.entities.items() if k in keys_to_keep}
            self.target_class = new_class
            self.goal = "inform"
        elif not self.target_class:
            self.target_class = new_class

        # 3. Accumulate Entities with Constraint Logic
        for k, v in new_entities.items():
            # If v is a simple value, convert to long form
            if not isinstance(v, dict):
                v = {"value": v, "op": "MUST"}
            
            # If dialogue act is 'correction', overwrite even if key exists
            if self.dialogue_act == "correction" or k not in self.entities:
                self.entities[k] = v
            else:
                # Merge logic: new values overwrite same key
                self.entities[k] = v

        if text:
            self.history.append({"role": "user", "content": text})
        
        self.last_updated = time.time()

    def clear(self):
        self.dialogue_act = "inform"
        self.goal = "inform"
        self.target_class = None
        self.entities = {}
        self.history = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dialogue_act": self.dialogue_act,
            "goal": self.goal,
            "class": self.target_class,
            "entities": self.entities
        }

class SessionManager:
    """Manages SituationModels for all active users."""
    def __init__(self):
        self.sessions: Dict[int, SituationModel] = {}
        self._lock = threading.Lock()

    def get_session(self, chat_id: int) -> SituationModel:
        with self._lock:
            if chat_id not in self.sessions:
                self.sessions[chat_id] = SituationModel(chat_id)
            return self.sessions[chat_id]

    def clear_session(self, chat_id: int):
        with self._lock:
            if chat_id in self.sessions:
                del self.sessions[chat_id]

# Global instance
session_manager = SessionManager()
