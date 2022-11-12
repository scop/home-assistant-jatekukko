"""Data update coordinator support for the jatekukko integration."""


from __future__ import annotations

import asyncio
from http import HTTPStatus

import aiohttp
from pytekukko import Pytekukko

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import CONF_CUSTOMER_NUMBER, DEFAULT_UPDATE_INTERVAL, DOMAIN, LOGGER
from .models import JatekukkoData, ServiceData


class JatekukkoCoordinatorEntity(CoordinatorEntity):
    """Data update coordinator entity base class for the jatekukko integration."""

    @property
    def device_info(self) -> DeviceInfo:
        """Get service information."""
        return DeviceInfo(
            configuration_url="https://tilasto.jatekukko.fi/indexservice2.jsp",
            default_manufacturer="Jätekukko",
            default_model="Omakukko",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={
                (DOMAIN, self.coordinator.config_entry.data[CONF_CUSTOMER_NUMBER])
            },
            name=self.coordinator.config_entry.data[CONF_CUSTOMER_NUMBER],
        )


class JatekukkoCoordinator(DataUpdateCoordinator[JatekukkoData]):
    """Data update coordinator for the jatekukko integration."""

    def __init__(self, hass: HomeAssistant, name: str, client: Pytekukko) -> None:
        """Set up a coordinator."""
        self.client = client
        super().__init__(
            hass,
            LOGGER,
            name=name,
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> JatekukkoData:
        try:
            services = await self.client.get_services()
        except aiohttp.ClientResponseError as ex:
            if ex.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from ex
            raise

        # TODO: do not fetch collection schedule for disabled service entities?
        results = await asyncio.gather(
            *(self.client.get_collection_schedule(service) for service in services),
            self.client.get_invoice_headers(),
        )
        service_data = {
            service.pos: ServiceData(service, results[i])
            for i, service in enumerate(services)
        }
        invoice_headers = results[-1]

        return JatekukkoData(service_data, invoice_headers)
