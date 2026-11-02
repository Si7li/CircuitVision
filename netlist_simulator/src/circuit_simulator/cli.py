"""
Command-line interface for the circuit simulator.

Provides a user-friendly CLI for simulating SPICE netlists.
"""

import argparse
import sys
import os
from typing import Optional

from .config import (
    SimulationConfig, PlotConfig, SimulationType, PlotType,
    load_config_from_file, create_default_config_file
)
from .simulator import (
    CircuitSimulator, SimulationResult,
    CircuitParseError, SimulationError, DependencyError
)
from .plotter import CircuitPlotter


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    
    parser = argparse.ArgumentParser(
        prog='circuit_sim',
        description='''
╔══════════════════════════════════════════════════════════════════════╗
║           SPICE Circuit Simulator and Plotter                        ║
║                                                                      ║
║  Automatically simulate and visualize SPICE circuit netlists.        ║
║  Supports transient, AC, and DC analysis.                            ║
╚══════════════════════════════════════════════════════════════════════╝
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s circuit.cir                    # Simulate with defaults
  %(prog)s circuit.cir -o results/        # Save plots to results/
  %(prog)s circuit.cir -n out n1 n2       # Plot only specific nodes
  %(prog)s circuit.cir --sim-type ac      # Force AC analysis
  %(prog)s --generate-config config.json  # Generate config template

For more information, visit: https://github.com/your-repo/circuit-simulator
        '''
    )
    
    # Required arguments (input file)
    parser.add_argument(
        'input',
        nargs='?',
        help='Path to the SPICE netlist file (.cir, .sp, .spice, .net)'
    )
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        '-o', '--output',
        metavar='PATH',
        default='.',
        help='Output directory or file path for plots (default: current directory)'
    )
    output_group.add_argument(
        '--format',
        choices=['png', 'pdf', 'svg', 'jpg'],
        default='png',
        help='Output image format (default: png)'
    )
    output_group.add_argument(
        '--dpi',
        type=int,
        default=150,
        metavar='N',
        help='DPI for output images (default: 150)'
    )
    output_group.add_argument(
        '--show',
        action='store_true',
        help='Display plots interactively (requires GUI)'
    )
    
    # Node selection
    node_group = parser.add_argument_group('Node Selection')
    node_group.add_argument(
        '-n', '--nodes',
        nargs='+',
        metavar='NODE',
        help='Specific nodes to plot (default: all nodes except ground)'
    )
    node_group.add_argument(
        '--exclude',
        nargs='+',
        metavar='NODE',
        default=['0', 'gnd'],
        help='Nodes to exclude from plotting (default: 0, gnd)'
    )
    
    # Plot type selection
    plot_group = parser.add_argument_group('Plot Types')
    plot_group.add_argument(
        '--plots',
        nargs='+',
        choices=['overlay', 'individual', 'currents', 'components', 'summary', 'all'],
        default=['all'],
        metavar='TYPE',
        help='Types of plots to generate: overlay, individual, currents, components, summary, all (default: all)'
    )
    plot_group.add_argument(
        '--no-currents',
        action='store_true',
        help='Skip current plots even if branch data is available'
    )
    plot_group.add_argument(
        '--no-components',
        action='store_true',
        help='Skip component voltage plots'
    )
    
    # Simulation options
    sim_group = parser.add_argument_group('Simulation Options')
    sim_group.add_argument(
        '--sim-type',
        choices=['auto', 'transient', 'ac', 'dc'],
        default='auto',
        help='Simulation type (default: auto-detect from .cir file)'
    )
    sim_group.add_argument(
        '--temp',
        type=float,
        default=25.0,
        metavar='C',
        help='Operating temperature in Celsius (default: 25)'
    )
    sim_group.add_argument(
        '--step',
        type=float,
        metavar='SEC',
        help='Time step for transient analysis (e.g., 1e-6 for 1µs)'
    )
    sim_group.add_argument(
        '--end-time',
        type=float,
        metavar='SEC',
        help='End time for transient analysis (e.g., 10e-3 for 10ms)'
    )
    sim_group.add_argument(
        '--start-freq',
        type=float,
        metavar='HZ',
        help='Start frequency for AC analysis'
    )
    sim_group.add_argument(
        '--stop-freq',
        type=float,
        metavar='HZ',
        help='Stop frequency for AC analysis'
    )
    
    # Configuration
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument(
        '-c', '--config',
        metavar='FILE',
        help='Load settings from a JSON/YAML configuration file'
    )
    config_group.add_argument(
        '--generate-config',
        metavar='FILE',
        help='Generate a default configuration file template'
    )
    
    # Utility options
    util_group = parser.add_argument_group('Utility Options')
    util_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=True,
        help='Show detailed progress messages (default: enabled)'
    )
    util_group.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress all output except errors'
    )
    util_group.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate the .cir file without simulating'
    )
    util_group.add_argument(
        '--list-nodes',
        action='store_true',
        help='List available nodes after simulation without plotting'
    )
    util_group.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser


def build_sim_config(args) -> SimulationConfig:
    """Build SimulationConfig from command line arguments."""
    
    # Start with defaults or loaded config
    if args.config:
        sim_config, _ = load_config_from_file(args.config)
    else:
        sim_config = SimulationConfig()
    
    # Override with command line arguments
    sim_type_map = {
        'auto': SimulationType.AUTO,
        'transient': SimulationType.TRANSIENT,
        'ac': SimulationType.AC,
        'dc': SimulationType.DC
    }
    sim_config.simulation_type = sim_type_map[args.sim_type]
    sim_config.temperature = args.temp
    sim_config.nominal_temperature = args.temp
    
    if args.step:
        sim_config.tran_step_time = args.step
    if args.end_time:
        sim_config.tran_end_time = args.end_time
    if args.start_freq:
        sim_config.ac_start_freq = args.start_freq
    if args.stop_freq:
        sim_config.ac_stop_freq = args.stop_freq
    
    return sim_config


def build_plot_config(args) -> PlotConfig:
    """Build PlotConfig from command line arguments."""
    
    # Start with defaults or loaded config
    if args.config:
        _, plot_config = load_config_from_file(args.config)
    else:
        plot_config = PlotConfig()
    
    # Override with command line arguments
    plot_config.output_format = args.format
    plot_config.figure_dpi = args.dpi
    plot_config.show_plots = args.show
    plot_config.selected_nodes = args.nodes
    plot_config.exclude_nodes = args.exclude
    
    # Handle plot types
    if 'all' in args.plots:
        plot_config.plot_types = [PlotType.ALL]
    else:
        type_map = {
            'overlay': PlotType.OVERLAY,
            'individual': PlotType.INDIVIDUAL,
            'currents': PlotType.CURRENTS,
            'components': PlotType.COMPONENTS,
        }
        plot_config.plot_types = [type_map[p] for p in args.plots if p in type_map]
    
    if args.no_currents:
        plot_config.plot_types = [pt for pt in plot_config.plot_types 
                                  if pt != PlotType.CURRENTS]
    
    if args.no_components:
        plot_config.plot_types = [pt for pt in plot_config.plot_types 
                                  if pt != PlotType.COMPONENTS]
    
    return plot_config


def get_output_path(args) -> str:
    """Determine the output file path."""
    
    if os.path.isdir(args.output):
        # Output is a directory, use input filename as base
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        return os.path.join(args.output, f'{base_name}.{args.format}')
    else:
        # Output is a file path
        return args.output


def print_banner():
    """Print the application banner."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " SPICE Circuit Simulator and Plotter ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()


def print_error(message: str):
    """Print an error message in a formatted way."""
    print(f"\n✗ Error: {message}", file=sys.stderr)


def print_success(message: str):
    """Print a success message."""
    print(f"\n✓ {message}")


def run_simulation(args) -> int:
    """
    Run the simulation with the given arguments.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    verbose = args.verbose and not args.quiet
    
    if verbose:
        print_banner()
    
    # Validate input file
    if not args.input:
        print_error("No input file specified. Use -h for help.")
        return 1
    
    if not os.path.exists(args.input):
        print_error(f"File not found: {args.input}")
        print("\n  Make sure the file path is correct.")
        print("  Example: python circuit_sim.py examples/rc_filter.cir")
        return 1
    
    try:
        # Build configurations
        sim_config = build_sim_config(args)
        plot_config = build_plot_config(args)
        
        # Create simulator
        simulator = CircuitSimulator(config=sim_config)
        
        # Validate only mode
        if args.validate_only:
            is_valid, message = simulator.validate_cir_file(args.input)
            if is_valid:
                print_success(f"File is valid: {args.input}")
                return 0
            else:
                print_error(message)
                return 1
        
        # Run simulation
        result = simulator.simulate(args.input, verbose=verbose)
        
        # List nodes mode
        if args.list_nodes:
            print("\n" + "=" * 50)
            print("Available Nodes:")
            print("=" * 50)
            for node in result.nodes.keys():
                print(f"  V({node})")
            if result.branches:
                print("\nAvailable Branch Currents:")
                for branch in result.branches.keys():
                    print(f"  I({branch})")
            return 0
        
        # Create output directory if needed
        output_path = get_output_path(args)
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            if verbose:
                print(f"\n✓ Created output directory: {output_dir}")
        
        # Generate plots
        plotter = CircuitPlotter(config=plot_config)
        
        # Handle summary plot separately
        if 'summary' in args.plots:
            plotter.create_summary_figure(result, output_path)
        
        # Generate standard plots
        if 'summary' not in args.plots or len(args.plots) > 1:
            plotter.plot_all(result, output_path)
        
        if verbose:
            print_success("Simulation complete!")
        
        return 0
        
    except DependencyError as e:
        print_error(str(e))
        return 2
        
    except CircuitParseError as e:
        print_error(f"Failed to parse circuit file:\n  {e}")
        print("\n  Tips:")
        print("  - Check that the file is a valid SPICE netlist")
        print("  - Ensure the file ends with .end directive")
        print("  - Verify component syntax (R1 node1 node2 value)")
        return 3
        
    except SimulationError as e:
        print_error(f"Simulation failed:\n  {e}")
        print("\n  Tips:")
        print("  - Check that ngspice is installed correctly")
        print("  - Verify your circuit has valid connections")
        print("  - Ensure there's a ground (node 0) connection")
        return 4
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 130
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def main(args=None) -> int:
    """
    Main entry point for the CLI.
    
    Parameters:
        args: Command line arguments (uses sys.argv if None)
        
    Returns:
        Exit code
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Handle config generation
    if parsed_args.generate_config:
        try:
            create_default_config_file(parsed_args.generate_config)
            print(f"\n✓ Configuration template created: {parsed_args.generate_config}")
            print("  Edit this file to customize simulation and plot settings.")
            return 0
        except Exception as e:
            print_error(f"Failed to create config file: {e}")
            return 1
    
    # Check if input file is required
    if not parsed_args.input and not parsed_args.generate_config:
        parser.print_help()
        return 0
    
    return run_simulation(parsed_args)


if __name__ == '__main__':
    sys.exit(main())
