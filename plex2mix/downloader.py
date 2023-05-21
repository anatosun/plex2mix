from concurrent.futures import ThreadPoolExecutor
import os
from plexapi.server import PlexServer
from plexapi.playlist import Playlist
from plexapi.audio import Track


class Downloader:
    def __init__(self, server: PlexServer, path: str, playlists_path: str, threads=4) -> None:

        self.server = server
        self.playlists = self.server.playlists(playlistType='audio')
        self.path = os.path.expanduser(os.path.join(path))
        self.playlists_path = os.path.expanduser(os.path.join(playlists_path))
        self.pool = ThreadPoolExecutor(max_workers=threads)
        self.tasks = []

    def get_playlists(self) -> list:
        if self.playlists is None:
            return []
        return self.playlists

    def get_playlist_titles(self) -> list:
        if self.playlists is None:
            return []
        return [p.title for p in self.playlists]

    def __download_track(self, track: Track,  overwrite=False) -> str:
        album_path, filepath = self.__path(track)
        size_on_server = track.media[0].parts[0].size
        if os.path.exists(filepath):
            while overwrite or size_on_server > os.path.getsize(filepath):
                track.download(album_path, keep_original_name=True)
                overwrite = False
        else:
            track.download(album_path, keep_original_name=True)

        return filepath

    def __path(self, track: Track) -> tuple:
        artist, album = track.grandparentTitle, track.parentTitle
        album_path = os.path.join(self.path, artist, album)
        _, file = os.path.split(track.media[0].parts[0].file)
        filepath = os.path.join(album_path, file)
        return album_path, filepath

    def dump_m3u8(self, playlist: Playlist) -> None:
        m3u8 = "#EXTM3U\n"
        m3u8 += f"#PLAYLIST:{playlist.title}\n"
        track: Track
        for track in playlist.items():
            _, filepath = self.__path(track)
            m3u8 += f"#EXTINF:{track.duration // 1000},{track.grandparentTitle} - {track.title}\n#EXT-X-RATING:{track.userRating if track.userRating is not None else 0}\n{filepath}\n"
        with open(os.path.join(self.playlists_path, f"{playlist.title}.m3u8"), "w") as f:
            f.write(m3u8)

    def futures(self):
        return self.futures

    def download(self, playlist: Playlist, overwrite=False) -> list:

        for track in playlist.items():
            future = self.pool.submit(self.__download_track, track, overwrite)
            self.tasks.append(future)
        self.pool.submit(self.dump_m3u8, playlist)
        return self.tasks
