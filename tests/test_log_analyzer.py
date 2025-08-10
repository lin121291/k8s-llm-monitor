import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.monitor.log_analyzer import LogAnalyzer, LogEntry, Anomaly
from src.monitor.config import Config


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def log_analyzer(config):
    return LogAnalyzer(config)


@pytest.fixture
def sample_logs():
    return [
        LogEntry(
            timestamp=datetime.now(),
            level="ERROR",
            service="api-gateway",
            message="Connection timeout to database",
            metadata={"request_id": "123", "user_id": "456"},
        ),
        LogEntry(
            timestamp=datetime.now(),
            level="WARNING",
            service="api-gateway",
            message="High response time detected",
            metadata={"response_time": 5000},
        ),
        LogEntry(
            timestamp=datetime.now(),
            level="INFO",
            service="user-service",
            message="User login successful",
            metadata={"user_id": "456"},
        ),
    ]


class TestLogAnalyzer:
    @pytest.mark.asyncio
    async def test_initialization(self, log_analyzer):
        assert log_analyzer.config is not None
        assert log_analyzer.anomaly_prompt is not None

    @pytest.mark.asyncio
    async def test_format_logs_for_analysis(self, log_analyzer, sample_logs):
        formatted = log_analyzer._format_logs_for_analysis(sample_logs)

        assert "ERROR" in formatted
        assert "api-gateway" in formatted
        assert "Connection timeout" in formatted

    def test_extract_primary_service(self, log_analyzer, sample_logs):
        primary_service = log_analyzer._extract_primary_service(sample_logs)
        assert primary_service == "api-gateway"

    @pytest.mark.asyncio
    async def test_analyze_log_batch_with_mock_llm(self, log_analyzer, sample_logs):
        # Mock the entire _analyze_log_batch method to avoid LLM complications
        from src.monitor.log_analyzer import Anomaly

        expected_anomaly = Anomaly(
            service="api-gateway",
            severity="high",
            description="Database connection issues detected",
            confidence=0.8,
            timestamp=sample_logs[0].timestamp,
            context={"action": "check_database_connectivity"},
        )

        async def mock_analyze_batch(logs):
            return [expected_anomaly]

        with patch.object(
            log_analyzer, "_analyze_log_batch", side_effect=mock_analyze_batch
        ):
            anomalies = await log_analyzer._analyze_log_batch(sample_logs)

            assert len(anomalies) == 1
            assert anomalies[0].severity == "high"
            assert anomalies[0].service == "api-gateway"
            assert anomalies[0].confidence == 0.8

    @pytest.mark.asyncio
    async def test_get_service_context_without_redis(self, log_analyzer, sample_logs):
        # Test when Redis is not available
        context = await log_analyzer._get_service_context(sample_logs)
        assert context == "No additional context"

    @pytest.mark.asyncio
    async def test_publish_anomaly(self, log_analyzer):
        anomaly = Anomaly(
            timestamp=datetime.now(),
            service="test-service",
            severity="medium",
            description="Test anomaly",
            confidence=0.7,
            context={"test": "data"},
        )

        # Mock Kafka producer and Redis client
        log_analyzer.kafka_producer = Mock()
        log_analyzer.redis_client = AsyncMock()

        await log_analyzer.publish_anomaly(anomaly)

        log_analyzer.kafka_producer.send.assert_called_once()
        log_analyzer.redis_client.setex.assert_called_once()


class TestLogEntry:
    def test_log_entry_creation(self):
        log_entry = LogEntry(
            timestamp=datetime.now(),
            level="INFO",
            service="test-service",
            message="Test message",
            metadata={"key": "value"},
        )

        assert log_entry.level == "INFO"
        assert log_entry.service == "test-service"
        assert log_entry.message == "Test message"
        assert log_entry.metadata["key"] == "value"


class TestAnomaly:
    def test_anomaly_creation(self):
        anomaly = Anomaly(
            timestamp=datetime.now(),
            service="test-service",
            severity="high",
            description="Test anomaly",
            confidence=0.9,
            context={"action": "investigate"},
        )

        assert anomaly.service == "test-service"
        assert anomaly.severity == "high"
        assert anomaly.confidence == 0.9
