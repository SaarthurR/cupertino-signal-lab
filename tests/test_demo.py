from contextlib import redirect_stderr, redirect_stdout
import csv
import gzip
import io
import json
import multiprocessing
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tools import demo, live_sim

FAKE_FRAMES = 40


def fake_frame(t):
    return dict(t=t, drain=t >= 59400+FAKE_FRAMES//2, cars=[1, 2500, 9000, 0], lights=['Gr'], waiting=0, finished=0, delay=0)


def fake_worker(arm, queue, stop):
    for t in range(59400, 59400+FAKE_FRAMES):
        queue.put(fake_frame(t))
    queue.put(dict(done=dict(old=dict(delay_s=856.0, unfinished=931), plan=dict(delay_s=650.2, unfinished=218))[arm]))


def broken_worker(arm, queue, stop):
    queue.put(dict(error='RuntimeError: sumo crashed'))


def endless_worker(arm, queue, stop):
    t = 59400
    while not stop.is_set():
        queue.put(fake_frame(t))
        t += 1


def crashed_worker(arm, queue, stop):
    if arm == 'old':
        time.sleep(1)
        os._exit(1)
    stop.wait(30)


def stalled_worker(arm, queue, stop):
    stop.wait(30)


def caught_error_worker(arm, queue, stop):
    if arm == 'old':
        time.sleep(1)
        for t in range(demo.FPS*8):
            queue.put(fake_frame(t))
        with mock.patch.object(live_sim, 'run', side_effect=RuntimeError('sumo crashed')):
            live_sim.worker(arm, queue, stop)
    else:
        stop.wait(30)


def sse(text):
    return [(block.split('\n')[0][len('event: '):], json.loads(block.split('\n')[1][len('data: '):]))
            for block in text.strip().split('\n\n') if block.startswith('event: ')]


def read_recording(path):
    """Python twin of loadRecording() in dashboard/console/console.js."""
    data = gzip.decompress(path.read_bytes())
    assert data[:4] == b'SLR1'
    size, = struct.unpack_from('<I', data, 4)
    head = json.loads(data[8:8+size])
    at, frames, width = 8+size, [], sum(head['lights'])
    for _ in range(head['frames']):
        frame, = struct.unpack_from('<I', data, at)
        frame, at = dict(t=frame), at+4
        for arm in ('old', 'plan'):
            n, = struct.unpack_from('<H', data, at)
            values = struct.unpack_from(f'<{3*n}H{n}B', data, at+2)
            at += 2+7*n
            waiting, finished, delay = struct.unpack_from('<3H', data, at+width)
            frame[arm] = dict(ids=list(values[:n]), x=list(values[n:2*n]), y=list(values[2*n:3*n]), stop=list(values[3*n:]),
                              lights=data[at:at+width].decode(), waiting=waiting, finished=finished, delay=delay)
            at += width+6
        frames.append(frame)
    assert at == len(data)
    return head, frames


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
                    for path in ('/console/', '/console/console.js', '/console/console.css', '/console/charts.js', '/console/sim.js'):
                        with urlopen(url+path) as response:
                            self.assertEqual(response.status, 200)
                    for target, source in demo.OPTIONAL.items():
                        with urlopen(f'{url}/{target}') as response:
                            expected = (demo.ROOT/source).read_bytes() if (demo.ROOT/source).is_file() else b'null'
                            self.assertEqual(response.read(), expected)
                    for road in ('wolfe', 'deanza'):
                        for name in ('card.json', 'plan.add.xml', 'pattern.csv', 'practice.json', 'road.yaml',
                                     'feed0.csv', 'feed1.csv', 'feed2.csv'):
                            with urlopen(f'{url}/console/data/{road}/{name}') as response:
                                self.assertEqual(response.read(), (demo.ROOT/demo.ASSETS[f'console/data/{road}/{name}']).read_bytes())
                    for path in ('/console/data/heldout/results.csv', '/console/data/heldout/go_back.json',
                                 '/console/data/deanza/posthoc.json', '/console/data/check-rule.txt',
                                 '/console/geo/wolfe.json', '/console/geo/deanza.json', '/console/geo/wolfe_seed200.rec.gz'):
                        with urlopen(url+path) as response:
                            self.assertEqual(response.status, 200)
                    for path in ('/console/data/', '/console/../README.md', '/reports/learner/wolfe/card.json',
                                 '/roads/wolfe/road.yaml', '/tools/demo.py', '/worlds/wolfe/routes.rou.xml',
                                 '/tools/live_sim.py', '/roads/wolfe/net.net.xml', '/console/geo/', '/api/sim/control'):
                        with self.assertRaises(HTTPError) as caught:
                            urlopen(url+path)
                        self.assertEqual(caught.exception.code, 404)
                        caught.exception.close()
                finally:
                    httpd.shutdown()
                    worker.join()

    def serve(self, temp):
        httpd = demo.server(temp)
        worker = threading.Thread(target=httpd.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(lambda: (httpd.shutdown(), worker.join(), httpd.server_close()))
        self.addCleanup(demo.SIM.update, speed=120, paused=False)
        return f'http://127.0.0.1:{httpd.server_port}'

    def test_stream_sends_both_plans_on_one_clock_then_the_scores(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(demo, 'live_ready', return_value=None), \
                mock.patch.object(demo, 'WORKER', fake_worker):
            url = self.serve(temp)
            with urlopen(url+'/api/sim/stream', timeout=30) as response:
                self.assertEqual(response.headers['Content-Type'], 'text/event-stream')
                events = sse(response.read().decode())
        self.assertEqual(events[0], ('status', dict(phase='starting')))
        frames = [value for kind, value in events if kind == 'frame']
        self.assertTrue(frames)
        self.assertTrue(all({'old', 'plan'} <= frame.keys() and frame['old']['t'] == frame['plan']['t'] == frame['t'] for frame in frames))
        self.assertEqual(frames[-1]['t'], 59400+FAKE_FRAMES-1)  # the last frame is always sent
        self.assertEqual(events[-1], ('end', dict(seed=200, old=dict(delay_s=856.0, unfinished=931), plan=dict(delay_s=650.2, unfinished=218))))
        self.assertFalse(demo.SIM_LOCK.locked())

    def test_stream_refuses_without_sumo_or_while_busy(self):
        with tempfile.TemporaryDirectory() as temp:
            url = self.serve(temp)
            with mock.patch.object(demo, 'live_ready', return_value='The simulator is not installed for this Python.'):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(url+'/api/sim/stream', timeout=10)
                self.assertEqual(caught.exception.code, 503)
                self.assertIn('not installed', json.loads(caught.exception.read())['reason'])
                caught.exception.close()
            with mock.patch.object(demo, 'live_ready', return_value=None), demo.SIM_LOCK:
                with self.assertRaises(HTTPError) as caught:
                    urlopen(url+'/api/sim/stream', timeout=10)
                self.assertEqual(caught.exception.code, 409)
                caught.exception.close()

    def test_worker_error_is_reported_as_a_failed_event(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(demo, 'live_ready', return_value=None), \
                mock.patch.object(demo, 'WORKER', broken_worker):
            url = self.serve(temp)
            with urlopen(url+'/api/sim/stream', timeout=30) as response:
                events = sse(response.read().decode())
        self.assertEqual(events[-1], ('failed', dict(reason='The simulation failed: RuntimeError: sumo crashed')))

    def test_closing_the_browser_stops_the_run(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(demo, 'live_ready', return_value=None), \
                mock.patch.object(demo, 'WORKER', endless_worker):
            url = self.serve(temp)
            response = urlopen(url+'/api/sim/stream', timeout=30)
            response.readline()
            self.assertTrue(demo.SIM_LOCK.locked())
            response.close()
            for _ in range(100):
                if not demo.SIM_LOCK.locked():
                    break
                time.sleep(0.1)
            self.assertFalse(demo.SIM_LOCK.locked())

    def test_abrupt_worker_exit_stops_peer_even_while_paused(self):
        for worker, paused in ((crashed_worker, False), (crashed_worker, True), (caught_error_worker, True)):
            with self.subTest(worker=worker, paused=paused), tempfile.TemporaryDirectory() as temp, \
                    mock.patch.object(demo, 'live_ready', return_value=None), \
                    mock.patch.object(demo, 'WORKER', worker):
                url = self.serve(temp)
                before = set(multiprocessing.active_children())
                with urlopen(url+'/api/sim/stream', timeout=8) as response:
                    response.readline()
                    demo.SIM['paused'] = paused
                    events = sse(response.read().decode())
                self.assertEqual(events[-1][0], 'failed')
                self.assertIn('exited unexpectedly', events[-1][1]['reason'])
                self.assertFalse(demo.SIM_LOCK.locked())
                self.assertEqual(set(multiprocessing.active_children()), before)

    def test_stalled_worker_respects_deadline_and_disconnect(self):
        for disconnect in (False, True):
            with self.subTest(disconnect=disconnect), tempfile.TemporaryDirectory() as temp, \
                    mock.patch.object(demo, 'live_ready', return_value=None), \
                    mock.patch.object(demo, 'WORKER', stalled_worker), \
                    mock.patch.object(demo, 'SIM_MAX_S', 30 if disconnect else 0.1):
                url = self.serve(temp)
                before = set(multiprocessing.active_children())
                with urlopen(url+'/api/sim/stream', timeout=8) as response:
                    if disconnect:
                        response.readline()
                    else:
                        events = sse(response.read().decode())
                        self.assertIn('too long', events[-1][1]['reason'])
                for _ in range(60):
                    if not demo.SIM_LOCK.locked():
                        break
                    time.sleep(0.1)
                self.assertFalse(demo.SIM_LOCK.locked())
                self.assertEqual(set(multiprocessing.active_children()), before)

    def test_control_sets_speed_and_pause_and_rejects_bad_input(self):
        with tempfile.TemporaryDirectory() as temp:
            url = self.serve(temp)+'/api/sim/control'
            with urlopen(Request(url, data=json.dumps(dict(speed=240, paused=True)).encode())) as response:
                self.assertEqual(json.loads(response.read()), dict(ok=True, speed=240, paused=True))
            self.assertEqual(demo.SIM, dict(speed=240, paused=True))
            for body in (b'{"speed": 7}', b'{"paused": "yes"}', b'not json', b'[1]', b'{"speed": 60}'*40):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(Request(url, data=body))
                self.assertEqual(caught.exception.code, 400)
                caught.exception.close()
            self.assertEqual(demo.SIM, dict(speed=240, paused=True))

    def test_recording_round_trips_and_the_committed_one_matches_the_saved_scores(self):
        frame = lambda t, n: dict(t=t, cars=[v for i in range(n) for v in (i+70000*(i == 0), 2500+i, 9000-i, i % 2)],
                                  lights=['GGr', 'ry'], waiting=3, finished=t-59400, delay=12.3)
        sides = dict(old=([frame(59400, 2), frame(59410, 0)], dict(delay_s=1.0, unfinished=0)),
                     plan=([frame(59400, 1), frame(59410, 3)], dict(delay_s=2.0, unfinished=1)))
        with tempfile.TemporaryDirectory() as temp:
            head, frames = read_recording(live_sim.write_recording(sides, Path(temp)/'r.gz'))
        self.assertEqual(head['final'], dict(old=dict(delay_s=1.0, unfinished=0), plan=dict(delay_s=2.0, unfinished=1)))
        self.assertEqual([f['t'] for f in frames], [59400, 59410])
        self.assertEqual(frames[0]['old'], dict(ids=[70000 % 65536, 1], x=[2500, 2501], y=[9000, 8999], stop=[0, 1],
                                                lights='GGrry', waiting=3, finished=0, delay=123))
        self.assertEqual(frames[1]['old']['ids'], [])
        committed = live_sim.RECORDING
        self.assertLessEqual(committed.stat().st_size, 4*1024*1024)
        head, frames = read_recording(committed)
        with (demo.ROOT/'reports/learner_heldout/results.csv').open() as rows:
            saved = {row['arm']: float(row['all_requested_delay_s']) for row in csv.DictReader(rows)
                     if row['road'] == 'wolfe' and row['seed'] == '200'}
        self.assertEqual(head['final']['old']['delay_s'], round(saved['old'], 1))
        self.assertEqual(head['final']['plan']['delay_s'], round(saved['learner'], 1))
        self.assertEqual(frames[0]['t'], 59400)
        self.assertTrue(all(b['t']-a['t'] == live_sim.EVERY_S for a, b in zip(frames, frames[1:])))

    def test_geometry_export_is_committed_and_fits_the_map(self):
        try:
            from tools import sim_geometry
        except ImportError as exc:
            self.skipTest(f'PyYAML is not installed: {exc}')
        for road in ('wolfe', 'deanza'):
            fresh = sim_geometry.export(road)
            self.assertEqual(json.loads((sim_geometry.OUT/f'{road}.json').read_text()), json.loads(json.dumps(fresh)))
            x0, y0, x1, y1 = fresh['bounds']
            self.assertTrue(fresh['lanes'] and any(lane['main'] for lane in fresh['lanes']))
            for lane in fresh['lanes']:
                # Lane shapes sit up to half a road width outside the edge-centre bounds.
                self.assertTrue(all(x0-5 <= x <= x1+5 for x in lane['xy'][0::2]) and all(y0-5 <= y <= y1+5 for y in lane['xy'][1::2]))
            for signal in fresh['signals']:
                self.assertTrue(signal['stops'])
                self.assertTrue(all(len(stop['xy']) == 4 and stop['links'] for stop in signal['stops']))

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
