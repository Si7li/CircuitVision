# CircuitVision Flutter App

Mobile app for circuit schematic analysis using AI.

## Features

- 📷 Capture circuit photos with camera
- 🖼️ Select images from gallery
- ⚡ Generate SPICE netlist automatically
- 📊 View simulation plots
- 📋 Copy netlist to clipboard

## Setup

### Prerequisites

- Flutter SDK 3.0+
- Dart 3.0+
- Android Studio / Xcode (for emulators)

### Installation

1. **Install dependencies**:
   ```bash
   cd flutter_app
   flutter pub get
   ```

2. **Configure API endpoint**:

   Edit `lib/services/api_config.dart`:
   ```dart
   // Option 1: Use proxy (recommended for production)
   class ProxyConfig {
     static const bool useProxy = true;
     static const String proxyBaseUrl = 'https://your-proxy-server.com/api/circuit';
   }

   // Option 2: Direct RunPod (development only)
   class ApiConfig {
     static const String endpointId = 'YOUR_RUNPOD_ENDPOINT_ID';
   }
   ```

3. **Run the app**:
   ```bash
   flutter run
   ```

## Project Structure

```
lib/
├── main.dart                # App entry point
├── models/
│   └── circuit_result.dart  # Data models
├── services/
│   ├── api_config.dart      # API configuration
│   └── circuit_service.dart # API service with polling
├── screens/
│   ├── home_screen.dart     # Landing page
│   ├── capture_screen.dart  # Image capture/selection
│   └── results_screen.dart  # Netlist and plots display
└── widgets/                 # Reusable components
```

## Security

**⚠️ NEVER embed API keys in the app!**

The app is designed to work with a secure proxy server that holds the RunPod API key. See `api_config.dart` for the proxy configuration.

### Secure Architecture

```
App → Your Proxy Server → RunPod
        (holds API key)
```

## Screens

### Home Screen
- App introduction
- Camera and gallery buttons

### Capture Screen
- Image preview
- Camera capture
- Gallery selection
- Analysis initiation

### Results Screen
- Tabbed interface (Netlist / Plots)
- Copyable netlist text
- Zoomable plot images
- Timing and debug info

## State Management

Uses Provider for state management:

```dart
// Access the service
final service = context.watch<CircuitService>();

// Check state
if (service.state == ProcessingState.processing) {
  showLoading();
}

// Get results
final result = service.result;
```

## API Integration

### Job Lifecycle

1. **Submit**: POST image to `/analyze`
2. **Poll**: GET `/status/{jobId}` until complete
3. **Handle**: Process response or show error

### States

| State | Description |
|-------|-------------|
| `idle` | Ready for new analysis |
| `uploading` | Sending image to server |
| `queued` | Waiting in RunPod queue |
| `processing` | Analysis in progress |
| `completed` | Results ready |
| `error` | Something went wrong |

## Building

### Android
```bash
flutter build apk --release
```

### iOS
```bash
flutter build ios --release
```

## Testing

```bash
flutter test
```

## Dependencies

- `provider` - State management
- `http` - HTTP client
- `image_picker` - Camera/gallery access
- `path_provider` - File system access
- `share_plus` - Share functionality

## License

Internal use - see project license.
