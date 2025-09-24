"""
Command Line Interface for Galactus.
"""

import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..database.config import db_settings
from ..database.connection import engine, Base
from .events.producer import event_producer
from .events.consumer import EventConsumer

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Galactus - Semi-Autonomous Lab Management System."""
    pass


@cli.command()
def init_db():
    """Initialize the database with all tables."""
    console.print("[bold blue]Initializing Galactus database...[/bold blue]")

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        console.print("[green]✓[/green] Database tables created successfully")

        # Initialize TimescaleDB extension
        with engine.connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
            conn.commit()
            console.print("[green]✓[/green] TimescaleDB extension enabled")

        console.print("[bold green]Database initialization completed![/bold green]")
    except Exception as e:
        console.print(f"[red]✗[/red] Database initialization failed: {e}")
        raise click.Abort()


@cli.command()
def status():
    """Show system status."""
    console.print(Panel.fit("Galactus System Status", style="bold blue"))

    # Database status
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT version()")
            db_version = result.fetchone()[0]
        db_status = "[green]Connected[/green]"
    except Exception as e:
        db_version = "Unknown"
        db_status = f"[red]Error: {e}[/red]"

    # Kafka status
    try:
        # Try to send a test event
        test_event_sent = event_producer.send_event(
            event_type="test",
            entity_id="00000000-0000-0000-0000-000000000000",
            entity_type="system",
            data={"test": True}
        )
        kafka_status = "[green]Connected[/green]" if test_event_sent else "[yellow]Warning[/yellow]"
    except Exception as e:
        kafka_status = f"[red]Error: {e}[/red]"

    # Display status table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Details", style="white")

    table.add_row("Database", db_status, f"PostgreSQL - {db_version.split(' ')[1]}")
    table.add_row("Kafka", kafka_status, f"{db_settings.kafka_bootstrap_servers}")

    console.print(table)


@cli.command()
@click.option("--topic", default="galactus.*", help="Topic pattern to subscribe to")
@click.option("--event-types", help="Comma-separated list of event types to handle")
def consume_events(topic, event_types):
    """Consume events from Kafka."""
    console.print(f"[bold blue]Starting event consumer for topic: {topic}[/bold blue]")

    consumer = EventConsumer()

    # Subscribe to topics
    if topic == "galactus.*":
        # Subscribe to common event topics
        consumer.subscribe_to_entity_events("task", ["created", "started", "completed", "failed"])
        consumer.subscribe_to_entity_events("workflow", ["created", "started", "completed", "failed"])
        consumer.subscribe_to_entity_events("device", ["status_changed"])
        consumer.subscribe_to_entity_events("job", ["created", "started", "completed", "failed"])
    else:
        topics = [t.strip() for t in topic.split(",")]
        consumer.subscribe_to_topics(topics)

    # Register basic event handlers
    def handle_task_event(event):
        console.print(f"[cyan]Task Event:[/cyan] {event.event_type} - {event.entity_id}")

    def handle_workflow_event(event):
        console.print(f"[green]Workflow Event:[/green] {event.event_type} - {event.entity_id}")

    def handle_device_event(event):
        console.print(f"[yellow]Device Event:[/yellow] {event.event_type} - {event.entity_id}")

    consumer.register_handler("task.created", handle_task_event)
    consumer.register_handler("workflow.created", handle_workflow_event)
    consumer.register_handler("device.status_changed", handle_device_event)

    try:
        consumer.start()
        console.print("[green]Event consumer started. Press Ctrl+C to stop.[/green]")

        # Keep running
        while consumer.running:
            import time
            time.sleep(1)

    except KeyboardInterrupt:
        console.print("[yellow]Stopping event consumer...[/yellow]")
    finally:
        consumer.stop()
        console.print("[red]Event consumer stopped.[/red]")


@cli.command()
def launch_worker():
    """Launch a task execution worker."""
    console.print("[bold blue]Starting Galactus worker...[/bold blue]")
    console.print("[yellow]Worker functionality not yet implemented.[/yellow]")
    console.print("This will start the Celery worker for task execution.")


@cli.command()
def launch_scheduler():
    """Launch the resource scheduler."""
    console.print("[bold blue]Starting Galactus scheduler...[/bold blue]")
    console.print("[yellow]Scheduler functionality not yet implemented.[/yellow]")
    console.print("This will start the resource allocation and scheduling service.")


@cli.command()
def dashboard():
    """Launch the web dashboard."""
    console.print("[bold blue]Starting Galactus dashboard...[/bold blue]")
    console.print("[yellow]Dashboard functionality not yet implemented.[/yellow]")
    console.print("This will start the FastAPI-based web interface.")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
def api(host, port):
    """Start the REST API server."""
    console.print(f"[bold blue]Starting Galactus API server on {host}:{port}...[/bold blue]")
    console.print("[yellow]API server functionality not yet implemented.[/yellow]")
    console.print("This will start the FastAPI server for the REST API.")


@cli.command()
def health():
    """Check system health."""
    console.print(Panel.fit("Galactus Health Check", style="bold blue"))

    health_issues = []

    # Check database
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        console.print("[green]✓[/green] Database: Healthy")
    except Exception as e:
        console.print(f"[red]✗[/red] Database: Unhealthy - {e}")
        health_issues.append("Database connection failed")

    # Check Kafka
    try:
        if event_producer.send_event("health_check", "test", "system", {"status": "ok"}):
            console.print("[green]✓[/green] Kafka: Healthy")
        else:
            console.print("[yellow]⚠[/yellow] Kafka: Warning - Test event failed")
            health_issues.append("Kafka test event failed")
    except Exception as e:
        console.print(f"[red]✗[/red] Kafka: Unhealthy - {e}")
        health_issues.append("Kafka connection failed")

    # Summary
    if health_issues:
        console.print(f"\n[red]Found {len(health_issues)} health issues:[/red]")
        for issue in health_issues:
            console.print(f"  • {issue}")
        raise click.Abort()
    else:
        console.print("\n[green]All systems healthy![/green]")


if __name__ == "__main__":
    cli()
