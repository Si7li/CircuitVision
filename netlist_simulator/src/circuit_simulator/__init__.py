"""
Circuit Simulator - Automatic SPICE .cir File Simulator and Plotter

A Python package for automatically simulating and plotting SPICE circuit netlists.
"""

__version__ = "1.0.0"
__author__ = "Circuit Simulator Team"

from .simulator import CircuitSimulator, SimulationResult, ComponentVoltage
from .plotter import CircuitPlotter
from .config import SimulationConfig, PlotConfig, PlotType

__all__ = [
    "CircuitSimulator",
    "CircuitPlotter", 
    "SimulationConfig",
    "PlotConfig",
    "PlotType",
    "SimulationResult",
    "ComponentVoltage",
]
