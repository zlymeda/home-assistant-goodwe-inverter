"""GoodWe PV inverter switch entities."""
import logging
from typing import Any

from goodwe import Inverter, InverterError
from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
    SwitchDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_DEVICE_INFO, KEY_INVERTER

_LOGGER = logging.getLogger(__name__)


SWITCHES: dict[str, SwitchEntityDescription] = {
    "load_control_switch": SwitchEntityDescription(
        key="load_control",
        translation_key="load_control",
        has_entity_name=True,
        entity_category=EntityCategory.CONFIG,
        device_class=SwitchDeviceClass.OUTLET,
    ),
    "grid_export": SwitchEntityDescription(
        key="grid_export",
        translation_key="grid_export",
        has_entity_name=True,
        entity_category=EntityCategory.CONFIG,
        device_class=SwitchDeviceClass.OUTLET,
    ),
}


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the inverter switch entities from a config entry."""
    inverter = hass.data[DOMAIN][config_entry.entry_id][KEY_INVERTER]
    device_info = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE_INFO]

    entities = []

    for setting_id in SWITCHES:
        try:
            current_value = await inverter.read_setting(setting_id)
        except (InverterError, ValueError):
            # Inverter model does not support this setting
            _LOGGER.debug("Could not read inverter setting %s", setting_id, exc_info=True)
            continue

        entities.append(
            InverterSwitchEntity(setting_id, device_info, SWITCHES[setting_id], inverter, current_value == 1)
        )

    if len(entities) > 0:
        async_add_entities(entities)


class InverterSwitchEntity(SwitchEntity):
    """Inverter switch setting entity."""

    _setting_id: str

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
            self,
            setting_id: str,
            device_info: DeviceInfo,
            description: SwitchEntityDescription,
            inverter: Inverter,
            current_state: bool,
    ) -> None:
        """Initialize the inverter switch setting entity."""
        self._setting_id = setting_id
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}-{description.key}-{inverter.serial_number}"
        self._attr_device_info = device_info
        self._attr_is_on = current_state
        self._inverter: Inverter = inverter

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self._write_setting(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self._write_setting(0)

    async def async_update(self):
        """Update the state of the inverter."""
        current_value = await self._inverter.read_setting(self._setting_id)
        self._attr_is_on = current_value == 1

    async def _write_setting(self, value):
        try:
            await self._inverter.write_setting(self._setting_id, value)
            self.async_schedule_update_ha_state(force_refresh=True)
        except InverterError as e:
            _LOGGER.error(
                "Error writing setting: %s=%s: %s",
                self._setting_id,
                value,
                e,
            )
