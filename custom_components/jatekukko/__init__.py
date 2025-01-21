"""The jatekukko integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytekukko import Pytekukko

from .const import CONF_CUSTOMER_NUMBER, LOGGER
from .coordinator import JatekukkoCoordinator

PLATFORMS = [
    Platform.CALENDAR,
    Platform.SENSOR,
]

type JatekukkoConfigEntry = ConfigEntry[JatekukkoCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: JatekukkoConfigEntry) -> bool:
    """Set up jatekukko from a config entry."""
    client = Pytekukko(
        async_get_clientsession(hass),
        customer_number=entry.data[CONF_CUSTOMER_NUMBER],
        password=entry.data[CONF_PASSWORD],
    )
    coordinator = JatekukkoCoordinator(
        hass,
        name=f"Customer number {entry.data['customer_number']}",
        client=client,
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JatekukkoConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = entry.runtime_data
        try:
            await coordinator.client.logout()
        except Exception:  # noqa: BLE001
            LOGGER.debug("Could not logout", exc_info=True)

    return unload_ok
