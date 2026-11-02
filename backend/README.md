# CircuitVision Mobile Backend

End-to-end system for circuit image analysis and SPICE simulation via RunPod serverless.

## Overview

This system provides:
- **Image → Netlist**: Process circuit photos using CircuitVision (YOLO + SAM2 + VLM)
- **Netlist → Simulation**: Run SPICE simulation via ngspice/PySpice
- **Simulation → Plots**: Generate PNG plots of circuit behavior
- **API**: RunPod serverless endpoint for mobile app integration

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────┐
│  Flutter App    │────▶│  RunPod Serverless                       │
│                 │     │  ┌──────────────────────────────────────┐│
│  - Capture      │◀────│  │ handler.py                           ││
│  - Results      │     │  │   └── pipeline.py                    ││
│                 │     │  │         ├── CircuitVision            ││
└─────────────────┘     │  │         │     (YOLO + SAM2 + VLM)    ││
                        │  │         ├── netlist_normalizer.py    ││
                        │  │         └── netlist_simulator        ││
                        │  └──────────────────────────────────────┘│
                        └──────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker with NVIDIA GPU support (for production)
- Python 3.10+
- ngspice (`apt install ngspice`)
- RunPod account (for deployment)

### Local Development

1. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   pip install -e ../netlist_simulator
   ```

2. **Set environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your GEMINI_API_KEY
   ```

3. **Download CircuitVision models**:
   ```bash
   cd ../CircuitVision
   python download_models.py
   ```

4. **Run local tests**:
   ```bash
   cd ../backend
   python test_local.py --sim-only
   ```

### Docker Build

Build from project root:
```bash
docker build -f backend/Dockerfile -t circuitvision-runpod .
```

Test locally:
```bash
docker run --rm -it \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  circuitvision-runpod python test_local.py --sim-only
```

### RunPod Deployment

1. Push image to Docker Hub or RunPod registry:
   ```bash
   docker tag circuitvision-runpod your-dockerhub/circuitvision-runpod:latest
   docker push your-dockerhub/circuitvision-runpod:latest
   ```

2. Create RunPod serverless endpoint:
   - Template: `your-dockerhub/circuitvision-runpod:latest`
   - GPU: Any NVIDIA GPU (RTX 3060+ recommended)
   - Environment: Set `GEMINI_API_KEY`

3. Note your endpoint ID for the mobile app.

## API Reference

### Request

**POST** `https://api.runpod.ai/v2/{endpoint_id}/run`

Headers:
```
Authorization: Bearer {RUNPOD_API_KEY}
Content-Type: application/json
```

Body:
```json
{
  "input": {
    "image": "<base64_encoded_image>",
    "options": {
      "use_vlm": true,
      "debug": false,
      "title": "My Circuit"
    }
  }
}
```

### Response

Job submission returns:
```json
{
  "id": "job-xxx",
  "status": "IN_QUEUE"
}
```

Poll status via `GET /status/{job_id}`:
```json
{
  "id": "job-xxx",
  "status": "COMPLETED",
  "output": {
    "status": "success",
    "netlist": "Circuit Name\nR1 in out 1k\n...\n.end",
    "plots": {
      "overlay.png": "<base64_png>",
      "currents.png": "<base64_png>"
    },
    "timing": {
      "image_load": 0.05,
      "yolo_detection": 0.8,
      "sam2_segmentation": 1.2,
      "node_analysis": 0.3,
      "netlist_generation": 0.1,
      "vlm_enrichment": 2.5,
      "netlist_normalization": 0.01,
      "simulation": 0.5,
      "plot_generation": 0.3
    },
    "warnings": [],
    "debug_info": {}
  }
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `success` | Full pipeline completed successfully |
| `partial` | Netlist generated but simulation failed |
| `error` | Pipeline failed (see `error_message`) |

### Error Response

```json
{
  "status": "error",
  "netlist": "",
  "plots": {},
  "error_message": "CircuitVision failed to generate netlist"
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for VLM |
| `OPENROUTER_API_KEY` | No | Alternative to Gemini |
| `DEBUG` | No | Enable debug traceback in errors |
| `RUNPOD_POD_ID` | Auto | Set by RunPod runtime |

## File Structure

```
backend/
├── handler.py              # RunPod entrypoint
├── test_local.py           # Local testing script
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container definition
├── docker-compose.yml      # Local development
├── src/
│   ├── __init__.py
│   ├── pipeline.py         # Main processing pipeline
│   └── netlist_normalizer.py  # Netlist validation/normalization
└── tests/
    ├── __init__.py
    └── test_netlist_normalizer.py  # Unit tests
```

## Testing Checklist

### Local Tests

- [ ] `python test_local.py --sim-only` passes
- [ ] `pytest tests/` passes
- [ ] Handler processes sample image (requires models)

### Docker Tests

- [ ] Docker build completes without errors
- [ ] Container starts and handler initializes
- [ ] GPU is accessible (for CircuitVision)

### Integration Tests

- [ ] Submit job via RunPod API
- [ ] Poll status returns COMPLETED
- [ ] Response contains valid netlist
- [ ] Response contains base64 PNGs
- [ ] PNGs decode to valid images

### Flutter App Tests

- [ ] App compiles without errors
- [ ] Camera capture works
- [ ] Gallery selection works
- [ ] API call submits successfully
- [ ] Polling updates UI state
- [ ] Results display correctly
- [ ] Netlist is copyable
- [ ] Plots are zoomable

## Security Notes

**IMPORTANT: Never embed RunPod API keys in mobile apps!**

### Secure Proxy Pattern

1. Deploy a proxy server (Firebase Functions, AWS Lambda, etc.)
2. Store RunPod API key in server environment
3. Mobile app calls your proxy
4. Proxy forwards requests to RunPod

Example Firebase Function:
```javascript
exports.analyzeCircuit = functions.https.onCall(async (data, context) => {
  // Authenticate user
  if (!context.auth) throw new Error('Unauthenticated');

  // Forward to RunPod
  const response = await fetch(RUNPOD_URL, {
    headers: { 'Authorization': `Bearer ${RUNPOD_KEY}` },
    body: JSON.stringify({ input: data })
  });

  return response.json();
});
```

## Troubleshooting

### Simulation Fails

1. Check netlist has ground reference (node `0`)
2. Check netlist has voltage source
3. Check analysis directive is valid
4. Run ngspice manually: `ngspice -b circuit.cir`

### CircuitVision Fails

1. Ensure models are downloaded
2. Check image is readable (not corrupted)
3. Verify GEMINI_API_KEY is set
4. Check GPU memory (SAM2 needs ~4GB)

### RunPod Issues

1. Check endpoint is active
2. Verify API key permissions
3. Check container logs in RunPod dashboard
4. Ensure GPU worker is assigned

## License

Internal use - see project license.
