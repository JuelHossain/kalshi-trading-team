"""
Quick demo of the Rich Display System features.
This script demonstrates the key features without user interaction.
"""

import time
from core.display import (
    GhostDisplay,
    AgentType,
    get_display,
    show_startup_banner,
    show_agent_status,
    update_agent_status,
    log_info,
    log_warning,
    log_error,
    log_critical,
    log_success,
)


def main():
    print("\n" + "="*70)
    print("Ghost Engine v3.0 - Rich Display System Quick Demo")
    print("="*70 + "\n")

    # Get display instance
    display = get_display()

    # 1. Show startup banner
    print("1. Startup Banner:")
    print("-" * 70)
    show_startup_banner()
    time.sleep(1)

    # 2. Demonstrate log levels
    print("\n2. Log Levels:")
    print("-" * 70)
    log_debug("System initialization complete", AgentType.SOUL)
    log_info("Starting trading cycle #1", AgentType.SOUL)
    log_warning("Approaching rate limit", AgentType.SENSES)
    log_error("Failed to fetch market data", AgentType.SENSES)
    log_critical("Hard floor breach imminent", AgentType.SOUL)
    log_success("Trade executed successfully", AgentType.HAND)
    time.sleep(1)

    # 3. Demonstrate agent status
    print("\n3. Agent Status:")
    print("-" * 70)
    display.current_cycle = 42
    update_agent_status(AgentType.SOUL, "ACTIVE")
    update_agent_status(AgentType.SENSES, "SCANNING")
    update_agent_status(AgentType.BRAIN, "THINKING")
    update_agent_status(AgentType.HAND, "IDLE")
    show_agent_status()
    time.sleep(1)

    # 4. Demonstrate error display
    print("\n4. Error Display:")
    print("-" * 70)
    display.show_error(
        title="Connection Failed",
        message="Could not connect to Kalshi API",
        context="Network request timed out after 30 seconds",
        hint="Check your internet connection and API credentials",
        severity="ERROR",
        agent=AgentType.GATEWAY
    )
    time.sleep(1)

    # 5. Demonstrate progress tracking
    print("\n5. Trading Cycle Progress:")
    print("-" * 70)
    with display.cycle_progress(1, is_paper_trading=True) as progress:
        # SOUL phase
        log_info("Authorization check in progress...", AgentType.SOUL)
        time.sleep(0.5)
        progress.complete_phase("soul")

        # SENSES phase
        log_info("Scanning markets for opportunities...", AgentType.SENSES)
        time.sleep(0.5)
        progress.complete_phase("senses")

        # BRAIN phase
        log_info("Analyzing market data...", AgentType.BRAIN)
        time.sleep(0.5)
        progress.complete_phase("brain")

        # HAND phase
        log_info("Executing trade...", AgentType.HAND)
        time.sleep(0.5)
        progress.complete_phase("hand")

    # 6. Demonstrate agent thinking
    print("\n6. Agent Thinking Animation:")
    print("-" * 70)
    with display.agent_thinking(AgentType.BRAIN, "Running Monte Carlo simulation..."):
        time.sleep(1.5)

    # 7. Show system messages
    print("\n7. System Messages:")
    print("-" * 70)
    display.show_system_online()
    time.sleep(1)
    display.show_shutdown_message()

    print("\n" + "="*70)
    print("Demo Complete! All features demonstrated successfully.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
