import argparse
from . import pipeline, demand, baseline, optimize, evaluate


def main():
    parser = argparse.ArgumentParser(description="Cupertino Signal Lab")
    verbs = parser.add_subparsers(dest="verb", required=True)
    for name in ("build-net", "build-demand", "check-demand", "baseline", "optimize", "eval", "bench", "dashboard"):
        sub = verbs.add_parser(name)
        if name == 'dashboard':
            sub.add_argument('--skip-video', action='store_true', help='Build only the page and deck from saved results')
        if name == "optimize":
            sub.add_argument("--trials", type=int, default=None)
        if name in ('optimize', 'eval'):
            sub.add_argument('--version', type=int, choices=(3, 4), default=3)
    args = parser.parse_args()
    if args.verb == "optimize" and args.trials is None:
        args.trials = 60 if args.version == 4 else 300
    module = evaluate if args.verb == 'eval' else optimize if args.verb == 'optimize' else baseline if args.verb == 'baseline' else demand if args.verb in ('build-demand', 'check-demand') else pipeline
    getattr(module, args.verb.replace("-", "_"))(**({"trials": args.trials, "version": args.version} if args.verb == "optimize" else {"version": args.version} if args.verb == "eval" else {"skip_video": args.skip_video} if args.verb == "dashboard" else {}))


if __name__ == "__main__":
    main()
