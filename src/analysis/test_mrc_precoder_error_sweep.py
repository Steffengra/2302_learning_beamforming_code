
from numpy import (
    arange,
    zeros,
    mean,
    std,
)
from datetime import (
    datetime,
)
from pathlib import (
    Path,
)
from gzip import (
    open as gzip_open,
)
from pickle import (
    dump as pickle_dump,
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
from src.data.channel.los_channel_model import (
    los_channel_model,
)
from src.data.precoder.mrc_precoder import (
    mrc_precoder_normalized,
)
from src.data.calc_sum_rate_no_iui import (
    calc_sum_rate_no_iui,
)
from src.utils.plot_sweep import (
    plot_sweep,
)
from src.utils.profiling import (
    start_profiling,
    end_profiling,
)


def test_mrc_precoder_error_sweep(
        config,
        csit_error_sweep_range,
        monte_carlo_iterations,
) -> None:

    def progress_print() -> None:
        progress = (error_sweep_idx * monte_carlo_iterations + iter_idx + 1) / (len(csit_error_sweep_range) * monte_carlo_iterations)
        timedelta = datetime.now() - real_time_start
        finish_time = real_time_start + timedelta / progress

        print(f'\rSimulation completed: {progress:.2%}, '
              f'est. finish {finish_time.hour:02d}:{finish_time.minute:02d}:{finish_time.second:02d}', end='')

    def set_new_error_value() -> None:
        if config.error_model.error_model_name == 'err_mult_on_steering_cos':
            config.error_model.uniform_error_interval['low'] = -1 * error_sweep_value
            config.error_model.uniform_error_interval['high'] = error_sweep_value
        elif config.error_model.error_model_name == 'err_sat2userdist':
            config.error_model.distance_error_std = error_sweep_value
        else:
            raise ValueError('Unknown error model name')

    def sim_update():
        user_manager.update_positions(config=config)
        satellite_manager.update_positions(config=config)

        satellite_manager.calculate_satellite_distances_to_users(users=user_manager.users)
        satellite_manager.calculate_satellite_aods_to_users(users=user_manager.users)
        satellite_manager.calculate_steering_vectors_to_users(users=user_manager.users)
        satellite_manager.update_channel_state_information(channel_model=los_channel_model, users=user_manager.users)
        satellite_manager.update_erroneous_channel_state_information(error_model_config=config.error_model, users=user_manager.users)

    def save_results():
        name = f'testing_mrc_sweep_{csit_error_sweep_range[0]}_{csit_error_sweep_range[-1]}_userwiggle_{config.user_dist_bound}.gzip'
        results_path = Path(config.output_metrics_path,
                            config.config_learner.training_name,
                            config.error_model.error_model_name,
                            'error_sweep')
        results_path.mkdir(parents=True, exist_ok=True)
        with gzip_open(Path(results_path, name), 'wb') as file:
            pickle_dump([csit_error_sweep_range, metrics], file=file)

    satellite_manager = SatelliteManager(config=config)
    user_manager = UserManager(config=config)

    real_time_start = datetime.now()

    profiler = None
    if config.profile:
        profiler = start_profiling()

    metrics = {
        'sum_rate': {
            'mrc': {
                'mean': zeros(len(csit_error_sweep_range)),
                'std': zeros(len(csit_error_sweep_range)),
            },
        },
    }

    for error_sweep_idx, error_sweep_value in enumerate(csit_error_sweep_range):

        # set new error value
        set_new_error_value()

        # set up per monte carlo metrics
        sum_rate_per_monte_carlo = zeros(monte_carlo_iterations)

        for iter_idx in range(monte_carlo_iterations):

            sim_update()

            w_mrc = mrc_precoder_normalized(
                channel_matrix=satellite_manager.erroneous_channel_state_information,
                **config.mrc_args,
            )
            sum_rate = calc_sum_rate_no_iui(
                channel_state=satellite_manager.channel_state_information,
                w_precoder=w_mrc,
                noise_power_watt=config.noise_power_watt
            )

            # log results
            sum_rate_per_monte_carlo[iter_idx] = sum_rate

            if iter_idx % 50 == 0:
                progress_print()

        metrics['sum_rate']['mrc']['mean'][error_sweep_idx] = mean(sum_rate_per_monte_carlo)
        metrics['sum_rate']['mrc']['std'][error_sweep_idx] = std(sum_rate_per_monte_carlo)

    if profiler is not None:
        end_profiling(profiler)

    save_results()

    plot_sweep(
        x=csit_error_sweep_range,
        y=metrics['sum_rate']['mrc']['mean'],
        yerr=metrics['sum_rate']['mrc']['std'],
        xlabel='error value',
        ylabel='sum rate',
        title='mrc',
    )

    if config.show_plots:
        plt_show()


if __name__ == '__main__':

    cfg = Config()
    cfg.config_learner.training_name = f'sat_{cfg.sat_nr}_ant_{cfg.sat_tot_ant_nr}_usr_{cfg.user_nr}_satdist_{cfg.sat_dist_average}_usrdist_{cfg.user_dist_average}'

    iterations: int = 10_000
    sweep_range = arange(0.0, 0.6, 0.1)
    # sweep_range = arange(0.0, 1/10_000_000, 1/100_000_000)

    test_mrc_precoder_error_sweep(
        config=cfg,
        csit_error_sweep_range=sweep_range,
        monte_carlo_iterations=iterations,
    )
