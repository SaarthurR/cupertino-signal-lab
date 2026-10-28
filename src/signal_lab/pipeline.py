import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(os.environ["SUMO_HOME"]) / "tools"
BIN = Path(os.environ["SUMO_HOME"]) / "bin"


def run(args):
    result = subprocess.run([str(a) for a in args], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def tool(name, *args):
    return run([sys.executable, TOOLS / name, *args])


def bench():
    with tempfile.TemporaryDirectory() as tmp:
        net = Path(tmp) / "bench.net.xml"
        routes = Path(tmp) / "bench.rou.xml"
        run([BIN / "netgenerate", "--grid", "--grid.number", "3", "--tls.guess", "--tls.default-type", "actuated", "-o", net])
        tool("randomTrips.py", "-n", net, "-r", routes, "-e", "3600", "-p", "2", "--seed", "0")
        start = time.monotonic()
        output = run([BIN / "sumo", "-n", net, "-r", routes, "-e", "3600", "--no-step-log", "--duration-log.statistics"])
        seconds = time.monotonic() - start
    report = f"# M0 benchmark\n\nOne simulation hour: {seconds:.3f} wall seconds.\n\nInitial scaffold: synthetic 3×3 actuated grid, not the corridor. Re-run after M4 for the actual optimization budget.\n\n```\n{output}\n```\n"
    (ROOT / "reports/bench.md").write_text(report)
    print(f"bench: {seconds:.3f} seconds (synthetic scaffold; corridor benchmark follows M4)")


def pending():
    raise SystemExit("Milestone not implemented yet")


build_net = build_demand = check_demand = baseline = optimize = eval = dashboard = pending
