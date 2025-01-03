"""Config flow for jatekukko integration."""

from http import HTTPStatus
from typing import Any, Final

import aiohttp
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytekukko import Pytekukko
import voluptuous as vol

from .const import CONF_CUSTOMER_NUMBER, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA: Final = vol.Schema(
    {
        vol.Required(CONF_CUSTOMER_NUMBER): str,
        vol.Required(CONF_PASSWORD): str,
    },
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    client = Pytekukko(
        async_get_clientsession(hass),
        data["customer_number"],
        data["password"],
    )

    try:
        _ = await client.login()
    except aiohttp.ClientConnectionError as ex:
        raise CannotConnectError from ex
    except aiohttp.ClientResponseError as ex:
        if ex.status == HTTPStatus.UNAUTHORIZED:
            raise InvalidAuthError from ex
        raise

    return {"title": data["customer_number"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for jatekukko."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
            )

        await self.async_set_unique_id(user_input["customer_number"])
        self._abort_if_unique_id_configured()

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnectError:
            errors["base"] = "cannot_connect"
        except InvalidAuthError:
            errors["base"] = "invalid_auth"
        except Exception:  # noqa: BLE001
            LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, _: dict[str, Any]) -> FlowResult:
        """Handle configuration by re-auth."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        errors = {}

        if user_input is not None:
            try:
                _ = await validate_input(self.hass, user_input)
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            except InvalidAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                existing_entry = await self.async_set_unique_id(
                    user_input["customer_number"]
                )
                if existing_entry:
                    return self.async_update_reload_and_abort(
                        existing_entry,
                        data={**existing_entry.data, **user_input},
                        reason="reauth_successful",
                    )
                return self.async_abort(reason="reauth_failed_existing")

        reauth_entry = self._get_reauth_entry()
        data_schema = self.add_suggested_values_to_schema(
            STEP_USER_DATA_SCHEMA,
            {
                CONF_CUSTOMER_NUMBER: reauth_entry.data[CONF_CUSTOMER_NUMBER],
            },
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=data_schema,
            errors=errors,
        )


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuthError(HomeAssistantError):
    """Error to indicate there is invalid auth."""
