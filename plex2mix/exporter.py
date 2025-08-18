import json
import os
import logging
from xml.etree.ElementTree import Element, SubElement, tostring, parse, ParseError
from xml.dom import minidom
from typing import List, Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)


class BaseExporter:
    """Base class for all exporters."""
    
    @property
    def name(self) -> str:
        """Return the name of the exporter."""
        return self.__class__.__name__.replace('Exporter', '').lower()
    
    def export(self, data: List[Dict[str, Any]], **kwargs) -> str:
        raise NotImplementedError("Exporter must implement export method")


class JSONExporter(BaseExporter):
    def export(self, data: List[Dict[str, Any]], **kwargs) -> str:
        logger.debug(f"JSON Export: Exporting {len(data)} tracks")
        result = json.dumps(data, indent=2, ensure_ascii=False)
        logger.info(f"JSON Export: Successfully exported {len(data)} tracks")
        return result


class M3U8Exporter(BaseExporter):
    def export(self, data: List[Dict[str, Any]], **kwargs) -> str:
        """
        Expects data as a list of dicts with at least a 'path' key.
        Returns an M3U8 playlist string.
        """
        logger.debug(f"M3U8 Export: Exporting {len(data)} tracks")
        
        lines = ["#EXTM3U"]
        for item in data:
            title = item.get("title", "Unknown")
            artist = item.get("artist", "")
            duration = item.get("duration", -1)
            path = item["path"]
            
            display_title = f"{artist} - {title}" if artist and artist != "Unknown Artist" else title
            lines.append(f"#EXTINF:{duration},{display_title}")
            lines.append(path)
        
        result = "\n".join(lines)
        logger.info(f"M3U8 Export: Successfully exported {len(data)} tracks")
        return result


class ITunesExporter(BaseExporter):
    def __init__(self):
        self.library_file = "iTunes Library.xml"
        self.track_id_counter = 1
        
    def export(self, data: List[Dict[str, Any]], playlist_name: str = None, library_path: str = None, **kwargs) -> str:
        """
        Maintains a single iTunes library file and adds/updates playlists.
        """
        if not library_path:
            raise ValueError("library_path is required for iTunes export")
            
        library_file_path = os.path.join(library_path, self.library_file)
        logger.info(f"iTunes Export: Processing playlist '{playlist_name}' with {len(data)} tracks")
        logger.debug(f"iTunes Export: Library file: {library_file_path}")
        
        # Load existing library or create new one
        plist, tracks_dict, playlists_array = self._load_or_create_library(library_file_path)
        
        # Add tracks to library and get their IDs
        track_ids = self._add_tracks_to_library(tracks_dict, data)
        
        # Add or update playlist
        if playlist_name:
            self._add_or_update_playlist(playlists_array, playlist_name, track_ids)
        
        # Save library
        self._save_library(library_file_path, plist)
        
        logger.info(f"iTunes Export: Successfully updated iTunes library")
        return f"Updated iTunes library at {library_file_path}"
    
    def _load_or_create_library(self, library_file_path: str) -> tuple:
        """Load existing iTunes library or create a new one."""
        if os.path.exists(library_file_path):
            logger.debug(f"iTunes Export: Loading existing library from {library_file_path}")
            try:
                tree = parse(library_file_path)
                plist = tree.getroot()
                
                # Find tracks dict and playlists array
                dict_root = plist.find('dict')
                tracks_dict = None
                playlists_array = None
                
                # Navigate through key-value pairs
                children = list(dict_root)
                for i in range(0, len(children), 2):  # Keys and values come in pairs
                    if i + 1 < len(children):
                        key = children[i]
                        value = children[i + 1]
                        
                        if key.tag == 'key' and key.text == 'Tracks' and value.tag == 'dict':
                            tracks_dict = value
                        elif key.tag == 'key' and key.text == 'Playlists' and value.tag == 'array':
                            playlists_array = value
                
                # Get highest track ID for counter
                existing_track_count = 0
                if tracks_dict is not None:
                    track_children = list(tracks_dict)
                    track_keys = []
                    for i in range(0, len(track_children), 2):
                        if i + 1 < len(track_children):
                            key = track_children[i]
                            if key.tag == 'key' and key.text.isdigit():
                                track_keys.append(int(key.text))
                    
                    existing_track_count = len(track_keys)
                    if track_keys:
                        self.track_id_counter = max(track_keys) + 1
                
                existing_playlist_count = len(playlists_array.findall('dict')) if playlists_array is not None else 0
                logger.debug(f"iTunes Export: Found {existing_track_count} existing tracks, {existing_playlist_count} existing playlists")
                logger.debug(f"iTunes Export: Next track ID will be {self.track_id_counter}")
                
                return plist, tracks_dict, playlists_array
                
            except (ParseError, AttributeError) as e:
                logger.warning(f"iTunes Export: Error parsing existing library: {e}")
                logger.info(f"iTunes Export: Creating new library")
        else:
            logger.debug(f"iTunes Export: No existing library found, creating new one")
        
        # Create new library
        return self._create_new_library()
    
    def _create_new_library(self) -> tuple:
        """Create a new iTunes library structure."""
        logger.debug(f"iTunes Export: Creating new iTunes library structure")
        plist = Element('plist', version="1.0")
        dict_root = SubElement(plist, 'dict')
        
        # Major Version
        SubElement(dict_root, 'key').text = 'Major Version'
        SubElement(dict_root, 'integer').text = '1'
        
        # Minor Version
        SubElement(dict_root, 'key').text = 'Minor Version'
        SubElement(dict_root, 'integer').text = '1'
        
        # Application Version
        SubElement(dict_root, 'key').text = 'Application Version'
        SubElement(dict_root, 'string').text = 'plex2mix'
        
        # Tracks
        SubElement(dict_root, 'key').text = 'Tracks'
        tracks_dict = SubElement(dict_root, 'dict')
        
        # Playlists
        SubElement(dict_root, 'key').text = 'Playlists'
        playlists_array = SubElement(dict_root, 'array')
        
        return plist, tracks_dict, playlists_array
    
    def _add_tracks_to_library(self, tracks_dict: Element, data: List[Dict[str, Any]]) -> List[int]:
        """Add tracks to the library and return their track IDs."""
        track_ids = []
        
        # Create a map of existing tracks (by file path) to avoid duplicates
        existing_tracks = {}
        if tracks_dict is not None:
            children = list(tracks_dict)
            for i in range(0, len(children), 2):  # Keys and values come in pairs
                if i + 1 < len(children):
                    key_elem = children[i]
                    track_dict = children[i + 1]
                    
                    if key_elem.tag == 'key' and track_dict.tag == 'dict':
                        track_id = key_elem.text
                        if track_id.isdigit():
                            # Find Location in track_dict
                            track_children = list(track_dict)
                            for j in range(0, len(track_children), 2):
                                if j + 1 < len(track_children):
                                    track_key = track_children[j]
                                    track_value = track_children[j + 1]
                                    if track_key.tag == 'key' and track_key.text == 'Location' and track_value.tag == 'string':
                                        path = track_value.text.replace('file://', '') if track_value.text else ''
                                        existing_tracks[path] = int(track_id)
                                        break
        
        logger.debug(f"iTunes Export: Found {len(existing_tracks)} existing tracks in library")
        
        new_tracks_added = 0
        existing_tracks_reused = 0
        
        for track in data:
            track_path = track.get('path', '')
            track_title = track.get('title', 'Unknown')
            
            # Check if track already exists
            if track_path in existing_tracks:
                track_id = existing_tracks[track_path]
                track_ids.append(track_id)
                existing_tracks_reused += 1
                logger.debug(f"iTunes Export: Reusing existing track ID {track_id} for '{track_title}'")
                continue
            
            # Add new track
            track_id = self.track_id_counter
            self.track_id_counter += 1
            track_ids.append(track_id)
            new_tracks_added += 1
            
            logger.debug(f"iTunes Export: Adding new track ID {track_id} for '{track_title}'")
            
            # Track ID as key
            SubElement(tracks_dict, 'key').text = str(track_id)
            
            # Track data
            track_dict = SubElement(tracks_dict, 'dict')
            
            SubElement(track_dict, 'key').text = 'Track ID'
            SubElement(track_dict, 'integer').text = str(track_id)
            
            SubElement(track_dict, 'key').text = 'Name'
            SubElement(track_dict, 'string').text = track.get('title', '')
            
            SubElement(track_dict, 'key').text = 'Artist'
            SubElement(track_dict, 'string').text = track.get('artist', '')
            
            SubElement(track_dict, 'key').text = 'Album'
            SubElement(track_dict, 'string').text = track.get('album', '')
            
            SubElement(track_dict, 'key').text = 'Location'
            SubElement(track_dict, 'string').text = f"file://{track_path}"
            
            if track.get('duration', -1) > 0:
                SubElement(track_dict, 'key').text = 'Total Time'
                SubElement(track_dict, 'integer').text = str(track['duration'] * 1000)  # iTunes uses milliseconds
        
        logger.info(f"iTunes Export: Added {new_tracks_added} new tracks, reused {existing_tracks_reused} existing tracks")
        return track_ids
    
    def _add_or_update_playlist(self, playlists_array: Element, playlist_name: str, track_ids: List[int]):
        """Add or update a playlist in the library."""
        logger.debug(f"iTunes Export: Processing playlist '{playlist_name}' with {len(track_ids)} tracks")
        
        # Check if playlist already exists
        existing_playlist = None
        playlist_index = -1
        for i, playlist_dict in enumerate(playlists_array.findall('dict')):
            # Look for the playlist name
            children = list(playlist_dict)
            for j in range(0, len(children), 2):
                if j + 1 < len(children):
                    key_elem = children[j]
                    value_elem = children[j + 1]
                    if (key_elem.tag == 'key' and key_elem.text == 'Name' and 
                        value_elem.tag == 'string' and value_elem.text == playlist_name):
                        existing_playlist = playlist_dict
                        playlist_index = i
                        break
            if existing_playlist is not None:
                break
        
        if existing_playlist is not None:
            logger.debug(f"iTunes Export: Updating existing playlist '{playlist_name}' (index {playlist_index})")
            
            # Count existing tracks in playlist and remove old items
            old_track_count = 0
            children = list(existing_playlist)
            items_to_remove = []
            
            for j in range(0, len(children), 2):
                if j + 1 < len(children):
                    key_elem = children[j]
                    value_elem = children[j + 1]
                    if key_elem.tag == 'key' and key_elem.text == 'Playlist Items' and value_elem.tag == 'array':
                        old_track_count = len(value_elem.findall('dict'))
                        items_to_remove = [key_elem, value_elem]
                        break
            
            logger.debug(f"iTunes Export: Playlist had {old_track_count} tracks, now will have {len(track_ids)} tracks")
            
            # Remove old track items
            for item in items_to_remove:
                existing_playlist.remove(item)
        else:
            logger.debug(f"iTunes Export: Creating new playlist '{playlist_name}'")
            # Create new playlist
            existing_playlist = SubElement(playlists_array, 'dict')
            
            SubElement(existing_playlist, 'key').text = 'Name'
            SubElement(existing_playlist, 'string').text = playlist_name
            
            playlist_id = len(playlists_array.findall('dict'))
            SubElement(existing_playlist, 'key').text = 'Playlist ID'
            SubElement(existing_playlist, 'integer').text = str(playlist_id)
            logger.debug(f"iTunes Export: Assigned playlist ID {playlist_id}")
        
        # Add track items
        SubElement(existing_playlist, 'key').text = 'Playlist Items'
        items_array = SubElement(existing_playlist, 'array')
        
        for i, track_id in enumerate(track_ids):
            item_dict = SubElement(items_array, 'dict')
            SubElement(item_dict, 'key').text = 'Track ID'
            SubElement(item_dict, 'integer').text = str(track_id)
        
        logger.info(f"iTunes Export: Successfully added {len(track_ids)} track references to playlist '{playlist_name}'")
    
    def _save_library(self, library_file_path: str, plist: Element):
        """Save the iTunes library to file with consistent formatting."""
        logger.debug(f"iTunes Export: Saving library to {library_file_path}")
        
        # Count final stats
        dict_root = plist.find('dict')
        total_tracks = 0
        total_playlists = 0
        
        if dict_root is not None:
            children = list(dict_root)
            for i in range(0, len(children), 2):
                if i + 1 < len(children):
                    key = children[i]
                    value = children[i + 1]
                    
                    if key.tag == 'key' and key.text == 'Tracks' and value.tag == 'dict':
                        track_children = list(value)
                        total_tracks = len([k for k in track_children[::2] if k.tag == 'key' and k.text.isdigit()])
                    elif key.tag == 'key' and key.text == 'Playlists' and value.tag == 'array':
                        total_playlists = len(value.findall('dict'))
        
        logger.debug(f"iTunes Export: Final library contains {total_tracks} tracks and {total_playlists} playlists")
        
        # Write XML manually with consistent formatting
        try:
            with open(library_file_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" ?>\n')
                f.write('<plist version="1.0">\n')
                f.write('  <dict>\n')
                
                # Write library metadata
                children = list(dict_root)
                for i in range(0, len(children), 2):
                    if i + 1 < len(children):
                        key = children[i]
                        value = children[i + 1]
                        
                        if key.tag == 'key' and key.text in ['Major Version', 'Minor Version', 'Application Version']:
                            f.write(f'    <key>{key.text}</key>\n')
                            if value.tag == 'integer':
                                f.write(f'    <integer>{value.text}</integer>\n')
                            elif value.tag == 'string':
                                f.write(f'    <string>{value.text}</string>\n')
                
                # Write tracks section
                f.write('    <key>Tracks</key>\n')
                f.write('    <dict>\n')
                
                for i in range(0, len(children), 2):
                    if i + 1 < len(children):
                        key = children[i]
                        value = children[i + 1]
                        
                        if key.tag == 'key' and key.text == 'Tracks' and value.tag == 'dict':
                            track_children = list(value)
                            for j in range(0, len(track_children), 2):
                                if j + 1 < len(track_children):
                                    track_key = track_children[j]
                                    track_dict = track_children[j + 1]
                                    
                                    if track_key.tag == 'key' and track_dict.tag == 'dict':
                                        f.write(f'      <key>{track_key.text}</key>\n')
                                        f.write('      <dict>\n')
                                        
                                        # Write track data
                                        track_data = list(track_dict)
                                        for k in range(0, len(track_data), 2):
                                            if k + 1 < len(track_data):
                                                data_key = track_data[k]
                                                data_value = track_data[k + 1]
                                                
                                                if data_key.tag == 'key':
                                                    f.write(f'        <key>{data_key.text}</key>\n')
                                                    if data_value.tag == 'integer':
                                                        f.write(f'        <integer>{data_value.text}</integer>\n')
                                                    elif data_value.tag == 'string':
                                                        # Escape XML characters
                                                        escaped_text = data_value.text.replace('&', '&amp;') if data_value.text else ''
                                                        f.write(f'        <string>{escaped_text}</string>\n')
                                        
                                        f.write('      </dict>\n')
                            break
                
                f.write('    </dict>\n')
                
                # Write playlists section
                f.write('    <key>Playlists</key>\n')
                f.write('    <array>\n')
                
                for i in range(0, len(children), 2):
                    if i + 1 < len(children):
                        key = children[i]
                        value = children[i + 1]
                        
                        if key.tag == 'key' and key.text == 'Playlists' and value.tag == 'array':
                            for playlist_dict in value.findall('dict'):
                                f.write('      <dict>\n')
                                
                                # Write playlist data
                                playlist_data = list(playlist_dict)
                                for j in range(0, len(playlist_data), 2):
                                    if j + 1 < len(playlist_data):
                                        playlist_key = playlist_data[j]
                                        playlist_value = playlist_data[j + 1]
                                        
                                        if playlist_key.tag == 'key':
                                            f.write(f'        <key>{playlist_key.text}</key>\n')
                                            
                                            if playlist_value.tag == 'string':
                                                f.write(f'        <string>{playlist_value.text}</string>\n')
                                            elif playlist_value.tag == 'integer':
                                                f.write(f'        <integer>{playlist_value.text}</integer>\n')
                                            elif playlist_value.tag == 'array':
                                                f.write('        <array>\n')
                                                
                                                for item_dict in playlist_value.findall('dict'):
                                                    f.write('          <dict>\n')
                                                    
                                                    item_data = list(item_dict)
                                                    for k in range(0, len(item_data), 2):
                                                        if k + 1 < len(item_data):
                                                            item_key = item_data[k]
                                                            item_value = item_data[k + 1]
                                                            
                                                            if item_key.tag == 'key':
                                                                f.write(f'            <key>{item_key.text}</key>\n')
                                                                if item_value.tag == 'integer':
                                                                    f.write(f'            <integer>{item_value.text}</integer>\n')
                                                    
                                                    f.write('          </dict>\n')
                                                
                                                f.write('        </array>\n')
                                
                                f.write('      </dict>\n')
                            break
                
                f.write('    </array>\n')
                f.write('  </dict>\n')
                f.write('</plist>\n')
            
            logger.info(f"iTunes Export: Library saved successfully with {total_tracks} tracks and {total_playlists} playlists")
            
        except Exception as e:
            logger.error(f"iTunes Export: Failed to save library: {e}")
            raise


def get_exporter_by_name(name: str) -> BaseExporter:
    name = name.lower()
    logger.debug(f"Creating exporter for format: {name}")
    
    if name == "json":
        return JSONExporter()
    elif name == "m3u8":
        return M3U8Exporter()
    elif name in ("itunes", "xml"):
        return ITunesExporter()
    else:
        logger.error(f"Unknown exporter type: {name}")
        raise ValueError(f"Unknown exporter type: {name}")
