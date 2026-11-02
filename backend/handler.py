"""
RunPod Serverless Handler

Single entrypoint for the CircuitVision + netlist_simulator pipeline.
Handles image input, processing, and returns netlist + simulation plots.

RunPod Handler Contract:
- Input: {"input": {"image": "<base64_encoded_image>", "options": {...}}}
- Output: {"status": "...", "netlist": "...", "plots": {...}, ...}
"""

import os
import sys
import base64
import tempfile
import json
import logging
import traceback
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add paths for local imports
HANDLER_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(HANDLER_DIR))
sys.path.insert(0, str(HANDLER_DIR / "src"))

from src.pipeline import CircuitPipeline


def decode_image(image_data: str) -> bytes:
    """
    Decode base64 image data.

    Args:
        image_data: Base64 encoded image string

    Returns:
        Raw image bytes
    """
    # Handle data URI format (data:image/png;base64,...)
    if ',' in image_data:
        image_data = image_data.split(',', 1)[1]

    return base64.b64decode(image_data)


def validate_input(job_input: dict) -> tuple:
    """
    Validate the job input.

    Args:
        job_input: The input dictionary from RunPod

    Returns:
        Tuple of (is_valid, error_message or None, validated_data)
    """
    if not job_input:
        return False, "No input provided", None

    image_data = job_input.get("image")
    if not image_data:
        return False, "Missing 'image' field in input. Expected base64 encoded image.", None

    # Validate base64
    try:
        image_bytes = decode_image(image_data)
        if len(image_bytes) < 100:
            return False, "Image data too small - likely corrupted or invalid", None
    except Exception as e:
        return False, f"Invalid base64 image data: {str(e)}", None

    # Extract options
    options = job_input.get("options", {})
    validated = {
        "image_bytes": image_bytes,
        "use_vlm": options.get("use_vlm", True),
        "debug": options.get("debug", False),
        "title": options.get("title", "CircuitVision Circuit")
    }

    return True, None, validated


def handler(job: dict) -> dict:
    """
    RunPod serverless handler function.

    Args:
        job: RunPod job dictionary with 'input' key

    Returns:
        Result dictionary with status, netlist, plots, timing, etc.
    """
    logger.info("Handler invoked")

    try:
        job_input = job.get("input", {})

        # Validate input
        is_valid, error_msg, validated = validate_input(job_input)
        if not is_valid:
            logger.error(f"Input validation failed: {error_msg}")
            return {
                "status": "error",
                "error_message": error_msg,
                "netlist": "",
                "plots": {}
            }

        # Write image to temp file
        with tempfile.NamedTemporaryFile(
            suffix='.png', delete=False
        ) as tmp_file:
            tmp_file.write(validated["image_bytes"])
            image_path = tmp_file.name

        try:
            # Initialize pipeline
            logger.info("Initializing pipeline...")
            pipeline = CircuitPipeline(
                use_vlm=validated["use_vlm"],
                debug=validated["debug"]
            )

            # Process image
            logger.info(f"Processing image: {image_path}")
            result = pipeline.process_image(image_path)

            # Format response
            response = {
                "status": result.status,
                "netlist": result.netlist,
                "plots": result.plots,
                "timing": result.timing,
                "warnings": result.warnings
            }

            # Include debug info if requested
            if validated["debug"]:
                response["debug_info"] = result.debug_info

            if result.error_message:
                response["error_message"] = result.error_message

            logger.info(f"Processing complete. Status: {result.status}")
            return response

        finally:
            # Clean up temp file
            if os.path.exists(image_path):
                os.unlink(image_path)

    except Exception as e:
        logger.exception("Handler exception")
        return {
            "status": "error",
            "error_message": f"Internal error: {str(e)}",
            "traceback": traceback.format_exc() if os.getenv("DEBUG") else None,
            "netlist": "",
            "plots": {}
        }


# RunPod entry point
if __name__ == "__main__":
    # Check if running locally or via RunPod
    if os.getenv("RUNPOD_POD_ID"):
        # Running on RunPod - use their serverless module
        import runpod
        runpod.serverless.start({"handler": handler})
    else:
        # Local testing mode
        print("Running in local test mode")
        print("Use test_local.py for local testing with sample images")
