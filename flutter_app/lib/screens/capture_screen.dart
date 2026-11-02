import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../services/circuit_service.dart';
import '../services/api_config.dart';
import 'results_screen.dart';

/// Screen for capturing or selecting a circuit image.
class CaptureScreen extends StatefulWidget {
  final bool openGallery;

  const CaptureScreen({super.key, this.openGallery = false});

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  final ImagePicker _picker = ImagePicker();
  File? _selectedImage;
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    if (widget.openGallery) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _pickFromGallery());
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final service = context.watch<CircuitService>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Capture Circuit'),
        actions: [
          if (_selectedImage != null)
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _clearImage,
              tooltip: 'Clear image',
            ),
        ],
      ),
      body: _isProcessing ? _buildProcessingView(service) : _buildCaptureView(theme),
    );
  }

  Widget _buildCaptureView(ThemeData theme) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Image preview
            Expanded(
              child: _selectedImage != null
                  ? _buildImagePreview()
                  : _buildPlaceholder(theme),
            ),
            const SizedBox(height: 24),

            // Action buttons
            if (_selectedImage != null) ...[
              FilledButton.icon(
                onPressed: _analyzeImage,
                icon: const Icon(Icons.play_arrow),
                label: const Text('Analyze Circuit'),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
              const SizedBox(height: 12),
            ],

            // Capture buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _captureFromCamera,
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Camera'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _pickFromGallery,
                    icon: const Icon(Icons.photo_library),
                    label: const Text('Gallery'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlaceholder(ThemeData theme) {
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceVariant.withOpacity(0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: theme.colorScheme.outline.withOpacity(0.3),
          width: 2,
          style: BorderStyle.solid,
        ),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.add_photo_alternate_outlined,
            size: 64,
            color: theme.colorScheme.onSurfaceVariant.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            'Select or capture a circuit image',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildImagePreview() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Image.file(
        _selectedImage!,
        fit: BoxFit.contain,
      ),
    );
  }

  Widget _buildProcessingView(CircuitService service) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Progress indicator
            _buildProgressIndicator(service.state),
            const SizedBox(height: 32),

            // Status message
            Text(
              service.progressMessage,
              style: Theme.of(context).textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),

            // State indicator
            Text(
              _getStateLabel(service.state),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                  ),
            ),
            const SizedBox(height: 32),

            // Cancel button
            OutlinedButton.icon(
              onPressed: _cancelProcessing,
              icon: const Icon(Icons.close),
              label: const Text('Cancel'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressIndicator(ProcessingState state) {
    return SizedBox(
      width: 80,
      height: 80,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CircularProgressIndicator(
            strokeWidth: 6,
            value: state == ProcessingState.completed ? 1.0 : null,
          ),
          Icon(
            _getStateIcon(state),
            size: 32,
            color: Theme.of(context).colorScheme.primary,
          ),
        ],
      ),
    );
  }

  IconData _getStateIcon(ProcessingState state) {
    switch (state) {
      case ProcessingState.idle:
        return Icons.hourglass_empty;
      case ProcessingState.uploading:
        return Icons.cloud_upload;
      case ProcessingState.queued:
        return Icons.queue;
      case ProcessingState.processing:
        return Icons.memory;
      case ProcessingState.completed:
        return Icons.check_circle;
      case ProcessingState.error:
        return Icons.error;
    }
  }

  String _getStateLabel(ProcessingState state) {
    switch (state) {
      case ProcessingState.idle:
        return 'Ready';
      case ProcessingState.uploading:
        return 'Uploading...';
      case ProcessingState.queued:
        return 'In Queue';
      case ProcessingState.processing:
        return 'Processing';
      case ProcessingState.completed:
        return 'Complete';
      case ProcessingState.error:
        return 'Error';
    }
  }

  Future<void> _captureFromCamera() async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 2048,
        maxHeight: 2048,
        imageQuality: 90,
      );

      if (photo != null) {
        setState(() {
          _selectedImage = File(photo.path);
        });
      }
    } catch (e) {
      _showError('Failed to capture image: $e');
    }
  }

  Future<void> _pickFromGallery() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 2048,
        maxHeight: 2048,
        imageQuality: 90,
      );

      if (image != null) {
        setState(() {
          _selectedImage = File(image.path);
        });
      }
    } catch (e) {
      _showError('Failed to select image: $e');
    }
  }

  void _clearImage() {
    setState(() {
      _selectedImage = null;
    });
  }

  Future<void> _analyzeImage() async {
    if (_selectedImage == null) return;

    setState(() {
      _isProcessing = true;
    });

    final service = context.read<CircuitService>();

    try {
      final bytes = await _selectedImage!.readAsBytes();
      final result = await service.analyzeImage(imageBytes: bytes);

      if (!mounted) return;

      // Navigate to results
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (context) => ResultsScreen(result: result),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      _showError('Analysis failed: $e');
      setState(() {
        _isProcessing = false;
      });
    }
  }

  void _cancelProcessing() {
    final service = context.read<CircuitService>();
    service.cancelCurrentJob();
    setState(() {
      _isProcessing = false;
    });
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Theme.of(context).colorScheme.error,
      ),
    );
  }
}
