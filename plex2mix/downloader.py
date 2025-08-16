from concurrent.futures import ThreadPoolExecutor
import os
import unicodedata
from plexapi.server import PlexServer
from plexapi.playlist import Playlist
from plexapi.audio import Track
from plex2mix.exporter import Exporter


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

    def __download_track(self, track: Track, overwrite=False, base_path=None) -> str:
        """
        Download a single track into the given base_path (playlist folder or global library).
        """
        base_path = base_path or self.path
        artist, album = track.grandparentTitle, track.parentTitle
        album_path = os.path.join(
            base_path,
            self.__normalize_path(artist),
            self.__normalize_path(album),
        )
        _, file = os.path.split(track.media[0].parts[0].file)
        file = self.__normalize_path(file)
        filepath = os.path.join(album_path, file)
        size_on_server = track.media[0].parts[0].size

        if not hasattr(track, "filepath"):
            track.filepath = filepath
        if not hasattr(track, "album_path"):
            track.album_path = album_path

        if os.path.exists(filepath):
            while overwrite or size_on_server > os.path.getsize(filepath):
                track.download(album_path, keep_original_name=True)
                overwrite = False
        else:
            track.download(album_path, keep_original_name=True)

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
    ) -> list:
        """
        Download all tracks in a playlist.
        If target_folder is provided, tracks will be saved under that folder.
        Otherwise, they go into the global library path.
        """
        tasks = []
        for track in list(playlist.items()):
            future = self.pool.submit(
                self.__download_track, track, overwrite, target_folder
            )
            tasks.append(future)

        # Register playlist for export
        self.pool.submit(self.exporter.register, playlist)
        return tasks

    def export(self, dump_m3u8=True, dump_itunes=False) -> None:
        self.exporter.proceed(dump_m3u8, dump_itunes)

    def __normalize_path(self, path: str):
        path = unicodedata.normalize("NFKC", path)
        path = unicodedata.normalize("NFKD", path).encode("ascii", "ignore").decode("ascii")
        return path