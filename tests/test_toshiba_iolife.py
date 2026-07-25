"""Tests for Toshiba IoLIFE integration support."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant import config_entries
from homeassistant.components.climate.const import PRESET_SLEEP
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from msmart.const import DeviceType
from msmart.device import ToshibaIoLifeAirConditioner, ToshibaProperty

from custom_components.midea_ac.binary_sensor import \
    async_setup_entry as async_setup_binary_sensors
from custom_components.midea_ac.climate import MideaClimateACDevice
from custom_components.midea_ac.const import (CONF_BEEP, CONF_DEVICE_PROTOCOL,
                                              CONF_DEVICE_TYPE, DOMAIN,
                                              DeviceProtocol)
from custom_components.midea_ac.device import (construct_device,
                                               construct_selected_device,
                                               protocol_for_device)
from custom_components.midea_ac.sensor import \
    async_setup_entry as async_setup_sensors
from custom_components.midea_ac.switch import MideaMethodSwitch


def test_toshiba_device_construction() -> None:
    """The persisted and config-flow constructors preserve the subclass."""
    connection = {
        "ip": "127.0.0.1",
        "port": 6444,
        "device_id": 1234,
    }
    selected = construct_selected_device("TOSHIBA_IOLIFE", **connection)
    persisted = construct_device(
        device_type=DeviceType.AIR_CONDITIONER,
        protocol=DeviceProtocol.TOSHIBA_IOLIFE,
        **connection,
    )

    assert isinstance(selected, ToshibaIoLifeAirConditioner)
    assert isinstance(persisted, ToshibaIoLifeAirConditioner)
    assert protocol_for_device(selected) is DeviceProtocol.TOSHIBA_IOLIFE


async def test_manual_toshiba_flow(hass: HomeAssistant) -> None:
    """Manual setup stores the protocol needed after a restart."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "manual"}
    )

    with (
        patch("custom_components.midea_ac.async_setup_entry",
              return_value=True),
        patch(
            "custom_components.midea_ac.device."
            "ToshibaIoLifeAirConditioner.refresh",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.midea_ac.device."
            "ToshibaIoLifeAirConditioner.online",
            new_callable=PropertyMock,
            return_value=True,
        ),
        patch(
            "custom_components.midea_ac.device."
            "ToshibaIoLifeAirConditioner.supported",
            new_callable=PropertyMock,
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": "127.0.0.1",
                "port": 6444,
                "id": "1234",
                CONF_DEVICE_TYPE: "TOSHIBA_IOLIFE",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE_TYPE] == DeviceType.AIR_CONDITIONER
    assert (
        result["data"][CONF_DEVICE_PROTOCOL]
        is DeviceProtocol.TOSHIBA_IOLIFE
    )
    assert result["options"][CONF_BEEP] is False


async def test_toshiba_climate_configuration(
    hass: HomeAssistant,
) -> None:
    """Toshiba climate omits unsupported Midea presets and branding."""
    device = ToshibaIoLifeAirConditioner(
        ip="127.0.0.1", port=6444, device_id=1234)
    coordinator = MagicMock()
    coordinator.device = device
    coordinator.apply = AsyncMock()

    entity = MideaClimateACDevice(hass, coordinator, {})

    assert PRESET_SLEEP not in entity.preset_modes
    assert entity.device_info["manufacturer"] == "Toshiba"
    assert entity.device_info["model"] == "IoLIFE"
    assert "follow_me" not in entity.extra_state_attributes


async def test_automatic_cleaning_method_switch() -> None:
    """The Toshiba auto-clean switch calls both preference methods."""
    device = MagicMock()
    device.id = 1234
    device.automatic_cleaning_enabled = False
    device.enable_automatic_cleaning = AsyncMock()
    device.disable_automatic_cleaning = AsyncMock()
    coordinator = MagicMock()
    coordinator.device = device
    coordinator.async_request_refresh = AsyncMock()

    entity = MideaMethodSwitch(
        coordinator,
        "automatic_cleaning_enabled",
        "enable_automatic_cleaning",
        "disable_automatic_cleaning",
        "automatic_cleaning",
    )

    await entity.async_turn_on()
    device.enable_automatic_cleaning.assert_awaited_once()

    await entity.async_turn_off()
    device.disable_automatic_cleaning.assert_awaited_once()
    assert coordinator.async_request_refresh.await_count == 2


async def test_extended_toshiba_binary_sensors(
    hass: HomeAssistant,
) -> None:
    """K-DR extended states become read-only diagnostic entities."""
    device = ToshibaIoLifeAirConditioner(
        ip="127.0.0.1", port=6444, device_id=1234)
    device._has_extended_state = True
    device._supported_toshiba_properties.update({
        ToshibaProperty.QUICK_MODE,
        ToshibaProperty.WIND_RADAR,
        ToshibaProperty.WAY_OUT,
        ToshibaProperty.AIR_CLEAN_SWITCH,
        ToshibaProperty.TIMER_SELF_CLEAN,
        ToshibaProperty.WIND_DEFLECTOR,
        ToshibaProperty.POWER_ON_TIMER,
        ToshibaProperty.POWER_OFF_TIMER,
        ToshibaProperty.HIGH_TEMPERATURE_MONITOR,
    })
    device._vertical_deflector_position = 25
    device._horizontal_deflector_position = 1
    device._vertical_swing_active = True
    device._horizontal_swing_active = True
    device._power_on_timer_enabled = False
    device._power_off_timer_enabled = False
    device._high_temperature_monitor_enabled = False
    device._defrost_active = False
    device._preheat_enabled = False
    device._preheat_active = False
    device._quick_mode = False
    device._air_monitor_enabled = True
    device._radar_active = True
    device._way_out_enabled = False
    device._air_clean_active = False
    device._air_clean_enabled = False
    device._uvc_enabled = True
    device._timer_self_clean_enabled = False
    coordinator = MagicMock()
    coordinator.device = device
    config_entry = MagicMock()
    config_entry.entry_id = "toshiba-k-dr"
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator
    entities = []

    await async_setup_binary_sensors(
        hass,
        config_entry,
        entities.extend,
    )

    translation_keys = {
        entity.translation_key
        for entity in entities
    }
    assert {
        "quick_mode",
        "air_monitor",
        "radar",
        "way_out",
        "air_clean",
        "air_clean_enabled",
        "uvc",
        "scheduled_cleaning",
        "vertical_swing",
        "horizontal_swing",
        "power_on_timer",
        "power_off_timer",
        "high_temperature_monitor",
        "defrost",
        "preheat_enabled",
        "preheat_active",
    } <= translation_keys


async def test_toshiba_telemetry_sensors(
    hass: HomeAssistant,
) -> None:
    """Confirmed Toshiba telemetry becomes read-only diagnostic sensors."""
    device = ToshibaIoLifeAirConditioner(
        ip="127.0.0.1", port=6444, device_id=4321)
    device._has_extended_state = True
    device._supported_toshiba_properties.update({
        ToshibaProperty.FAN_SPEED_REAL,
        ToshibaProperty.WIND_DEFLECTOR,
        ToshibaProperty.POWER_ON_TIMER,
        ToshibaProperty.POWER_OFF_TIMER,
        ToshibaProperty.HIGH_TEMPERATURE_MONITOR,
        ToshibaProperty.DEHUMIDIFY,
        ToshibaProperty.NEW_NO_WIND_SENSE,
        ToshibaProperty.WIND_RADAR,
        ToshibaProperty.AREA,
    })
    device._actual_fan_speed = 20
    device._vertical_deflector_position = 25
    device._horizontal_deflector_position = 1
    device._power_on_timer_enabled = False
    device._power_off_timer_enabled = False
    device._high_temperature_monitor_status = 0
    device._dehumidification_mode = 1
    device._advanced_no_wind_mode = 0
    device._wind_radar_mode = 0
    device._area_mode = 0
    device._air_monitor_status = 1
    device._radar_zone_mask = 0
    coordinator = MagicMock()
    coordinator.device = device
    config_entry = MagicMock()
    config_entry.entry_id = "toshiba-k-dr-sensors"
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator
    entities = []

    await async_setup_sensors(
        hass,
        config_entry,
        entities.extend,
    )

    translation_keys = {
        entity.translation_key
        for entity in entities
    }
    assert {
        "actual_fan_speed",
        "vertical_deflector_position",
        "horizontal_deflector_position",
        "power_on_timer",
        "power_off_timer",
        "high_temperature_monitor_status",
        "dehumidification_mode",
        "advanced_no_wind_mode",
        "wind_radar_mode",
        "area_mode",
        "air_monitor_status",
        "radar_zone_mask",
    } <= translation_keys


async def test_unsupported_extended_toshiba_binary_sensors_are_omitted(
    hass: HomeAssistant,
) -> None:
    """Reserved state bits cannot enable features absent from the model."""
    device = ToshibaIoLifeAirConditioner(
        ip="127.0.0.1", port=6444, device_id=5678)
    # Simulate stale or incorrectly parsed internal values. Public state must
    # remain unknown unless the appliance confirms extended-state support.
    device._quick_mode = True
    device._air_monitor_enabled = True
    device._radar_active = True
    device._way_out_enabled = True
    device._air_clean_active = True
    device._air_clean_enabled = True
    device._uvc_enabled = True
    device._timer_self_clean_enabled = True
    device._vertical_swing_active = True
    device._horizontal_swing_active = True
    device._power_on_timer_enabled = True
    device._power_off_timer_enabled = True
    device._high_temperature_monitor_enabled = True
    device._defrost_active = True
    device._preheat_enabled = True
    device._preheat_active = True
    coordinator = MagicMock()
    coordinator.device = device
    config_entry = MagicMock()
    config_entry.entry_id = "toshiba-j-dt"
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator
    entities = []

    await async_setup_binary_sensors(
        hass,
        config_entry,
        entities.extend,
    )

    extended_translation_keys = {
        "quick_mode",
        "air_monitor",
        "radar",
        "way_out",
        "air_clean",
        "air_clean_enabled",
        "uvc",
        "scheduled_cleaning",
        "vertical_swing",
        "horizontal_swing",
        "power_on_timer",
        "power_off_timer",
        "high_temperature_monitor",
        "defrost",
        "preheat_enabled",
        "preheat_active",
    }
    assert extended_translation_keys.isdisjoint({
        entity.translation_key
        for entity in entities
    })
