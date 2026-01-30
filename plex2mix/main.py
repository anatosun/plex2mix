#!/usr/bin/env python3
import sys
import time
import yaml
import click
import logging
from pathlib import Path
from concurrent.futures import as_completed
from typing import Dict, Any, List

from plexapi.myplex import MyPlexPinLogin, MyPlexAccount
from plexapi.server import PlexServer
from plex2mix import __version__
from plex2mix.downloader import Downloader
from plex2mix.exporter import get_exporter_by_name
from plex2mix.converter import AudioConverter

# Set up logging
logger = logging.getLogger(__name__)

CONFIG_DIR = Path(click.get_app_dir("plex2mix"))
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    if verbose:
        level = logging.DEBUG
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        logger.info(f"Verbose logging enabled at level {logging.getLevelName(level)}")
    else:
        # Disable all logging by setting root logger level very high
        logging.getLogger().setLevel(logging.CRITICAL + 1)
        # Also disable logging for all plex2mix modules
        logging.getLogger('plex2mix').setLevel(logging.CRITICAL + 1)
        logging.getLogger('__main__').setLevel(logging.CRITICAL + 1)


def show_banner():
    """Display the plex2mix ASCII art banner."""
    banner = """
    ██████╗ ██╗     ███████╗██╗  ██╗██████╗ ███╗   ███╗██╗██╗  ██╗
    ██╔══██╗██║     ██╔════╝╚██╗██╔╝╚════██╗████╗ ████║██║╚██╗██╔╝
    ██████╔╝██║     █████╗   ╚███╔╝  █████╔╝██╔████╔██║██║ ╚███╔╝ 
    ██╔═══╝ ██║     ██╔══╝   ██╔██╗ ██╔═══╝ ██║╚██╔╝██║██║ ██╔██╗ 
    ██║     ███████╗███████╗██╔╝ ██╗███████╗██║ ╚═╝ ██║██║██╔╝ ██╗
    ╚═╝     ╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═╝
    
    🎵 Plex Music Downloader for DJs 🎧
    """
    click.echo(click.style(banner, fg='cyan', bold=True))
    click.echo(click.style("    Convert your Plex playlists to DJ-ready formats", fg='yellow'))
    click.echo()  # Empty line for spacing


def load_config() -> Dict[str, Any]:
    logger.debug(f"Loading configuration from {CONFIG_FILE}")
    
    if not CONFIG_DIR.exists():
        logger.info(f"Creating config directory: {CONFIG_DIR}")
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        logger.info(f"Creating new config file: {CONFIG_FILE}")
        CONFIG_FILE.write_text(yaml.dump({}))

    with CONFIG_FILE.open("r") as f:
        config = yaml.safe_load(f) or {}

    logger.debug(f"Loaded configuration with {len(config)} keys")
    return config


def save_config(config: Dict[str, Any]) -> None:
    logger.debug(f"Saving configuration to {CONFIG_FILE}")
    with CONFIG_FILE.open("w") as f:
        yaml.dump(config, f)
    logger.debug("Configuration saved successfully")


def login(token: str = "") -> PlexServer:
    """Authenticate with Plex and return a connected PlexServer."""
    logger.info("Starting Plex authentication")
    
    if not token:
        logger.info("No token provided, starting PIN authentication")
        login_session = MyPlexPinLogin()
        login_session.run()
        click.echo(f"Visit https://plex.tv/link and enter the code: {login_session.pin}")
        click.echo("Waiting for authorization...")
        logger.debug(f"Generated PIN: {login_session.pin}")

        login_session.waitForLogin()
        token = str(login_session.token)
        logger.info("PIN authentication successful")

    try:
        account = MyPlexAccount(token=token)
        logger.info(f"Authenticated as user: {account.username}")
        click.echo(f"Logged in as {account.username}")
        
        resources = [r for r in account.resources() if r.provides == "server"]
        logger.debug(f"Found {len(resources)} Plex servers")

        if not resources:
            logger.error("No Plex servers found for this account")
            click.echo("No server found", err=True)
            sys.exit(1)

        if len(resources) > 1:
            logger.info("Multiple servers found, prompting user selection")
            for i, resource in enumerate(resources):
                click.echo(f"{i}: {resource.name} ({resource.clientIdentifier})")
            index = click.prompt("Select your server", default=0, type=int)
        else:
            index = 0
            logger.debug(f"Using single available server: {resources[0].name}")

        server: PlexServer = resources[index].connect()
        logger.info(f"Connected to Plex server: {server.friendlyName}")
        click.echo(f"Connected to {server.friendlyName}")
        return server
        
    except Exception as e:
        logger.error(f"Failed to authenticate with Plex: {e}")
        click.echo(f"Could not connect to server: {e}", err=True)
        sys.exit(1)


def interactive_mode(ctx):
    """Interactive mode for plex2mix."""
    click.echo(click.style("🎛️  Welcome to plex2mix Interactive Mode!", fg='green', bold=True))
    click.echo("Type 'help' for available commands or 'quit' to exit.\n")
    
    while True:
        try:
            # Show prompt
            command = click.prompt(click.style("plex2mix", fg='cyan', bold=True) + click.style(" > ", fg='white'), 
                                 default="", show_default=False).strip()
            
            if not command:
                continue
                
            # Handle built-in interactive commands
            if command.lower() in ['quit', 'exit', 'q']:
                click.echo(click.style("👋 Goodbye!", fg='yellow'))
                break
                
            elif command.lower() in ['help', 'h', '?']:
                show_interactive_help()
                continue
                
            elif command.lower() in ['clear', 'cls']:
                click.clear()
                show_banner()
                continue
            
            # Parse and execute plex2mix commands
            try:
                # Split command into parts
                parts = command.split()
                cmd = parts[0].lower()
                args = parts[1:]
                
                logger.debug(f"Interactive mode executing: {cmd} with args: {args}")
                
                if cmd == 'list' or cmd == 'ls':
                    ctx.invoke(list)
                    
                elif cmd == 'download' or cmd == 'dl':
                    # Parse download arguments
                    indices = []
                    download_all = False
                    overwrite = False
                    
                    i = 0
                    while i < len(args):
                        if args[i] in ['-a', '--all']:
                            download_all = True
                        elif args[i] in ['-o', '--overwrite']:
                            overwrite = True
                        elif args[i].isdigit():
                            indices.append(int(args[i]))
                        i += 1
                    
                    # If no indices and not --all, prompt for selection
                    if not indices and not download_all:
                        playlists = ctx.obj["downloaders"][0].get_playlists()
                        if playlists:
                            # Show playlists first
                            ctx.invoke(list)
                            click.echo()
                            try:
                                idx = click.prompt("Enter playlist number to download", type=int)
                                indices = [idx]
                            except click.Abort:
                                continue
                        else:
                            click.echo("No playlists available")
                            continue
                    
                    # Execute download
                    if download_all:
                        playlists = ctx.obj["downloaders"][0].get_playlists()
                        indices = list(range(len(playlists)))
                    
                    if indices:
                        download_playlists(ctx, indices, overwrite)
                    
                elif cmd == 'refresh':
                    force = '-f' in args or '--force' in args
                    ctx.invoke(refresh, force=force)
                    
                elif cmd == 'ignore':
                    # Parse ignore arguments
                    indices = [int(arg) for arg in args if arg.isdigit()]
                    
                    if not indices:
                        playlists = ctx.obj["downloaders"][0].get_playlists()
                        if playlists:
                            ctx.invoke(list)
                            click.echo()
                            try:
                                idx = click.prompt("Enter playlist number to ignore", type=int)
                                indices = [idx]
                            except click.Abort:
                                continue
                        else:
                            click.echo("No playlists available")
                            continue
                    
                    # Execute ignore
                    ctx.invoke(ignore, indices=indices)
                    
                elif cmd == 'config':
                    ctx.invoke(config)
                    
                elif cmd == 'reset':
                    ctx.invoke(reset)
                    
                elif cmd == 'status':
                    show_status(ctx)
                    
                else:
                    click.echo(f"Unknown command: {cmd}")
                    click.echo("Type 'help' for available commands.")
                    
            except (ValueError, IndexError) as e:
                click.echo(f"Invalid command format: {e}")
                click.echo("Type 'help' for command syntax.")
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
                click.echo(f"Error: {e}")
                
        except KeyboardInterrupt:
            click.echo(click.style("\n👋 Goodbye!", fg='yellow'))
            break
        except EOFError:
            click.echo(click.style("\n👋 Goodbye!", fg='yellow'))
            break


def show_interactive_help():
    """Show help for interactive mode."""
    help_text = """
🎵 plex2mix Interactive Mode Commands:

📋 Playlist Management:
  list, ls                    - List all playlists
  download [indices] [-a] [-o] - Download playlists (indices: 0 1 2, -a: all, -o: overwrite)
  refresh [-f]                - Refresh saved playlists (-f: force overwrite)
  ignore [indices]            - Ignore playlists
  status                      - Show current status

⚙️  Configuration:
  config                      - Show current configuration
  reset                       - Reset configuration

🎛️  Interactive:
  help, h, ?                  - Show this help
  clear, cls                  - Clear screen
  quit, exit, q               - Exit interactive mode

💡 Examples:
  download 0 1 2              - Download playlists 0, 1, and 2
  download -a -o              - Download all playlists with overwrite
  ignore 3                    - Ignore playlist 3
  refresh -f                  - Force refresh all saved playlists

🎵 Note: Downloaded files will be automatically converted to MP3 if conversion is enabled in config (preserves metadata and album artwork).
"""
    click.echo(click.style(help_text, fg='cyan'))


def show_status(ctx):
    """Show current plex2mix status."""
    config = ctx.obj["config"]
    try:
        playlists = ctx.obj["downloaders"][0].get_playlists()
        saved = config["playlists"]["saved"]
        ignored = config["playlists"]["ignored"]
        
        click.echo(click.style("📊 plex2mix Status", fg='cyan', bold=True))
        click.echo(f"🎵 Total playlists: {len(playlists)}")
        click.echo(f"💾 Saved playlists: {len(saved)}")
        click.echo(f"🚫 Ignored playlists: {len(ignored)}")
        click.echo(f"📁 Download path: {config['path']}")
        click.echo(f"🎼 Playlist path: {config['playlists_path']}")
        click.echo(f"📤 Export formats: {', '.join(config['export_formats'])}")
        click.echo(f"🧵 Download threads: {config['threads']}")
        click.echo(f"🖥️  Server: {config['server']['name']}")
        
        # Show MP3 conversion status
        if config.get("convert_to_mp3"):
            quality = config.get("mp3_quality", "320k")
            storage_mode = config.get("mp3_storage_mode", "replace")
            click.echo(f"🎵 MP3 conversion: Enabled ({quality}, {storage_mode})")
        else:
            click.echo(f"🎵 MP3 conversion: Disabled")
        
    except Exception as e:
        click.echo(f"Error getting status: {e}")


def download_playlists(ctx, indices: List[int], overwrite: bool = False):
    """Download playlists by indices."""
    logger.info(f"Starting download for {len(indices)} playlists (overwrite={overwrite})")
    
    try:
        playlists = ctx.obj["downloaders"][0].get_playlists()
        saved, ignored = ctx.obj["config"]["playlists"]["saved"], ctx.obj["config"]["playlists"]["ignored"]

        for i in indices:
            if i >= len(playlists):
                logger.error(f"Invalid playlist index: {i} (max: {len(playlists)-1})")
                click.echo(f"Invalid playlist index: {i}", err=True)
                continue
                
            playlist = playlists[i]
            
            if playlist.ratingKey in ignored:
                logger.info(f"Skipping ignored playlist: {playlist.title}")
                click.echo(f"Skipping ignored playlist: {playlist.title}")
                continue

            logger.info(f"Processing playlist: {playlist.title}")
            click.echo(f"Processing playlist: {playlist.title}")
            
            for downloader in ctx.obj["downloaders"]:
                try:
                    logger.debug(f"Starting download with {type(downloader.exporter).__name__}")
                    tasks = downloader.download(playlist, overwrite=overwrite)
                    
                    if tasks:
                        logger.info(f"Processing {len(tasks)} download tasks")
                        with click.progressbar(
                            as_completed(tasks), 
                            length=len(tasks), 
                            label=f"{playlist.title} ({downloader.exporter.name})"
                        ) as bar:
                            for _ in bar:
                                pass
                    else:
                        logger.warning(f"No tracks to download for {playlist.title}")
                        click.echo(f"No tracks to download for {playlist.title}")
                        
                except Exception as e:
                    logger.error(f"Error downloading {playlist.title} with {downloader.exporter.name}: {e}")
                    click.echo(f"Error downloading {playlist.title} with {downloader.exporter.name}: {e}", err=True)

            # Update playlist status
            if playlist.ratingKey not in saved:
                saved.append(playlist.ratingKey)
                logger.debug(f"Added playlist {playlist.title} to saved list")
            if playlist.ratingKey in ignored:
                ignored.remove(playlist.ratingKey)
                logger.debug(f"Removed playlist {playlist.title} from ignored list")

            ctx.obj["save"]()
            logger.info(f"Completed processing playlist: {playlist.title}")
            click.echo(f"Completed: {playlist.title}")

    except Exception as e:
        logger.error(f"Error during download process: {e}")
        click.echo(f"Error during download: {e}", err=True)


@click.group(invoke_without_command=True)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.version_option(version=__version__, prog_name="plex2mix")
@click.pass_context
def cli(ctx, verbose: bool) -> None:
    """plex2mix CLI"""
    show_banner()
    setup_logging(verbose)
    ctx.ensure_object(dict)
    
    logger.info("Starting plex2mix CLI")
    config = load_config()

    # Handle authentication
    if not config.get("token"):
        logger.info("No authentication token found, starting login process")
        server = login()
        config["token"] = server._token
        config["server"] = {"url": server._baseurl, "name": server.friendlyName}
        save_config(config)
        logger.info("Authentication completed and saved")
    else:
        logger.debug("Using existing authentication token")
        try:
            server = PlexServer(config["server"]["url"], config["token"])
            logger.info(f"Successfully connected to server: {config['server']['name']}")
        except Exception as e:
            logger.warning(f"Failed to connect with existing token: {e}")
            click.echo(f"Could not connect to server: {e}", err=True)
            click.echo(f"Clearing invalid token. Please run the command again to re-authenticate.")
            config.pop("token", None)
            config.pop("server", None)
            save_config(config)
            logger.info("Invalid token cleared, user needs to re-authenticate")
            sys.exit(1)

    # Setup paths
    if "path" not in config:
        logger.info("Download path not configured, prompting user")
        path = Path(click.prompt("Enter path to download to", default="~/Music")).expanduser() / "plex2mix"
        config["path"] = str(path)
        save_config(config)
        logger.info(f"Download path set to: {path}")

    if "threads" not in config:
        logger.info("Thread count not configured, prompting user")
        config["threads"] = click.prompt("Enter number of download threads", default=4, type=int)
        save_config(config)
        logger.info(f"Thread count set to: {config['threads']}")

    # Initialize playlist tracking
    playlists_config = config.get("playlists")
    if not playlists_config or not hasattr(playlists_config, 'get'):
        logger.info("Initializing playlist tracking configuration")
        config["playlists"] = {"saved": [], "ignored": []}
        save_config(config)

    # Setup export formats
    export_formats = config.get("export_formats")
    if not export_formats or not hasattr(export_formats, '__iter__') or type(export_formats) is str:
        logger.info("Export formats not configured, prompting user")
        formats = click.prompt("Select export formats (comma-separated, e.g., m3u8,itunes)", default="m3u8")
        config["export_formats"] = [f.strip() for f in formats.split(",") if f.strip()]
        save_config(config)
        logger.info(f"Export formats set to: {config['export_formats']}")

    # Setup MP3 conversion
    convert_to_mp3 = config.get("convert_to_mp3")
    if convert_to_mp3 is None:
        logger.info("MP3 conversion not configured, prompting user")
        convert = click.confirm("Convert downloaded files to MP3 format?", default=False)
        config["convert_to_mp3"] = convert
        if convert:
            quality = click.prompt("MP3 quality (bitrate, e.g., 320k, 256k, 192k)", default="320k")
            config["mp3_quality"] = quality
            
            # Ask about storage mode
            click.echo("Choose how to handle original files:")
            click.echo("  replace: Replace original files with MP3 (saves space)")
            click.echo("  separate: Keep originals and put MP3s in 'converted' folder")
            click.echo("  keep_both: Keep both original and MP3 in same folder")
            storage_mode = click.prompt("Storage mode", default="replace", 
                                      type=click.Choice(["replace", "separate", "keep_both"]))
            config["mp3_storage_mode"] = storage_mode
        save_config(config)
        logger.info(f"MP3 conversion set to: {config['convert_to_mp3']}")
        if config.get("convert_to_mp3"):
            logger.info(f"MP3 quality set to: {config['mp3_quality']}")
            logger.info(f"MP3 storage mode set to: {config['mp3_storage_mode']}")

    # Create directories
    path = Path(config["path"]).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured download directory exists: {path}")

    if not config.get("playlists_path"):
        playlists_path = path / "playlists"
        config["playlists_path"] = str(playlists_path)
        save_config(config)
        logger.info(f"Playlists path set to: {playlists_path}")

    Path(config["playlists_path"]).mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured playlists directory exists: {config['playlists_path']}")

    # Create converter if MP3 conversion is enabled
    converter = None
    if config.get("convert_to_mp3"):
        try:
            quality = config.get("mp3_quality", "320k")
            storage_mode = config.get("mp3_storage_mode", "replace")
            converter = AudioConverter(quality=quality, storage_mode=storage_mode)
            logger.info(f"Created MP3 converter with quality: {quality}, storage: {storage_mode}")
        except RuntimeError as e:
            logger.error(f"Failed to create MP3 converter: {e}")
            click.echo(f"Warning: {e}", err=True)
            config["convert_to_mp3"] = False
            save_config(config)

    # Create downloaders for each export format
    downloaders = []
    logger.info(f"Creating downloaders for {len(config['export_formats'])} export formats")
    
    for fmt in config["export_formats"]:
        try:
            exporter = get_exporter_by_name(fmt)
            downloader = Downloader(
                server,
                config["path"],
                config["playlists_path"],
                config["threads"],
                exporter=exporter,
                converter=converter
            )
            downloaders.append(downloader)
            logger.debug(f"Created downloader for format: {fmt}")
        except ValueError as e:
            logger.error(f"Failed to create exporter for format '{fmt}': {e}")
            click.echo(f"Warning: {e}", err=True)

    if not downloaders:
        logger.error("No valid downloaders created")
        click.echo("No valid export formats configured", err=True)
        sys.exit(1)

    logger.info(f"Successfully created {len(downloaders)} downloaders")
    ctx.obj["config"] = config
    ctx.obj["server"] = server
    ctx.obj["save"] = lambda: save_config(config)
    ctx.obj["downloaders"] = downloaders
    
    # If no command was invoked, start interactive mode
    if ctx.invoked_subcommand is None:
        logger.info("No command specified, starting interactive mode")
        interactive_mode(ctx)


@cli.command()
@click.pass_context
def list(ctx) -> None:
    """List playlists"""
    logger.info("Listing playlists")
    
    try:
        playlists = ctx.obj["downloaders"][0].get_playlists()
        saved, ignored = ctx.obj["config"]["playlists"]["saved"], ctx.obj["config"]["playlists"]["ignored"]

        if not playlists:
            logger.warning("No playlists found on the server")
            click.echo("No playlists found on the server.")
            return

        logger.info(f"Displaying {len(playlists)} playlists")
        for i, playlist in enumerate(playlists):
            if playlist.ratingKey in saved:
                color = "green"
                status = " (saved)"
            elif playlist.ratingKey in ignored:
                color = "red"
                status = " (ignored)"
            else:
                color = "white"
                status = ""
            click.echo(click.style(f"{i}: {playlist.title}{status}", fg=color))
            
    except Exception as e:
        logger.error(f"Error listing playlists: {e}")
        click.echo(f"Error listing playlists: {e}", err=True)


@cli.command()
@click.argument("indices", nargs=-1, type=int)
@click.option("-a", "--all", "download_all", is_flag=True, help="Download all playlists")
@click.option("-o", "--overwrite", is_flag=True, help="Overwrite existing files")
@click.pass_context
def download(ctx, indices: List[int], download_all: bool, overwrite: bool) -> None:
    """Download playlists"""
    logger.info(f"Download command called (all={download_all}, overwrite={overwrite}, indices={indices})")
    
    playlists = ctx.obj["downloaders"][0].get_playlists()
    
    if download_all:
        logger.info("Downloading all playlists")
        indices = list(range(len(playlists)))
    elif not indices:
        if not playlists:
            logger.warning("No playlists available for download")
            click.echo("No playlists available")
            return
            
        logger.info("No indices provided, prompting user for selection")
        max_index = len(playlists) - 1
        i = -1
        while i < 0 or i > max_index:
            try:
                i = click.prompt(f"Select playlist to download [0-{max_index}]", default=0, type=int)
            except click.Abort:
                logger.info("User aborted playlist selection")
                return
        indices = [i]

    logger.info(f"Starting download for indices: {indices}")
    download_playlists(ctx, indices, overwrite=overwrite)


@cli.command()
@click.option("-f", "--force", is_flag=True, help="Force refresh (overwrite existing files)")
@click.pass_context
def refresh(ctx, force: bool) -> None:
    """Refresh saved playlists"""
    logger.info(f"Refresh command called (force={force})")
    
    try:
        playlists = ctx.obj["downloaders"][0].get_playlists()
        saved = ctx.obj["config"]["playlists"]["saved"]

        if not saved:
            logger.warning("No saved playlists to refresh")
            click.echo("No saved playlists to refresh")
            return

        # Find indices of saved playlists
        indices = []
        for i, p in enumerate(playlists):
            if p.ratingKey in saved:
                indices.append(i)

        if not indices:
            logger.warning("No saved playlists found on server")
            click.echo("No saved playlists found on server")
            return

        logger.info(f"Refreshing {len(indices)} saved playlists")
        click.echo(f"Refreshing {len(indices)} saved playlists...")
        download_playlists(ctx, indices, overwrite=force)
        
    except Exception as e:
        logger.error(f"Error during refresh: {e}")
        click.echo(f"Error during refresh: {e}", err=True)


@cli.command()
@click.argument("indices", nargs=-1, type=int)
@click.pass_context
def ignore(ctx, indices: List[int]) -> None:
    """Ignore playlists"""
    logger.info(f"Ignore command called with indices: {indices}")
    
    try:
        playlists = ctx.obj["downloaders"][0].get_playlists()
        saved, ignored = ctx.obj["config"]["playlists"]["saved"], ctx.obj["config"]["playlists"]["ignored"]

        if not indices:
            if not playlists:
                logger.warning("No playlists available to ignore")
                click.echo("No playlists available")
                return
                
            logger.info("No indices provided, prompting user for selection")
            max_index = len(playlists) - 1
            i = -1
            while i < 0 or i > max_index:
                try:
                    i = click.prompt(f"Select playlist to ignore [0-{max_index}]", default=0, type=int)
                except click.Abort:
                    logger.info("User aborted playlist selection")
                    return
            indices = [i]

        for i in indices:
            if i >= len(playlists):
                logger.error(f"Invalid playlist index: {i}")
                click.echo(f"Invalid playlist index: {i}", err=True)
                continue
                
            playlist = playlists[i]
            
            if playlist.ratingKey in saved:
                saved.remove(playlist.ratingKey)
                logger.debug(f"Removed playlist {playlist.title} from saved list")
            if playlist.ratingKey not in ignored:
                ignored.append(playlist.ratingKey)
                logger.debug(f"Added playlist {playlist.title} to ignored list")
                
            logger.info(f"Ignored playlist: {playlist.title}")
            click.echo(f"Ignored playlist \"{playlist.title}\"")

        ctx.obj["save"]()
        logger.info(f"Configuration saved after ignoring {len(indices)} playlists")
        
    except Exception as e:
        logger.error(f"Error ignoring playlists: {e}")
        click.echo(f"Error ignoring playlists: {e}", err=True)


@cli.command()
@click.pass_context
def config(ctx) -> None:
    """Show config"""
    logger.info("Displaying current configuration")
    click.echo(f"Configuration file: {CONFIG_FILE}")
    click.echo(yaml.dump(ctx.obj["config"], default_flow_style=False))


@cli.command()
@click.pass_context
def reset(ctx) -> None:
    """Reset configuration"""
    logger.info("Reset command called")
    
    if click.confirm("This will delete all configuration. Are you sure?"):
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
            logger.info(f"Deleted configuration file: {CONFIG_FILE}")
        else:
            logger.info("Configuration file does not exist")
        click.echo("Configuration reset. Please run the command again to reconfigure.")
    else:
        logger.info("User cancelled configuration reset")


if __name__ == "__main__":
    cli()
