"""
Terminal Test Interface for Voice Agent
Simulates voice input → AI Gateway → Response flow
"""
import asyncio
import sys
from typing import Optional
import uuid

from app.agent.adapters import ai_gateway_client
from app.config import settings
from app.utils.logger import setup_logging, get_logger

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


class TerminalVoiceTester:
    """Test voice agent via terminal input"""
    
    def __init__(self, user_id: str, org_id: str):
        self.user_id = user_id
        self.org_id = org_id
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []
    
    async def process_input(self, text: str) -> str:
        """Process text input as if it came from voice"""
        print(f"\n📝 You: {text}")
        print("🔄 Processing...")
        
        # Call AI Gateway directly (same as voice flow)
        response = await ai_gateway_client.process_voice_input(
            text=text,
            user_id=self.user_id,
            org_id=self.org_id,
            session_id=self.session_id,
            conversation_history=self.conversation_history,
        )
        
        # Extract response
        response_text = response.get("response_text", "No response")
        intent = response.get("intent", "UNKNOWN")
        confidence = response.get("confidence", 0.0)
        
        # Update conversation history
        self.conversation_history.append({
            "role": "user",
            "content": text
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Print response
        print(f"\n🤖 Agent: {response_text}")
        print(f"   Intent: {intent} (confidence: {confidence:.2f})")
        
        return response_text
    
    async def run_interactive(self):
        """Run interactive terminal session"""
        print("=" * 60)
        print("LedgerTalk Voice Agent - Terminal Test Mode")
        print("=" * 60)
        print(f"Session ID: {self.session_id}")
        print(f"User ID: {self.user_id}")
        print(f"Org ID: {self.org_id}")
        print(f"AI Gateway: {settings.AI_GATEWAY_URL}")
        print("\nType your commands (or 'exit' to quit):\n")
        
        # Check AI Gateway health
        is_healthy = await ai_gateway_client.health_check()
        if not is_healthy:
            print("⚠️  Warning: AI Gateway health check failed!")
            print(f"   Make sure AI Gateway is running at {settings.AI_GATEWAY_URL}")
        else:
            print("✅ AI Gateway is healthy\n")
        
        while True:
            try:
                # Get user input
                user_input = input("\n💬 > ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                # Process input
                await self.process_input(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error("terminal_error", error=str(e))
                print(f"\n❌ Error: {e}")


async def main():
    """Main entry point"""
    # Default test user/org (can be overridden via env or args)
    user_id = sys.argv[1] if len(sys.argv) > 1 else "test-user-001"
    org_id = sys.argv[2] if len(sys.argv) > 2 else "test-org-001"
    
    tester = TerminalVoiceTester(user_id=user_id, org_id=org_id)
    await tester.run_interactive()
    
    # Cleanup
    await ai_gateway_client.close()


if __name__ == "__main__":
    asyncio.run(main())
