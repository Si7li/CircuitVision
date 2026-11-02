"""
Configuration classes for simulation and plotting settings.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


class SimulationType(Enum):
    """Supported simulation types."""
    TRANSIENT = "transient"
    AC = "ac"
    DC = "dc"
    AUTO = "auto"  # Auto-detect from .cir file


class PlotType(Enum):
    """Types of plots that can be generated."""
    OVERLAY = "overlay"       # All voltages on one plot
    INDIVIDUAL = "individual" # Separate subplot for each node
    CURRENTS = "currents"     # Branch currents
    COMPONENTS = "components" # Voltage differences across components
    ALL = "all"               # Generate all plot types


@dataclass
class SimulationConfig:
    """
    Configuration for circuit simulation parameters.
    
    Attributes:
        simulation_type: Type of simulation (transient, AC, DC, or auto-detect)
        temperature: Operating temperature in Celsius
        nominal_temperature: Nominal temperature in Celsius
        
        # Transient analysis parameters
        tran_step_time: Time step for transient analysis (seconds)
        tran_end_time: End time for transient analysis (seconds)
        
        # AC analysis parameters  
        ac_start_freq: Start frequency for AC analysis (Hz)
        ac_stop_freq: Stop frequency for AC analysis (Hz)
        ac_num_points: Number of frequency points
        ac_variation: Frequency variation type ('dec', 'oct', 'lin')
    """
    simulation_type: SimulationType = SimulationType.AUTO
    temperature: float = 25.0
    nominal_temperature: float = 25.0
    
    # Transient analysis defaults
    tran_step_time: float = 10e-6    # 10 microseconds
    tran_end_time: float = 10e-3     # 10 milliseconds
    
    # AC analysis defaults
    ac_start_freq: float = 1.0       # 1 Hz
    ac_stop_freq: float = 1e6        # 1 MHz
    ac_num_points: int = 100
    ac_variation: str = 'dec'
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.tran_step_time <= 0:
            raise ValueError("tran_step_time must be positive")
        if self.tran_end_time <= 0:
            raise ValueError("tran_end_time must be positive")
        if self.tran_step_time >= self.tran_end_time:
            raise ValueError("tran_step_time must be less than tran_end_time")
        if self.ac_start_freq <= 0:
            raise ValueError("ac_start_freq must be positive")
        if self.ac_stop_freq <= self.ac_start_freq:
            raise ValueError("ac_stop_freq must be greater than ac_start_freq")
        if self.ac_num_points < 2:
            raise ValueError("ac_num_points must be at least 2")
        if self.ac_variation not in ['dec', 'oct', 'lin']:
            raise ValueError("ac_variation must be 'dec', 'oct', or 'lin'")


@dataclass
class PlotConfig:
    """
    Configuration for plot generation and styling.
    
    Attributes:
        plot_types: List of plot types to generate
        selected_nodes: Specific nodes to plot (None = all nodes)
        exclude_nodes: Nodes to exclude from plotting
        
        # Figure settings
        figure_dpi: DPI for saved figures
        overlay_figsize: Figure size for overlay plot (width, height)
        individual_figsize_per_plot: Size per subplot in individual plot
        current_figsize: Figure size for current plot
        
        # Style settings
        colormap: Matplotlib colormap name for voltage plots
        current_colormap: Matplotlib colormap for current plots
        line_width: Line width for plots
        grid_alpha: Transparency for grid lines
        font_size_label: Font size for axis labels
        font_size_title: Font size for titles
        font_size_legend: Font size for legend
        
        # Output settings
        output_format: Image format ('png', 'pdf', 'svg')
        show_plots: Whether to display plots interactively
    """
    plot_types: List[PlotType] = field(default_factory=lambda: [PlotType.ALL])
    selected_nodes: Optional[List[str]] = None
    exclude_nodes: List[str] = field(default_factory=lambda: ['0', 'gnd'])
    
    # Figure settings
    figure_dpi: int = 150
    overlay_figsize: Tuple[float, float] = (12, 6)
    individual_figsize_per_plot: Tuple[float, float] = (4, 3)
    current_figsize: Tuple[float, float] = (12, 5)
    
    # Style settings
    colormap: str = 'tab20'
    current_colormap: str = 'Set2'
    line_width: float = 1.5
    grid_alpha: float = 0.3
    font_size_label: int = 12
    font_size_title: int = 14
    font_size_legend: int = 9
    
    # Output settings
    output_format: str = 'png'
    show_plots: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.figure_dpi < 50 or self.figure_dpi > 600:
            raise ValueError("figure_dpi should be between 50 and 600")
        if self.output_format not in ['png', 'pdf', 'svg', 'jpg']:
            raise ValueError("output_format must be 'png', 'pdf', 'svg', or 'jpg'")
        if self.line_width <= 0:
            raise ValueError("line_width must be positive")
    
    def should_generate(self, plot_type: PlotType) -> bool:
        """Check if a specific plot type should be generated."""
        if PlotType.ALL in self.plot_types:
            return True
        return plot_type in self.plot_types


def load_config_from_file(config_path: str) -> Tuple[SimulationConfig, PlotConfig]:
    """
    Load configuration from a YAML or JSON file.
    
    Parameters:
        config_path: Path to configuration file
        
    Returns:
        Tuple of (SimulationConfig, PlotConfig)
    """
    import json
    import os
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        if config_path.endswith('.yaml') or config_path.endswith('.yml'):
            try:
                import yaml
                data = yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML is required to load YAML config files. "
                                "Install with: pip install pyyaml")
        else:
            data = json.load(f)
    
    sim_data = data.get('simulation', {})
    plot_data = data.get('plotting', {})
    
    # Handle simulation type enum
    if 'simulation_type' in sim_data:
        sim_data['simulation_type'] = SimulationType(sim_data['simulation_type'])
    
    # Handle plot types enum
    if 'plot_types' in plot_data:
        plot_data['plot_types'] = [PlotType(pt) for pt in plot_data['plot_types']]
    
    # Convert tuples
    for key in ['overlay_figsize', 'individual_figsize_per_plot', 'current_figsize']:
        if key in plot_data:
            plot_data[key] = tuple(plot_data[key])
    
    sim_config = SimulationConfig(**sim_data)
    plot_config = PlotConfig(**plot_data)
    
    return sim_config, plot_config


def create_default_config_file(output_path: str):
    """
    Create a default configuration file template.
    
    Parameters:
        output_path: Path where to save the config file
    """
    default_config = {
        "simulation": {
            "simulation_type": "auto",
            "temperature": 25.0,
            "nominal_temperature": 25.0,
            "tran_step_time": 10e-6,
            "tran_end_time": 10e-3,
            "ac_start_freq": 1.0,
            "ac_stop_freq": 1e6,
            "ac_num_points": 100,
            "ac_variation": "dec"
        },
        "plotting": {
            "plot_types": ["all"],
            "selected_nodes": None,
            "exclude_nodes": ["0", "gnd"],
            "figure_dpi": 150,
            "overlay_figsize": [12, 6],
            "individual_figsize_per_plot": [4, 3],
            "current_figsize": [12, 5],
            "colormap": "tab20",
            "current_colormap": "Set2",
            "line_width": 1.5,
            "grid_alpha": 0.3,
            "output_format": "png",
            "show_plots": False
        }
    }
    
    import json
    with open(output_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print(f"✓ Default configuration saved to: {output_path}")
