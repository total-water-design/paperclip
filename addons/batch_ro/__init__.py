"""Total RO Design Batch RO add-on."""
from .engine import calculate_batch_ro


def register_batch_ro(app, calculations) -> None:
    """Register the Batch RO calculation mode without changing conventional RO."""
    calculations["batch_ro"] = calculate_batch_ro


__all__ = ["calculate_batch_ro", "register_batch_ro"]
