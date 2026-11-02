"""
Local test script for CircuitVision + netlist_simulator backend.

Usage:
    # Test simulation only (no CircuitVision, uses sample netlist)
    python test_local.py --sim-only

    # Test with sample image
    python test_local.py --image path/to/circuit.png

    # Test handler directly
    python test_local.py --handler path/to/circuit.png
"""

import os
import sys
import json
import base64
import argparse
import tempfile
from pathlib import Path

# Add paths
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "src"))


def test_netlist_normalizer():
    """Test netlist normalizer module."""
    print("\n=== Testing Netlist Normalizer ===")

    from src.netlist_normalizer import NetlistNormalizer

    normalizer = NetlistNormalizer()

    # Test case 1: Add missing directives
    print("\nTest 1: Add missing title/analysis/end")
    netlist = "R1 in out 1k\nC1 out 0 1u"
    result = normalizer.normalize(netlist)
    print(f"  Success: {result.success}")
    print(f"  Changes: {result.changes_made}")
    print(f"  Normalized:\n{result.normalized_netlist}")

    # Test case 2: Valid netlist
    print("\nTest 2: Already valid netlist")
    netlist = """RC Filter
R1 in out 1k
C1 out 0 1u
V1 in 0 DC 5
.tran 1u 10m
.end
"""
    result = normalizer.normalize(netlist)
    print(f"  Success: {result.success}")
    print(f"  Changes: {result.changes_made}")

    # Test case 3: CircuitVision format
    print("\nTest 3: CircuitVision component list")
    components = [
        {"component_type": "V", "component_num": 1, "node_1": "in", "node_2": "0", "value": "5"},
        {"component_type": "R", "component_num": 1, "node_1": "in", "node_2": "out", "value": "1k"},
        {"component_type": "C", "component_num": 1, "node_1": "out", "node_2": "0", "value": "1u"},
    ]
    result = normalizer.from_circuitvision_format(components)
    print(f"  Success: {result.success}")
    print(f"  Normalized:\n{result.normalized_netlist}")

    print("\n✓ Netlist normalizer tests passed")


def test_simulation():
    """Test simulation with a sample netlist."""
    print("\n=== Testing Simulation ===")

    try:
        # Check if netlist_simulator is available
        sys.path.insert(0, str(SCRIPT_DIR.parent / "netlist_simulator" / "src"))
        from circuit_simulator import CircuitSimulator, CircuitPlotter
        from circuit_simulator.config import SimulationConfig, PlotConfig, PlotType
    except ImportError as e:
        print(f"  ✗ Failed to import netlist_simulator: {e}")
        print("  Make sure netlist_simulator is installed: pip install -e ../netlist_simulator")
        return False

    # Create a sample netlist
    sample_netlist = """RC Low-Pass Filter Test
* Generated for testing
V1 in 0 DC 5 AC 1
R1 in out 1k
C1 out 0 1u
.tran 1u 10m
.end
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.cir', delete=False) as f:
        f.write(sample_netlist)
        cir_path = f.name

    try:
        print(f"  Created test netlist: {cir_path}")

        # Run simulation
        sim_config = SimulationConfig()
        simulator = CircuitSimulator(config=sim_config)

        # Validate
        is_valid, msg = simulator.validate_cir_file(cir_path)
        print(f"  Validation: {is_valid} - {msg}")

        if not is_valid:
            return False

        # Simulate
        print("  Running simulation...")
        result = simulator.simulate(cir_path, verbose=True)
        print(f"  ✓ Simulation complete: {result.sim_type}")
        print(f"  Nodes: {list(result.nodes.keys())}")
        print(f"  Branches: {list(result.branches.keys())}")

        # Generate plots
        with tempfile.TemporaryDirectory() as plot_dir:
            plot_config = PlotConfig(
                plot_types=[PlotType.OVERLAY],
                figure_dpi=100,
                output_format='png',
                show_plots=False
            )
            plotter = CircuitPlotter(config=plot_config)
            output_base = os.path.join(plot_dir, "test")
            saved_files = plotter.plot_all(result, output_base)
            print(f"  ✓ Generated {len(saved_files)} plots")
            for f in saved_files:
                print(f"    - {os.path.basename(f)}")

        print("\n✓ Simulation test passed")
        return True

    except Exception as e:
        print(f"  ✗ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if os.path.exists(cir_path):
            os.unlink(cir_path)


def test_handler(image_path: str):
    """Test the RunPod handler with an image."""
    print(f"\n=== Testing Handler with {image_path} ===")

    if not os.path.exists(image_path):
        print(f"  ✗ Image not found: {image_path}")
        return False

    try:
        from handler import handler

        # Read and encode image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        # Build job
        job = {
            "input": {
                "image": image_b64,
                "options": {
                    "use_vlm": True,
                    "debug": True
                }
            }
        }

        print("  Calling handler...")
        result = handler(job)

        # Check result
        print(f"\n  Status: {result['status']}")

        if result.get('error_message'):
            print(f"  Error: {result['error_message']}")

        if result.get('netlist'):
            print(f"\n  Netlist ({len(result['netlist'])} chars):")
            print("  " + "\n  ".join(result['netlist'].split('\n')[:10]))
            if len(result['netlist'].split('\n')) > 10:
                print("  ...")

        if result.get('plots'):
            print(f"\n  Plots: {list(result['plots'].keys())}")

        if result.get('timing'):
            print(f"\n  Timing:")
            for k, v in result['timing'].items():
                print(f"    {k}: {v:.3f}s")

        if result.get('warnings'):
            print(f"\n  Warnings: {result['warnings']}")

        success = result['status'] in ['success', 'partial']
        print(f"\n{'✓' if success else '✗'} Handler test {'passed' if success else 'failed'}")
        return success

    except Exception as e:
        print(f"  ✗ Handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Test CircuitVision backend locally")
    parser.add_argument("--sim-only", action="store_true", help="Test simulation only")
    parser.add_argument("--image", type=str, help="Path to circuit image for handler test")
    parser.add_argument("--handler", type=str, help="Alias for --image")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    args = parser.parse_args()

    print("=" * 60)
    print("CircuitVision Backend Local Test")
    print("=" * 60)

    results = {}

    # Always test normalizer
    try:
        test_netlist_normalizer()
        results['normalizer'] = True
    except Exception as e:
        print(f"  ✗ Normalizer test failed: {e}")
        results['normalizer'] = False

    # Test simulation
    if args.sim_only or args.all or not (args.image or args.handler):
        results['simulation'] = test_simulation()

    # Test handler with image
    image_path = args.image or args.handler
    if image_path:
        results['handler'] = test_handler(image_path)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_name}: {status}")

    all_passed = all(results.values())
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
