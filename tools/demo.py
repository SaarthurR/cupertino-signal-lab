"""Serve the saved, team-only Signal Learner demo locally; only the console's live simulation needs SUMO."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import multiprocessing
from pathlib import Path
import shutil
import tempfile
import threading
from queue import Empty
import time

from tools import live_sim

ROOT = Path(__file__).resolve().parents[1]
DECK = Path('dashboard/signal-learner')
ASSETS = {name: DECK/name for name in (
    'index.html', 'signal-learner.pdf', 'wolfe_side_by_side.mp4', 'wolfe_side_by_side_poster.png')}
ASSETS.update({f'cards/{name}.md': Path(f'reports/learner/{name}/card.md') for name in ('wolfe', 'deanza')})
ASSETS['runbook.txt'] = Path('docs/DEMO.md')
ASSETS.update({f'console/{name}': Path('dashboard/console')/name for name in ('index.html', 'console.css', 'console.js')})
for corridor in ('wolfe', 'deanza'):
    ASSETS[f'console/data/{corridor}/road.yaml'] = Path(f'roads/{corridor}/road.yaml')
    ASSETS.update({f'console/data/{corridor}/{name}': Path(f'reports/learner/{corridor}/{name}')
                   for name in ('card.json', 'plan.add.xml', 'pattern.csv', 'practice.json')})
    ASSETS.update({f'console/data/{corridor}/feed{seed}.csv': Path(f'reports/learner/{corridor}/feed/seed{seed}/feed.csv')
                   for seed in range(3)})
ASSETS.update({f'console/data/heldout/{name}': Path(f'reports/learner_heldout/{name}') for name in ('results.csv', 'go_back.json')})
ASSETS['console/data/check-rule.txt'] = Path('src/learner/check.py')
ASSETS['console/data/deanza/posthoc.json'] = Path('reports/learner_story/deanza_posthoc.json')
ASSETS.update({f'console/geo/{name}': Path('dashboard/console/geo')/name for name in ('wolfe.json', 'deanza.json', live_sim.RECORDING.name)})

SPEEDS = (60, 120, 240)  # simulated seconds per real second
SIM = dict(speed=120, paused=False)  # what the browser last asked for; one run at a time
SIM_LOCK = threading.Lock()
SIM_MAX_S = 15*60  # a paused or forgotten run is stopped after this long
FPS = 30  # frames sent per real second; the browser draws in between
WORKER = live_sim.worker


def live_ready():
    """None when this Python can run SUMO live, else the reason; the console then plays the recording."""
    if not live_sim.ROUTES.is_file():
        return 'The simulation inputs are not on this laptop (worlds/wolfe/routes.rou.xml is generated, not in Git).'
    missing = [name for name in ('libsumo', 'traci', 'yaml', 'sumolib') if importlib.util.find_spec(name) is None]
    return f'The simulator is not installed for this Python (missing {", ".join(missing)}).' if missing else None


def prepare(folder):
    """Copy only presentation assets; never serve the repository or its data directories."""
    for source in ASSETS.values():
        path = (ROOT/source).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
            raise FileNotFoundError(f'Missing or unsafe demo asset: {source}. Restore it from the repository.')
    for target, source in ASSETS.items():
        dest = Path(folder)/target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/source, dest)
        if target.startswith('cards/'):
            note = ('Historical original-study card. Presentation annotations do not change its recorded decision.\n\n')
            if target == 'cards/deanza.md':
                note += ('Reading note: the selected timing is unchanged. The forecast below belongs to a rejected candidate, '
                         'not the selected plan. The original "no clear gain" sentence was inaccurate: the candidate '
                         'failed the teleport feasibility constraint. The archived source is preserved below.\n\n')
            dest.write_text(note + dest.read_text(encoding='utf-8'), encoding='utf-8')


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.md': 'text/plain; charset=utf-8',
                      '.txt': 'text/plain; charset=utf-8', '.yaml': 'text/plain; charset=utf-8',
                      '.csv': 'text/csv; charset=utf-8', '.xml': 'application/xml', '.gz': 'application/octet-stream'}

    def list_directory(self, path):
        self.send_error(404)

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            self.log_message('Client disconnected during transfer')

    def do_GET(self):
        if self.path == '/api/sim/stream':
            return self.stream()
        return super().do_GET()

    def do_POST(self):
        if self.path != '/api/sim/control':
            return self.send_error(501, 'Unsupported method')
        try:
            length = int(self.headers.get('Content-Length', 0))
            asked = json.loads(self.rfile.read(length)) if 0 < length <= 200 else None
            speed, paused = asked.get('speed', SIM['speed']), asked.get('paused', SIM['paused'])
            if speed not in SPEEDS or not isinstance(paused, bool):
                raise ValueError
        except (ValueError, AttributeError):
            return self.send_json(400, dict(ok=False, reason=f'Send JSON with speed in {SPEEDS} and/or paused true/false.'))
        SIM.update(speed=speed, paused=paused)
        self.send_json(200, dict(ok=True, **SIM))

    def stream(self):
        """Server-Sent Events: both Wolfe plans run live in SUMO, same traffic, same clock, paced to SIM['speed']."""
        reason = live_ready()
        if reason:
            return self.send_json(503, dict(ok=False, reason=reason))
        if not SIM_LOCK.acquire(blocking=False):
            return self.send_json(409, dict(ok=False, reason='A simulation is already running.'))
        context = multiprocessing.get_context('spawn')
        stop, arms = context.Event(), list(live_sim.TIMINGS)
        queues = [context.Queue(maxsize=FPS*8) for _ in arms]
        workers = [context.Process(target=WORKER, args=(arm, queue, stop), daemon=True) for arm, queue in zip(arms, queues)]
        SIM.update(speed=120, paused=False)
        try:
            for process in workers:
                process.start()
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.event('status', dict(phase='starting'))
            self.pace(arms, queues, time.monotonic()+SIM_MAX_S)
        except (BrokenPipeError, ConnectionResetError):
            self.log_message('Browser left the simulation; stopped it')
        finally:
            stop.set()
            for process in workers:
                process.join(3)
                if process.is_alive():
                    process.terminate()
                    process.join(3)
            SIM_LOCK.release()

    def pace(self, arms, queues, deadline):
        last, done, due, sent = {}, {}, time.monotonic(), -10**9
        while len(done) < len(arms):
            if time.monotonic() > deadline:
                return self.event('failed', dict(reason='The run took too long and was stopped.'))
            if SIM['paused']:
                self.wfile.write(b': paused\n\n')  # a write per second notices a closed browser
                self.wfile.flush()
                time.sleep(0.5)
                due = time.monotonic()
                continue
            for arm, queue in zip(arms, queues):
                if arm in done:
                    continue
                try:
                    item = queue.get(timeout=120)
                except Empty:
                    return self.event('failed', dict(reason='The simulator stopped answering.'))
                if 'error' in item:
                    return self.event('failed', dict(reason=f'The simulation failed: {item["error"]}'))
                if 'done' in item:
                    done[arm] = item['done']
                else:
                    last[arm] = item
            if not last:
                continue
            t = max(frame['t'] for frame in last.values())
            # After 6:30 PM only the cars already on the road finish; play that part 4x faster.
            speed = SIM['speed']*(4 if any(frame['drain'] for frame in last.values()) else 1)
            due = max(due+1/speed, time.monotonic()-0.25)  # never burst to catch up after a stall
            if due > time.monotonic():
                time.sleep(due-time.monotonic())
            if t-sent >= speed/FPS or len(done) == len(arms):
                self.event('frame', dict(t=t, **{arm: last[arm] for arm in arms if arm in last}))
                sent = t
        self.event('end', dict(seed=live_sim.SEED, **done))

    def event(self, kind, value):
        self.wfile.write(f'event: {kind}\ndata: {json.dumps(value, separators=(",", ":"))}\n\n'.encode())
        self.wfile.flush()

    def send_json(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Server(ThreadingHTTPServer):
    request_queue_size = 32  # The console fetches its saved inputs concurrently.


def server(folder, port=0):
    return Server(('127.0.0.1', port), partial(Handler, directory=str(folder)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=0, help='localhost port; default: an available port')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('--port must be between 0 and 65535')
    try:
        with tempfile.TemporaryDirectory(prefix='signal-learner-demo-') as folder:
            prepare(folder)
            with server(folder, args.port) as httpd:
                url = f'http://127.0.0.1:{httpd.server_port}'
                print('Simulation only. VTA data: cite "VTA, 2024 CMP Monitoring and Conformance Report".', flush=True)
                print(f'Slides: {url}/\nEngineer console: {url}/console/', flush=True)
                print(f'Video: {url}/wolfe_side_by_side.mp4\nPDF: {url}/signal-learner.pdf', flush=True)
                print(f'Engineer cards: {url}/cards/wolfe.md  {url}/cards/deanza.md', flush=True)
                print(f'Runbook: {url}/runbook.txt\nArrows: slides. N: notes. Ctrl-C: stop.', flush=True)
                httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nDemo stopped.')
    except OSError as exc:
        parser.exit(1, f'Demo could not start: {exc}\n')


if __name__ == '__main__':
    main()
