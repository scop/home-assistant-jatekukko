"""Data update coordinator support for the jatekukko integration."""

import asyncio
from datetime import date
from http import HTTPStatus
from typing import Any, cast

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from pytekukko import Pytekukko
from pytekukko.models import InvoiceHeader

from .const import CONF_CUSTOMER_NUMBER, DEFAULT_UPDATE_INTERVAL, DOMAIN, LOGGER
from .models import JatekukkoData, ServiceData


class JatekukkoCoordinatorEntity(CoordinatorEntity["JatekukkoCoordinator"]):
    """Data update coordinator entity base class for the jatekukko integration."""

    def __init__(self, coordinator: "JatekukkoCoordinator", context: Any = None):
        """Set up a coordinator entity."""
        super().__init__(coordinator, context)
        self._attr_device_info = DeviceInfo(
            configuration_url="https://tilasto.jatekukko.fi/indexservice2.jsp",
            manufacturer="Jätekukko",
            model="Omakukko",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={
                (DOMAIN, self.coordinator.config_entry.data[CONF_CUSTOMER_NUMBER]),
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

        # TODO(scop): do not fetch schedule for disabled service entities? # noqa: FIX002,TD003,E501
        results = await asyncio.gather(
            *(self.client.get_collection_schedule(service) for service in services),
            self.client.get_invoice_headers(),
        )
        service_data = {
            service.pos: ServiceData(service, cast(list[date], results[i]))
            for i, service in enumerate(services)
        }
        invoice_headers = cast(list[InvoiceHeader], results[-1])

        return JatekukkoData(service_data, invoice_headers)
