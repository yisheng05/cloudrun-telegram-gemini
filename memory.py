import threading
import time
from typing import Dict, Any, Optional

class SituationModel:
    """
    Accumulates state and entities across multiple conversation turns.
    Inspired by the zero-hallucination-auditor architecture.
    """
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.intent: Optional[str] = None
        self.target_class: Optional[str] = None
        self.entities: Dict[str, Any] = {}
        self.last_updated = time.time()
        self.history: list = [] # Store raw text history if needed

    def update(self, tmr: Dict[str, Any], text: Optional[str] = None):
        """Merges a new Text Meaning Representation into the existing state."""
        new_intent = tmr.get("intent")
        new_class = tmr.get("class")
        new_entities = tmr.get("entities", {})

        # 1. Update Class and Intent Transition
        # If class changes (e.g. from NaturePark to Attraction/Museum), 
        # we often want to clear class-specific entities but keep location/accessibility
        if new_class and new_class != self.target_class:
            # Clear sticky specific types that might conflict
            self.entities.pop("activity_type", None)
            self.entities.pop("nature_feature", None)
            self.entities.pop("shopping_type", None)
            self.target_class = new_class
            self.intent = new_intent or "inform"
        elif not self.target_class:
            self.target_class = new_class

        # 2. Update Intent
        if new_intent and new_intent not in ["inform", "query"]:
            self.intent = new_intent
        elif not self.intent:
            self.intent = new_intent

        # 3. Accumulate Entities
        for k, v in new_entities.items():
            if v is not None:
                self.entities[k] = v

        if text:
            self.history.append({"role": "user", "content": text})
        
        self.last_updated = time.time()

    def clear(self):
        self.intent = None
        self.target_class = None
        self.entities = {}
        self.history = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
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
