import os
import requests
import time
from typing import Dict, Any, List
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class HealthAdvisoryChain:
    """Fetches real-time health news and alerts using NewsAPI client with strict medical filtering."""
    
    # CLASS-LEVEL shared cache and rate limiter (shared across all instances)
    _shared_cache = None
    _shared_cache_timestamp = None
    _shared_last_request_time = 0
    _cache_ttl_seconds = 30 * 60  # 30 minutes
    _min_request_interval = 6.0  # 6 seconds (GDELT requires 5, adding buffer)
    
    def __init__(self, llm, fetch_on_init=False):
        self.llm = llm
        # GDELT API is free and doesn't require API key
        self.gdelt_base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
        
        # Fetch data immediately on initialization if requested
        if fetch_on_init:
            print("      🔄 Fetching initial health news data...")
            try:
                self.fetch_headlines()
            except Exception as e:
                print(f"      ⚠️ Initial fetch failed: {e}. Will use fallback data.")
            
        # Fallback data
        self.fallback_data = [
            {
                "title": "General Health Alert: Seasonal Flu",
                "source": {"name": "Health Ministry"},
                "description": "Advising public to take precautions against seasonal influenza.",
                "url": "#",
                "publishedAt": "2024-12-01T00:00:00Z"
            },
            {
                "title": "Dengue Awareness Drive",
                "source": {"name": "Municipal Corporation"},
                "description": "Enhanced fogging operations start today in metro areas.",
                "url": "#",
                "publishedAt": "2024-12-05T00:00:00Z"
            }
        ]
        
        # Strict medical keywords that MUST appear in articles
        self.medical_keywords = [
            'disease', 'virus', 'infection', 'outbreak', 'epidemic', 'pandemic',
            'vaccine', 'vaccination', 'hospital', 'patient', 'doctor', 'medical',
            'health ministry', 'who', 'dengue', 'malaria', 'flu', 'influenza',
            'covid', 'coronavirus', 'cases', 'death toll', 'infected', 'symptoms',
            'treatment', 'cure', 'medicine', 'drug', 'clinical', 'diagnosis',
            'surgery', 'healthcare', 'public health', 'mortality', 'morbidity'
        ]
        
        # Keywords that indicate NON-medical content (auto-reject)
        self.exclude_keywords = [
            'stock', 'market', 'shares', 'revenue', 'profit', 'earnings',
            'ipo', 'investment', 'economy', 'gdp', 'fiscal', 'budget',
            'cricket', 'football', 'sports', 'match', 'tournament', 'player',
            'election', 'politics', 'minister', 'parliament', 'government policy',
            'tax', 'gst', 'finance', 'banking', 'loan', 'insurance',
            'real estate', 'property', 'housing', 'construction'
        ]
        
        self.summarize_prompt = ChatPromptTemplate.from_template(
            """You are a public health alert system.
            
            User Query: {user_input}
            
            Top Health Headlines (India):
            {headlines}
            
            Based on the above headlines, provide a concise summary or answer the user's specific question.
            If the headlines are relevant to the query (e.g., "dengue news"), prioritize those.
            If the query is general ("any alerts?"), summarize the top 3 most critical ones.
            
            Format clearly with bold text for headlines and emojis like 🚨, 🏥, 🦠.
            """
        )
        self.chain = self.summarize_prompt | llm | StrOutputParser()

    def _is_medical_article(self, article: Dict[str, Any]) -> bool:
        """Strict filter to determine if article is truly medical/health related."""
        title = (article.get('title') or '').lower()
        description = (article.get('description') or '').lower()
        content = (article.get('content') or '').lower()
        
        full_text = f"{title} {description} {content}"
        
        # Reject if contains exclude keywords
        if any(keyword in full_text for keyword in self.exclude_keywords):
            return False
        
        # GDELT articles are already filtered by query, so require only 1 keyword match
        medical_matches = sum(1 for keyword in self.medical_keywords if keyword in full_text)
        
        return medical_matches >= 1

    def fetch_headlines(self) -> List[Dict[str, Any]]:
        """Fetch health news from GDELT Project API for Uttarakhand region with caching."""
        
        # Check CLASS-LEVEL cache first (shared across all instances)
        if HealthAdvisoryChain._shared_cache is not None and HealthAdvisoryChain._shared_cache_timestamp is not None:
            time_elapsed = (datetime.utcnow() - HealthAdvisoryChain._shared_cache_timestamp).total_seconds()
            if time_elapsed < HealthAdvisoryChain._cache_ttl_seconds:
                print(f"      ✓ Using cached health news (age: {int(time_elapsed/60)} minutes)")
                return HealthAdvisoryChain._shared_cache
        
        try:
            print(f"      → GDELT API: Fetching health news for Uttarakhand/Dehradun...")
            
            # GDELT query for Uttarakhand health news - simplified
            params = {
                'query': 'Uttarakhand (vaccine OR vaccination OR disease OR hospital OR ill OR scheme OR pollution OR patient OR health OR medical OR dengue OR malaria OR outbreak)',
                'mode': 'artlist',
                'format': 'json',
                'maxrecords': 30,  # Get more to filter from
                'sort': 'datedesc'
            }
            
            # Simple rate limiting (only called once per hour from background task)
            time_since_last = time.time() - HealthAdvisoryChain._shared_last_request_time
            if time_since_last < HealthAdvisoryChain._min_request_interval:
                wait_time = HealthAdvisoryChain._min_request_interval - time_since_last
                print(f"      ⏱️ Waiting {wait_time:.1f}s for rate limit...")
                time.sleep(wait_time)
            
            HealthAdvisoryChain._shared_last_request_time = time.time()
            
            # Add browser-like headers to avoid rate limiting
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.gdeltproject.org/',
                'Origin': 'https://www.gdeltproject.org',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site'
            }
            
            response = requests.get(self.gdelt_base_url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 429:
                print("      ⚠️ Rate limit hit. Will retry on next refresh cycle.")
                return self.fallback_data if not HealthAdvisoryChain._shared_cache else HealthAdvisoryChain._shared_cache
            
            response.raise_for_status()
            
            # Check if response has content
            if not response.text or response.text.strip() == '':
                print("      ⚠️ GDELT returned empty response. Using fallback data.")
                return self.fallback_data
            
            try:
                data = response.json()
            except Exception as json_error:
                print(f"      ⚠️ GDELT response not JSON. Status: {response.status_code}, Content: {response.text[:200]}")
                return self.fallback_data
            
            articles = data.get('articles', [])
            
            print(f"      → Found {len(articles)} Uttarakhand health articles")
            
            filtered_articles = []
            seen_titles = set()  # Track unique titles
            
            # Exclude non-health topics
            exclude_title_keywords = [
                'upsc', 'kvs', 'recruitment', 'job', 'admission', 'exam',
                'election', 'politics', 'mla', 'mp',
                'sports', 'cricket', 'football', 'tournament'
            ]
            
            # Must have health-related keywords (comprehensive list including schemes, pollution, environment)
            health_keywords = [
                # Direct health
                'vaccin', 'immuniz', 'dose',
                'disease', 'outbreak', 'epidemic', 'pandemic', 'spread',
                'hospital', 'patient', 'doctor', 'medical', 'clinic', 'nursing',
                'dengue', 'malaria', 'flu', 'fever', 'viral', 'infection',
                'health', 'healthcare', 'health drive', 'health camp', 'checkup',
                'covid', 'corona', 'virus', 'bacteria',
                'treatment', 'medicine', 'drug', 'pharma', 'pharmacy',
                'surgery', 'operation', 'emergency',
                'ambulance', 'icu', 'bed', 'ward',
                'death', 'mortality', 'fatality', 'died',
                'injury', 'accident', 'trauma',
                'mental health', 'depression', 'stress',
                'nutrition', 'malnutrition', 'anemia',
                'pregnancy', 'maternal', 'child health',
                'sanitation', 'hygiene', 'clean',
                'cough syrup', 'medication', 'prescription',
                # Government health schemes
                'health scheme', 'ayushman', 'health insurance', 'medical scheme',
                'health program', 'health initiative', 'health benefit',
                # Environmental health
                'pollution', 'aqi', 'air quality', 'air pollution',
                'water quality', 'drinking water', 'contamination',
                'waste management', 'garbage', 'sewage',
                'smog', 'toxic', 'hazard', 'poisoning',
                # Weather affecting health
                'cold wave', 'heat wave', 'temperature', 'fog', 'snowfall',
                'weather alert', 'extreme weather', 'weather warning'
            ]
            
            for article in articles:
                title = article.get('title', 'No Title')
                title_lower = title.lower()
                
                # Skip non-health content
                if any(keyword in title_lower for keyword in exclude_title_keywords):
                    continue
                
                # Must contain at least one health keyword
                if not any(keyword in title_lower for keyword in health_keywords):
                    continue
                
                # Convert GDELT format to standard format
                formatted_article = {
                    'title': title,
                    'source': {'name': article.get('domain', 'Unknown')},
                    'description': title[:150],  # Use title as description since seendate is just a date
                    'url': article.get('url', '#'),
                    'publishedAt': article.get('seendate', '')
                }
                
                # Exclude non-medical domains
                domain = article.get('domain', '').lower()
                exclude_domains = ['cricbuzz', 'espn', 'business-standard', 'moneycontrol', 'economictimes', 'jagran.com']
                
                if not any(excluded in domain for excluded in exclude_domains):
                    # Check for duplicate URLs AND titles
                    if (not any(a.get('url') == formatted_article.get('url') for a in filtered_articles) and
                        title not in seen_titles):
                        filtered_articles.append(formatted_article)
                        seen_titles.add(title)
                        if len(filtered_articles) >= 10:
                            break
            
            if filtered_articles:
                print(f"      ✓ Found {len(filtered_articles)} relevant health articles from GDELT")
                # Update CLASS-LEVEL cache (shared across all instances)
                HealthAdvisoryChain._shared_cache = filtered_articles[:10]
                HealthAdvisoryChain._shared_cache_timestamp = datetime.utcnow()
                return HealthAdvisoryChain._shared_cache

            print("      ⚠️ No relevant medical articles found. Using fallback data.")
            return self.fallback_data
                
        except Exception as e:
            print(f"      ❌ NewsAPI Error: {e}")
            import traceback
            traceback.print_exc()
            return self.fallback_data

    def run(self, user_input: str) -> str:
        """Execute the chain."""
        articles = self.fetch_headlines()
        
        # Format for LLM
        headlines_text = ""
        for a in articles:
            source = a.get('source', {}).get('name', 'Unknown')
            title = a.get('title', 'No Title')
            desc = a.get('description', '')
            headlines_text += f"- {title} (Source: {source})\n  Context: {desc}\n\n"
        
        return self.chain.invoke({
            "user_input": user_input,
            "headlines": headlines_text
        })
