
import json
import hashlib
import zlib
from pathlib import Path
from typing import Dict, List

# 256-byte deterministic table for a rolling "gear" hash
_GEAR_TABLE = ([
    0x00000000,0x7f4a7c15,0xfe94f82a,0x81de843f,0xfd29f054,0x82638c41,0x03bd087e,0x7cf7746b,
    0xfb53e0a8,0x84199cbd,0x05c71882,0x7a8d6497,0x067a10fc,0x79306ce9,0xf8eee8d6,0x87a494c3,
    0xf6a7c150,0x89edbd45,0x0833397a,0x7779456f,0x0b8e3104,0x74c44d11,0xf51ac92e,0x8a50b53b,
    0x0df421f8,0x72be5ded,0xf360d9d2,0x8c2aa5c7,0xf0ddd1ac,0x8f97adb9,0x0e492986,0x71035593,
    0xed4f82a0,0x9205feb5,0x13db7a8a,0x6c91069f,0x106672f4,0x6f2c0ee1,0xeef28ade,0x91b8f6cb,
    0x161c6208,0x69561e1d,0xe8889a22,0x97c2e637,0xeb35925c,0x947fee49,0x15a16a76,0x6aeb1663,
    0x1be843f0,0x64a23fe5,0xe57cbbda,0x9a36c7cf,0xe6c1b3a4,0x998bcfb1,0x18554b8e,0x671f379b,
    0xe0bba358,0x9ff1df4d,0x1e2f5b72,0x61652767,0x1d92530c,0x62d82f19,0xe306ab26,0x9c4cd733,
] * 4)

def _gear_update(h: int, b: int) -> int:
    return ((h << 1) + _GEAR_TABLE[b & 0xFF]) & 0xFFFFFFFFFFFFFFFF

def cdc_split(data: bytes, avg: int = 8192, min_size: int = 2048, max_size: int = 16384) -> List[bytes]:
    if not data:
        return []
    bits = max(8, int(round(avg.bit_length() - 1)))  # ~log2(avg)
    mask = (1 << bits) - 1
    chunks: List[bytes] = []
    i, n = 0, len(data)
    while i < n:
        start = i
        end = min(n, start + max_size)
        if end - start <= min_size:
            chunks.append(data[start:end])
            i = end
            continue
        h = 0
        cut = None
        j = start + min_size
        while j < end:
            h = _gear_update(h, data[j])
            if (h & mask) == 0:
                cut = j + 1
                break
            j += 1
        if cut is None:
            cut = end
        chunks.append(data[start:cut])
        i = cut
    return chunks

class TileStore:
    def __init__(self, root: str = "data"):
        self.root = Path(root)
        self.tiles_dir = self.root / "tiles"
        self.manifest_path = self.root / "manifest.json"
        self.tiles_index_path = self.root / "tiles_index.json"
        self.tiles_dir.mkdir(parents=True, exist_ok=True)
        if not self.manifest_path.exists():
            self._save(self.manifest_path, {})
        if not self.tiles_index_path.exists():
            self._save(self.tiles_index_path, {})

    def _load(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, path: Path, obj):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)

    def _hash(self, b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()

    def _norm_key(self, filepath: str) -> str:
        p = Path(filepath)
        try:
            if p.is_absolute():
                return str(p.resolve())
        except Exception:
            pass
        return p.as_posix().lstrip("./")

    def store_file(self, filepath: str, mode: str = "cdc", tile_size: int = 8192,
                   cdc_avg: int = 8192, cdc_min: int = 2048, cdc_max: int = 16384) -> str:
        manifest: Dict[str, List[str]] = self._load(self.manifest_path)
        tiles_index: Dict[str, Dict] = self._load(self.tiles_index_path)

        src = Path(filepath)
        if not src.exists():
            raise FileNotFoundError(f"Input file not found: {filepath}")
        data = src.read_bytes()

        if mode == "fixed":
            chunks = [data[i:i+tile_size] for i in range(0, len(data), tile_size)] if data else [b""]
        elif mode == "cdc":
            chunks = cdc_split(data, avg=cdc_avg, min_size=cdc_min, max_size=cdc_max) or [b""]
        else:
            raise ValueError("mode must be 'fixed' or 'cdc'")

        tile_ids: List[str] = []
        new_tiles = 0
        for chunk in chunks:
            tid = self._hash(chunk)
            tile_path = self.tiles_dir / tid
            if not tile_path.exists():
                comp = zlib.compress(chunk, level=6)
                tile_path.write_bytes(comp)
                tiles_index[tid] = {"raw_size": len(chunk), "stored_size": len(comp), "codec": "zlib"}
                new_tiles += 1
            tile_ids.append(tid)

        key = self._norm_key(filepath)
        manifest[key] = tile_ids
        self._save(self.manifest_path, manifest)
        self._save(self.tiles_index_path, tiles_index)
        return f"Stored {key} in {len(tile_ids)} tiles ({new_tiles} new). Mode={mode}"

    def reconstruct_file(self, original_path: str, output_path: str) -> str:
        manifest: Dict[str, List[str]] = self._load(self.manifest_path)
        key = self._norm_key(original_path)
        tiles = manifest.get(key) or manifest.get(original_path)
        if not tiles:
            raise KeyError(f"File not found in manifest: {original_path} (normalized as {key})")
        out = Path(output_path)
        with open(out, "wb") as f:
            for tid in tiles:
                comp = (self.tiles_dir / tid).read_bytes()
                f.write(zlib.decompress(comp))
        return f"Reconstructed {key} -> {out.as_posix()}"

    def report(self, top_k: int = 10) -> Dict:
        manifest: Dict[str, List[str]] = self._load(self.manifest_path)
        tiles_index: Dict[str, Dict] = self._load(self.tiles_index_path)

        ref_count: Dict[str, int] = {}
        referenced_raw_total = 0
        for tiles in manifest.values():
            for tid in tiles:
                ref_count[tid] = ref_count.get(tid, 0) + 1
                referenced_raw_total += int(tiles_index.get(tid, {}).get("raw_size", 0))

        unique_tiles = list(ref_count.keys())
        unique_raw_total = sum(int(tiles_index.get(tid, {}).get("raw_size", 0)) for tid in unique_tiles)
        unique_stored_total = sum(int(tiles_index.get(tid, {}).get("stored_size", 0)) for tid in unique_tiles)

        hot = sorted(((tid, c) for tid, c in ref_count.items() if c > 1), key=lambda x: x[1], reverse=True)
        top_hot = hot[:top_k]

        return {
            "files": len(manifest),
            "unique_tiles": len(unique_tiles),
            "referenced_tiles": sum(ref_count.values()),
            "hot_tiles": len(hot),
            "referenced_raw_bytes": referenced_raw_total,
            "unique_raw_bytes": unique_raw_total,
            "unique_stored_bytes": unique_stored_total,
            "dedup_saved_bytes": referenced_raw_total - unique_raw_total,
            "compression_saved_bytes": unique_raw_total - unique_stored_total,
            "top_hot": [
                {"tile": tid, "refs": c,
                 "raw": tiles_index.get(tid, {}).get("raw_size", 0),
                 "stored": tiles_index.get(tid, {}).get("stored_size", 0)}
                for tid, c in top_hot
            ],
        }
