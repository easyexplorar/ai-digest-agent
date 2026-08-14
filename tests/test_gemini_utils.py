import pytest

from gemini_utils import generate_content_with_retry


class _FakeModels:
    def __init__(self, fail_times, result="ok"):
        self.fail_times = fail_times
        self.result = result
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"transient failure {self.calls}")
        return self.result


class _FakeClient:
    def __init__(self, fail_times, result="ok"):
        self.models = _FakeModels(fail_times, result)


def test_succeeds_on_first_attempt(monkeypatch):
    monkeypatch.setattr("gemini_utils.time.sleep", lambda s: None)
    client = _FakeClient(fail_times=0, result="response")
    assert generate_content_with_retry(client) == "response"
    assert client.models.calls == 1


def test_retries_and_eventually_succeeds(monkeypatch):
    sleeps = []
    monkeypatch.setattr("gemini_utils.time.sleep", lambda s: sleeps.append(s))
    client = _FakeClient(fail_times=2, result="response")

    result = generate_content_with_retry(client, attempts=3, base_delay=1.0)

    assert result == "response"
    assert client.models.calls == 3
    assert sleeps == [1.0, 2.0]  # exponential backoff


def test_raises_after_exhausting_all_attempts(monkeypatch):
    monkeypatch.setattr("gemini_utils.time.sleep", lambda s: None)
    client = _FakeClient(fail_times=99)

    with pytest.raises(RuntimeError):
        generate_content_with_retry(client, attempts=3, base_delay=0.01)

    assert client.models.calls == 3
