"""
Agente base — todos los agentes heredan de esta clase.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Agent(ABC):
    """Interfaz común para todos los agentes del sistema."""

    @abstractmethod
    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Procesa los datos de entrada y devuelve el resultado.
        
        Cada agente recibe un dict con lo que necesita y devuelve
        un dict con el resultado para el siguiente paso del pipeline.
        """
        ...