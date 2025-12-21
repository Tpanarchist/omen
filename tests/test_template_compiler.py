"""
Tests for OMEN Template Compiler

Verifies that templates compile to structurally valid packet sequences
that pass FSM validation (schema details TBD).
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from templates.v0_7.template_compiler import (
    TemplateCompiler,
    TemplateID,
    TemplateContext,
    compile_template,
    quick_compile
)


class TestTemplateCompiler:
    """Test template compilation"""
    
    def test_compiler_initialization(self):
        """Test compiler can be created"""
        compiler = TemplateCompiler()
        assert compiler is not None
    
    def test_template_a_grounding_loop(self):
        """Test Template A: Grounding Loop compiles"""
        ctx = TemplateContext(correlation_id="test_a_001")
        compiler = TemplateCompiler()
        
        packets = compiler.compile(TemplateID.GROUNDING_LOOP, ctx)
        
        assert len(packets) == 3
        assert packets[0]["header"]["packet_type"] == "ObservationPacket"
        assert packets[1]["header"]["packet_type"] == "BeliefUpdatePacket"
        assert packets[2]["header"]["packet_type"] == "DecisionPacket"
        
        # All packets should share correlation_id
        for pkt in packets:
            assert pkt["header"]["correlation_id"] == "test_a_001"
        
        # Packets should chain via previous_packet_id
        assert "previous_packet_id" not in packets[0]["header"]
        assert packets[1]["header"]["previous_packet_id"] == packets[0]["header"]["packet_id"]
        assert packets[2]["header"]["previous_packet_id"] == packets[1]["header"]["packet_id"]
    
    def test_template_b_verification_loop(self):
        """Test Template B: Verification Loop compiles"""
        ctx = TemplateContext(correlation_id="test_b_001")
        compiler = TemplateCompiler()
        
        packets = compiler.compile(TemplateID.VERIFICATION_LOOP, ctx)
        
        assert len(packets) == 8
        # First decision should be VERIFY_FIRST
        decision1 = [p for p in packets if p["header"]["packet_type"] == "DecisionPacket"][0]
        assert decision1["payload"]["decision_outcome"] == "VERIFY_FIRST"
        
        # Should have verification directive and result
        directives = [p for p in packets if p["header"]["packet_type"] == "TaskDirectivePacket"]
        results = [p for p in packets if p["header"]["packet_type"] == "TaskResultPacket"]
        assert len(directives) >= 1
        assert len(results) >= 1
        
        # Final decision should be ACT
        decisions = [p for p in packets if p["header"]["packet_type"] == "DecisionPacket"]
        assert decisions[-1]["payload"]["decision_outcome"] == "ACT"
    
    def test_template_c_readonly_act(self):
        """Test Template C: Read-Only Act compiles"""
        ctx = TemplateContext(correlation_id="test_c_001")
        compiler = TemplateCompiler()
        
        packets = compiler.compile(TemplateID.READONLY_ACT, ctx)
        
        assert len(packets) == 5
        # Should have decision, directive, result, observation, belief
        types = [p["header"]["packet_type"] for p in packets]
        assert "DecisionPacket" in types
        assert "TaskDirectivePacket" in types
        assert "TaskResultPacket" in types
        assert "ObservationPacket" in types
        assert "BeliefUpdatePacket" in types
    
    def test_template_d_write_act(self):
        """Test Template D: Write Act compiles"""
        ctx = TemplateContext(correlation_id="test_d_001")
        compiler = TemplateCompiler()
        
        packets = compiler.compile(TemplateID.WRITE_ACT, ctx)
        
        assert len(packets) == 6
        # Should have token before directive
        types = [p["header"]["packet_type"] for p in packets]
        assert "ToolAuthorizationToken" in types
        assert "DecisionPacket" in types
        assert "TaskDirectivePacket" in types
        
        # Token should come before directive
        token_idx = types.index("ToolAuthorizationToken")
        directive_idx = types.index("TaskDirectivePacket")
        assert token_idx < directive_idx
    
    def test_template_e_escalation(self):
        """Test Template E: Escalation compiles"""
        ctx = TemplateContext(correlation_id="test_e_001")
        compiler = TemplateCompiler()
        
        packets = compiler.compile(TemplateID.ESCALATION, ctx)
        
        assert len(packets) == 2
        assert packets[0]["header"]["packet_type"] == "DecisionPacket"
        assert packets[0]["payload"]["decision_outcome"] == "ESCALATE"
        assert packets[1]["header"]["packet_type"] == "EscalationPacket"
        
        # EscalationPacket should have 2-3 options
        options = packets[1]["payload"]["top_options"]
        assert 2 <= len(options) <= 3
    
    def test_template_f_degraded_tools(self):
        """Test Template F: Degraded Tools compiles"""
        ctx = TemplateContext(correlation_id="test_f_001")
        compiler = TemplateCompiler()
        
        packets = compiler.compile(TemplateID.DEGRADED_TOOLS, ctx)
        
        assert len(packets) == 4
        # Should observe degradation, update beliefs, decide escalate, emit escalation
        types = [p["header"]["packet_type"] for p in packets]
        assert types == ["ObservationPacket", "BeliefUpdatePacket", "DecisionPacket", "EscalationPacket"]
        
        # Decision should be ESCALATE
        assert packets[2]["payload"]["decision_outcome"] == "ESCALATE"
    
    def test_template_g_compile_to_code(self):
        """Test Template G: Compile-to-Code compiles"""
        ctx = TemplateContext(correlation_id="test_g_001")
        compiler = TemplateCompiler()
        
        packets = compiler.compile(TemplateID.COMPILE_TO_CODE, ctx)
        
        assert len(packets) == 7
        # Should have VERIFY_FIRST, generation, test, belief update, ACT
        decisions = [p for p in packets if p["header"]["packet_type"] == "DecisionPacket"]
        assert len(decisions) == 2
        assert decisions[0]["payload"]["decision_outcome"] == "VERIFY_FIRST"
        assert decisions[1]["payload"]["decision_outcome"] == "ACT"


class TestConvenienceFunctions:
    """Test convenience compilation functions"""
    
    def test_compile_template_function(self):
        """Test compile_template convenience function"""
        packets = compile_template(
            TemplateID.GROUNDING_LOOP,
            "test_conv_001",
            intent_summary="Test compilation",
            stakes_level="LOW"
        )
        
        assert len(packets) == 3
        assert packets[0]["header"]["correlation_id"] == "test_conv_001"
        # Note: Template A overrides intent per packet, but stakes should be consistent
        assert packets[0]["mcp"]["stakes"]["stakes_level"] == "LOW"
    
    def test_quick_compile_with_template_name(self):
        """Test quick_compile with string template names"""
        # Test various name aliases
        packets_a = quick_compile("grounding", "test_quick_a")
        assert len(packets_a) == 3
        
        packets_b = quick_compile("verification", "test_quick_b")
        assert len(packets_b) == 8
        
        packets_c = quick_compile("readonly", "test_quick_c")
        assert len(packets_c) == 5
        
        packets_d = quick_compile("write", "test_quick_d")
        assert len(packets_d) == 6
        
        packets_e = quick_compile("escalation", "test_quick_e")
        assert len(packets_e) == 2
        
        packets_f = quick_compile("degraded", "test_quick_f")
        assert len(packets_f) == 4
        
        packets_g = quick_compile("compile", "test_quick_g")
        assert len(packets_g) == 7
    
    def test_quick_compile_unknown_template(self):
        """Test quick_compile rejects unknown template names"""
        with pytest.raises(ValueError, match="Unknown template"):
            quick_compile("nonexistent", "test_fail")


class TestExportFunctions:
    """Test packet export functionality"""
    
    def test_export_jsonl(self, tmp_path):
        """Test JSONL export"""
        packets = compile_template(TemplateID.GROUNDING_LOOP, "test_export_001")
        output_file = tmp_path / "test.jsonl"
        
        TemplateCompiler.export_jsonl(str(output_file), packets)
        
        assert output_file.exists()
        lines = output_file.read_text().strip().split('\n')
        assert len(lines) == 3
        
        # Each line should be valid JSON
        import json
        for line in lines:
            pkt = json.loads(line)
            assert "header" in pkt
            assert "mcp" in pkt
    
    def test_export_json(self, tmp_path):
        """Test JSON export"""
        packets = compile_template(TemplateID.GROUNDING_LOOP, "test_export_002")
        output_file = tmp_path / "test.json"
        
        TemplateCompiler.export_json(str(output_file), packets)
        
        assert output_file.exists()
        
        import json
        data = json.loads(output_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 3
    
    def test_compile_and_export(self, tmp_path):
        """Test compile_and_export convenience method"""
        ctx = TemplateContext(correlation_id="test_export_003")
        compiler = TemplateCompiler()
        output_file = tmp_path / "test.jsonl"
        
        packets = compiler.compile_and_export(
            TemplateID.GROUNDING_LOOP,
            ctx,
            str(output_file),
            format='jsonl'
        )
        
        assert len(packets) == 3
        assert output_file.exists()


class TestTemplateContext:
    """Test template context configuration"""
    
    def test_context_defaults(self):
        """Test TemplateContext uses reasonable defaults"""
        ctx = TemplateContext(correlation_id="test_ctx_001")
        
        assert ctx.correlation_id == "test_ctx_001"
        assert ctx.campaign_id == "camp_OMEN_BOOT"
        assert ctx.stakes_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert ctx.quality_tier in ["SUBPAR", "PAR", "SUPERB"]
        assert ctx.tools_state in ["tools_ok", "tools_partial", "tools_down"]
    
    def test_context_overrides(self):
        """Test TemplateContext accepts overrides"""
        ctx = TemplateContext(
            correlation_id="test_ctx_002",
            intent_summary="Custom intent",
            stakes_level="CRITICAL",
            quality_tier="SUPERB",
            tools_state="tools_partial",
            token_budget=5000
        )
        
        assert ctx.intent_summary == "Custom intent"
        assert ctx.stakes_level == "CRITICAL"
        assert ctx.quality_tier == "SUPERB"
        assert ctx.tools_state == "tools_partial"
        assert ctx.token_budget == 5000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
