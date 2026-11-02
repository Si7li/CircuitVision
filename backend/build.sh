#!/bin/bash
# Build script for CircuitVision RunPod Docker image
#
# Usage:
#   ./build.sh [--push] [--tag TAG]
#
# Options:
#   --push    Push to Docker Hub after building
#   --tag     Custom tag (default: circuitvision-runpod:latest)

set -e

# Configuration
DEFAULT_TAG="circuitvision-runpod:latest"
REGISTRY=""  # Set to your registry, e.g., "docker.io/username/"

# Parse arguments
PUSH=false
TAG="$DEFAULT_TAG"

while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH=true
            shift
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=============================================="
echo "Building CircuitVision RunPod Docker Image"
echo "=============================================="
echo "Project root: $PROJECT_ROOT"
echo "Tag: $TAG"
echo ""

# Build from project root
cd "$PROJECT_ROOT"

echo "Building Docker image..."
docker build \
    -f backend/Dockerfile \
    -t "$TAG" \
    .

echo ""
echo "Build complete!"

# Test the build
echo ""
echo "Running quick verification..."
docker run --rm "$TAG" python -c "
import sys
sys.path.insert(0, '/app')
from src.netlist_normalizer import NetlistNormalizer
n = NetlistNormalizer()
result = n.normalize('R1 in out 1k\\nC1 out 0 1u')
assert result.success, 'Normalizer test failed'
print('Normalizer test: PASS')
"

# Run simulation-only test
echo ""
echo "Running simulation test..."
docker run --rm "$TAG" python test_local.py --sim-only

# Push if requested
if [ "$PUSH" = true ]; then
    echo ""
    echo "Pushing to registry..."
    docker push "${REGISTRY}${TAG}"
    echo "Push complete!"
fi

echo ""
echo "=============================================="
echo "Build Summary"
echo "=============================================="
echo "Image: $TAG"
echo "Size: $(docker images --format '{{.Size}}' "$TAG")"
echo ""
echo "To run locally:"
echo "  docker run --rm -it $TAG python test_local.py --sim-only"
echo ""
echo "To test with an image:"
echo "  docker run --rm -v \$(pwd)/test_image.png:/app/test.png $TAG python test_local.py /app/test.png"
echo ""
echo "For RunPod deployment, push to your container registry:"
echo "  docker tag $TAG your-registry/$TAG"
echo "  docker push your-registry/$TAG"
