/// Circuit analysis API service with RunPod polling support.

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/circuit_result.dart';
import 'api_config.dart';

/// Service for circuit analysis API calls.
///
/// This service handles:
/// - Uploading images to the RunPod endpoint
/// - Polling for job status
/// - Returning results
///
/// IMPORTANT: In production, use a secure proxy server instead of
/// embedding the RunPod API key directly in the app.
class CircuitService extends ChangeNotifier {
  /// Current processing state.
  ProcessingState _state = ProcessingState.idle;
  ProcessingState get state => _state;

  /// Current job ID for polling.
  String? _currentJobId;
  String? get currentJobId => _currentJobId;

  /// Latest result.
  CircuitResult? _result;
  CircuitResult? get result => _result;

  /// Error message if any.
  String? _error;
  String? get error => _error;

  /// Progress message for UI.
  String _progressMessage = '';
  String get progressMessage => _progressMessage;

  /// Polling timer.
  Timer? _pollingTimer;

  /// HTTP client.
  final http.Client _client = http.Client();

  /// API key (should come from secure storage in production).
  /// PLACEHOLDER: Replace with secure key management.
  String? _apiKey;

  /// Set the API key.
  /// In production, this should be fetched from secure storage
  /// or handled by a proxy server.
  void setApiKey(String key) {
    _apiKey = key;
  }

  /// Analyze a circuit image.
  ///
  /// [imageBytes] - Raw image bytes
  /// [useVlm] - Whether to use VLM for value extraction
  /// [debug] - Enable debug info in response
  Future<CircuitResult> analyzeImage({
    required Uint8List imageBytes,
    bool useVlm = true,
    bool debug = false,
  }) async {
    // Validate image size
    if (imageBytes.length > ApiConfig.maxImageSizeBytes) {
      throw CircuitServiceException(
        'Image too large. Maximum size: ${ApiConfig.maxImageSizeBytes ~/ (1024 * 1024)}MB',
      );
    }

    try {
      _setState(ProcessingState.uploading);
      _setProgress('Uploading image...');

      // Encode image to base64
      final imageB64 = base64Encode(imageBytes);

      // Build request body
      final body = {
        'input': {
          'image': imageB64,
          'options': {
            'use_vlm': useVlm,
            'debug': debug,
          },
        },
      };

      // Submit job
      final jobId = await _submitJob(body);
      _currentJobId = jobId;

      _setState(ProcessingState.queued);
      _setProgress('Job submitted, waiting in queue...');

      // Poll for result
      final result = await _pollForResult(jobId);
      _result = result;

      _setState(ProcessingState.completed);
      _setProgress('Analysis complete!');

      return result;
    } catch (e) {
      _setState(ProcessingState.error);
      _error = e.toString();
      _setProgress('Error: $_error');
      rethrow;
    }
  }

  /// Analyze a circuit image from file path.
  Future<CircuitResult> analyzeImageFile(String filePath) async {
    final file = File(filePath);
    if (!await file.exists()) {
      throw CircuitServiceException('File not found: $filePath');
    }

    final bytes = await file.readAsBytes();
    return analyzeImage(imageBytes: bytes);
  }

  /// Submit a job to RunPod.
  Future<String> _submitJob(Map<String, dynamic> body) async {
    final headers = _buildHeaders();
    final url = ProxyConfig.analyzeUrl;

    final response = await _client
        .post(
          Uri.parse(url),
          headers: headers,
          body: jsonEncode(body),
        )
        .timeout(Duration(seconds: ApiConfig.requestTimeoutSeconds));

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw CircuitServiceException(
        'Failed to submit job: ${response.statusCode} - ${response.body}',
      );
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final jobId = data['id'] as String?;

    if (jobId == null) {
      throw CircuitServiceException('No job ID in response: ${response.body}');
    }

    return jobId;
  }

  /// Poll for job result.
  Future<CircuitResult> _pollForResult(String jobId) async {
    final startTime = DateTime.now();
    final maxDuration = Duration(seconds: ApiConfig.maxPollingDurationSeconds);

    while (true) {
      // Check timeout
      if (DateTime.now().difference(startTime) > maxDuration) {
        throw CircuitServiceException(
          'Job timed out after ${ApiConfig.maxPollingDurationSeconds} seconds',
        );
      }

      // Get status
      final status = await _getJobStatus(jobId);

      if (status.isCompleted) {
        if (status.output != null) {
          return status.output!;
        }
        throw CircuitServiceException('Job completed but no output received');
      }

      if (status.isFailed) {
        throw CircuitServiceException(
          status.error ?? 'Job failed with status: ${status.status}',
        );
      }

      // Update progress
      if (status.status == 'IN_QUEUE') {
        _setState(ProcessingState.queued);
        _setProgress('Waiting in queue...');
      } else if (status.status == 'IN_PROGRESS') {
        _setState(ProcessingState.processing);
        _setProgress('Analyzing circuit...');
      }

      // Wait before next poll
      await Future.delayed(
        Duration(milliseconds: ApiConfig.pollingIntervalMs),
      );
    }
  }

  /// Get job status.
  Future<RunPodJobStatus> _getJobStatus(String jobId) async {
    final headers = _buildHeaders();
    final url = ProxyConfig.statusUrl(jobId);

    final response = await _client
        .get(Uri.parse(url), headers: headers)
        .timeout(Duration(seconds: ApiConfig.requestTimeoutSeconds));

    if (response.statusCode != 200) {
      throw CircuitServiceException(
        'Failed to get job status: ${response.statusCode}',
      );
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return RunPodJobStatus.fromJson(data);
  }

  /// Cancel current job.
  Future<void> cancelCurrentJob() async {
    if (_currentJobId == null) return;

    try {
      final headers = _buildHeaders();
      final url = ApiConfig.cancelUrl(_currentJobId!);

      await _client
          .post(Uri.parse(url), headers: headers)
          .timeout(Duration(seconds: ApiConfig.requestTimeoutSeconds));
    } catch (e) {
      debugPrint('Failed to cancel job: $e');
    } finally {
      reset();
    }
  }

  /// Reset service state.
  void reset() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
    _currentJobId = null;
    _result = null;
    _error = null;
    _setState(ProcessingState.idle);
    _setProgress('');
  }

  /// Build request headers.
  Map<String, String> _buildHeaders() {
    final headers = {
      'Content-Type': 'application/json',
    };

    // Add API key if not using proxy
    if (!ProxyConfig.useProxy) {
      headers['Authorization'] = 'Bearer ${ProxyConfig.runpodApiKey}';
    }

    return headers;
  }

  void _setState(ProcessingState newState) {
    _state = newState;
    notifyListeners();
  }

  void _setProgress(String message) {
    _progressMessage = message;
    notifyListeners();
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    _client.close();
    super.dispose();
  }
}

/// Exception thrown by CircuitService.
class CircuitServiceException implements Exception {
  final String message;
  CircuitServiceException(this.message);

  @override
  String toString() => message;
}
