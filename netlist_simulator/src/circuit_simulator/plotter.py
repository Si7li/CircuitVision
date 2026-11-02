"""
Plotting module for circuit simulation results.

Generates various visualizations of voltage and current data.
"""

import os
from typing import Optional, List
import numpy as np

from .config import PlotConfig, PlotType
from .simulator import SimulationResult


class CircuitPlotter:
    """
    Handles all plotting functionality for circuit simulation results.
    
    Example usage:
        plotter = CircuitPlotter()
        plotter.plot_all(simulation_result, 'output.png')
    """
    
    def __init__(self, config: Optional[PlotConfig] = None):
        """
        Initialize the circuit plotter.
        
        Parameters:
            config: Plot configuration. Uses defaults if not provided.
        """
        self.config = config or PlotConfig()
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check that matplotlib is available."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError(
                "matplotlib is not installed. Install with:\n"
                "  pip install matplotlib"
            )
    
    def _get_plot_nodes(self, result: SimulationResult) -> List[str]:
        """
        Get list of nodes to plot based on configuration.
        
        Parameters:
            result: Simulation result
            
        Returns:
            List of node names to plot
        """
        all_nodes = list(result.nodes.keys())
        
        # Filter out excluded nodes
        nodes = [n for n in all_nodes if n.lower() not in 
                [e.lower() for e in self.config.exclude_nodes]]
        
        # Apply selection if specified
        if self.config.selected_nodes:
            nodes = [n for n in nodes if n in self.config.selected_nodes]
        
        return nodes
    
    def _get_colors(self, n: int, colormap: str):
        """Get array of colors from a colormap."""
        import matplotlib.pyplot as plt
        cmap = plt.cm.get_cmap(colormap)
        return cmap(np.linspace(0, 1, max(n, 1)))
    
    def _downsample_data(self, x_data, y_data, max_points: int = 2000):
        """
        Downsample data for cleaner plotting while preserving signal shape.
        
        Uses LTTB (Largest-Triangle-Three-Buckets) inspired approach that
        keeps local minima and maxima to preserve signal edges.
        
        Parameters:
            x_data: X-axis data array
            y_data: Y-axis data array
            max_points: Maximum number of points to keep
            
        Returns:
            Tuple of (downsampled_x, downsampled_y)
        """
        n_points = len(x_data)
        
        if n_points <= max_points:
            return x_data, y_data
        
        # Use min-max decimation to preserve peaks and valleys
        # This is important for digital signals with fast edges
        bucket_size = n_points // (max_points // 2)
        
        indices = [0]  # Always keep first point
        
        for i in range(0, n_points - bucket_size, bucket_size):
            bucket = y_data[i:i + bucket_size]
            min_idx = i + np.argmin(bucket)
            max_idx = i + np.argmax(bucket)
            
            # Add min and max in chronological order
            if min_idx < max_idx:
                indices.extend([min_idx, max_idx])
            else:
                indices.extend([max_idx, min_idx])
        
        indices.append(n_points - 1)  # Always keep last point
        
        # Remove duplicates and sort
        indices = sorted(set(indices))
        
        return np.array(x_data)[indices], np.array(y_data)[indices]
    
    def plot_overlay(self, result: SimulationResult, output_path: str,
                     nodes: Optional[List[str]] = None) -> str:
        """
        Create overlay plot with all voltages on one figure.
        
        Parameters:
            result: Simulation result
            output_path: Path to save the plot
            nodes: Optional list of specific nodes to plot
            
        Returns:
            Path to the saved plot
        """
        import matplotlib.pyplot as plt
        
        plot_nodes = nodes or self._get_plot_nodes(result)
        
        if not plot_nodes:
            print("⚠ No nodes to plot")
            return ""
        
        fig, ax = plt.subplots(figsize=self.config.overlay_figsize)
        colors = self._get_colors(len(plot_nodes), self.config.colormap)
        
        for i, node in enumerate(plot_nodes):
            y_data = np.array(result.nodes[node])
            # Downsample for cleaner plots
            x_plot, y_plot = self._downsample_data(result.x_data, y_data)
            ax.plot(x_plot, y_plot, 
                   label=f'V({node})',
                   linewidth=self.config.line_width,
                   color=colors[i],
                   alpha=0.8)
        
        ax.set_xlabel(result.x_label, fontsize=self.config.font_size_label)
        ax.set_ylabel('Voltage (V)', fontsize=self.config.font_size_label)
        ax.set_title(f'All Node Voltages - {result.circuit_title}',
                    fontsize=self.config.font_size_title, fontweight='bold')
        ax.grid(True, alpha=self.config.grid_alpha)
        ax.legend(loc='best', fontsize=self.config.font_size_legend,
                 ncol=max(1, len(plot_nodes) // 8))
        
        plt.tight_layout()
        
        # Save with appropriate extension
        save_path = self._ensure_extension(output_path, '_overlay')
        plt.savefig(save_path, dpi=self.config.figure_dpi, bbox_inches='tight')
        
        if self.config.show_plots:
            plt.show()
        plt.close(fig)
        
        print(f"✓ Overlay plot saved: {save_path}")
        return save_path
    
    def plot_individual(self, result: SimulationResult, output_path: str,
                        nodes: Optional[List[str]] = None,
                        max_plots: int = 12) -> str:
        """
        Create individual subplots for each voltage node.
        
        Parameters:
            result: Simulation result
            output_path: Path to save the plot
            nodes: Optional list of specific nodes to plot
            max_plots: Maximum number of subplots to create
            
        Returns:
            Path to the saved plot
        """
        import matplotlib.pyplot as plt
        
        plot_nodes = nodes or self._get_plot_nodes(result)
        
        if not plot_nodes:
            print("⚠ No nodes to plot")
            return ""
        
        # Limit number of plots
        plot_nodes = plot_nodes[:max_plots]
        n_plots = len(plot_nodes)
        
        if n_plots == 1:
            # Single plot, just use overlay
            return self.plot_overlay(result, output_path, plot_nodes)
        
        # Determine grid size
        if n_plots <= 4:
            n_cols = 2
            n_rows = (n_plots + 1) // 2
        elif n_plots <= 9:
            n_cols = 3
            n_rows = (n_plots + 2) // 3
        else:
            n_cols = 4
            n_rows = 3
        
        figsize = (self.config.individual_figsize_per_plot[0] * n_cols,
                   self.config.individual_figsize_per_plot[1] * n_rows)
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        axes = np.array(axes).flatten() if n_plots > 1 else [axes]
        
        colors = self._get_colors(len(plot_nodes), self.config.colormap)
        
        for i, node in enumerate(plot_nodes):
            ax = axes[i]
            y_data = np.array(result.nodes[node])
            # Downsample for cleaner plots
            x_plot, y_plot = self._downsample_data(result.x_data, y_data)
            ax.plot(x_plot, y_plot,
                   linewidth=self.config.line_width + 0.5,
                   color=colors[i])
            ax.set_xlabel(result.x_label, fontsize=self.config.font_size_label - 2)
            ax.set_ylabel('Voltage (V)', fontsize=self.config.font_size_label - 2)
            ax.set_title(f'V({node})', fontsize=self.config.font_size_title - 3,
                        fontweight='bold')
            ax.grid(True, alpha=self.config.grid_alpha)
        
        # Hide unused subplots
        for i in range(len(plot_nodes), len(axes)):
            axes[i].axis('off')
        
        plt.suptitle(f'Individual Node Voltages - {result.circuit_title}',
                    fontsize=self.config.font_size_title, fontweight='bold', y=1.00)
        plt.tight_layout()
        
        save_path = self._ensure_extension(output_path, '_individual')
        plt.savefig(save_path, dpi=self.config.figure_dpi, bbox_inches='tight')
        
        if self.config.show_plots:
            plt.show()
        plt.close(fig)
        
        print(f"✓ Individual plots saved: {save_path}")
        return save_path
    
    def plot_currents(self, result: SimulationResult, output_path: str,
                      branches: Optional[List[str]] = None) -> str:
        """
        Create plot of branch currents.
        
        Parameters:
            result: Simulation result
            output_path: Path to save the plot
            branches: Optional list of specific branches to plot
            
        Returns:
            Path to the saved plot (empty string if no currents)
        """
        import matplotlib.pyplot as plt
        
        plot_branches = branches or list(result.branches.keys())
        
        if not plot_branches:
            print("  ℹ No branch currents available")
            return ""
        
        fig, ax = plt.subplots(figsize=self.config.current_figsize)
        colors = self._get_colors(len(plot_branches), self.config.current_colormap)
        
        for i, branch in enumerate(plot_branches):
            i_data = np.array(result.branches[branch]) * 1e3  # Convert to mA
            # Downsample for cleaner plots
            x_plot, y_plot = self._downsample_data(result.x_data, i_data)
            ax.plot(x_plot, y_plot,
                   label=f'I({branch})',
                   linewidth=self.config.line_width + 0.5,
                   color=colors[i])
        
        ax.set_xlabel(result.x_label, fontsize=self.config.font_size_label)
        ax.set_ylabel('Current (mA)', fontsize=self.config.font_size_label)
        ax.set_title(f'Branch Currents - {result.circuit_title}',
                    fontsize=self.config.font_size_title, fontweight='bold')
        ax.grid(True, alpha=self.config.grid_alpha)
        ax.legend(loc='best', fontsize=self.config.font_size_legend + 1)
        
        plt.tight_layout()
        
        save_path = self._ensure_extension(output_path, '_currents')
        plt.savefig(save_path, dpi=self.config.figure_dpi, bbox_inches='tight')
        
        if self.config.show_plots:
            plt.show()
        plt.close(fig)
        
        print(f"✓ Current plots saved: {save_path}")
        return save_path
    
    def plot_components_overlay(self, result: SimulationResult, output_path: str,
                                components: Optional[List[str]] = None) -> str:
        """
        Create overlay plot with voltage differences across all components.
        
        Parameters:
            result: Simulation result
            output_path: Path to save the plot
            components: Optional list of specific components to plot
            
        Returns:
            Path to the saved plot (empty string if no components)
        """
        import matplotlib.pyplot as plt
        
        if not result.component_voltages:
            print("  ℹ No component voltage differences available")
            return ""
        
        plot_components = components or list(result.component_voltages.keys())
        plot_components = [c for c in plot_components if c in result.component_voltages]
        
        if not plot_components:
            print("  ℹ No matching components to plot")
            return ""
        
        fig, ax = plt.subplots(figsize=self.config.overlay_figsize)
        colors = self._get_colors(len(plot_components), 'tab10')
        
        for i, comp_name in enumerate(plot_components):
            data = result.component_voltages[comp_name]
            y_data = np.array(data.voltage)
            # Downsample for cleaner plots
            x_plot, y_plot = self._downsample_data(result.x_data, y_data)
            ax.plot(x_plot, y_plot,
                   label=f'V({comp_name})',
                   linewidth=self.config.line_width,
                   color=colors[i],
                   alpha=0.8)
        
        ax.set_xlabel(result.x_label, fontsize=self.config.font_size_label)
        ax.set_ylabel('Voltage (V)', fontsize=self.config.font_size_label)
        ax.set_title(f'Voltage Across Components - {result.circuit_title}',
                    fontsize=self.config.font_size_title, fontweight='bold')
        ax.grid(True, alpha=self.config.grid_alpha)
        ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5, alpha=0.3)
        ax.legend(loc='best', fontsize=self.config.font_size_legend)
        
        plt.tight_layout()
        
        save_path = self._ensure_extension(output_path, '_components_overlay')
        plt.savefig(save_path, dpi=self.config.figure_dpi, bbox_inches='tight')
        
        if self.config.show_plots:
            plt.show()
        plt.close(fig)
        
        print(f"✓ Component voltage overlay saved: {save_path}")
        return save_path
    
    def plot_components_individual(self, result: SimulationResult, output_path: str,
                                   components: Optional[List[str]] = None,
                                   max_plots: int = 12) -> str:
        """
        Create individual subplots for voltage across each component.
        
        Parameters:
            result: Simulation result
            output_path: Path to save the plot
            components: Optional list of specific components to plot
            max_plots: Maximum number of subplots to create
            
        Returns:
            Path to the saved plot (empty string if no components)
        """
        import matplotlib.pyplot as plt
        
        if not result.component_voltages:
            return ""
        
        plot_components = components or list(result.component_voltages.keys())
        plot_components = [c for c in plot_components if c in result.component_voltages]
        plot_components = plot_components[:max_plots]
        
        if not plot_components:
            return ""
        
        n_components = len(plot_components)
        
        if n_components == 1:
            return self.plot_components_overlay(result, output_path, plot_components)
        
        # Determine grid size
        n_cols = min(3, n_components)
        n_rows = (n_components + n_cols - 1) // n_cols
        
        figsize = (5 * n_cols, 3 * n_rows)
        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        axes = np.array(axes).flatten() if n_components > 1 else [axes]
        
        colors = self._get_colors(len(plot_components), 'tab10')
        
        for i, comp_name in enumerate(plot_components):
            ax = axes[i]
            data = result.component_voltages[comp_name]
            y_data = np.array(data.voltage)
            # Downsample for cleaner plots
            x_plot, y_plot = self._downsample_data(result.x_data, y_data)
            ax.plot(x_plot, y_plot,
                   linewidth=self.config.line_width + 0.5,
                   color=colors[i])
            ax.set_xlabel(result.x_label, fontsize=self.config.font_size_label - 2)
            ax.set_ylabel('Voltage (V)', fontsize=self.config.font_size_label - 2)
            ax.set_title(f'V({comp_name}) - {data.nodes}',
                        fontsize=self.config.font_size_title - 4, fontweight='bold')
            ax.grid(True, alpha=self.config.grid_alpha)
            ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5, alpha=0.3)
        
        # Hide unused subplots
        for i in range(n_components, len(axes)):
            axes[i].axis('off')
        
        plt.suptitle(f'Individual Component Voltages - {result.circuit_title}',
                    fontsize=self.config.font_size_title, fontweight='bold', y=1.00)
        plt.tight_layout()
        
        save_path = self._ensure_extension(output_path, '_components_individual')
        plt.savefig(save_path, dpi=self.config.figure_dpi, bbox_inches='tight')
        
        if self.config.show_plots:
            plt.show()
        plt.close(fig)
        
        print(f"✓ Component voltage individual plots saved: {save_path}")
        return save_path
    
    def plot_all(self, result: SimulationResult, output_path: str,
                 nodes: Optional[List[str]] = None) -> List[str]:
        """
        Generate all configured plot types.
        
        Parameters:
            result: Simulation result
            output_path: Base path for output files
            nodes: Optional list of specific nodes to plot
            
        Returns:
            List of paths to saved plots
        """
        saved_plots = []
        plot_nodes = nodes or self._get_plot_nodes(result)
        
        if not plot_nodes:
            print("\n⚠ No nodes to plot (only ground found)")
            return saved_plots
        
        print(f"\nPlotting {len(plot_nodes)} voltage nodes...")
        
        # Generate overlay plot
        if self.config.should_generate(PlotType.OVERLAY):
            path = self.plot_overlay(result, output_path, plot_nodes)
            if path:
                saved_plots.append(path)
        
        # Generate individual plots
        if self.config.should_generate(PlotType.INDIVIDUAL) and len(plot_nodes) > 1:
            path = self.plot_individual(result, output_path, plot_nodes)
            if path:
                saved_plots.append(path)
        
        # Generate current plots
        if self.config.should_generate(PlotType.CURRENTS) and result.branches:
            path = self.plot_currents(result, output_path)
            if path:
                saved_plots.append(path)
        
        # Generate component voltage plots
        if self.config.should_generate(PlotType.COMPONENTS) and result.component_voltages:
            print(f"\nPlotting voltage across {len(result.component_voltages)} components...")
            path = self.plot_components_overlay(result, output_path)
            if path:
                saved_plots.append(path)
            if len(result.component_voltages) > 1:
                path = self.plot_components_individual(result, output_path)
                if path:
                    saved_plots.append(path)
        
        print(f"\n✓ All plots generated successfully!")
        print("=" * 70)
        
        return saved_plots
    
    def _ensure_extension(self, base_path: str, suffix: str) -> str:
        """
        Ensure output path has correct suffix and extension.
        
        Parameters:
            base_path: Base output path
            suffix: Suffix to add (e.g., '_overlay')
            
        Returns:
            Complete output path
        """
        # Remove existing extension
        base, ext = os.path.splitext(base_path)
        
        # Use configured format
        ext = f'.{self.config.output_format}'
        
        return f"{base}{suffix}{ext}"
    
    def create_summary_figure(self, result: SimulationResult, output_path: str,
                              max_nodes: int = 6) -> str:
        """
        Create a single summary figure with key information.
        
        Parameters:
            result: Simulation result
            output_path: Path to save the figure
            max_nodes: Maximum nodes to show
            
        Returns:
            Path to saved figure
        """
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
        
        plot_nodes = self._get_plot_nodes(result)[:max_nodes]
        has_currents = bool(result.branches)
        
        # Create figure with custom layout
        fig = plt.figure(figsize=(14, 8))
        
        if has_currents:
            gs = GridSpec(2, 2, figure=fig, height_ratios=[1.2, 1])
            ax_overlay = fig.add_subplot(gs[0, :])
            ax_individual = fig.add_subplot(gs[1, 0])
            ax_currents = fig.add_subplot(gs[1, 1])
        else:
            gs = GridSpec(2, 1, figure=fig, height_ratios=[1.2, 1])
            ax_overlay = fig.add_subplot(gs[0])
            ax_individual = fig.add_subplot(gs[1])
            ax_currents = None
        
        colors = self._get_colors(len(plot_nodes), self.config.colormap)
        
        # Overlay plot
        for i, node in enumerate(plot_nodes):
            y_data = np.array(result.nodes[node])
            # Downsample for cleaner plots
            x_plot, y_plot = self._downsample_data(result.x_data, y_data)
            ax_overlay.plot(x_plot, y_plot, label=f'V({node})',
                           linewidth=self.config.line_width, color=colors[i], alpha=0.8)
        
        ax_overlay.set_xlabel(result.x_label)
        ax_overlay.set_ylabel('Voltage (V)')
        ax_overlay.set_title(f'Circuit Analysis - {result.circuit_title}',
                            fontsize=14, fontweight='bold')
        ax_overlay.grid(True, alpha=0.3)
        ax_overlay.legend(loc='best', fontsize=8)
        
        # First node detail
        if plot_nodes:
            first_node = plot_nodes[0]
            y_data = np.array(result.nodes[first_node])
            # Downsample for cleaner plots
            x_plot, y_plot = self._downsample_data(result.x_data, y_data)
            ax_individual.plot(x_plot, y_plot, linewidth=2, color=colors[0])
            ax_individual.set_xlabel(result.x_label)
            ax_individual.set_ylabel('Voltage (V)')
            ax_individual.set_title(f'V({first_node}) Detail', fontweight='bold')
            ax_individual.grid(True, alpha=0.3)
        
        # Currents
        if ax_currents and result.branches:
            branch_colors = self._get_colors(len(result.branches), self.config.current_colormap)
            for i, (branch, data) in enumerate(result.branches.items()):
                i_data = np.array(data) * 1e3
                # Downsample for cleaner plots
                x_plot, y_plot = self._downsample_data(result.x_data, i_data)
                ax_currents.plot(x_plot, y_plot, label=f'I({branch})',
                                linewidth=2, color=branch_colors[i])
            ax_currents.set_xlabel(result.x_label)
            ax_currents.set_ylabel('Current (mA)')
            ax_currents.set_title('Branch Currents', fontweight='bold')
            ax_currents.grid(True, alpha=0.3)
            ax_currents.legend(loc='best', fontsize=8)
        
        plt.tight_layout()
        
        save_path = self._ensure_extension(output_path, '_summary')
        plt.savefig(save_path, dpi=self.config.figure_dpi, bbox_inches='tight')
        
        if self.config.show_plots:
            plt.show()
        plt.close(fig)
        
        print(f"✓ Summary figure saved: {save_path}")
        return save_path
