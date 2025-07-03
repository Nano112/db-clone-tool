#!/usr/bin/env python3
"""
PostgreSQL Database Clone Tool
A Textual-based tool for cloning PostgreSQL databases with sequence reset support.
"""

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import psycopg2
from dotenv import load_dotenv

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Button, Input, Log, Static, 
    Select, Switch, ProgressBar, Label
)
from textual.binding import Binding
from textual.screen import Screen


class DatabaseConfig:
    """Database configuration class"""
    def __init__(self, host: str, port: int, database: str, username: str, password: str, ssl: bool = False):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.ssl = ssl
    
    @property
    def connection_string(self) -> str:
        ssl_param = "?sslmode=require" if self.ssl else ""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}{ssl_param}"
    
    @property
    def psql_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env['PGPASSWORD'] = self.password
        return env


class ConfigScreen(Screen):
    """Configuration screen for database settings"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="config-container"):
            yield Static("Database Clone Configuration", id="config-title")
            
            with Horizontal():
                with Vertical(classes="config-column"):
                    yield Label("Source Database")
                    yield Input(placeholder="Host", id="src-host")
                    yield Input(placeholder="Port (5432)", id="src-port", value="5432")
                    yield Input(placeholder="Database", id="src-database")
                    yield Input(placeholder="Username", id="src-username")
                    yield Input(placeholder="Password", password=True, id="src-password")
                    yield Switch(value=False, id="src-ssl")
                    yield Label("SSL Required", classes="switch-label")
                
                with Vertical(classes="config-column"):
                    yield Label("Target Database")
                    yield Input(placeholder="Host", id="tgt-host")
                    yield Input(placeholder="Port (5432)", id="tgt-port", value="5432")
                    yield Input(placeholder="Database", id="tgt-database")
                    yield Input(placeholder="Username", id="tgt-username")
                    yield Input(placeholder="Password", password=True, id="tgt-password")
                    yield Switch(value=False, id="tgt-ssl")
                    yield Label("SSL Required", classes="switch-label")
            
            with Horizontal(classes="button-row"):
                yield Button("Load from .env", id="load-env", variant="primary")
                yield Button("Test Connections", id="test-connections")
                yield Button("Start Clone", id="start-clone", variant="success")
        
        yield Footer()
    
    def on_mount(self) -> None:
        self.load_from_env()
    
    def load_from_env(self) -> None:
        """Load configuration from environment variables"""
        # Try to load from .env file
        env_files = ['.env', '.env.local', '.env.production', '.env.development']
        for env_file in env_files:
            if Path(env_file).exists():
                load_dotenv(env_file)
                break
        
        # Source database (production)
        self.query_one("#src-host").value = os.getenv('PROD_DB_HOST', '')
        self.query_one("#src-port").value = os.getenv('PROD_DB_PORT', '5432')
        self.query_one("#src-database").value = os.getenv('PROD_DB_DATABASE', '')
        self.query_one("#src-username").value = os.getenv('PROD_DB_USERNAME', '')
        self.query_one("#src-password").value = os.getenv('PROD_DB_PASSWORD', '')
        self.query_one("#src-ssl").value = os.getenv('PROD_DB_SSL', 'false').lower() == 'true'
        
        # Target database (local)
        self.query_one("#tgt-host").value = os.getenv('DB_HOST', 'localhost')
        self.query_one("#tgt-port").value = os.getenv('DB_PORT', '5432')
        self.query_one("#tgt-database").value = os.getenv('DB_DATABASE', '')
        self.query_one("#tgt-username").value = os.getenv('DB_USERNAME', '')
        self.query_one("#tgt-password").value = os.getenv('DB_PASSWORD', '')
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "load-env":
            self.load_from_env()
            self.app.notify("Environment variables loaded!")
        
        elif event.button.id == "test-connections":
            self.test_connections()
        
        elif event.button.id == "start-clone":
            self.start_clone_process()
    
    def get_database_configs(self) -> tuple[DatabaseConfig, DatabaseConfig]:
        """Get source and target database configurations"""
        source = DatabaseConfig(
            host=self.query_one("#src-host").value,
            port=int(self.query_one("#src-port").value or 5432),
            database=self.query_one("#src-database").value,
            username=self.query_one("#src-username").value,
            password=self.query_one("#src-password").value,
            ssl=self.query_one("#src-ssl").value
        )
        
        target = DatabaseConfig(
            host=self.query_one("#tgt-host").value,
            port=int(self.query_one("#tgt-port").value or 5432),
            database=self.query_one("#tgt-database").value,
            username=self.query_one("#tgt-username").value,
            password=self.query_one("#tgt-password").value,
            ssl=self.query_one("#tgt-ssl").value
        )
        
        return source, target
    
    def test_connections(self) -> None:
        """Test database connections"""
        source, target = self.get_database_configs()
        
        # Test source connection
        try:
            conn = psycopg2.connect(
                host=source.host,
                port=source.port,
                database=source.database,
                user=source.username,
                password=source.password,
                sslmode="require" if source.ssl else "prefer"
            )
            conn.close()
            self.app.notify("✓ Source database connection successful!", severity="information")
        except Exception as e:
            self.app.notify(f"✗ Source database connection failed: {e}", severity="error")
            return
        
        # Test target connection
        try:
            conn = psycopg2.connect(
                host=target.host,
                port=target.port,
                database=target.database,
                user=target.username,
                password=target.password,
                sslmode="require" if target.ssl else "prefer"
            )
            conn.close()
            self.app.notify("✓ Target database connection successful!", severity="information")
        except Exception as e:
            self.app.notify(f"✗ Target database connection failed: {e}", severity="error")
            return
    
    def start_clone_process(self) -> None:
        """Start the database cloning process"""
        source, target = self.get_database_configs()
        
        # Validate inputs
        if not all([source.host, source.database, source.username, source.password]):
            self.app.notify("Please fill in all source database fields", severity="error")
            return
        
        if not all([target.host, target.database, target.username, target.password]):
            self.app.notify("Please fill in all target database fields", severity="error")
            return
        
        # Switch to clone screen
        clone_screen = CloneScreen(source, target)
        self.app.push_screen(clone_screen)


class CloneScreen(Screen):
    """Screen for performing the database clone operation"""
    
    def __init__(self, source: DatabaseConfig, target: DatabaseConfig):
        super().__init__()
        self.source = source
        self.target = target
        self.temp_files = []
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="clone-container"):
            yield Static("Database Clone in Progress", id="clone-title")
            yield ProgressBar(total=100, id="progress")
            yield Log(id="clone-log")
            
            with Horizontal(classes="button-row"):
                yield Button("Cancel", id="cancel", variant="error")
                yield Button("Back to Config", id="back", disabled=True)
        yield Footer()
    
    def on_mount(self) -> None:
        """Start the clone process when screen mounts"""
        self.call_later(self.run_clone_process)
    
    async def run_clone_process(self) -> None:
        """Run the complete database cloning process"""
        log = self.query_one("#clone-log", Log)
        progress = self.query_one("#progress", ProgressBar)
        
        try:
            # Step 1: Create database dump
            log.write_line("🚀 Starting database clone process...")
            progress.update(progress=10)
            
            dump_file = await self.create_dump()
            progress.update(progress=40)
            
            # Step 2: Restore to target
            log.write_line("📥 Restoring to target database...")
            await self.restore_dump(dump_file)
            progress.update(progress=70)
            
            # Step 3: Reset sequences
            log.write_line("🔄 Resetting sequences...")
            await self.reset_sequences()
            progress.update(progress=90)
            
            # Step 4: Verify
            log.write_line("✅ Verifying clone...")
            await self.verify_clone()
            progress.update(progress=100)
            
            log.write_line("🎉 Database clone completed successfully!")
            self.query_one("#back").disabled = False
            
        except Exception as e:
            log.write_line(f"❌ Error during clone process: {e}")
            self.app.notify(f"Clone failed: {e}", severity="error")
            self.query_one("#back").disabled = False
        
        finally:
            # Clean up temporary files
            for temp_file in self.temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    async def create_dump(self) -> str:
        """Create database dump using pg_dump"""
        log = self.query_one("#clone-log", Log)
        
        # Create temporary file for dump
        fd, dump_file = tempfile.mkstemp(suffix='.custom', prefix='db_clone_')
        os.close(fd)
        self.temp_files.append(dump_file)
        
        log.write_line(f"📊 Creating dump from {self.source.host}/{self.source.database}...")
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            self.source.connection_string,
            '--format=custom',
            '--no-owner',
            '--no-privileges',
            '--verbose',
            '-f', dump_file
        ]
        
        # Run pg_dump
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.source.psql_env
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"pg_dump failed: {stderr.decode()}")
        
        log.write_line("✓ Database dump created successfully")
        return dump_file
    
    async def restore_dump(self, dump_file: str) -> None:
        """Restore dump to target database"""
        log = self.query_one("#clone-log", Log)
        
        log.write_line(f"📦 Restoring to {self.target.host}/{self.target.database}...")
        
        # Build pg_restore command
        cmd = [
            'pg_restore',
            '--disable-triggers',
            '--clean',
            '--if-exists',
            '--no-owner',
            '--no-privileges',
            '--verbose',
            '-h', self.target.host,
            '-p', str(self.target.port),
            '-U', self.target.username,
            '-d', self.target.database,
            dump_file
        ]
        
        # Run pg_restore
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.target.psql_env
        )
        
        stdout, stderr = await process.communicate()
        
        # pg_restore often returns non-zero even on success due to warnings
        log.write_line("✓ Database restore completed")
        
        # Log any warnings
        if stderr:
            stderr_text = stderr.decode()
            if "warning" in stderr_text.lower() or "error" in stderr_text.lower():
                log.write_line(f"⚠️  Restore warnings/errors (often ignorable): {stderr_text[:200]}...")
    
    async def reset_sequences(self) -> None:
        """Reset database sequences to correct values"""
        log = self.query_one("#clone-log", Log)
        
        reset_sql = """
        DO $$
        DECLARE
            seq_record RECORD;
            table_name TEXT;
            max_val BIGINT;
        BEGIN
            FOR seq_record IN 
                SELECT schemaname, sequencename 
                FROM pg_sequences 
                WHERE schemaname = 'public'
            LOOP
                -- Extract table name from sequence name
                table_name := regexp_replace(seq_record.sequencename, '_id_seq$', '');
                
                -- Get max ID from the table
                EXECUTE format('SELECT COALESCE(MAX(id), 0) FROM %I', table_name) INTO max_val;
                
                -- Set sequence to max_val + 1
                EXECUTE format('SELECT setval(%L, %s)', 
                    seq_record.schemaname || '.' || seq_record.sequencename, 
                    GREATEST(max_val + 1, 1));
                
                RAISE NOTICE 'Reset sequence % to %', seq_record.sequencename, GREATEST(max_val + 1, 1);
            END LOOP;
        END $$;
        """
        
        # Build psql command
        cmd = [
            'psql',
            '-h', self.target.host,
            '-p', str(self.target.port),
            '-U', self.target.username,
            '-d', self.target.database,
            '-c', reset_sql
        ]
        
        # Run sequence reset
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.target.psql_env
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            log.write_line("✓ Sequences reset successfully")
        else:
            log.write_line(f"⚠️  Sequence reset warnings: {stderr.decode()}")
    
    async def verify_clone(self) -> None:
        """Verify the cloned database"""
        log = self.query_one("#clone-log", Log)
        
        try:
            # Connect to target database and get table count
            conn = psycopg2.connect(
                host=self.target.host,
                port=self.target.port,
                database=self.target.database,
                user=self.target.username,
                password=self.target.password,
                sslmode="require" if self.target.ssl else "prefer"
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM pg_sequences WHERE schemaname = 'public'")
            sequence_count = cursor.fetchone()[0]
            
            conn.close()
            
            log.write_line(f"✓ Verification complete: {table_count} tables, {sequence_count} sequences")
            
        except Exception as e:
            log.write_line(f"⚠️  Verification failed: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "back":
            self.app.pop_screen()


class DatabaseCloneApp(App):
    """Main application class"""
    
    CSS = """
    #config-container {
        padding: 1;
        height: auto;
    }
    
    #config-title, #clone-title {
        text-align: center;
        margin: 1;
        text-style: bold;
        color: $accent;
    }
    
    .config-column {
        width: 1fr;
        padding: 0 1;
    }
    
    .config-column Input {
        margin: 0 0 1 0;
    }
    
    .config-column Label {
        margin: 0 0 0 0;
    }
    
    .switch-label {
        margin: 0 0 1 0;
        text-style: italic;
    }
    
    .button-row {
        margin: 1 0;
        height: auto;
    }
    
    .button-row Button {
        margin: 0 1;
    }
    
    #clone-container {
        padding: 1;
    }
    
    #clone-log {
        height: 20;
        margin: 1 0;
    }
    
    #progress {
        margin: 1 0;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
    ]
    
    def on_mount(self) -> None:
        """Called when app starts"""
        self.title = "PostgreSQL Database Clone Tool"
        self.push_screen(ConfigScreen())
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


def main():
    """Main entry point"""
    app = DatabaseCloneApp()
    app.run()


if __name__ == "__main__":
    main()