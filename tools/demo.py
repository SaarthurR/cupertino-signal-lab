"""Serve the saved, team-only Signal Learner demo locally; only the console's optional live test needs SUMO."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time

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

TEST_SEED = 200  # one held-out traffic day the learner never saw
TEST_LOCK = threading.Lock()


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


def live_test(seed=TEST_SEED):
    """Old Wolfe timing vs the learner plan on one traffic day; returns what the console shows, never raises."""
    files = [ROOT/'worlds/wolfe/routes.rou.xml', ROOT/'roads/wolfe/old_timing.add.xml', ROOT/'reports/learner/wolfe/plan.add.xml']
    missing = [str(path.relative_to(ROOT)) for path in files if not path.is_file()]
    if missing:
        return dict(ok=False, reason='Simulation inputs are not on this laptop (generated, not in Git): ' + ', '.join(missing))
    if str(ROOT/'src') not in sys.path:
        sys.path.insert(0, str(ROOT/'src'))
    try:
        from learner import road
    except Exception as exc:  # no SUMO, PyYAML or SUMO_HOME in this Python
        return dict(ok=False, reason=f'The simulator (SUMO and its Python packages) is not installed for this Python ({exc}).')
    start = time.monotonic()
    try:
        results = road.many([(road.load('wolfe'), files[0], timing, seed, False, (), 120) for timing in files[1:]])
    except Exception as exc:
        return dict(ok=False, reason=f'The simulation failed: {type(exc).__name__}: {exc}')
    old, plan = (dict(delay_s=round(stats['all_requested_delay_s'], 1), unfinished=stats['unfinished']) for stats, _ in results)
    return dict(ok=True, seed=seed, old=old, learner=plan, wall_s=round(time.monotonic()-start, 1))


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.md': 'text/plain; charset=utf-8',
                      '.txt': 'text/plain; charset=utf-8', '.yaml': 'text/plain; charset=utf-8',
                      '.csv': 'text/csv; charset=utf-8', '.xml': 'application/xml'}

    def list_directory(self, path):
        self.send_error(404)

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            self.log_message('Client disconnected during transfer')

    def do_POST(self):
        if self.path != '/api/test-run':
            return self.send_error(501, 'Unsupported method')
        if not TEST_LOCK.acquire(blocking=False):
            return self.send_json(409, dict(ok=False, reason='A test is already running.'))
        try:
            self.send_json(200, live_test())
        finally:
            TEST_LOCK.release()

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
