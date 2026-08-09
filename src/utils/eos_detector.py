"""
EOS Detector Module

Detects whether a Steam game uses Epic Online Services (EOS) by checking if
EOSSDK-Win64-Shipping.dll (or the renamed EOSSDK-Win64-Shipping.yes) is present.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

class EOSDetector:
    """Class to detect Epic Online Services (EOS) usage for a Steam game."""

    @staticmethod
    def get_eos_dll_paths(game_directory: Union[str, Path]) -> List[Path]:
        """Find all instances of EOSSDK-Win64-Shipping.dll or EOSSDK-Win64-Shipping.yes in the game folder."""
        dir_path = Path(game_directory)
        found_paths = []
        if not dir_path.exists() or not dir_path.is_dir():
            return found_paths

        try:
            # Walk directory looking for specific filenames
            for root, _, files in os.walk(dir_path):
                # Skip .DepotDownloader folder staging files
                parts = Path(root).parts
                if ".DepotDownloader" in parts:
                    continue
                for file in files:
                    if file in ("EOSSDK-Win64-Shipping.dll", "EOSSDK-Win64-Shipping.yes"):
                        found_paths.append(Path(root) / file)
        except Exception:
            pass

        return found_paths

    @classmethod
    def detect_eos(cls, appid: Union[int, str], game_directory: Optional[Union[str, Path]] = None) -> Dict[str, Union[bool, str, List[str]]]:
        """Check if EOS is used by scanning for EOSSDK-Win64-Shipping.dll/yes files."""
        if not game_directory:
            return {
                "uses_eos": False,
                "method": "none",
                "detected_files": [],
                "details": "No game directory provided for local file scan."
            }

        dll_paths = cls.get_eos_dll_paths(game_directory)
        if dll_paths:
            rel_paths = []
            dir_path = Path(game_directory)
            for p in dll_paths:
                try:
                    rel_paths.append(str(p.relative_to(dir_path)))
                except ValueError:
                    rel_paths.append(str(p))
            
            return {
                "uses_eos": True,
                "method": "files",
                "detected_files": rel_paths,
                "details": f"Detected EOS binaries: {', '.join(rel_paths)}"
            }

        return {
            "uses_eos": False,
            "method": "none",
            "detected_files": [],
            "details": "EOSSDK-Win64-Shipping.dll/yes not found in game directory."
        }
