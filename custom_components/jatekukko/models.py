"""Model objects for the jatekukko integration."""

from datetime import date
from typing import NamedTuple

from pytekukko.models import InvoiceHeader, Service


class ServiceData(NamedTuple):
    """Container for a Jätekukko service instance."""

    service: Service
    collection_schedule: list[date]


class JatekukkoData(NamedTuple):
    """Container for Jätekukko integration wide data."""

    service_datas: dict[int, ServiceData]
    invoice_headers: list[InvoiceHeader]
