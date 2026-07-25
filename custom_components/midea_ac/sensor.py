"""Sensor platform for Midea Smart AC."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (PERCENTAGE, EntityCategory, UnitOfEnergy,
                                 UnitOfPower, UnitOfTemperature, UnitOfTime)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from msmart.utils import MideaIntEnum

from .const import (CONF_ENERGY_DATA_FORMAT, CONF_ENERGY_DATA_SCALE,
                    CONF_ENERGY_SENSOR, CONF_POWER_SENSOR, DOMAIN,
                    EnergyFormat)
from .coordinator import (MideaCoordinatorEntity, MideaDeviceUpdateCoordinator,
                          MideaGroup5Entity)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Setup the sensor platform for Midea Smart AC."""

    _LOGGER.info("Setting up sensor platform.")

    # Fetch coordinator from global data
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device

    entities = [
        # Temperature sensors
        MideaSensor(
            coordinator,
            "indoor_temperature",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            "indoor_temperature",
        ),
        MideaSensor(
            coordinator,
            "outdoor_temperature",
            SensorDeviceClass.TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            "outdoor_temperature",
        ),
    ]

    if hasattr(device, "indoor_humidity") and getattr(device, "supports_humidity", False):
        entities.append(MideaSensor(
            coordinator,
            "indoor_humidity",
            SensorDeviceClass.HUMIDITY,
            PERCENTAGE,
            "indoor_humidity",
        ))

    if getattr(device, "is_toshiba_iolife", False):
        for prop, translation_key in (
            ("actual_fan_speed", "actual_fan_speed"),
            ("vertical_deflector_position",
             "vertical_deflector_position"),
            ("horizontal_deflector_position",
             "horizontal_deflector_position"),
            ("high_temperature_monitor_status",
             "high_temperature_monitor_status"),
            ("dehumidification_mode", "dehumidification_mode"),
            ("advanced_no_wind_mode", "advanced_no_wind_mode"),
            ("wind_radar_mode", "wind_radar_mode"),
            ("area_mode", "area_mode"),
            ("air_monitor_status", "air_monitor_status"),
            ("radar_zone_mask", "radar_zone_mask"),
        ):
            if getattr(device, prop, None) is not None:
                entities.append(MideaSensor(
                    coordinator,
                    prop,
                    None,
                    None,
                    translation_key,
                    state_class=None,
                    entity_category=EntityCategory.DIAGNOSTIC,
                ))

        for prop, enabled_prop, translation_key in (
            ("power_on_timer_minutes", "power_on_timer_enabled",
             "power_on_timer"),
            ("power_off_timer_minutes", "power_off_timer_enabled",
             "power_off_timer"),
        ):
            if getattr(device, enabled_prop, None) is not None:
                entities.append(MideaSensor(
                    coordinator,
                    prop,
                    SensorDeviceClass.DURATION,
                    UnitOfTime.MINUTES,
                    translation_key,
                    state_class=None,
                    entity_category=EntityCategory.DIAGNOSTIC,
                ))

    # Only add energy sensors if device supports energy requests
    if (hasattr(device, "enable_energy_usage_requests")
            and not getattr(device, "is_toshiba_iolife", False)):
        def _get_energy_config(key: str) -> tuple[EnergyFormat, float]:
            config = config_entry.options.get(key)
            format = device.EnergyDataFormat.get_from_name(
                config.get(CONF_ENERGY_DATA_FORMAT).upper())
            scale = config.get(CONF_ENERGY_DATA_SCALE)
            return format, scale

        # Configure energy format
        energy_data_format, energy_scale = _get_energy_config(
            CONF_ENERGY_SENSOR)
        _LOGGER.info(
            "Using energy format %r (scale: %f) for device ID %s.", energy_data_format, energy_scale, coordinator.device.id)

        power_data_format, power_scale = _get_energy_config(CONF_POWER_SENSOR)
        _LOGGER.info(
            "Using power format %r (scale: %f) for device ID %s.", power_data_format, power_scale, coordinator.device.id)

        entities.extend(
            [
                # Energy sensors
                MideaEnergySensor(
                    coordinator,
                    "total_energy_usage",
                    SensorDeviceClass.ENERGY,
                    UnitOfEnergy.KILO_WATT_HOUR,
                    "total_energy_usage",
                    format=energy_data_format,
                    scale=energy_scale,
                    state_class=SensorStateClass.TOTAL,
                ),
                MideaEnergySensor(
                    coordinator,
                    "current_energy_usage",
                    SensorDeviceClass.ENERGY,
                    UnitOfEnergy.KILO_WATT_HOUR,
                    "current_energy_usage",
                    format=energy_data_format,
                    scale=energy_scale,
                    state_class=SensorStateClass.TOTAL_INCREASING,
                ),
                MideaEnergySensor(
                    coordinator,
                    "real_time_power_usage",
                    SensorDeviceClass.POWER,
                    UnitOfPower.WATT,
                    "real_time_power_usage",
                    format=power_data_format,
                    scale=power_scale,
                )
            ])

    if (hasattr(device, "outdoor_fan_speed")
            and hasattr(device, "enable_group5_data_requests")
            and not getattr(device, "is_toshiba_iolife", False)):
        entities.append(MideaGroup5Sensor(
            coordinator,
            "outdoor_fan_speed",
            None,
            None,
            "outdoor_fan_speed",
        ))

    add_entities(entities)


class MideaSensor(MideaCoordinatorEntity, SensorEntity):
    """Generic sensor class for Midea AC."""

    def __init__(self,
                 coordinator: MideaDeviceUpdateCoordinator,
                 prop: str,
                 device_class: SensorDeviceClass | None,
                 unit: str | None,
                 translation_key: str | None = None,
                 *,
                 state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT,
                 entity_category: EntityCategory | None = None,
                 ) -> None:
        MideaCoordinatorEntity.__init__(self, coordinator)

        self._prop = prop
        self._device_class = device_class
        self._state_class = state_class
        self._unit = unit
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
    def available(self) -> bool:
        """Check entity availability."""

        # Sensor is unavailable if device is offline or value is None
        return super().available and self.native_value is not None

    @property
    def device_class(self) -> str:
        """Return the device class of this entity."""
        return self._device_class

    @property
    def state_class(self) -> str | None:
        """Return the state class of this entity."""
        return self._state_class

    @property
    def entity_category(self) -> str | None:
        """Return the entity category of this entity."""
        return self._entity_category

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the native units of this entity."""
        return self._unit

    @property
    def native_value(self) -> float | None:
        """Return the current native value."""
        return getattr(self._device, self._prop, None)


class MideaEnergySensor(MideaSensor):
    """Energy sensor class for Midea AC."""

    def __init__(self,
                 *args,
                 format: MideaIntEnum,
                 scale: float = 1.0,
                 **kwargs) -> None:
        MideaSensor.__init__(self, *args, **kwargs)

        self._format = format
        self._scale = scale
        self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Call super method to ensure lifecycle is properly handled
        await super().async_added_to_hass()

        # Register energy sensor with coordinator
        self.coordinator.register_energy_sensor()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        # Call super method to ensure lifecycle is properly handled
        await super().async_will_remove_from_hass()

        # Unregister energy sensor with coordinator
        self.coordinator.unregister_energy_sensor()

    @property
    def native_value(self) -> float | None:
        """Return the scaled native value."""
        # Manually prepend 'get_' to the property.
        # This is so we don't have to change prop which causes unique ids to change
        get_method = getattr(self._device, f"get_{self._prop}", None)
        if get_method and callable(get_method):
            value = get_method(self._format)
        else:
            value = None

        if value is None:
            return None

        return value * self._scale


class MideaGroup5Sensor(MideaSensor, MideaGroup5Entity):
    """Sensor for Midea AC group 5 data."""

    def __init__(self,
                 *args,
                 **kwargs
                 ) -> None:
        MideaSensor.__init__(self, *args, **kwargs)

        # Group5 sensors start disabled in case device doesn't support them
        self._attr_entity_registry_enabled_default = False
