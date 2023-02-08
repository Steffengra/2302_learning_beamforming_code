
from numpy import (
    ndarray,
    array,
    arange,
    pi,
    exp,
    cos,
    arcsin,
)

from src.utils.spherical_to_cartesian_coordinates import (
    spherical_to_cartesian_coordinates,
)
from src.utils.euclidian_distance import (
    euclidian_distance,
)
from src.utils.get_wavelength import (
    get_wavelength,
)


class Satellite:

    def __init__(
            self,
            rng,
            idx,
            spherical_coordinates: ndarray,
            antenna_nr: int,
            antenna_distance: float,
            antenna_gain_linear: float,
            freq: float,
            center_aod_earth_deg: float,
    ) -> None:

        self.rng = rng

        self.idx: int = idx
        self.spherical_coordinates: ndarray = spherical_coordinates
        self.cartesian_coordinates: ndarray = spherical_to_cartesian_coordinates(spherical_coordinates)

        self.antenna_nr: int = antenna_nr
        self.antenna_distance: float = antenna_distance  # antenna distance in meters
        self.antenna_gain_linear: float = antenna_gain_linear

        self.freq: float = freq
        self.wavelength: float = get_wavelength(self.freq)

        self.center_aod_earth_deg: float = center_aod_earth_deg

        self.distance_to_users: dict = {}  # user_idx[int]: dist[float]
        self.aods_to_users: dict = {}  # user_idx[int]: aod[float] in rad
        self.steering_vectors_to_users: dict = {}  # user_idx[int]: steering_vector[ndarray] \in 1 x antenna_nr

        self.channel_state_to_users: ndarray = array([])  # depends on channel model
        self.erroneous_channel_state_to_users: ndarray = array([])  # depends on channel & error model

    def update_position(
            self,
            spherical_coordinates,
    ):

        self.spherical_coordinates = spherical_coordinates
        self.cartesian_coordinates = spherical_to_cartesian_coordinates(spherical_coordinates)

    def calculate_distance_to_users(
            self,
            users: list,
    ) -> None:
        # TODO: This doesn't change values of users that might have disappeared

        for user in users:
            self.distance_to_users[user.idx] = euclidian_distance(self.cartesian_coordinates,
                                                                  user.cartesian_coordinates)

    def calculate_aods_to_users(
            self,
            users: list
    ) -> None:
        """
        The calculation of the AODs is given by
        AOD = asin(
            ((orbit+radius_earth)^2 + sat_user_dist^2 - radius_earth^2)
            /
            (2 * (orbit+radius_earth) * sat_user_dist)
        )
        """
        # TODO: This doesn't change values of users that might have disappeared

        user_pos_idx = arange(0, len(users)) - (len(users) - 1) / 2

        for user in users:

            self.aods_to_users[user.idx] = arcsin(
                (
                        + self.spherical_coordinates[0] ** 2
                        + self.distance_to_users[user.idx] ** 2
                        - user.spherical_coordinates[0] ** 2
                )  # numerator
                /
                (
                        2 * self.spherical_coordinates[0] * self.distance_to_users[user.idx]
                )  # denominator
            )

            if user_pos_idx[user.idx] < 0:
                self.aods_to_users[user.idx] = 2 * (self.center_aod_earth_deg * pi/180) - self.aods_to_users[user.idx]

            # if user_pos_idx[user.idx] >= 0:
            #     self.aods_to_users[user.idx] = arcsin(
            #         (
            #             + self.spherical_coordinates[0]**2
            #             + self.distance_to_users[user.idx]**2
            #             - user.spherical_coordinates[0]**2
            #         )  # numerator
            #         /
            #         (
            #             2 * self.spherical_coordinates[0] * self.distance_to_users[user.idx]
            #         )  # denominator
            #     )
            # elif user_pos_idx[user.idx] < 0:
            #     aod_temp = arcsin(
            #         (
            #             + self.spherical_coordinates[0]**2
            #             + self.distance_to_users[user.idx]**2
            #             - user.spherical_coordinates[0]**2
            #         )  # numerator
            #         /
            #         (
            #             2 * self.spherical_coordinates[0] * self.distance_to_users[user.idx]
            #         )  # denominator
            #     )
            #     self.aods_to_users[user.idx] = 2 * (90 * pi/180) - aod_temp

    def calculate_steering_vectors(
            self,
            users: list,
    ) -> None:
        """
        This function provides the steering vectors for a given ULA and AOD
        """

        steering_idx = arange(0, self.antenna_nr) - (self.antenna_nr - 1) / 2

        for user in users:
            self.steering_vectors_to_users[user.idx] = exp(
                steering_idx * (
                    -1j * 2 * pi / self.wavelength
                    * self.antenna_distance
                    * cos(self.aods_to_users[user.idx])
                )
            )

    def update_channel_state_information(
            self,
            channel_model,
            users: list,
    ) -> None:
        """
        This function updates the channel state to given users
        according to a given channel model
        """
        self.channel_state_to_users = channel_model(self, users)

    def update_erroneous_channel_state_information(
            self,
            error_model_config,
            users: list,
    ) -> None:
        """
        This function updates erroneous channel state information to users
        according to a given user list and error model config
        """

        self.erroneous_channel_state_to_users = error_model_config.error_model(error_model_config=error_model_config,
                                                                               satellite=self,
                                                                               users=users)
