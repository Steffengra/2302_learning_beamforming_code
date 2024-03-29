
from datetime import (
    datetime,
)
from pathlib import (
    Path,
)
from shutil import (
    copytree,
    rmtree,
)
from gzip import (
    open as gzip_open,
)
from pickle import (
    dump as pickle_dump,
)
from numpy import (
    ones,
    infty,
    mean,
    std,
)
from matplotlib.pyplot import (
    show as plt_show,
)

from src.config.config import (
    Config,
)
from src.data.satellite_manager import (
    SatelliteManager,
)
from src.data.user_manager import (
    UserManager,
)
from src.models.algorithms.soft_actor_critic import (
    SoftActorCritic,
)
from src.data.channel.los_channel_model import (
    los_channel_model,
)
from src.data.calc_sum_rate import (
    calc_sum_rate,
)
from src.data.precoder.mmse_precoder import (
    mmse_precoder_normalized,
)
from src.utils.real_complex_vector_reshaping import (
    real_vector_to_half_complex_vector,
    rad_and_phase_to_complex_vector,
    complex_vector_to_double_real_vector,
    complex_vector_to_rad_and_phase,
)
from src.utils.norm_precoder import (
    norm_precoder,
)
from src.utils.plot_sweep import (
    plot_sweep,
)
from src.utils.profiling import (
    start_profiling,
    end_profiling,
)


def train_sac_single_error(config) -> Path:

    def progress_print() -> None:
        progress = (
                (training_episode_id * config.config_learner.training_steps_per_episode + training_step_id + 1)
                / (config.config_learner.training_episodes * config.config_learner.training_steps_per_episode)
        )
        timedelta = datetime.now() - real_time_start
        finish_time = real_time_start + timedelta / progress

        print(f'\rSimulation completed: {progress:.2%}, '
              f'est. finish {finish_time.hour:02d}:{finish_time.minute:02d}:{finish_time.second:02d}', end='')

    def policy_training_criterion() -> bool:
        """Train policy networks only every k steps and/or only after j total steps to ensure a good value function"""
        if (
            simulation_step > config.config_learner.train_policy_after_j_steps
            and
            (simulation_step % config.config_learner.train_policy_every_k_steps) == 0
        ):
            return True
        return False

    def sim_update():
        user_manager.update_positions(config=config)
        satellite_manager.update_positions(config=config)

        satellite_manager.calculate_satellite_distances_to_users(users=user_manager.users)
        satellite_manager.calculate_satellite_aods_to_users(users=user_manager.users)
        satellite_manager.calculate_steering_vectors_to_users(users=user_manager.users)
        satellite_manager.update_channel_state_information(channel_model=los_channel_model, users=user_manager.users)
        satellite_manager.update_erroneous_channel_state_information(error_model_config=config.error_model, users=user_manager.users)

    def add_mmse_experience():

        # this needs to use erroneous csi, otherwise the data distribution in buffer
        #  is changed significantly from reality, i.e., the learner gets too much confidence that
        #  the csi is reliable
        w_mmse = mmse_precoder_normalized(
            channel_matrix=satellite_manager.erroneous_channel_state_information,
            **config.mmse_args
        )
        reward_mmse = calc_sum_rate(
            channel_state=satellite_manager.channel_state_information,
            w_precoder=w_mmse,
            noise_power_watt=config.noise_power_watt,
        )
        mmse_experience = {
            'state': state_current,
            'action': complex_vector_to_double_real_vector(w_mmse.flatten()),
            'reward': reward_mmse,
            'next_state': state_next,
        }
        sac.add_experience(mmse_experience)

    def save_model_checkpoint(extra=None):

        if config.error_model.error_model_name == 'err_mult_on_steering_cos':
            name = f'error_{config.error_model.uniform_error_interval["high"]}_userwiggle_{config.user_dist_bound}'
        elif config.error_model.error_model_name == 'err_sat2userdist':
            name = f'error_{config.error_model.distance_error_std}_userwiggle_{config.user_dist_bound}'
        elif config.error_model.error_model_name == 'err_satpos_and_userpos':
            name = f'error_st_{config.error_model.uniform_error_interval["high"]}_ph_{config.error_model.phase_sat_error_std}_userwiggle_{config.user_dist_bound}'
        else:
            raise ValueError('unknown error model name')
        if extra is not None:
            name += f'_snap_{extra:.3f}'
        checkpoint_path = Path(
            config.trained_models_path,
            config.config_learner.training_name,
            config.error_model.error_model_name,
            'single_error',
            name,
        )

        sac.networks['policy'][0]['primary'].save(Path(checkpoint_path, 'model'))

        # save config
        copytree(Path(config.project_root_path, 'src', 'config'),
                 Path(checkpoint_path, 'config'),
                 dirs_exist_ok=True)

        # clean model checkpoints
        for high_score_prior_id, high_score_prior in enumerate(reversed(high_scores)):
            if high_score > 1.05 * high_score_prior or high_score_prior_id > 3:

                if config.error_model.error_model_name == 'err_mult_on_steering_cos':
                    name = f'error_{config.error_model.uniform_error_interval["high"]}_userwiggle_{config.user_dist_bound}_snap_{high_score_prior:.3f}'
                elif config.error_model.error_model_name == 'err_sat2userdist':
                    name = f'error_{config.error_model.distance_error_std}_userwiggle_{config.user_dist_bound}_snap_{high_score_prior:.3f}'
                elif config.error_model.error_model_name == 'err_satpos_and_userpos':
                    name = f'error_st_{config.error_model.uniform_error_interval["high"]}_ph_{config.error_model.phase_sat_error_std}_userwiggle_{config.user_dist_bound}_snap_{high_score_prior:.3f}'

                prior_checkpoint_path = Path(config.trained_models_path, config.config_learner.training_name, config.error_model.error_model_name, 'single_error', name)
                rmtree(path=prior_checkpoint_path, ignore_errors=True)
                high_scores.remove(high_score_prior)

        return checkpoint_path

    def save_results():

        if config.error_model.error_model_name == 'err_mult_on_steering_cos':
            name = f'training_error_{config.error_model.uniform_error_interval["high"]}_userwiggle_{config.user_dist_bound}.gzip'
        elif config.error_model.error_model_name == 'err_sat2userdist':
            name = f'training_error_{config.error_model.distance_error_std}_userwiggle_{config.user_dist_bound}.gzip'
        elif config.error_model.error_model_name == 'err_satpos_and_userpos':
            name = f'training_error_st_{config.error_model.uniform_error_interval["high"]}_ph_{config.error_model.phase_sat_error_std}_userwiggle_{config.user_dist_bound}.gzip'
        else:
            raise ValueError('unknown model name')

        results_path = Path(config.output_metrics_path, config.config_learner.training_name, config.error_model.error_model_name, 'single_error')
        results_path.mkdir(parents=True, exist_ok=True)
        with gzip_open(Path(results_path, name), 'wb') as file:
            pickle_dump(metrics, file=file)

    satellite_manager = SatelliteManager(config=config)
    user_manager = UserManager(config=config)
    sac = SoftActorCritic(rng=config.rng, **config.config_learner.algorithm_args)

    metrics: dict = {
        'mean_sum_rate_per_episode': -infty * ones(config.config_learner.training_episodes)
    }
    high_score = -infty
    high_scores = []

    real_time_start = datetime.now()

    profiler = None
    if config.profile:
        profiler = start_profiling()

    step_experience: dict = {'state': 0, 'action': 0, 'reward': 0, 'next_state': 0}

    for training_episode_id in range(config.config_learner.training_episodes):

        episode_metrics: dict = {
            'sum_rate_per_step': -infty * ones(config.config_learner.training_steps_per_episode),
            'mean_log_prob_density': infty * ones(config.config_learner.training_steps_per_episode),
            'value_loss': -infty * ones(config.config_learner.training_steps_per_episode),
        }

        sim_update()

        state_next = config.config_learner.get_state(satellites=satellite_manager, **config.config_learner.get_state_args)

        for training_step_id in range(config.config_learner.training_steps_per_episode):

            simulation_step = training_episode_id * config.config_learner.training_steps_per_episode + training_step_id

            # determine state
            state_current = state_next
            step_experience['state'] = state_current

            # determine action based on state
            action = sac.get_action(state=state_current)
            step_experience['action'] = action

            # reshape to fit reward calculation
            w_precoder_vector = real_vector_to_half_complex_vector(action)
            w_precoder = w_precoder_vector.reshape((config.sat_nr*config.sat_ant_nr, config.user_nr))
            w_precoder_normed = norm_precoder(precoding_matrix=w_precoder, power_constraint_watt=config.power_constraint_watt,
                                              per_satellite=True, sat_nr=config.sat_nr, sat_ant_nr=config.sat_ant_nr)

            # step simulation based on action, determine reward
            reward = calc_sum_rate(
                channel_state=satellite_manager.channel_state_information,
                w_precoder=w_precoder_normed,
                noise_power_watt=config.noise_power_watt,
            )
            step_experience['reward'] = reward

            # optionally add the corresponding mmse precoder to the data set
            if config.rng.random() < config.config_learner.percentage_mmse_samples_added_to_exp_buffer:
                add_mmse_experience()  # todo note: currently state_next saved in the mmse experience is not correct

            # update simulation state
            sim_update()

            # get new state
            state_next = config.config_learner.get_state(satellites=satellite_manager, **config.config_learner.get_state_args)
            step_experience['next_state'] = state_next

            sac.add_experience(experience=step_experience)

            # train allocator off-policy
            train_policy = False
            if policy_training_criterion():
                train_policy = True
            mean_log_prob_density, value_loss = sac.train(
                toggle_train_value_networks=True,
                toggle_train_policy_network=train_policy,
                toggle_train_entropy_scale_alpha=True,
            )

            # log results
            episode_metrics['sum_rate_per_step'][training_step_id] = reward
            episode_metrics['mean_log_prob_density'][training_step_id] = mean_log_prob_density
            episode_metrics['value_loss'][training_step_id] = value_loss

            if config.verbosity > 0:
                if training_step_id % 50 == 0:
                    progress_print()

        # log episode results
        episode_mean_sum_rate = mean(episode_metrics['sum_rate_per_step'])
        metrics['mean_sum_rate_per_episode'][training_episode_id] = episode_mean_sum_rate
        if config.verbosity == 1:
            print(f' Episode mean reward: {episode_mean_sum_rate:.4f}'
                  f' std {std(episode_metrics["sum_rate_per_step"]):.2f},'
                  f' current exploration: {mean(episode_metrics["mean_log_prob_density"]):.2f},'
                  f' value loss: {mean(episode_metrics["value_loss"]):.5f}'
                  )

        # save network snapshot
        if episode_mean_sum_rate > high_score:
            high_score = mean(episode_metrics['sum_rate_per_step'])
            high_scores.append(high_score)
            best_model_path = save_model_checkpoint(extra=episode_mean_sum_rate)

    # end compute performance profiling
    if profiler is not None:
        end_profiling(profiler)

    save_results()

    # TODO: Move this to proper place
    plot_sweep(range(config.config_learner.training_episodes), metrics['mean_sum_rate_per_episode'],
               'Training Episode', 'Sum Rate')
    if config.show_plots:
        plt_show()

    return best_model_path


if __name__ == '__main__':
    cfg = Config()
    train_sac_single_error(config=cfg)
