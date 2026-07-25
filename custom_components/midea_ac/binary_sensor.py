"""Binary platform for Midea Smart AC."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (BinarySensorDeviceClass,
                                                    BinarySensorEntity)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import (MideaCoordinatorEntity, MideaDeviceUpdateCoordinator,
                          MideaGroup5Entity)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Setup the binary sensor platform for Midea Smart AC."""

    _LOGGER.info("Setting up binary sensor platform.")

    # Fetch coordinator from global data
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device

    # Create entities for supported features
    entities = []
    if hasattr(device, "filter_alert") and getattr(device, "supports_filter_reminder", False):
        entities.append(MideaBinarySensor(coordinator,
                                          "filter_alert",
                                          BinarySensorDeviceClass.PROBLEM,
                                          "filter_alert"
                                          ))

    if (hasattr(device, "self_clean_active")
            and (getattr(device, "supports_self_clean", False)
                 or getattr(device, "supports_automatic_cleaning", False))):
        translation_key = (
            "cleaning_cycle"
            if getattr(device, "supports_automatic_cleaning", False)
            else "self_clean"
        )
        entities.append(MideaBinarySensor(coordinator,
                                          "self_clean_active",
                                          BinarySensorDeviceClass.RUNNING,
                                          translation_key,
                                          entity_category=EntityCategory.DIAGNOSTIC,
                                          ))

    if getattr(device, "is_toshiba_iolife", False):
        for prop, translation_key, device_class in (
            ("quick_mode", "quick_mode", BinarySensorDeviceClass.RUNNING),
            ("air_monitor_enabled", "air_monitor", None),
            ("radar_active", "radar", BinarySensorDeviceClass.RUNNING),
            ("way_out_enabled", "way_out", None),
            ("air_clean_active", "air_clean", BinarySensorDeviceClass.RUNNING),
            ("air_clean_enabled", "air_clean_enabled", None),
            ("uvc_enabled", "uvc", None),
            ("timer_self_clean_enabled", "scheduled_cleaning", None),
            ("vertical_swing_active", "vertical_swing",
             BinarySensorDeviceClass.RUNNING),
            ("horizontal_swing_active", "horizontal_swing",
             BinarySensorDeviceClass.RUNNING),
            ("power_on_timer_enabled", "power_on_timer", None),
            ("power_off_timer_enabled", "power_off_timer", None),
            ("high_temperature_monitor_enabled",
             "high_temperature_monitor", None),
            ("defrost_active", "defrost",
             BinarySensorDeviceClass.RUNNING),
            ("preheat_enabled", "preheat_enabled", None),
            ("preheat_active", "preheat_active",
             BinarySensorDeviceClass.RUNNING),
        ):
            if getattr(device, prop, None) is not None:
                entities.append(MideaBinarySensor(
                    coordinator,
                    prop,
                    device_class,
                    translation_key,
                    entity_category=EntityCategory.DIAGNOSTIC,
                ))

    if (hasattr(device, "defrost_active")
            and hasattr(device, "enable_group5_data_requests")
            and not getattr(device, "is_toshiba_iolife", False)):
        entities.append(MideaGroup5BinarySensor(coordinator,
                                                "defrost_active",
                                                BinarySensorDeviceClass.RUNNING,
                                                "defrost",
                                                entity_category=EntityCategory.DIAGNOSTIC,
                                                ))
    add_entities(entities)


class MideaBinarySensor(MideaCoordinatorEntity, BinarySensorEntity):
    """Binary sensor for Midea AC."""

    def __init__(self,
                 coordinator: MideaDeviceUpdateCoordinator,
                 prop: str,
                 device_class: BinarySensorDeviceClass | None,
                 translation_key: str | None = None,
                 *,
                 entity_category: EntityCategory = None) -> None:
        MideaCoordinatorEntity.__init__(self, coordinator)

        self._prop = prop
        self._device_class = device_class
        self._entity_category = entity_category
        self._attr_translation_key = translation_key

    @property
    def device_info(self) -> dict:
        """Return info for device registry."""
        return {
            "identifiers": {
                (DOMAIN, self._device.id)
            },
        }

    @property
    def has_entity_name(self) -> bool:
        """Indicates if entity follows naming conventions."""
        return True

    @property
    def unique_id(self) -> str:
        """Return the unique ID of this entity."""
        return f"{self._device.id}-{self._prop}"

    @property
    def device_class(self) -> str:
        """Return the device class of this entity."""
        return self._device_class

    @property
    def entity_category(self) -> str:
        """Return the entity category of this entity."""
        return self._entity_category

    @property
    def is_on(self) -> bool | None:
        """Return the on state of this entity."""
        return getattr(self._device, self._prop, None)


class MideaGroup5BinarySensor(MideaBinarySensor, MideaGroup5Entity):
    """Binary sensor for Midea AC group 5 data."""

    def __init__(self,
                 *args,
                 **kwargs
                 ) -> None:
        MideaBinarySensor.__init__(self, *args, **kwargs)

        # Group5 sensors start disabled in case device doesn't support them
        self._attr_entity_registry_enabled_default = False
