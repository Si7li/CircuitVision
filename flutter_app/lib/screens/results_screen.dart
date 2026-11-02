import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/circuit_result.dart';

/// Screen displaying analysis results: netlist and simulation plots.
class ResultsScreen extends StatefulWidget {
  final CircuitResult result;

  const ResultsScreen({super.key, required this.result});

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: widget.result.hasPlots ? 2 : 1,
      vsync: this,
    );
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final result = widget.result;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Analysis Results'),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            const Tab(text: 'Netlist', icon: Icon(Icons.code)),
            if (result.hasPlots)
              const Tab(text: 'Plots', icon: Icon(Icons.show_chart)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () => _showInfo(context),
            tooltip: 'Analysis info',
          ),
        ],
      ),
      body: Column(
        children: [
          // Status banner
          if (!result.isSuccess) _buildStatusBanner(theme),

          // Warnings
          if (result.warnings.isNotEmpty) _buildWarnings(theme),

          // Tab content
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _NetlistTab(netlist: result.netlist),
                if (result.hasPlots) _PlotsTab(plots: result.plots),
              ],
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
        icon: const Icon(Icons.camera_alt),
        label: const Text('New Analysis'),
      ),
    );
  }

  Widget _buildStatusBanner(ThemeData theme) {
    final result = widget.result;
    Color backgroundColor;
    IconData icon;
    String message;

    if (result.isError) {
      backgroundColor = theme.colorScheme.errorContainer;
      icon = Icons.error;
      message = result.errorMessage ?? 'Analysis failed';
    } else if (result.isPartial) {
      backgroundColor = theme.colorScheme.tertiaryContainer;
      icon = Icons.warning;
      message = 'Partial results - some steps may have failed';
    } else {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      color: backgroundColor,
      child: Row(
        children: [
          Icon(icon, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: theme.textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWarnings(ThemeData theme) {
    return ExpansionTile(
      leading: Icon(
        Icons.warning_amber,
        color: theme.colorScheme.tertiary,
      ),
      title: Text('${widget.result.warnings.length} warning(s)'),
      children: widget.result.warnings
          .map((w) => ListTile(
                dense: true,
                leading: const Icon(Icons.arrow_right),
                title: Text(w, style: theme.textTheme.bodySmall),
              ))
          .toList(),
    );
  }

  void _showInfo(BuildContext context) {
    final result = widget.result;
    final timing = result.timing;

    showModalBottomSheet(
      context: context,
      builder: (context) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Analysis Information',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            _InfoRow(label: 'Status', value: result.status),
            _InfoRow(
              label: 'Total Time',
              value: '${result.totalTime.toStringAsFixed(2)}s',
            ),
            if (timing.isNotEmpty) ...[
              const Divider(),
              Text(
                'Timing Breakdown',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              ...timing.entries.map((e) => _InfoRow(
                    label: e.key,
                    value: '${e.value.toStringAsFixed(3)}s',
                  )),
            ],
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
          ),
        ],
      ),
    );
  }
}

/// Tab showing the SPICE netlist.
class _NetlistTab extends StatelessWidget {
  final String netlist;

  const _NetlistTab({required this.netlist});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (netlist.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.code_off,
              size: 64,
              color: theme.colorScheme.onSurface.withOpacity(0.3),
            ),
            const SizedBox(height: 16),
            Text(
              'No netlist generated',
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.6),
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        // Copy button
        Padding(
          padding: const EdgeInsets.all(8.0),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton.icon(
                onPressed: () => _copyNetlist(context),
                icon: const Icon(Icons.copy),
                label: const Text('Copy'),
              ),
              TextButton.icon(
                onPressed: () => _shareNetlist(context),
                icon: const Icon(Icons.share),
                label: const Text('Share'),
              ),
            ],
          ),
        ),

        // Netlist content
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceVariant.withOpacity(0.5),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: theme.colorScheme.outline.withOpacity(0.3),
                ),
              ),
              child: SelectableText(
                netlist,
                style: TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 14,
                  color: theme.colorScheme.onSurface,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  void _copyNetlist(BuildContext context) {
    Clipboard.setData(ClipboardData(text: netlist));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Netlist copied to clipboard')),
    );
  }

  void _shareNetlist(BuildContext context) {
    // In a real app, use share_plus package
    _copyNetlist(context);
  }
}

/// Tab showing simulation plots.
class _PlotsTab extends StatefulWidget {
  final Map<String, String> plots;

  const _PlotsTab({required this.plots});

  @override
  State<_PlotsTab> createState() => _PlotsTabState();
}

class _PlotsTabState extends State<_PlotsTab> {
  String? _selectedPlot;

  @override
  void initState() {
    super.initState();
    if (widget.plots.isNotEmpty) {
      _selectedPlot = widget.plots.keys.first;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (widget.plots.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.show_chart,
              size: 64,
              color: theme.colorScheme.onSurface.withOpacity(0.3),
            ),
            const SizedBox(height: 16),
            Text(
              'No plots available',
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.6),
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        // Plot selector
        if (widget.plots.length > 1) _buildPlotSelector(theme),

        // Plot image
        Expanded(
          child: _buildPlotImage(),
        ),
      ],
    );
  }

  Widget _buildPlotSelector(ThemeData theme) {
    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: widget.plots.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final name = widget.plots.keys.elementAt(index);
          final isSelected = _selectedPlot == name;

          return FilterChip(
            label: Text(_formatPlotName(name)),
            selected: isSelected,
            onSelected: (selected) {
              if (selected) {
                setState(() {
                  _selectedPlot = name;
                });
              }
            },
          );
        },
      ),
    );
  }

  Widget _buildPlotImage() {
    if (_selectedPlot == null) {
      return const SizedBox.shrink();
    }

    final base64Data = widget.plots[_selectedPlot!];
    if (base64Data == null) {
      return const Center(child: Text('Plot data not available'));
    }

    try {
      final bytes = _decodeBase64(base64Data);

      return InteractiveViewer(
        minScale: 0.5,
        maxScale: 4.0,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Image.memory(
            bytes,
            fit: BoxFit.contain,
          ),
        ),
      );
    } catch (e) {
      return Center(
        child: Text('Failed to decode plot: $e'),
      );
    }
  }

  Uint8List _decodeBase64(String data) {
    // Handle data URI format
    if (data.contains(',')) {
      data = data.split(',').last;
    }
    return Uint8List.fromList(
      List<int>.from(
        Uri.parse('data:image/png;base64,$data').data!.contentAsBytes(),
      ),
    );
  }

  String _formatPlotName(String name) {
    // Remove file extension and format nicely
    return name
        .replaceAll('.png', '')
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '')
        .join(' ');
  }
}
