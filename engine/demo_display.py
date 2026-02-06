"""
Ghost Engine v3.0 - Display System Demo
Showcase all features of the Rich-powered CLI display system.

Run this script to see the display system in action:
    python demo_display.py
"""

import asyncio
import time
from core.display import (
    GhostDisplay,
    AgentType,
    get_display,
    show_startup_banner,
    show_agent_status,
    update_agent_status,
    log_debug,
    log_info,
    log_warning,
    log_error,
    log_critical,
    log_success,
    show_error,
)


def demo_startup_banner():
    """Demo: Startup Banner"""
    print("\n" + "="*60)
    print("DEMO: Startup Banner")
    print("="*60 + "\n")
    show_startup_banner()


def demo_log_levels():
    """Demo: Log Levels"""
    print("\n" + "="*60)
    print("DEMO: Log Levels")
    print("="*60 + "\n")

    display = get_display()

    display.debug("This is a DEBUG message - detailed diagnostic information")
    display.info("This is an INFO message - general informational message")
    display.warning("This is a WARNING message - something unusual happened")
    display.error("This is an ERROR message - something went wrong")
    display.critical("This is a CRITICAL message - serious problem occurred")
    display.success("This is a SUCCESS message - operation completed successfully")

    print()


def demo_agent_logs():
    """Demo: Agent-specific logs"""
    print("\n" + "="*60)
    print("DEMO: Agent-specific Logs")
    print("="*60 + "\n")

    log_debug("Scanning markets for opportunities...", AgentType.SENSES)
    log_info("Found 3 potential trades", AgentType.SENSES)

    log_debug("Running Monte Carlo simulations...", AgentType.BRAIN)
    log_info("Analysis complete - 85% confidence", AgentType.BRAIN)

    log_info("Preparing to execute trade...", AgentType.HAND)
    log_success("Trade executed successfully", AgentType.HAND)

    log_warning("Balance below threshold", AgentType.SOUL)
    log_error("Failed to fetch market data", AgentType.SENSES)

    print()


def demo_agent_status():
    """Demo: Agent Status Table"""
    print("\n" + "="*60)
    print("DEMO: Agent Status Table")
    print("="*60 + "\n")

    display = get_display()
    display.current_cycle = 42

    # Set different agent statuses
    update_agent_status(AgentType.SOUL, "ACTIVE")
    update_agent_status(AgentType.SENSES, "SCANNING")
    update_agent_status(AgentType.BRAIN, "THINKING")
    update_agent_status(AgentType.HAND, "IDLE")
    update_agent_status(AgentType.GATEWAY, "ACTIVE")

    show_agent_status()

    # Reset statuses
    for agent in AgentType:
        update_agent_status(agent, "IDLE")


def demo_error_panels():
    """Demo: Error Panels"""
    print("\n" + "="*60)
    print("DEMO: Error Panels")
    print("="*60 + "\n")

    display = get_display()

    # Warning
    display.show_error(
        title="Rate Limit Warning",
        message="Approaching API rate limit",
        context="50 requests made in last minute (limit: 60)",
        hint="Consider adding a small delay between requests",
        severity="WARNING",
        agent=AgentType.SENSES
    )

    # Error
    display.show_error(
        title="Connection Failed",
        message="Could not connect to Kalshi API",
        context="Network request timed out after 30 seconds",
        hint="Check your internet connection and API credentials",
        severity="ERROR",
        agent=AgentType.GATEWAY
    )

    # Critical
    display.show_error(
        title="Hard Floor Breach",
        message="Account balance dropped below hard floor",
        context="Current balance: $200, Hard floor: $255",
        hint="System initiated emergency lockdown - manual review required",
        severity="CRITICAL",
        agent=AgentType.SOUL
    )


def demo_cycle_progress():
    """Demo: Cycle Progress"""
    print("\n" + "="*60)
    print("DEMO: Trading Cycle Progress")
    print("="*60 + "\n")

    display = get_display()
    display.current_cycle = 1

    with display.cycle_progress(1, is_paper_trading=True) as progress:
        # SOUL Phase
        time.sleep(0.3)
        progress.update_phase("soul", 50)
        log_info("Authorization check passed", AgentType.SOUL)
        time.sleep(0.3)
        progress.complete_phase("soul")

        # SENSES Phase
        time.sleep(0.3)
        progress.update_phase("senses", 50)
        log_info("Market scan complete - found 5 opportunities", AgentType.SENSES)
        time.sleep(0.3)
        progress.complete_phase("senses")

        # BRAIN Phase
        time.sleep(0.3)
        progress.update_phase("brain", 50)
        log_info("Intelligence analysis complete - 87% confidence", AgentType.BRAIN)
        time.sleep(0.3)
        progress.complete_phase("brain")

        # HAND Phase
        time.sleep(0.3)
        progress.update_phase("hand", 50)
        log_success("Order executed - YES @ $0.45", AgentType.HAND)
        time.sleep(0.3)
        progress.complete_phase("hand")


def demo_agent_thinking():
    """Demo: Agent Thinking Animation"""
    print("\n" + "="*60)
    print("DEMO: Agent Thinking Animation")
    print("="*60 + "\n")

    display = get_display()

    # BRAIN thinking
    with display.agent_thinking(AgentType.BRAIN, "Running Monte Carlo simulation..."):
        time.sleep(1.5)

    # SENSES thinking
    with display.agent_thinking(AgentType.SENSES, "Scanning markets..."):
        time.sleep(1.5)

    # HAND thinking
    with display.agent_thinking(AgentType.HAND, "Executing order..."):
        time.sleep(1.5)


def demo_system_messages():
    """Demo: System Messages"""
    print("\n" + "="*60)
    print("DEMO: System Messages")
    print("="*60 + "\n")

    display = get_display()

    display.show_system_online()
    display.show_shutdown_message()


def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("GHOST ENGINE v3.0 - DISPLAY SYSTEM DEMO")
    print("="*60)
    print("\nThis demo showcases all features of the Rich-powered")
    print("CLI display system for the Ghost Engine.\n")

    demos = [
        ("Startup Banner", demo_startup_banner),
        ("Log Levels", demo_log_levels),
        ("Agent-specific Logs", demo_agent_logs),
        ("Agent Status Table", demo_agent_status),
        ("Error Panels", demo_error_panels),
        ("Trading Cycle Progress", demo_cycle_progress),
        ("Agent Thinking Animation", demo_agent_thinking),
        ("System Messages", demo_system_messages),
    ]

    print("Available demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  all. Run all demos")
    print()

    choice = input("Select a demo (1-8, or 'all'): ").strip().lower()

    if choice == "all":
        for name, demo_func in demos:
            demo_func()
            input("\nPress Enter to continue to next demo...")
    elif choice.isdigit() and 1 <= int(choice) <= len(demos):
        name, demo_func = demos[int(choice) - 1]
        demo_func()
    else:
        print("Invalid choice. Running all demos...")
        for name, demo_func in demos:
            demo_func()
            input("\nPress Enter to continue to next demo...")

    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
