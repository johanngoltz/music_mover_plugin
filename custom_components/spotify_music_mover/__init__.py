"""Move music between Spotify devices."""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp
import homeassistant
import homeassistant.core
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)
from spotifyaio import SpotifyClient

from custom_components.spotify_music_mover.const import DOMAIN
from custom_components.spotify_music_mover.coordinator import SpotifyCoordinator
from custom_components.spotify_music_mover.model import SpotifyData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
]


SPOTIFY_SCOPES = [
    # Needed to be able to control playback
    "user-modify-playback-state",
    # Needed in order to read available devices
    "user-read-playback-state",
    # needed?
    "user-read-private",
]

type SpotifyConfigEntry = ConfigEntry[SpotifyData]


async def async_setup_entry(hass: HomeAssistant, entry: SpotifyConfigEntry) -> bool:
    """Set up Spotify from a config entry."""
    implementation = await async_get_config_entry_implementation(hass, entry)
    session = OAuth2Session(hass, entry, implementation)

    try:
        await session.async_ensure_token_valid()
    except aiohttp.ClientError as err:
        raise ConfigEntryNotReady from err

    spotify = SpotifyClient(async_get_clientsession(hass))
    spotify.authenticate(session.token["access_token"])

    async def _refresh_token() -> str:
        await session.async_ensure_token_valid()
        token = session.token["access_token"]
        if TYPE_CHECKING:
            assert isinstance(token, str)
        return token

    spotify.refresh_token_function = _refresh_token

    coordinator = SpotifyCoordinator(hass, spotify)

    await coordinator.async_config_entry_first_refresh()

    if not set(session.token["scope"].split(" ")).issuperset(SPOTIFY_SCOPES):
        raise ConfigEntryAuthFailed

    # commented out because it raises
    # ModuleNotFoundError: No module named 'custom_components.spotify_music_mover.media_player'
    # await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_move(call: homeassistant.core.ServiceCall) -> None:
        device_id = call.data.get("device_id")
        if TYPE_CHECKING:
            assert isinstance(device_id, str)

        await spotify.transfer_playback(device_id)

    hass.services.async_register(DOMAIN, "move", handle_move)

    return True


# device ids
# pc d35070d526315e501c040356bb4cc215646a1e5b
# srs 4bec8d212326bced75eac7b1347d4c86a1044979
# mcp 963930c60334416990b82580d1745bc95d26271e


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Spotify config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
