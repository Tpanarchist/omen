"""Tests for bus infrastructure."""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import Mock

from omen.vocabulary import LayerSource, PacketType
from omen.buses import (
    Bus,
    BusMessage,
    DeliveryFailure,
    NorthboundBus,
    SouthboundBus,
    create_northbound_bus,
    create_southbound_bus,
    LAYER_ORDER,
)


class MockPacket:
    """Mock packet for testing."""
    def __init__(self, packet_type: PacketType):
        self.header = Mock()
        self.header.packet_type = packet_type


class MockPacketNoHeader:
    """Mock packet without header for testing graceful handling."""
    def __init__(self):
        pass


class TestBusMessage:
    """Tests for BusMessage."""
    
    def test_create_message(self):
        """Create a bus message."""
        packet = MockPacket(PacketType.OBSERVATION)
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_6,
            target_layer=LayerSource.LAYER_5,
            correlation_id=uuid4(),
        )
        assert msg.source_layer == LayerSource.LAYER_6
        assert msg.target_layer == LayerSource.LAYER_5
        assert msg.packet_type == PacketType.OBSERVATION
    
    def test_broadcast_message(self):
        """Message with None target is broadcast."""
        packet = MockPacket(PacketType.OBSERVATION)
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_6,
            target_layer=None,  # Broadcast
            correlation_id=uuid4(),
        )
        assert msg.target_layer is None
    
    def test_packet_type_graceful_failure(self):
        """packet_type returns None for packets without header."""
        packet = MockPacketNoHeader()
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_6,
            target_layer=None,
            correlation_id=uuid4(),
        )
        assert msg.packet_type is None


class TestNorthboundBus:
    """Tests for northbound bus."""
    
    @pytest.fixture
    def bus(self):
        return create_northbound_bus()
    
    def test_direction(self, bus):
        """Northbound bus reports correct direction."""
        assert bus.direction() == "northbound"
    
    def test_can_route_up(self, bus):
        """Northbound allows routing to higher layers."""
        # L6 can send to L5
        assert bus.can_route(LayerSource.LAYER_6, LayerSource.LAYER_5) is True
        # L6 can send to L1
        assert bus.can_route(LayerSource.LAYER_6, LayerSource.LAYER_1) is True
        # L3 can send to L2
        assert bus.can_route(LayerSource.LAYER_3, LayerSource.LAYER_2) is True
    
    def test_cannot_route_down(self, bus):
        """Northbound blocks routing to lower layers."""
        # L1 cannot send northbound to L6
        assert bus.can_route(LayerSource.LAYER_1, LayerSource.LAYER_6) is False
        # L3 cannot send northbound to L5
        assert bus.can_route(LayerSource.LAYER_3, LayerSource.LAYER_5) is False
    
    def test_cannot_route_same_layer(self, bus):
        """Northbound blocks same-layer routing."""
        assert bus.can_route(LayerSource.LAYER_5, LayerSource.LAYER_5) is False
    
    def test_integrity_receives_all(self, bus):
        """Integrity can receive from any layer."""
        for layer in [LayerSource.LAYER_1, LayerSource.LAYER_2, LayerSource.LAYER_3,
                      LayerSource.LAYER_4, LayerSource.LAYER_5, LayerSource.LAYER_6]:
            assert bus.can_route(layer, LayerSource.INTEGRITY) is True
    
    def test_publish_to_subscriber(self, bus):
        """Published messages reach subscribed handlers."""
        received = []
        bus.subscribe(LayerSource.LAYER_5, lambda m: received.append(m))
        
        packet = MockPacket(PacketType.OBSERVATION)
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_6,
            target_layer=LayerSource.LAYER_5,
            correlation_id=uuid4(),
        )
        
        delivered, failures = bus.publish(msg)
        assert LayerSource.LAYER_5 in delivered
        assert len(failures) == 0
        assert len(received) == 1
        assert received[0] == msg
    
    def test_publish_respects_routing(self, bus):
        """Messages only reach valid routing targets."""
        received_l5 = []
        received_l1 = []
        bus.subscribe(LayerSource.LAYER_5, lambda m: received_l5.append(m))
        bus.subscribe(LayerSource.LAYER_1, lambda m: received_l1.append(m))
        
        # L6 broadcasts northbound
        packet = MockPacket(PacketType.OBSERVATION)
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_6,
            target_layer=None,  # Broadcast
            correlation_id=uuid4(),
        )
        
        delivered, failures = bus.publish(msg)
        
        # Both L5 and L1 should receive (both are north of L6)
        assert len(received_l5) == 1
        assert len(received_l1) == 1
        assert len(failures) == 0
        assert LayerSource.LAYER_5 in delivered
        assert LayerSource.LAYER_1 in delivered
    
    def test_publish_blocks_invalid_routing(self, bus):
        """Messages don't reach layers that violate routing rules."""
        received_l6 = []
        bus.subscribe(LayerSource.LAYER_6, lambda m: received_l6.append(m))
        
        # L5 tries to broadcast northbound (L6 should not receive)
        packet = MockPacket(PacketType.OBSERVATION)
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_5,
            target_layer=None,  # Broadcast
            correlation_id=uuid4(),
        )
        
        delivered, failures = bus.publish(msg)
        
        # L6 should not receive (it's below L5)
        assert len(received_l6) == 0
        assert LayerSource.LAYER_6 not in delivered


class TestSouthboundBus:
    """Tests for southbound bus."""
    
    @pytest.fixture
    def bus(self):
        return create_southbound_bus()
    
    def test_direction(self, bus):
        """Southbound bus reports correct direction."""
        assert bus.direction() == "southbound"
    
    def test_can_route_down(self, bus):
        """Southbound allows routing to lower layers."""
        # L1 can send to L6
        assert bus.can_route(LayerSource.LAYER_1, LayerSource.LAYER_6) is True
        # L2 can send to L5
        assert bus.can_route(LayerSource.LAYER_2, LayerSource.LAYER_5) is True
    
    def test_cannot_route_up(self, bus):
        """Southbound blocks routing to higher layers."""
        # L6 cannot send southbound to L1
        assert bus.can_route(LayerSource.LAYER_6, LayerSource.LAYER_1) is False
    
    def test_cannot_route_same_layer(self, bus):
        """Southbound blocks same-layer routing."""
        assert bus.can_route(LayerSource.LAYER_3, LayerSource.LAYER_3) is False
    
    def test_integrity_sends_to_all(self, bus):
        """Integrity can send to any layer."""
        for layer in [LayerSource.LAYER_1, LayerSource.LAYER_2, LayerSource.LAYER_3,
                      LayerSource.LAYER_4, LayerSource.LAYER_5, LayerSource.LAYER_6]:
            assert bus.can_route(LayerSource.INTEGRITY, layer) is True
    
    def test_publish_to_subscriber(self, bus):
        """Published messages reach subscribed handlers."""
        received = []
        bus.subscribe(LayerSource.LAYER_6, lambda m: received.append(m))
        
        packet = MockPacket(PacketType.TASK_DIRECTIVE)
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_1,
            target_layer=LayerSource.LAYER_6,
            correlation_id=uuid4(),
        )
        
        delivered, failures = bus.publish(msg)
        assert LayerSource.LAYER_6 in delivered
        assert len(failures) == 0
        assert len(received) == 1


class TestBusMessageLog:
    """Tests for message logging and querying."""
    
    @pytest.fixture
    def bus(self):
        return create_northbound_bus()
    
    def test_messages_logged(self, bus):
        """Published messages are logged."""
        packet = MockPacket(PacketType.OBSERVATION)
        cid = uuid4()
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_6,
            target_layer=None,
            correlation_id=cid,
        )
        
        bus.publish(msg)
        
        messages = bus.get_messages()
        assert len(messages) == 1
        assert messages[0].correlation_id == cid
    
    def test_query_by_correlation_id(self, bus):
        """Query messages by correlation ID."""
        cid1 = uuid4()
        cid2 = uuid4()
        
        bus.publish(BusMessage(
            packet=MockPacket(PacketType.OBSERVATION),
            source_layer=LayerSource.LAYER_6,
            target_layer=None,
            correlation_id=cid1,
        ))
        bus.publish(BusMessage(
            packet=MockPacket(PacketType.TASK_RESULT),
            source_layer=LayerSource.LAYER_6,
            target_layer=None,
            correlation_id=cid2,
        ))
        
        messages = bus.get_messages(correlation_id=cid1)
        assert len(messages) == 1
        assert messages[0].correlation_id == cid1
    
    def test_query_by_source_layer(self, bus):
        """Query messages by source layer."""
        bus.publish(BusMessage(
            packet=MockPacket(PacketType.OBSERVATION),
            source_layer=LayerSource.LAYER_6,
            target_layer=None,
            correlation_id=uuid4(),
        ))
        bus.publish(BusMessage(
            packet=MockPacket(PacketType.DECISION),
            source_layer=LayerSource.LAYER_5,
            target_layer=None,
            correlation_id=uuid4(),
        ))
        
        messages = bus.get_messages(source_layer=LayerSource.LAYER_6)
        assert len(messages) == 1
        assert messages[0].source_layer == LayerSource.LAYER_6
    
    def test_query_by_packet_type(self, bus):
        """Query messages by packet type."""
        bus.publish(BusMessage(
            packet=MockPacket(PacketType.OBSERVATION),
            source_layer=LayerSource.LAYER_6,
            target_layer=None,
            correlation_id=uuid4(),
        ))
        bus.publish(BusMessage(
            packet=MockPacket(PacketType.DECISION),
            source_layer=LayerSource.LAYER_5,
            target_layer=None,
            correlation_id=uuid4(),
        ))
        
        messages = bus.get_messages(packet_type=PacketType.OBSERVATION)
        assert len(messages) == 1
        assert messages[0].packet_type == PacketType.OBSERVATION
    
    def test_query_multiple_filters(self, bus):
        """Query with multiple filters combines them."""
        cid = uuid4()
        bus.publish(BusMessage(
            packet=MockPacket(PacketType.OBSERVATION),
            source_layer=LayerSource.LAYER_6,
            target_layer=None,
            correlation_id=cid,
        ))
        bus.publish(BusMessage(
            packet=MockPacket(PacketType.OBSERVATION),
            source_layer=LayerSource.LAYER_5,
            target_layer=None,
            correlation_id=uuid4(),
        ))
        
        messages = bus.get_messages(
            correlation_id=cid,
            packet_type=PacketType.OBSERVATION
        )
        assert len(messages) == 1
        assert messages[0].correlation_id == cid
        assert messages[0].packet_type == PacketType.OBSERVATION
    
    def test_clear_log(self, bus):
        """clear_log removes all messages."""
        bus.publish(BusMessage(
            packet=MockPacket(PacketType.OBSERVATION),
            source_layer=LayerSource.LAYER_6,
            target_layer=None,
            correlation_id=uuid4(),
        ))
        
        assert len(bus.get_messages()) == 1
        bus.clear_log()
        assert len(bus.get_messages()) == 0


class TestBusErrorHandling:
    """Tests for bus error handling and resilience."""
    
    @pytest.fixture
    def bus(self):
        return create_northbound_bus()
    
    def test_handler_exception_doesnt_stop_delivery(self, bus):
        """Failing handler doesn't prevent delivery to other subscribers."""
        received_l5 = []
        received_l1 = []
        
        # L5 handler fails
        def failing_handler(msg):
            raise RuntimeError("Handler failed")
        
        bus.subscribe(LayerSource.LAYER_5, failing_handler)
        bus.subscribe(LayerSource.LAYER_1, lambda m: received_l1.append(m))
        
        packet = MockPacket(PacketType.OBSERVATION)
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_6,
            target_layer=None,  # Broadcast
            correlation_id=uuid4(),
        )
        
        delivered, failures = bus.publish(msg)
        
        # L1 should still receive despite L5 failure
        assert LayerSource.LAYER_1 in delivered
        assert len(received_l1) == 1
        
        # L5 failure should be recorded
        assert len(failures) == 1
        assert failures[0].layer == LayerSource.LAYER_5
        assert isinstance(failures[0].exception, RuntimeError)
    
    def test_multiple_handler_failures(self, bus):
        """Multiple failing handlers are all recorded."""
        def failing_handler_1(msg):
            raise ValueError("Error 1")
        
        def failing_handler_2(msg):
            raise TypeError("Error 2")
        
        bus.subscribe(LayerSource.LAYER_5, failing_handler_1)
        bus.subscribe(LayerSource.LAYER_4, failing_handler_2)
        
        packet = MockPacket(PacketType.OBSERVATION)
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_6,
            target_layer=None,  # Broadcast
            correlation_id=uuid4(),
        )
        
        delivered, failures = bus.publish(msg)
        
        assert len(failures) == 2
        assert failures[0].layer == LayerSource.LAYER_5
        assert failures[1].layer == LayerSource.LAYER_4
        assert isinstance(failures[0].exception, ValueError)
        assert isinstance(failures[1].exception, TypeError)
    
    def test_unsubscribe_removes_handler(self, bus):
        """Unsubscribed layers don't receive messages."""
        received = []
        bus.subscribe(LayerSource.LAYER_5, lambda m: received.append(m))
        bus.unsubscribe(LayerSource.LAYER_5)
        
        packet = MockPacket(PacketType.OBSERVATION)
        msg = BusMessage(
            packet=packet,
            source_layer=LayerSource.LAYER_6,
            target_layer=LayerSource.LAYER_5,
            correlation_id=uuid4(),
        )
        
        delivered, failures = bus.publish(msg)
        
        assert len(received) == 0
        assert LayerSource.LAYER_5 not in delivered


class TestLayerOrder:
    """Tests for LAYER_ORDER constant."""
    
    def test_layer_order_values(self):
        """LAYER_ORDER has correct hierarchy."""
        assert LAYER_ORDER[LayerSource.LAYER_1] == 1
        assert LAYER_ORDER[LayerSource.LAYER_2] == 2
        assert LAYER_ORDER[LayerSource.LAYER_3] == 3
        assert LAYER_ORDER[LayerSource.LAYER_4] == 4
        assert LAYER_ORDER[LayerSource.LAYER_5] == 5
        assert LAYER_ORDER[LayerSource.LAYER_6] == 6
        assert LAYER_ORDER[LayerSource.INTEGRITY] == 0
    
    def test_integrity_highest_priority(self):
        """Integrity has lowest order (highest priority)."""
        integrity_order = LAYER_ORDER[LayerSource.INTEGRITY]
        for layer, order in LAYER_ORDER.items():
            if layer != LayerSource.INTEGRITY:
                assert integrity_order < order
