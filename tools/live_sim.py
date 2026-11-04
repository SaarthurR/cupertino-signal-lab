"""Live Wolfe Road run for the console: SUMO frames for one plan, or a recording of both for laptops without SUMO.

python -m tools.live_sim   # rewrites dashboard/console/geo/wolfe_seed200.rec.gz
"""
import gzip
import json
import multiprocessing
import os
from pathlib import Path
from queue import Full
import struct
import time

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ROOT/'worlds/wolfe/routes.rou.xml'
TIMINGS = {'old': ROOT/'roads/wolfe/old_timing.add.xml', 'plan': ROOT/'reports/learner/wolfe/plan.add.xml'}
SEED = 200  # one held-out traffic day the learner never saw
RECORDING = ROOT/'dashboard/console/geo/wolfe_seed200.rec.gz'
EVERY_S = 10  # recording keeps one frame per this many simulated seconds


def run(arm, emit, seed=SEED, timeout=1800):
    """The scored road.simulate run, stepped through libsumo; emit(frame) once per simulated second from the window start."""
    from learner import road  # sets SUMO_HOME before libsumo loads
    import libsumo as sumo
    from traci import constants as tc
    cfg = road.load('wolfe')
    begin, end = road.window(cfg)
    tls = [signal['sumo_tls_id'] for signal in cfg['signals']]
    wanted = (tc.VAR_POSITION, tc.VAR_SPEED, tc.VAR_TIMELOSS)

    def runner(args, timeout):
        stop, deadline = float(args[args.index('-e')+1]), time.monotonic()+timeout
        sumo.start([str(a) for a in args])
        try:
            ids, loss, depart, finished, delay = {}, {}, {}, 0, 0.0
            # Same stop rule as the SUMO binary: end time, or earlier when no vehicle is left.
            while sumo.simulation.getMinExpectedNumber() > 0 and sumo.simulation.getTime() < stop:
                if time.monotonic() > deadline:
                    raise TimeoutError(f'live run passed {timeout} s')
                sumo.simulationStep()
                t = sumo.simulation.getTime()
                for vid in sumo.simulation.getDepartedIDList():
                    sumo.vehicle.subscribe(vid, wanted)
                    ids[vid], depart[vid] = len(ids), sumo.vehicle.getDepartDelay(vid)
                for vid in sumo.simulation.getArrivedIDList():
                    if t >= begin:
                        finished, delay = finished+1, delay+loss.get(vid, 0)+depart.get(vid, 0)
                    loss.pop(vid, None), depart.pop(vid, None)
                cars = []
                for vid, values in sumo.vehicle.getAllSubscriptionResults().items():
                    (x, y), loss[vid] = values[tc.VAR_POSITION], values[tc.VAR_TIMELOSS]
                    cars += [ids[vid], round(x*10), round(y*10), int(values[tc.VAR_SPEED] < 0.1)]
                if t >= begin:
                    emit(dict(t=int(t), drain=t >= end, cars=cars, lights=[sumo.trafficlight.getRedYellowGreenState(i) for i in tls],
                              waiting=len(sumo.simulation.getPendingVehicles()), finished=finished,
                              delay=round(delay/finished, 1) if finished else 0))
        finally:
            sumo.close()

    stats, _ = road.simulate(cfg, ROUTES, TIMINGS[arm], seed, timeout=timeout, runner=runner)
    return dict(delay_s=round(stats['all_requested_delay_s'], 1), unfinished=stats['unfinished'])


def worker(arm, queue, stop):
    """Child process: frames into a bounded queue (backpressure), then {'done': score} or {'error': text}."""
    quiet = os.open(os.devnull, os.O_WRONLY)
    os.dup2(quiet, 1), os.dup2(quiet, 2)  # SUMO prints every warning; the score reads them from its error log

    def emit(frame):
        while not stop.is_set():
            try:
                return queue.put(frame, timeout=0.5)
            except Full:
                pass
        raise SystemExit
    try:
        queue.put(dict(done=run(arm, emit)))
    except SystemExit:
        pass
    except BaseException as exc:
        queue.put(dict(error=f'{type(exc).__name__}: {exc}'))


def _record(arm):
    frames = []
    final = run(arm, lambda frame: frame['t'] % EVERY_S == 0 and frames.append(frame))
    return frames, final


def write_recording(sides, path=RECORDING):
    """sides: {'old': (frames, final), 'plan': ...}. Gzip of 'SLR1', uint32 header length, a JSON header, then per frame
    uint32 time and, per side (old, plan): uint16 count, ids, x and y in decimetres (uint16), stopped flags (uint8), lights (ASCII), waiting, finished,
    delay in tenths (uint16 each). Little-endian."""
    (old, old_final), (plan, plan_final) = sides['old'], sides['plan']
    times = sorted({f['t'] for f in old} & {f['t'] for f in plan})
    by = [{f['t']: f for f in frames} for frames in (old, plan)]
    head = dict(seed=SEED, every_s=EVERY_S, frames=len(times),
                lights=[len(s) for s in old[0]['lights']], final=dict(old=old_final, plan=plan_final))
    out = [b'SLR1', json.dumps(head).encode()]
    out.insert(1, struct.pack('<I', len(out[1])))
    for t in times:
        out.append(struct.pack('<I', t))
        for side in by:
            f = side[t]
            n, cars = len(f['cars'])//4, f['cars']
            out.append(struct.pack(f'<H{n}H{n}H{n}H{n}B', n, *(c % 65536 for c in cars[0::4]), *cars[1::4], *cars[2::4], *cars[3::4]))
            out.append(''.join(f['lights']).encode())
            out.append(struct.pack('<3H', min(f['waiting'], 65535), min(f['finished'], 65535), round(f['delay']*10)))
    path.write_bytes(gzip.compress(b''.join(out), 9, mtime=0))
    return path


def main():
    with multiprocessing.get_context('spawn').Pool(2) as pool:
        sides = dict(zip(TIMINGS, pool.map(_record, TIMINGS)))
    path = write_recording(sides)
    print(path.relative_to(ROOT), path.stat().st_size, 'bytes', {arm: final for arm, (_, final) in sides.items()})


if __name__ == '__main__':
    main()
