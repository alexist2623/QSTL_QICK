from __future__ import annotations
from typing import (
    Generator,
    Any,
)
from dataclasses import dataclass

@dataclass
class UnitsEnum:
    mV = "mV"
    V = "V"
    GHz = "GHz"
    MHz = "MHz"
    ns = "ns"
    us = "us"

    @classmethod
    def from_string(cls, unit: str) -> UnitsEnum:
        try:
            return cls[unit]
        except KeyError:
            raise ValueError(f"Invalid unit: {unit}")

class Variable:
    r"""
    An abstract base class for quantities whose values can be changed.
    """
    def __init__(self):
        if type(self) is Variable:
            raise TypeError(
                "Variable is an abstract base class and cannot be instantiated directly."
            )
        self.constant: bool = None
        self.dtype: type = None
        self.name: str = None
        self.parents: Generator[Variable] = None
        self.read_only: bool = None
        self.unit: UnitsEnum = None
        self.value: Any = None

    @classmethod
    def _from_value(
        cls,
        value: any,
        dtype: type | None = None
    ) -> Variable:
        r"""
        Create a Variable from a value or pass through a value that is already a
        variable.

        :param value: The value to create a variable from.
        :param dtype: The dtype of the variable to create.
        :raises ValueError: If ``value`` cannot be used to construct a subclass of this.
        """
        dtype = dtype or complex
        if isinstance(value, Variable):
            value._validate_type(dtype)
            return value
        for subclass in cls.__subclasses__():
            try:
                return subclass._from_value(value, dtype)
            except (TypeError, ValueError):
                pass
        raise ValueError(f"Could not construct a Variable from {value}.")

    def _validate_type(
        self,
        dtype: type
    ) -> None:
        r"""
        Validate that this variable has a specifed dtype.

        :raises ValueError: If ``dtype`` is not ``self.dtype``.
        """
        if self.dtype is not dtype:
            raise ValueError(f"The dtype of {self} is not {dtype}.")

    def __add__(self, other) -> Variable:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError

    def __truediv__(self, other) -> Variable:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError

    def __mul__(self, other) -> Variable:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError

    def __rsub__(self, other) -> Variable:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError

    def __rtruediv__(self, other) -> Variable:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError

    def __sub__(self, other) -> Variable:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError

    __radd__ = __add__

    __rdiv__ = __rtruediv__

    __rmul__ = __mul__

    __div__ = __truediv__

class Scalar(Variable):
    r"""
    A class for scalar quantities whose values are unknown or can be changed.

    .. jupyter-execute::

        import keysight.qcs as qcs

        # initialize a scalar with no set value
        scalar = qcs.Scalar("my_scalar", dtype=float)

        # initialize a scalar with set value
        scalar = qcs.Scalar("my_scalar", value=0.1, dtype=float)

    :param name: The name of scalar.
    :param value: The value of scalar, or ``None`` for a scalar with no set
        value.
    :param dtype: The dtype of scalar, which must be one of
        :py:class:`~keysight.qcs.utils.DTYPE_COERCIONS`\. Defaults to ``complex`` as
        it is the broadest supported type.
    :param unit: The unit of the scalar, which must be one of
        :py:class:`~keysight.qcs.variables.UnitsEnum`\. Defaults to None.
    :param read_only: Whether the scalar is read-only.
    :raises ValueError: If ``dtype`` is not one of
        :py:class:`~keysight.qcs.utils.DTYPE_COERCIONS`\.
    :raises ValueError: If the ``unit`` is not one of
        :py:class:`~keysight.qcs.variables.UnitsEnum`\.
    """
    def __init__(
        self,
        name: str,
        value: Any = None,
        dtype: type | None = None,
        unit: str | UnitsEnum | None = None,
        read_only: bool = False,
    ) -> None:
        if value is None:
            raise ValueError("Cannot create a Scalar with no set value in QICK.")
        self.dtype = dtype or complex
        self.value = None if value is None else dtype(value)

        if unit is not None:
            try:
                self.unit = (
                    unit if isinstance(unit, UnitsEnum) else UnitsEnum.from_string(unit)
                )
            except:
                raise ValueError

    @classmethod
    def _from_value(cls, value: any, dtype: type | None = None) -> Variable:
        r"""
        No reason to use this in QICK
        """
        raise NotImplementedError
    
    def get_value(self) -> Any:
        r"""
        Get the value of the scalar.

        :raises ValueError: If the scalar has no set value.
        """
        if self.value is None:
            raise ValueError(f"The value of {self.name} has not been set.")
        return self.value
