
import asyncio
import os
import sys

# Add project root to path
sys.path.append(r"c:\Users\archa\OneDrive\Desktop\MoneyOps\MoneyOps\ai-gateway")

from app.agents.finance_agent import finance_agent
from app.schemas.intents import Intent

async def test():
    print("Testing FinanceAgent analytics query with REAL endpoint...")
    
    # Simulate context from voice.py
    context = {
        "org_id": "9f3b96db-7e13-489d-a5a4-18ecdbc3d616",
        "user_id": "user_3A7rlO2f0Jq0iBG45BYBsj8LvtI",
        "business_id": 1,
        "user_input": "tell me what is my current revenue"
    }
    
    # Test ANALYTICS_QUERY
    resp = await finance_agent.process(
        intent=Intent.ANALYTICS_QUERY,
        entities={},
        context=context
    )
    
    print(f"Success: {resp.success}")
    print(f"Message: {resp.message}")
    if resp.data:
        print(f"Data: {resp.data.get('summary')}")

    # Test BALANCE_CHECK
    print("\nTesting FinanceAgent balance check...")
    resp = await finance_agent.process(
        intent=Intent.BALANCE_CHECK,
        entities={},
        context=context
    )
    print(f"Success: {resp.success}")
    print(f"Message: {resp.message}")

if __name__ == "__main__":
    asyncio.run(test())
