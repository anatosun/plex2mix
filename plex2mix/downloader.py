from concurrent.futures import ThreadPoolExecutor
import os
import logging
from plexapi.server import PlexServer
from plexapi.playlist import Playlist
from plexapi.audio import Track
from pathlib import Path
from typing import List, Dict, Any

# Set up logging
logger = logging.getLogger(__name__)


class Downloader:
    """Handles downloading audio tracks from Plex playlists."""

    def __init__(self, server: PlexServer, path: str, playlists_path: str, threads: int = 4, exporter=None) -> None:
        self.server = server
        self.path = os.path.expanduser(path)
        self.playlists_path = os.path.expanduser(playlists_path)
        self.pool = ThreadPoolExecutor(max_workers=threads)
        self.exporter = exporter
        logger.info(f"Initialized downloader with {threads} threads")
        logger.info(f"Music path: {self.path}")
        logger.info(f"Playlists path: {self.playlists_path}")
        if self.exporter:
            logger.info(f"Using exporter: {type(self.exporter).__name__}")

    def get_playlists(self) -> List[Playlist]:
        """Get all audio playlists from the Plex server."""
        logger.debug("Fetching playlists from Plex server")
        playlists = [p for p in self.server.playlists() if p.playlistType == 'audio']
        logger.info(f"Found {len(playlists)} audio playlists")
        return playlists

    def _path(self, track: Track) -> tuple[str, str]:
        """Return (album_path, filepath) for a track."""
        artist, album = track.grandparentTitle or "Unknown Artist", track.parentTitle or "Unknown Album"
        album_path = os.path.join(self.path, artist, album)
        _, file = os.path.split(track.media[0].parts[0].file)
        filepath = os.path.join(album_path, file)
        return album_path, filepath

    def _download_track(self, track: Track, overwrite: bool = False) -> str:
        """Download a single track if missing or incomplete."""
        album_path, filepath = self._path(track)
        
        # Ensure directory exists
        os.makedirs(album_path, exist_ok=True)
        
        size_on_server = track.media[0].parts[0].size
        track_name = f"{track.grandparentTitle or 'Unknown'} - {track.title or 'Unknown'}"

        if os.path.exists(filepath):
            local_size = os.path.getsize(filepath)
            if overwrite:
                logger.info(f"Overwriting '{track_name}' (forced)")
                track.download(album_path, keep_original_name=True)
            elif local_size < size_on_server:
                logger.warning(f"Redownloading '{track_name}' (incomplete: {local_size}/{size_on_server} bytes)")
                track.download(album_path, keep_original_name=True)
            else:
                logger.debug(f"Skipping '{track_name}' (already exists)")
        else:
            logger.info(f"Downloading '{track_name}'")
            track.download(album_path, keep_original_name=True)

        return filepath

    def download(self, playlist: Playlist, overwrite: bool = False):
        """Download all tracks in a playlist and export playlist file."""
        logger.info(f"Starting download for playlist '{playlist.title}'")
        
        tasks = []
        track_data = []
        
        # Get all tracks first
        tracks = list(playlist.items())
        logger.info(f"Playlist '{playlist.title}' contains {len(tracks)} tracks")
        
        # Download tracks
        for i, track in enumerate(tracks, 1):
            logger.debug(f"Submitting track {i}/{len(tracks)} for download: {track.title}")
            future = self.pool.submit(self._download_track, track, overwrite)
            tasks.append(future)
            
            # Collect track metadata for playlist export
            album_path, filepath = self._path(track)
            track_info = {
                'title': track.title,
                'artist': track.grandparentTitle or 'Unknown Artist',
                'album': track.parentTitle or 'Unknown Album',
                'path': filepath,
                'duration': int(track.duration / 1000) if track.duration else -1  # Convert to seconds
            }
            track_data.append(track_info)
        
        logger.info(f"Submitted {len(tasks)} download tasks to thread pool")
        
        # Export playlist file if exporter is available
        if self.exporter:
            logger.info(f"Exporting playlist '{playlist.title}' using {type(self.exporter).__name__}")
            self._export_playlist(playlist, track_data)
        else:
            logger.warning("No exporter configured, skipping playlist export")
        
        return tasks

    def _export_playlist(self, playlist: Playlist, track_data: List[Dict[str, Any]]) -> None:
        """Export playlist in the specified format."""
        if not self.exporter:
            logger.error(f"No exporter available for playlist '{playlist.title}'")
            return
        
        exporter_type = type(self.exporter).__name__
        logger.debug(f"Starting export of playlist '{playlist.title}' with {exporter_type}")
        
        try:
            if exporter_type == 'ITunesExporter':
                # iTunes exporter handles the library file directly
                logger.debug(f"Calling iTunes exporter for '{playlist.title}'")
                self.exporter.export(
                    track_data, 
                    playlist_name=playlist.title,
                    library_path=self.playlists_path
                )
                logger.info(f"iTunes export completed for '{playlist.title}'")
            else:
                # Other exporters create individual playlist files
                exporter_extensions = {
                    'JSONExporter': 'json',
                    'M3U8Exporter': 'm3u8'
                }
                
                extension = exporter_extensions.get(exporter_type, 'txt')
                filename = f"{playlist.title}.{extension}"
                filepath = os.path.join(self.playlists_path, filename)
                
                logger.debug(f"Exporting playlist to file: {filepath}")
                
                # Export playlist data
                exported_content = self.exporter.export(track_data)
                
                # Write to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(exported_content)
                
                logger.info(f"Exported playlist '{playlist.title}' to {filename}")
        
        except Exception as e:
            logger.error(f"Failed to export playlist '{playlist.title}': {e}")
            raise

    def download_playlist(self, playlist: Playlist, overwrite: bool = False):
        """Download all tracks in a playlist (legacy method for backwards compatibility)."""
        logger.debug(f"Legacy download_playlist called for '{playlist.title}'")
        return self.download(playlist, overwrite)
