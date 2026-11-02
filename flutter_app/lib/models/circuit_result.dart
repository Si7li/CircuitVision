/// Data models for circuit analysis results.

import 'dart:convert';
import 'dart:typed_data';

/// Result from circuit analysis.
class CircuitResult {
  /// Status: "success", "partial", or "error".
  final String status;

  /// Generated SPICE netlist.
  final String netlist;

  /// Map of plot name -> base64 encoded PNG.
  final Map<String, String> plots;

  /// Timing information for each step.
  final Map<String, double> timing;

  /// Debug information (if requested).
  final Map<String, dynamic>? debugInfo;

  /// Error message if status is "error".
  final String? errorMessage;

  /// Warnings generated during processing.
  final List<String> warnings;

  CircuitResult({
    required this.status,
    required this.netlist,
    required this.plots,
    this.timing = const {},
    this.debugInfo,
    this.errorMessage,
    this.warnings = const [],
  });

  /// Whether the analysis was successful.
  bool get isSuccess => status == 'success';

  /// Whether the analysis was partial (e.g., no simulation plots).
  bool get isPartial => status == 'partial';

  /// Whether the analysis failed.
  bool get isError => status == 'error';

  /// Whether we have a netlist.
  bool get hasNetlist => netlist.isNotEmpty;

  /// Whether we have any plots.
  bool get hasPlots => plots.isNotEmpty;

  /// Get plot names.
  List<String> get plotNames => plots.keys.toList();

  /// Get decoded plot bytes.
  Uint8List? getPlotBytes(String plotName) {
    final b64 = plots[plotName];
    if (b64 == null) return null;
    return base64Decode(b64);
  }

  /// Get total processing time.
  double get totalTime {
    return timing.values.fold(0.0, (sum, t) => sum + t);
  }

  factory CircuitResult.fromJson(Map<String, dynamic> json) {
    return CircuitResult(
      status: json['status'] as String? ?? 'error',
      netlist: json['netlist'] as String? ?? '',
      plots: (json['plots'] as Map<String, dynamic>?)?.map(
            (k, v) => MapEntry(k, v as String),
          ) ??
          {},
      timing: (json['timing'] as Map<String, dynamic>?)?.map(
            (k, v) => MapEntry(k, (v as num).toDouble()),
          ) ??
          {},
      debugInfo: json['debug_info'] as Map<String, dynamic>?,
      errorMessage: json['error_message'] as String?,
      warnings: (json['warnings'] as List?)?.cast<String>() ?? [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status,
      'netlist': netlist,
      'plots': plots,
      'timing': timing,
      'debug_info': debugInfo,
      'error_message': errorMessage,
      'warnings': warnings,
    };
  }

  @override
  String toString() {
    return 'CircuitResult(status: $status, netlist: ${netlist.length} chars, plots: ${plots.length})';
  }
}

/// A decoded plot image.
class PlotImage {
  final String name;
  final Uint8List bytes;

  PlotImage({required this.name, required this.bytes});

  /// Create from base64 string.
  factory PlotImage.fromBase64(String name, String base64Data) {
    return PlotImage(
      name: name,
      bytes: base64Decode(base64Data),
    );
  }
}
