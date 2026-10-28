# Setup check: fixed-timer lights vs. a briefly trained AI on sumo-rl's sample intersection.
import os
import sumo  # sets SUMO_HOME for the pip-installed SUMO; must come before sumo_rl
import sumo_rl
from sumo_rl import SumoEnvironment
from stable_baselines3 import PPO

NET = os.path.join(os.path.dirname(sumo_rl.__file__), "nets", "single-intersection")
SECONDS = 2000


def make_env(fixed=False):
    return SumoEnvironment(
        net_file=f"{NET}/single-intersection.net.xml",
        route_file=f"{NET}/single-intersection.rou.xml",
        single_agent=True, use_gui=False, num_seconds=SECONDS,
        fixed_ts=fixed, sumo_seed=42, reward_fn="diff-waiting-time",
    )


def avg_wait(env, model=None):
    obs, _ = env.reset()
    waits, done = [], False
    while not done:
        action = model.predict(obs, deterministic=True)[0] if model else 0  # fixed_ts ignores the action
        obs, _, term, trunc, info = env.step(action)
        waits.append(info["system_mean_waiting_time"])
        done = term or trunc
    env.close()
    return sum(waits) / len(waits)


fixed = avg_wait(make_env(fixed=True))
env = make_env()
model = PPO("MlpPolicy", env, verbose=0, seed=0).learn(total_timesteps=20_000)
ai = avg_wait(env, model)
print(f"Fixed timer: average wait {fixed:.1f} s")
print(f"AI (PPO):    average wait {ai:.1f} s")
