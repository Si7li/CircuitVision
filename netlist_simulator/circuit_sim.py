#!/usr/bin/env python3
"""
Circuit Simulator - Main Entry Point

Automatically simulates and plots SPICE circuit netlists.

Usage:
    python circuit_sim.py <input.cir> [options]
    
Examples:
    python circuit_sim.py examples/rc_filter.cir
    python circuit_sim.py examples/rc_filter.cir -o results/
    python circuit_sim.py examples/multi_stage_filter.cir -n out n1 n2
    
For help:
    python circuit_sim.py --help
"""

import sys
import os

# Add src directory to path for development usage
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from circuit_simulator.cli import main

if __name__ == '__main__':
    sys.exit(main())
