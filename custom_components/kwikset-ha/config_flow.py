from typing import Any
from collections.abc import Mapping

from aiokwikset import API
from aiokwikset.errors import RequestError, NotAuthorized
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_CODE
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN, 
    LOGGER,
    CONF_HOME_ID,
    CONF_REFRESH_TOKEN,
    CONF_CODE_TYPE,
)

from .util import async_connect_api, async_validate_api, CannotConnect, KWIKSET_CLIENT

CODE_TYPES = ['email','phone']

class KwiksetFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle configuration of Kwikset integrations."""

    VERSION = 2

    entry: config_entries.ConfigEntry | None

    def __init__(self):
        """Create a new instance of the flow handler"""
        self.api = None
        self.pre_auth = None
        self.username = None
        self.password = None
        self.code_type = None
        self.home_id = None
        self.client = KWIKSET_CLIENT

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle re-authentication with kwikset"""

        self.entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_user()
    
    async def async_step_reauth_user(self, user_input=None):
        """Get the email and password from the user"""
        errors: dict[str, str] = {}
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("email"): str,
                        vol.Required("password"): str
                    }
                ),
                errors = errors
            )
            
        self.username = user_input[CONF_EMAIL]
        self.password = user_input[CONF_PASSWORD]

        return await self.async_step_reauth_code_type()
    
    async def async_step_reauth_code_type(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                step_id="code_type",
                data_schema=vol.Schema({
                    vol.Required("code_type"): vol.In(CODE_TYPES),
                })
            )
        
        self.code_type = user_input[CONF_CODE_TYPE]
        LOGGER.debug(self.code_type)

        return await self.async_step_reauth_code()
    
    async def async_step_reauth_code(self, user_input=None):
        """Get the Verification code from the user"""
        errors: dict[str, str] = {}

        if user_input is None:
            try:
                #initialize API
                self.api = API(self.username)
                #start authentication
                self.pre_auth = await self.api.authenticate(self.password, self.code_type)
                LOGGER.debug(self.pre_auth)
            
            except RequestError as request_error:
                LOGGER.error("Error connecting to the kwikset API: %s", request_error)
                errors["base"] = "cannot_connect"
                raise CannotConnect from request_error
            except NotAuthorized:
                errors["base"] = "refresh_token_revoked"

            return self.async_show_form(
                step_id="code",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_CODE): str
                    }
                ),
                errors = errors
            )
        
        #MFA verification
        await self.api.verify_user(self.pre_auth, user_input[CONF_CODE])

        self.hass.config_entries.async_update_entry(
            self.entry,
            data={
                **self.entry.data,
                CONF_EMAIL: self.username,
                CONF_HOME_ID: self.home_id,
                CONF_REFRESH_TOKEN: self.api.refresh_token
            }
        )
        await self.hass.config_entries.async_reload(self.entry.entry_id)
        return self.async_abort(reason="reauth_successful")


    async def async_step_user(self, user_input=None):
        """Get the email and password from the user"""
        errors: dict[str, str] = {}
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("email"): str,
                        vol.Required("password"): str
                    }
                ),
                errors = errors
            )
            
        self.username = user_input[CONF_EMAIL]
        self.password = user_input[CONF_PASSWORD]

        return await self.async_step_code_type()

    async def async_step_code_type(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                step_id="code_type",
                data_schema=vol.Schema({
                    vol.Required("code_type"): vol.In(CODE_TYPES),
                })
            )
        
        self.code_type = user_input[CONF_CODE_TYPE]
        LOGGER.debug(self.code_type)

        return await self.async_step_code()
        

    async def async_step_code(self, user_input=None):
        """Get the Verification code from the user"""
        errors: dict[str, str] = {}

        if user_input is None:
            try:
                #initialize API
                pre_auth = await async_connect_api(self.username)
            
            except RequestError as request_error:
                LOGGER.error("Error connecting to the kwikset API: %s", request_error)
                errors["base"] = "cannot_connect"
                raise CannotConnect from request_error
            except NotAuthorized:
                errors["base"] = "refresh_token_revoked"

            return self.async_show_form(
                step_id="code",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_CODE): str
                    }
                ),
                errors = errors
            )
        
        #MFA verification
        await async_validate_api(pre_auth, user_input[CONF_CODE])

        return await self.async_step_select_home()

    async def async_step_select_home(self, user_input=None):
        """Ask user to select the home to setup"""
        if user_input is None or CONF_HOME_ID not in user_input:
            #Get available locations
            existing_homes = [
                entry.data[CONF_HOME_ID] for entry in self._async_current_entries()
            ]
            homes = await self.client.user.get_homes()
            homes_options = {
                home['homeid']: home['homename']
                for home in homes
                if home['homeid'] not in existing_homes
            }
            if not homes_options:
                return self.async_abort(reason="no_available_homes")

            return self.async_show_form(
                step_id="select_home",
                data_schema=vol.Schema(
                    {vol.Required(CONF_HOME_ID): vol.In(homes_options)}
                ),
            )

        self.home_id = user_input[CONF_HOME_ID]
        await self.async_set_unique_id(f"{self.home_id}")
        self._abort_if_unique_id_configured()
        return await self.async_step_install()

    async def async_step_install(self, data=None):
        """Create a config entry at completion of a flow and authorization"""
        data = {
            CONF_EMAIL: self.username,
            CONF_HOME_ID: self.home_id,
        }

        homes = await self.client.user.get_homes()
        for home in homes:
            if home['homeid'] == data[CONF_HOME_ID]:
                home_name = home['homename']
                return self.async_create_entry(title=home_name, data=data)


