"""
Core circuit simulation module.

Handles parsing .cir files and running SPICE simulations via PySpice/ngspice.
"""

import os
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from .config import SimulationConfig, SimulationType


class SimulationError(Exception):
    """Custom exception for simulation-related errors."""
    pass


class CircuitParseError(Exception):
    """Custom exception for circuit parsing errors."""
    pass


class DependencyError(Exception):
    """Custom exception for missing dependencies."""
    pass


@dataclass
class ComponentVoltage:
    """
    Container for voltage difference across a component.
    
    Attributes:
        voltage: Voltage difference data (numpy array)
        nodes: String describing the node connection (e.g., "n1 → n2")
        component_type: Type of component (R, C, L, etc.)
    """
    voltage: Any
    nodes: str
    component_type: str


@dataclass
class SimulationResult:
    """
    Container for simulation results.
    
    Attributes:
        analysis: PySpice analysis object with simulation data
        sim_type: Type of simulation that was run
        circuit_title: Title from the circuit file
        nodes: Dictionary mapping node names to voltage data
        branches: Dictionary mapping branch names to current data
        component_voltages: Dictionary mapping component names to ComponentVoltage
        x_data: X-axis data (time or frequency)
        x_label: Label for x-axis
        x_multiplier: Multiplier applied to x-data for display
    """
    analysis: Any
    sim_type: str
    circuit_title: str
    nodes: Dict[str, Any]
    branches: Dict[str, Any]
    component_voltages: Dict[str, ComponentVoltage]
    x_data: Any
    x_label: str
    x_multiplier: float


class CircuitSimulator:
    """
    Main class for simulating SPICE circuit netlists.
    
    Example usage:
        simulator = CircuitSimulator()
        result = simulator.simulate('my_circuit.cir')
        print(f"Available nodes: {list(result.nodes.keys())}")
    """
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        """
        Initialize the circuit simulator.
        
        Parameters:
            config: Simulation configuration. Uses defaults if not provided.
        """
        self.config = config or SimulationConfig()
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check that required dependencies are available."""
        try:
            from PySpice.Spice.Parser import SpiceParser
            from PySpice.Unit import u_us, u_ms
        except ImportError as e:
            raise DependencyError(
                "PySpice is not installed. Install with:\n"
                "  pip install PySpice\n\n"
                "You also need ngspice installed on your system:\n"
                "  Ubuntu/Debian: sudo apt install ngspice\n"
                "  macOS: brew install ngspice\n"
                "  Windows: Download from http://ngspice.sourceforge.net/\n\n"
                f"Original error: {e}"
            )
        
        # Try to verify ngspice is available
        try:
            import subprocess
            result = subprocess.run(['ngspice', '--version'], 
                                  capture_output=True, text=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("⚠ Warning: ngspice not found in PATH. Simulation may fail.")
            print("  Install ngspice:")
            print("    Ubuntu/Debian: sudo apt install ngspice")
            print("    macOS: brew install ngspice")
            print("    Windows: Download from http://ngspice.sourceforge.net/")
    
    def validate_cir_file(self, cir_file_path: str) -> Tuple[bool, str]:
        """
        Validate a .cir file before simulation.
        
        Parameters:
            cir_file_path: Path to the .cir file
            
        Returns:
            Tuple of (is_valid, message)
        """
        # Check file exists
        if not os.path.exists(cir_file_path):
            return False, f"File not found: {cir_file_path}"
        
        # Check file extension
        if not cir_file_path.lower().endswith(('.cir', '.sp', '.spice', '.net')):
            return False, (f"Unexpected file extension. Expected .cir, .sp, .spice, or .net. "
                          f"Got: {os.path.splitext(cir_file_path)[1]}")
        
        # Check file is readable and has content
        try:
            with open(cir_file_path, 'r') as f:
                content = f.read()
        except PermissionError:
            return False, f"Permission denied: Cannot read {cir_file_path}"
        except UnicodeDecodeError:
            return False, f"Invalid file encoding: {cir_file_path} is not a valid text file"
        
        if not content.strip():
            return False, f"File is empty: {cir_file_path}"
        
        # Check for basic SPICE structure
        lines = content.strip().split('\n')
        if len(lines) < 2:
            return False, "File too short: A valid netlist needs at least a title and one element"
        
        # Check for .end directive
        content_lower = content.lower()
        if '.end' not in content_lower:
            return False, "Missing .end directive: SPICE netlists should end with .end"
        
        # Check for at least one element (R, C, L, V, I, etc.)
        has_element = False
        element_prefixes = ['r', 'c', 'l', 'v', 'i', 'd', 'q', 'm', 'x', 'e', 'f', 'g', 'h']
        for line in lines[1:]:  # Skip title line
            line = line.strip().lower()
            if line and not line.startswith(('*', '.')) and line[0] in element_prefixes:
                has_element = True
                break
        
        if not has_element:
            return False, "No circuit elements found: Need at least one R, C, L, V, or I component"
        
        return True, "File validation passed"
    
    def detect_simulation_type(self, cir_content: str) -> SimulationType:
        """
        Detect the simulation type from .cir file content.
        
        Parameters:
            cir_content: Content of the .cir file
            
        Returns:
            Detected SimulationType
        """
        content_lower = cir_content.lower()
        
        if '.tran ' in content_lower or '\n.tran' in content_lower:
            return SimulationType.TRANSIENT
        elif '.ac ' in content_lower or '\n.ac' in content_lower:
            return SimulationType.AC
        elif '.dc ' in content_lower or '\n.dc' in content_lower:
            return SimulationType.DC
        else:
            return SimulationType.TRANSIENT  # Default
    
    def _parse_spice_value(self, value_str: str) -> float:
        """
        Parse a SPICE value string with unit suffix to float.
        
        Parameters:
            value_str: Value string like '10u', '1m', '100n', '1meg'
            
        Returns:
            Float value in base units
        """
        value_str = value_str.strip().lower()
        
        # SPICE unit multipliers
        multipliers = {
            'f': 1e-15,  # femto
            'p': 1e-12,  # pico
            'n': 1e-9,   # nano
            'u': 1e-6,   # micro
            'm': 1e-3,   # milli
            'k': 1e3,    # kilo
            'meg': 1e6,  # mega
            'g': 1e9,    # giga
            't': 1e12,   # tera
        }
        
        # Try to find a unit suffix
        for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
            if value_str.endswith(suffix):
                try:
                    return float(value_str[:-len(suffix)]) * mult
                except ValueError:
                    pass
        
        # No suffix, try direct conversion
        try:
            return float(value_str)
        except ValueError:
            return None
    
    def _parse_tran_parameters(self, cir_content: str) -> tuple:
        """
        Parse .tran parameters from .cir file content.
        
        Parameters:
            cir_content: Content of the .cir file
            
        Returns:
            Tuple of (step_time, end_time) or (None, None) if not found
        """
        import re
        
        # Find .tran line: .tran step_time end_time [start_time] [max_step]
        pattern = r'\.tran\s+(\S+)\s+(\S+)'
        match = re.search(pattern, cir_content.lower())
        
        if match:
            step_str = match.group(1)
            end_str = match.group(2)
            
            step_time = self._parse_spice_value(step_str)
            end_time = self._parse_spice_value(end_str)
            
            if step_time and end_time:
                return step_time, end_time
        
        return None, None
    
    def _parse_ac_parameters(self, cir_content: str) -> tuple:
        """
        Parse .ac parameters from .cir file content.
        
        Parameters:
            cir_content: Content of the .cir file
            
        Returns:
            Tuple of (variation, num_points, start_freq, stop_freq) or None values
        """
        import re
        
        # Find .ac line: .ac dec/oct/lin num_points start_freq stop_freq
        pattern = r'\.ac\s+(dec|oct|lin)\s+(\d+)\s+(\S+)\s+(\S+)'
        match = re.search(pattern, cir_content.lower())
        
        if match:
            variation = match.group(1)
            num_points = int(match.group(2))
            start_freq = self._parse_spice_value(match.group(3))
            stop_freq = self._parse_spice_value(match.group(4))
            
            if start_freq and stop_freq:
                return variation, num_points, start_freq, stop_freq
        
        return None, None, None, None
    
    def simulate(self, cir_file_path: str, verbose: bool = True) -> SimulationResult:
        """
        Simulate a SPICE circuit netlist.
        
        Parameters:
            cir_file_path: Path to the .cir file
            verbose: Whether to print progress messages
            
        Returns:
            SimulationResult containing all simulation data
            
        Raises:
            CircuitParseError: If the circuit file cannot be parsed
            SimulationError: If the simulation fails
        """
        from PySpice.Spice.Parser import SpiceParser
        from PySpice.Unit import u_us, u_ms, u_Hz, u_MHz
        import numpy as np
        
        # Validate file
        is_valid, message = self.validate_cir_file(cir_file_path)
        if not is_valid:
            raise CircuitParseError(message)
        
        if verbose:
            print("=" * 70)
            print(f"Simulating: {cir_file_path}")
            print("=" * 70)
        
        # Parse the circuit file
        try:
            parser = SpiceParser(path=cir_file_path)
            circuit = parser.build_circuit()
        except Exception as e:
            raise CircuitParseError(f"Failed to parse circuit file: {e}")
        
        if verbose:
            print(f"\n✓ Circuit loaded: {circuit.title}")
            print(f"  Elements: {len(circuit.elements)}")
        
        # Read file to detect simulation type
        with open(cir_file_path, 'r') as f:
            cir_content = f.read()
        
        # Determine simulation type
        if self.config.simulation_type == SimulationType.AUTO:
            sim_type = self.detect_simulation_type(cir_content)
            if verbose:
                print(f"\n  Auto-detected simulation type: {sim_type.value.upper()}")
        else:
            sim_type = self.config.simulation_type
        
        # Create simulator
        simulator = circuit.simulator(
            temperature=self.config.temperature,
            nominal_temperature=self.config.nominal_temperature
        )
        
        if verbose:
            print("\nRunning simulation...")
        
        # Run appropriate simulation
        try:
            if sim_type == SimulationType.TRANSIENT:
                # Try to parse parameters from .cir file first
                parsed_step, parsed_end = self._parse_tran_parameters(cir_content)
                
                step_time = parsed_step if parsed_step else self.config.tran_step_time
                end_time = parsed_end if parsed_end else self.config.tran_end_time
                
                if verbose and parsed_step:
                    print(f"  Using .cir parameters: step={step_time*1e6:.2f}µs, end={end_time*1e6:.2f}µs")
                
                analysis = simulator.transient(
                    step_time=step_time,
                    end_time=end_time
                )
                
                # Choose appropriate time unit for display
                if end_time < 1e-3:
                    x_label = 'Time (µs)'
                    x_multiplier = 1e6
                else:
                    x_label = 'Time (ms)'
                    x_multiplier = 1e3
                x_data = np.array(analysis.time) * x_multiplier
                
            elif sim_type == SimulationType.AC:
                # Try to parse parameters from .cir file first
                parsed_var, parsed_pts, parsed_start, parsed_stop = self._parse_ac_parameters(cir_content)
                
                variation = parsed_var if parsed_var else self.config.ac_variation
                num_points = parsed_pts if parsed_pts else self.config.ac_num_points
                start_freq = parsed_start if parsed_start else self.config.ac_start_freq
                stop_freq = parsed_stop if parsed_stop else self.config.ac_stop_freq
                
                if verbose and parsed_start:
                    print(f"  Using .cir parameters: {variation} {num_points}pts {start_freq}Hz-{stop_freq}Hz")
                
                analysis = simulator.ac(
                    start_frequency=start_freq,
                    stop_frequency=stop_freq,
                    number_of_points=num_points,
                    variation=variation
                )
                x_label = 'Frequency (Hz)'
                x_multiplier = 1
                x_data = np.array(analysis.frequency)
                
            elif sim_type == SimulationType.DC:
                if verbose:
                    print("  ⚠ DC sweep requires manual source configuration")
                    print("    Defaulting to transient analysis")
                # Use parsed transient params if available
                parsed_step, parsed_end = self._parse_tran_parameters(cir_content)
                step_time = parsed_step if parsed_step else self.config.tran_step_time
                end_time = parsed_end if parsed_end else self.config.tran_end_time
                
                analysis = simulator.transient(
                    step_time=step_time,
                    end_time=end_time
                )
                sim_type = SimulationType.TRANSIENT
                if end_time < 1e-3:
                    x_label = 'Time (µs)'
                    x_multiplier = 1e6
                else:
                    x_label = 'Time (ms)'
                    x_multiplier = 1e3
                x_data = np.array(analysis.time) * x_multiplier
            
            else:
                raise SimulationError(f"Unknown simulation type: {sim_type}")
                
        except Exception as e:
            raise SimulationError(f"Simulation failed: {e}")
        
        if verbose:
            print("✓ Simulation completed\n")
        
        # Extract results
        nodes = {str(name): analysis[name] for name in analysis.nodes.keys()}
        branches = {str(name): analysis[name] for name in analysis.branches.keys()}
        
        # Extract component voltage differences
        component_voltages = self._extract_component_voltages(circuit, analysis, verbose)
        
        if verbose:
            print("Available signals:")
            print(f"  Voltage nodes: {len(nodes)}")
            for node in nodes:
                print(f"    - V({node})")
            if branches:
                print(f"  Current branches: {len(branches)}")
                for branch in branches:
                    print(f"    - I({branch})")
            if component_voltages:
                print(f"  Component voltages: {len(component_voltages)}")
                for comp_name, data in component_voltages.items():
                    print(f"    - V({comp_name}): {data.nodes}")
        
        return SimulationResult(
            analysis=analysis,
            sim_type=sim_type.value,
            circuit_title=circuit.title,
            nodes=nodes,
            branches=branches,
            component_voltages=component_voltages,
            x_data=x_data,
            x_label=x_label,
            x_multiplier=x_multiplier
        )
    
    def get_node_voltage(self, result: SimulationResult, node_name: str):
        """
        Get voltage data for a specific node.
        
        Parameters:
            result: SimulationResult from simulate()
            node_name: Name of the node
            
        Returns:
            numpy array of voltage values
        """
        import numpy as np
        
        if node_name not in result.nodes:
            available = list(result.nodes.keys())
            raise ValueError(f"Node '{node_name}' not found. Available nodes: {available}")
        
        return np.array(result.nodes[node_name])
    
    def get_branch_current(self, result: SimulationResult, branch_name: str):
        """
        Get current data for a specific branch.
        
        Parameters:
            result: SimulationResult from simulate()
            branch_name: Name of the branch
            
        Returns:
            numpy array of current values
        """
        import numpy as np
        
        if branch_name not in result.branches:
            available = list(result.branches.keys())
            raise ValueError(f"Branch '{branch_name}' not found. Available branches: {available}")
        
        return np.array(result.branches[branch_name])
    
    def _extract_component_voltages(self, circuit, analysis, verbose: bool = False) -> Dict[str, ComponentVoltage]:
        """
        Extract voltage differences across circuit components.
        
        Parameters:
            circuit: PySpice circuit object
            analysis: PySpice analysis object
            verbose: Whether to print progress
            
        Returns:
            Dictionary mapping component names to ComponentVoltage objects
        """
        import numpy as np
        
        component_voltages = {}
        
        for element in circuit.elements:
            element_str = str(element)
            parts = element_str.split()
            
            if len(parts) < 3:
                continue
            
            component_name = parts[0]
            component_type = component_name[0].upper()
            
            # Skip voltage sources (we already plot their currents)
            if component_type == 'V':
                continue
            
            try:
                # Handle two-terminal components (R, C, L)
                if component_type in ['R', 'C', 'L']:
                    node1 = parts[1].lower()
                    node2 = parts[2].lower()
                    
                    # Calculate voltage difference
                    if node1 in analysis.nodes and node2 in analysis.nodes:
                        v_diff = np.array(analysis[node1]) - np.array(analysis[node2])
                        component_voltages[component_name] = ComponentVoltage(
                            voltage=v_diff,
                            nodes=f"{node1} → {node2}",
                            component_type=component_type
                        )
                    elif node1 in analysis.nodes and node2 in ['0', 'gnd']:
                        v_diff = np.array(analysis[node1])
                        component_voltages[component_name] = ComponentVoltage(
                            voltage=v_diff,
                            nodes=f"{node1} → GND",
                            component_type=component_type
                        )
                    elif node2 in analysis.nodes and node1 in ['0', 'gnd']:
                        v_diff = -np.array(analysis[node2])
                        component_voltages[component_name] = ComponentVoltage(
                            voltage=v_diff,
                            nodes=f"GND → {node2}",
                            component_type=component_type
                        )
            except (IndexError, KeyError):
                pass
        
        return component_voltages
    
    def get_component_voltage(self, result: SimulationResult, component_name: str):
        """
        Get voltage difference across a specific component.
        
        Parameters:
            result: SimulationResult from simulate()
            component_name: Name of the component (e.g., 'R1', 'C1')
            
        Returns:
            numpy array of voltage values
        """
        import numpy as np
        
        if component_name not in result.component_voltages:
            available = list(result.component_voltages.keys())
            raise ValueError(f"Component '{component_name}' not found. Available: {available}")
        
        return np.array(result.component_voltages[component_name].voltage)


def simulate_and_plot_circuit(cir_file_path: str, output_image: str = 'circuit_results.png',
                              sim_config: Optional[SimulationConfig] = None,
                              plot_config = None) -> SimulationResult:
    """
    Convenience function to simulate and plot a circuit in one call.
    
    This is the main entry point for simple usage.
    
    Parameters:
        cir_file_path: Path to the .cir file
        output_image: Base path for output images
        sim_config: Optional simulation configuration
        plot_config: Optional plot configuration
        
    Returns:
        SimulationResult with all data
    """
    from .plotter import CircuitPlotter
    from .config import PlotConfig
    
    # Create simulator and run
    simulator = CircuitSimulator(config=sim_config)
    result = simulator.simulate(cir_file_path, verbose=True)
    
    # Create plotter and generate plots
    plot_cfg = plot_config or PlotConfig()
    plotter = CircuitPlotter(config=plot_cfg)
    plotter.plot_all(result, output_image)
    
    return result
