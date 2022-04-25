"""Support for locks through the Kwikset API."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from .const import DOMAIN as KWIKSET_DOMAIN, LOGGER
from .device import KwiksetDeviceDataUpdateCoordinator
from .entity import KwiksetEntity

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Rinnai Water heater from config entry."""
    devices: list[KwiksetDeviceDataUpdateCoordinator] = hass.data[KWIKSET_DOMAIN][
        config_entry.entry_id
    ]["devices"]
    entities = []
    for device in devices:
        entities.append(KwiksetLock(device, config_entry.options))
    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()

class KwiksetLock(KwiksetEntity, LockEntity):
    """Define a Kwikset lock."""

    def __init__(self, device: KwiksetDeviceDataUpdateCoordinator, options) -> None:
        """Initialize the lock heater."""
        super().__init__("lock",device.device_name,device)
        self.options = options

    async def async_lock(self, **kwargs):
        """Lock the device."""
        await self._device.lock()
        self._device.async_request_refresh()

    async def async_unlock(self, **kwargs):
        """Unlock the device."""
        await self._device.unlock()
        self._device.async_request_refresh()

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self._device.status == "Locked"