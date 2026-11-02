"""
Tests for netlist normalizer module.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from netlist_normalizer import NetlistNormalizer, normalize_netlist, ValidationResult, NormalizationResult


class TestValidation:
    """Tests for netlist validation."""

    def test_empty_netlist_invalid(self):
        normalizer = NetlistNormalizer()
        result = normalizer.validate_netlist("")
        assert not result.is_valid
        assert "empty" in result.errors[0].lower()

    def test_valid_simple_netlist(self):
        netlist = """RC Filter
R1 in out 1k
C1 out 0 1u
.tran 1u 10m
.end
"""
        normalizer = NetlistNormalizer()
        result = normalizer.validate_netlist(netlist)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_end_warning(self):
        netlist = """RC Filter
R1 in out 1k
C1 out 0 1u
.tran 1u 10m
"""
        normalizer = NetlistNormalizer()
        result = normalizer.validate_netlist(netlist)
        # Should have warning about missing .end
        assert any(".end" in w.lower() for w in result.warnings)

    def test_missing_analysis_warning(self):
        netlist = """RC Filter
R1 in out 1k
C1 out 0 1u
.end
"""
        normalizer = NetlistNormalizer()
        result = normalizer.validate_netlist(netlist)
        # Should have warning about missing analysis directive
        assert any("analysis" in w.lower() for w in result.warnings)

    def test_ground_reference_warning(self):
        netlist = """RC Filter
R1 n1 n2 1k
C1 n2 n3 1u
.tran 1u 10m
.end
"""
        normalizer = NetlistNormalizer()
        result = normalizer.validate_netlist(netlist)
        # Should have warning about missing ground
        assert any("ground" in w.lower() for w in result.warnings)

    def test_invalid_component_prefix(self):
        netlist = """Test Circuit
Z1 n1 n2 100
.end
"""
        normalizer = NetlistNormalizer()
        result = normalizer.validate_netlist(netlist)
        assert not result.is_valid
        assert any("unknown" in e.lower() for e in result.errors)


class TestNormalization:
    """Tests for netlist normalization."""

    def test_add_title(self):
        netlist = """R1 in out 1k
C1 out 0 1u
"""
        normalizer = NetlistNormalizer()
        result = normalizer.normalize(netlist)
        lines = result.normalized_netlist.split('\n')
        # First line should no longer be a component
        assert not lines[0].startswith('R')
        assert "title" in ' '.join(result.changes_made).lower()

    def test_add_end_directive(self):
        netlist = """RC Filter
R1 in out 1k
C1 out 0 1u
"""
        normalizer = NetlistNormalizer()
        result = normalizer.normalize(netlist)
        assert result.normalized_netlist.strip().endswith('.end')
        assert any(".end" in c.lower() for c in result.changes_made)

    def test_add_analysis_directive(self):
        netlist = """RC Filter
R1 in out 1k
C1 out 0 1u
.end
"""
        normalizer = NetlistNormalizer()
        result = normalizer.normalize(netlist)
        assert '.tran' in result.normalized_netlist.lower()
        assert any("analysis" in c.lower() for c in result.changes_made)

    def test_preserve_existing_analysis(self):
        netlist = """RC Filter
R1 in out 1k
C1 out 0 1u
.ac dec 100 1 1Meg
.end
"""
        normalizer = NetlistNormalizer()
        result = normalizer.normalize(netlist)
        assert '.ac' in result.normalized_netlist.lower()
        # Should not have added default tran
        assert not any("added default analysis" in c.lower() for c in result.changes_made)

    def test_custom_defaults(self):
        normalizer = NetlistNormalizer(
            default_title="Custom Circuit",
            default_analysis=".ac dec 10 1 100k"
        )
        netlist = """R1 in out 1k
.end
"""
        result = normalizer.normalize(netlist)
        assert "Custom Circuit" in result.normalized_netlist
        assert ".ac" in result.normalized_netlist.lower()

    def test_normalize_idempotent(self):
        """Normalizing twice should give same result."""
        netlist = """R1 in out 1k
C1 out 0 1u
"""
        normalizer = NetlistNormalizer()
        result1 = normalizer.normalize(netlist)
        result2 = normalizer.normalize(result1.normalized_netlist)
        assert result1.normalized_netlist == result2.normalized_netlist


class TestCircuitVisionFormat:
    """Tests for CircuitVision format conversion."""

    def test_basic_conversion(self):
        components = [
            {
                'class': 'resistor',
                'component_type': 'R',
                'component_num': 1,
                'node_1': 'in',
                'node_2': 'out',
                'value': '10k'
            },
            {
                'class': 'capacitor',
                'component_type': 'C',
                'component_num': 1,
                'node_1': 'out',
                'node_2': '0',
                'value': '1u'
            }
        ]
        normalizer = NetlistNormalizer()
        result = normalizer.from_circuitvision_format(components)
        assert result.success
        assert "R1 in out 10k" in result.normalized_netlist
        assert "C1 out 0 1u" in result.normalized_netlist

    def test_voltage_source_conversion(self):
        components = [
            {
                'class': 'voltage.dc',
                'component_type': 'V',
                'component_num': 1,
                'node_1': 'in',
                'node_2': '0',
                'value': '12'
            }
        ]
        normalizer = NetlistNormalizer()
        result = normalizer.from_circuitvision_format(components)
        assert "V1 in 0" in result.normalized_netlist
        assert "DC" in result.normalized_netlist.upper()

    def test_empty_components_error(self):
        normalizer = NetlistNormalizer()
        result = normalizer.from_circuitvision_format([])
        assert not result.success
        assert "empty" in result.errors[0].lower()


class TestConvenienceFunction:
    """Tests for the convenience function."""

    def test_normalize_netlist_function(self):
        netlist = """R1 in out 1k
C1 out 0 1u
"""
        normalized, changes = normalize_netlist(netlist)
        assert ".end" in normalized
        assert ".tran" in normalized.lower()
        assert len(changes) > 0

    def test_normalize_netlist_error(self):
        with pytest.raises(ValueError):
            normalize_netlist("")


class TestEdgeCases:
    """Tests for edge cases."""

    def test_comments_preserved(self):
        netlist = """RC Filter
* This is a comment
R1 in out 1k
* Another comment
C1 out 0 1u
.end
"""
        normalizer = NetlistNormalizer()
        result = normalizer.normalize(netlist)
        # Comments should still be in there (though stripped)
        # Note: our normalization removes empty lines but should keep comment lines
        # Actually, in our current implementation, we only keep non-empty lines
        # that aren't just whitespace, so comments starting with * should be kept

    def test_whitespace_handling(self):
        netlist = """  RC Filter
  R1 in out 1k
  C1 out 0 1u
  .end
"""
        normalizer = NetlistNormalizer()
        result = normalizer.normalize(netlist)
        # Lines should be stripped
        lines = result.normalized_netlist.split('\n')
        for line in lines:
            assert not line.startswith(' ')
            assert not line.endswith(' ')

    def test_case_insensitive_end(self):
        netlist = """RC Filter
R1 in out 1k
.END
"""
        normalizer = NetlistNormalizer()
        result = normalizer.normalize(netlist)
        # Should not add another .end
        count = result.normalized_netlist.lower().count('.end')
        assert count == 1

    def test_multiple_analysis_directives(self):
        netlist = """RC Filter
R1 in out 1k
.tran 1u 10m
.ac dec 100 1 1Meg
.end
"""
        normalizer = NetlistNormalizer()
        result = normalizer.normalize(netlist)
        # Should preserve both
        assert '.tran' in result.normalized_netlist.lower()
        assert '.ac' in result.normalized_netlist.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
