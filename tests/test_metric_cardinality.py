from dataclasses import fields

from app.observability.metrics import Metrics


FORBIDDEN_LABELS = {
    "request_id",
    "telegram_user_id",
    "telegram_chat_id",
    "username",
    "invoice_id",
    "path",
    "url",
}


def test_metric_labels_are_bounded_operational_dimensions() -> None:
    metrics = Metrics.create()
    for field in fields(metrics):
        value = getattr(metrics, field.name)
        labelnames = set(getattr(value, "_labelnames", ()))
        assert labelnames.isdisjoint(FORBIDDEN_LABELS)
