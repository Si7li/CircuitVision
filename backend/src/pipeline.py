"""
CircuitVision + Simulation Pipeline

Orchestrates the full pipeline:
1. Process image through CircuitVision
2. Normalize netlist for simulation
3. Run simulation with netlist_simulator
4. Return results with PNG plots
"""

import os
import sys
import cv2
import base64
import tempfile
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from copy import deepcopy

# Add parent directories to path for imports
SCRIPT_DIR = Path(__file__).parent.resolve()  # /app/src or backend/src
APP_DIR = SCRIPT_DIR.parent  # /app or backend

# Check if running in container (/app) or locally
if (APP_DIR / "CircuitVision").exists():
    # Container structure: /app/CircuitVision, /app/netlist_simulator
    CV_PATH = APP_DIR / "CircuitVision"
    SIM_PATH = APP_DIR / "netlist_simulator"
else:
    # Local structure: backend/../CircuitVision
    PROJECT_ROOT = APP_DIR.parent
    CV_PATH = PROJECT_ROOT / "CircuitVision"
    SIM_PATH = PROJECT_ROOT / "netlist_simulator"

sys.path.insert(0, str(CV_PATH))  # For imports like 'from src.circuit_analyzer'
sys.path.insert(0, str(SIM_PATH / "src"))

from .netlist_normalizer import NetlistNormalizer, NormalizationResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result from the full pipeline."""
    status: str  # "success", "error", "partial"
    netlist: str = ""
    plots: Dict[str, str] = field(default_factory=dict)  # name -> base64 PNG
    timing: Dict[str, float] = field(default_factory=dict)
    debug_info: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)


class CircuitPipeline:
    """
    Full pipeline for circuit image -> netlist -> simulation -> plots.

    This class integrates CircuitVision for image processing and
    netlist_simulator for SPICE simulation.
    """

    def __init__(
        self,
        yolo_path: Optional[str] = None,
        sam2_config_path: Optional[str] = None,
        sam2_base_checkpoint_path: Optional[str] = None,
        sam2_finetuned_checkpoint_path: Optional[str] = None,
        use_sam2: bool = True,
        use_vlm: bool = True,
        debug: bool = False
    ):
        """
        Initialize the pipeline.

        Args:
            yolo_path: Path to YOLO model weights
            sam2_config_path: Path to SAM2 config
            sam2_base_checkpoint_path: Path to SAM2 base checkpoint
            sam2_finetuned_checkpoint_path: Path to SAM2 finetuned checkpoint
            use_sam2: Whether to use SAM2 for segmentation
            use_vlm: Whether to use VLM for value extraction
            debug: Enable debug mode
        """
        self.use_sam2 = use_sam2
        self.use_vlm = use_vlm
        self.debug = debug

        # Default model paths
        self.model_dir = CV_PATH / "models"
        self.yolo_path = yolo_path or str(self.model_dir / "YOLO" / "best_large_model_yolo.pt")
        self.sam2_config_path = sam2_config_path or "/models/configs/sam2.1_hiera_l.yaml"
        self.sam2_base_checkpoint_path = sam2_base_checkpoint_path or str(
            self.model_dir / "SAM2" / "sam2.1_hiera_large.pt"
        )
        self.sam2_finetuned_checkpoint_path = sam2_finetuned_checkpoint_path or str(
            self.model_dir / "SAM2" / "best_miou_model_SAM_latest.pth"
        )

        self._analyzer = None
        self._normalizer = NetlistNormalizer()

    def _get_analyzer(self):
        """Lazily load CircuitAnalyzer."""
        if self._analyzer is None:
            from src.circuit_analyzer import CircuitAnalyzer
            self._analyzer = CircuitAnalyzer(
                yolo_path=self.yolo_path,
                sam2_config_path=self.sam2_config_path,
                sam2_base_checkpoint_path=self.sam2_base_checkpoint_path,
                sam2_finetuned_checkpoint_path=self.sam2_finetuned_checkpoint_path,
                use_sam2=self.use_sam2,
                debug=self.debug
            )
        return self._analyzer

    def process_image(self, image_path: str) -> PipelineResult:
        """
        Process a circuit image and return netlist + simulation plots.

        Args:
            image_path: Path to the circuit image

        Returns:
            PipelineResult with netlist and base64 encoded PNG plots
        """
        timing = {}
        debug_info = {}
        warnings = []

        try:
            # Validate input
            if not os.path.exists(image_path):
                return PipelineResult(
                    status="error",
                    error_message=f"Image file not found: {image_path}"
                )

            # Load image
            start_time = time.time()
            image_bgr = cv2.imread(image_path)
            if image_bgr is None:
                return PipelineResult(
                    status="error",
                    error_message=f"Failed to load image: {image_path}"
                )

            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            timing["image_load"] = time.time() - start_time

            # Run CircuitVision pipeline
            netlist_str, cv_timing, cv_debug = self._run_circuit_vision(image_rgb)
            timing.update(cv_timing)
            debug_info.update(cv_debug)

            if not netlist_str:
                return PipelineResult(
                    status="error",
                    error_message="CircuitVision failed to generate netlist",
                    timing=timing,
                    debug_info=debug_info
                )

            # Normalize netlist
            start_time = time.time()
            norm_result = self._normalizer.normalize(netlist_str, "CircuitVision Circuit")
            timing["netlist_normalization"] = time.time() - start_time

            if not norm_result.success:
                warnings.extend(norm_result.errors)
                # Try to proceed anyway if we have some netlist
                if not norm_result.normalized_netlist:
                    return PipelineResult(
                        status="error",
                        error_message=f"Netlist normalization failed: {', '.join(norm_result.errors)}",
                        netlist=netlist_str,
                        timing=timing,
                        debug_info=debug_info
                    )

            debug_info["normalization_changes"] = norm_result.changes_made
            final_netlist = norm_result.normalized_netlist

            # Run simulation
            plots, sim_timing, sim_warnings = self._run_simulation(final_netlist)
            timing.update(sim_timing)
            warnings.extend(sim_warnings)

            status = "success" if plots else "partial"
            if not plots:
                warnings.append("Simulation completed but no plots were generated")

            return PipelineResult(
                status=status,
                netlist=final_netlist,
                plots=plots,
                timing=timing,
                debug_info=debug_info,
                warnings=warnings
            )

        except Exception as e:
            logger.exception("Pipeline error")
            return PipelineResult(
                status="error",
                error_message=f"Pipeline error: {str(e)}",
                timing=timing,
                debug_info=debug_info
            )

    def _run_circuit_vision(self, image_rgb) -> tuple:
        """Run CircuitVision pipeline on image."""
        timing = {}
        debug_info = {}

        try:
            analyzer = self._get_analyzer()

            # Import utilities
            from src.utils import non_max_suppression_by_confidence, gemini_labels

            # Phase 1: YOLO detection
            start = time.time()
            raw_bboxes = analyzer.bboxes(image_rgb)
            bboxes_nms = non_max_suppression_by_confidence(raw_bboxes, iou_threshold=0.6)
            timing["yolo_detection"] = time.time() - start
            debug_info["detected_components"] = len(bboxes_nms)

            if not bboxes_nms:
                return "", timing, debug_info

            # Phase 2: Crop and segment
            start = time.time()
            cropped_image, adjusted_bboxes, crop_info = analyzer.crop_image_and_adjust_bboxes(
                image_rgb, deepcopy(bboxes_nms), padding=80
            )
            timing["crop"] = time.time() - start

            if self.use_sam2:
                start = time.time()
                binary_mask, colored_mask, extent_bbox = analyzer.segment_with_sam2(cropped_image)
                timing["sam2_segmentation"] = time.time() - start
            else:
                # Fallback: create simple mask
                import numpy as np
                binary_mask = np.ones(cropped_image.shape[:2], dtype=np.uint8) * 255

            # Phase 3: Node analysis
            start = time.time()
            nodes, emptied_mask, enhanced, contour_img, viz, conn_points = analyzer.get_node_connections(
                cropped_image, binary_mask, adjusted_bboxes
            )
            timing["node_analysis"] = time.time() - start
            debug_info["nodes_found"] = len(nodes) if nodes else 0

            # Phase 4: Generate netlist
            start = time.time()
            valueless_netlist = analyzer.generate_netlist_from_nodes(nodes)
            timing["netlist_generation"] = time.time() - start

            # Phase 5: VLM value enrichment (optional)
            if self.use_vlm and valueless_netlist:
                start = time.time()
                try:
                    enum_img, bbox_ids = analyzer.enumerate_components(
                        cropped_image, deepcopy(adjusted_bboxes)
                    )
                    gemini_info = gemini_labels(enum_img)
                    final_netlist = deepcopy(valueless_netlist)
                    analyzer.fix_netlist(final_netlist, gemini_info, bbox_ids)
                    timing["vlm_enrichment"] = time.time() - start
                except Exception as e:
                    logger.warning(f"VLM enrichment failed: {e}")
                    final_netlist = valueless_netlist
                    timing["vlm_enrichment"] = time.time() - start
                    debug_info["vlm_error"] = str(e)
            else:
                final_netlist = valueless_netlist

            # Convert to SPICE string
            netlist_lines = [analyzer.stringify_line(line) for line in final_netlist]
            netlist_str = '\n'.join(netlist_lines)

            return netlist_str, timing, debug_info

        except Exception as e:
            logger.exception("CircuitVision error")
            debug_info["error"] = str(e)
            return "", timing, debug_info

    def _run_simulation(self, netlist: str) -> tuple:
        """Run SPICE simulation and generate plots."""
        timing = {}
        warnings = []
        plots = {}

        try:
            from circuit_simulator import CircuitSimulator, CircuitPlotter
            from circuit_simulator.config import SimulationConfig, PlotConfig, PlotType

            # Write netlist to temp file
            start = time.time()
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.cir', delete=False
            ) as f:
                f.write(netlist)
                cir_path = f.name

            try:
                # Configure simulation
                sim_config = SimulationConfig(
                    tran_step_time=10e-6,
                    tran_end_time=10e-3
                )

                plot_config = PlotConfig(
                    plot_types=[PlotType.OVERLAY, PlotType.INDIVIDUAL, PlotType.CURRENTS],
                    figure_dpi=150,
                    output_format='png',
                    show_plots=False
                )

                # Run simulation
                simulator = CircuitSimulator(config=sim_config)

                # Validate first
                is_valid, msg = simulator.validate_cir_file(cir_path)
                if not is_valid:
                    warnings.append(f"Validation warning: {msg}")

                result = simulator.simulate(cir_path, verbose=False)
                timing["simulation"] = time.time() - start

                # Generate plots
                start = time.time()
                with tempfile.TemporaryDirectory() as plot_dir:
                    plotter = CircuitPlotter(config=plot_config)
                    output_base = os.path.join(plot_dir, "circuit")
                    saved_files = plotter.plot_all(result, output_base)

                    # Read and encode plots
                    for plot_file in saved_files:
                        if os.path.exists(plot_file):
                            with open(plot_file, 'rb') as f:
                                plot_data = f.read()
                            plot_name = os.path.basename(plot_file)
                            plots[plot_name] = base64.b64encode(plot_data).decode('utf-8')

                timing["plot_generation"] = time.time() - start

            finally:
                # Clean up temp file
                if os.path.exists(cir_path):
                    os.unlink(cir_path)

        except Exception as e:
            logger.exception("Simulation error")
            warnings.append(f"Simulation failed: {str(e)}")

        return plots, timing, warnings


def process_circuit_image(
    image_path: str,
    use_vlm: bool = True,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to process a circuit image.

    Args:
        image_path: Path to circuit image
        use_vlm: Whether to use VLM for value extraction
        debug: Enable debug mode

    Returns:
        Dictionary with status, netlist, plots, timing, and debug info
    """
    pipeline = CircuitPipeline(use_vlm=use_vlm, debug=debug)
    result = pipeline.process_image(image_path)

    return {
        "status": result.status,
        "netlist": result.netlist,
        "plots": result.plots,
        "timing": result.timing,
        "debug_info": result.debug_info,
        "error_message": result.error_message,
        "warnings": result.warnings
    }
