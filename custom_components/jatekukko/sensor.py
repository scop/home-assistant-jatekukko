"""Jätekukko sensors."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytekukko.models import Service as PytekukkoService

from . import JatekukkoConfigEntry
from .const import CONF_CUSTOMER_NUMBER
from .coordinator import JatekukkoCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 # API
    entry: JatekukkoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jätekukko sensors based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        JatekukkoNextCollectionSensor(entry, service_data.service)
        for _, service_data in coordinator.data.service_datas.items()
        if service_data.service.next_collection
    )


class JatekukkoNextCollectionSensor(JatekukkoCoordinatorEntity, SensorEntity):
    """Jätekukko Sensor."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self,
        entry: JatekukkoConfigEntry,
        service: PytekukkoService,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(entry.runtime_data)

        self._pos = service.pos

        self.entity_description = SensorEntityDescription(
            key="next_collection",
            name=service.name,
            device_class=SensorDeviceClass.DATE,
        )
        self._attr_unique_id = f"{self._pos}@{entry.data[CONF_CUSTOMER_NUMBER]}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond to a JatekukkoCoordinator update."""
        self.update_from_latest_data()
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self.update_from_latest_data()

    @callback
    def update_from_latest_data(self) -> None:
        """Update the state."""
        service_data = self.coordinator.data.service_datas.get(self._pos)
        if not service_data:
            self._attr_available = False
            return

        self._attr_available = True
        self._attr_native_value = service_data.service.next_collection
