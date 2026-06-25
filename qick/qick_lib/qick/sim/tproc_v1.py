"""ASM v1 tProcessor behavior simulator."""

from .virtual_hw import install_pynq_stubs

install_pynq_stubs()

from qick.awg_tuning import TProcV1BehaviorModel, TimedCommandEvent  # noqa: E402


class TProcV1Sim(TProcV1BehaviorModel):
    """Public qick.sim name for the ASM v1 behavior interpreter."""

    @classmethod
    def handlers(cls):
        return cls.handler_names()


__all__ = ["TProcV1Sim", "TimedCommandEvent"]
