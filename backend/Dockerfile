# CircuitVision + netlist_simulator RunPod Serverless Dockerfile
#
# This Dockerfile creates a container for running the circuit analysis
# and simulation pipeline on RunPod serverless.
#
# Build from project root:
#   docker build -f backend/Dockerfile -t circuitvision-runpod .
#
# Or use the build script:
#   cd backend && ./build.sh

FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

LABEL maintainer="CircuitVision Team"
LABEL description="CircuitVision + netlist_simulator RunPod serverless handler"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV MPLBACKEND=Agg

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # ngspice and SPICE simulation
    ngspice \
    libngspice0 \
    libngspice0-dev \
    # Build tools
    build-essential \
    gcc \
    g++ \
    # Image processing
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # Utilities
    git \
    wget \
    curl \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install SAM2 from git
RUN pip install --no-cache-dir git+https://github.com/facebookresearch/sam2.git

# Copy CircuitVision (excluding large model files initially)
COPY CircuitVision/src /app/CircuitVision/src
COPY CircuitVision/classes.json /app/CircuitVision/
COPY CircuitVision/download_models.py /app/CircuitVision/
COPY CircuitVision/requirements.txt /app/CircuitVision/

# Copy netlist_simulator
COPY netlist_simulator/src /app/netlist_simulator/src
COPY netlist_simulator/setup.py /app/netlist_simulator/
COPY netlist_simulator/requirements.txt /app/netlist_simulator/

# Install netlist_simulator
RUN pip install --no-cache-dir -e /app/netlist_simulator

# Copy backend code
COPY backend/src/ /app/src/
COPY backend/handler.py /app/
COPY backend/test_local.py /app/

# Create models directory
RUN mkdir -p /app/CircuitVision/models/YOLO \
             /app/CircuitVision/models/SAM2 \
             /app/CircuitVision/models/configs

# Download models
# Note: This requires models to be accessible. For production,
# consider using a model volume or pre-baked models.
WORKDIR /app/CircuitVision
RUN python download_models.py || echo "WARNING: Model download incomplete - ensure models are mounted"

WORKDIR /app

# Verify installations
RUN python -c "import torch; print(f'PyTorch: {torch.__version__}')" && \
    python -c "import cv2; print(f'OpenCV: {cv2.__version__}')" && \
    python -c "import matplotlib; print(f'Matplotlib: {matplotlib.__version__}')" && \
    python -c "from PySpice.Spice.Parser import SpiceParser; print('PySpice: OK')" && \
    ngspice --version | head -1

# Health check endpoint (for local testing)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import handler; print('OK')" || exit 1

# Default command: start RunPod handler
CMD ["python", "-u", "handler.py"]
