import 'package:flutter/material.dart';
import 'capture_screen.dart';

/// Home screen with app introduction and capture button.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('CircuitVision'),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // App icon
              Icon(
                Icons.memory,
                size: 80,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 24),

              // Title
              Text(
                'CircuitVision',
                style: theme.textTheme.headlineLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),

              // Subtitle
              Text(
                'Analyze circuit schematics with AI',
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.7),
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),

              // Features list
              _FeatureItem(
                icon: Icons.camera_alt,
                title: 'Capture',
                description: 'Take a photo of your circuit schematic',
              ),
              const SizedBox(height: 16),
              _FeatureItem(
                icon: Icons.code,
                title: 'Generate',
                description: 'Get SPICE netlist automatically',
              ),
              const SizedBox(height: 16),
              _FeatureItem(
                icon: Icons.show_chart,
                title: 'Simulate',
                description: 'View simulation results as plots',
              ),
              const Spacer(),

              // Start button
              FilledButton.icon(
                onPressed: () => _navigateToCapture(context),
                icon: const Icon(Icons.camera_alt),
                label: const Text('Analyze Circuit'),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
              const SizedBox(height: 16),

              // Gallery button
              OutlinedButton.icon(
                onPressed: () => _navigateToCapture(context, fromGallery: true),
                icon: const Icon(Icons.photo_library),
                label: const Text('Choose from Gallery'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _navigateToCapture(BuildContext context, {bool fromGallery = false}) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => CaptureScreen(openGallery: fromGallery),
      ),
    );
  }
}

class _FeatureItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;

  const _FeatureItem({
    required this.icon,
    required this.title,
    required this.description,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: theme.colorScheme.primaryContainer,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(
            icon,
            color: theme.colorScheme.onPrimaryContainer,
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                description,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.7),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
