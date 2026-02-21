from dotenv import load_dotenv
import asyncio
from livekit.plugins import groq
import os

load_dotenv()

async def main():
    try:
        t = groq.TTS()
        print(f"TTS initialized: {t}")
        # Try synthesize (dry run)
        s = t.synthesize("Hello")
        async for chunk in s:
            if chunk:
                print("Got audio chunk")
                break
        print("TTS working!")
    except Exception as e:
        print(f"TTS Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
