
import os
import hashlib
import zlib
import json

DATA_DIR = "data"
TILE_DIR = os.path.join(DATA_DIR, "tiles")
MANIFEST = os.path.join(DATA_DIR, "manifest.json")

class TileStore:
    def __init__(self):
        os.makedirs(TILE_DIR, exist_ok=True)
        if not os.path.exists(MANIFEST):
            with open(MANIFEST, "w") as f:
                json.dump({}, f)

    def _hash(self, data):
        return hashlib.sha256(data).hexdigest()

    def store_file(self, filepath):
        with open(filepath, "rb") as f:
            data = f.read()

        tile_hash = self._hash(data)
        tile_path = os.path.join(TILE_DIR, tile_hash)

        if not os.path.exists(tile_path):
            compressed = zlib.compress(data)
            with open(tile_path, "wb") as t:
                t.write(compressed)

        with open(MANIFEST, "r") as f:
            manifest = json.load(f)

        manifest[filepath] = [tile_hash]

        with open(MANIFEST, "w") as f:
            json.dump(manifest, f, indent=2)

        return f"Stored {filepath} in 1 tile."

    def reconstruct_file(self, original, output):
        with open(MANIFEST, "r") as f:
            manifest = json.load(f)

        if original not in manifest:
            raise KeyError("File not found in manifest")

        tile_hash = manifest[original][0]
        tile_path = os.path.join(TILE_DIR, tile_hash)

        with open(tile_path, "rb") as t:
            compressed = t.read()

        data = zlib.decompress(compressed)

        with open(output, "wb") as out:
            out.write(data)

        return f"Reconstructed {original} -> {output}"

    def report(self):
        with open(MANIFEST, "r") as f:
            manifest = json.load(f)

        files = len(manifest)
        unique_tiles = len(os.listdir(TILE_DIR))

        return f"Files tracked: {files}\nUnique tiles: {unique_tiles}"
