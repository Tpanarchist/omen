#!/usr/bin/env python3
"""
OMEN v0.7 Unified Validator CLI

Validates OMEN packets and episodes through three validation layers:
1. Schema validation (JSON Schema + structural checks)
2. FSM validation (state machine + sequential dependencies)
3. Invariant validation (cross-policy constraints + episode semantics)

Usage:
    python validate_omen.py packet <file.json>           # Validate single packet
    python validate_omen.py episode <file.jsonl>         # Validate episode sequence
    python validate_omen.py goldens                      # Validate all golden fixtures
    python validate_omen.py --help                       # Show help
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Add validators to path
sys.path.insert(0, str(Path(__file__).parent / "validators" / "v0.7"))

from schema_validator import SchemaValidator
from fsm_validator import FSMValidator
from invariant_validator import InvariantValidator


class ValidationResult:
    """Unified validation result"""
    def __init__(self):
        self.packet_id: str = "unknown"
        self.schema_valid: bool = True
        self.fsm_valid: bool = True
        self.invariant_valid: bool = True
        self.schema_errors: List[str] = []
        self.fsm_errors: List[str] = []
        self.invariant_errors: List[str] = []
        self.warnings: List[str] = []
    
    @property
    def is_valid(self) -> bool:
        return self.schema_valid and self.fsm_valid and self.invariant_valid
    
    def add_schema_errors(self, errors: List[str]):
        if errors:
            self.schema_valid = False
            self.schema_errors.extend(errors)
    
    def add_fsm_errors(self, errors: List[str]):
        if errors:
            self.fsm_valid = False
            self.fsm_errors.extend(errors)
    
    def add_invariant_errors(self, errors: List[str]):
        if errors:
            self.invariant_valid = False
            self.invariant_errors.extend(errors)


class OMENValidator:
    """Unified OMEN validator combining all three layers"""
    
    def __init__(self, enable_schema=True, enable_fsm=True, enable_invariants=True, 
                 check_timestamps=True):
        """
        Initialize validator
        
        Args:
            enable_schema: Enable schema validation layer
            enable_fsm: Enable FSM validation layer
            enable_invariants: Enable invariant validation layer
            check_timestamps: Enable timestamp checks (disable for historical fixtures)
        """
        self.enable_schema = enable_schema
        self.enable_fsm = enable_fsm
        self.enable_invariants = enable_invariants
        
        if enable_schema:
            self.schema_validator = SchemaValidator()
        if enable_fsm:
            self.fsm_validator = FSMValidator()
        if enable_invariants:
            self.invariant_validator = InvariantValidator(check_timestamps=check_timestamps)
    
    def validate_packet(self, packet: Dict) -> ValidationResult:
        """Validate single packet through all enabled layers"""
        result = ValidationResult()
        result.packet_id = packet.get("header", {}).get("packet_id", "unknown")
        
        # Layer 1: Schema validation
        if self.enable_schema:
            schema_result = self.schema_validator.validate_packet(packet)
            result.add_schema_errors(schema_result.errors)
            result.warnings.extend(schema_result.warnings)
        
        # Layer 2: FSM validation (only if schema passed)
        if self.enable_fsm and result.schema_valid:
            fsm_result = self.fsm_validator.validate_packet(packet)
            result.add_fsm_errors(fsm_result.errors)
            result.warnings.extend(fsm_result.warnings)
        
        # Layer 3: Invariant validation (only if FSM passed)
        if self.enable_invariants and result.fsm_valid:
            inv_result = self.invariant_validator.validate_packet(packet)
            result.add_invariant_errors(inv_result.violations)
            result.warnings.extend(inv_result.warnings)
        
        return result
    
    def validate_episode(self, packets: List[Dict]) -> List[ValidationResult]:
        """Validate episode sequence"""
        results = []
        
        for packet in packets:
            result = self.validate_packet(packet)
            results.append(result)
            
            # Stop on first failure
            if not result.is_valid:
                break
        
        return results


def print_result(result: ValidationResult, verbose: bool = False):
    """Print validation result"""
    status = "[PASS]" if result.is_valid else "[FAIL]"
    print(f"{status} - {result.packet_id}")
    
    if not result.is_valid or verbose:
        if result.schema_errors:
            print("  Schema errors:")
            for error in result.schema_errors:
                print(f"    • {error}")
        
        if result.fsm_errors:
            print("  FSM errors:")
            for error in result.fsm_errors:
                print(f"    • {error}")
        
        if result.invariant_errors:
            print("  Invariant errors:")
            for error in result.invariant_errors:
                print(f"    • {error}")
    
    if verbose and result.warnings:
        print("  Warnings:")
        for warning in result.warnings:
            print(f"    [!] {warning}")


def validate_packet_file(filepath: Path, validator: OMENValidator, verbose: bool, 
                         skip_stateful: bool = False) -> bool:
    """Validate single packet file"""
    print(f"\n[Packet] Validating: {filepath.name}")
    
    try:
        with open(filepath, 'r') as f:
            packet = json.load(f)
        
        # For standalone packets, optionally skip FSM/invariant validation
        # (they require episode context)
        if skip_stateful:
            validator_copy = OMENValidator(
                enable_schema=validator.enable_schema,
                enable_fsm=False,
                enable_invariants=False
            )
            result = validator_copy.validate_packet(packet)
        else:
            result = validator.validate_packet(packet)
        
        print_result(result, verbose)
        
        return result.is_valid
    
    except json.JSONDecodeError as e:
        print(f"[FAIL] - Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] - Error: {e}")
        return False


def validate_episode_file(filepath: Path, validator: OMENValidator, verbose: bool) -> bool:
    """Validate episode sequence file"""
    print(f"\n[Episode] Validating: {filepath.name}")
    
    try:
        packets = []
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        packet = json.loads(line)
                        packets.append(packet)
                    except json.JSONDecodeError as e:
                        print(f"[FAIL] - Line {line_num}: Invalid JSON: {e}")
                        return False
        
        if not packets:
            print("[FAIL] - No packets found in file")
            return False
        
        print(f"  Validating {len(packets)} packets...")
        results = validator.validate_episode(packets)
        
        all_valid = True
        for result in results:
            if not result.is_valid:
                print_result(result, verbose=True)
                all_valid = False
                break
            elif verbose:
                print_result(result, verbose=True)
        
        if all_valid:
            print(f"[PASS] - All {len(results)} packets valid")
        
        return all_valid
    
    except Exception as e:
        print(f"[FAIL] - Error: {e}")
        return False


def validate_goldens(goldens_dir: Path, validator: OMENValidator, verbose: bool) -> Tuple[int, int]:
    """Validate all golden fixtures"""
    print(f"\n[Golden Fixtures] Validating in: {goldens_dir}")
    
    passed = 0
    failed = 0
    
    # Validate individual packet fixtures (schema only - no episode context)
    packet_files = sorted(goldens_dir.glob("*.json"))
    for filepath in packet_files:
        if "INVALID" not in filepath.name:  # Skip intentionally invalid fixtures
            if validate_packet_file(filepath, validator, verbose, skip_stateful=True):
                passed += 1
            else:
                failed += 1
    
    # Validate episode fixtures (all layers)
    episode_files = sorted(goldens_dir.glob("Episode.*.jsonl"))
    for filepath in episode_files:
        if "INVALID" not in filepath.name:
            if validate_episode_file(filepath, validator, verbose):
                passed += 1
            else:
                failed += 1
    
    return passed, failed


def main():
    parser = argparse.ArgumentParser(
        description="OMEN v0.7 Unified Validator - Validates packets and episodes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single packet
  python validate_omen.py packet goldens/v0.7/DecisionPacket.verify_first.json
  
  # Validate an episode sequence
  python validate_omen.py episode goldens/v0.7/Episode.verify_loop.jsonl
  
  # Validate all golden fixtures
  python validate_omen.py goldens
  
  # Verbose output with warnings
  python validate_omen.py goldens -v
  
  # Skip specific validation layers
  python validate_omen.py episode file.jsonl --no-invariants
        """
    )
    
    parser.add_argument(
        "mode",
        choices=["packet", "episode", "goldens"],
        help="Validation mode"
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="File to validate (required for packet/episode modes)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output (show all details)"
    )
    parser.add_argument(
        "--no-schema",
        action="store_true",
        help="Disable schema validation layer"
    )
    parser.add_argument(
        "--no-fsm",
        action="store_true",
        help="Disable FSM validation layer"
    )
    parser.add_argument(
        "--no-invariants",
        action="store_true",
        help="Disable invariant validation layer"
    )
    parser.add_argument(
        "--no-timestamp-checks",
        action="store_true",
        help="Disable timestamp checks (for historical fixtures)"
    )
    parser.add_argument(
        "--goldens-dir",
        type=Path,
        default=Path("goldens/v0.7"),
        help="Golden fixtures directory (default: goldens/v0.7)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.mode in ["packet", "episode"] and not args.file:
        parser.error(f"{args.mode} mode requires a file argument")
    
    # Initialize validator
    validator = OMENValidator(
        enable_schema=not args.no_schema,
        enable_fsm=not args.no_fsm,
        enable_invariants=not args.no_invariants,
        check_timestamps=not args.no_timestamp_checks
    )
    
    # Execute validation
    try:
        if args.mode == "packet":
            filepath = Path(args.file)
            if not filepath.exists():
                print(f"[ERROR] File not found: {filepath}")
                sys.exit(1)
            
            success = validate_packet_file(filepath, validator, args.verbose)
            sys.exit(0 if success else 1)
        
        elif args.mode == "episode":
            filepath = Path(args.file)
            if not filepath.exists():
                print(f"[ERROR] File not found: {filepath}")
                sys.exit(1)
            
            success = validate_episode_file(filepath, validator, args.verbose)
            sys.exit(0 if success else 1)
        
        elif args.mode == "goldens":
            if not args.goldens_dir.exists():
                print(f"[ERROR] Golden fixtures directory not found: {args.goldens_dir}")
                sys.exit(1)
            
            # Disable timestamp checks for historical golden fixtures
            validator = OMENValidator(
                enable_schema=not args.no_schema,
                enable_fsm=not args.no_fsm,
                enable_invariants=not args.no_invariants,
                check_timestamps=False
            )
            
            passed, failed = validate_goldens(args.goldens_dir, validator, args.verbose)
            
            print(f"\n{'='*60}")
            print(f"Summary: {passed} passed, {failed} failed")
            print(f"{'='*60}")
            
            sys.exit(0 if failed == 0 else 1)
    
    except KeyboardInterrupt:
        print("\n\n[WARNING] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
