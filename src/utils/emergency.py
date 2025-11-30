import re
from typing import Tuple, List

class HybridEmergencyDetector:
    """
    Hybrid emergency detection system combining keyword matching and regex patterns.
    Acts as a fast first line of defense before LLM processing.
    """
    
    def __init__(self):
        # Critical keywords that almost always indicate emergency
        self.critical_keywords = {
            "suicide", "kill myself", "want to die", "end my life",
            "heart attack", "chest pain", "stroke", "paralysis",
            "breathing difficulty", "cannot breathe", "choking",
            "severe bleeding", "unconscious", "fainted",
            "poison", "overdose", "snake bite", "snakebite",
            "severe burn", "head injury", "broken bone", "fracture",
            "seizure", "convulsion", "anaphylaxis", "allergic reaction"
        }
        
        # Regex patterns for more complex matching
        self.patterns = [
            r"severe\s+pain",
            r"blood\s+vomit",
            r"coughing\s+blood",
            r"sudden\s+vision\s+loss",
            r"slurred\s+speech",
            r"call\s+(?:an\s+|the\s+)?(ambulance|911|108|102)",
            r"emergency\s+help",
            r"collapsed"
        ]
        
    def check_emergency(self, text: str) -> Tuple[bool, str]:
        """
        Check if the input text indicates a medical emergency.
        
        Args:
            text: User input string
            
        Returns:
            Tuple[bool, str]: (is_emergency, reason)
        """
        text_lower = text.lower()
        
        # 1. Direct keyword check
        for keyword in self.critical_keywords:
            if keyword in text_lower:
                return True, f"Detected critical keyword: '{keyword}'"
                
        # 2. Pattern matching
        for pattern in self.patterns:
            if re.search(pattern, text_lower):
                return True, f"Detected emergency pattern matching '{pattern}'"
                
        return False, ""
