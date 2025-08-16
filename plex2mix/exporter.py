import os
import xml.etree.ElementTree as ET
from plexapi.audio import Playlist


class Exporter:
    def __init__(self, path):
        self.path = path
        self.playlists = set()
        self.tracks = set()

    def register(self, playlist: Playlist):
        """Register a playlist and its tracks for export."""
        if playlist in self.playlists:
            return
        self.playlists.add(playlist)
        self.tracks = self.tracks.union(set(playlist.items()))

    def proceed(self, m3u8=True, itunes=False):
        """Export playlists to m3u8 and/or iTunes XML."""
        if m3u8:
            self.__m3u8()
        if itunes:
            self.__itunes()

    def __m3u8(self):
        os.makedirs(self.path, exist_ok=True)
        for playlist in self.playlists:
            title = playlist.title.strip()
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-").rstrip()
            filepath = os.path.join(self.path, f"{safe_title}.m3u8")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for track in list(playlist.items()):
                    if hasattr(track, "filepath") and track.filepath:
                        duration = track.duration // 1000 if track.duration else -1
                        artist = track.grandparentTitle or "Unknown Artist"
                        title = track.title or "Unknown Title"
                        f.write(f"#EXTINF:{duration},{artist} - {title}\n")
                        f.write(f"{track.filepath}\n")

    def __itunes(self):
        filename = "iTunes Music Library.xml"
        filepath = os.path.join(self.path, filename)
        plist = ET.Element("plist", {"version": "1.0"})
        plist_element = ET.SubElement(plist, "dict")
        ET.SubElement(plist_element, "key").text = "Major Version"
        ET.SubElement(plist_element, "integer").text = "1"
        ET.SubElement(plist_element, "key").text = "Minor Version"
        ET.SubElement(plist_element, "integer").text = "1"
        ET.SubElement(plist_element, "key").text = "Music Folder"
        ET.SubElement(plist_element, "string").text = self.path
        ET.SubElement(plist_element, "key").text = "Library Persistent ID"
        ET.SubElement(plist_element, "string").text = "plex2mix"
        ET.SubElement(plist_element, "key").text = "Tracks"

        tracks_element = ET.SubElement(plist_element, "dict")

        for track in self.tracks:
            ET.SubElement(tracks_element, "key").text = str(track.ratingKey)
            track_element = ET.SubElement(tracks_element, "dict")
            ET.SubElement(track_element, "key").text = "Track ID"
            ET.SubElement(track_element, "integer").text = str(track.ratingKey)
            ET.SubElement(track_element, "key").text = "Name"
            ET.SubElement(track_element, "string").text = track.title
            ET.SubElement(track_element, "key").text = "Artist"
            ET.SubElement(track_element, "string").text = track.grandparentTitle
            ET.SubElement(track_element, "key").text = "Album"
            ET.SubElement(track_element, "string").text = track.parentTitle
            if track.userRating:
                ET.SubElement(track_element, "key").text = "Rating"
                ET.SubElement(track_element, "integer").text = str(int(track.userRating) * 10)
            if track.album().year:
                ET.SubElement(track_element, "key").text = "Year"
                ET.SubElement(track_element, "integer").text = str(track.album().year)
            ET.SubElement(track_element, "key").text = "Play Count"
            ET.SubElement(track_element, "integer").text = str(track.viewCount)
            ET.SubElement(track_element, "key").text = "Track Type"
            ET.SubElement(track_element, "string").text = "File"

            genre = ""
            for style in track.album().genres:
                if genre:
                    genre += ";"
                genre += style.tag
            if genre:
                ET.SubElement(track_element, "key").text = "Genre"
                ET.SubElement(track_element, "string").text = genre

            ET.SubElement(track_element, "key").text = "Location"
            ET.SubElement(track_element, "string").text = track.filepath

        ET.SubElement(plist_element, "key").text = "Playlists"
        playlist_element = ET.SubElement(plist_element, "array")

        for playlist in self.playlists:
            playlist_dict = ET.SubElement(playlist_element, "dict")
            ET.SubElement(playlist_dict, "key").text = "Playlist ID"
            ET.SubElement(playlist_dict, "integer").text = str(playlist.ratingKey)
            ET.SubElement(playlist_dict, "key").text = "Playlist Persistent ID"
            ET.SubElement(playlist_dict, "string").text = playlist.guid
            ET.SubElement(playlist_dict, "key").text = "All Items"
            ET.SubElement(playlist_dict, "true")
            ET.SubElement(playlist_dict, "key").text = "Name"
            ET.SubElement(playlist_dict, "string").text = playlist.title.strip()
            ET.SubElement(playlist_dict, "key").text = "Playlist Items"

            tracksElement = ET.SubElement(playlist_dict, "array")
            for track in list(playlist.items()):
                track_element = ET.SubElement(tracksElement, "dict")
                ET.SubElement(track_element, "key").text = "Track ID"
                ET.SubElement(track_element, "integer").text = str(track.ratingKey)

        with open(filepath, "wb") as f:
            f.write('<?xml version="1.0" encoding="UTF-8" ?>\n'.encode("utf8"))
            f.write(
                '<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'.encode("utf8")
            )
            ET.ElementTree(plist).write(f, "utf-8")
