/// API configuration for CircuitVision service.
///
/// IMPORTANT: Do NOT embed RunPod API keys directly in the app.
/// Use a secure proxy server pattern instead.

import '../models/circuit_result.dart';

/// Configuration for direct RunPod API calls.
/// Only use this for development/testing.
class ApiConfig {
  /// RunPod endpoint ID: pass it at build time with --dart-define=RUNPOD_ENDPOINT_ID=...
  static const String endpointId =
      String.fromEnvironment('RUNPOD_ENDPOINT_ID', defaultValue: 'your-endpoint-id');

  /// Base URL for RunPod serverless API.
  static String get baseUrl => 'https://api.runpod.ai/v2/$endpointId';

  /// URL to submit a job.
  static String get runUrl => '$baseUrl/run';

  /// URL to check job status.
  static String statusUrl(String jobId) => '$baseUrl/status/$jobId';

  /// URL to cancel a job.
  static String cancelUrl(String jobId) => '$baseUrl/cancel/$jobId';

  /// Polling interval in milliseconds.
  static const int pollingIntervalMs = 2000;

  /// Maximum polling duration in seconds.
  static const int maxPollingDurationSeconds = 300;

  /// Request timeout in seconds.
  static const int requestTimeoutSeconds = 30;

  /// Maximum image size in bytes (10MB).
  static const int maxImageSizeBytes = 10 * 1024 * 1024;
}

/// Configuration for secure proxy pattern.
///
/// In production, you should:
/// 1. Deploy a proxy server (e.g., Firebase Functions, AWS Lambda, or your own backend)
/// 2. The proxy holds the RunPod API key securely
/// 3. Your app calls the proxy, which forwards to RunPod
///
/// This prevents API key exposure in client apps.
class ProxyConfig {
  /// Whether to use proxy server.
  /// Set to FALSE for testing, TRUE for production
  static const bool useProxy = false;

  /// RunPod API Key - FOR TESTING ONLY!
  /// In production, use a proxy server instead.
  /// Pass it at build time: flutter run --dart-define=RUNPOD_API_KEY=...
  static const String runpodApiKey = String.fromEnvironment('RUNPOD_API_KEY');

  /// Proxy server base URL.
  /// Replace with your actual proxy URL.
  static const String proxyBaseUrl = 'https://your-proxy-server.com/api/circuit';

  /// Get the URL for submitting analysis.
  static String get analyzeUrl {
    if (useProxy) {
      return '$proxyBaseUrl/analyze';
    }
    return ApiConfig.runUrl;
  }

  /// Get the URL for checking status.
  static String statusUrl(String jobId) {
    if (useProxy) {
      return '$proxyBaseUrl/status/$jobId';
    }
    return ApiConfig.statusUrl(jobId);
  }
}

/// Processing states for the service.
enum ProcessingState {
  idle,
  uploading,
  queued,
  processing,
  completed,
  error,
}

/// Job status from RunPod.
class RunPodJobStatus {
  final String id;
  final String status;
  final CircuitResult? output;
  final String? error;
  final double? executionTime;

  RunPodJobStatus({
    required this.id,
    required this.status,
    this.output,
    this.error,
    this.executionTime,
  });

  bool get isCompleted => status == 'COMPLETED';
  bool get isFailed => status == 'FAILED' || status == 'CANCELLED';
  bool get isInProgress => status == 'IN_PROGRESS';
  bool get isQueued => status == 'IN_QUEUE';

  factory RunPodJobStatus.fromJson(Map<String, dynamic> json) {
    CircuitResult? output;
    if (json['output'] != null) {
      output = CircuitResult.fromJson(json['output'] as Map<String, dynamic>);
    }

    return RunPodJobStatus(
      id: json['id'] as String? ?? '',
      status: json['status'] as String? ?? 'UNKNOWN',
      output: output,
      error: json['error'] as String?,
      executionTime: (json['executionTime'] as num?)?.toDouble(),
    );
  }
}
