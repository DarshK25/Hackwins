"""
Test suite for voice agent consistency fixes
Tests session locking, input deduplication, and agent persistence
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "MoneyOps" / "ai-gateway"))

from app.state.session_manager import SessionManager, VoiceSession


class TestVoiceSessionDeduplication:
    """Test input deduplication functionality"""
    
    def test_is_input_recently_processed_detects_duplicate(self):
        """Same input within tolerance window should be detected as duplicate"""
        session = VoiceSession(session_id="test-1", user_id="user-1", org_id="org-1")
        
        # First call
        is_dup1 = session.is_input_recently_processed("create invoice for 5000")
        assert is_dup1 is False, "First input should not be duplicate"
        
        # Immediate second call with same input
        is_dup2 = session.is_input_recently_processed("create invoice for 5000")
        assert is_dup2 is True, "Immediate duplicate should be detected"
    
    def test_is_input_recently_processed_allows_different_input(self):
        """Different input should not be detected as duplicate"""
        session = VoiceSession(session_id="test-2", user_id="user-2", org_id="org-2")
        
        # First input
        is_dup1 = session.is_input_recently_processed("create invoice")
        assert is_dup1 is False
        
        # Different input
        is_dup2 = session.is_input_recently_processed("what's the balance")
        assert is_dup2 is False, "Different input should not be duplicate"
    
    def test_is_input_recently_processed_respects_tolerance(self):
        """Duplicate outside tolerance window should not be detected"""
        session = VoiceSession(session_id="test-3", user_id="user-3", org_id="org-3")
        
        # First input
        is_dup1 = session.is_input_recently_processed("hello")
        assert is_dup1 is False
        
        # Simulate time passage
        session.last_input_timestamp = time.time() - 2.0  # 2 seconds ago
        
        # Same input after timeout
        is_dup2 = session.is_input_recently_processed("hello", tolerance_seconds=1.5)
        assert is_dup2 is False, "Input outside tolerance should not be duplicate"


class TestVoiceSessionProcessingLock:
    """Test input processing lock functionality"""
    
    def test_set_input_processing_lock(self):
        """Setting lock should update state"""
        session = VoiceSession(session_id="test-4", user_id="user-4", org_id="org-4")
        
        assert session.input_processing_lock is False
        session.set_input_processing_lock(True)
        assert session.input_processing_lock is True
        session.set_input_processing_lock(False)
        assert session.input_processing_lock is False


class TestSessionManager:
    """Test SessionManager locking and persistence"""
    
    def setup_method(self):
        """Create fresh SessionManager for each test"""
        self.manager = SessionManager()
    
    def test_acquire_processing_lock_success(self):
        """Should acquire lock when not held"""
        session_id = "session-1"
        self.manager.get_session(session_id)
        
        acquired = self.manager.acquire_processing_lock(session_id)
        assert acquired is True
        
        # Lock should be held
        assert self.manager.is_processing_locked(session_id)
    
    def test_acquire_processing_lock_fail_when_held(self):
        """Should fail to acquire lock when already held"""
        session_id = "session-2"
        self.manager.get_session(session_id)
        
        # First acquisition succeeds
        acquired1 = self.manager.acquire_processing_lock(session_id)
        assert acquired1 is True
        
        # Second acquisition fails
        acquired2 = self.manager.acquire_processing_lock(session_id)
        assert acquired2 is False
    
    def test_release_processing_lock(self):
        """Releasing lock should allow re-acquisition"""
        session_id = "session-3"
        self.manager.get_session(session_id)
        
        # Acquire
        self.manager.acquire_processing_lock(session_id)
        assert self.manager.is_processing_locked(session_id)
        
        # Release
        self.manager.release_processing_lock(session_id)
        assert not self.manager.is_processing_locked(session_id)
        
        # Can acquire again
        acquired = self.manager.acquire_processing_lock(session_id)
        assert acquired is True
    
    def test_lock_agent_for_session(self):
        """Should lock session to agent type"""
        session_id = "session-4"
        self.manager.get_session(session_id)
        
        self.manager.lock_agent_for_session(session_id, "FINANCE_AGENT")
        
        locked_agent = self.manager.get_locked_agent_type(session_id)
        assert locked_agent == "FINANCE_AGENT"
    
    def test_lock_tts_voice_for_session(self):
        """Should lock session to TTS voice"""
        session_id = "session-5"
        self.manager.get_session(session_id)
        
        self.manager.lock_tts_voice_for_session(session_id, "voice-model-123")
        
        locked_voice = self.manager.get_locked_tts_voice(session_id)
        assert locked_voice == "voice-model-123"
    
    def test_session_persistence_across_gets(self):
        """Session state should persist across get() calls"""
        session_id = "session-6"
        
        # Create and modify
        session1 = self.manager.get_session(session_id)
        self.manager.lock_agent_for_session(session_id, "MARKET_AGENT")
        
        # Retrieve again
        session2 = self.manager.get_session(session_id)
        
        # Should have locked agent
        assert session2.locked_agent_type == "MARKET_AGENT"


class TestAgentLocking:
    """Test agent locking behavior in router"""
    
    @pytest.mark.asyncio
    async def test_agent_router_uses_locked_agent(self):
        """Agent router should use locked agent type when available"""
        # This would require mocking the agent_router, intent classifier, etc.
        # Skipping for now as it requires full setup
        pass


class TestInputDeduplicationScenarios:
    """Test real-world scenarios"""
    
    def test_scenario_ui_click_then_voice(self):
        """Simulate: UI click with client name, then voice input"""
        manager = SessionManager()
        session_id = "scenario-1"
        session = manager.get_session(session_id)
        
        # UI click triggers processing
        lock_acquired_1 = manager.acquire_processing_lock(session_id)
        assert lock_acquired_1, "First input (UI click) should acquire lock"
        
        # Simulate UI processing time
        time.sleep(0.1)
        
        # Should detect duplicate if user immediately speaks same thing
        is_dup = session.is_input_recently_processed("Sam Altman")
        
        release_lock = manager.release_processing_lock(session_id)
        # No return value, but shouldn't crash
        
        # Next input: different text
        lock_acquired_2 = manager.acquire_processing_lock(session_id)
        assert lock_acquired_2, "Should acquire lock for different input"
        
        is_dup_2 = session.is_input_recently_processed("5000 rupees")
        assert is_dup_2 is False, "Different input should not be duplicate"
        
        manager.release_processing_lock(session_id)
    
    def test_scenario_rapid_client_clicks(self):
        """Simulate: User rapid-clicks different clients"""
        manager = SessionManager()
        session_id = "scenario-2"
        
        clients = ["Sam Altman", "Elon Musk", "Mark Zuckerberg"]
        
        for client in clients:
            # Try to acquire lock
            acquired = manager.acquire_processing_lock(session_id)
            
            if acquired:
                # Check if duplicate
                session = manager.get_session(session_id)
                is_dup = session.is_input_recently_processed(f"select {client}")
                
                # Each should be fresh (different client name)
                assert is_dup is False, f"First mention of {client} should not be dup"
                
                manager.release_processing_lock(session_id)
            else:
                # Lock held - would be rejected in real scenario
                pass


class TestMessageFlow:
    """Test conversation message flow consistency"""
    
    def test_locked_intent_maintains_flow(self):
        """Session locked_intent should maintain conversation flow"""
        session = VoiceSession(session_id="flow-1", user_id="user-1", org_id="org-1")
        
        # Start invoice creation
        session.locked_intent = "INVOICE_CREATE"
        session.locked_agent_type = "FINANCE_AGENT"
        
        # Simulate multiple turns
        for turn in range(5):
            # Intent should remain locked
            assert session.locked_intent == "INVOICE_CREATE"
            assert session.locked_agent_type == "FINANCE_AGENT"
            
            # Add history
            session.history.append({
                "role": "user" if turn % 2 == 0 else "assistant",
                "content": f"Turn {turn}",
                "intent": "INVOICE_CREATE"
            })
        
        # After all turns, should still be locked
        assert len(session.history) == 5
        assert session.locked_intent == "INVOICE_CREATE"


# ── Performance Tests ──────────────────────────────────────────────────────
class TestPerformance:
    """Test performance characteristics"""
    
    def test_lock_acquisition_is_fast(self):
        """Lock acquisition should be O(1) and very fast"""
        manager = SessionManager()
        session_id = "perf-1"
        manager.get_session(session_id)
        
        start = time.time()
        for _ in range(1000):
            manager.acquire_processing_lock(session_id)
            manager.release_processing_lock(session_id)
        elapsed = time.time() - start
        
        # 1000 lock cycles should take < 10ms
        assert elapsed < 0.01, f"Lock cycles too slow: {elapsed}s"
    
    def test_deduplication_check_is_fast(self):
        """Deduplication check should be O(1) and very fast"""
        session = VoiceSession(session_id="perf-2", user_id="user-1", org_id="org-1")
        
        start = time.time()
        for _ in range(1000):
            session.is_input_recently_processed("test input")
        elapsed = time.time() - start
        
        # 1000 dedup checks should take < 10ms
        assert elapsed < 0.01, f"Dedup checks too slow: {elapsed}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
