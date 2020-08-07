# for reloading modules
%load_ext autoreload
%autoreload 2


## imports
import numpy as np
import copy
from dm_control import suite
import matplotlib.pyplot as plt
from tqdm import tqdm
from dm_tests import Agents, utils
import ipdb
import time
import tensorflow as tf

print('disabling GPUs for tensorflow')
tf.config.set_visible_devices([], 'GPU')
visible_devices = tf.config.get_visible_devices()
for device in visible_devices:
    assert device.device_type != 'GPU'






## train

# settings
action_grid = 3
action_repeats = 4  # repeat every action this number of times
episodes = 1000
steps_per_update = 4  # steps before updating q (increase this to cycle through episodes more quickly)
batch_size = 64
q_update_interval = 100  # (updates) frequency of q_target updates
eval_interval = 20  # (episodes) check average return every eval_interval updates
steps_per_episode = 1000  # don't change (this is a characteristic of the environment...)
epsilon_start = 1
epsilon_final = .1
epsilon_final_update = (steps_per_episode / steps_per_update * episodes)*.5  # (updates) epsilon_final is reach after this many updates
buffer_length = 50000
q_pretrain_value = None  # use for "optimistic" initialize of q model
learning_rate = .001
units_per_layer = (12,24)  # number of units per hidden layer (must have len()>1)
double_dqn = True
gamma = .99

# choose task
# env = suite.load('cartpole', 'balance')  # success
# env = suite.load('cartpole', 'balance_sparse')  # success (1000 max)
# env = suite.load('cartpole', 'swingup')  # success (>500 is good)
# env = suite.load('cartpole', 'swingup_sparse')  # success!

# env = suite.load('pendulum', 'swingup')

# env = suite.load('ball_in_cup', 'catch')

# env = suite.load('point_mass', 'easy')

env = suite.load('reacher', 'easy')




# make agent
agent = Agents.Agent(env.observation_spec(), env.action_spec(), action_grid=action_grid, units_per_layer=units_per_layer,
                     q_update_interval=q_update_interval, buffer_length=buffer_length, learning_rate=learning_rate,
                     double_dqn=double_dqn)
utils.initialize_buffer(agent, env)

if q_pretrain_value is not None:
    utils.train_optimistic_q(agent, target_q=q_pretrain_value)

##
print('training agent...')

for i in tqdm(range(episodes)):
    time_step = env.reset()
    done = False
    step_counter = 0
    action_counter = action_repeats

    while not done:
        epsilon_temp = epsilon_start - min(agent.total_updates / epsilon_final_update, 1) * (epsilon_start - epsilon_final)
        if action_counter==action_repeats:
            action = agent.select_action(time_step, epsilon=epsilon_temp)
            action_counter = 0
        action_counter += 1

        time_step_next = env.step(action)
        done = time_step_next.last()
        agent.add_experience(time_step, action, time_step_next)
        time_step = time_step_next

        step_counter += 1
        if step_counter==steps_per_update:
            agent.update(batch_size=batch_size, gamma=gamma)
            step_counter = 0

    if (i+1) % eval_interval == 0:
        avg_return, returns = utils.get_avg_return(agent, env)
        print('iteration {}, avg return {:.2f}, epsilon {:.2f}, returns: {}'.format(
            i+1, avg_return, epsilon_temp, [round(x,1) for x in returns]))

##
utils.show_rollout(agent, env, epsilon=.1)


## plot q funcion (test)
import matplotlib.pyplot as plt
prediction_grid, axis_limits = agent.get_prediction_grid(bins=10, percentile_lims=(0,100))
axis_limits = np.array(axis_limits)
action_num = agent.action_grid * agent.action_dim
observation_dim = agent.observation_dim
fig = plt.figure(figsize=(16,6))
show_action_diff = action_num == 2
axes = fig.subplots(action_num + show_action_diff, observation_dim - 1)

for i in range(observation_dim-1):
    mean_dims = tuple([d for d in range(observation_dim) if d < i or d > i + 1])
    slice = prediction_grid.mean(axis=mean_dims)
    for j in range(action_num):
        img = axes[j,i].imshow(slice[:,:,j], aspect='auto', extent=(axis_limits[0,i], axis_limits[1,i],
                                                                    axis_limits[0,i+1], axis_limits[1,i+1]))
        fig.colorbar(img, ax=axes[j,i])

    if show_action_diff:
        actions_diff = np.diff(slice, axis=2).squeeze()
        img = axes[2, i].imshow(actions_diff, aspect='auto', extent=(axis_limits[0, i], axis_limits[1, i],
                                                                       axis_limits[0, i + 1], axis_limits[1, i + 1]))
        fig.colorbar(img, ax=axes[2,i])

