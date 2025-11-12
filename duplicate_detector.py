"""
Duplicate Detector for WallpaperChanger

Uses perceptual hashing to detect duplicate and similar wallpapers.
Helps keep the cache clean and avoid downloading duplicates.
"""

import os
from typing import Dict, List, Tuple, Optional
import imagehash
from PIL import Image


class DuplicateDetector:
    """Detect duplicate and similar images using perceptual hashing"""

    # Hamming distance thresholds
    EXACT_MATCH = 0  # Identical images
    VERY_SIMILAR = 5  # Nearly identical (minor edits, compression)
    SIMILAR = 10  # Similar composition/content
    SOMEWHAT_SIMILAR = 15  # Some similarities

    def __init__(self, hash_size: int = 8):
        """
        Initialize duplicate detector

        Args:
            hash_size: Size of the hash (8 = 64-bit hash, 16 = 256-bit hash)
                      Larger = more precise but slower
        """
        self.hash_size = hash_size

    def compute_hash(self, image_path: str) -> Optional[str]:
        """
        Compute perceptual hash for an image

        Args:
            image_path: Path to the image file

        Returns:
            Hash string or None if error
        """
        try:
            with Image.open(image_path) as img:
                # Use average hash (fast and good for duplicates)
                # Alternative: phash (more robust), dhash (good for transformations)
                hash_value = imagehash.average_hash(img, hash_size=self.hash_size)
                return str(hash_value)
        except Exception as e:
            print(f"[ERROR] Failed to compute hash for {image_path}: {e}")
            return None

    def compute_multiple_hashes(self, image_path: str) -> Optional[Dict[str, str]]:
        """
        Compute multiple types of hashes for better detection

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with different hash types
        """
        try:
            with Image.open(image_path) as img:
                return {
                    'ahash': str(imagehash.average_hash(img, hash_size=self.hash_size)),
                    'phash': str(imagehash.phash(img, hash_size=self.hash_size)),
                    'dhash': str(imagehash.dhash(img, hash_size=self.hash_size)),
                }
        except Exception as e:
            print(f"[ERROR] Failed to compute hashes for {image_path}: {e}")
            return None

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Calculate Hamming distance between two hashes

        Args:
            hash1: First hash string
            hash2: Second hash string

        Returns:
            Hamming distance (number of different bits)
        """
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2  # imagehash overloads - operator for Hamming distance
        except Exception as e:
            print(f"[ERROR] Failed to calculate distance: {e}")
            return 999  # Return high value to indicate error

    def find_duplicates(
        self,
        image_paths: List[str],
        threshold: int = VERY_SIMILAR
    ) -> List[Tuple[str, str, int]]:
        """
        Find duplicate/similar images in a list

        Args:
            image_paths: List of image file paths
            threshold: Maximum Hamming distance to consider similar

        Returns:
            List of tuples (path1, path2, distance) for similar images
        """
        print(f"[DUPLICATE] Scanning {len(image_paths)} images...")

        # Compute hashes for all images
        hashes = {}
        for path in image_paths:
            hash_value = self.compute_hash(path)
            if hash_value:
                hashes[path] = hash_value

        print(f"[DUPLICATE] Computed hashes for {len(hashes)} images")

        # Find similar pairs
        duplicates = []
        paths_list = list(hashes.keys())

        for i, path1 in enumerate(paths_list):
            for path2 in paths_list[i + 1:]:
                distance = self.hamming_distance(hashes[path1], hashes[path2])
                if distance <= threshold:
                    duplicates.append((path1, path2, distance))

        print(f"[DUPLICATE] Found {len(duplicates)} similar pairs")
        return duplicates

    def find_similar_to(
        self,
        target_path: str,
        candidate_paths: List[str],
        threshold: int = VERY_SIMILAR
    ) -> List[Tuple[str, int]]:
        """
        Find images similar to a target image

        Args:
            target_path: Path to target image
            candidate_paths: List of candidate image paths
            threshold: Maximum Hamming distance to consider similar

        Returns:
            List of tuples (path, distance) sorted by similarity
        """
        target_hash = self.compute_hash(target_path)
        if not target_hash:
            return []

        similar = []
        for path in candidate_paths:
            if path == target_path:
                continue

            candidate_hash = self.compute_hash(path)
            if not candidate_hash:
                continue

            distance = self.hamming_distance(target_hash, candidate_hash)
            if distance <= threshold:
                similar.append((path, distance))

        # Sort by distance (most similar first)
        similar.sort(key=lambda x: x[1])
        return similar

    def is_duplicate(
        self,
        image_path: str,
        existing_hashes: Dict[str, str],
        threshold: int = VERY_SIMILAR
    ) -> Optional[Tuple[str, int]]:
        """
        Check if an image is a duplicate of any existing images

        Args:
            image_path: Path to new image
            existing_hashes: Dict mapping paths to their hashes
            threshold: Maximum Hamming distance to consider duplicate

        Returns:
            Tuple (duplicate_path, distance) if duplicate found, None otherwise
        """
        new_hash = self.compute_hash(image_path)
        if not new_hash:
            return None

        for existing_path, existing_hash in existing_hashes.items():
            distance = self.hamming_distance(new_hash, existing_hash)
            if distance <= threshold:
                return (existing_path, distance)

        return None

    def get_similarity_description(self, distance: int) -> str:
        """Get human-readable description of similarity level"""
        if distance == self.EXACT_MATCH:
            return "Exact duplicate"
        elif distance <= self.VERY_SIMILAR:
            return "Nearly identical"
        elif distance <= self.SIMILAR:
            return "Very similar"
        elif distance <= self.SOMEWHAT_SIMILAR:
            return "Similar"
        else:
            return "Somewhat similar"


if __name__ == "__main__":
    # Test the duplicate detector
    detector = DuplicateDetector()
    print("Duplicate Detector initialized")
    print(f"Thresholds:")
    print(f"  Exact match: {detector.EXACT_MATCH}")
    print(f"  Very similar: {detector.VERY_SIMILAR}")
    print(f"  Similar: {detector.SIMILAR}")
    print(f"  Somewhat similar: {detector.SOMEWHAT_SIMILAR}")
