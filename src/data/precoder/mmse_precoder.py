
from numpy import (
    ndarray,
    finfo,
    eye,
    matmul,
    trace,
    sqrt,
)
from numpy.linalg import (
    inv,
)

from src.utils.norm_precoder import (
    norm_precoder,
)


def mmse_precoder(
        channel_matrix,
        noise_power_watt: float,
        power_constraint_watt: float,
        sat_nr,
        sat_ant_nr,
) -> ndarray:

    precoding_matrix = mmse_precoder_no_norm(
        channel_matrix=channel_matrix,
        noise_power_watt=noise_power_watt,
        power_constraint_watt=power_constraint_watt,
    )

    precoding_matrix_normed = norm_precoder(
        precoding_matrix=precoding_matrix,
        power_constraint_watt=power_constraint_watt,
        per_satellite=True,
        sat_nr=sat_nr,
        sat_ant_nr=sat_ant_nr,
    )

    return precoding_matrix_normed


def mmse_precoder_no_norm(
        channel_matrix,
        noise_power_watt: float,
        power_constraint_watt: float,
) -> ndarray:

    # inversion_constant_lambda = finfo('float32').tiny
    inversion_constant_lambda = 0

    user_nr = channel_matrix.shape[0]
    sat_tot_ant_nr = channel_matrix.shape[1]

    precoding_matrix = (
        matmul(
            inv(
                matmul(channel_matrix.conj().T, channel_matrix)
                + (noise_power_watt * user_nr / power_constraint_watt + inversion_constant_lambda) * eye(sat_tot_ant_nr)
            ),
            channel_matrix.conj().T
        )
    )

    # tr(A^H * A) is the sum of squared elements
    # after applying norm_factor, the trace of norm_factor * (A^H * A) will be == power_constraint_watt
    norm_factor = sqrt(power_constraint_watt / trace(matmul(precoding_matrix.conj().T, precoding_matrix)))

    w_mmse = norm_factor * precoding_matrix

    return w_mmse
