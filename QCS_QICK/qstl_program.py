"""Python driver for QICK control for QSTL"""
from __future__ import annotations
from pathlib import Path
from typing import (
    Iterable,
    Optional,
)

from qstl_channel import (
    Channels,
    SingleVirtualChannel
)
from qstl_variable import (
    Variable,
    Scalar,
)
from qstl_waveform import (
    HardwareOperation,
    Synchronize,
    BaseOperation,
    Delay,
)

class Sweep:
    def __init__(
        self,
        start: float,
        step: float,
        number: int,
        name: Optional[str] = None,
    ):
        self.start = start
        self.step = step
        self.number = number
        self.name = name

class Program:
    r"""
    A program described as a sequence of back-to-back layers, where each layer describes
    all the control instructions to be performed during a time interval.

    :param layers: The layers of this program.
    :param name: The name of this program.
    :param save_path: The path to save the program to.
    """
    def __init__(
        self,
        name: str | None = None,
        save_path: str | Path | None = None,
    ) -> None:
        self.name = "Program" if name is None else name
        self.save_path = save_path
        self.results = None
        self.repetitions = None
        self.save_path = None
        self.variables = None
        self._n_shots = 1

        self.operations: list[
            tuple[SingleVirtualChannel, BaseOperation] |
            Synchronize
        ] = []

    def add_acquisition(
        self,
        integration_filter: (
            HardwareOperation
            | float
            | Scalar
        ),
        channels: Channels | SingleVirtualChannel,
        new_layer: Optional[bool] = None,
        pre_delay: Variable | float | None = None,
    ) -> None:
        r"""
        Adds an acquisition to perform on a digitizer channel.

        The channels are added to the results attribute to enable the results to be
        retrieved by channel.

        :param integration_filter: The integration filter to be used when integrating
            the acquired data, or a duration in seconds for a raw acquisition.
        :param channels: The channels to acquire results from.
        :param classifier: The classifiers used to classify the integrated acquisition.
        :param new_layer: Whether to insert the operation into a new layer. The default
            of ``None`` will insert in the last layer if possible otherwise it will
            insert into a new layer.
        :param pre_delay: An optional delay in seconds to insert before the operation.
        """
        if pre_delay is not None:
            pre_delay = Delay(
                duration = pre_delay,
            )
            self.operations.append(
                (channels, pre_delay)
            )
        if new_layer is True:
            self.operations.append(
                Synchronize()
            )
        if isinstance(channels, SingleVirtualChannel):
            self.operations.append(
                (channels, integration_filter)
            )
        else:
            self.operations.append(
                Synchronize()
            )
            for ch in channels:
                self.operations.append(
                    (ch, integration_filter)
                )

    def add_waveform(
        self,
        pulse: HardwareOperation,
        channels: Channels | SingleVirtualChannel,
        new_layer: Optional[bool] = None,
        pre_delay: Variable | float | Iterable[float] | None = None,
    ) -> None:
        r"""
        Adds a waveform to play on an AWG channel.

        :param pulse: The waveform to play.
        :param channels: The channels on which to play the waveform.
        :param new_layer: Whether to insert the operation into a new layer. The default
            of ``None`` will insert in the last layer if possible otherwise it will
            insert into a new layer.
        :param pre_delay: The delay in seconds to insert before the operation.
        """
        if pre_delay is not None:
            pre_delay = Delay(
                duration = pre_delay,
            )
            self.operations.append(
                (channels, pre_delay)
            )
        if new_layer is True:
            self.operations.append(
                Synchronize()
            )
        if isinstance(channels, SingleVirtualChannel):
            self.operations.append(
                (channels, pulse)
            )
        else:
            self.operations.append(
                Synchronize()
            )
            for ch in channels:
                self.operations.append(
                    (ch, pulse)
                )

    def declare(self, variable: Variable) -> Variable:
        r"""
        Declares a variable as part of this program.

        :param variable: The variable to be declared.
        """
        raise NotImplementedError

    def n_shots(self, num_reps: int) -> Program:
        r"""
        Repeat this program a specified number of times.

        :param num_reps: The number of times to repeat this program.
        :raises Warning: If `n_shots` has already been called on this program.
        """
        self._n_shots = num_reps
        return self

    def sweep(
        self,
        sweep_values: Sweep | tuple[Sweep],
        targets: Variable | tuple[Variable]
    ) -> Program:
        r"""
        Creates a program that sweeps a target variable. Additionally, can sweep
        several targets provided their sweep value shapes are compatible.

        :param sweep_values: The values to sweep.
        :param targets: The variables of this program to sweep.
        :raises ValueError: If the number of targets does not match the number of sweep
            values.
        """
        raise NotImplementedError
