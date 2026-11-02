"""
Netlist Normalizer Module

Converts raw netlists from CircuitVision into valid SPICE .cir format.
Ensures:
- Title line present
- Analysis directive present (defaults to .tran if absent)
- .end directive present
- Valid component syntax
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of netlist validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class NormalizationResult:
    """Result of netlist normalization."""
    success: bool
    normalized_netlist: str
    original_netlist: str
    changes_made: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class NetlistNormalizer:
    """
    Normalizes raw netlists from CircuitVision into valid SPICE format.

    The netlist from CircuitVision may be:
    - A list of dicts: [{'class': 'resistor', 'component_type': 'R', ...}, ...]
    - A string already in SPICE format

    This module ensures the output is a valid .cir file that ngspice can simulate.
    """

    # Default analysis directive if none present
    DEFAULT_TRAN_DIRECTIVE = ".tran 10u 10m"
    DEFAULT_TITLE = "CircuitVision Generated Circuit"

    # Valid component prefixes in SPICE
    VALID_PREFIXES = {'R', 'C', 'L', 'V', 'I', 'D', 'Q', 'M', 'X', 'E', 'F', 'G', 'H', 'K', 'S', 'W', 'T', 'O'}

    # Analysis directive patterns
    ANALYSIS_PATTERNS = [
        r'\.tran\s+',
        r'\.ac\s+',
        r'\.dc\s+',
        r'\.op\b',
        r'\.tf\s+',
        r'\.noise\s+',
        r'\.sens\s+',
        r'\.four\s+',
    ]

    def __init__(self, default_title: Optional[str] = None, default_analysis: Optional[str] = None):
        """
        Initialize the normalizer.

        Args:
            default_title: Default title to use if none provided
            default_analysis: Default analysis directive to use if none present
        """
        self.default_title = default_title or self.DEFAULT_TITLE
        self.default_analysis = default_analysis or self.DEFAULT_TRAN_DIRECTIVE

    def validate_netlist(self, netlist: str) -> ValidationResult:
        """
        Validate a netlist string.

        Args:
            netlist: SPICE netlist string

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        if not netlist or not netlist.strip():
            errors.append("Netlist is empty")
            return ValidationResult(is_valid=False, errors=errors)

        lines = netlist.strip().split('\n')

        # Check for minimum lines (title + at least one component + .end)
        non_empty_lines = [l for l in lines if l.strip() and not l.strip().startswith('*')]
        if len(non_empty_lines) < 2:
            errors.append("Netlist too short: needs at least title and one component")

        # Check if first line looks like a component (should be title)
        first_line = lines[0].strip()
        if first_line and first_line[0].upper() in self.VALID_PREFIXES and len(first_line) > 1:
            if first_line[1].isdigit() or first_line[1] == ' ':
                warnings.append(f"First line looks like a component, not a title: '{first_line}'")

        # Check for .end directive
        has_end = any(line.strip().lower() == '.end' for line in lines)
        if not has_end:
            warnings.append("Missing .end directive")

        # Check for analysis directive
        has_analysis = self._has_analysis_directive(netlist)
        if not has_analysis:
            warnings.append("No analysis directive found (.tran, .ac, .dc, etc.)")

        # Check for ground reference
        has_ground = self._has_ground_reference(netlist)
        if not has_ground:
            warnings.append("No ground reference (node 0 or gnd) found - simulation may fail")

        # Check for voltage source (needed for most simulations)
        has_voltage_source = bool(re.search(r'^V\w*\s+', netlist, re.MULTILINE | re.IGNORECASE))
        if not has_voltage_source:
            warnings.append("No voltage source found - circuit may not simulate")

        # Validate component syntax
        for i, line in enumerate(lines[1:], start=2):  # Skip title line
            line = line.strip()
            if not line or line.startswith('*') or line.startswith('.'):
                continue

            comp_error = self._validate_component_line(line, i)
            if comp_error:
                errors.append(comp_error)

        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

    def _validate_component_line(self, line: str, line_num: int) -> Optional[str]:
        """Validate a single component line."""
        parts = line.split()
        if not parts:
            return None

        name = parts[0]
        prefix = name[0].upper()

        if prefix not in self.VALID_PREFIXES:
            return f"Line {line_num}: Unknown component prefix '{prefix}' in '{name}'"

        # Check minimum parts for basic components
        min_parts = {
            'R': 4, 'C': 4, 'L': 4,  # name node1 node2 value
            'V': 3, 'I': 3,  # name node1 node2 [value_spec]
            'D': 3, 'Q': 4, 'M': 4,  # varying requirements
        }

        required = min_parts.get(prefix, 3)
        if len(parts) < required:
            return f"Line {line_num}: '{name}' needs at least {required} parts, got {len(parts)}"

        return None

    def _has_analysis_directive(self, netlist: str) -> bool:
        """Check if netlist contains an analysis directive."""
        for pattern in self.ANALYSIS_PATTERNS:
            if re.search(pattern, netlist, re.IGNORECASE | re.MULTILINE):
                return True
        return False

    def _has_ground_reference(self, netlist: str) -> bool:
        """Check if netlist has a ground reference (node 0 or gnd)."""
        # Look for node 0 or gnd in component lines
        lines = netlist.split('\n')
        for line in lines:
            line = line.strip().lower()
            if not line or line.startswith('*') or line.startswith('.'):
                continue
            parts = line.split()
            if len(parts) >= 3:
                # Check if any node is 0 or gnd
                nodes = parts[1:3]  # Typically nodes are second and third elements
                if '0' in nodes or 'gnd' in nodes:
                    return True
        return False

    def normalize(self, netlist: str, title: Optional[str] = None) -> NormalizationResult:
        """
        Normalize a netlist string into valid SPICE format.

        Ensures:
        - Title line is present
        - Analysis directive is present
        - .end directive is present

        Args:
            netlist: Raw netlist string
            title: Optional title to use

        Returns:
            NormalizationResult with normalized netlist
        """
        if not netlist or not netlist.strip():
            return NormalizationResult(
                success=False,
                normalized_netlist="",
                original_netlist=netlist,
                errors=["Empty netlist provided"]
            )

        original = netlist
        changes = []
        lines = netlist.strip().split('\n')

        # Ensure title line
        first_line = lines[0].strip() if lines else ""
        needs_title = self._looks_like_component(first_line)

        if needs_title:
            effective_title = title or self.default_title
            lines.insert(0, effective_title)
            changes.append(f"Added title: '{effective_title}'")
        elif title and title != first_line:
            lines[0] = title
            changes.append(f"Replaced title: '{first_line}' -> '{title}'")

        # Find where .end is (or should be)
        end_idx = None
        for i, line in enumerate(lines):
            if line.strip().lower() == '.end':
                end_idx = i
                break

        # Ensure analysis directive
        has_analysis = self._has_analysis_directive('\n'.join(lines))
        if not has_analysis:
            # Insert before .end or at the end
            insert_idx = end_idx if end_idx is not None else len(lines)
            lines.insert(insert_idx, self.default_analysis)
            changes.append(f"Added default analysis: '{self.default_analysis}'")
            if end_idx is not None:
                end_idx += 1  # Adjust for insertion

        # Ensure .end directive
        if end_idx is None:
            lines.append('.end')
            changes.append("Added .end directive")

        # Clean up blank lines and normalize spacing
        normalized_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                normalized_lines.append(stripped)

        normalized_netlist = '\n'.join(normalized_lines)

        # Final validation
        validation = self.validate_netlist(normalized_netlist)

        return NormalizationResult(
            success=validation.is_valid,
            normalized_netlist=normalized_netlist,
            original_netlist=original,
            changes_made=changes,
            errors=validation.errors
        )

    def _looks_like_component(self, line: str) -> bool:
        """Check if a line looks like a component definition rather than a title."""
        if not line:
            return False

        line = line.strip()
        first_char = line[0].upper()

        # If starts with valid component prefix and followed by digit or space
        if first_char in self.VALID_PREFIXES and len(line) > 1:
            second_char = line[1]
            if second_char.isdigit() or second_char == ' ':
                return True

        return False

    def from_circuitvision_format(self, components: list, title: Optional[str] = None) -> NormalizationResult:
        """
        Convert CircuitVision component list to SPICE netlist.

        Args:
            components: List of component dicts from CircuitVision
                        [{'class': 'resistor', 'component_type': 'R',
                          'component_num': 1, 'node_1': 'n1', 'node_2': 'n2',
                          'value': '10k'}, ...]
            title: Optional circuit title

        Returns:
            NormalizationResult with SPICE netlist
        """
        if not components:
            return NormalizationResult(
                success=False,
                normalized_netlist="",
                original_netlist="",
                errors=["Empty component list provided"]
            )

        lines = []
        lines.append(title or self.default_title)
        lines.append("* Generated by CircuitVision")
        lines.append("")

        for comp in components:
            line = self._component_to_spice_line(comp)
            if line:
                lines.append(line)

        # Add analysis and end
        lines.append("")
        lines.append(self.default_analysis)
        lines.append(".end")

        netlist = '\n'.join(lines)

        return NormalizationResult(
            success=True,
            normalized_netlist=netlist,
            original_netlist=str(components),
            changes_made=["Converted from CircuitVision format"]
        )

    def _component_to_spice_line(self, comp: dict) -> Optional[str]:
        """Convert a single CircuitVision component dict to SPICE line."""
        comp_type = comp.get('component_type', '')
        comp_num = comp.get('component_num', 1)
        node_1 = comp.get('node_1', 'n1')
        node_2 = comp.get('node_2', 'n2')
        value = comp.get('value', '')

        if not comp_type:
            return None

        name = f"{comp_type}{comp_num}"

        # Handle different component types
        if comp_type in ['R', 'C', 'L']:
            # Passive components: NAME N1 N2 VALUE
            value_str = str(value) if value else '1k'  # Default for missing values
            return f"{name} {node_1} {node_2} {value_str}"

        elif comp_type == 'V':
            # Voltage source: NAME N+ N- [DC value] [AC mag phase] [transient]
            value_str = str(value) if value else 'DC 5'
            if not value_str.upper().startswith(('DC', 'AC', 'SIN', 'PULSE')):
                value_str = f"DC {value_str}"
            return f"{name} {node_1} {node_2} {value_str}"

        elif comp_type == 'I':
            # Current source: NAME N+ N- VALUE
            value_str = str(value) if value else 'DC 1m'
            if not value_str.upper().startswith(('DC', 'AC', 'SIN', 'PULSE')):
                value_str = f"DC {value_str}"
            return f"{name} {node_1} {node_2} {value_str}"

        elif comp_type == 'D':
            # Diode: NAME N+ N- MODEL
            model = value if value else 'D1N4148'
            return f"{name} {node_1} {node_2} {model}"

        elif comp_type in ['Q', 'M']:
            # Transistor: NAME NC NB NE MODEL (simplified)
            node_3 = comp.get('node_3', '0')
            model = value if value else ('2N2222' if comp_type == 'Q' else 'NMOS')
            return f"{name} {node_1} {node_2} {node_3} {model}"

        elif comp_type in ['E', 'G', 'F', 'H']:
            # Dependent sources
            ctrl_node_1 = comp.get('ctrl_node_1', 'ctrl1')
            ctrl_node_2 = comp.get('ctrl_node_2', 'ctrl2')
            gain = value if value else '1'
            return f"{name} {node_1} {node_2} {ctrl_node_1} {ctrl_node_2} {gain}"

        else:
            # Generic fallback
            value_str = str(value) if value else ''
            return f"{name} {node_1} {node_2} {value_str}".strip()


def normalize_netlist(netlist: str, title: Optional[str] = None) -> Tuple[str, List[str]]:
    """
    Convenience function to normalize a netlist.

    Args:
        netlist: Raw netlist string
        title: Optional title

    Returns:
        Tuple of (normalized_netlist, list_of_changes)

    Raises:
        ValueError if normalization fails
    """
    normalizer = NetlistNormalizer()
    result = normalizer.normalize(netlist, title)

    if not result.success:
        raise ValueError(f"Netlist normalization failed: {', '.join(result.errors)}")

    return result.normalized_netlist, result.changes_made
