#!/usr/bin/env python3
import sys
import time
import yaml
import click
from pathlib import Path
from concurrent.futures import as_completed
from typing import Dict, Any, List

from plexapi.myplex import MyPlexPinLogin, MyPlexAccount
from plexapi.server import PlexServer
from plex2mix.downloader import Downloader
from plex2mix.exporter import get_exporter_by_name

CONFIG_DIR = Path(click.get_app_dir("plex2mix"))
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def load_config() -> Dict[str, Any]:
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(yaml.dump({}))

    with CONFIG_FILE.open("r") as f:
        config = yaml.safe_load(f) or {}

    return config


def save_config(config: Dict[str, Any]) -> None:
    with CONFIG_FILE.open("w") as f:
        yaml.dump(config, f)


def login(token: str = "") -> PlexServer:
    """Authenticate with Plex and return a connected PlexServer."""
    if not token:
        login_session = MyPlexPinLogin()
        pin = login_session.pin
        click.echo(f"Visit https://plex.tv/link and enter the code: {pin}")
        click.echo("Waiting for authorization...")
        while not login_session.checkLogin():
            time.sleep(5)
        token = str(login_session.token)

    account = MyPlexAccount(token=token)
    click.echo(f"Logged in as {account.username}")
    resources = [r for r in account.resources() if r.provides == "server"]

    if not resources:
        click.echo("No server found", err=True)
        sys.exit(1)

    if len(resources) > 1:
        for i, resource in enumerate(resources):
            click.echo(f"{i}: {resource.name} ({resource.clientIdentifier})")
        index = click.prompt("Select your server", default=0, type=int)
    else:
        index = 0

    try:
        server: PlexServer = resources[index].connect()
        click.echo(f"Connected to {server.friendlyName}")
        return server
    except Exception as e:
        click.echo(f"Could not connect to server: {e}", err=True)
        sys.exit(1)


@click.group()
@click.pass_context
def cli(ctx) -> None:
    """plex2mix CLI"""
    ctx.ensure_object(dict)
    config = load_config()

    # Handle authentication
    if not config.get("token"):
        server = login()
        config["token"] = server._token
        config["server"] = {"url": server._baseurl, "name": server.friendlyName}
        save_config(config)
    else:
        try:
            server = PlexServer(config["server"]["url"], config["token"])
        except Exception as e:
            click.echo(f"Could not connect to server: {e}", err=True)
            click.echo(f"Clearing invalid token. Please run the command again to re-authenticate.")
            config.pop("token", None)
            config.pop("server", None)
            save_config(config)
            sys.exit(1)

    # Setup paths
    if "path" not in config:
        path = Path(click.prompt("Enter path to download to", default="~/Music")).expanduser() / "plex2mix"
        config["path"] = str(path)
        save_config(config)

    if "threads" not in config:
        config["threads"] = click.prompt("Enter number of download threads", default=4, type=int)
        save_config(config)

    # Initialize playlist tracking
    playlists_config = config.get("playlists")
    if not playlists_config or not hasattr(playlists_config, 'get'):
        config["playlists"] = {"saved": [], "ignored": []}
        save_config(config)

    # Setup export formats
    export_formats = config.get("export_formats")
    if not export_formats or not hasattr(export_formats, '__iter__') or type(export_formats) is str:
        formats = click.prompt("Select export formats (comma-separated, e.g., m3u8,itunes)", default="m3u8")
        config["export_formats"] = [f.strip() for f in formats.split(",") if f.strip()]
        save_config(config)

    # Create directories
    path = Path(config["path"]).expanduser()
    path.mkdir(parents=True, exist_ok=True)

    if not config.get("playlists_path"):
        playlists_path = path / "playlists"
        config["playlists_path"] = str(playlists_path)
        save_config(config)

    Path(config["playlists_path"]).mkdir(parents=True, exist_ok=True)

    # Create downloaders for each export format
    downloaders = []
    for fmt in config["export_formats"]:
        try:
            exporter = get_exporter_by_name(fmt)
            downloader = Downloader(
                server,
                config["path"],
                config["playlists_path"],
                config["threads"],
                exporter=exporter
            )
            downloaders.append(downloader)
        except ValueError as e:
            click.echo(f"Warning: {e}", err=True)

    if not downloaders:
        click.echo("No valid export formats configured", err=True)
        sys.exit(1)

    ctx.obj["config"] = config
    ctx.obj["server"] = server
    ctx.obj["save"] = lambda: save_config(config)
    ctx.obj["downloaders"] = downloaders


@cli.command()
@click.pass_context
def list(ctx) -> None:
    """List playlists"""
    try:
        playlists = ctx.obj["downloaders"][0].get_playlists()
        saved, ignored = ctx.obj["config"]["playlists"]["saved"], ctx.obj["config"]["playlists"]["ignored"]

        if not playlists:
            click.echo("No playlists found on the server.")
            return

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
        click.echo(f"Error listing playlists: {e}", err=True)


def download_playlists(ctx, indices: List[int], overwrite: bool = False):
    """Download playlists by indices."""
    try:
        playlists = ctx.obj["downloaders"][0].get_playlists()
        saved, ignored = ctx.obj["config"]["playlists"]["saved"], ctx.obj["config"]["playlists"]["ignored"]

        for i in indices:
            if i >= len(playlists):
                click.echo(f"Invalid playlist index: {i}", err=True)
                continue
                
            playlist = playlists[i]
            if playlist.ratingKey in ignored:
                click.echo(f"Skipping ignored playlist: {playlist.title}")
                continue

            click.echo(f"Processing playlist: {playlist.title}")
            
            for downloader in ctx.obj["downloaders"]:
                try:
                    tasks = downloader.download(playlist, overwrite=overwrite)
                    if tasks:
                        with click.progressbar(
                            as_completed(tasks), 
                            length=len(tasks), 
                            label=f"{playlist.title} ({downloader.exporter.name})"
                        ) as bar:
                            for _ in bar:
                                pass
                    else:
                        click.echo(f"No tracks to download for {playlist.title}")
                except Exception as e:
                    click.echo(f"Error downloading {playlist.title} with {downloader.exporter.name}: {e}", err=True)

            # Update playlist status
            if playlist.ratingKey not in saved:
                saved.append(playlist.ratingKey)
            if playlist.ratingKey in ignored:
                ignored.remove(playlist.ratingKey)

            ctx.obj["save"]()
            click.echo(f"Completed: {playlist.title}")

    except Exception as e:
        click.echo(f"Error during download: {e}", err=True)


@cli.command()
@click.argument("indices", nargs=-1, type=int)
@click.option("-a", "--all", "download_all", is_flag=True, help="Download all playlists")
@click.option("-o", "--overwrite", is_flag=True, help="Overwrite existing files")
@click.pass_context
def download(ctx, indices: List[int], download_all: bool, overwrite: bool) -> None:
    """Download playlists"""
    playlists = ctx.obj["downloaders"][0].get_playlists()
    
    if download_all:
        indices = list(range(len(playlists)))
    elif not indices:
        if not playlists:
            click.echo("No playlists available")
            return
            
        max_index = len(playlists) - 1
        i = -1
        while i < 0 or i > max_index:
            try:
                i = click.prompt(f"Select playlist to download [0-{max_index}]", default=0, type=int)
            except click.Abort:
                return
        indices = [i]

    download_playlists(ctx, indices, overwrite=overwrite)


@cli.command()
@click.option("-f", "--force", is_flag=True, help="Force refresh (overwrite existing files)")
@click.pass_context
def refresh(ctx, force: bool) -> None:
    """Refresh saved playlists"""
    try:
        playlists = ctx.obj["downloaders"][0].get_playlists()
        saved = ctx.obj["config"]["playlists"]["saved"]

        if not saved:
            click.echo("No saved playlists to refresh")
            return

        # Find indices of saved playlists
        indices = []
        for i, p in enumerate(playlists):
            if p.ratingKey in saved:
                indices.append(i)

        if not indices:
            click.echo("No saved playlists found on server")
            return

        click.echo(f"Refreshing {len(indices)} saved playlists...")
        download_playlists(ctx, indices, overwrite=force)
    except Exception as e:
        click.echo(f"Error during refresh: {e}", err=True)


@cli.command()
@click.argument("indices", nargs=-1, type=int)
@click.pass_context
def ignore(ctx, indices: List[int]) -> None:
    """Ignore playlists"""
    try:
        playlists = ctx.obj["downloaders"][0].get_playlists()
        saved, ignored = ctx.obj["config"]["playlists"]["saved"], ctx.obj["config"]["playlists"]["ignored"]

        if not indices:
            if not playlists:
                click.echo("No playlists available")
                return
                
            max_index = len(playlists) - 1
            i = -1
            while i < 0 or i > max_index:
                try:
                    i = click.prompt(f"Select playlist to ignore [0-{max_index}]", default=0, type=int)
                except click.Abort:
                    return
            indices = [i]

        for i in indices:
            if i >= len(playlists):
                click.echo(f"Invalid playlist index: {i}", err=True)
                continue
                
            playlist = playlists[i]
            if playlist.ratingKey in saved:
                saved.remove(playlist.ratingKey)
            if playlist.ratingKey not in ignored:
                ignored.append(playlist.ratingKey)
            click.echo(f"Ignored playlist \"{playlist.title}\"")

        ctx.obj["save"]()
    except Exception as e:
        click.echo(f"Error ignoring playlists: {e}", err=True)


@cli.command()
@click.pass_context
def config(ctx) -> None:
    """Show config"""
    click.echo(f"Configuration file: {CONFIG_FILE}")
    click.echo(yaml.dump(ctx.obj["config"], default_flow_style=False))


@cli.command()
@click.pass_context
def reset(ctx) -> None:
    """Reset configuration"""
    if click.confirm("This will delete all configuration. Are you sure?"):
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        click.echo("Configuration reset. Please run the command again to reconfigure.")


if __name__ == "__main__":
    cli()
