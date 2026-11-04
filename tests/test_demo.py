from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tools import demo


class DemoTests(unittest.TestCase):
    def test_historical_card_view_clarifies_rejection_without_editing_source(self):
        original = (demo.ROOT/'reports/learner/deanza/card.md').read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            demo.prepare(temp)
            shown = (Path(temp)/'cards/deanza.md').read_text()
            self.assertIn('forecast below belongs to a rejected candidate', shown)
            self.assertIn('Presentation annotations do not change its recorded decision', shown)
            self.assertTrue(shown.endswith(original.decode('utf-8')))
        self.assertEqual((demo.ROOT/'reports/learner/deanza/card.md').read_bytes(), original)

    def test_cancelled_transfers_are_logged_and_other_io_errors_propagate(self):
        handler = demo.Handler.__new__(demo.Handler)
        for error in (BrokenPipeError, ConnectionResetError):
            output = mock.Mock()
            output.write.side_effect = error('client left')
            with mock.patch.object(handler, 'log_message') as log:
                handler.copyfile(io.BytesIO(b'video'), output)
                log.assert_called_once_with('Client disconnected during transfer')
        output.write.side_effect = OSError('disk error')
        with self.assertRaisesRegex(OSError, 'disk error'):
            handler.copyfile(io.BytesIO(b'video'), output)

    def test_only_allowlisted_assets_are_copied_and_missing_files_fail_before_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            root, dest = Path(temp)/'source', Path(temp)/'demo'
            root.mkdir()
            (root/'deck.html').write_text('slides')
            (root/'.env').write_text('private')
            with mock.patch.object(demo, 'ROOT', root), \
                    mock.patch.object(demo, 'ASSETS', {'index.html': Path('deck.html')}):
                demo.prepare(dest)
                self.assertEqual([p.name for p in dest.iterdir()], ['index.html'])
                self.assertEqual((dest/'index.html').read_text(), 'slides')
            with mock.patch.object(demo, 'ROOT', root), \
                    mock.patch.object(demo, 'ASSETS', {'index.html': Path('deck.html'), 'missing': Path('missing')}):
                with self.assertRaisesRegex(FileNotFoundError, 'Missing or unsafe demo asset'):
                    demo.prepare(Path(temp)/'unused')
                self.assertFalse((Path(temp)/'unused').exists())
            (root/'outside').symlink_to(dest/'index.html')
            with mock.patch.object(demo, 'ROOT', root), \
                    mock.patch.object(demo, 'ASSETS', {'index.html': Path('outside')}):
                with self.assertRaises(FileNotFoundError):
                    demo.prepare(Path(temp)/'unused')

    def test_real_assets_http_head_and_denied_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            demo.prepare(temp)
            with demo.server(temp) as httpd:
                worker = threading.Thread(target=httpd.serve_forever, daemon=True)
                worker.start()
                url = f'http://127.0.0.1:{httpd.server_port}'
                try:
                    self.assertEqual(httpd.server_address[0], '127.0.0.1')
                    for path in ('/', '/signal-learner.pdf', '/wolfe_side_by_side.mp4',
                                 '/wolfe_side_by_side_poster.png', '/cards/wolfe.md',
                                 '/cards/deanza.md', '/runbook.txt'):
                        with urlopen(url+path) as response:
                            self.assertEqual(response.status, 200)
                            self.assertTrue(response.read())
                    with urlopen(Request(url+'/cards/wolfe.md', method='HEAD')) as response:
                        self.assertEqual(response.read(), b'')
                        self.assertIn('text/plain', response.headers['Content-Type'])
                    for path in ('/.git/config', '/data/', '/cards/', '/../README.md', '/%2e%2e/README.md'):
                        with self.assertRaises(HTTPError) as caught:
                            urlopen(url+path)
                        self.assertEqual(caught.exception.code, 404)
                        caught.exception.close()
                    with self.assertRaises(HTTPError) as caught:
                        urlopen(Request(url+'/', data=b'no writes'))
                    self.assertEqual(caught.exception.code, 501)
                    caught.exception.close()
                finally:
                    httpd.shutdown()
                    worker.join()

    def test_console_and_its_data_copies_are_served_but_repo_files_are_not(self):
        with tempfile.TemporaryDirectory() as temp:
            demo.prepare(temp)
            with demo.server(temp) as httpd:
                worker = threading.Thread(target=httpd.serve_forever, daemon=True)
                worker.start()
                url = f'http://127.0.0.1:{httpd.server_port}'
                try:
                    for path in ('/console/', '/console/console.js', '/console/console.css'):
                        with urlopen(url+path) as response:
                            self.assertEqual(response.status, 200)
                    for road in ('wolfe', 'deanza'):
                        for name in ('card.json', 'plan.add.xml', 'pattern.csv', 'practice.json', 'road.yaml',
                                     'feed0.csv', 'feed1.csv', 'feed2.csv'):
                            with urlopen(f'{url}/console/data/{road}/{name}') as response:
                                self.assertEqual(response.read(), (demo.ROOT/demo.ASSETS[f'console/data/{road}/{name}']).read_bytes())
                    for path in ('/console/data/heldout/results.csv', '/console/data/heldout/go_back.json',
                                 '/console/data/deanza/posthoc.json', '/console/data/check-rule.txt'):
                        with urlopen(url+path) as response:
                            self.assertEqual(response.status, 200)
                    for path in ('/console/data/', '/console/../README.md', '/reports/learner/wolfe/card.json',
                                 '/roads/wolfe/road.yaml', '/tools/demo.py', '/worlds/wolfe/routes.rou.xml'):
                        with self.assertRaises(HTTPError) as caught:
                            urlopen(url+path)
                        self.assertEqual(caught.exception.code, 404)
                        caught.exception.close()
                finally:
                    httpd.shutdown()
                    worker.join()

    def test_test_run_endpoint_returns_the_run_and_refuses_overlap(self):
        result = dict(ok=True, seed=200, old=dict(delay_s=856.0, unfinished=931),
                      learner=dict(delay_s=650.2, unfinished=218), wall_s=9.5)
        with tempfile.TemporaryDirectory() as temp, demo.server(temp) as httpd, \
                mock.patch.object(demo, 'live_test', return_value=result) as run:
            worker = threading.Thread(target=httpd.serve_forever, daemon=True)
            worker.start()
            url = f'http://127.0.0.1:{httpd.server_port}/api/test-run'
            try:
                with urlopen(Request(url, method='POST')) as response:
                    self.assertEqual(response.headers['Content-Type'], 'application/json')
                    self.assertEqual(json.loads(response.read()), result)
                run.assert_called_once_with()
                started, release = threading.Event(), threading.Event()
                def blocked_run():
                    started.set()
                    if not release.wait(5):
                        raise TimeoutError('test did not release the simulation')
                    return result
                run.side_effect = blocked_run
                responses = []
                def request_run():
                    with urlopen(Request(url, method='POST'), timeout=10) as response:
                        responses.append(json.loads(response.read()))
                first = threading.Thread(target=request_run)
                first.start()
                try:
                    self.assertTrue(started.wait(5))
                    with self.assertRaises(HTTPError) as caught:
                        urlopen(Request(url, method='POST'), timeout=5)
                    self.assertEqual(caught.exception.code, 409)
                    self.assertFalse(json.loads(caught.exception.read())['ok'])
                    caught.exception.close()
                    self.assertEqual(run.call_count, 2)
                    # Static requests remain responsive while SUMO is busy.
                    with self.assertRaises(HTTPError) as get:
                        urlopen(url.replace('/api/test-run', '/missing'), timeout=5)
                    self.assertEqual(get.exception.code, 404)
                    get.exception.close()
                finally:
                    release.set()
                    first.join(5)
                self.assertEqual(responses, [result])
                with self.assertRaises(HTTPError) as caught:
                    urlopen(Request(url, method='GET'))
                self.assertEqual(caught.exception.code, 404)
                caught.exception.close()
            finally:
                httpd.shutdown()
                worker.join()

    def test_live_test_degrades_without_inputs_or_sumo_and_formats_a_mocked_run(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(demo, 'ROOT', Path(temp)):
            missing = demo.live_test()
            self.assertFalse(missing['ok'])
            self.assertIn('worlds/wolfe/routes.rou.xml', missing['reason'])
            files = [Path(temp)/name for name in ('worlds/wolfe/routes.rou.xml', 'roads/wolfe/old_timing.add.xml',
                                                  'reports/learner/wolfe/plan.add.xml')]
            for path in files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('<additional/>')
            with mock.patch.dict(sys.modules, {'learner': None}):
                no_sumo = demo.live_test()
            self.assertFalse(no_sumo['ok'])
            self.assertIn('simulator (SUMO and its Python packages) is not installed', no_sumo['reason'])
            road = mock.Mock()
            road.many.return_value = [({'all_requested_delay_s': 855.9988, 'unfinished': 931}, None),
                                      ({'all_requested_delay_s': 650.1908, 'unfinished': 218}, None)]
            package = mock.Mock(road=road)
            with mock.patch.dict(sys.modules, {'learner': package, 'learner.road': road}):
                shown = demo.live_test()
                road.many.side_effect = RuntimeError('sumo crashed')
                crashed = demo.live_test()
            self.assertEqual({k: shown[k] for k in ('ok', 'seed', 'old', 'learner')},
                             dict(ok=True, seed=200, old=dict(delay_s=856.0, unfinished=931),
                                  learner=dict(delay_s=650.2, unfinished=218)))
            (jobs,), _ = road.many.call_args
            self.assertEqual([job[1:] for job in jobs], [(files[0], files[1], 200, False, (), 120), (files[0], files[2], 200, False, (), 120)])
            self.assertEqual(crashed, dict(ok=False, reason='The simulation failed: RuntimeError: sumo crashed'))
            road.many.side_effect = subprocess.TimeoutExpired('sumo', 120)
            with mock.patch.dict(sys.modules, {'learner': package, 'learner.road': road}):
                timed_out = demo.live_test()
            self.assertFalse(timed_out['ok'])
            self.assertIn('TimeoutExpired', timed_out['reason'])

    def test_demo_timeout_reaches_the_sumo_subprocess(self):
        from learner import road
        cfg = road.load('wolfe')
        with mock.patch.object(road, 'net'), mock.patch.object(road, 'feed_detectors', return_value=('detectors', {})), \
                mock.patch.object(road.p, 'check_battery'), \
                mock.patch.object(road.p.subprocess, 'run', side_effect=subprocess.TimeoutExpired('sumo', 120)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                road.simulate(cfg, 'routes', 'timing', 200, timeout=120)
            self.assertEqual(run.call_args.kwargs['timeout'], 120)

    def test_cli_rejects_invalid_ports_and_missing_assets(self):
        for value in ('-1', '65536', 'not-a-port'):
            result = subprocess.run([sys.executable, '-m', 'tools.demo', '--port', value],
                                    cwd=demo.ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('error:', result.stderr)
        with mock.patch.object(sys, 'argv', ['demo']), mock.patch.object(demo, 'ASSETS', {'bad': Path('absent')}), \
                mock.patch.object(demo, 'server') as server, redirect_stdout(io.StringIO()), \
                redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                demo.main()
            self.assertEqual(caught.exception.code, 1)
            server.assert_not_called()

    def test_occupied_port_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp, demo.server(temp) as httpd:
            result = subprocess.run([sys.executable, '-m', 'tools.demo', '--port', str(httpd.server_port)],
                                    cwd=demo.ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Demo could not start:', result.stderr)


if __name__ == '__main__':
    unittest.main()
