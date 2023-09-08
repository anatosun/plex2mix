import os
import pathlib
import xml.etree.ElementTree as ET
from plexapi.server import PlexServer
from plexapi.playlist import Playlist
from plexapi.audio import Track
from plex2mix.downloader import Downloader

class Itunes:
    def __init__(self, downloader: Downloader, serverUrl: str, path: str, playlists_path: str, playlists_saved) -> None:

        self.downloader = downloader
        self.serverUrl = serverUrl
        self.path = path
        self.playlists_path = os.path.expanduser(os.path.join(playlists_path))
        self.playlists_saved = playlists_saved
        self.filename = 'iTunes Music Library.xml'

    def dump_itunes_xml(self) -> None:
        plist = ET.Element('plist', {'version': '1.0'})
        plistElement = ET.SubElement(plist, 'dict')

        # Dump Library Informations
        ET.SubElement(plistElement, 'key').text = 'Major Version'
        ET.SubElement(plistElement, 'integer').text = '1'
        ET.SubElement(plistElement, 'key').text = 'Minor Version'
        ET.SubElement(plistElement, 'integer').text = '1'
        ET.SubElement(plistElement, 'key').text = 'Music Folder'
        ET.SubElement(plistElement, 'string').text = self.path
        ET.SubElement(plistElement, 'key').text = 'Library Persistent ID'
        ET.SubElement(plistElement, 'string').text = self.serverUrl

        # Dump tracks
        ET.SubElement(plistElement, 'key').text = 'Tracks'

        tracks = self.get_tracks()
        tracksElement = ET.SubElement(plistElement, 'dict')
        for trackId in tracks:
            track = tracks[trackId]
            ET.SubElement(tracksElement, 'key').text = str(trackId)

            trackElement = ET.SubElement(tracksElement, 'dict')
            ET.SubElement(trackElement, 'key').text = "Track ID"
            ET.SubElement(trackElement, 'integer').text = str(trackId)
            ET.SubElement(trackElement, 'key').text = "Name"
            ET.SubElement(trackElement, 'string').text = track.title
            ET.SubElement(trackElement, 'key').text = "Artist"
            ET.SubElement(trackElement, 'string').text = track.grandparentTitle
            ET.SubElement(trackElement, 'key').text = "Album"
            ET.SubElement(trackElement, 'string').text = track.parentTitle
            if track.userRating:
                ET.SubElement(trackElement, 'key').text = "Rating"
                ET.SubElement(trackElement, 'integer').text = str(int(track.userRating) * 10)
            if track.album().year:
                ET.SubElement(trackElement, 'key').text = "Year"
                ET.SubElement(trackElement, 'integer').text = str(track.album().year)
            ET.SubElement(trackElement, 'key').text = "Play Count"
            ET.SubElement(trackElement, 'integer').text = str(track.viewCount)
            ET.SubElement(trackElement, 'key').text = "Track Type"
            ET.SubElement(trackElement, 'string').text = "File"

            genre = ''
            for style in track.album().genres:
                if len(genre) > 0:
                    genre = genre + ';'
                genre = style.tag
            if len(genre) > 0:
                ET.SubElement(trackElement, 'key').text = "Genre"
                ET.SubElement(trackElement, 'string').text = genre

            _, trackLocation = self.downloader.get_path(track)
            ET.SubElement(trackElement, 'key').text = "Location"
            ET.SubElement(trackElement, 'string').text = pathlib.Path(trackLocation).as_uri()


        # Dump playlists
        ET.SubElement(plistElement, 'key').text = 'Playlists'

        playlists = self.downloader.get_playlists()
        playlistsElement = ET.SubElement(plistElement, 'array')
        playlistId = 1
        for playlist in playlists:
            if playlist.ratingKey in self.playlists_saved:
                playlistElement = ET.SubElement(playlistsElement, 'dict')
                ET.SubElement(playlistElement, 'key').text = 'Playlist ID'
                ET.SubElement(playlistElement, 'integer').text = str(playlistId)
                ET.SubElement(playlistElement, 'key').text = 'Playlist Persistent ID'
                ET.SubElement(playlistElement, 'string').text = playlist.guid
                ET.SubElement(playlistElement, 'key').text = 'All Items'
                ET.SubElement(playlistElement, 'true')
                ET.SubElement(playlistElement, 'key').text = 'Name'
                ET.SubElement(playlistElement, 'string').text = playlist.title.strip()
                ET.SubElement(playlistElement, 'key').text = 'Playlist Items'

                tracksElement = ET.SubElement(playlistElement, 'array')
                for playlistTrack in playlist.items():
                    for trackId in tracks:
                        track = tracks[trackId]
                        if track.guid == playlistTrack.guid:
                            trackElement = ET.SubElement(tracksElement, 'dict')
                            ET.SubElement(trackElement, 'key').text = 'Track ID'
                            ET.SubElement(trackElement, 'integer').text = str(trackId)
                playlistId = playlistId + 1


        itunes_xml_path = os.path.join(self.playlists_path, self.filename)
        with open(itunes_xml_path, 'wb') as f:
            f.write('<?xml version="1.0" encoding="UTF-8" ?>'.encode('utf8'))
            f.write('<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">'.encode('utf8'))
            ET.ElementTree(plist).write(f, 'utf-8')

    def get_tracks(self):
        tracks = {}
        playlists = self.downloader.get_playlists()
        for playlist in playlists:
            if playlist.ratingKey in self.playlists_saved:
                for track in playlist.items():
                    tracks[track.guid] = track # use guid to ensure track is unique in list

        tracksDict = {}
        id = 1
        for trackGuid in tracks:
            tracksDict[id] = tracks[trackGuid]
            id = id + 1

        return tracksDict
