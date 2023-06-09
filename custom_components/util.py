from typing import Any

from aiokwikset import API
from aiokwikset.errors import RequestError, NotAuthorized

from homeassistant import exceptions

from .const import LOGGER

# Create a single instance of KwikSet API that is
# used during the initial config flow and afterwards by
# the update coordinator.
KWIKSET_CLIENT = API("")

async def async_connect_api(self, username: str, password: str, code_type: str) -> None:
    """Start the connection to the API"""

    try:
        #initialize API
        self.api = API(self.username)
        #start authentication
        self.pre_auth = await self.api.authenticate(self.password, self.code_type)
        LOGGER.debug(self.pre_auth)

    except NotAuthorized as err:
        LOGGER.error("Your refresh token has been revoked and you must re-authenticate the integration")
        raise NotAuthorized from err
    except RequestError as err:
        LOGGER.error("Error connecting to the kwikset API: %s", err)
        raise CannotConnect from err
    
    return self.pre_auth
    
async def async_validate_api(self, pre_auth: Any, code: str) -> None:
    """Validate the code and connect to the API"""
    #MFA verification
    await self.api.verify_user(pre_auth, code)
    
class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""