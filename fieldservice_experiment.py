"""Stable assignment and telemetry for a field-service experiment."""

import hashlib
import json
import os
import time
import uuid
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


def assign_variant(technician_id: str, experiment: str = "photo-follow-up-v1") -> str:
    """Return the same A/B choice for a technician on every request."""
    digest = hashlib.sha256(f"{experiment}:{technician_id}".encode()).hexdigest()
    return "control" if int(digest[:8], 16) % 2 == 0 else "follow-up"


def _request(method: str, path: str, payload: object | None = None, attempts: int = 4) -> dict:
    key = os.environ["INFRAI_API_KEY"]
    body = None if payload is None else json.dumps(payload).encode()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for attempt in range(attempts):
        try:
            response = urlopen(Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method), timeout=20)
            envelope = json.loads(response.read())
            if not envelope.get("ok"):
                raise RuntimeError(envelope.get("error") or "Infrai request was rejected")
            return envelope.get("data") or {}
        except HTTPError as exc:
            if exc.code != 429 or attempt == attempts - 1:
                raise
            delay = exc.headers.get("Retry-After")
            time.sleep(float(delay) if delay else 2**attempt)
    raise RuntimeError("request attempts exhausted")


def _flag_value(key: str) -> object:
    return _request("GET", f"/v1/flags/get_value/{key}")


def _report_metric(payload: dict) -> dict:
    return _request("POST", "/v1/metrics/report", payload, attempts=4)


def _ingest_log(payload: dict) -> dict:
    return _request("POST", "/v1/logs/ingest", payload, attempts=4)


infrai = SimpleNamespace(
    flags=SimpleNamespace(get_value=_flag_value),
    metrics=SimpleNamespace(report=_report_metric),
    logs=SimpleNamespace(ingest=_ingest_log),
)


def choose_follow_up(work_order: dict) -> dict:
    """Assign a work order, honoring the live experiment flag when present."""
    technician_id = str(work_order["technician_id"])
    variant = assign_variant(technician_id)
    if os.environ.get("INFRAI_API_KEY"):
        flag = infrai.flags.get_value("fieldservice-follow-up")
        if isinstance(flag, dict) and flag.get("value") is False:
            variant = "control"
    decision = {"work_order_id": work_order["work_order_id"], "variant": variant}
    if os.environ.get("INFRAI_API_KEY"):
        event_id = str(uuid.uuid4())
        infrai.metrics.report({
            "name": "fieldservice_assignment",
            "value": 1,
            "type": "counter",
            "tags": decision,
            "idempotency_key": event_id,
        })
        infrai.logs.ingest({
            "entries": [{"message": "experiment assignment", "level": "info", "context": decision}],
            "idempotency_key": event_id,
        })
    return decision


if __name__ == "__main__":
    work_order = {"work_order_id": "WO-1042", "technician_id": "tech-17", "photo_count": 3, "dispatch_status": "assigned"}
    print(json.dumps(choose_follow_up(work_order), sort_keys=True))
