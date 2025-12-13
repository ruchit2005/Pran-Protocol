import os
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from newsapi import NewsApiClient

class HealthAdvisoryChain:
    """Fetches real-time health news and alerts using NewsAPI client with strict medical filtering."""
    
    def __init__(self, llm):
        self.llm = llm
        self.api_key = os.getenv("NEWS_API_KEY")
        # Initialize the official client
        try:
            self.newsapi = NewsApiClient(api_key=self.api_key)
        except:
            self.newsapi = None
        
        # Cache configuration (30 minutes TTL)
        self._cache = None
        self._cache_timestamp = None
        self._cache_ttl_seconds = 30 * 60  # 30 minutes
            
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
        
        # Must contain at least 2 medical keywords to be considered relevant
        medical_matches = sum(1 for keyword in self.medical_keywords if keyword in full_text)
        
        return medical_matches >= 2

    def fetch_headlines(self) -> List[Dict[str, Any]]:
        """Fetch raw headlines using NewsApiClient with aggressive medical filtering and caching."""
        
        # Check cache first
        from datetime import datetime, timedelta
        if self._cache is not None and self._cache_timestamp is not None:
            time_elapsed = (datetime.utcnow() - self._cache_timestamp).total_seconds()
            if time_elapsed < self._cache_ttl_seconds:
                print(f"      ✓ Using cached health news (age: {int(time_elapsed/60)} minutes)")
                return self._cache
        
        if not self.newsapi:
            print("⚠️ NewsApiClient not initialized. Using fallback data.")
            return self.fallback_data
            
        try:
            print("      → NewsAPI: Fetching Top Headlines (Category: Health, Country: IN)...")
            
            # Strategy 1: Top Headlines with Health Category
            top_headlines = self.newsapi.get_top_headlines(
                category='health',
                country='in',
                language='en',
                page_size=20  # Get more to filter from
            )
            
            filtered_articles = []
            
            if top_headlines.get('status') == 'ok':
                articles = top_headlines.get('articles', [])
                # Apply strict medical filter
                for article in articles:
                    if article.get('title') == '[Removed]':
                        continue
                    if self._is_medical_article(article):
                        filtered_articles.append(article)
                
                if filtered_articles:
                    print(f"      ✓ Found {len(filtered_articles)} medical articles from top headlines.")
                    # Update cache
                    self._cache = filtered_articles[:5]
                    self._cache_timestamp = datetime.utcnow()
                    return self._cache

            # Strategy 2: Search with specific medical queries
            print("      → NewsAPI: Using targeted medical search...")
            
            # Multiple specific searches for different health topics
            # Prioritize India-specific news, but allow major global health events
            search_queries = [
                # India-specific searches (priority)
                'dengue India OR Mumbai OR Delhi',
                'malaria India OR outbreak India',
                'flu India OR influenza India',
                'hospital India OR healthcare India',
                'vaccine India OR vaccination India',
                'disease India OR epidemic India',
                # Major global health events (if India news is scarce)
                'WHO pandemic OR global outbreak',
                'bird flu H5N1',
                'mpox monkeypox'
            ]
            
            for query in search_queries:
                try:
                    results = self.newsapi.get_everything(
                        q=query,
                        language='en',
                        sort_by='publishedAt',
                        page_size=10,
                        exclude_domains='moneycontrol.com,economictimes.indiatimes.com,livemint.com,business-standard.com,financialexpress.com,cricbuzz.com,espncricinfo.com'
                    )
                    
                    if results.get('status') == 'ok':
                        articles = results.get('articles', [])
                        for article in articles:
                            if article.get('title') == '[Removed]':
                                continue
                            if self._is_medical_article(article):
                                # Avoid duplicates
                                if not any(a.get('url') == article.get('url') for a in filtered_articles):
                                    filtered_articles.append(article)
                                    
                                    if len(filtered_articles) >= 5:
                                        break
                    
                    if len(filtered_articles) >= 5:
                        break
                        
                except Exception as e:
                    print(f"      ⚠️ Search query '{query}' failed: {e}")
                    continue

            if filtered_articles:
                print(f"      ✓ Found {len(filtered_articles)} medical articles from targeted search.")
                # Update cache
                self._cache = filtered_articles[:5]
                self._cache_timestamp = datetime.utcnow()
                return self._cache

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
