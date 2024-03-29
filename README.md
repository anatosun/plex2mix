# Plex2Mix

Plex2Mix is a Plex music downloader geared towards DJs that self-host their music on a Plex server. It allows downloading selected playlists locally on your computer and dump them into `m3u8` files. This is meant to ease the import to DJ software such as Rekordbox, Traktor or Mixxx.

## Why not using Plexamp download feature?

By the time of writing, several reasons make Plexamp unsuitable for DJs.

- Plexamp downloads are not meant to be used by third-party apps.
- Plexamp downloaded playlists are limited to a duration of 24h.
- Plexamp may duplicate tracks that are member of multiple playlists.
- Plexamp dumps playlist information in a `json` file that does not contain the playlist title.
- The exported format (`json`) is not universally recognized by DJ softwares.

Plexamp team is however very reactive in implementing features, the above mentioned limitations might not hold in the future.

## Installation

You must clone this repository locally and execute:

```bash
python setup.py install --user
```

## Usage

During the first execution of Plex2Mix, you will be prompted to login using the provided PIN. You will be asked where to store you music library and to enter the number of concurrent downloads (number of threads).

```console
$ plex2mix list
Please visit https://plex.tv/link and enter the following code: 4VPT
Waiting for authorization...
You are logged in as Anatosun
0:  Server (b95d611c640365fcbd07vf960b19fdadb966c021)
Select your server [0]:
Connected to Server
Enter path to download to [~/Music]:
Enter number of download threads [4]:
```

The next step consists in listing your playlists:

```console
$ plex2mix list
0: ❤️ Tracks
1: All Music
2: Bad
```

You can thereafter pick the ones you wish to save by providing their indices:

```bash
plex2mix save 0 1
```

You can also choose to save every playlists on your server:

```bash
plex2mix save --all
```

Now, if you want to exclude a playlist from the above command you can ignore it:

```bash
plex2mix ignore 2
```

After your selection (save/ignore), you can download playlists and track with:

```bash
plex2mix download
```

If you modified your playlists on the server you might want to update them locally, just execute this command again.

Additionally, you can export your playlists to m3u8 or iTunes XML with the appropriate flags.

```bash
plex2mix download --m3u8 --itunes
```

You may also want to clear unreferenced tracks.

```bash
plex2mix download --clear
```

For any assistance you can query the help section:

```console
$ plex2mix --help
Usage: plex2mix [OPTIONS] COMMAND [ARGS]...

  plex2mix

Options:
  --help  Show this message and exit.

Commands:
  config    Print config
  download  Download and refresh playlists
  ignore    Ignore playlists
  list      List playlists
  save      Save playlists to download
```

## Configuration

Most of the information provided on the first execution can be changed by editing the `config.yaml` located under `~/.config/plex2mix/` on Linux and under the default location on other operating systems.

## Playlists information

Your playlists are downloaded under the specified path. By default, the `m3u8` dumps and the iTunes XML are stored in the `playlists` subfolder. This option can also be changed in the configuration file.
