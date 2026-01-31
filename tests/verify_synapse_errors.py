
import asyncio
import os
import sys
import shutil
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure engine is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "engine")))

# Mock environment variables for local test
os.environ["KALSHI_API_KEY"] = "test"
os.environ["KALSHI_API_SECRET"] = "test"
os.environ["SUPABASE_URL"] = "http://test.com"
os.environ["SUPABASE_KEY"] = "test"

async def test_synapse_error_halting():
    print("\n--- TEST: Synapse Error Halting ---")
    
    from core.synapse import Synapse, SynapseError
    from core.bus import EventBus
    from core.vault import RecursiveVault
    from main import GhostEngine
    
    # Use a temporary test DB
    test_db = "test_synapse_halt.db"
    if os.path.exists(test_db):
        os.remove(test_db)
        
    try:
        synapse = Synapse(test_db)
        bus = EventBus()
        vault = RecursiveVault()
        vault.current_balance = 30000  # $300 balance
        
        # Initialize Engine (Mocked agents to avoid full startup)
        with patch("main.SoulAgent"), patch("main.SensesAgent"), \
             patch("main.BrainAgent"), patch("main.HandAgent"), \
             patch("main.GatewayAgent"), patch("core.network.kalshi_client"):
            
            engine = GhostEngine()
            engine.synapse = synapse
            engine.vault = vault
            
            # 1. Verify authorize_cycle passes when NO errors
            is_auth = await engine.authorize_cycle()
            assert is_auth is True, "Should be authorized when error box is empty"
            print("✅ PASS: Authorized when no errors.")
            
            # 2. Inject an error into Synapse Error Box
            err = SynapseError(
                agent_name="TEST_AGENT",
                code="DATA_VALIDATION_FAILED",
                message="Test Error",
                severity="CRITICAL",
                domain="SYSTEM"
            )
            await synapse.errors.push(err)
            
            # 3. Verify authorize_cycle FAILS now
            is_auth = await engine.authorize_cycle()
            assert is_auth is False, "Should NOT be authorized when error box has errors"
            print("✅ PASS: Halting confirmed when error box has items.")
            
    finally:
        if os.path.exists(test_db):
            os.remove(test_db)

async def test_error_dispatcher_integration():
    print("\n--- TEST: ErrorDispatcher -> Synapse Integration ---")
    
    from core.synapse import Synapse
    from core.error_dispatcher import ErrorDispatcher, ErrorSeverity
    
    test_db = "test_error_dispatch.db"
    if os.path.exists(test_db):
        os.remove(test_db)
        
    try:
        synapse = Synapse(test_db)
        bus = MagicMock()
        
        dispatcher = ErrorDispatcher("TEST_AGENT", event_bus=bus, synapse=synapse)
        
        # Dispatch an error
        await dispatcher.dispatch(
            code="INTELLIGENCE_AI_UNAVAILABLE",
            message="Gemini is down for test",
            severity=ErrorSeverity.CRITICAL
        )
        
        # Give async task a small moment to complete
        await asyncio.sleep(0.2)
        
        # Verify it exists in Synapse
        err_count = await synapse.errors.size()
        assert err_count == 1, f"Expected 1 error in Synapse, got {err_count}"
        
        popped_err = await synapse.errors.pop()
        assert popped_err.agent_name == "TEST_AGENT"
        assert popped_err.code == "INTELLIGENCE_AI_UNAVAILABLE"
        print("✅ PASS: ErrorDispatcher correctly persisted error to Synapse.")
        
    finally:
        if os.path.exists(test_db):
            os.remove(test_db)

async def main():
    try:
        await test_synapse_error_halting()
        await test_error_dispatcher_integration()
        print("\n🎉 ALL SYNAPSE ERROR TESTS PASSED")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ RUNTIME ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
