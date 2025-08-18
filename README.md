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
- **Interactive Mode**: Full-featured interactive shell for easy playlist management
- **Beautiful CLI**: ASCII art banner and colorful, intuitive interface
- **Conditional Logging**: Silent by default, verbose logging available for debugging
- **Smart File Handling**: Automatic directory creation and file organization

## Installation

## From PyPI

The easiest way to install Plex2Mix is using the PyPI package directly:

```
pip install plex2mix
```

## Manual installation

You must clone the repository locally and execute:

```bash
python setup.py install --user
```

Alternatively, you can install the requirements and run directly:

```bash
pip install -r requirements.txt
```

## Usage

### Interactive Mode

Simply run `plex2mix` without any arguments to enter the interactive mode:

```console
$ plex2mix

    ██████╗ ██╗     ███████╗██╗  ██╗██████╗ ███╗   ███╗██╗██╗  ██╗
    ██╔══██╗██║     ██╔════╝╚██╗██╔╝╚════██╗████╗ ████║██║╚██╗██╔╝
    ██████╔╝██║     █████╗   ╚███╔╝  █████╔╝██╔████╔██║██║ ╚███╔╝
    ██╔═══╝ ██║     ██╔══╝   ██╔██╗ ██╔═══╝ ██║╚██╔╝██║██║ ██╔██╗
    ██║     ███████╗███████╗██╔╝ ██╗███████╗██║ ╚═╝ ██║██║██╔╝ ██╗
    ╚═╝     ╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═╝

    🎵 Plex Music Downloader for DJs 🎧
    Convert your Plex playlists to DJ-ready formats

🎛️  Welcome to plex2mix Interactive Mode!
Type 'help' for available commands or 'quit' to exit.

plex2mix > help
plex2mix > list
plex2mix > download 0 1 2
plex2mix > status
plex2mix > quit
```

### Command Line Mode

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

List your playlists with color-coded status:

```console
$ plex2mix list
0: ❤️ Tracks
1: Favs (saved)
2: Good old tracks (saved)
3: Bad (ignored)
```

Download specific playlists:

```bash
plex2mix download 0 1
```

Download all playlists:

```bash
plex2mix download --all
```

Overwrite existing files during download:

```bash
plex2mix download --overwrite 0 1
```

Ignore playlists from bulk operations:

```bash
plex2mix ignore 3
```

Refresh saved playlists:

```bash
plex2mix refresh
```

Force refresh (overwrite existing files):

```bash
plex2mix refresh --force
```

View current configuration and status:

```bash
plex2mix config
plex2mix status  # Available in interactive mode
```

Reset configuration:

```bash
plex2mix reset
```

### Verbose Logging

Enable detailed logging for debugging or monitoring:

```bash
plex2mix --verbose list
plex2mix --verbose download 0 1
plex2mix --verbose refresh --force
```

This will show detailed information about:

- Authentication and server connection
- Playlist discovery and track processing
- Download decisions (skip/download/overwrite)
- Export operations and file creation
- iTunes library management and deduplication

### Interactive Mode Commands

The interactive mode supports all CLI commands plus additional features:

```
📋 Playlist Management:
  list, ls                    - List all playlists
  download [indices] [-a] [-o] - Download playlists
  refresh [-f]                - Refresh saved playlists
  ignore [indices]            - Ignore playlists
  status                      - Show current status

⚙️  Configuration:
  config                      - Show current configuration
  reset                       - Reset configuration

🎛️  Interactive:
  help, h, ?                  - Show this help
  clear, cls                  - Clear screen
  quit, exit, q               - Exit interactive mode
```

Examples:

```
plex2mix > download 0 1 2      # Download specific playlists
plex2mix > download -a -o      # Download all with overwrite
plex2mix > refresh -f          # Force refresh saved playlists
plex2mix > ignore 3            # Ignore playlist 3
```

### Help and Documentation

For complete command reference:

```console
$ plex2mix --help
Usage: plex2mix [OPTIONS] COMMAND [ARGS]...

  plex2mix CLI

Options:
  -v, --verbose  Enable verbose logging
  --help         Show this message and exit.

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

**Features:**

- Standard M3U8 extended format with track durations
- Artist and title information in track entries
- Direct file path references for local playback

### JSON Format

Creates individual `.json` files for each playlist containing detailed track metadata.

**Features:**

- Complete track metadata (title, artist, album, duration, path)
- Human-readable format for custom integrations
- Easy parsing for third-party applications

### iTunes Format

Creates a single `iTunes Library.xml` file that contains all tracks and playlists. This format:

**Features:**

- **Smart Deduplication**: Tracks are stored once and referenced by multiple playlists
- **Incremental Updates**: Adding playlists doesn't recreate existing tracks
- **iTunes Compatibility**: Can be imported directly into iTunes or Music.app
- **Universal Support**: Works with many music management applications
- **Persistent Track IDs**: Maintains consistent track references across updates

**How it works:**

- Creates a central track database with unique Track IDs
- Playlists reference tracks by ID, enabling efficient sharing
- Updates preserve existing tracks and only add new ones
- Maintains iTunes-standard XML structure for maximum compatibility

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

### Configuration Options

- **export_formats**: List of formats to export (m3u8, json, itunes)
- **path**: Base directory for downloaded music
- **playlists_path**: Directory for playlist files
- **threads**: Number of concurrent download threads
- **playlists.saved**: Track IDs of downloaded playlists
- **playlists.ignored**: Track IDs of ignored playlists
- **server**: Plex server connection details
- **token**: Plex authentication token

## Directory Structure

Your downloaded music will be organized as follows:

```
~/Music/plex2mix/
├── playlists/
│   ├── My Playlist.m3u8      # M3U8 playlist files
│   ├── Another Playlist.json # JSON playlist files
│   └── iTunes Library.xml    # Single iTunes library
├── Artist Name/              # Music organized by artist
│   └── Album Name/           # Then by album
│       ├── 01 Track Name.flac
│       └── 02 Another Track.flac
└── Another Artist/
    └── Album/
        └── Track.mp3
```

### File Organization

- **Music Files**: Organized in `Artist/Album/Track` hierarchy
- **Playlist Files**: Stored in dedicated `playlists/` directory
- **iTunes Library**: Single XML file containing all tracks and playlists
- **Original Filenames**: Preserved from Plex server
- **Automatic Cleanup**: Missing directories created automatically

## Advanced Features

### Smart Download Logic

- **Skip Existing**: Files already downloaded are automatically skipped
- **Resume Incomplete**: Partially downloaded files are completed
- **Size Verification**: Compares local and server file sizes
- **Overwrite Control**: Manual control over file replacement
- **Thread Safety**: Concurrent downloads with proper error handling

### Playlist State Management

- **Saved Playlists**: Automatically tracked for easy refresh
- **Ignored Playlists**: Excluded from bulk operations
- **Status Tracking**: Visual indicators in playlist listings
- **Persistent State**: Configuration saved automatically

### Error Handling

- **Graceful Failures**: Individual track failures don't stop entire downloads
- **Retry Logic**: Built-in handling for temporary network issues
- **Progress Tracking**: Real-time progress bars for download operations
- **Detailed Logging**: Comprehensive error reporting in verbose mode

## Requirements

- **Python 3.8+**: Modern Python with type hints support
- **PlexAPI**: Official Plex API client library
- **Click**: Command-line interface framework
- **PyYAML**: Configuration file handling
- **Concurrent.futures**: Built-in threading support

## Troubleshooting

### Common Issues

**Authentication Problems:**

```bash
plex2mix reset  # Clear saved credentials
plex2mix --verbose list  # Check connection details
```

**Download Issues:**

```bash
plex2mix --verbose download 0  # See detailed download process
plex2mix download --overwrite 0  # Force redownload
```

**Permission Errors:**

- Ensure write access to download directory
- Check available disk space
- Verify Plex server accessibility

### Debug Mode

Use `--verbose` flag for detailed operation logging:

- Authentication and server connection details
- Individual track download decisions
- Export format processing
- iTunes library management operations
- Error details and stack traces

### Getting Help

1. Check this README for usage examples
2. Use `plex2mix --help` for command reference
3. Try `plex2mix --verbose` for detailed operation info
4. Use interactive mode `help` command for quick reference
