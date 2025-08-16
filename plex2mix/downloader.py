from concurrent.futures import ThreadPoolExecutor
import os
import unicodedata
import logging
from plexapi.server import PlexServer
from plexapi.playlist import Playlist
from plexapi.audio import Track
from plex2mix.exporter import Exporter

logger = logging.getLogger("plex2mix.downloader")


class Downloader:
    def __init__(self, server: PlexServer, path: str, playlists_path: str, threads=4) -> None:
        self.server = server
        self.playlists = self.server.playlists(playlistType="audio")
        self.path = os.path.expanduser(os.path.join(path))
        self.playlists_path = os.path.expanduser(os.path.join(playlists_path))
        self.pool = ThreadPoolExecutor(max_workers=threads)
        self.exporter = Exporter(self.playlists_path)
        self.downloaded = []

    def get_playlists(self) -> list:
        if self.playlists is None:
            return []
        return self.playlists

    def get_playlist_titles(self) -> list:
        if self.playlists is None:
            return []
        return [p.title for p in self.playlists]

    def __download_track(self, track: Track, overwrite=False, base_path=None, no_subfolders=False) -> str:
        base_path = base_path or self.path
        logger.debug(f"Preparing to download track: {track.title} (Artist={track.grandparentTitle}, Album={track.parentTitle})")

        if no_subfolders:
            album_path = base_path
        else:
            artist, album = track.grandparentTitle, track.parentTitle
            album_path = os.path.join(
                base_path,
                self.__normalize_path(artist),
                self.__normalize_path(album),
            )

        os.makedirs(album_path, exist_ok=True)

        _, file = os.path.split(track.media[0].parts[0].file)
        file = self.__normalize_path(file)
        filepath = os.path.join(album_path, file)
        size_on_server = track.media[0].parts[0].size

        if os.path.exists(filepath) and not overwrite:
            local_size = os.path.getsize(filepath)
            if local_size == size_on_server:
                logger.debug(f"Skipping track (already exists): {filepath}")
                track.filepath = filepath
                track.album_path = album_path
                self.downloaded.append(filepath)
                return filepath
            else:
                logger.debug(f"File exists but size mismatch (local={local_size}, server={size_on_server}), re-downloading: {filepath}")

        logger.debug(f"Downloading track to: {filepath}")
        try:
            track.download(album_path, keep_original_name=True)
            logger.debug(f"Finished downloading: {filepath}")
        except Exception as e:
            logger.error(f"Error downloading {track.title}: {e}")
            raise

        actual_files = os.listdir(album_path)
        ext = os.path.splitext(file)[1].lower()
        candidates = [f for f in actual_files if f.lower().endswith(ext)]
        if candidates:
            filepath = os.path.join(album_path, candidates[0])

        track.filepath = filepath
        track.album_path = album_path
        self.downloaded.append(filepath)
        return filepath

    def futures(self):
        return self.futures

    def download(
        self,
        playlist: Playlist,
        overwrite=False,
        dump_m3u8=False,
        dump_itunes=False,
        target_folder=None,
        no_subfolders=False,
    ) -> list:
        logger.info(f"Starting download for playlist: {playlist.title} (Tracks={len(playlist.items())})")
        tasks = []
        for track in list(playlist.items()):
            logger.debug(f"Queueing track: {track.title}")
            future = self.pool.submit(
                self.__download_track,
                track,
                overwrite,
                target_folder,
                no_subfolders,
            )
            tasks.append(future)

        self.pool.submit(self.exporter.register, playlist)
        return tasks

    def export(self, dump_m3u8=True, dump_itunes=False) -> None:
        logger.info("Exporting playlists")
        self.exporter.proceed(dump_m3u8, dump_itunes)

    def __normalize_path(self, path: str):
        path = unicodedata.normalize("NFKC", path)
        path = unicodedata.normalize("NFKD", path).encode("ascii", "ignore").decode("ascii")
        return path
