"""
RunPod Serverless Handler - Simple Version
Deploy directly without Docker using: runpod deploy

This version only does simulation (no CircuitVision) for easy testing.
"""

import runpod
import base64
import tempfile
import os

# Simple netlist normalizer (inline)
def normalize_netlist(netlist: str) -> str:
    """Ensure netlist has title, analysis directive, and .end"""
    lines = netlist.strip().split('\n')

    # Check if first line looks like a component
    first = lines[0].strip() if lines else ""
    if first and first[0].upper() in 'RCLVIDEQM' and len(first) > 1 and first[1].isdigit():
        lines.insert(0, "CircuitVision Circuit")

    # Check for .end
    has_end = any(line.strip().lower() == '.end' for line in lines)
    if not has_end:
        lines.append('.end')

    # Check for analysis directive
    content = '\n'.join(lines).lower()
    if '.tran' not in content and '.ac' not in content and '.dc' not in content:
        # Insert before .end
        for i, line in enumerate(lines):
            if line.strip().lower() == '.end':
                lines.insert(i, '.tran 10u 10m')
                break

    return '\n'.join(lines)


def run_simulation(netlist: str) -> dict:
    """Run SPICE simulation and generate plots."""
    try:
        from PySpice.Spice.Parser import SpiceParser
        from PySpice.Spice.NgSpice.Shared import NgSpiceShared
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np

        # Write netlist to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cir', delete=False) as f:
            f.write(netlist)
            cir_path = f.name

        try:
            # Parse and simulate
            parser = SpiceParser(path=cir_path)
            circuit = parser.build_circuit()
            simulator = circuit.simulator()

            # Run transient analysis
            analysis = simulator.transient(step_time=10e-6, end_time=10e-3)

            # Generate plot
            fig, ax = plt.subplots(figsize=(10, 6))
            time_data = np.array(analysis.time) * 1000  # Convert to ms

            for node_name in analysis.nodes:
                if node_name != '0':
                    voltage = np.array(analysis[node_name])
                    ax.plot(time_data, voltage, label=f'V({node_name})')

            ax.set_xlabel('Time (ms)')
            ax.set_ylabel('Voltage (V)')
            ax.set_title('Circuit Simulation')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Save to base64
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as png_file:
                plt.savefig(png_file.name, dpi=150, bbox_inches='tight')
                plt.close()

                with open(png_file.name, 'rb') as f:
                    plot_b64 = base64.b64encode(f.read()).decode('utf-8')
                os.unlink(png_file.name)

            return {
                "success": True,
                "plots": {"simulation.png": plot_b64}
            }

        finally:
            os.unlink(cir_path)

    except Exception as e:
        return {"success": False, "error": str(e)}


def handler(job):
    """RunPod handler function."""
    job_input = job.get("input", {})

    # Get netlist from input (or use sample)
    netlist = job_input.get("netlist", """
RC Filter Test
V1 in 0 DC 0 SIN(0 5 1k)
R1 in out 1k
C1 out 0 1u
.tran 10u 10m
.end
""")

    # Normalize netlist
    normalized = normalize_netlist(netlist)

    # Run simulation
    sim_result = run_simulation(normalized)

    return {
        "status": "success" if sim_result.get("success") else "error",
        "netlist": normalized,
        "plots": sim_result.get("plots", {}),
        "error_message": sim_result.get("error")
    }


# RunPod entry point
runpod.serverless.start({"handler": handler})
