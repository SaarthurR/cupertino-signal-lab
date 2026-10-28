import argparse
from . import pipeline


def main():
    parser = argparse.ArgumentParser(description="Cupertino Signal Lab")
    verbs = parser.add_subparsers(dest="verb", required=True)
    for name in ("build-net", "build-demand", "check-demand", "baseline", "optimize", "eval", "bench", "dashboard"):
        sub = verbs.add_parser(name)
        if name == "optimize":
            sub.add_argument("--trials", type=int, default=200)
    args = parser.parse_args()
    getattr(pipeline, args.verb.replace("-", "_"))(**({"trials": args.trials} if args.verb == "optimize" else {}))


if __name__ == "__main__":
    main()
