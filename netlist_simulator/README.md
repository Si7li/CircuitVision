# Circuit Simulator

A Python package for automatically simulating and visualizing SPICE circuit netlists (.cir files).

## Features

- **Automatic simulation** - Detects simulation type (transient, AC, DC) from your .cir file
- **Smart plotting** - Automatically discovers all voltage nodes and current branches
- **Component voltage analysis** - Plots voltage differences across R, C, L components
- **Multiple plot types** - Overlay plots, individual subplots, current plots, component voltages, and summary figures
- **Flexible CLI** - Easy command-line interface with many options
- **Configurable** - JSON/YAML configuration files for custom settings
- **Beginner-friendly** - Clear error messages and helpful tips

## Installation

### Prerequisites

1. **Python 3.8+** is required

2. **ngspice** must be installed on your system:

   ```bash
   # Ubuntu/Debian
   sudo apt install ngspice

   # macOS (with Homebrew)
   brew install ngspice

   # Windows
   # Download from http://ngspice.sourceforge.net/download.html
   ```

### Install the Package

```bash
# Clone or download this repository
cd netlist_simulator

# Install in development mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```bash
# Simulate a circuit and generate all plots
python circuit_sim.py examples/rc_filter.cir

# Specify output directory
python circuit_sim.py examples/rc_filter.cir -o results/

# Plot only specific nodes
python circuit_sim.py examples/multi_stage_filter.cir -n out n1 n2
```

### Python API

```python
from circuit_simulator import CircuitSimulator, CircuitPlotter

# Simple one-liner
from circuit_simulator.simulator import simulate_and_plot_circuit
result = simulate_and_plot_circuit('my_circuit.cir')

# Or with more control
simulator = CircuitSimulator()
result = simulator.simulate('my_circuit.cir')

plotter = CircuitPlotter()
plotter.plot_all(result, 'output.png')

# Access the data
print(f"Available nodes: {list(result.nodes.keys())}")
time = result.x_data
v_out = result.nodes['out']
```

## Command Line Options

```
usage: circuit_sim.py [-h] [-o PATH] [--format {png,pdf,svg,jpg}] [--dpi N]
                      [--show] [-n NODE [NODE ...]] [--exclude NODE [NODE ...]]
                      [--plots TYPE [TYPE ...]] [--no-currents]
                      [--sim-type {auto,transient,ac,dc}] [--temp C]
                      [--step SEC] [--end-time SEC] [--start-freq HZ]
                      [--stop-freq HZ] [-c FILE] [--generate-config FILE]
                      [-v] [-q] [--validate-only] [--list-nodes] [--version]
                      [input]

SPICE Circuit Simulator and Plotter
```

### Common Options

| Option | Description |
|--------|-------------|
| `input` | Path to the .cir file |
| `-o, --output` | Output directory or file path |
| `--format` | Image format: png, pdf, svg, jpg |
| `-n, --nodes` | Specific nodes to plot |
| `--plots` | Plot types: overlay, individual, currents, summary, all |
| `--sim-type` | Force simulation type: auto, transient, ac, dc |
| `-c, --config` | Load settings from config file |
| `--validate-only` | Only validate the .cir file |
| `--list-nodes` | Show available nodes without plotting |

### Examples

```bash
# Generate only overlay plot in PDF format
python circuit_sim.py circuit.cir --plots overlay --format pdf

# Force AC analysis with custom frequency range
python circuit_sim.py circuit.cir --sim-type ac --start-freq 10 --stop-freq 100000

# Validate a circuit file
python circuit_sim.py circuit.cir --validate-only

# Generate a configuration template
python circuit_sim.py --generate-config my_config.json

# Use a configuration file
python circuit_sim.py circuit.cir -c my_config.json

# Show plots interactively (requires GUI)
python circuit_sim.py circuit.cir --show
```

## Configuration

You can customize simulation and plotting settings using a JSON configuration file:

```bash
# Generate a template
python circuit_sim.py --generate-config config.json
```

Example configuration:

```json
{
  "simulation": {
    "simulation_type": "auto",
    "temperature": 25.0,
    "tran_step_time": 1e-6,
    "tran_end_time": 10e-3,
    "ac_start_freq": 1.0,
    "ac_stop_freq": 1000000.0
  },
  "plotting": {
    "plot_types": ["all"],
    "figure_dpi": 150,
    "colormap": "tab20",
    "line_width": 1.5,
    "output_format": "png"
  }
}
```

## Example Circuits

The `examples/` directory contains several test circuits:

| File | Description |
|------|-------------|
| `rc_filter.cir` | Simple RC low-pass filter |
| `voltage_divider.cir` | Basic resistor voltage divider |
| `rlc_circuit.cir` | Series RLC resonant circuit |
| `multi_stage_filter.cir` | Cascaded 3-stage RC filter |

## Project Structure

```
netlist_simulator/
├── circuit_sim.py           # Main entry point
├── requirements.txt         # Python dependencies
├── setup.py                 # Package installation
├── README.md               
├── examples/                # Example .cir files
│   ├── rc_filter.cir
│   ├── voltage_divider.cir
│   ├── rlc_circuit.cir
│   └── multi_stage_filter.cir
├── src/
│   └── circuit_simulator/
│       ├── __init__.py
│       ├── cli.py           # Command-line interface
│       ├── config.py        # Configuration classes
│       ├── plotter.py       # Plotting functionality
│       └── simulator.py     # Core simulation logic
└── tests/
    ├── __init__.py
    └── test_simulator.py
```

## Troubleshooting

### "ngspice not found"

Make sure ngspice is installed and in your PATH:

```bash
# Check if installed
ngspice --version

# Ubuntu/Debian
sudo apt install ngspice

# macOS
brew install ngspice
```

### "No module named 'PySpice'"

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### "No nodes to plot"

Your circuit might only have a ground node. Make sure your circuit has:
- At least one voltage source
- Named nodes (not just node 0)
- A complete path from source to ground

### Simulation errors

Common issues:
- Missing `.end` directive at the end of the file
- Floating nodes (not connected to ground)
- Invalid component syntax
- Missing ground connection (node 0)

## API Reference

### CircuitSimulator

```python
simulator = CircuitSimulator(config=SimulationConfig())

# Validate a file
is_valid, message = simulator.validate_cir_file('circuit.cir')

# Run simulation
result = simulator.simulate('circuit.cir', verbose=True)

# Access results
voltage = simulator.get_node_voltage(result, 'out')
current = simulator.get_branch_current(result, 'vin')
```

### CircuitPlotter

```python
plotter = CircuitPlotter(config=PlotConfig())

# Generate all plots
plotter.plot_all(result, 'output.png')

# Generate specific plots
plotter.plot_overlay(result, 'overlay.png')
plotter.plot_individual(result, 'individual.png')
plotter.plot_currents(result, 'currents.png')
plotter.create_summary_figure(result, 'summary.png')
```

### SimulationResult

```python
result.circuit_title   # Circuit title from .cir file
result.sim_type        # 'transient', 'ac', or 'dc'
result.nodes           # Dict of node_name -> voltage_data
result.branches        # Dict of branch_name -> current_data
result.x_data          # X-axis data (time or frequency)
result.x_label         # Label for x-axis
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
