
import tensorflow as tf

from src.models.helpers.get_state import (
    get_state_erroneous_channel_state_information,
    get_state_aods,
)


class ConfigSACLearner:
    def __init__(
            self,
            size_state,
            num_actions,
    ) -> None:

        self.training_name: str = 'test'

        self.get_state = get_state_erroneous_channel_state_information
        self.get_state_args = {
            'csi_format': 'rad_phase',
            'norm_csi': True,
        }

        self.percentage_mmse_samples_added_to_exp_buffer: float = 0.0  # [0.0, 1.0] chance for mmse action to be added

        self.training_args: dict = {
            'future_reward_discount_gamma': 0.0,  # Exponential future reward discount for stability
            'entropy_scale_alpha_initial': 1,  # weights the 'soft' entropy penalty against the td error
            'target_entropy': 1.0,  # SAC heuristic impl. = product of action_space.shape
            'entropy_scale_optimizer': tf.keras.optimizers.SGD,
            'entropy_scale_optimizer_args': {
                'learning_rate': 1e-4,  # LR=0.0 -> No adaptive entropy scale -> manually tune initial entropy scale
            },
            'training_minimum_experiences': 1_000,
            'training_batch_size': 512,
            'training_target_update_momentum_tau': 0,  # How much of the primary network copy to target networks
        }
        self.experience_buffer_args: dict = {
            'buffer_size': 10_000,
            'priority_scale_alpha': 0.0,  # alpha in [0, 1], alpha=0 uniform sampling, 1 is fully prioritized sampling
            'importance_sampling_correction_beta': 1.0  # beta in [0%, 100%], beta=100% is full correction
        }
        self.network_args: dict = {
            'value_network_args': {
                'hidden_layer_units': [512, 512, 512, 512],
                'activation_hidden': 'tanh',  # >'relu', 'tanh', 'penalized_tanh'
                'kernel_initializer_hidden': 'glorot_uniform'  # >glorot_uniform, he_uniform
            },
            'value_network_optimizer': tf.keras.optimizers.Adam,
            'value_network_optimizer_args': {
                'learning_rate': 1e-5,
                'amsgrad': False,
            },
            'policy_network_args': {
                'hidden_layer_units': [512, 512, 512, 512],
                'activation_hidden': 'tanh',  # >'relu', 'tanh', 'penalized_tanh'
                'kernel_initializer_hidden': 'glorot_uniform'  # >glorot_uniform, he_uniform
            },
            'policy_network_optimizer': tf.keras.optimizers.Adam,
            'policy_network_optimizer_args': {
                'learning_rate': 1e-6,
                'amsgrad': True,
            },
        }

        # TRAINING
        self.training_episodes: int = 3_000  # a new episode is a full reset of the simulation environment
        self.training_steps_per_episode: int = 1_000

        self.train_policy_every_k_steps: int = 1  # train policy only every k steps to give value approx. time to settle
        self.train_policy_after_j_steps: int = 0  # start training policy only after value approx. starts being sensible

        self._post_init(num_actions=num_actions, size_state=size_state)

    def _post_init(
            self,
            num_actions,
            size_state,
    ) -> None:

        self.training_args['training_minimum_experiences'] = max(self.training_args['training_minimum_experiences'],
                                                                 self.training_args['training_batch_size'])
        self.network_args['size_state'] = size_state
        self.network_args['num_actions'] = num_actions

        # Collected args
        self.algorithm_args = {
            **self.training_args,
            'network_args': self.network_args,
            'experience_buffer_args': self.experience_buffer_args,
        }
