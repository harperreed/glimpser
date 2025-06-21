#!/usr/bin/env python3
"""Initial setup script for Glimpser application.

This script creates an admin user, configures sane default settings,
and adds example templates to help new users get started.
"""

import argparse
import getpass
import logging
import os
import secrets
import sqlite3
import sys
from datetime import datetime

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
from werkzeug.security import generate_password_hash

import app.config

console = Console()


def create_tables(conn):
    """
    Create all required SQLite database tables for the Glimpser application if they do not already exist.
    
    This includes tables for application settings, users, templates, summaries, push notification subscriptions, and offline jobs. Commits the schema changes to the database.
    """
    cursor = conn.cursor()

    # Settings table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL
        );
    """
    )

    # Users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT
        );
    """
    )

    # Templates table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            frequency INTEGER DEFAULT 60,
            timeout INTEGER DEFAULT 10,
            notes TEXT DEFAULT '',
            motion_filter TEXT DEFAULT '',
            last_caption TEXT DEFAULT '',
            last_caption_time TEXT DEFAULT '',
            last_motion_caption TEXT DEFAULT '',
            last_motion_time TEXT DEFAULT '',
            last_screenshot_time TEXT DEFAULT '',
            last_video_time TEXT DEFAULT '',
            offline_since TEXT DEFAULT '',
            capture_failed BOOLEAN DEFAULT 0,
            object_filter TEXT DEFAULT '',
            object_confidence REAL DEFAULT 0.5,
            popup_xpath TEXT DEFAULT '',
            dedicated_xpath TEXT DEFAULT '',
            callback_url TEXT DEFAULT '',
            proxy TEXT DEFAULT '',
            auth_username TEXT DEFAULT '',
            auth_password TEXT DEFAULT '',
            url TEXT DEFAULT '',
            thumbnail TEXT DEFAULT '',
            groups TEXT DEFAULT '',
            invert BOOLEAN DEFAULT 0,
            dark BOOLEAN DEFAULT 0,
            headless BOOLEAN DEFAULT 1,
            stealth BOOLEAN DEFAULT 0,
            browser BOOLEAN DEFAULT 0,
            livecaption BOOLEAN DEFAULT 0,
            danger BOOLEAN DEFAULT 0,
            motion REAL DEFAULT 0.2,
            rollback_frames INTEGER DEFAULT 0
        );
    """
    )

    # Summaries table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            content TEXT NOT NULL
        );
    """
    )

    # Push subscriptions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL UNIQUE,
            auth TEXT NOT NULL,
            p256dh TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """
    )

    # Offline jobs table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS offline_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            function TEXT NOT NULL,
            args TEXT NOT NULL,
            timeout INTEGER NOT NULL,
            timestamp INTEGER NOT NULL
        );
    """
    )

    conn.commit()


def upsert_setting(conn, name, value):
    """
    Insert or update a configuration setting in the database by name.
    
    If a setting with the given name exists, its value is updated; otherwise, a new setting is inserted. Does nothing if the value is None.
    """
    if value is None:
        return

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO settings (name, value)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET value=excluded.value;
    """,
        (name, value),
    )
    conn.commit()


def upsert_user(conn, username, password_hash, role):
    """
    Insert a new user or update an existing user's password hash and role in the database.
    
    If a user with the given username already exists, their password hash and role are updated.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (username, password_hash, role)
        VALUES (?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            password_hash=excluded.password_hash,
            role=excluded.role;
    """,
        (username, password_hash, role),
    )
    conn.commit()


def insert_template(conn, template_data):
    """
    Insert a new template into the database if a template with the same name does not already exist.
    
    Parameters:
        template_data (dict): Dictionary containing template fields and their values.
    
    Returns:
        bool: True if the template was inserted, False if a template with the same name already exists.
    """
    cursor = conn.cursor()

    # Check if template already exists
    cursor.execute(
        "SELECT COUNT(*) FROM templates WHERE name = ?", (template_data["name"],)
    )
    if cursor.fetchone()[0] > 0:
        return False

    # Insert the template
    columns = ", ".join(template_data.keys())
    placeholders = ", ".join(["?" for _ in template_data])
    query = f"INSERT INTO templates ({columns}) VALUES ({placeholders})"

    cursor.execute(query, list(template_data.values()))
    conn.commit()
    return True


def setup_default_settings(conn):
    """
    Populate the database with default configuration settings for the Glimpser application.
    
    This function inserts or updates a comprehensive set of default settings covering application basics, security, performance, capture, UI, browser, scheduler, hardware acceleration, and feature toggles. Existing settings are updated; missing ones are created.
    """
    with console.status("[bold green]Setting up default configuration..."):
        # Application basics
        upsert_setting(conn, "NAME", "Glimpser")
        upsert_setting(conn, "HOST", "0.0.0.0")
        upsert_setting(conn, "PORT", "8082")
        upsert_setting(conn, "DEBUG", "False")
        upsert_setting(conn, "LOG_LEVEL", "INFO")
        upsert_setting(conn, "LOG_COLOR", "True")

        # Security settings
        upsert_setting(conn, "SESSION_COOKIE_SECURE", "True")
        upsert_setting(conn, "SESSION_COOKIE_HTTPONLY", "True")
        upsert_setting(conn, "SESSION_TIMEOUT_MINUTES", "30")
        upsert_setting(conn, "AUTO_LOGIN_DAYS", "7")

        # Performance settings
        upsert_setting(conn, "MAX_WORKERS", "4")
        upsert_setting(conn, "MAX_RAW_DATA_SIZE", str(100 * 1024 * 1024))  # 100MB
        upsert_setting(conn, "MAX_IMAGE_RETENTION_AGE", "7")  # days
        upsert_setting(conn, "MAX_VIDEO_RETENTION_AGE", "30")  # days

        # Capture settings
        upsert_setting(conn, "NUM_FRAMES", "3")
        upsert_setting(conn, "CAPTURE_TIMEOUT", "30")
        upsert_setting(conn, "LIVE_FALLBACK_FPS", "1")
        upsert_setting(conn, "DEFAULT_CLIP_DURATION", "60")

        # UI settings
        upsert_setting(conn, "CLOCK_NAVBAR", "True")
        upsert_setting(conn, "CLOCK_OVERLAY", "False")
        upsert_setting(conn, "HEALTH_STATUS_ALWAYS_VISIBLE", "False")

        # Browser settings
        upsert_setting(
            conn,
            "UA",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        )
        upsert_setting(conn, "LANG", "en-US")
        upsert_setting(conn, "TZ", "UTC")

        # Scheduler settings
        upsert_setting(conn, "SCHEDULER_API_ENABLED", "True")
        upsert_setting(conn, "DISCOVERY_AUTOSTART", "False")

        # Hardware acceleration
        upsert_setting(conn, "FFMPEG_HWACCEL", "auto")
        upsert_setting(conn, "FFMPEG_THREADS", "2")

        # Disable features that require additional setup
        upsert_setting(conn, "EMAIL_ENABLED", "False")
        upsert_setting(conn, "SMS_ENABLED", "False")
        upsert_setting(conn, "CAP_ENABLED", "False")
        upsert_setting(conn, "ALLOW_BOTS", "False")
        upsert_setting(conn, "AUTO_UPDATE_BRANCH", "None")

    console.print("✅ Default settings configured", style="bold green")


def create_example_templates(conn):
    """
    Insert a set of predefined example templates into the database to help users get started with common use cases.
    
    Creates templates for public webcams, news sites, IP cameras, YouTube livestreams, airport tracking, and weather forecasts. Only inserts templates that do not already exist. Displays the number of templates created.
    """
    with console.status("[bold blue]Creating example templates..."):
        # Example 1: Public webcam (snapshot only)
        template1 = {
            "name": "example_earth_cam",
            "url": "https://www.earthcam.com/cams/common/viewsnap.php?cam=abbey_road",
            "frequency": 5,  # 5 minutes
            "timeout": 15,
            "notes": "Example: Abbey Road crossing webcam (snapshot)",
            "groups": "examples,public_cams",
            "headless": True,
            "browser": False,
            "stealth": False,
            "livecaption": False,
            "motion": 0.1,
            "object_confidence": 0.7,
        }

        # Example 2: News website requiring browser
        template2 = {
            "name": "example_news_site",
            "url": "https://example.com",
            "frequency": 10,  # 10 minutes
            "timeout": 30,
            "notes": "Example: News website (requires browser)",
            "groups": "examples,news",
            "headless": True,
            "browser": True,
            "stealth": True,
            "livecaption": True,
            "motion": 0.2,
            "object_confidence": 0.5,
        }

        # Example 3: Local IP camera
        template3 = {
            "name": "example_ip_camera",
            "url": "http://192.168.1.100/snapshot.jpg",
            "frequency": 1,  # 1 minute
            "timeout": 10,
            "notes": "Example: Local IP camera (update URL to match your camera)",
            "groups": "examples,local_cameras",
            "headless": True,
            "browser": False,
            "stealth": False,
            "livecaption": False,
            "motion": 0.3,
            "object_confidence": 0.6,
            "auth_username": "",
            "auth_password": "",
        }

        # Example 4: YouTube livestream
        template4 = {
            "name": "example_youtube_stream",
            "url": "https://www.youtube.com/watch?v=RryMRpS3nh4",
            "frequency": 2,  # 2 minutes
            "timeout": 45,
            "notes": "Example: YouTube livestream (requires browser)",
            "groups": "examples,livestreams",
            "headless": True,
            "browser": True,
            "stealth": True,
            "livecaption": True,
            "motion": 0.2,
            "object_confidence": 0.5,
        }

        # Example 5: Another YouTube livestream
        template5 = {
            "name": "example_youtube_stream_2",
            "url": "https://www.youtube.com/watch?v=hb22ynjZPxk",
            "frequency": 3,  # 3 minutes
            "timeout": 45,
            "notes": "Example: Another YouTube livestream (requires browser)",
            "groups": "examples,livestreams",
            "headless": True,
            "browser": True,
            "stealth": True,
            "livecaption": True,
            "motion": 0.2,
            "object_confidence": 0.5,
        }

        # Example 6: FlightAware airport tracking
        template6 = {
            "name": "example_flightaware_ord",
            "url": "https://www.flightaware.com/live/airport/KORD",
            "frequency": 5,  # 5 minutes
            "timeout": 30,
            "notes": "Example: FlightAware ORD airport tracking (requires browser)",
            "groups": "examples,aviation,tracking",
            "headless": True,
            "browser": True,
            "stealth": True,
            "livecaption": True,
            "motion": 0.1,
            "object_confidence": 0.6,
        }

        # Example 7: Merrysky weather forecast
        template7 = {
            "name": "example_merrysky_chicago",
            "url": "https://merrysky.net/forecast/chicago/si",
            "frequency": 15,  # 15 minutes
            "timeout": 25,
            "notes": "Example: Merrysky Chicago weather forecast (requires browser)",
            "groups": "examples,weather,chicago",
            "headless": True,
            "browser": True,
            "stealth": True,
            "livecaption": True,
            "motion": 0.1,
            "object_confidence": 0.5,
        }

        templates = [
            template1,
            template2,
            template3,
            template4,
            template5,
            template6,
            template7,
        ]

        created_count = 0
        for template in templates:
            if insert_template(conn, template):
                created_count += 1

    console.print(f"✅ Created {created_count} example templates", style="bold green")


def create_directories():
    """
    Create all required directories for application data storage and logs if they do not already exist.
    """
    directories = [
        "data",
        "data/screenshots",
        "data/video",
        "data/clips",
        "data/summaries",
        "logs",
    ]

    with console.status("[bold cyan]Creating directories..."):
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    console.print("✅ Directory structure created", style="bold green")


def interactive_setup():
    """
    Launches an interactive setup wizard for the Glimpser application using a rich terminal interface.
    
    Guides the user through configuring the database path, admin credentials, API key, and optional example templates. Presents a summary for confirmation before proceeding. On confirmation, creates required directories, initializes the database schema, sets up default settings, creates the admin user, configures security keys, and optionally adds example templates. Handles user cancellation and setup errors gracefully.
    
    Returns:
        int: 0 if setup completes successfully, 1 if cancelled or an error occurs.
    """

    # Welcome screen
    console.print()
    welcome_panel = Panel.fit(
        Text.from_markup(
            "[bold cyan]🎬 Glimpser Initial Setup[/bold cyan]\n\n"
            "Welcome! This will set up your Glimpser application with:\n"
            "• Database tables and structure\n"
            "• Admin user account\n"
            "• Sensible default settings\n"
            "• Example templates to get started\n\n"
            "[dim]Press Ctrl+C at any time to cancel[/dim]"
        ),
        title="[bold green]Setup Wizard[/bold green]",
        border_style="green",
        box=box.ROUNDED,
    )
    console.print(welcome_panel)
    console.print()

    try:
        # Database path
        default_db = app.config.get_setting("DATABASE_PATH", "data/glimpser.db")
        database_path = Prompt.ask(
            "[bold]Database path[/bold]", default=default_db, show_default=True
        )

        # Admin user setup
        console.print("\n[bold blue]👤 Admin User Setup[/bold blue]")
        username = Prompt.ask("[bold]Admin username[/bold]", default="admin")

        # Check if user exists
        if os.path.exists(database_path):
            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM users WHERE username = ?", (username,)
                )
                user_exists = cursor.fetchone()[0] > 0
            except:
                user_exists = False
            conn.close()

            if user_exists:
                if not Confirm.ask(
                    f"[yellow]User '{username}' already exists. Overwrite?[/yellow]"
                ):
                    console.print("[red]Setup cancelled.[/red]")
                    return 1

        password = Prompt.ask("[bold]Admin password[/bold]", password=True)

        # API key
        console.print("\n[bold blue]🔑 API Configuration[/bold blue]")
        if Confirm.ask("Generate a random API key?", default=True):
            api_key = f"glimpser_{secrets.token_hex(8)}"
            console.print(f"Generated API key: [green]{api_key}[/green]")
        else:
            api_key = Prompt.ask("Enter custom API key")

        # Example templates
        console.print("\n[bold blue]📝 Example Templates[/bold blue]")
        create_templates = Confirm.ask(
            "Create example templates? (Recommended for first-time users)", default=True
        )

        # Confirm setup
        console.print("\n[bold yellow]📋 Setup Summary[/bold yellow]")
        summary_table = Table(show_header=False, box=box.SIMPLE)
        summary_table.add_column("Setting", style="bold")
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Database", database_path)
        summary_table.add_row("Username", username)
        summary_table.add_row("Password", "•" * len(password))
        summary_table.add_row("API Key", api_key)
        summary_table.add_row("Example Templates", "Yes" if create_templates else "No")

        console.print(summary_table)
        console.print()

        if not Confirm.ask("[bold]Proceed with setup?[/bold]", default=True):
            console.print("[red]Setup cancelled.[/red]")
            return 1

        # Perform setup
        console.print("\n[bold green]🚀 Setting up Glimpser...[/bold green]")

        # Create directories
        create_directories()

        # Connect to database
        conn = sqlite3.connect(database_path)

        try:
            # Create tables
            with console.status("[bold green]Creating database tables..."):
                create_tables(conn)
            console.print("✅ Database tables created", style="bold green")

            # Setup default settings
            setup_default_settings(conn)

            # Create admin user
            with console.status("[bold green]Creating admin user..."):
                password_hash = generate_password_hash(password)
                upsert_user(conn, username, password_hash, "admin")
                upsert_setting(conn, "USER_NAME", username)
                upsert_setting(conn, "USER_PASSWORD_HASH", password_hash)
            console.print(f"✅ Created admin user: {username}", style="bold green")

            # Setup keys
            with console.status("[bold green]Configuring security keys..."):
                secret_key = secrets.token_hex(32)
                upsert_setting(conn, "SECRET_KEY", secret_key)
                upsert_setting(conn, "API_KEY", api_key)
            console.print("✅ Security keys configured", style="bold green")

            # Create example templates
            if create_templates:
                create_example_templates(conn)

            # Success message
            console.print()
            success_panel = Panel.fit(
                Text.from_markup(
                    "[bold green]🎉 Setup completed successfully![/bold green]\n\n"
                    "[bold]Next steps:[/bold]\n"
                    f"1. Start Glimpser: [cyan]uv run main.py[/cyan]\n"
                    f"2. Open [cyan]http://localhost:8082[/cyan] in your browser\n"
                    f"3. Login with username: [green]{username}[/green]\n"
                    + (
                        "4. Review and customize the example templates\n"
                        "5. Update the IP camera URL to match your setup\n"
                        if create_templates
                        else ""
                    )
                    + "\n[dim]For more information, see the documentation.[/dim]"
                ),
                title="[bold green]✅ Success[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
            console.print(success_panel)

            return 0

        except Exception as e:
            console.print(f"[red]❌ Setup failed: {e}[/red]")
            logging.error("Setup error: %s", e)
            return 1
        finally:
            conn.close()

    except KeyboardInterrupt:
        console.print("\n[red]Setup cancelled by user.[/red]")
        return 1


def main():
    """
    Handles the initial setup process for the Glimpser application in both interactive and command-line modes.
    
    Parses command-line arguments to configure the database path, admin credentials, secret key, API key, and template creation options. If no arguments are provided, launches an interactive setup wizard. Otherwise, performs non-interactive setup by creating required directories, initializing the database schema, configuring default settings, creating or updating the admin user, setting security keys, and optionally adding example templates. Provides rich console feedback and returns an exit code indicating success or failure.
    
    Returns:
        int: 0 if setup completes successfully, 1 if an error occurs.
    """
    parser = argparse.ArgumentParser(description="Initial setup for Glimpser")
    parser.add_argument("--db-path", type=str, help="Path to SQLite database file")
    parser.add_argument("--username", type=str, help="Admin username")
    parser.add_argument("--password", type=str, help="Admin password")
    parser.add_argument("--secret-key", type=str, help="Flask secret key")
    parser.add_argument("--api-key", type=str, help="API key for external access")
    parser.add_argument(
        "--skip-templates", action="store_true", help="Skip creating example templates"
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing admin user"
    )

    args = parser.parse_args()

    # If no arguments provided, run interactive setup
    if (
        not args.db_path
        and not args.username
        and not args.password
        and not args.secret_key
        and not args.api_key
        and not args.skip_templates
        and not args.force
    ):
        return interactive_setup()

    # Non-interactive mode (existing logic but with rich output)
    database_path = args.db_path or app.config.get_setting(
        "DATABASE_PATH", "data/glimpser.db"
    )

    console.print(
        Panel.fit(
            f"[bold cyan]Glimpser Setup[/bold cyan]\n" f"Database: {database_path}",
            border_style="blue",
        )
    )

    create_directories()
    conn = sqlite3.connect(database_path)

    try:
        create_tables(conn)
        console.print("✅ Database tables created", style="bold green")

        setup_default_settings(conn)

        username = args.username or "admin"
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
        user_exists = cursor.fetchone()[0] > 0

        if user_exists and not args.force:
            console.print(
                f"[red]User '{username}' already exists. Use --force to overwrite.[/red]"
            )
            return 1

        password = args.password or secrets.token_hex(16)
        if not args.password:
            console.print(f"Generated password: [green]{password}[/green]")

        password_hash = generate_password_hash(password)
        upsert_user(conn, username, password_hash, "admin")
        upsert_setting(conn, "USER_NAME", username)
        upsert_setting(conn, "USER_PASSWORD_HASH", password_hash)

        console.print(f"✅ Created admin user: {username}", style="bold green")

        secret_key = args.secret_key or secrets.token_hex(32)
        upsert_setting(conn, "SECRET_KEY", secret_key)

        api_key = args.api_key or f"glimpser_{secrets.token_hex(8)}"
        upsert_setting(conn, "API_KEY", api_key)
        if not args.api_key:
            console.print(f"Generated API key: [green]{api_key}[/green]")

        if not args.skip_templates:
            create_example_templates(conn)

        console.print("\n[bold green]✅ Setup completed successfully![/bold green]")

    except Exception as e:
        console.print(f"[red]❌ Setup failed: {e}[/red]")
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
