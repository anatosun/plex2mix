# Plex2Mix

Plex2Mix is a Plex music downloader geared towards DJs that self-host their music on a Plex server. It allows downloading selected playlists locally on your computer and dump them into `m3u8` files. This is meant to ease the import to DJ software such as Rekordbox, Traktor or Mixxx.

## Why this instead of using the plex/plexamp download feature?

By the time of writing, several reasons make Plexamp unsuitable for DJs.

- Plexamp downloads are not meant to be used by third-party apps.
- Plexamp downloaded playlists are limited to a duration of 24h.
- Plexamp may duplicate tracks that are member of multiple playlists.
- Plexamp dumps playlist information in a `json` file that does not contain the playlist title.
- The exported format (`json`) is not universally recognized by DJ softwares.

Plexamp team is however very reactive in implementing features, the above mentioned limitations might not hold in the future.


---


## Installation

please use a **virtual environment** for the least possible mess while / after setting up

### 1. Clone the repository

```bash
git clone https://github.com/raspberryhead/plex2mix.git
cd plex2mix
```

### 2. Create and activate a virtual environment

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> ⚠️ If you get a security error in PowerShell, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

#### Windows (Command Prompt)

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install Plex2Mix in editable mode

```bash
pip install -e .
```


---

### 4. Verify installation

```bash
plex2mix --help
```

You should see the CLI help output.

---

## Uninstall
```bash
pip uninstall plex2mix -y
```

---


## Usage

During the first execution of Plex2Mix, you will be prompted to log in using the provided PIN.  
You will also be asked where to store your music library and how many concurrent downloads (threads) to use.

```console
$ plex2mix list
Please visit https://plex.tv/link and enter the following code: 4VPT
Waiting for authorization...
You are logged in as *
0:  Server (string)
Select your server []:
Connected to Server
Enter path to download to [~/Music]:
Enter number of download threads [4]:
```

---

### Listing Playlists

```bash
plex2mix list
```

Example output:

```console
0: ❤️ Tracks
1: All Music
2: Bad
```

---

### Saving Playlists

Save specific playlists by index # separated by a space:

```bash
plex2mix save 0 1
```

Save all playlists:

```bash
plex2mix save --all
```

Ignore a playlist:

```bash
plex2mix ignore 2
```

---

### Downloading Playlists

two arguments for download:

- **`playlist`** → Save each playlist into its own subfolder  
- **`noplaylist`** → Save all tracks into a dedicated `noplaylist/` folder with Artist/Album subfolders  

Examples:

```bash
# Saves each playlist into its own folder
plex2mix download playlist

# Saves all tracks into the "noplaylist" folder with Artist/Album subfolders
plex2mix download noplaylist
```

When using `playlist` mode, you can flatten the structure so that all tracks are dumped directly into the playlist folder (no Artist/Album subfolders) with the following command: 

```bash
plex2mix download playlist --no-subfolders
```

Result:
~/Music/plex2mix/Chill Vibes/track1.mp3
~/Music/plex2mix/Chill Vibes/track2.mp3


Additional options:

```bash
# Force overwrite existing files
plex2mix download playlist --force

# Export playlists to M3U8 and iTunes XML
plex2mix download playlist --m3u8 --itunes

# Clear unreferenced tracks
plex2mix download playlist --clear

$ plex2mix download --help
Usage: plex2mix download [OPTIONS] [MODE]
```

Download and refresh playlists.

```
$ plex2mix download --help
Usage: plex2mix download [OPTIONS] [MODE]

  Download and refresh playlists.

  MODE:
    playlist   Save each playlist into its own subfolder
    noplaylist Save all tracks into a 'noplaylist' folder with Artist/Album subfolders

Options:
  -f, --force        Force refresh
  -c, --clear        Clear unreferenced tracks
  --itunes           Export to iTunes XML
  --m3u8             Export to m3u8
  --no-subfolders    When in playlist mode, dump all tracks directly into the playlist folder (no Artist/Album subfolders).
  --help             Show this message and exit.
 ```


---

### Help

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
there's a separate help menu for the download command as well, since i've added new arguments

```console
$ plex2mix download --help
Usage: plex2mix download [OPTIONS] [MODE]

  Download and refresh playlists.

  MODE:
    playlist   → Save each playlist into its own subfolder
    noplaylist → Save all tracks into the main library folder
```

---

## Configuration

Most of the information provided on the first execution can be changed by editing the `config.yaml` located under:

- Linux: `~/.config/plex2mix/config.yaml`  
- Windows: `%APPDATA%\plex2mix\config.yaml`  
- macOS: `~/Library/Application Support/plex2mix/config.yaml`





---





## Playlists Information





- Your playlists are downloaded under the specified path.  
- In **playlist mode**, each playlist is saved into its own subfolder.  
- In **noplaylist mode**, all tracks are saved into the main library folder.  
- By default, the `m3u8` dumps and the iTunes XML are stored in the `playlists` subfolder.
- By default, the script will check if the files already exist at the specified path dependant on subfolder structure. You can use `--force` to force the files to redownload regardless of already existing.
- REMINDER MOST OPTIONS CAN BE CHANGED BY DIRECTLY EDITING THE CONFIG FILE
