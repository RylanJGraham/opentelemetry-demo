"""Utilities for hashing, caching, and image processing."""
import hashlib
import io
import json
import logging
from typing import Dict, List, Optional, Tuple
from PIL import Image
import imagehash

logger = logging.getLogger("agent.utils")


class ImageHasher:
    """Multi-level image hashing for screen identification."""
    
    @staticmethod
    def content_hash(image_bytes: bytes) -> str:
        """
        Level 1: Exact content hash (SHA-256).
        Fastest - detects identical screenshots.
        """
        return hashlib.sha256(image_bytes).hexdigest()
    
    @staticmethod
    def perceptual_hash(image_bytes: bytes) -> str:
        """
        Level 2: Perceptual hash (pHash).
        Detects similar-looking screens despite minor visual differences.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            phash = imagehash.phash(img, hash_size=16)
            return str(phash)
        except Exception as e:
            logger.error(f"pHash computation failed: {e}")
            return ""
    
    @staticmethod
    def structure_hash(image_bytes: bytes) -> str:
        """
        Level 3: Structure hash (average hash).
        Detects screens with same layout but different content.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            # Resize to small size to focus on structure
            img = img.resize((16, 16), Image.Resampling.LANCZOS)
            # Convert to grayscale
            img = img.convert('L')
            # Compute average hash
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)
            # Create binary hash
            bits = ''.join('1' if p > avg else '0' for p in pixels)
            return hex(int(bits, 2))[2:].zfill(64)
        except Exception as e:
            logger.error(f"Structure hash computation failed: {e}")
            return ""
    
    @staticmethod
    def compute_all_hashes(image_bytes: bytes) -> Dict[str, str]:
        """Compute all hash types for a screenshot."""
        return {
            "content_hash": ImageHasher.content_hash(image_bytes),
            "perceptual_hash": ImageHasher.perceptual_hash(image_bytes),
            "structure_hash": ImageHasher.structure_hash(image_bytes),
        }
    
    @staticmethod
    def phash_similarity(hash1: str, hash2: str) -> float:
        """Calculate similarity between two perceptual hashes (0-1)."""
        if not hash1 or not hash2:
            return 0.0
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            # Hamming distance
            distance = h1 - h2
            # Normalize: max distance for 16-bit hash is 256
            similarity = 1.0 - (distance / 256.0)
            return max(0.0, similarity)
        except Exception:
            return 0.0


class StructureHasher:
    """Hash based on UI element structure rather than pixels."""
    
    @staticmethod
    def compute_element_fingerprint(elements: List[Dict]) -> str:
        """
        Create a hash based on the structure of UI elements.
        This helps identify the same screen type even with different content.
        """
        # Sort elements by position
        sorted_elements = sorted(
            elements, 
            key=lambda e: (e.get('y', 0), e.get('x', 0))
        )
        
        # Create structure string: type_count_grid
        structure_parts = []
        
        # Group by rough vertical position (rows)
        row_height = 200  # pixels
        rows: Dict[int, List[str]] = {}
        
        for el in sorted_elements:
            y = el.get('y', 0)
            row = int(y / row_height)
            el_type = el.get('type', 'unknown')
            if row not in rows:
                rows[row] = []
            rows[row].append(el_type)
        
        # Build structure string
        for row in sorted(rows.keys()):
            types = rows[row]
            type_counts = {}
            for t in types:
                type_counts[t] = type_counts.get(t, 0) + 1
            row_str = ','.join(f"{t}:{c}" for t, c in sorted(type_counts.items()))
            structure_parts.append(f"R{row}=[{row_str}]")
        
        structure_str = '|'.join(structure_parts)
        return hashlib.md5(structure_str.encode()).hexdigest()


class ScreenCache:
    """Multi-level cache for screen analysis results."""
    
    # Similarity thresholds
    PHASH_SIMILARITY_THRESHOLD = 0.95  # 95% similar = same screen
    
    def __init__(self, db):
        self.db = db
        self._memory_cache: Dict[str, Dict] = {}  # content_hash -> screen_data
    
    async def find_matching_screen(self, hashes: Dict[str, str]) -> Optional[Dict]:
        """
        Find a matching screen using multi-level cache strategy.
        Returns existing screen data or None if new.
        """
        content_hash = hashes['content_hash']
        perceptual_hash = hashes['perceptual_hash']
        
        # Level 1: Exact content match (memory)
        if content_hash in self._memory_cache:
            logger.debug(f"L1 cache hit (memory): {content_hash[:8]}")
            return self._memory_cache[content_hash]
        
        # Level 1: Exact content match (database)
        existing = await self.db.fetchone(
            "SELECT * FROM screens WHERE content_hash = ?",
            (content_hash,)
        )
        if existing:
            logger.debug(f"L1 cache hit (DB): {content_hash[:8]}")
            self._memory_cache[content_hash] = existing
            return existing
        
        # Level 2: Perceptual hash match
        if perceptual_hash:
            # Get all screens with perceptual hashes
            candidates = await self.db.fetchall(
                "SELECT * FROM screens WHERE perceptual_hash IS NOT NULL"
            )
            
            for candidate in candidates:
                candidate_phash = candidate.get('perceptual_hash')
                if candidate_phash:
                    similarity = ImageHasher.phash_similarity(
                        perceptual_hash, candidate_phash
                    )
                    if similarity >= self.PHASH_SIMILARITY_THRESHOLD:
                        logger.info(
                            f"L2 cache hit (pHash {similarity:.2%}): "
                            f"{content_hash[:8]} -> {candidate['id'][:8]}"
                        )
                        # Store mapping for future lookups
                        await self._store_hash_mapping(content_hash, candidate['id'])
                        return candidate
        
        # Level 3: Structure hash match (handled by caller with elements)
        return None
    
    async def _store_hash_mapping(self, content_hash: str, screen_id: str):
        """Store a new content hash mapping to existing screen."""
        await self.db.execute(
            """INSERT OR REPLACE INTO screen_hash_mappings 
               (content_hash, screen_id, created_at) VALUES (?, ?, ?)""",
            (content_hash, screen_id, __import__('time').time())
        )
        await self.db.commit()
    
    async def store_screen_analysis(
        self, 
        screen_id: str,
        hashes: Dict[str, str],
        analysis: Dict,
        elements: List[Dict]
    ):
        """Store new screen analysis in cache."""
        content_hash = hashes['content_hash']
        
        screen_data = {
            'id': screen_id,
            'content_hash': content_hash,
            'perceptual_hash': hashes.get('perceptual_hash'),
            'structure_hash': hashes.get('structure_hash'),
            'name': analysis.get('name', 'Unknown'),
            'screen_type': analysis.get('screen_type', 'unknown'),
            'description': analysis.get('description', ''),
            'elements': elements,
        }
        
        self._memory_cache[content_hash] = screen_data
        return screen_data


def compute_content_hash_from_elements(elements: List[Dict]) -> str:
    """Compute a hash based on element properties for quick comparison."""
    element_strs = []
    for el in sorted(elements, key=lambda e: e.get('label', '')):
        el_str = f"{el.get('type')}:{el.get('label')}:{el.get('x')}:{el.get('y')}"
        element_strs.append(el_str)
    combined = '|'.join(element_strs)
    return hashlib.md5(combined.encode()).hexdigest()


def normalize_element_type(raw_type: str) -> str:
    """Normalize element type to standard categories."""
    type_mapping = {
        'button': 'button',
        'btn': 'button',
        'input': 'input',
        'textfield': 'input',
        'edittext': 'input',
        'text': 'text',
        'label': 'text',
        'image': 'image',
        'img': 'image',
        'icon': 'icon',
        'link': 'link',
        'a': 'link',
        'list': 'list',
        'scroll': 'scroll',
        'container': 'container',
        'view': 'container',
        'clickable': 'clickable',
    }
    raw_lower = raw_type.lower()
    return type_mapping.get(raw_lower, raw_lower)


def is_interactive_element(element: Dict) -> bool:
    """Determine if an element is interactive/tappable."""
    interactive_types = {'button', 'input', 'link', 'clickable', 'listitem'}
    el_type = normalize_element_type(element.get('type', ''))
    
    if el_type in interactive_types:
        return True
    
    # Check for clickable flag
    if element.get('clickable') or element.get('enabled'):
        return True
    
    return False


def get_element_signature(element: Dict) -> str:
    """Create a unique signature for an element based on its properties."""
    parts = [
        element.get('type', 'unknown'),
        element.get('label', '')[:50],
        str(element.get('x', 0)),
        str(element.get('y', 0)),
    ]
    return '|'.join(parts)
