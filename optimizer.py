
import time
from engine import TileStore

def _fmt_bytes(n: int) -> str:
    units = ["B","KB","MB","GB","TB"]
    x = float(n)
    for u in units:
        if x < 1024 or u == units[-1]:
            return f"{x:.2f} {u}" if u != "B" else f"{int(x)} B"
        x /= 1024
    return f"{x:.2f} TB"

class Optimizer:
    def __init__(self, root="data"):
        self.store = TileStore(root=root)

    def analyze(self, top_k=10):
        r = self.store.report(top_k=top_k)
        print("=== Optimization Report (V2) ===")
        print(f"Files tracked: {r['files']}")
        print(f"Unique tiles: {r['unique_tiles']} | Referenced tiles: {r['referenced_tiles']} | Hot tiles: {r['hot_tiles']}")
        print(f"Referenced raw:      {_fmt_bytes(r['referenced_raw_bytes'])}")
        print(f"Unique raw:          {_fmt_bytes(r['unique_raw_bytes'])}")
        print(f"Stored (compressed): {_fmt_bytes(r['unique_stored_bytes'])}")
        print(f"Dedup saved:         {_fmt_bytes(r['dedup_saved_bytes'])}")
        print(f"Compression saved:   {_fmt_bytes(r['compression_saved_bytes'])}")
        if r["top_hot"]:
            print("Top shared tiles:")
            for t in r["top_hot"]:
                print(f"  {t['tile'][:12]}… refs={t['refs']} raw={t['raw']}B stored={t['stored']}B")
        else:
            print("Top shared tiles: (none)")

    def run_loop(self, interval=10, top_k=10):
        print("Autonomous optimization loop started (Ctrl+C to stop).")
        while True:
            self.analyze(top_k=top_k)
            time.sleep(interval)
