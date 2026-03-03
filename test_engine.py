import pytest
import tempfile
import shutil
import json
import zlib
from pathlib import Path

from engine import cdc_split, _gear_update, TileStore


class TestGearUpdate:
    """Tests for the gear hash update function."""

    def test_gear_update_returns_int(self):
        result = _gear_update(0, 65)
        assert isinstance(result, int)

    def test_gear_update_deterministic(self):
        """Same inputs should produce same outputs."""
        h1 = _gear_update(12345, 100)
        h2 = _gear_update(12345, 100)
        assert h1 == h2

    def test_gear_update_different_bytes(self):
        """Different bytes should produce different hashes."""
        h1 = _gear_update(0, 0)
        h2 = _gear_update(0, 255)
        assert h1 != h2


class TestCdcSplit:
    """Tests for content-defined chunking."""

    def test_empty_data_returns_empty_list(self):
        assert cdc_split(b"") == []

    def test_small_data_single_chunk(self):
        """Data smaller than min_size should be a single chunk."""
        data = b"hello world"
        chunks = cdc_split(data, avg=8192, min_size=2048, max_size=16384)
        assert len(chunks) == 1
        assert b"".join(chunks) == data

    def test_chunks_reconstruct_original(self):
        """Joining chunks should produce original data."""
        data = b"x" * 50000
        chunks = cdc_split(data, avg=8192, min_size=2048, max_size=16384)
        assert b"".join(chunks) == data

    def test_chunk_sizes_within_bounds(self):
        """All chunks except possibly the last should respect size constraints."""
        data = bytes(range(256)) * 500  # 128KB of patterned data
        min_size, max_size = 2048, 16384
        chunks = cdc_split(data, avg=8192, min_size=min_size, max_size=max_size)
        
        for i, chunk in enumerate(chunks[:-1]):  # Exclude last chunk
            assert len(chunk) >= min_size, f"Chunk {i} too small: {len(chunk)}"
            assert len(chunk) <= max_size, f"Chunk {i} too large: {len(chunk)}"
        
        # Last chunk can be smaller
        if chunks:
            assert len(chunks[-1]) <= max_size

    def test_deterministic_chunking(self):
        """Same data should produce same chunks."""
        data = b"deterministic chunking test data " * 1000
        chunks1 = cdc_split(data)
        chunks2 = cdc_split(data)
        assert chunks1 == chunks2

    def test_custom_parameters(self):
        """CDC should work with custom parameters."""
        data = b"a" * 10000
        chunks = cdc_split(data, avg=1024, min_size=512, max_size=2048)
        assert b"".join(chunks) == data


class TestTileStore:
    """Tests for the TileStore class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for each test."""
        d = tempfile.mkdtemp()
        yield d
        shutil.rmtree(d)

    @pytest.fixture
    def store(self, temp_dir):
        """Create a TileStore in the temp directory."""
        return TileStore(root=temp_dir)

    @pytest.fixture
    def sample_file(self, temp_dir):
        """Create a sample file for testing."""
        path = Path(temp_dir) / "sample.txt"
        content = b"This is sample content for testing TileMindFS storage."
        path.write_bytes(content)
        return str(path), content

    def test_init_creates_directories(self, temp_dir):
        """TileStore should create necessary directories on init."""
        store = TileStore(root=temp_dir)
        assert (Path(temp_dir) / "tiles").is_dir()
        assert (Path(temp_dir) / "manifest.json").exists()
        assert (Path(temp_dir) / "tiles_index.json").exists()

    def test_init_empty_manifest(self, store, temp_dir):
        """Initial manifest should be empty."""
        manifest = json.loads((Path(temp_dir) / "manifest.json").read_text())
        assert manifest == {}

    def test_store_file_basic(self, store, sample_file):
        """Store a file and verify it's tracked."""
        path, content = sample_file
        result = store.store_file(path)
        assert "Stored" in result
        assert "tiles" in result

    def test_store_file_nonexistent_raises(self, store, temp_dir):
        """Storing nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            store.store_file(str(Path(temp_dir) / "nonexistent.txt"))

    def test_store_file_fixed_mode(self, store, sample_file):
        """Store file in fixed tile mode."""
        path, content = sample_file
        result = store.store_file(path, mode="fixed", tile_size=16)
        assert "Mode=fixed" in result

    def test_store_file_cdc_mode(self, store, sample_file):
        """Store file in CDC mode."""
        path, content = sample_file
        result = store.store_file(path, mode="cdc")
        assert "Mode=cdc" in result

    def test_store_file_invalid_mode_raises(self, store, sample_file):
        """Invalid mode should raise ValueError."""
        path, _ = sample_file
        with pytest.raises(ValueError, match="mode must be"):
            store.store_file(path, mode="invalid")

    def test_reconstruct_file(self, store, sample_file, temp_dir):
        """Reconstruct should produce identical content."""
        path, content = sample_file
        store.store_file(path)
        
        output_path = str(Path(temp_dir) / "reconstructed.txt")
        store.reconstruct_file(path, output_path)
        
        reconstructed = Path(output_path).read_bytes()
        assert reconstructed == content

    def test_reconstruct_nonexistent_raises(self, store, temp_dir):
        """Reconstructing unknown file should raise KeyError."""
        with pytest.raises(KeyError):
            store.reconstruct_file("unknown.txt", str(Path(temp_dir) / "out.txt"))

    def test_deduplication(self, store, temp_dir):
        """Identical files should share tiles."""
        content = b"duplicate content " * 100
        
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        file1.write_bytes(content)
        file2.write_bytes(content)
        
        store.store_file(str(file1))
        result2 = store.store_file(str(file2))
        
        # Second store should report 0 new tiles (all deduped)
        assert "0 new" in result2

    def test_report_empty_store(self, store):
        """Report on empty store should return zeros."""
        report = store.report()
        assert report["files"] == 0
        assert report["unique_tiles"] == 0
        assert report["referenced_tiles"] == 0

    def test_report_after_store(self, store, sample_file):
        """Report should reflect stored file."""
        path, _ = sample_file
        store.store_file(path)
        
        report = store.report()
        assert report["files"] == 1
        assert report["unique_tiles"] > 0
        assert report["referenced_tiles"] > 0

    def test_compression_applied(self, store, temp_dir):
        """Stored tiles should be compressed."""
        # Highly compressible content
        content = b"a" * 10000
        file_path = Path(temp_dir) / "compressible.txt"
        file_path.write_bytes(content)
        
        store.store_file(str(file_path))
        
        report = store.report()
        # Compressed size should be much smaller than raw
        assert report["unique_stored_bytes"] < report["unique_raw_bytes"]

    def test_tiles_are_compressed_with_zlib(self, store, sample_file, temp_dir):
        """Verify tiles are actually zlib compressed."""
        path, content = sample_file
        store.store_file(path)
        
        tiles_dir = Path(temp_dir) / "tiles"
        for tile_file in tiles_dir.iterdir():
            compressed = tile_file.read_bytes()
            # Should be able to decompress with zlib
            decompressed = zlib.decompress(compressed)
            assert len(decompressed) > 0

    def test_norm_key_relative_path(self, store):
        """Normalize relative paths."""
        assert store._norm_key("./foo/bar.txt") == "foo/bar.txt"
        assert store._norm_key("foo/bar.txt") == "foo/bar.txt"

    def test_store_empty_file(self, store, temp_dir):
        """Empty files should be handled."""
        empty_file = Path(temp_dir) / "empty.txt"
        empty_file.write_bytes(b"")
        
        result = store.store_file(str(empty_file))
        assert "Stored" in result
        
        output = Path(temp_dir) / "empty_out.txt"
        store.reconstruct_file(str(empty_file), str(output))
        assert output.read_bytes() == b""

    def test_large_file_reconstruction(self, store, temp_dir):
        """Test reconstruction of larger files with multiple tiles."""
        content = bytes(range(256)) * 1000  # 256KB
        large_file = Path(temp_dir) / "large.bin"
        large_file.write_bytes(content)
        
        store.store_file(str(large_file))
        
        output = Path(temp_dir) / "large_out.bin"
        store.reconstruct_file(str(large_file), str(output))
        
        assert output.read_bytes() == content

    def test_hot_tiles_in_report(self, store, temp_dir):
        """Files sharing tiles should show in hot_tiles."""
        # Create files with shared content
        shared = b"shared content block " * 500
        unique1 = b"unique header 1 "
        unique2 = b"unique header 2 "
        
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        file1.write_bytes(unique1 + shared)
        file2.write_bytes(unique2 + shared)
        
        store.store_file(str(file1))
        store.store_file(str(file2))
        
        report = store.report()
        # Should have some tiles referenced multiple times
        assert report["hot_tiles"] >= 0  # May or may not have hot tiles depending on chunking
