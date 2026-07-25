"""Device construction helpers for Midea Smart AC."""
from __future__ import annotations

from typing import Any

from msmart.base_device import Device
from msmart.const import DeviceType
from msmart.device import (AirConditioner, CommercialAirConditioner,
                           ToshibaIoLifeAirConditioner)

from .const import DeviceProtocol

DEVICE_SELECTIONS = {
    "AC": (DeviceType.AIR_CONDITIONER, DeviceProtocol.MIDEA),
    "CC": (DeviceType.COMMERCIAL_AC, DeviceProtocol.MIDEA),
    "TOSHIBA_IOLIFE": (
        DeviceType.AIR_CONDITIONER,
        DeviceProtocol.TOSHIBA_IOLIFE,
    ),
}


def protocol_for_device(
    device: AirConditioner | CommercialAirConditioner,
) -> DeviceProtocol:
    """Return the protocol needed to reconstruct a discovered device."""
    if isinstance(device, ToshibaIoLifeAirConditioner):
        return DeviceProtocol.TOSHIBA_IOLIFE
    return DeviceProtocol.MIDEA


def construct_device(
    *,
    device_type: DeviceType | int,
    protocol: DeviceProtocol | str = DeviceProtocol.MIDEA,
    **kwargs: Any,
) -> AirConditioner | CommercialAirConditioner | Device:
    """Construct the correct msmart device class from persisted config."""
    protocol = DeviceProtocol(protocol)
    if protocol is DeviceProtocol.TOSHIBA_IOLIFE:
        if DeviceType(device_type) is not DeviceType.AIR_CONDITIONER:
            raise ValueError("Toshiba IoLIFE protocol requires AC device type")
        return ToshibaIoLifeAirConditioner(**kwargs)
    return Device.construct(type=DeviceType(device_type), **kwargs)


def construct_selected_device(
    selection: str,
    **kwargs: Any,
) -> AirConditioner | CommercialAirConditioner | Device:
    """Construct a device from the manual config-flow selection."""
    try:
        device_type, protocol = DEVICE_SELECTIONS[selection.upper()]
    except KeyError as error:
        raise ValueError(f"Unknown device selection: {selection}") from error
    return construct_device(
        device_type=device_type,
        protocol=protocol,
        **kwargs,
    )
