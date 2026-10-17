"""Model objects for the jatekukko integration."""

# Copyright 2022 Ville Skyttä

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from datetime import date

    from pytekukko.models import InvoiceHeader, Service


class ServiceData(NamedTuple):
    """Container for a Jätekukko service instance."""

    service: Service
    collection_schedule: list[date]


class JatekukkoData(NamedTuple):
    """Container for Jätekukko integration wide data."""

    service_data: dict[int, ServiceData]
    invoice_headers: list[InvoiceHeader]
