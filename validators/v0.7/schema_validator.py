"""
OMEN v0.7 Schema Validator

Validates packets against JSON Schema definitions per OMEN.md Section 9.
Enforces structural correctness, type safety, and enum constraints.

Usage:
    validator = SchemaValidator()
    result = validator.validate_packet(packet_dict)
    if not result.is_valid:
        print(result.errors)
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

try:
    from jsonschema import Draft202012Validator, ValidationError
    from jsonschema.exceptions import SchemaError
    import jsonschema.validators as jsval
    
    # Prevent remote schema fetching
    import requests
    _original_get = requests.get
    def no_remote_get(url, *args, **kwargs):
        if 'omen.ace-framework.org' in url:
            raise ValueError(f"Refusing remote schema fetch for {url}. All schemas must be local.")
        return _original_get(url, *args, **kwargs)
    requests.get = no_remote_get
    
except ImportError:
    raise ImportError(
        "jsonschema package required. Install with: pip install jsonschema"
    )


class ValidationResultType(Enum):
    """Validation outcome classification."""
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"  # Schema loading or internal error


@dataclass
class ValidationResult:
    """Result of schema validation."""
    is_valid: bool
    result_type: ValidationResultType
    errors: List[str]
    warnings: List[str]
    packet_type: Optional[str] = None
    packet_id: Optional[str] = None
    
    def __bool__(self) -> bool:
        """Allow boolean check: if result: ..."""
        return self.is_valid


class SchemaValidator:
    """
    Validates OMEN packets against JSON Schema definitions.
    
    Loads schemas from schema/v0.7/ directory and validates packet
    structure, types, required fields, and enum constraints.
    """
    
    def __init__(self, schema_base_path: Optional[Path] = None):
        """
        Initialize validator with schema base path.
        
        Args:
            schema_base_path: Root directory containing schema/v0.7/
                            Defaults to repository root if None
        """
        if schema_base_path is None:
            # Assume we're in validators/v0.7/, go up to repo root
            schema_base_path = Path(__file__).parent.parent.parent
        
        self.schema_base_path = Path(schema_base_path).resolve()
        self.schema_dir = self.schema_base_path / "schema" / "v0.7"
        
        if not self.schema_dir.exists():
            raise FileNotFoundError(
                f"Schema directory not found: {self.schema_dir}"
            )
        
        # Cache for loaded schemas
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft202012Validator] = {}
        
        # Preload core schemas
        self._load_core_schemas()
    
    def _load_core_schemas(self) -> None:
        """Preload header, MCP, and base schemas."""
        core_schemas = [
            "header/PacketHeader.schema.json",
            "mcp/MCP.schema.json",
            "packets/PacketBase.schema.json"
        ]
        
        for schema_path in core_schemas:
            self._load_schema(schema_path)
    
    def _load_schema(self, relative_path: str) -> Dict[str, Any]:
        """
        Load a JSON schema file.
        
        Args:
            relative_path: Path relative to schema_dir
            
        Returns:
            Schema dictionary
            
        Raises:
            FileNotFoundError: Schema file not found
            json.JSONDecodeError: Invalid JSON
        """
        if relative_path in self._schema_cache:
            return self._schema_cache[relative_path]
        
        schema_file = self.schema_dir / relative_path
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema not found: {schema_file}")
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        self._schema_cache[relative_path] = schema
        return schema
    
    def _get_validator(self, schema_path: str) -> Draft202012Validator:
        """
        Get or create a validator for a schema.
        
        Args:
            schema_path: Relative path to schema file
            
        Returns:
            Configured validator instance
        """
        if schema_path in self._validators:
            return self._validators[schema_path]
        
        schema = self._load_schema(schema_path)
        
        # List of schemas to preload for $ref resolution
        schema_paths_to_load = [
            'header/PacketHeader.schema.json',
            'mcp/MCP.schema.json', 
            'packets/PacketBase.schema.json',
            'packets/ObservationPacket.schema.json',
            'packets/BeliefUpdatePacket.schema.json',
            'packets/DecisionPacket.schema.json',
            'packets/TaskDirectivePacket.schema.json',
            'packets/TaskResultPacket.schema.json',
            'packets/ToolAuthorizationToken.schema.json',
            'packets/EscalationPacket.schema.json'
        ]
        
        # Build a schema registry for $ref resolution
        # Import referencing if available (jsonschema 4.18+)
        try:
            from referencing import Registry, Resource
            from referencing.jsonschema import DRAFT202012
            
            resources = []
            for path in schema_paths_to_load:
                try:
                    s = self._load_schema(path)
                    if "$id" in s:
                        resources.append((s["$id"], Resource.from_contents(s, default_specification=DRAFT202012)))
                except FileNotFoundError:
                    pass
            
            registry = Registry().with_resources(resources)
            validator = Draft202012Validator(schema, registry=registry)
            
        except ImportError:
            # Fall back to deprecated RefResolver for older jsonschema
            from jsonschema import RefResolver
            
            store = {}
            for path in schema_paths_to_load:
                try:
                    s = self._load_schema(path)
                    if "$id" in s:
                        store[s["$id"]] = s
                except FileNotFoundError:
                    pass
            
            if "$id" in schema:
                store[schema["$id"]] = schema
            
            schema_uri = (self.schema_dir / schema_path).as_uri()
            resolver = RefResolver(
                base_uri=schema_uri,
                referrer=schema,
                store=store
            )
            
            validator = Draft202012Validator(schema, resolver=resolver)
        
        self._validators[schema_path] = validator
        
        return validator
    
    def validate_packet(self, packet: Dict[str, Any]) -> ValidationResult:
        """
        Validate a packet against appropriate schema.
        
        Args:
            packet: Packet dictionary (must have header.packet_type)
            
        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []
        
        # Extract packet metadata
        try:
            packet_type = packet["header"]["packet_type"]
            packet_id = packet["header"]["packet_id"]
        except KeyError as e:
            return ValidationResult(
                is_valid=False,
                result_type=ValidationResultType.FAIL,
                errors=[f"Missing required header field: {e}"],
                warnings=[]
            )
        
        # Determine schema path
        schema_path = f"packets/{packet_type}.schema.json"
        
        try:
            validator = self._get_validator(schema_path)
        except FileNotFoundError:
            return ValidationResult(
                is_valid=False,
                result_type=ValidationResultType.ERROR,
                errors=[f"No schema found for packet_type: {packet_type}"],
                warnings=[],
                packet_type=packet_type,
                packet_id=packet_id
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                result_type=ValidationResultType.ERROR,
                errors=[f"Schema loading error: {str(e)}"],
                warnings=[],
                packet_type=packet_type,
                packet_id=packet_id
            )
        
        # Validate packet
        validation_errors = list(validator.iter_errors(packet))
        
        for error in validation_errors:
            # Build error path
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            error_msg = f"{path}: {error.message}"
            errors.append(error_msg)
        
        # Check for warnings (optional best practices)
        warnings.extend(self._check_warnings(packet, packet_type))
        
        is_valid = len(errors) == 0
        result_type = (
            ValidationResultType.PASS if is_valid
            else ValidationResultType.FAIL
        )
        
        return ValidationResult(
            is_valid=is_valid,
            result_type=result_type,
            errors=errors,
            warnings=warnings,
            packet_type=packet_type,
            packet_id=packet_id
        )
    
    def _check_warnings(
        self,
        packet: Dict[str, Any],
        packet_type: str
    ) -> List[str]:
        """
        Check for warnings (soft constraints, best practices).
        
        Args:
            packet: Packet dictionary
            packet_type: Packet type string
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check evidence_absent_reason when evidence_refs empty
        try:
            evidence = packet.get("mcp", {}).get("evidence", {})
            refs = evidence.get("evidence_refs", [])
            reason = evidence.get("evidence_absent_reason")
            
            if len(refs) == 0 and not reason:
                warnings.append(
                    "evidence_absent_reason recommended when evidence_refs empty"
                )
        except (KeyError, TypeError):
            pass  # MCP might not be present for all packet types
        
        # Check campaign_id presence for long-running operations
        if packet_type in ["DecisionPacket", "EscalationPacket"]:
            if not packet.get("header", {}).get("campaign_id"):
                warnings.append(
                    "campaign_id recommended for strategic decisions"
                )
        
        return warnings
    
    def validate_episode_sequence(
        self,
        packets: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """
        Validate a sequence of packets (e.g., from JSONL episode).
        
        Args:
            packets: List of packet dictionaries
            
        Returns:
            List of validation results (one per packet)
        """
        return [self.validate_packet(packet) for packet in packets]
    
    def load_and_validate_file(self, file_path: Path) -> ValidationResult:
        """
        Load and validate a single packet from JSON file.
        
        Args:
            file_path: Path to JSON packet file
            
        Returns:
            ValidationResult
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                packet = json.load(f)
            return self.validate_packet(packet)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                result_type=ValidationResultType.ERROR,
                errors=[f"Invalid JSON: {str(e)}"],
                warnings=[]
            )
        except FileNotFoundError:
            return ValidationResult(
                is_valid=False,
                result_type=ValidationResultType.ERROR,
                errors=[f"File not found: {file_path}"],
                warnings=[]
            )
    
    def load_and_validate_jsonl(
        self,
        file_path: Path
    ) -> List[ValidationResult]:
        """
        Load and validate episode sequence from JSONL file.
        
        Args:
            file_path: Path to JSONL episode file
            
        Returns:
            List of validation results
        """
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        packet = json.loads(line)
                        result = self.validate_packet(packet)
                        results.append(result)
                    except json.JSONDecodeError as e:
                        results.append(
                            ValidationResult(
                                is_valid=False,
                                result_type=ValidationResultType.ERROR,
                                errors=[f"Line {line_num}: Invalid JSON: {str(e)}"],
                                warnings=[]
                            )
                        )
        except FileNotFoundError:
            results.append(
                ValidationResult(
                    is_valid=False,
                    result_type=ValidationResultType.ERROR,
                    errors=[f"File not found: {file_path}"],
                    warnings=[]
                )
            )
        
        return results


def validate_golden_fixtures(schema_base_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Validate all golden fixtures and return summary.
    
    Args:
        schema_base_path: Root directory containing schema/ and goldens/
        
    Returns:
        Dictionary with validation summary
    """
    if schema_base_path is None:
        schema_base_path = Path(__file__).parent.parent.parent
    
    validator = SchemaValidator(schema_base_path)
    goldens_dir = schema_base_path / "goldens" / "v0.7"
    
    if not goldens_dir.exists():
        return {
            "error": f"Goldens directory not found: {goldens_dir}",
            "total": 0,
            "passed": 0,
            "failed": 0
        }
    
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "files": {}
    }
    
    # Validate single packet files
    for json_file in goldens_dir.glob("*.json"):
        result = validator.load_and_validate_file(json_file)
        results["total"] += 1
        
        # Check if this is an INVALID fixture (expected to fail)
        is_negative_test = "INVALID" in json_file.name
        
        if is_negative_test:
            # For negative tests, we expect validation to fail
            passed = not result.is_valid
        else:
            passed = result.is_valid
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        results["files"][str(json_file.name)] = {
            "passed": passed,
            "is_negative_test": is_negative_test,
            "errors": result.errors,
            "warnings": result.warnings
        }
    
    # Validate episode sequences
    for jsonl_file in goldens_dir.glob("*.jsonl"):
        packet_results = validator.load_and_validate_jsonl(jsonl_file)
        
        for i, result in enumerate(packet_results):
            results["total"] += 1
            if result.is_valid:
                results["passed"] += 1
            else:
                results["failed"] += 1
        
        # Summary for episode
        all_valid = all(r.is_valid for r in packet_results)
        results["files"][str(jsonl_file.name)] = {
            "passed": all_valid,
            "is_negative_test": False,
            "packet_count": len(packet_results),
            "errors": [e for r in packet_results for e in r.errors],
            "warnings": [w for r in packet_results for w in r.warnings]
        }
    
    return results


if __name__ == "__main__":
    """CLI usage: python schema_validator.py"""
    import sys
    
    # Run validation on golden fixtures
    results = validate_golden_fixtures()
    
    print(f"\n{'='*60}")
    print("OMEN v0.7 Schema Validation Report")
    print(f"{'='*60}\n")
    
    print(f"Total Packets:  {results['total']}")
    print(f"Passed:         {results['passed']}")
    print(f"Failed:         {results['failed']}")
    print(f"Success Rate:   {results['passed']/results['total']*100:.1f}%\n")
    
    if results.get("error"):
        print(f"ERROR: {results['error']}\n")
        sys.exit(1)
    
    # Detailed results
    for filename, file_result in results["files"].items():
        status = "✓ PASS" if file_result["passed"] else "✗ FAIL"
        negative = " (negative test)" if file_result["is_negative_test"] else ""
        print(f"{status} {filename}{negative}")
        
        if file_result["errors"]:
            for error in file_result["errors"][:3]:  # Show first 3 errors
                print(f"    ERROR: {error}")
            if len(file_result["errors"]) > 3:
                print(f"    ... and {len(file_result['errors'])-3} more errors")
        
        if file_result["warnings"]:
            for warning in file_result["warnings"][:2]:
                print(f"    WARN:  {warning}")
    
    print()
    
    # Exit code based on results
    if results["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)
