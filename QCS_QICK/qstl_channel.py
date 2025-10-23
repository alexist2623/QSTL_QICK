from __future__ import annotations
from typing import (
    Iterable,
    Optional,
)
from dataclasses import dataclass
import re

from qstl_variable import (
    Scalar,
)

class SingleVirtualChannel:
    def __init__(
        self,
        name: str,
        absolute_phase: bool
    ):
        self.last_time = 0
        self.name = name
        self.absolute_phase = absolute_phase

class Channels:
    r"""
    A collection of channels to target.

    Channels are destinations for channel-level operations. Channels
    that are grouped together can be used as a target for a common operation. Individual
    channels are identified by an integer label and the name of the collection.

    :param labels: An iterable of channel labels, or an integer representing a single
        label.
    :param name: The name of this channel collection.
    :param absolute_phase: Whether :py:class:`~keysight.qcs.channels.RFWaveform`\s
        played on the channels in this collection are rendered with a relative
        or an absolute phase.
    :raises ValueError: If the name contains symbols other than letters, numbers and
        underscores.
    """
    def __init__(
        self,
        labels: int | Iterable[int],
        name: str | None = None,
        absolute_phase: bool = False,
    ) -> None:
        self.labels = labels if isinstance(labels, Iterable) else [0]
        self.name = "channels" if name is None else name
        self.absolute_phase = absolute_phase
        self._channels = (
            [
                SingleVirtualChannel(self.name + "_" + str(x), absolute_phase) for x in range(len(labels))
            ] if isinstance(labels, Iterable) else [
                SingleVirtualChannel(self.name + "_0", absolute_phase)
            ]
        )
        if not re.match("^[A-Za-z0-9_]*$", name):
            raise ValueError(
                "Channel names can only contain letters, numbers and underscores."
            )

    def __getitem__(self, idx: int = 0) -> SingleVirtualChannel:
        return self._channels[idx]


@dataclass
class InstrumentEnum:
    RF = "RF"
    DC = "DC"
    Digitizer = "Digitizer"

class PhysicalChannel:
    def __init__(self, addr: int, inst_type: InstrumentEnum):
        self.addr: int = addr
        self.inst_type: InstrumentEnum = inst_type

class ChannelMapper:
    r"""
    Virtual to physical channel mapping.
    """
    def __init__(
        self,
        ip_address: Optional[str] = None
    ):
        self.ip_address: str | None = None if ip_address is None else ip_address
        self.channels: list[Channels] = []
        self.physical_channels: list[PhysicalChannel] = []
        self.out_channel_map: dict[int, PhysicalChannel] = {}
        self.in_channel_map: dict[int, PhysicalChannel] = {}

    def add_channel_mapping(
        self,
        channels: Channels,
        addresses: int | Iterable[int],
        instrument_types: InstrumentEnum | Iterable[InstrumentEnum],
    ) -> None:
        r"""
        Adds a channel configuration

        :param channels: The channels to map from.
        :param addresses: The physical channel addresses to map to.
        :param instrument_types: The type of instrument present at ``address``.
        :raises ValueError: If the number of physical channels does not match
            the number of labels.
        :raises ValueError: If the attributes of ``channels`` does not
            match those specified in the channel map.
        """
        addresses = addresses if isinstance(addresses, list) else [addresses]
        if not isinstance(instrument_types, list):
            instrument_types = [instrument_types] * len(addresses)
        if len(channels.labels) != len(instrument_types):
            raise ValueError(
                "The number of instrument_types must be one "
                "or must match the number of labels."
            )
        for channel, addr, inst_type in zip(channels, addresses, instrument_types):
            if inst_type in (
                InstrumentEnum.RF,
                InstrumentEnum.DC,
            ):
                self.out_channel_map.update(
                    {
                        channel: PhysicalChannel(addr, inst_type)
                    }
                )
            elif inst_type in (
                InstrumentEnum.Digitizer,
            ):
                self.in_channel_map.update(
                    {
                        channel: PhysicalChannel(addr, inst_type)
                        for channel, addr, inst_type in zip(channels, addresses, instrument_types)
                    }
                )
    def add_downconverters(
        self,
        dig_addresses: int | Iterable[int],
        downcon_addresses: int,
    ) -> None:
        r"""
        No downconverter in QICK
        """
        raise NotImplementedError

    def get_downconverter(
        self, channel: PhysicalChannel
    ) -> PhysicalChannel | None:
        r"""
        No downconverter in QICK
        """
        raise NotImplementedError

    def get_physical_channel(
        self, channel: SingleVirtualChannel
    ) -> PhysicalChannel:
        r"""
        Return physical channel of virtual channel
        """
        if channel in self.out_channel_map:
            return self.out_channel_map[channel]
        elif channel in self.in_channel_map:
            return self.in_channel_map[channel]
        else:
            raise ValueError(
                f"No physical channel found for virtual channel {channel}."
            )

    def get_physical_channels(self, channels: Channels) -> list[PhysicalChannel]:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError

    def get_virtual_channels(
        self, address: int, out: bool = True
    ) -> Iterable[Channels]:
        r"""
        Returns the :py:class:`~keysight.qcs.channels.Channels`\s for the given address.

        :param address: The address to get the virtual channels of.
        """
        for channel in (
            self.out_channel_map if out else self.in_channel_map
        ).values():
            if channel.addr == address:
                return channel
        raise ValueError(f"No channel found with address {address}.")

    def constrain_lo_frequencies(
        self,
        addresses: int,
        min_freq: float,
        max_freq: float,
    ) -> float:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError

    def set_delays(
        self,
        addresses: int
        | list[int],
        delays: float | list[float] | Scalar | list[Scalar],
    ) -> None:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError
