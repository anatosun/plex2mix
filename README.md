# Plex2Mix

Plex2Mix is a Plex music downloader geared towards DJs that self-host their music on a Plex server. It allows downloading selected playlists locally on your computer and exports them in multiple formats including `m3u8`, `json`, and iTunes-compatible `xml`. This is meant to ease the import to DJ software such as Rekordbox, Traktor, Mixxx, or iTunes.

## Why not using Plexamp download feature?

By the time of writing, several reasons make Plexamp unsuitable for DJs:

- Plexamp downloads are not meant to be used by third-party apps.
- Plexamp downloaded playlists are limited to a certain duration for efficiency.
- Plexamp may duplicate tracks that are member of multiple playlists.
- Plexamp dumps playlist information in a `json` file that does not contain the playlist title.
- The exported format (`json`) is not universally recognized by DJ softwares.

Plexamp team is however very reactive in implementing features, the above mentioned limitations might not hold in the future.

## Features

- **Multiple Export Formats**: Support for M3U8, JSON, and iTunes XML formats
- **Smart Track Deduplication**: Tracks shared between playlists are only downloaded once
- **iTunes Library Management**: Creates a single iTunes library file that can be imported into iTunes or other compatible players
- **Concurrent Downloads**: Multi-threaded downloading for faster sync
- **Playlist Management**: Track which playlists are downloaded, ignored, or need refreshing
- **Incremental Updates**: Only download new or changed tracks when refreshing playlists

## Installation

You must clone the repository locally and execute:

```bash
python setup.py install --user
```

Alternatively, you can install the requirements and run directly:

```bash
pip install -r requirements.txt
```

## Usage

During the first execution of Plex2Mix, you will be prompted to login using the provided PIN. You will be asked where to store your music library, to enter the number of concurrent downloads (number of threads), and to select your preferred export formats.

```console
$ plex2mix list
Visit https://plex.tv/link and enter the code: 4VPT
Waiting for authorization...
Logged in as Anatosun
0: Server (b95d611c640365fcbd07vf960b19fdadb966c021)
Select your server [0]:
Connected to Server
Enter path to download to [~/Music]: ~/Music/plex2mix
Enter number of download threads [4]: 4
Select export formats (comma-separated, e.g., m3u8,itunes) [m3u8]: m3u8,itunes
```

The next step consists in listing your playlists:

```console
$ plex2mix list
0: ❤️ Tracks
1: Favs (saved)
2: Good old tracks (saved)
3: Bad (ignored)
```

You can thereafter pick the ones you wish to download by providing their indices:

```bash
plex2mix download 0 1
```

You can also choose to download all the playlists on your server:

```bash
plex2mix download --all
```

To overwrite existing files during download:

```bash
plex2mix download --overwrite 0 1
```

Now, if you want to exclude a playlist from bulk operations you can ignore it:

```bash
plex2mix ignore 2
```

At some point, if you modified your playlists on the server you might want to update them locally, this is done with a refresh:

```bash
plex2mix refresh
```

To force refresh (overwrite existing files):

```bash
plex2mix refresh --force
```

View your current configuration:

```bash
plex2mix config
```

Reset your configuration (useful if you need to re-authenticate or change servers):

```bash
plex2mix reset
```

For any assistance you can query the help section:

```console
$ plex2mix --help
Usage: plex2mix [OPTIONS] COMMAND [ARGS]...

  plex2mix CLI

Options:
  --help  Show this message and exit.

Commands:
  config    Show config
  download  Download playlists
  ignore    Ignore playlists
  list      List playlists
  refresh   Refresh saved playlists
  reset     Reset configuration
```

## Export Formats

### M3U8 Format

Creates individual `.m3u8` files for each playlist in the `playlists` directory. Compatible with most DJ software and media players.

### JSON Format

Creates individual `.json` files for each playlist containing detailed track metadata.

### iTunes Format

Creates a single `iTunes Library.xml` file that contains all tracks and playlists. This format:

- Eliminates track duplication by maintaining a central track database
- Allows tracks to be shared between multiple playlists
- Can be imported directly into iTunes or other compatible applications
- Updates playlists incrementally without recreating the entire library

## Configuration

Most of the information provided on the first execution can be changed by editing the `config.yaml` located under `~/.config/plex2mix/` on Linux and under the default location on other operating systems.

Example configuration:

```yaml
export_formats:
  - m3u8
  - itunes
path: /home/user/Music/plex2mix
playlists:
  ignored: []
  saved: []
playlists_path: /home/user/Music/plex2mix/playlists
server:
  name: My Plex Server
  url: http://192.168.1.100:32400
threads: 4
token: your_plex_token_here
```

## Directory Structure

Your downloaded music will be organized as follows:

```
~/Music/plex2mix/
├── playlists/
│   ├── My Playlist.m3u8
│   ├── Another Playlist.json
│   └── iTunes Library.xml
├── Artist Name/
│   └── Album Name/
│       ├── 01 Track Name.flac
│       └── 02 Another Track.flac
└── Another Artist/
    └── Album/
        └── Track.mp3
```

## Requirements

- Python 3.8+
- PlexAPI
- Click
- PyYAML
