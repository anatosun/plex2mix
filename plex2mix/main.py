#!/usr/bin/env python
from concurrent.futures import as_completed
import os
import click
import yaml
import time
from plexapi.myplex import MyPlexPinLogin, MyPlexAccount
from plexapi.server import PlexServer
from plex2mix.downloader import Downloader


@click.group()
@click.pass_context
def cli(ctx) -> None:
    """plex2mix"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = {}
    ctx.obj["config_file"] = f"{os.path.join(click.get_app_dir('plex2mix'), 'config.yaml')}"
    if not os.path.exists(click.get_app_dir('plex2mix')) or not os.path.exists(ctx.obj["config_file"]):
        os.makedirs(click.get_app_dir('plex2mix'), exist_ok=True)
        yaml.dump(ctx.obj["config"], open(ctx.obj["config_file"], "w"))

    with open(ctx.obj["config_file"], "r") as f:
        ctx.obj["config"] = yaml.safe_load(f)
        if ctx.obj["config"] is None:
            ctx.obj["config"] = {}

    ctx.obj["save"] = lambda: yaml.dump(
        ctx.obj["config"], open(ctx.obj["config_file"], "w")
    )

    # Handle login and server connection
    if "token" not in ctx.obj["config"] or ctx.obj["config"]["token"] == "":
        server = login()
        ctx.obj["server"] = server
        ctx.obj["config"]["token"] = server._token
        ctx.obj["config"]["server"] = {
            "url": server._baseurl,
            "name": server.friendlyName,
        }
        ctx.obj["save"]()
    elif "server" not in ctx.obj["config"] or "url" not in ctx.obj["config"]["server"]:
        server = login(ctx.obj["config"]["token"])
        ctx.obj["server"] = server
        ctx.obj["config"]["token"] = server._token
        ctx.obj["save"]()
    else:
        try:
            server = PlexServer(
                ctx.obj["config"]["server"]["url"], ctx.obj["config"]["token"]
            )
        except Exception:
            click.echo("Could not connect to server", err=True)
            click.echo(f"Check your configuration at {ctx.obj['config_file']}")
            exit(1)
    ctx.obj["server"] = server

    # Setup download path
    if ctx.obj["config"].get("path") is None:
        path = click.prompt("Enter path to download to", default="~/Music")
        ctx.obj["config"]["path"] = os.path.expanduser(
            os.path.join(path, "plex2mix")
        )
        ctx.obj["save"]()
    if ctx.obj["config"].get("threads") is None:
        ctx.obj["config"]["threads"] = click.prompt(
            "Enter number of download threads", default=4, type=int
        )
        ctx.obj["save"]()
    if (
        ctx.obj["config"].get("playlists") is None
        or ctx.obj["config"]["playlists"].get("saved") is None
        or ctx.obj["config"]["playlists"].get("ignored") is None
    ):
        ctx.obj["config"]["playlists"] = {"saved": [], "ignored": []}
        ctx.obj["save"]()

    path = os.path.join(ctx.obj["config"]["path"])
    path = os.path.expanduser(path)
    os.makedirs(path, exist_ok=True)

    if ctx.obj["config"].get("playlists_path") is None:
        playlists_path = os.path.join(path, "playlists")
        ctx.obj["config"]["playlists_path"] = playlists_path
        ctx.obj["save"]()
    os.makedirs(ctx.obj["config"]["playlists_path"], exist_ok=True)

    ctx.obj["downloader"] = Downloader(
        ctx.obj["server"],
        ctx.obj["config"]["path"],
        ctx.obj["config"]["playlists_path"],
        ctx.obj["config"]["threads"],
    )


def login(token: str = "") -> PlexServer:
    """Login to Plex and return a PlexServer instance."""
    if not token:
        # PIN-based login flow
        login = MyPlexPinLogin()
        pin = login.pin
        click.echo(
            f"Please visit https://plex.tv/link and enter the following code: {pin}"
        )
        click.echo("Waiting for authorization...")
        while not login.checkLogin():
            time.sleep(5)
        token = str(login.token)

    # Use token to create account
    account = MyPlexAccount(token=token)
    click.echo(f"You are logged in as {account.username}")

    # Get available servers
    resources = [r for r in account.resources() if r.provides == "server"]
    if not resources:
        click.echo("No Plex servers found on this account.")
        exit(1)

    if len(resources) == 1:
        resource = resources[0]
    else:
        for i, resource in enumerate(resources):
            click.echo(f"{i}: {resource.name} ({resource.clientIdentifier})")
        index = click.prompt("Select your server", default=0, type=int)
        resource = resources[index]

    try:
        server: PlexServer = resource.connect()
        click.echo(f"Connected to {server.friendlyName}")
        return server
    except Exception as e:
        click.echo(f"Could not connect to server: {e}", err=True)
        exit(1)


@cli.command()
@click.pass_context
def list(ctx) -> None:
    """List playlists"""
    playlists = ctx.obj["downloader"].get_playlists()
    saved, ignored = (
        ctx.obj["config"]["playlists"]["saved"],
        ctx.obj["config"]["playlists"]["ignored"],
    )
    for i, playlist in enumerate(playlists):
        if playlist.ratingKey in saved:
            color = "green"
        elif playlist.ratingKey in ignored:
            color = "red"
        else:
            color = "white"
        click.echo(click.style(f"{i}: {playlist.title.strip()}", fg=color))


@cli.command()
@click.argument("indices", nargs=-1, type=int)
@click.option(
    "-a", "--all", "save_all", is_flag=True, help="Save all playlists"
)
@click.pass_context
def save(ctx, indices=[], save_all=False) -> None:
    """Save playlists to download"""
    playlists = ctx.obj["downloader"].get_playlists()
    saved, ignored = (
        ctx.obj["config"]["playlists"]["saved"],
        ctx.obj["config"]["playlists"]["ignored"],
    )

    if save_all:
        indices = list(range(len(playlists)))

    if len(indices) == 0:
        i = -1
        while i < 0 or i > len(playlists):
            i = click.prompt(
                "Select playlist to save",
                default=0,
                show_default=False,
                type=int,
                show_choices=False,
                prompt_suffix=f" [0-{len(playlists)-1}]: ",
            )
        indices = [i]

    for i in indices:
        playlist = playlists[i]
        if playlist.ratingKey not in saved:
            saved.append(playlist.ratingKey)
        if playlist.ratingKey in ignored:
            ignored.remove(playlist.ratingKey)
        ctx.obj["config"]["playlists"]["saved"] = saved
        ctx.obj["config"]["playlists"]["ignored"] = ignored
        ctx.obj["save"]()


@cli.command()
@click.argument(
    "mode",
    type=click.Choice(["playlist", "noplaylist"], case_sensitive=False),
    default="playlist",
    required=False,
)
@click.option("-f", "--force", is_flag=True, help="Force refresh")
@click.option("-c", "--clear", is_flag=True, help="Clear unreferenced tracks")
@click.option("--itunes", "itunes", is_flag=True, help="Export to iTunes XML")
@click.option("--m3u8", "m3u8", is_flag=True, help="Export to m3u8")
@click.pass_context
def download(ctx, mode, force=False, clear=False, m3u8=True, itunes=False) -> None:
    """
    Download and refresh playlists.

    MODE:
      playlist   Save each playlist into its own subfolder
      noplaylist Save all tracks into the main library folder
    """
    base_library = ctx.obj["config"]["path"]
    click.echo(f"Download and refresh playlists to {base_library} (mode: {mode})")

    playlists = ctx.obj["downloader"].get_playlists()
    saved = ctx.obj["config"]["playlists"]["saved"]
    downloader = ctx.obj["downloader"]

    for p in playlists:
        if p.ratingKey in saved:
            if mode == "playlist":
                # Create a subfolder for this playlist
                safe_name = "".join(
                    c for c in p.title if c.isalnum() or c in " _-"
                ).rstrip()
                playlist_folder = os.path.join(base_library, safe_name)
                os.makedirs(playlist_folder, exist_ok=True)
                target_folder = playlist_folder
                click.echo(f"Downloading playlist: {p.title} → {playlist_folder}")
            else:
                # Save directly into the main library folder
                target_folder = base_library
                click.echo(f"Downloading playlist: {p.title} → {base_library}")

            # Download into the chosen folder
            t = downloader.download(p, overwrite=force, target_folder=target_folder)

            with click.progressbar(
                as_completed(t), length=len(t), label=p.title
            ) as bar:
                for _ in bar:
                    pass

    # Export playlists (m3u8/itunes)
    downloader.export(m3u8, itunes)

    # Optionally clear unreferenced tracks
    if clear:
        downloaded_tracks = downloader.downloaded
        for (path, _, files) in os.walk(base_library):
            for file in files:
                pathFile = os.path.join(path, file)
                if pathFile not in downloaded_tracks:
                    os.remove(pathFile)
        for path, _, _ in os.walk(base_library, topdown=False):
            if len(os.listdir(path)) == 0:
                os.rmdir(path)


@cli.command()
@click.argument("indices", nargs=-1, type=int)
@click.pass_context
def ignore(ctx, indices=[]) -> None:
    """Ignore playlists"""
    playlists = ctx.obj["downloader"].get_playlists()
    saved, ignored = (
        ctx.obj["config"]["playlists"]["saved"],
        ctx.obj["config"]["playlists"]["ignored"],
    )
    if len(indices) == 0:
        i = -1
        while i < 0 or i > len(playlists):
            i = click.prompt(
                "Select playlist to ignore",
                default=0,
                show_default=False,
                type=int,
                show_choices=False,
                prompt_suffix=f" [0-{len(playlists)-1}]: ",
            )
        indices = [i]
    for i in indices:
        playlist = playlists[i]
        if playlist.ratingKey in saved:
            saved.remove(playlist.ratingKey)
        if playlist.ratingKey not in ignored:
            ignored.append(playlist.ratingKey)
        click.echo(f"Ignored playlist \"{playlist.title}\"")

    ctx.obj["config"]["playlists"]["saved"] = saved
    ctx.obj["config"]["playlists"]["ignored"] = ignored
    ctx.obj["save"]()


@cli.command()
@click.pass_context
def config(ctx):
    """Print config"""
    click.echo(f"Configuration file is located at {ctx.obj['config_file']}")
    click.echo(ctx.obj["config"])