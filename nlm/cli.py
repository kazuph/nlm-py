import os
import sys
import click
from typing import List, Optional, Tuple
import json
from pathlib import Path

from .api.client import Client
from .auth import handle_auth, load_stored_env


class NotebookLMCLI:
    """Main CLI for NotebookLM."""
    def __init__(self):
        self.auth_token = os.environ.get("NLM_AUTH_TOKEN", "")
        self.cookies = os.environ.get("NLM_COOKIES", "")
        self.debug = False
        self.client = None
        
    def load_env(self):
        """Load environment variables."""
        # Try to load from stored env
        if not self.auth_token or not self.cookies:
            auth_token, cookies = load_stored_env()
            if auth_token:
                self.auth_token = auth_token
            if cookies:
                self.cookies = cookies
                
    def init_client(self):
        """Initialize API client."""
        if not self.client:
            if not self.auth_token or not self.cookies:
                print("Authentication required. Run 'nlm auth' first.")
                sys.exit(1)
                
            self.client = Client(self.auth_token, self.cookies, self.debug)
            
    def run_command(self, cmd: str, args: List[str]):
        """Run a NotebookLM command."""
        self.load_env()
        
        # Handle auth command separately
        if cmd == "auth":
            auth_token, cookies, err = handle_auth(args, self.debug)
            if err:
                print(f"Error: {err}")
                sys.exit(1)
            self.auth_token = auth_token
            self.cookies = cookies
            return
            
        # For other commands, initialize client
        self.init_client()
        
        # Dispatch to appropriate handler
        try:
            # Notebook operations
            if cmd in ["list", "ls"]:
                self.list_notebooks()
            elif cmd == "create":
                if len(args) != 1:
                    print("Usage: nlm create <title>")
                    sys.exit(1)
                self.create_notebook(args[0])
            elif cmd == "rm":
                if len(args) != 1:
                    print("Usage: nlm rm <id>")
                    sys.exit(1)
                self.remove_notebook(args[0])
                
            # Source operations
            elif cmd == "sources":
                if len(args) != 1:
                    print("Usage: nlm sources <notebook-id>")
                    sys.exit(1)
                self.list_sources(args[0])
            elif cmd == "add":
                if len(args) != 2:
                    print("Usage: nlm add <notebook-id> <file>")
                    sys.exit(1)
                source_id = self.add_source(args[0], args[1])
                print(source_id)
            elif cmd == "rm-source":
                if len(args) != 2:
                    print("Usage: nlm rm-source <notebook-id> <source-id>")
                    sys.exit(1)
                self.remove_source(args[0], args[1])
            elif cmd == "rename-source":
                if len(args) != 2:
                    print("Usage: nlm rename-source <source-id> <new-name>")
                    sys.exit(1)
                self.rename_source(args[0], args[1])
                
            # Note operations
            elif cmd == "new-note":
                if len(args) != 2:
                    print("Usage: nlm new-note <notebook-id> <title>")
                    sys.exit(1)
                self.create_note(args[0], args[1])
            elif cmd == "update-note":
                if len(args) != 4:
                    print("Usage: nlm update-note <notebook-id> <note-id> <content> <title>")
                    sys.exit(1)
                self.update_note(args[0], args[1], args[2], args[3])
            elif cmd == "rm-note":
                if len(args) != 1:
                    print("Usage: nlm rm-note <notebook-id> <note-id>")
                    sys.exit(1)
                self.remove_note(args[0], args[1])
                
            # Audio operations
            elif cmd == "audio-create":
                if len(args) != 2:
                    print("Usage: nlm audio-create <notebook-id> <instructions>")
                    sys.exit(1)
                self.create_audio_overview(args[0], args[1])
            elif cmd == "audio-get":
                if len(args) != 1:
                    print("Usage: nlm audio-get <notebook-id>")
                    sys.exit(1)
                self.get_audio_overview(args[0])
            elif cmd == "audio-rm":
                if len(args) != 1:
                    print("Usage: nlm audio-rm <notebook-id>")
                    sys.exit(1)
                self.delete_audio_overview(args[0])
            elif cmd == "audio-share":
                if len(args) != 1:
                    print("Usage: nlm audio-share <notebook-id>")
                    sys.exit(1)
                self.share_audio_overview(args[0])
                
            # Generation operations
            elif cmd == "generate-guide":
                if len(args) != 1:
                    print("Usage: nlm generate-guide <notebook-id>")
                    sys.exit(1)
                self.generate_notebook_guide(args[0])
            elif cmd == "generate-outline":
                if len(args) != 1:
                    print("Usage: nlm generate-outline <notebook-id>")
                    sys.exit(1)
                self.generate_outline(args[0])
            elif cmd == "generate-section":
                if len(args) != 1:
                    print("Usage: nlm generate-section <notebook-id>")
                    sys.exit(1)
                self.generate_section(args[0])
                
            # Other operations
            elif cmd == "hb":  # Heartbeat
                pass  # Do nothing
            else:
                self.print_usage()
                sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
            
    def print_usage(self):
        """Print CLI usage information."""
        print("Usage: nlm <command> [arguments]\n")
        print("Notebook Commands:")
        print("  list, ls          List all notebooks")
        print("  create <title>    Create a new notebook")
        print("  rm <id>           Delete a notebook")
        print("  analytics <id>    Show notebook analytics\n")
        
        print("Source Commands:")
        print("  sources <id>      List sources in notebook")
        print("  add <id> <input>  Add source to notebook")
        print("  rm-source <id> <source-id>  Remove source")
        print("  rename-source <source-id> <new-name>  Rename source")
        print("  refresh-source <source-id>  Refresh source content")
        print("  check-source <source-id>  Check source freshness\n")
        
        print("Note Commands:")
        print("  notes <id>        List notes in notebook")
        print("  new-note <id> <title>  Create new note")
        print("  edit-note <id> <note-id> <content>  Edit note")
        print("  rm-note <note-id>  Remove note\n")
        
        print("Audio Commands:")
        print("  audio-create <id> <instructions>  Create audio overview")
        print("  audio-get <id>    Get audio overview")
        print("  audio-rm <id>     Delete audio overview")
        print("  audio-share <id>  Share audio overview\n")
        
        print("Generation Commands:")
        print("  generate-guide <id>  Generate notebook guide")
        print("  generate-outline <id>  Generate content outline")
        print("  generate-section <id>  Generate new section\n")
        
        print("Other Commands:")
        print("  auth              Setup authentication")
        
    # Notebook operations
    def list_notebooks(self):
        """List all notebooks."""
        notebooks = self.client.list_recently_viewed_projects()
        
        # Print header
        print("ID\tTITLE\tLAST UPDATED")
        
        # Print notebooks in same format as Go implementation
        for nb in notebooks:
            # Handle last updated time - use create_time as in Go code
            last_updated = ""
            if nb.metadata and nb.metadata.create_time:
                last_updated = nb.metadata.create_time.isoformat()
                
            # Format title with emoji
            title = f"{nb.emoji} {nb.title}" if nb.emoji else nb.title
            
            # Print the notebook line
            print(f"{nb.project_id}\t{title}\t{last_updated}")
            
    def create_notebook(self, title: str):
        """Create a new notebook."""
        notebook = self.client.create_project(title, "📙")
        print(notebook.project_id)
        
    def remove_notebook(self, notebook_id: str):
        """Delete a notebook."""
        print(f"Are you sure you want to delete notebook {notebook_id}? [y/N] ", end="")
        response = input().lower()
        
        if not response.startswith("y"):
            print("Operation cancelled")
            sys.exit(1)
            
        self.client.delete_projects([notebook_id])
        
    # Source operations
    def list_sources(self, notebook_id: str):
        """List sources in a notebook."""
        project = self.client.get_project(notebook_id)
        
        # Print header
        print("ID\tTITLE\tTYPE\tSTATUS\tLAST UPDATED")
        
        # Print each source in the notebook
        for src in project.sources:
            # Handle source status
            status = "ENABLED"
            if src.settings:
                status = src.settings.status.name.replace("SOURCE_STATUS_", "")
                
            # Handle last updated time
            last_updated = "unknown"
            if src.metadata and src.metadata.last_modified_time:
                last_updated = src.metadata.last_modified_time.isoformat()
                
            # Handle source type
            source_type = "UNKNOWN"
            if src.metadata:
                source_type = src.metadata.source_type.name.replace("SOURCE_TYPE_", "")
                
            # Print the source line
            print(f"{src.source_id.source_id}\t{src.title}\t{source_type}\t{status}\t{last_updated}")
            
    def add_source(self, notebook_id: str, input_path: str) -> str:
        """Add a source to a notebook."""
        # Handle special input designators
        if input_path == "-":  # stdin
            print("Reading from stdin...")
            return self.client.add_source_from_reader(notebook_id, sys.stdin.buffer, "Pasted Text")
        if not input_path:  # empty input
            raise ValueError("Input required (file, URL, or '-' for stdin)")
            
        # Check if input is a URL
        if input_path.startswith("http://") or input_path.startswith("https://"):
            print(f"Adding source from URL: {input_path}")
            return self.client.add_source_from_url(notebook_id, input_path)
            
        # Try as local file
        if os.path.exists(input_path):
            print(f"Adding source from file: {input_path}")
            return self.client.add_source_from_file(notebook_id, input_path)
            
        # If it's not a URL or file, treat as direct text content
        print("Adding text content as source...")
        return self.client.add_source_from_text(notebook_id, input_path, "Text Source")
        
    def remove_source(self, notebook_id: str, source_id: str):
        """Remove a source from a notebook."""
        print(f"Are you sure you want to remove source {source_id}? [y/N] ", end="")
        response = input().lower()
        
        if not response.startswith("y"):
            print("Operation cancelled")
            sys.exit(1)
            
        self.client.delete_sources(notebook_id, [source_id])
        print(f"✅ Removed source {source_id} from notebook {notebook_id}")
        
    def rename_source(self, source_id: str, new_name: str):
        """Rename a source."""
        print(f"Renaming source {source_id} to: {new_name}")
        
        self.client.mutate_source(source_id, {"title": new_name})
        print(f"✅ Renamed source to: {new_name}")
        
    # Note operations
    def create_note(self, notebook_id: str, title: str):
        """Create a new note."""
        print(f"Creating note in notebook {notebook_id}...")
        
        note = self.client.create_note(notebook_id, title, "")
        print(f"✅ Created note: {title}")
        
    def update_note(self, notebook_id: str, note_id: str, content: str, title: str):
        """Update a note."""
        print(f"Updating note {note_id}...")
        
        note = self.client.mutate_note(notebook_id, note_id, content, title)
        print(f"✅ Updated note: {title}")
        
    def remove_note(self, notebook_id: str, note_id: str):
        """Remove a note."""
        print(f"Are you sure you want to remove note {note_id}? [y/N] ", end="")
        response = input().lower()
        
        if not response.startswith("y"):
            print("Operation cancelled")
            sys.exit(1)
            
        self.client.delete_notes(notebook_id, [note_id])
        print(f"✅ Removed note: {note_id}")
        
    # Audio operations
    def create_audio_overview(self, project_id: str, instructions: str):
        """Create an audio overview."""
        print(f"Creating audio overview for notebook {project_id}...")
        print(f"Instructions: {instructions}")
        
        result = self.client.create_audio_overview(project_id, instructions)
        
        if not result.is_ready:
            print("✅ Audio overview creation started. Use 'nlm audio-get' to check status.")
            return
            
        # If the result is immediately ready (unlikely but possible)
        print("✅ Audio Overview created:")
        print(f"  Title: {result.title}")
        print(f"  ID: {result.audio_id}")
        
        # Save audio file if available
        if result.audio_data:
            try:
                audio_data = result.get_audio_bytes()
                filename = f"audio_overview_{result.audio_id}.wav"
                
                with open(filename, "wb") as f:
                    f.write(audio_data)
                    
                print(f"  Saved audio to: {filename}")
            except Exception as e:
                print(f"Error saving audio file: {e}")
                
    def get_audio_overview(self, project_id: str):
        """Get an audio overview."""
        print("Fetching audio overview...")
        
        result = self.client.get_audio_overview(project_id)
        
        if not result.is_ready:
            print("Audio overview is not ready yet. Try again in a few moments.")
            return
            
        print("Audio Overview:")
        print(f"  Title: {result.title}")
        print(f"  ID: {result.audio_id}")
        print(f"  Ready: {result.is_ready}")
        
        # Optionally save the audio file
        if result.audio_data:
            try:
                audio_data = result.get_audio_bytes()
                filename = f"audio_overview_{result.audio_id}.wav"
                
                with open(filename, "wb") as f:
                    f.write(audio_data)
                    
                print(f"  Saved audio to: {filename}")
            except Exception as e:
                print(f"Error saving audio file: {e}")
                
    def delete_audio_overview(self, project_id: str):
        """Delete an audio overview."""
        print("Are you sure you want to delete the audio overview? [y/N] ", end="")
        response = input().lower()
        
        if not response.startswith("y"):
            print("Operation cancelled")
            sys.exit(1)
            
        self.client.delete_audio_overview(project_id)
        print("✅ Deleted audio overview")
        
    def share_audio_overview(self, project_id: str):
        """Share an audio overview."""
        print("Generating share link...")
        
        resp = self.client.share_audio(project_id, self.client.ShareOption.PUBLIC)
        print(f"Share URL: {resp.share_url}")
        
    # Generation operations
    def generate_notebook_guide(self, project_id: str):
        """Generate a notebook guide."""
        print("Generating notebook guide...")
        
        guide = self.client.generate_notebook_guide(project_id)
        print(f"Guide:\n{guide.content}")
        
    def generate_outline(self, project_id: str):
        """Generate a content outline."""
        print("Generating outline...")
        
        outline = self.client.generate_outline(project_id)
        print(f"Outline:\n{outline.content}")
        
    def generate_section(self, project_id: str):
        """Generate a new section."""
        print("Generating section...")
        
        section = self.client.generate_section(project_id)
        print(f"Section:\n{section.content}")


@click.command(add_help_option=False, context_settings=dict(ignore_unknown_options=True))
@click.option('--debug', is_flag=True, help='Enable debug output')
@click.option('--auth', help='Auth token')
@click.option('--cookies', help='Cookies for authentication')
@click.argument('args', nargs=-1)
def cli(debug, auth, cookies, args):
    """NotebookLM CLI."""
    nlm = NotebookLMCLI()
    
    # Set options
    if debug:
        nlm.debug = True
    if auth:
        nlm.auth_token = auth
    if cookies:
        nlm.cookies = cookies
        
    # Parse command and arguments
    if not args:
        nlm.print_usage()
        sys.exit(1)
        
    cmd = args[0]
    cmd_args = list(args[1:])
    
    nlm.run_command(cmd, cmd_args)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
