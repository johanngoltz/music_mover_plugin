"""Coordinator for Spotify."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import homeassistant.util.dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from spotifyaio import (
    PlaybackState,
    SpotifyClient,
    SpotifyConnectionError,
    UserProfile,
)

from .const import DOMAIN

if TYPE_CHECKING:
    from . import SpotifyData

_LOGGER = logging.getLogger(__name__)


type SpotifyConfigEntry = ConfigEntry[SpotifyData]


@dataclass
class SpotifyCoordinatorData:
    """Class to hold Spotify data."""

    position_updated_at: datetime | None
    current_playback: PlaybackState | None


class SpotifyCoordinator(DataUpdateCoordinator[SpotifyCoordinatorData]):
    """Class to manage fetching Spotify data."""

    current_user: UserProfile
    config_entry: SpotifyConfigEntry

    def __init__(self, hass: HomeAssistant, client: SpotifyClient) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.client = client

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        try:
            self.current_user = await self.client.get_current_user()
        except SpotifyConnectionError as err:
            raise UpdateFailed("Error communicating with Spotify API") from err

    async def _async_update_data(self) -> SpotifyCoordinatorData:
        try:
            current = await self.client.get_playback()
        except SpotifyConnectionError as err:
            raise UpdateFailed("Error communicating with Spotify API") from err
        if not current:
            return SpotifyCoordinatorData(
                current_playback=None, position_updated_at=None
            )
        # Record the last updated time, because Spotify's timestamp property is unreliable
        # and doesn't actually return the fetch time as is mentioned in the API description
        position_updated_at = dt_util.utcnow()
        return SpotifyCoordinatorData(
            current_playback=current, position_updated_at=position_updated_at
        )
