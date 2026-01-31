
import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure engine is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "engine")))

# Mock environment variables
os.environ["KALSHI_API_KEY"] = "test_key"
os.environ["KALSHI_API_SECRET"] = "test_secret"
os.environ["SUPABASE_URL"] = "http://test-supabase.com"
os.environ["SUPABASE_KEY"] = "test_supabase_key"
os.environ["GEMINI_API_KEY"] = "test_gemini_key"

# Mock dependencies BEFORE importing agents
with patch("core.network.KalshiClient") as MockKalshi, \
     patch("core.db.supabase", new_callable=MagicMock) as MockSupabase:
     
    from agents.soul import SoulAgent
    from core.bus import EventBus
    from core.vault import RecursiveVault
    from core.network import kalshi_client

    async def test_api_checks_pass():
        print("\n--- TEST: API Checks PASS ---")
        
        # Setup Mocks
        bus = EventBus()
        vault = RecursiveVault()
        vault.current_balance = 30000
        
        # Mock Kalshi (Success)
        kalshi_client.get_balance = AsyncMock(return_value=1000)
        kalshi_client.get_active_markets = AsyncMock(return_value=[{"ticker": "TEST"}])
        
        # Mock Supabase (Success)
        # We need to mock check_connection. 
        # Since check_connection is imported in soul.py, we patch it there.
        with patch("agents.soul.check_supabase_connection", new_callable=AsyncMock) as mock_db_check:
            mock_db_check.return_value = True
            
            # Mock Gemini (Success - client exists)
            # SoulAgent init checks os.environ.
            
            soul = SoulAgent(1, bus, vault)
            soul.client = MagicMock() # Simulate Gemini client
            # Mock generate_content
            soul.client.models.generate_content = MagicMock(return_value=MagicMock(text="pong"))
            
            # Setup: Connect cycle start listener
            await soul.setup()
            
            # Run Check via Cycle Start (First Run)
            await soul.on_cycle_start(MagicMock())
            
            assert not soul.is_locked_down, "Soul should NOT be locked down if APIs are healthy"
            print("✅ PASS: Soul is active.")

    async def test_api_checks_fail_kalshi():
        print("\n--- TEST: API Checks FAIL (Kalshi) ---")
        
        bus = EventBus()
        vault = RecursiveVault()
        vault.current_balance = 50000  # Prevent Hard Floor
        
        # Mock Kalshi (Fail)
        kalshi_client.get_balance = AsyncMock(return_value=0)
        kalshi_client.get_active_markets = AsyncMock(return_value=[]) # Empty -> Fail
        
        with patch("agents.soul.check_supabase_connection", new_callable=AsyncMock) as mock_db_check:
            mock_db_check.return_value = True
            
            soul = SoulAgent(1, bus, vault)
            soul.client = MagicMock()
            
            # Use on_cycle_start instead of direct check
            await soul.setup()
            await soul.on_cycle_start(MagicMock())
            
            assert soul.is_locked_down, "Soul MUST be locked down if Kalshi fails"
            print("✅ PASS: Soul is locked down.")

    async def test_api_checks_fail_database():
        print("\n--- TEST: API Checks FAIL (Supabase) ---")
        
        bus = EventBus()
        vault = RecursiveVault()
        vault.current_balance = 50000  # Prevent Hard Floor
        kalshi_client.get_balance = AsyncMock(return_value=1000)
        
        with patch("agents.soul.check_supabase_connection", new_callable=AsyncMock) as mock_db_check:
            mock_db_check.return_value = False # Fail
            
            soul = SoulAgent(1, bus, vault)
            
            await soul.setup()
            await soul.on_cycle_start(MagicMock())
            
            assert soul.is_locked_down, "Soul MUST be locked down if Supabase fails"
            print("✅ PASS: Soul is locked down.")

    async def test_openrouter_fallback_success():
        print("\n--- TEST: OpenRouter Fallback SUCCESS ---")
        bus = EventBus()
        vault = RecursiveVault()
        vault.current_balance = 50000  # Prevent Hard Floor
        kalshi_client.get_balance = AsyncMock(return_value=1000)
        
        with patch("agents.soul.check_supabase_connection", new_callable=AsyncMock) as mock_db_check:
            mock_db_check.return_value = True
            
            soul = SoulAgent(1, bus, vault)
            # Mock Gemini Failure
            soul.client = MagicMock()
            soul.client.models.generate_content = MagicMock(side_effect=Exception("Gemini Down"))
            
            # Mock OpenRouter Key
            soul.openrouter_key = "test_or_key"
            
            with patch.object(soul, '_call_openrouter', new_callable=AsyncMock) as mock_or:
                mock_or.return_value = "OR Content"
                
                await soul.setup()
                await soul.on_cycle_start(MagicMock())
                
                assert not soul.is_locked_down, "Soul should be ACTIVE if OpenRouter succeeds"
                mock_or.assert_called_once()
                print("✅ PASS: OpenRouter Fallback worked.")

    async def test_all_ai_fail():
        print("\n--- TEST: ALL AI FAIL (Lockdown) ---")
        bus = EventBus()
        vault = RecursiveVault()
        vault.current_balance = 50000  # Prevent Hard Floor
        kalshi_client.get_balance = AsyncMock(return_value=1000)
        
        with patch("agents.soul.check_supabase_connection", new_callable=AsyncMock) as mock_db_check:
            mock_db_check.return_value = True
            
            soul = SoulAgent(1, bus, vault)
            soul.client = MagicMock()
            soul.client.models.generate_content = MagicMock(side_effect=Exception("Gemini Down"))
            soul.openrouter_key = "test_or_key"
            
            with patch.object(soul, '_call_openrouter', new_callable=AsyncMock) as mock_or:
                mock_or.return_value = None # Fail
                
                await soul.setup()
                await soul.on_cycle_start(MagicMock())
                
                assert soul.is_locked_down, "Soul MUST lock down if ALL AI fail"
                print("✅ PASS: All AI Fail triggers lockdown.")

    async def main():
        try:
            await test_api_checks_pass()
            await test_api_checks_fail_kalshi()
            await test_api_checks_fail_database()
            await test_openrouter_fallback_success()
            await test_all_ai_fail()
            print("\n🎉 ALL TESTS PASSED")
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ RUNTIME ERROR: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
