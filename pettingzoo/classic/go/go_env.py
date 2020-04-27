from pettingzoo import AECEnv
from pettingzoo.utils.agent_selector import agent_selector
from pettingzoo.utils.env_logger import EnvLogger
from gym import spaces
from . import go
from . import coords
import numpy as np


class env(AECEnv):

    metadata = {'render.modes': ['human']}

    def __init__(self, board_size: int = 19, komi: float = 7.5):
        # board_size: a int, representing the board size (board has a board_size x board_size shape)
        # komi: a float, representing points given to the second player.
        super(env, self).__init__()

        self._overwrite_go_global_variables(board_size=board_size)
        self._komi = komi

        self.agents = ['black_0', 'white_0']
        self.num_agents = len(self.agents)
        self.has_reset = False

        self.observation_spaces = self._convert_to_dict([spaces.Box(low=0, high=1, shape=(self._N, self._N, 3), dtype=np.bool) for _ in range(self.num_agents)])
        self.action_spaces = self._convert_to_dict([spaces.Discrete(self._N * self._N + 1) for _ in range(self.num_agents)])

        self.agent_order = self.agents
        self._agent_selector = agent_selector(self.agent_order)

    def _overwrite_go_global_variables(self, board_size: int):
        self._N = board_size
        go.N = self._N
        go.ALL_COORDS = [(i, j) for i in range(self._N) for j in range(self._N)]
        go.EMPTY_BOARD = np.zeros([self._N, self._N], dtype=np.int8)
        go.NEIGHBORS = {(x, y): list(filter(self._check_bounds, [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])) for x, y in go.ALL_COORDS}
        go.DIAGONALS = {(x, y): list(filter(self._check_bounds, [(x + 1, y + 1), (x + 1, y - 1), (x - 1, y + 1), (x - 1, y - 1)])) for x, y in go.ALL_COORDS}
        return

    def _check_bounds(self, c):
        return 0 <= c[0] < self._N and 0 <= c[1] < self._N

    def _encode_player_plane(self, agent):
        if agent == self.agents[0]:
            return np.zeros([self._N, self._N], dtype=np.uint8)
        else:
            return np.ones([self._N, self._N], dtype=np.uint8)

    def _encode_board_planes(self, agent):
        agent_factor = -1 if agent == self.agents[0] else 1
        current_agent_plane_idx = np.where(self._go.board == agent_factor)
        opponent_agent_plane_idx = np.where(self._go.board == -agent_factor)
        current_agent_plane = np.zeros([self._N, self._N], dtype=np.uint8)
        opponent_agent_plane = np.zeros([self._N, self._N], dtype=np.uint8)
        current_agent_plane[current_agent_plane_idx] = 1
        opponent_agent_plane[opponent_agent_plane_idx] = 1
        return current_agent_plane, opponent_agent_plane

    def _int_to_name(self, ind):
        return self.agents[ind]

    def _name_to_int(self, name):
        return self.agents.index(name)

    def _convert_to_dict(self, list_of_list):
        return dict(zip(self.agents, list_of_list))

    def _encode_legal_actions(self, actions):
        return np.where(actions == 1)[0]

    def _encode_rewards(self, result):
        return [1, -1] if result == 1 else [-1, 1]

    def observe(self, agent):
        if not self.has_reset:
            EnvLogger.error_observe_before_reset()
        current_agent_plane, opponent_agent_plane = self._encode_board_planes(agent)
        player_plane = self._encode_player_plane(agent)
        return np.dstack((current_agent_plane, opponent_agent_plane, player_plane))

    def step(self, action, observe=True):
        if not self.has_reset:
            EnvLogger.error_step_before_reset()
        backup_policy = "Game terminating with current player losing"
        act_space = self.action_spaces[self.agent_selection]
        if np.isnan(action).any():
            EnvLogger.warn_action_is_NaN(backup_policy)
        if not act_space.contains(action):
            EnvLogger.warn_action_out_of_bound(action, act_space, backup_policy)

        if self.dones[self.agent_selection]:
            self.dones = self._convert_to_dict([True for _ in range(self.num_agents)])
            next_player = False
        else:
            if action not in self.infos[self.agent_selection]['legal_moves']:
                EnvLogger.warn_on_illegal_move()
                self.rewards[self.agent_selection] = -1
                self.dones = self._convert_to_dict([True for _ in range(self.num_agents)])
                info_copy = self.infos[self.agent_selection]
                self.infos = self._convert_to_dict([{'legal_moves': [self._N * self._N + 1]} for agent in range(self.num_agents)])
                self.infos[self.agent_selection] = info_copy
                self.agent_selection = self._agent_selector.next()
                return self._last_obs
            self._go = self._go.play_move(coords.from_flat(action))
            self._last_obs = self.observe(self.agent_selection)
            next_player = self._agent_selector.next()
            if self._go.is_game_over():
                self.dones = self._convert_to_dict([True for _ in range(self.num_agents)])
                self.rewards = self._convert_to_dict(self._encode_rewards(self._go.result()))
                self.infos[next_player]['legal_moves'] = [self._N * self._N + 1]
            else:
                self.infos[next_player]['legal_moves'] = self._encode_legal_actions(self._go.all_legal_moves())
        self.agent_selection = next_player if next_player else self._agent_selector.next()
        if observe:
            return self._last_obs

    def reset(self, observe=True):
        self.has_reset = True
        self._go = go.Position(board=None, komi=self._komi)

        self.agent_selection = self._agent_selector.reset()
        self.rewards = self._convert_to_dict(np.array([0.0, 0.0]))
        self.dones = self._convert_to_dict([False for _ in range(self.num_agents)])
        self.infos = self._convert_to_dict([{'legal_moves': []} for _ in range(self.num_agents)])
        self.infos[self.agent_selection]['legal_moves'] = self._encode_legal_actions(self._go.all_legal_moves())
        self._last_obs = self.observe(self.agents[0])
        if observe:
            return self._last_obs
        else:
            return

    def render(self, mode='human'):
        print(self._go)

    def close(self):
        EnvLogger.warn_close_unrendered_env()