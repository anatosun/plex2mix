import os
import xml.etree.ElementTree as ET

from plexapi.audio import Playlist


class Exporter:

    def __init__(self, path):
        self.path = path
        self.exported = set()
        self.tracks = set()

    def proceed(self, playlist: Playlist, m3u8=True, itunes=False):
        if playlist in self.exported:
            return
        self.exported.add(playlist)
        self.tracks = self.tracks.union(set(playlist.items()))
        if m3u8:
            self.__m3u8(playlist)
        if itunes:
            self.__itunes(playlist)

    def __m3u8(self, playlist):
        title = playlist.title.strip()
        filepath = os.path.join(self.path, f"{title}.m3u8")
        f = open(filepath, "w", encoding="utf-8")
        f.write("#EXTM3u\n")
        for track in playlist.items():
            if track.duration and track.grandparentTitle and track.parentTitle is not None:
                m3u8 = f"#EXTINF:{track.duration // 1000},{track.grandparentTitle} - {track.title}\n{track.filepath}\n"
                f.write(m3u8)

    def __itunes(self, playlist):
        filename = 'iTunes Music Library.xml'
        filepath = os.path.join(self.path, filename)
        plist: ET.Element
        plist = ET.Element('plist', {'version': '1.0'})
        plist_element = ET.SubElement(plist, 'dict')
        ET.SubElement(plist_element, 'key').text = 'Major Version'
        ET.SubElement(plist_element, 'integer').text = '1'
        ET.SubElement(plist_element, 'key').text = 'Minor Version'
        ET.SubElement(plist_element, 'integer').text = '1'
        ET.SubElement(plist_element, 'key').text = 'Music Folder'
        ET.SubElement(plist_element, 'string').text = self.path
        ET.SubElement(plist_element, 'key').text = 'Library Persistent ID'
        ET.SubElement(plist_element, 'string').text = 'plex2mix'
        ET.SubElement(plist_element, 'key').text = 'Tracks'

        tracks_element = ET.SubElement(plist_element, 'dict')

        for track in self.tracks:
            ET.SubElement(tracks_element, 'key').text = str(track.ratingKey)
            track_element = ET.SubElement(tracks_element, 'dict')
            ET.SubElement(track_element, 'key').text = "Track ID"
            ET.SubElement(track_element, 'integer').text = str(track.ratingKey)
            ET.SubElement(track_element, 'key').text = "Name"
            ET.SubElement(track_element, 'string').text = track.title
            ET.SubElement(track_element, 'key').text = "Artist"
            ET.SubElement(
                track_element, 'string').text = track.grandparentTitle
            ET.SubElement(track_element, 'key').text = "Album"
            ET.SubElement(track_element, 'string').text = track.parentTitle
            if track.userRating:
                ET.SubElement(track_element, 'key').text = "Rating"
                ET.SubElement(track_element, 'integer').text = str(
                    int(track.userRating) * 10)
            if track.album().year:
                ET.SubElement(track_element, 'key').text = "Year"
                ET.SubElement(track_element, 'integer').text = str(
                    track.album().year)
            ET.SubElement(track_element, 'key').text = "Play Count"
            ET.SubElement(track_element, 'integer').text = str(track.viewCount)
            ET.SubElement(track_element, 'key').text = "Track Type"
            ET.SubElement(track_element, 'string').text = "File"

            genre = ''
            for style in track.album().genres:
                if len(genre) > 0:
                    genre = genre + ';'
                genre = style.tag
            if len(genre) > 0:
                ET.SubElement(track_element, 'key').text = "Genre"
                ET.SubElement(track_element, 'string').text = genre

            ET.SubElement(track_element, 'key').text = "Location"
            ET.SubElement(track_element, 'string').text = track.filepath

        ET.SubElement(plist_element, 'key').text = 'Playlists'
        playlist_element = ET.SubElement(plist_element, 'array')

        for playlist in self.exported:
            ET.SubElement(playlist_element, 'key').text = 'Playlist ID'
            ET.SubElement(playlist_element, 'integer').text = str(
                playlist.ratingKey)
            ET.SubElement(playlist_element,
                          'key').text = 'Playlist Persistent ID'
            ET.SubElement(playlist_element, 'string').text = playlist.guid
            ET.SubElement(playlist_element, 'key').text = 'All Items'
            ET.SubElement(playlist_element, 'true')
            ET.SubElement(playlist_element, 'key').text = 'Name'
            ET.SubElement(playlist_element,
                          'string').text = playlist.title.strip()
            ET.SubElement(playlist_element, 'key').text = 'Playlist Items'

            tracksElement = ET.SubElement(playlist_element, 'array')
            for track in playlist.items():
                track_element = ET.SubElement(tracksElement, 'dict')
                ET.SubElement(track_element, 'key').text = 'Track ID'
                ET.SubElement(track_element, 'integer').text = str(
                    track.ratingKey)
        with open(filepath, 'wb') as f:
            f.write('<?xml version="1.0" encoding="UTF-8" ?>'.encode('utf8'))
            f.write('<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">'.encode('utf8'))
            ET.ElementTree(plist).write(f, 'utf-8')
