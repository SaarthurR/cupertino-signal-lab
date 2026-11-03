"""Signal Learner, simulation only. Usage: python -m tools.learner <step> [--road NAME] [--seed N] [--plan learner|bad|noop]"""
import argparse
import json
import tempfile
from pathlib import Path

from learner import card, learn, practice, road
from world import roads, trial, worlds

STEPS = ('build-road', 'build-world', 'watch', 'learn', 'practice', 'recommend', 'check', 'run', 'dev-check', 'heldout-test')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=STEPS)
    names = sorted(set(roads.SPECS) | {p.parent.name for p in roads.ROADS.glob('*/road.yaml')})
    parser.add_argument('--road', choices=names)
    parser.add_argument('--seed', type=int, default=300)
    parser.add_argument('--plan', choices=('learner', 'bad', 'noop'), default='learner')
    args = parser.parse_args()
    name = args.road
    if args.step != 'heldout-test' and name is None:
        parser.error('--road is required for this step')
    if args.step == 'heldout-test' and name is not None:
        parser.error('heldout-test has fixed roads; do not supply --road')
    if args.seed < 0:
        parser.error('--seed must be nonnegative')
    if name and (roads.ROADS/name/'road.yaml').exists() and road.load(name)['role'] == 'heldout':
        parser.error(f'{name} is held out; use only its separately registered evaluation, never standalone mutation')
    if args.step == 'build-road':
        roads.stevens_creek() if name == 'stevens_creek' else roads.build_road(name)
    elif args.step == 'build-world':
        worlds.build_world(name)
    elif args.step == 'watch':
        worlds.watch(name)
    elif args.step in ('learn', 'practice', 'recommend'):
        {'learn': learn.learn, 'practice': practice.practice, 'recommend': card.recommend}[args.step](name)
    elif args.step == 'check':
        cfg = road.load(name)
        with tempfile.TemporaryDirectory() as temp:
            plan, program = road.OUT/name/'plan.add.xml', 'learner'
            if args.plan != 'learner':
                plan = Path(temp)/'plan.xml'
                program = {'bad': worlds.bad_plan, 'noop': worlds.noop_plan}[args.plan](cfg, plan)
            print(json.dumps(worlds.check_run(name, plan, program, args.seed), indent=2))
    elif args.step == 'run':
        print(json.dumps(trial.run_learner(name)))
    elif args.step == 'dev-check':
        result = trial.dev_check(name)
        print(json.dumps({k: v for k, v in result.items() if k != 'go_back'} | {'go_back_passed': result['go_back']['passed']}, indent=2))
    else:
        print(json.dumps(trial.heldout_test(), indent=2))


if __name__ == '__main__':
    main()
