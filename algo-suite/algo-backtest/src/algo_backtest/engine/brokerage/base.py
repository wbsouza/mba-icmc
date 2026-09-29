"""The BrokerageAdapter port: config-selected fill/fee/spread model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BrokerageAdapter(ABC):
    """Applies one brokerage simulation model to a running QCAlgorithm.

    Concrete adapters call the algorithm's real ``set_brokerage_model`` (or
    equivalent) so the fill/fee/spread model is config-selected, never
    hardcoded into ``engine/algorithm.py``.
    """

    name: str

    @abstractmethod
    def apply(self, algorithm: Any) -> None:
        """Apply this brokerage model to ``algorithm`` before the first bar."""
