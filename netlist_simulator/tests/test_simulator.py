"""
Unit tests for the circuit simulator.
"""

import pytest
import os
import tempfile
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from circuit_simulator.config import SimulationConfig, PlotConfig, SimulationType, PlotType
from circuit_simulator.simulator import CircuitSimulator, CircuitParseError


class TestSimulationConfig:
    """Tests for SimulationConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SimulationConfig()
        assert config.temperature == 25.0
        assert config.simulation_type == SimulationType.AUTO
        assert config.tran_step_time == 10e-6
        assert config.tran_end_time == 10e-3
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = SimulationConfig(
            temperature=50.0,
            tran_step_time=1e-6,
            tran_end_time=5e-3
        )
        assert config.temperature == 50.0
        assert config.tran_step_time == 1e-6
        assert config.tran_end_time == 5e-3
    
    def test_invalid_step_time(self):
        """Test that invalid step time raises error."""
        with pytest.raises(ValueError):
            SimulationConfig(tran_step_time=0)
        with pytest.raises(ValueError):
            SimulationConfig(tran_step_time=-1e-6)
    
    def test_step_time_greater_than_end_time(self):
        """Test that step time >= end time raises error."""
        with pytest.raises(ValueError):
            SimulationConfig(tran_step_time=10e-3, tran_end_time=1e-3)


class TestPlotConfig:
    """Tests for PlotConfig class."""
    
    def test_default_config(self):
        """Test default plot configuration."""
        config = PlotConfig()
        assert config.figure_dpi == 150
        assert config.output_format == 'png'
        assert config.show_plots == False
        assert '0' in config.exclude_nodes
        assert 'gnd' in config.exclude_nodes
    
    def test_should_generate(self):
        """Test plot type checking."""
        config = PlotConfig(plot_types=[PlotType.ALL])
        assert config.should_generate(PlotType.OVERLAY) == True
        assert config.should_generate(PlotType.INDIVIDUAL) == True
        
        config2 = PlotConfig(plot_types=[PlotType.OVERLAY])
        assert config2.should_generate(PlotType.OVERLAY) == True
        assert config2.should_generate(PlotType.INDIVIDUAL) == False
    
    def test_invalid_dpi(self):
        """Test that invalid DPI raises error."""
        with pytest.raises(ValueError):
            PlotConfig(figure_dpi=10)
        with pytest.raises(ValueError):
            PlotConfig(figure_dpi=1000)
    
    def test_invalid_format(self):
        """Test that invalid format raises error."""
        with pytest.raises(ValueError):
            PlotConfig(output_format='bmp')


class TestCircuitSimulator:
    """Tests for CircuitSimulator class."""
    
    @pytest.fixture
    def valid_cir_content(self):
        """Return valid .cir file content."""
        return """Test Circuit
* Simple test circuit
VIN in 0 DC 5
R1 in out 1k
RL out 0 10k
.tran 0.01m 10m
.end
"""
    
    @pytest.fixture
    def invalid_cir_content(self):
        """Return invalid .cir file content."""
        return """Bad Circuit
* Missing components and .end
"""
    
    def test_validate_valid_file(self, valid_cir_content, tmp_path):
        """Test validation of valid .cir file."""
        cir_file = tmp_path / "test.cir"
        cir_file.write_text(valid_cir_content)
        
        simulator = CircuitSimulator()
        is_valid, message = simulator.validate_cir_file(str(cir_file))
        assert is_valid == True
    
    def test_validate_missing_file(self):
        """Test validation of non-existent file."""
        simulator = CircuitSimulator()
        is_valid, message = simulator.validate_cir_file('/nonexistent/file.cir')
        assert is_valid == False
        assert 'not found' in message.lower()
    
    def test_validate_invalid_extension(self, valid_cir_content, tmp_path):
        """Test validation with wrong file extension."""
        bad_file = tmp_path / "test.txt"
        bad_file.write_text(valid_cir_content)
        
        simulator = CircuitSimulator()
        is_valid, message = simulator.validate_cir_file(str(bad_file))
        assert is_valid == False
        assert 'extension' in message.lower()
    
    def test_validate_missing_end(self, tmp_path):
        """Test validation of file missing .end directive."""
        cir_file = tmp_path / "test.cir"
        cir_file.write_text("""Test Circuit
VIN in 0 DC 5
R1 in out 1k
""")
        
        simulator = CircuitSimulator()
        is_valid, message = simulator.validate_cir_file(str(cir_file))
        assert is_valid == False
        assert '.end' in message.lower()
    
    def test_detect_transient_type(self):
        """Test detection of transient simulation type."""
        simulator = CircuitSimulator()
        
        content = ".tran 0.01m 10m\n.end"
        assert simulator.detect_simulation_type(content) == SimulationType.TRANSIENT
    
    def test_detect_ac_type(self):
        """Test detection of AC simulation type."""
        simulator = CircuitSimulator()
        
        content = ".ac dec 100 1 1meg\n.end"
        assert simulator.detect_simulation_type(content) == SimulationType.AC
    
    def test_detect_dc_type(self):
        """Test detection of DC simulation type."""
        simulator = CircuitSimulator()
        
        content = ".dc v1 0 10 0.1\n.end"
        assert simulator.detect_simulation_type(content) == SimulationType.DC
    
    def test_detect_default_type(self):
        """Test default simulation type when none specified."""
        simulator = CircuitSimulator()
        
        content = "* no simulation directive\n.end"
        assert simulator.detect_simulation_type(content) == SimulationType.TRANSIENT


class TestCLI:
    """Tests for CLI functionality."""
    
    def test_parser_creation(self):
        """Test that argument parser is created correctly."""
        from circuit_simulator.cli import create_parser
        parser = create_parser()
        assert parser is not None
    
    def test_build_sim_config(self):
        """Test building simulation config from args."""
        from circuit_simulator.cli import create_parser, build_sim_config
        
        parser = create_parser()
        args = parser.parse_args(['test.cir', '--sim-type', 'ac', '--temp', '30'])
        
        config = build_sim_config(args)
        assert config.simulation_type == SimulationType.AC
        assert config.temperature == 30.0
    
    def test_build_plot_config(self):
        """Test building plot config from args."""
        from circuit_simulator.cli import create_parser, build_plot_config
        
        parser = create_parser()
        args = parser.parse_args(['test.cir', '--format', 'pdf', '--dpi', '300'])
        
        config = build_plot_config(args)
        assert config.output_format == 'pdf'
        assert config.figure_dpi == 300


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
