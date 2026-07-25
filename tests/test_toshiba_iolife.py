"""Tests for Toshiba IoLIFE integration support."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant import config_entries
from homeassistant.components.climate.const import PRESET_SLEEP
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from msmart.const import DeviceType
from msmart.device import ToshibaIoLifeAirConditioner

from custom_components.midea_ac.climate import MideaClimateACDevice
from custom_components.midea_ac.const import (CONF_BEEP, CONF_DEVICE_PROTOCOL,
                                              CONF_DEVICE_TYPE, DOMAIN,
                                              DeviceProtocol)
from custom_components.midea_ac.device import (construct_device,
                                               construct_selected_device,
                                               protocol_for_device)
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


async def test_self_clean_method_switch() -> None:
    """The Toshiba cleaning switch calls both control methods."""
    device = MagicMock()
    device.id = 1234
    device.self_clean_active = False
    device.start_self_clean = AsyncMock()
    device.stop_self_clean = AsyncMock()
    coordinator = MagicMock()
    coordinator.device = device
    coordinator.async_request_refresh = AsyncMock()

    entity = MideaMethodSwitch(
        coordinator,
        "self_clean_active",
        "start_self_clean",
        "stop_self_clean",
        "self_clean",
    )

    await entity.async_turn_on()
    device.start_self_clean.assert_awaited_once()

    await entity.async_turn_off()
    device.stop_self_clean.assert_awaited_once()
    assert coordinator.async_request_refresh.await_count == 2
