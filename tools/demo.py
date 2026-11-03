"""Serve the saved, team-only Signal Learner demo locally; no simulation dependencies."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DECK = Path('dashboard/signal-learner')
ASSETS = {name: DECK/name for name in (
    'index.html', 'signal-learner.pdf', 'wolfe_side_by_side.mp4', 'wolfe_side_by_side_poster.png')}
ASSETS.update({f'cards/{name}.md': Path(f'reports/learner/{name}/card.md') for name in ('wolfe', 'deanza')})
ASSETS['runbook.txt'] = Path('docs/DEMO.md')


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


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.md': 'text/plain; charset=utf-8',
                      '.txt': 'text/plain; charset=utf-8'}

    def list_directory(self, path):
        self.send_error(404)

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            self.log_message('Client disconnected during transfer')


def server(folder, port=0):
    return ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=str(folder)))


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
                print(f'Slides: {url}/\nVideo: {url}/wolfe_side_by_side.mp4\nPDF: {url}/signal-learner.pdf', flush=True)
                print(f'Engineer cards: {url}/cards/wolfe.md  {url}/cards/deanza.md', flush=True)
                print(f'Runbook: {url}/runbook.txt\nArrows: slides. N: notes. Ctrl-C: stop.', flush=True)
                httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nDemo stopped.')
    except OSError as exc:
        parser.exit(1, f'Demo could not start: {exc}\n')


if __name__ == '__main__':
    main()
