
import argparse
from engine import TileStore
from optimizer import Optimizer, _fmt_bytes

def main():
    p = argparse.ArgumentParser(prog="TileMindFS", description="Tile-based dedup + compression storage (MVP V2).")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("store", help="Store a file into tiles")
    s.add_argument("path")
    s.add_argument("--mode", choices=["cdc","fixed"], default="cdc")
    s.add_argument("--tile-size", type=int, default=8192)
    s.add_argument("--avg", type=int, default=8192)
    s.add_argument("--min", dest="min_size", type=int, default=2048)
    s.add_argument("--max", dest="max_size", type=int, default=16384)

    r = sub.add_parser("reconstruct", help="Reconstruct a stored file")
    r.add_argument("original")
    r.add_argument("output")

    rep = sub.add_parser("report", help="Print a storage report")
    rep.add_argument("--top", type=int, default=10)

    opt = sub.add_parser("optimize", help="Run the autonomous optimizer loop")
    opt.add_argument("--interval", type=int, default=10)
    opt.add_argument("--top", type=int, default=10)

    args = p.parse_args()
    store = TileStore()

    if args.cmd == "store":
        print(store.store_file(args.path, mode=args.mode, tile_size=args.tile_size,
                             cdc_avg=args.avg, cdc_min=args.min_size, cdc_max=args.max_size))
    elif args.cmd == "reconstruct":
        print(store.reconstruct_file(args.original, args.output))
    elif args.cmd == "report":
        rep = store.report(top_k=args.top)
        print("=== Report ===")
        print(f"Files tracked: {rep['files']}")
        print(f"Unique tiles: {rep['unique_tiles']} | Referenced tiles: {rep['referenced_tiles']} | Hot tiles: {rep['hot_tiles']}")
        print(f"Referenced raw: {_fmt_bytes(rep['referenced_raw_bytes'])}")
        print(f"Unique raw:     {_fmt_bytes(rep['unique_raw_bytes'])}")
        print(f"Stored bytes:   {_fmt_bytes(rep['unique_stored_bytes'])}")
        print(f"Dedup saved:    {_fmt_bytes(rep['dedup_saved_bytes'])}")
        print(f"Compress saved: {_fmt_bytes(rep['compression_saved_bytes'])}")
        if rep["top_hot"]:
            print("Top shared tiles:")
            for t in rep["top_hot"]:
                print(f"  {t['tile'][:12]}… refs={t['refs']} raw={t['raw']}B stored={t['stored']}B")
    elif args.cmd == "optimize":
        Optimizer().run_loop(interval=args.interval, top_k=args.top)

if __name__ == "__main__":
    main()
