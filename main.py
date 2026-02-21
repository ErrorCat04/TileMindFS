
import argparse
from engine import TileStore
from optimizer import Optimizer

def main():
    parser = argparse.ArgumentParser(
        prog="TileMindFS",
        description="Tile-based dedup + compression storage (MVP V2)."
    )
    sub = parser.add_subparsers(dest="command")

    store_p = sub.add_parser("store", help="Store a file into tiles")
    store_p.add_argument("file")

    rec_p = sub.add_parser("reconstruct", help="Reconstruct a stored file")
    rec_p.add_argument("original")
    rec_p.add_argument("output")

    sub.add_parser("report", help="Print storage report")

    opt_p = sub.add_parser("optimize", help="Run optimizer loop")
    opt_p.add_argument("--interval", type=int, default=5)

    args = parser.parse_args()
    store = TileStore()

    if args.command == "store":
        print(store.store_file(args.file))
    elif args.command == "reconstruct":
        print(store.reconstruct_file(args.original, args.output))
    elif args.command == "report":
        print(store.report())
    elif args.command == "optimize":
        Optimizer().run_loop(args.interval)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
