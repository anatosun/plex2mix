#!/usr/bin/env python
from concurrent.futures import as_completed
import os
import click
import yaml
import time
from click_aliases import ClickAliasedGroup
from plexapi.myplex import MyPlexPinLogin, MyPlexAccount
from plexapi.server import PlexServer
from plex2mix.downloader import Downloader
from plex2mix.itunes import Itunes


@ click.group(cls=ClickAliasedGroup)
@ click.pass_context
def cli(ctx) -> None:
    """plex2mix"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = {}
    ctx.obj["config_file"] = f"{os.path.join(click.get_app_dir('plex2mix'), 'config.yaml')}"
    if not os.path.exists(click.get_app_dir('plex2mix')) or not os.path.exists(ctx.obj["config_file"]):
        os.makedirs(click.get_app_dir('plex2mix'), exist_ok=True)
        yaml.dump(ctx.obj["config"], open(ctx.obj²["config_file"], "w"))

    with open(ctx.obj["config_file"], "r") as f:
        ctx.obj["config"] = yaml.safe_load(f)
        if ctx.obj["config"] is None:
            ctx.obj["config"] = {}

    ctx.obj["save"] = lambda: yaml.dump(
        ctx.obj["config"], open(ctx.obj["config_file"], "w"))

    if "token" not in ctx.obj["config"] or ctx.obj["config"]["token"] == "":
        server = login()
        ctx.obj["server"] = server
        ctx.obj["config"]["token"] = server._token
        ctx.obj["config"]["server"] = {
            "url": server._baseurl, "name": server.friendlyName}
        ctx.obj["save"]()
    elif "server" not in ctx.obj["config"] or "url" not in ctx.obj["config"]["server"]:
        server = login(ctx.obj["config"]["token"])
        ctx.obj["server"] = server
        ctx.obj["config"]["token"] = server._token
        ctx.obj["save"]()
    else:
        try:
            server = PlexServer(
                ctx.obj["config"]["server"]["url"], ctx.obj["config"]["token"])
        except:
            click.echo("Could not connect to server", err=True)
            click.echo(f"Check your configuration at {ctx.obj['config_file']}")
            exit(1)
    ctx.obj["server"] = server
    if ctx.obj["config"].get("path") is None:
        path = click.prompt("Enter path to download to", default="~/Music")
        ctx.obj["config"]["path"] = os.path.expanduser(
            os.path.join(path, "plex2mix"))
        ctx.obj["save"]()
    if ctx.obj["config"].get("threads") is None:
        ctx.obj["config"]["threads"] = click.prompt(
            "Enter number of download threads", default=4, type=int)
        ctx.obj["save"]()
    if ctx.obj["config"].get("playlists") is None or ctx.obj["config"]["playlists"].get("saved") is None or ctx.obj["config"]["playlists"].get("ignored") is None:
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
        ctx.obj["server"], ctx.obj["config"]["path"], ctx.obj["config"]["playlists_path"], ctx.obj["config"]["threads"])
    ctx.obj["itunes"] = Itunes(
        ctx.obj["downloader"], ctx.obj["config"]["server"]["url"], ctx.obj["config"]["path"], ctx.obj["config"]["playlists_path"], ctx.obj["config"]["playlists"]["saved"])

def login(token="") -> PlexServer:
    """Login to Plex"""
    if token == "":
        login = MyPlexPinLogin()
        pin = login.pin
        click.echo(
            f"Please visit https://plex.tv/link and enter the following code: {pin} ")
        click.echo("Waiting for authorization...")
        while not login.checkLogin():
            time.sleep(5)
        if token is not None:
            token = str(login.token)
    account = MyPlexAccount(token)
    click.echo(f"You are logged in as {account.username}")
    ressources = account.resources()
    if len(ressources) == 0:
        click.echo("No server found")
        exit(1)
    elif len(ressources) == 1:
        index = 0
    else:
        for i, ressource in enumerate(ressources):
            if ressource.provides == "server":
                click.echo(
                    f"{i}:  {ressource.name} ({ressource.clientIdentifier})")
        index = click.prompt("Select your server", default=0, type=int)
    try:
        server: PlexServer = ressources[index].connect()
        click.echo(f"Connected to {server.friendlyName}")
        return server
    except:
        click.echo("Could not connect to server", err=True)
        exit(1)


@ cli.command()
@ click.pass_context
def list(ctx) -> None:
    """List playlists"""
    playlists = ctx.obj["downloader"].get_playlists()
    saved, ignored = ctx.obj["config"]["playlists"]["saved"], ctx.obj["config"]["playlists"]["ignored"]
    for i, playlist in enumerate(playlists):
        if playlist.ratingKey in saved:
            color = "green"
        elif playlist.ratingKey in ignored:
            color = "red"
        else:
            color = "white"
        click.echo(click.style(f"{i}: {playlist.title.strip()}", fg=color))


@ cli.command()
@ click.argument('indices',  nargs=-1, type=int)
@ click.option('-a', '--all', 'enable_all', is_flag=True, help='Enable all playlists')
@ click.pass_context
def enable(ctx, indices=[], enable_all=False) -> None:
    """Enable playlists to saved"""
    playlists = ctx.obj["downloader"].get_playlists()
    saved, ignored = ctx.obj["config"]["playlists"]["saved"], ctx.obj["config"]["playlists"]["ignored"]

    if enable_all:
        indices = range(len(playlists))

    if len(indices) == 0:
        i = -1
        while i < 0 or i > len(playlists):
            i = click.prompt("Select playlist to enable",
                             default=0, show_default=False, type=int, show_choices=False, prompt_suffix=f" [0-{len(playlists)-1}]: ")

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

@ cli.command(aliases=['refresh'])
@click.option('-f', '--force', is_flag=True, help='Force refresh')
@ click.option('-c', '--clear', is_flag=True, help='Clear unmapped tracks')
@ click.pass_context
def download(ctx, force=False) -> None:
    """Download playlists (or refresh)"""
    configPath = ctx.obj["config"]["path"]
    click.echo(f"Download playlists (or refresh) to {configPath}")
    playlists = ctx.obj["downloader"].get_playlists()
    saved = ctx.obj["config"]["playlists"]["saved"]
    downloader = ctx.obj["downloader"]
    itunes = ctx.obj["itunes"]
    for p in playlists:
        if p.ratingKey in saved:
            t = downloader.download(p, overwrite=force)
            with click.progressbar(as_completed(t), length=len(t), label=p.title) as bar:
                for _ in bar:
                    pass
    if clear:
        clean(ctx)
    click.echo("Generate itunes XML")
    itunes.dump_itunes_xml()

@ cli.command()
@ click.pass_context
def itunes(ctx) -> None:
    """Generate itunes XML"""
    click.echo("Generate itunes XML")
    itunes = ctx.obj["itunes"]
    itunes.dump_itunes_xml()

@ cli.command()
@ click.argument('indices',  nargs=-1, type=int)
@ click.option('-a', '--all', 'enable_all', is_flag=True, help='Enable all playlists')
@ click.pass_context
def ignore(ctx, indices=[], enable_all=False) -> None:
    """Ignore playlists"""
    playlists = ctx.obj["downloader"].get_playlists()
    saved, ignored = ctx.obj["config"]["playlists"]["saved"], ctx.obj["config"]["playlists"]["ignored"]

    if enable_all:
        indices = range(len(playlists))

    if len(indices) == 0:
        i = -1
        while i < 0 or i > len(playlists):
            i = click.prompt("Select playlist to ignore",
                             default=0, show_default=False, type=int, show_choices=False, prompt_suffix=f" [0-{len(playlists)-1}]: ")
        indices = [i]
    for i in indices:
        playlist = playlists[i]
        if playlist.ratingKey in saved:
            saved.remove(playlist.ratingKey)
        if playlist.ratingKey not in ignored:
            ignored.append(playlist.ratingKey)
        click.echo(f"Ignored playlist \"{playlist.title.strip()}\"")

    ctx.obj["config"]["playlists"]["saved"] = saved
    ctx.obj["config"]["playlists"]["ignored"] = ignored
    ctx.obj["save"]()


@cli.command()
@ click.pass_context
def config(ctx):
    """Show config"""
    click.echo(f"Configuration file is located at {ctx.obj['config_file']}")
    click.echo(ctx.obj["config"])

def clean(ctx):
    click.echo('Clean playlists ignored')
    # clean playlists ignored
    playlists = ctx.obj["downloader"].get_playlists()
    saved = ctx.obj["config"]["playlists"]["saved"]
    configPlaylistsPath = ctx.obj["config"]["playlists_path"]
    for p in playlists:
        pathFile = os.path.join(configPlaylistsPath, p.title.strip() + '.m3u8')
        if p.ratingKey not in saved and os.path.isfile(pathFile):
            os.remove(pathFile)
    # clean tracks without playlists
    click.echo('Clean useless tracks')
    configPath = ctx.obj["config"]["path"]
    downloadedTracks = ctx.obj["downloader"].downloadedTracks
    for (path, directories, files) in os.walk(configPath):
        for file in files:
            pathFile = os.path.join(path, file)
            if pathFile not in downloadedTracks:
                os.remove(pathFile)
    remove_empty_folders(configPath)

def remove_empty_folders(path_abs):
    for path, _, _ in os.walk(path_abs, topdown=False):
        if len(os.listdir(path)) == 0:
            os.rmdir(path)
