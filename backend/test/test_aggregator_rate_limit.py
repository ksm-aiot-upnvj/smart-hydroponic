import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from unittest.mock import patch, AsyncMock

from utils.aggregator import HydroponicAggregator


def _find_call(mock, **expected_kwargs):
    """Return the first recorded call whose kwargs match all expected_kwargs
    (substring match for string values), or None if not found."""
    for call in mock.await_args_list:
        kwargs = call.kwargs
        match = True
        for key, expected in expected_kwargs.items():
            actual = kwargs.get(key, "")
            if isinstance(expected, str) and isinstance(actual, str):
                if expected.lower() not in actual.lower():
                    match = False
                    break
            elif actual != expected:
                match = False
                break
        if match:
            return call
    return None


@pytest.mark.asyncio
async def test_rate_limit_drops_fast_repeats():
    agg = HydroponicAggregator(min_interval=0.2, timeout=60.0)

    with patch("utils.aggregator._best_effort_log", new_callable=AsyncMock) as mock_log:
        first = await agg.gather_data("plant", {"moisture1": 1})
        second = await agg.gather_data("plant", {"moisture1": 2})  # too soon

        assert first is True
        assert second is False

        await asyncio.sleep(0.05)

        match = _find_call(mock_log, event_type="system", description="rate-limit")
        assert match is not None, (
            f"expected a rate-limit log call; got calls: {mock_log.await_args_list}"
        )


@pytest.mark.asyncio
async def test_rate_limit_allows_after_interval():
    agg = HydroponicAggregator(min_interval=0.05, timeout=60.0)

    assert await agg.gather_data("plant", {"moisture1": 1}) is True
    await asyncio.sleep(0.1)  # widened margin over min_interval for stability
    assert await agg.gather_data("plant", {"moisture1": 2}) is True


@pytest.mark.asyncio
async def test_drop_log_throttling_suppresses_repeats():
    agg = HydroponicAggregator(min_interval=1.0, timeout=60.0)

    with patch("utils.aggregator._best_effort_log", new_callable=AsyncMock) as mock_log:
        first = await agg.gather_data("plant", {"moisture1": 1})
        assert first is True  # this one is buffered, not dropped

        results = []
        for i in range(5):
            results.append(await agg.gather_data("plant", {"moisture1": i}))

        assert results == [False, False, False, False, False], (
            f"expected all 5 rapid calls to be rate-limit-dropped, got: {results}"
        )

        await asyncio.sleep(0.05)

        rate_limit_calls = [
            c
            for c in mock_log.await_args_list
            if "rate-limit" in c.kwargs.get("description", "").lower()
        ]
        assert len(rate_limit_calls) == 1, (
            f"expected exactly 1 throttled rate-limit log, got {len(rate_limit_calls)}: "
            f"{mock_log.await_args_list}"
        )


@pytest.mark.asyncio
async def test_ring_buffer_overflow_logs_error_severity():
    agg = HydroponicAggregator(min_interval=0.0, ring_size=2, timeout=60.0)

    with patch("utils.aggregator._best_effort_log", new_callable=AsyncMock) as mock_log:
        for i in range(4):  # overflow the ring_size=2 buffer
            await agg.gather_data("plant", {"moisture1": i})

        await asyncio.sleep(0.05)

        match = _find_call(mock_log, severity="error", description="ring buffer")
        assert match is not None, (
            f"expected a ring-buffer-overflow error log; got calls: {mock_log.await_args_list}"
        )


@pytest.mark.asyncio
async def test_queue_full_logs_critical_severity():
    agg = HydroponicAggregator(min_interval=0.0, queue_maxsize=1, timeout=999.0)

    with patch("utils.aggregator._best_effort_log", new_callable=AsyncMock) as mock_log:
        for i in range(5):
            await agg.gather_data("plant", {"moisture1": i})
            await agg.gather_data("environment", {"temperature_atas": 20 + i})

        await asyncio.sleep(0.05)

        match = _find_call(mock_log, severity="critical", description="queue full")
        assert match is not None, (
            f"expected a queue-full critical log; got calls: {mock_log.await_args_list}"
        )


@pytest.mark.asyncio
async def test_stale_pair_timeout_drops_and_logs():
    agg = HydroponicAggregator(min_interval=0.0, timeout=0.05)

    with patch("utils.aggregator._best_effort_log", new_callable=AsyncMock) as mock_log:
        await agg.gather_data("plant", {"moisture1": 1})
        await asyncio.sleep(0.1)  # exceed pairing timeout
        await agg.gather_data("environment", {"temperature_atas": 25})

        await asyncio.sleep(0.05)

        assert agg.process_queue.empty(), (
            "expected no snapshot to be enqueued after a stale-pair drop, "
            f"but process_queue has {agg.process_queue.qsize()} item(s)"
        )

        match = _find_call(mock_log, description="stale")
        assert match is not None, (
            f"expected a stale-pair log entry; got calls: {mock_log.await_args_list}"
        )
