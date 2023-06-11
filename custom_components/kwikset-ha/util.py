from typing import Any

from aiokwikset import API
from aiokwikset.errors import RequestError, NotAuthorized

from homeassistant import exceptions

from .const import LOGGER

# Create a single instance of KwikSet API that is
# used during the initial config flow and afterwards by
# the update coordinator.
KWIKSET_CLIENT = API("")

async def async_connect_api(username, password, code_type) -> None:
    """Start the connection to the API"""

    #initialize API
    KWIKSET_CLIENT.username = username
    client = KWIKSET_CLIENT

    try:
        #start authentication
        pre_auth = await client.authenticate(password, code_type)
    except NotAuthorized as err:
        LOGGER.error("Your refresh token has been revoked and you must re-authenticate the integration")
        raise NotAuthorized from err
    except RequestError as err:
        LOGGER.error("Error connecting to the kwikset API: %s", err)
        raise CannotConnect from err
    
    return pre_auth
    
async def async_validate_api(pre_auth: Any, code: str) -> None:
    """Validate the code and connect to the API"""
    client = KWIKSET_CLIENT
    #MFA verification
    await client.verify_user(pre_auth, code)
    
class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""