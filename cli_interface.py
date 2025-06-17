"""
CLI Interface - The command-line control panel for the multi-agent system.
This provides a terminal-based interface for monitoring and controlling the system.
Think of it as the old-school terminal that still gets the job done.
"""

import asyncio
import json
import sys
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import argparse

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.align import Align

from system_orchestrator import orchestrator
from utils.message_bus import message_bus
from config import config

console = Console()

class CLIInterface:
    """Command-line interface for the multi-agent monitoring system."""
    
    def __init__(self):
        self.running = False
        self.system_task = None
    
    async def start(self):
        """Start the CLI interface."""
        self.running = True
        
        # Start the system in the background
        self.system_task = asyncio.create_task(self._start_system())
        
        # Wait a moment for system to start
        await asyncio.sleep(2)
        
        # Show main menu
        await self._main_menu()
    
    async def stop(self):
        """Stop the CLI interface."""
        self.running = False
        
        if self.system_task:
            self.system_task.cancel()
            try:
                await self.system_task
            except asyncio.CancelledError:
                pass
        
        await orchestrator.stop()
    
    async def _start_system(self):
        """Start the multi-agent system."""
        try:
            await orchestrator.start()
        except Exception as e:
            console.print(f"[red]Failed to start system: {e}[/red]")
    
    async def _main_menu(self):
        """Display the main menu."""
        while self.running:
            console.clear()
            
            # Show system status
            await self._show_system_status()
            
            # Show menu options
            console.print("\n[bold cyan]Multi-Agent Monitoring System - CLI[/bold cyan]")
            console.print("=" * 50)
            console.print("1. 📊 System Status")
            console.print("2. 🤖 Agent Details")
            console.print("3. 📈 System Metrics")
            console.print("4. 🧠 Analysis Results")
            console.print("5. 🔧 Remediation Status")
            console.print("6. 📡 Message Bus")
            console.print("7. ⚙️ Configuration")
            console.print("8. 🎮 Send Commands")
            console.print("9. 📋 Live Monitoring")
            console.print("0. 🚪 Exit")
            console.print("=" * 50)
            
            try:
                choice = Prompt.ask("Select an option", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"])
                
                if choice == "0":
                    if Confirm.ask("Are you sure you want to exit?"):
                        await self.stop()
                        break
                elif choice == "1":
                    await self._show_detailed_status()
                elif choice == "2":
                    await self._show_agent_details()
                elif choice == "3":
                    await self._show_system_metrics()
                elif choice == "4":
                    await self._show_analysis_results()
                elif choice == "5":
                    await self._show_remediation_status()
                elif choice == "6":
                    await self._show_message_bus()
                elif choice == "7":
                    await self._show_configuration()
                elif choice == "8":
                    await self._send_commands()
                elif choice == "9":
                    await self._live_monitoring()
                
                if choice != "0":
                    Prompt.ask("\nPress Enter to continue")
                    
            except KeyboardInterrupt:
                if Confirm.ask("\nAre you sure you want to exit?"):
                    await self.stop()
                    break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                Prompt.ask("\nPress Enter to continue")
    
    async def _show_system_status(self):
        """Show current system status."""
        try:
            system_info = orchestrator.get_system_info()
            
            # Create status panel
            status_text = f"""
[bold]System Health:[/bold] {system_info.get('system_health', 'Unknown')}
[bold]Uptime:[/bold] {system_info.get('uptime', 0):.0f} seconds
[bold]Agents:[/bold] {system_info.get('running_agents', 0)}/{system_info.get('total_agents', 0)} running
[bold]Start Time:[/bold] {system_info.get('startup_time', 'Unknown')}
            """
            
            health_color = "green" if system_info.get('system_health') == 'healthy' else \
                          "yellow" if system_info.get('system_health') == 'warning' else \
                          "red" if system_info.get('system_health') == 'critical' else "white"
            
            panel = Panel(
                status_text,
                title="[bold]System Status[/bold]",
                border_style=health_color
            )
            
            console.print(panel)
            
        except Exception as e:
            console.print(f"[red]Error getting system status: {e}[/red]")
    
    async def _show_detailed_status(self):
        """Show detailed system status."""
        console.clear()
        console.print("[bold cyan]Detailed System Status[/bold cyan]")
        console.print("=" * 50)
        
        try:
            system_info = orchestrator.get_system_info()
            
            # System overview
            console.print(f"[bold]System Health:[/bold] {system_info.get('system_health', 'Unknown')}")
            console.print(f"[bold]Uptime:[/bold] {system_info.get('uptime', 0):.0f} seconds")
            console.print(f"[bold]Total Agents:[/bold] {system_info.get('total_agents', 0)}")
            console.print(f"[bold]Running Agents:[/bold] {system_info.get('running_agents', 0)}")
            
            # Agent details table
            table = Table(title="Agent Details")
            table.add_column("Agent", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("Health", style="yellow")
            table.add_column("Uptime", style="blue")
            table.add_column("Checks", style="white")
            table.add_column("Errors", style="red")
            
            for name, details in system_info.get('agent_details', {}).items():
                status_color = "green" if details.get('status') == 'running' else "red"
                health_color = "green" if details.get('health') == 'healthy' else \
                              "yellow" if details.get('health') == 'warning' else \
                              "red" if details.get('health') == 'critical' else "white"
                
                table.add_row(
                    name,
                    details.get('type', 'Unknown'),
                    f"[{status_color}]{details.get('status', 'Unknown')}[/{status_color}]",
                    f"[{health_color}]{details.get('health', 'Unknown')}[/{health_color}]",
                    f"{details.get('uptime', 0):.0f}s",
                    str(details.get('check_count', 0)),
                    str(details.get('error_count', 0))
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    async def _show_agent_details(self):
        """Show detailed information about a specific agent."""
        console.clear()
        console.print("[bold cyan]Agent Details[/bold cyan]")
        console.print("=" * 50)
        
        # List available agents
        agents = ["sensor", "analyzer", "remediator", "communicator"]
        for i, agent in enumerate(agents, 1):
            console.print(f"{i}. {agent}")
        
        console.print("0. Back to main menu")
        
        try:
            choice = Prompt.ask("Select an agent", choices=["0", "1", "2", "3", "4"])
            
            if choice == "0":
                return
            
            agent_name = agents[int(choice) - 1]
            stats = orchestrator.get_agent_stats(agent_name)
            
            if stats:
                console.print(f"\n[bold]Agent: {agent_name}[/bold]")
                console.print(f"Type: {stats.get('agent_type', 'Unknown')}")
                console.print(f"Status: {stats.get('running', False)}")
                console.print(f"Health: {stats.get('health_status', 'Unknown')}")
                console.print(f"Uptime: {stats.get('uptime', 0):.0f} seconds")
                console.print(f"Check Count: {stats.get('check_count', 0)}")
                console.print(f"Error Count: {stats.get('error_count', 0)}")
                console.print(f"Success Count: {stats.get('success_count', 0)}")
                console.print(f"Average Response Time: {stats.get('avg_response_time', 0):.3f}s")
                
                if stats.get('issues_detected'):
                    console.print(f"\n[bold]Recent Issues:[/bold]")
                    for issue in stats['issues_detected'][-5:]:
                        console.print(f"  - {issue.get('description', 'Unknown')}")
            else:
                console.print(f"[red]No data available for agent {agent_name}[/red]")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    async def _show_system_metrics(self):
        """Show current system metrics."""
        console.clear()
        console.print("[bold cyan]System Metrics[/bold cyan]")
        console.print("=" * 50)
        
        try:
            # Get metrics from sensor agent
            sensor_agent = orchestrator.agents.get("sensor")
            if sensor_agent and hasattr(sensor_agent, 'get_current_metrics'):
                metrics = sensor_agent.get_current_metrics()
                
                if metrics:
                    # CPU metrics
                    if 'cpu' in metrics:
                        cpu = metrics['cpu']
                        console.print(f"[bold]CPU Usage:[/bold] {cpu.get('usage_percent', 'N/A')}%")
                        console.print(f"[bold]CPU Cores:[/bold] {cpu.get('core_count', 'N/A')}")
                    
                    # Memory metrics
                    if 'memory' in metrics:
                        memory = metrics['memory']
                        console.print(f"[bold]Memory Usage:[/bold] {memory.get('usage_percent', 'N/A')}%")
                        console.print(f"[bold]Memory Total:[/bold] {memory.get('total_gb', 'N/A'):.1f} GB")
                        console.print(f"[bold]Memory Available:[/bold] {memory.get('available_gb', 'N/A'):.1f} GB")
                    
                    # Disk metrics
                    if 'disk' in metrics:
                        console.print(f"\n[bold]Disk Usage:[/bold]")
                        for path, disk in metrics['disk'].items():
                            console.print(f"  {path}: {disk.get('usage_percent', 'N/A')}%")
                    
                    # Performance metrics
                    if 'performance' in metrics:
                        perf = metrics['performance']
                        console.print(f"\n[bold]System Load Score:[/bold] {perf.get('system_load_score', 'N/A'):.1f}/100")
                        console.print(f"[bold]Health Status:[/bold] {perf.get('health_status', 'N/A')}")
                        console.print(f"[bold]Performance Trend:[/bold] {perf.get('performance_trend', 'N/A')}")
                        
                        if perf.get('bottlenecks'):
                            console.print(f"\n[bold]Bottlenecks:[/bold]")
                            for bottleneck in perf['bottlenecks']:
                                console.print(f"  - {bottleneck}")
                else:
                    console.print("[yellow]No metrics available[/yellow]")
            else:
                console.print("[red]Sensor agent not available[/red]")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    async def _show_analysis_results(self):
        """Show analysis results."""
        console.clear()
        console.print("[bold cyan]Analysis Results[/bold cyan]")
        console.print("=" * 50)
        
        try:
            analyzer_agent = orchestrator.agents.get("analyzer")
            if analyzer_agent and hasattr(analyzer_agent, 'get_analysis_summary'):
                summary = analyzer_agent.get_analysis_summary()
                
                if 'error' not in summary:
                    console.print(f"[bold]Health Score:[/bold] {summary.get('health_score', 'N/A')}")
                    console.print(f"[bold]Issues Detected:[/bold] {summary.get('issues_detected', 0)}")
                    console.print(f"[bold]GPT Confidence:[/bold] {summary.get('gpt_confidence', 'N/A')}")
                    console.print(f"[bold]Risk Level:[/bold] {summary.get('risk_level', 'N/A')}")
                    
                    if summary.get('latest_analysis'):
                        analysis = summary['latest_analysis']
                        if 'gpt_analysis' in analysis:
                            gpt = analysis['gpt_analysis']
                            console.print(f"\n[bold]GPT Decision:[/bold] {gpt.get('decision', 'N/A')}")
                            console.print(f"[bold]Reasoning:[/bold] {gpt.get('reasoning', 'N/A')}")
                            console.print(f"[bold]Suggested Actions:[/bold]")
                            for action in gpt.get('suggested_actions', []):
                                console.print(f"  - {action}")
                else:
                    console.print(f"[red]Error: {summary['error']}[/red]")
            else:
                console.print("[red]Analyzer agent not available[/red]")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    async def _show_remediation_status(self):
        """Show remediation status."""
        console.clear()
        console.print("[bold cyan]Remediation Status[/bold cyan]")
        console.print("=" * 50)
        
        try:
            remediator_agent = orchestrator.agents.get("remediator")
            if remediator_agent and hasattr(remediator_agent, 'get_remediation_summary'):
                summary = remediator_agent.get_remediation_summary()
                
                console.print(f"[bold]Total Actions:[/bold] {summary.get('total_actions', 0)}")
                console.print(f"[bold]Successful Remediations:[/bold] {summary.get('successful_remediations', 0)}")
                console.print(f"[bold]Failed Remediations:[/bold] {summary.get('failed_remediations', 0)}")
                console.print(f"[bold]Success Rate:[/bold] {summary.get('success_rate', 0):.1f}%")
                console.print(f"[bold]Active Remediations:[/bold] {summary.get('active_remediations', 0)}")
                
                if summary.get('recent_attempts'):
                    console.print(f"\n[bold]Recent Remediation Attempts:[/bold]")
                    for attempt in summary['recent_attempts'][-5:]:
                        success_color = "green" if attempt.get('success') else "red"
                        console.print(f"  [{success_color}]{'✓' if attempt.get('success') else '✗'}[/{success_color}] {attempt.get('action', 'Unknown')}")
                
                if summary.get('failed_attempts'):
                    console.print(f"\n[bold]Failed Attempts by Issue:[/bold]")
                    for issue, count in summary['failed_attempts'].items():
                        console.print(f"  {issue}: {count} attempts")
            else:
                console.print("[red]Remediator agent not available[/red]")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    async def _show_message_bus(self):
        """Show message bus statistics."""
        console.clear()
        console.print("[bold cyan]Message Bus Statistics[/bold cyan]")
        console.print("=" * 50)
        
        try:
            stats = message_bus.get_stats()
            
            console.print(f"[bold]Running:[/bold] {stats.get('running', False)}")
            console.print(f"[bold]History Size:[/bold] {stats.get('history_size', 0)}")
            
            console.print(f"\n[bold]Queue Sizes:[/bold]")
            for priority, size in stats.get('queue_sizes', {}).items():
                console.print(f"  {priority}: {size}")
            
            console.print(f"\n[bold]Subscriber Counts:[/bold]")
            for msg_type, count in stats.get('subscriber_counts', {}).items():
                console.print(f"  {msg_type}: {count}")
            
            # Show recent messages
            recent_messages = message_bus.get_recent_messages(10)
            if recent_messages:
                console.print(f"\n[bold]Recent Messages:[/bold]")
                for msg in recent_messages:
                    console.print(f"  [{msg.get('timestamp', 'Unknown')}] {msg.get('sender', 'Unknown')} → {msg.get('type', 'Unknown')}")
                    
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    async def _show_configuration(self):
        """Show system configuration."""
        console.clear()
        console.print("[bold cyan]System Configuration[/bold cyan]")
        console.print("=" * 50)
        
        try:
            config_dict = config.to_dict()
            
            # Show key configuration sections
            console.print(f"[bold]Thresholds:[/bold]")
            thresholds = config_dict.get('thresholds', {})
            for key, value in thresholds.items():
                console.print(f"  {key}: {value}")
            
            console.print(f"\n[bold]GPT Configuration:[/bold]")
            gpt_config = config_dict.get('gpt', {})
            for key, value in gpt_config.items():
                if key != 'api_key':  # Don't show API key
                    console.print(f"  {key}: {value}")
            
            console.print(f"\n[bold]Agent Configuration:[/bold]")
            agents_config = config_dict.get('agents', {})
            for agent_name, agent_config in agents_config.items():
                console.print(f"  {agent_name}: {agent_config.get('check_interval', 'N/A')}s interval")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    async def _send_commands(self):
        """Send commands to the system."""
        console.clear()
        console.print("[bold cyan]Send Commands[/bold cyan]")
        console.print("=" * 50)
        
        console.print("Available commands:")
        console.print("1. status - Get system status")
        console.print("2. health_check - Perform health check")
        console.print("3. restart - Restart system")
        console.print("4. custom - Send custom command")
        console.print("0. Back to main menu")
        
        try:
            choice = Prompt.ask("Select a command", choices=["0", "1", "2", "3", "4"])
            
            if choice == "0":
                return
            
            commands = {
                "1": "status",
                "2": "health_check", 
                "3": "restart"
            }
            
            if choice in commands:
                command = commands[choice]
                target = Prompt.ask("Target (all/sensor/analyzer/remediator/communicator)", default="all")
                
                console.print(f"[yellow]Sending command '{command}' to {target}...[/yellow]")
                await orchestrator.send_command(command, target)
                console.print("[green]Command sent successfully![/green]")
                
            elif choice == "4":
                command = Prompt.ask("Enter custom command")
                target = Prompt.ask("Target", default="all")
                
                console.print(f"[yellow]Sending custom command '{command}' to {target}...[/yellow]")
                await orchestrator.send_command(command, target)
                console.print("[green]Command sent successfully![/green]")
                
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    async def _live_monitoring(self):
        """Show live monitoring dashboard."""
        console.clear()
        console.print("[bold cyan]Live Monitoring Dashboard[/bold cyan]")
        console.print("Press Ctrl+C to return to main menu")
        console.print("=" * 50)
        
        try:
            with Live(auto_refresh=True, refresh_per_second=1) as live:
                while True:
                    # Get current system info
                    system_info = orchestrator.get_system_info()
                    
                    # Create layout
                    layout = Layout()
                    layout.split_column(
                        Layout(name="header", size=3),
                        Layout(name="body"),
                        Layout(name="footer", size=3)
                    )
                    
                    layout["body"].split_row(
                        Layout(name="left"),
                        Layout(name="right")
                    )
                    
                    # Header
                    header_text = f"🤖 Multi-Agent System | Health: {system_info.get('system_health', 'Unknown')} | Uptime: {system_info.get('uptime', 0):.0f}s"
                    layout["header"].update(Panel(header_text, title="System Status"))
                    
                    # Left panel - Agent status
                    agent_text = ""
                    for name, details in system_info.get('agent_details', {}).items():
                        status_icon = "🟢" if details.get('status') == 'running' else "🔴"
                        agent_text += f"{status_icon} {name}: {details.get('health', 'Unknown')}\n"
                    
                    layout["left"].update(Panel(agent_text, title="Agent Health"))
                    
                    # Right panel - Metrics
                    try:
                        sensor_agent = orchestrator.agents.get("sensor")
                        if sensor_agent and hasattr(sensor_agent, 'get_current_metrics'):
                            metrics = sensor_agent.get_current_metrics()
                            metrics_text = ""
                            
                            if metrics.get('cpu'):
                                metrics_text += f"CPU: {metrics['cpu'].get('usage_percent', 'N/A')}%\n"
                            if metrics.get('memory'):
                                metrics_text += f"Memory: {metrics['memory'].get('usage_percent', 'N/A')}%\n"
                            if metrics.get('disk'):
                                for path, disk in metrics['disk'].items():
                                    metrics_text += f"Disk {path}: {disk.get('usage_percent', 'N/A')}%\n"
                            
                            layout["right"].update(Panel(metrics_text, title="System Metrics"))
                    except:
                        layout["right"].update(Panel("Metrics unavailable", title="System Metrics"))
                    
                    # Footer
                    footer_text = f"Last update: {datetime.now().strftime('%H:%M:%S')} | Press Ctrl+C to exit"
                    layout["footer"].update(Panel(footer_text, title="Controls"))
                    
                    live.update(layout)
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]Returning to main menu...[/yellow]")
        except Exception as e:
            console.print(f"[red]Error in live monitoring: {e}[/red]")

async def main():
    """Main entry point for CLI interface."""
    cli = CLIInterface()
    
    try:
        await cli.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        await cli.stop()

if __name__ == "__main__":
    asyncio.run(main()) 