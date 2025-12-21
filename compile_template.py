#!/usr/bin/env python3
"""
OMEN Template Compiler CLI

Command-line tool for compiling episode templates into valid packet sequences.

Usage:
    python compile_template.py <template> <correlation_id> [options]
    
Examples:
    # Compile verification loop
    python compile_template.py verification corr_001 --output test.jsonl
    
    # Compile write template with custom stakes
    python compile_template.py write corr_write_001 --stakes HIGH --output write_episode.jsonl
    
    # Compile and validate in one command
    python compile_template.py escalation corr_esc_001 --validate --verbose
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from templates.v0_7.template_compiler import (
    TemplateCompiler,
    TemplateID,
    TemplateContext,
    quick_compile
)


def main():
    parser = argparse.ArgumentParser(
        description='OMEN Template Compiler - Generate valid episode sequences from templates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Templates:
  a, grounding       - Template A: Grounding Loop (Sense → Model → Decide)
  b, verification    - Template B: Verification Loop (verify-first pattern)
  c, readonly        - Template C: Read-Only Act (fast path)
  d, write           - Template D: Write Act (token-authorized writes)
  e, escalation      - Template E: Escalation (high stakes/uncertainty)
  f, degraded        - Template F: Degraded Tools (tool failure handling)
  g, compile         - Template G: Compile-to-Code (code generation workflow)

Examples:
  # Basic compilation
  python compile_template.py verification corr_001 -o episode.jsonl
  
  # Custom stakes and quality
  python compile_template.py write corr_002 --stakes CRITICAL --tier SUPERB -o write.jsonl
  
  # Compile and validate
  python compile_template.py degraded corr_003 --validate -v
  
  # List all packets (no file output)
  python compile_template.py grounding corr_004 --list
        """
    )
    
    # Positional arguments
    parser.add_argument('template', 
                       help='Template name (a-g, grounding, verification, etc.)')
    parser.add_argument('correlation_id',
                       help='Episode correlation ID')
    
    # Output control
    parser.add_argument('-o', '--output',
                       help='Output file path (default: stdout if --list, else <correlation_id>.jsonl)')
    parser.add_argument('-f', '--format',
                       choices=['jsonl', 'json'],
                       default='jsonl',
                       help='Output format (default: jsonl)')
    parser.add_argument('-l', '--list',
                       action='store_true',
                       help='List packet IDs and types (no file output)')
    
    # MCP envelope overrides
    parser.add_argument('--intent',
                       help='Intent summary override')
    parser.add_argument('--scope',
                       help='Intent scope override')
    parser.add_argument('--stakes',
                       choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
                       help='Stakes level override')
    parser.add_argument('--tier',
                       choices=['SUBPAR', 'PAR', 'SUPERB'],
                       help='Quality tier override')
    parser.add_argument('--tools-state',
                       choices=['tools_ok', 'tools_partial', 'tools_down'],
                       help='Tools state override')
    
    # Validation
    parser.add_argument('--validate',
                       action='store_true',
                       help='Validate compiled episode with full validator stack')
    parser.add_argument('--no-timestamp-checks',
                       action='store_true',
                       help='Disable timestamp checks during validation')
    
    # Verbose output
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Build context from arguments
    ctx_kwargs = {
        'correlation_id': args.correlation_id
    }
    
    if args.intent:
        ctx_kwargs['intent_summary'] = args.intent
    if args.scope:
        ctx_kwargs['intent_scope'] = args.scope
    if args.stakes:
        ctx_kwargs['stakes_level'] = args.stakes
        # Set consistent impact for stakes level
        stakes_impact_map = {'LOW': 'LOW', 'MEDIUM': 'MEDIUM', 'HIGH': 'HIGH', 'CRITICAL': 'CRITICAL'}
        ctx_kwargs['impact'] = stakes_impact_map[args.stakes]
    if args.tier:
        ctx_kwargs['quality_tier'] = args.tier
    if args.tools_state:
        ctx_kwargs['tools_state'] = args.tools_state
    
    try:
        # Compile template
        if args.verbose:
            print(f"[INFO] Compiling template: {args.template}")
            print(f"[INFO] Correlation ID: {args.correlation_id}")
            if ctx_kwargs:
                print(f"[INFO] Context overrides: {ctx_kwargs}")
        
        packets = quick_compile(args.template, **ctx_kwargs)
        
        if args.verbose:
            print(f"[PASS] Compiled {len(packets)} packets")
        
        # List mode - just show packet info
        if args.list:
            print(f"\nEpisode: {args.correlation_id} ({len(packets)} packets)")
            print("=" * 80)
            for i, pkt in enumerate(packets, 1):
                header = pkt['header']
                print(f"{i}. {header['packet_type']:30s} {header['packet_id']}")
            return 0
        
        # Determine output path
        if args.output:
            output_path = args.output
        else:
            output_path = f"{args.correlation_id}.{args.format}"
        
        # Export
        compiler = TemplateCompiler()
        if args.format == 'jsonl':
            compiler.export_jsonl(output_path, packets)
        else:
            compiler.export_json(output_path, packets)
        
        print(f"[PASS] Exported {len(packets)} packets to: {output_path}")
        
        # Validate if requested
        if args.validate:
            if args.verbose:
                print(f"[INFO] Validating episode...")
            
            # Import validator
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from validate_omen import OMENValidator
                
                validator = OMENValidator(
                    check_timestamps=not args.no_timestamp_checks
                )
                
                # Validate each packet
                all_valid = True
                for i, packet in enumerate(packets, 1):
                    result = validator.validate_packet(packet)
                    if not result.is_valid:
                        all_valid = False
                        print(f"[FAIL] Packet {i} ({packet['header']['packet_type']}): INVALID")
                        if result.schema_errors:
                            for error in result.schema_errors:
                                print(f"  - Schema: {error}")
                        if result.fsm_errors:
                            for error in result.fsm_errors:
                                print(f"  - FSM: {error}")
                        if result.invariant_errors:
                            for error in result.invariant_errors:
                                print(f"  - Invariant: {error}")
                    elif args.verbose:
                        print(f"[PASS] Packet {i} ({packet['header']['packet_type']}): VALID")
                
                if all_valid:
                    print(f"[PASS] All {len(packets)} packets validated successfully")
                    return 0
                else:
                    print(f"[FAIL] Some packets failed validation")
                    return 1
                    
            except ImportError as e:
                print(f"[WARNING] Could not import validator: {e}")
                print("[WARNING] Skipping validation (run validate_omen.py separately)")
                return 0
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Compilation failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
