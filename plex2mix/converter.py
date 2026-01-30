import os
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Literal

# Set up logging
logger = logging.getLogger(__name__)


class AudioConverter:
    """Handles audio file conversion using ffmpeg.

    This converter preserves metadata and album artwork during conversion.
    """

    def __init__(self, quality: str = "320k", codec: str = "libmp3lame", storage_mode: str = "replace"):
        """
        Initialize the audio converter.

        Args:
            quality: Quality setting for ffmpeg (e.g., "320k" for CBR, "2" for VBR)
            codec: Audio codec to use (default: libmp3lame for MP3)
            storage_mode: How to handle converted files
                - "replace": Replace original files with MP3
                - "separate": Keep originals and put MP3s in 'converted' subdirectory
                - "keep_both": Keep both original and MP3 in same directory
        """
        self.quality = quality
        self.codec = codec
        self.storage_mode = storage_mode
        self._check_ffmpeg()
        logger.info(f"Initialized AudioConverter with quality={quality}, codec={codec}, storage_mode={storage_mode}")

    def _check_ffmpeg(self) -> None:
        """Check if ffmpeg is available on the system."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.debug("ffmpeg is available")
                return
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass

        logger.error("ffmpeg not found. Please install ffmpeg to use audio conversion.")
        raise RuntimeError("ffmpeg is required for audio conversion but was not found.")

    def _get_output_path(self, input_path: Path) -> Path:
        """Generate the output path based on storage mode."""
        if self.storage_mode == "replace":
            # Replace original file with MP3
            return input_path.with_suffix('.mp3')
        elif self.storage_mode == "keep_both":
            # Keep both files in same directory
            return input_path.with_suffix('.mp3')
        elif self.storage_mode == "separate":
            # Put MP3 in a 'converted' subdirectory, maintaining relative structure
            # Find the music base directory (should be 3 levels up from track: base/artist/album/track)
            # If the structure is different, we'll use the parent of the artist directory
            if len(input_path.parts) >= 3:
                # Assume structure: .../music_base/artist/album/track.ext
                music_base = input_path.parents[2]  # Go up 3 levels from track file
                relative_path = input_path.relative_to(music_base)
                converted_base = music_base / "converted"
                output_path = converted_base / relative_path.with_suffix('.mp3')
                return output_path
            else:
                # Fallback: just put in converted directory next to the file
                return input_path.parent / "converted" / input_path.with_suffix('.mp3').name
        else:
            raise ValueError(f"Unknown storage_mode: {self.storage_mode}")

    def convert_to_mp3(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Convert an audio file to MP3 format.

        Preserves all metadata (title, artist, album, etc.) and album artwork
        from the original file in the converted MP3.

        Args:
            input_path: Path to the input audio file
            output_path: Path for the output MP3 file (optional, auto-generated if not provided)

        Returns:
            Path to the converted MP3 file

        Raises:
            RuntimeError: If conversion fails
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {input_path}")

        # Generate output path if not provided
        if output_path is None:
            output_path = self._get_output_path(input_path)
        else:
            output_path = Path(output_path)

        # Skip if already MP3 and output path is the same
        if input_path.suffix.lower() == '.mp3' and input_path == output_path:
            logger.debug(f"File is already MP3: {input_path}")
            return str(input_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Converting {input_path} to MP3: {output_path}")

        # Build ffmpeg command with metadata and artwork preservation
        cmd = [
            "ffmpeg",
            "-i", str(input_path),  # Input file
            "-map", "0:a",         # Map audio stream
            "-map", "0:v?",        # Map video stream (artwork) if it exists (optional)
            "-c:v", "copy",        # Copy video codec (for artwork)
            "-acodec", self.codec, # Audio codec
            "-b:a", self.quality,  # Bitrate/quality
            "-map_metadata", "0",  # Copy all metadata
            "-y",                  # Overwrite output files
            str(output_path)       # Output file
        ]

        try:
            # Run ffmpeg conversion
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg conversion failed: {result.stderr}")
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

            # Verify output file was created
            if not output_path.exists():
                raise RuntimeError("Output file was not created")

            # Handle original file based on storage mode
            if self.storage_mode == "replace":
                # Remove original file after successful conversion
                try:
                    input_path.unlink()
                    logger.debug(f"Removed original file: {input_path}")
                except OSError as e:
                    logger.warning(f"Could not remove original file {input_path}: {e}")

            logger.info(f"Successfully converted to: {output_path}")
            return str(output_path)

        except subprocess.TimeoutExpired:
            logger.error(f"ffmpeg conversion timed out for: {input_path}")
            raise RuntimeError(f"Conversion timed out for: {input_path}")
        except Exception as e:
            logger.error(f"Error during conversion: {e}")
            raise RuntimeError(f"Conversion failed: {e}")

    def get_conversion_settings(self) -> Dict[str, Any]:
        """Get current conversion settings."""
        return {
            "quality": self.quality,
            "codec": self.codec,
            "format": "mp3",
            "storage_mode": self.storage_mode
        }