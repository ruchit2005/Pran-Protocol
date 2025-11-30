import asyncio
import os
import sys
from dotenv import load_dotenv

# Add root to path
sys.path.append(os.getcwd())

from src.utils.emergency import HybridEmergencyDetector
from src.utils.youtube_client import search_videos

async def test_emergency_triage():
    print("\n--- Testing Emergency Triage ---")
    detector = HybridEmergencyDetector()
    
    cases = [
        ("I want to kill myself", True),
        ("I have severe chest pain", True),
        ("I have a mild headache", False),
        ("Call an ambulance", True),
        ("Yoga for back pain", False)
    ]
    
    for text, expected in cases:
        is_emergency, reason = detector.check_emergency(text)
        status = "✅" if is_emergency == expected else "❌"
        print(f"{status} Input: '{text}' -> Emergency: {is_emergency} ({reason})")

async def test_youtube_links():
    print("\n--- Testing YouTube Links ---")
    try:
        videos = await search_videos("yoga for stress", max_results=2)
        if videos:
            print(f"✅ Found {len(videos)} videos:")
            for v in videos:
                print(f"   - {v['title']} ({v['url']})")
        else:
            print("⚠️ No videos found (check API key or quota)")
    except Exception as e:
        print(f"❌ Error fetching videos: {e}")

async def main():
    load_dotenv()
    await test_emergency_triage()
    await test_youtube_links()
    # Note: Testing full RAG workflow requires initialized ChromaDB and LLM, 
    # which might be heavy for this script. We rely on the unit tests for components.

if __name__ == "__main__":
    asyncio.run(main())
