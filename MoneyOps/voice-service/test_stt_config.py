"""
Quick test to verify AssemblyAI STT is properly configured
"""
import sys
import os

# Add the service directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔍 Testing STT Configuration...")
print("=" * 50)

# Test 1: Load config
try:
    from app.config import settings
    print("✅ Config loaded successfully")
    print(f"   - AssemblyAI Key: {settings.ASSEMBLYAI_API_KEY[:15]}...")
    print(f"   - Groq Model: {settings.GROQ_MODEL}")
except Exception as e:
    print(f"❌ Config failed: {e}")
    sys.exit(1)

# Test 2: Import AssemblyAI plugin
try:
    from livekit.plugins import assemblyai
    print("✅ AssemblyAI plugin imported")
except Exception as e:
    print(f"❌ AssemblyAI import failed: {e}")
    sys.exit(1)

# Test 3: Create STT instance
try:
    stt = assemblyai.STT(
        api_key=settings.ASSEMBLYAI_API_KEY,
    )
    print("✅ AssemblyAI STT instance created")
except Exception as e:
    print(f"❌ STT creation failed: {e}")
    sys.exit(1)

# Test 4: Import entrypoint
try:
    from app.agent.entrypoint import server
    print("✅ Entrypoint imports successfully")
except Exception as e:
    print(f"❌ Entrypoint import failed: {e}")
    sys.exit(1)

print("=" * 50)
print("🎉 All tests passed! STT is configured correctly.")
print("\nNext step: Run the agent with:")
print("   python -m app.agent.entrypoint dev")
