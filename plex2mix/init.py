"""
Plex2Mix - Plex music downloader for DJs

🎵 Download playlists locally with deduplication, export to M3U8/JSON/iTunes 
formats, and manage your music library efficiently.

Copyright (C) 2025 anatosun

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

__author__ = "anatosun"
__email__ = "z4jyol8l@duck.com"
__description__ = "Plex music downloader for DJs"
__license__ = "GPL-3.0-or-later"

# Make main CLI function available at package level
from .main import cli

__all__ = ["cli", "__version__"]
