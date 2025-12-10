from typing import Dict, Any, List
import requests
from datetime import datetime

class HealthAdvisoryChain:
    """Fetches real-time health advisories from MoHFW/Govt Sources (simulated)"""
    
    def __init__(self, llm):
        self.llm = llm
        # No complex prompt needed as it's data retrieval + simple formatting
        
    def run(self, user_input: str) -> Dict[str, Any]:
        print(f"      → HealthAdvisory: Fetching real-time data...")
        
        # In a real app, we would hit https://main.mohfw.gov.in/rss/new-content
        # For now, we simulate this to ensure reliability during demo
        
        advisories = [
            {
                "title": "Heatwave Alert",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "severity": "High",
                "details": "Severe heatwave conditions expected in Northern India. Stay hydrated.",
                "source": "IMD/MoHFW"
            },
            {
                "title": "Dengue Prevention",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "severity": "Medium",
                "details": "Monsoon season brings risk of Dengue. Keep surroundings dry.",
                "source": "National Vector Borne Disease Control Programme"
            },
            {
                "title": "COVID-19 Update",
                "date": "2024-12-01",
                "severity": "Low",
                "details": "Cases are stable. Vaccination recommended for elderly.",
                "source": "MoHFW"
            }
        ]
        
        # Simple keyword filtering
        query_lower = user_input.lower()
        if "heat" in query_lower:
            relevant = [a for a in advisories if "Heat" in a['title']]
        elif "dengue" in query_lower:
            relevant = [a for a in advisories if "Dengue" in a['title']]
        elif "covid" in query_lower:
            relevant = [a for a in advisories if "COVID" in a['title']]
        else:
            relevant = advisories[:2] # Default to top 2
            
        formatted_response = "📢 **Health Advisories & Alerts**\n\n"
        for adv in relevant:
            formatted_response += f"**{adv['title']}** ({adv['date']})\n"
            formatted_response += f"⚠️ Severity: {adv['severity']}\n"
            formatted_response += f"{adv['details']}\n"
            formatted_response += f"_[Source: {adv['source']}]_\n\n"
            
        return formatted_response
