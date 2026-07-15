"""Tests for cloud sink debug payload batch numbering."""

from __future__ import annotations

from jira_importer.import_pipeline.cloud.constants import BATCH_SIZE  # type: ignore[import-untyped]
from jira_importer.import_pipeline.sinks import cloud_sink  # type: ignore[import-untyped]


class _FakeClient:
    """Minimal client placeholder for batch tests."""


def test_create_issues_batch_uses_global_batch_sequence(monkeypatch) -> None:
    """Batch numbers should continue from the provided starting number."""
    seen_batch_numbers: list[int] = []

    def _fake_process_single_batch(
        _client,
        batch,
        _batch_context,
        batch_num,
        _debug_context,
        _issue_type,
        _context_suffix,
        *,
        submit: bool = True,
    ):
        del submit
        seen_batch_numbers.append(batch_num)
        return (len(batch), 0, [], [])

    monkeypatch.setattr(cloud_sink, "_process_single_batch", _fake_process_single_batch)

    issues = [(i, {"fields": {"summary": f"Issue {i}"}}) for i in range(BATCH_SIZE + 1)]
    result = cloud_sink._create_issues_batch(  # pylint: disable=protected-access
        _FakeClient(),
        issues,
        debug_context=cloud_sink.CloudDebugContext(),
        issue_type="test",
        start_batch_num=3,
    )

    assert seen_batch_numbers == [3, 4]
    assert result["batches"] == 2
    assert result["next_batch_num"] == 5


def test_process_single_batch_submit_false_writes_payload_without_post(tmp_path, monkeypatch) -> None:
    """submit=False writes debug JSON and must not call issue/bulk."""

    class _Client:
        def post(self, *_args, **_kwargs):
            raise AssertionError("issue/bulk must not be called when submit=False")

    written: list[int] = []

    def _fake_write(payload, batch_num, debug_context):
        del payload, debug_context
        written.append(batch_num)

    monkeypatch.setattr(cloud_sink, "_write_payload_debug", _fake_write)

    created, failed, errors, issues = cloud_sink._process_single_batch(  # pylint: disable=protected-access
        _Client(),
        [{"fields": {"summary": "A"}}],
        [(1, {"fields": {"summary": "A"}})],
        batch_num=1,
        debug_context=cloud_sink.CloudDebugContext(output_dir=tmp_path),
        issue_type="test",
        context_suffix="",
        submit=False,
    )

    assert written == [1]
    assert created == 0
    assert failed == 0
    assert errors == []
    assert issues == []


def test_write_payload_debug_prefixes_input_stem(tmp_path) -> None:
    """Debug payload file should include input file stem prefix when provided."""
    payload = {"issueUpdates": []}
    debug_context = cloud_sink.CloudDebugContext(output_dir=tmp_path, input_file_stem="super_dataset22")
    written = cloud_sink._write_payload_debug(  # pylint: disable=protected-access
        payload, batch_num=1, debug_context=debug_context
    )

    debug_file = tmp_path / "super_dataset22_cloud_payload_batch_001.json"
    assert debug_file.exists()
    assert written is not None
    assert written == debug_file.resolve()
    assert debug_context.written_files == [debug_file.resolve()]
