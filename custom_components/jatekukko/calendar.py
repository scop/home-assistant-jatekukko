"""Jätekukko calendar entries."""

import datetime
import typing

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytekukko import SERVICE_TIMEZONE

from . import JatekukkoConfigEntry
from .const import CONF_CUSTOMER_NUMBER
from .coordinator import JatekukkoCoordinatorEntity
from .models import ServiceData

if typing.TYPE_CHECKING:
    from pytekukko.models import InvoiceHeader


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 # API
    entry: JatekukkoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jätekukko calendar entries based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        JatekukkoCollectionCalendar(entry, service_data)
        for _, service_data in coordinator.data.service_datas.items()
        if service_data.collection_schedule
    )
    async_add_entities([JatekukkoInvoiceCalendar(entry)])


class JatekukkoCollectionCalendar(JatekukkoCoordinatorEntity, CalendarEntity):
    """Jätekukko collection calendar."""

    def __init__(
        self,
        entry: JatekukkoConfigEntry,
        service_data: ServiceData,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(entry.runtime_data)

        self._pos = service_data.service.pos

        self._attr_name = service_data.service.name
        self._attr_unique_id = f"{self._pos}@{entry.data[CONF_CUSTOMER_NUMBER]}"
        self.collection_schedule = sorted(service_data.collection_schedule)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond to a DataUpdateCoordinator update."""
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
            self.collection_schedule.clear()
            return

        self._attr_available = True
        self.collection_schedule = sorted(service_data.collection_schedule)

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if not self.name:  # should not really happen, but can in theory
            return None
        today = datetime.datetime.now(tz=SERVICE_TIMEZONE).date()
        for date in self.collection_schedule:
            if date >= today:
                return CalendarEvent(
                    start=date,
                    end=date + datetime.timedelta(days=1),
                    summary=self.name,  # type: ignore[arg-type] # false positive, cf. "not self.name" check above
                )
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        if not self.name:  # should not really happen, but can in theory
            return []

        start_date_date = start_date.date()
        end_date_date = end_date.date()

        matching_dates = filter(
            lambda date: start_date_date <= date < end_date_date,
            self.collection_schedule,
        )

        return [
            CalendarEvent(
                start=date,
                end=date + datetime.timedelta(days=1),
                summary=self.name,  # type: ignore[arg-type] # false positive, cf. "not self.name" check above
            )
            for date in matching_dates
        ]


class JatekukkoInvoiceCalendar(JatekukkoCoordinatorEntity, CalendarEntity):
    """Jätekukko invoice calendar."""

    def __init__(
        self,
        entry: JatekukkoConfigEntry,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(entry.runtime_data)
        self._attr_name = "Jätekukko invoices"
        self._attr_unique_id = f"invoices@{entry.data[CONF_CUSTOMER_NUMBER]}"
        self.invoice_headers: list[InvoiceHeader] = []

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond to a DataUpdateCoordinator update."""
        self.update_from_latest_data()
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self.update_from_latest_data()

    @callback
    def update_from_latest_data(self) -> None:
        """Update the state."""
        self.invoice_headers = sorted(
            self.coordinator.data.invoice_headers,
            key=lambda invoice_header: invoice_header.due_date,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        today = datetime.datetime.now(tz=SERVICE_TIMEZONE).date()
        for invoice_header in self.invoice_headers:
            if invoice_header.due_date >= today:
                return CalendarEvent(
                    start=invoice_header.due_date,
                    end=invoice_header.due_date + datetime.timedelta(days=1),
                    summary=invoice_header.name,
                )
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        start_date_date = start_date.date()
        end_date_date = end_date.date()

        matching_invoice_headers = filter(
            lambda invoice_header: start_date_date
            <= invoice_header.due_date
            < end_date_date,
            self.invoice_headers,
        )

        return [
            CalendarEvent(
                start=invoice_header.due_date,
                end=invoice_header.due_date + datetime.timedelta(days=1),
                summary=invoice_header.name,
            )
            for invoice_header in matching_invoice_headers
        ]
