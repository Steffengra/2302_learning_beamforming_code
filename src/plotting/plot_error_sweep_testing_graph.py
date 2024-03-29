
import matplotlib.pyplot as plt
from gzip import (
    open as gzip_open,
)
from pickle import (
    load as pickle_load,
)
from pathlib import (
    Path,
)

from src.config.config import (
    Config,
)
from src.config.config_plotting import (
    PlotConfig,
    save_figures,
    generic_styling,
)


def plot_error_sweep_testing_graph(
        paths,
        name,
        width,
        height,
        xlabel,
        ylabel,
        plots_parent_path,
        legend: list or None = None,
        colors: list or None = None,
        markerstyle: list or None = None,
        linestyles: list or None = None,
) -> None:

    fig, ax = plt.subplots(figsize=(width, height))

    data = []
    for path in paths:
        with gzip_open(path, 'rb') as file:
            data.append(pickle_load(file))

    for data_id, data_entry in enumerate(data):
        first_entry = list(data_entry[1]['sum_rate'].keys())[0]

        if markerstyle is not None:
            marker = markerstyle[data_id]
        else:
            marker = None

        if colors is not None:
            color = colors[data_id]
        else:
            color = None

        if linestyles is not None:
            linestyle = linestyles[data_id]
        else:
            linestyle = None

        ax.errorbar(data_entry[0],
                    data_entry[1]['sum_rate'][first_entry]['mean'],
                    yerr=data_entry[1]['sum_rate'][first_entry]['std'],
                    marker=marker,
                    color=color,
                    linestyle=linestyle,
                    )

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    if legend:
        ax.legend(legend, ncols=2)

    generic_styling(ax=ax)
    fig.tight_layout(pad=0)

    save_figures(plots_parent_path=plots_parent_path, plot_name=name, padding=0)


if __name__ == '__main__':

    cfg = Config()
    plot_cfg = PlotConfig()

    data_paths = [
        Path(cfg.output_metrics_path,
             'sat_2_ant_4_usr_3_satdist_10000_usrdist_1000', 'err_satpos_and_userpos', 'error_sweep',
             'testing_mmse_sweep_0.0_0.07_userwiggle_30.gzip'),

        Path(cfg.output_metrics_path,
             'sat_2_ant_4_usr_3_satdist_10000_usrdist_1000', 'err_satpos_and_userpos', 'error_sweep',
             'testing_sac_error_st_0.1_ph_0.01_userwiggle_30_snap_2.785_sweep_0.0_0.07_userwiggle_30.gzip'),
    ]

    plot_width = 0.99 * plot_cfg.textwidth
    plot_height = plot_width * 9 / 20

    plot_legend = ['MMSE', 'OMA', 'SAC1', 'SAC2']
    plot_markerstyle = ['o', '^', 's', 'x']
    plot_colors = [plot_cfg.cp2['blue'], plot_cfg.cp2['black'], plot_cfg.cp2['magenta'], plot_cfg.cp2['green']]
    plot_linestyles = ['-', '--', '-', '-']

    plot_error_sweep_testing_graph(
        paths=data_paths,
        name='error_sweep_test',
        width=plot_width,
        xlabel='Error Bound',
        ylabel='Sum Rate',
        height=plot_height,
        legend=plot_legend,
        colors=plot_colors,
        markerstyle=plot_markerstyle,
        linestyles=plot_linestyles,
        plots_parent_path=plot_cfg.plots_parent_path,
    )
    plt.show()
