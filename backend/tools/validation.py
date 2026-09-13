from models.schemas import AuditRecord


def validate_record(record: AuditRecord) -> AuditRecord:
    if record.quantity < 0:
        record.status = "NEEDS_REVIEW"
        record.message = "Quantity cannot be negative."
    if record.factor is not None and record.factor < 0:
        record.status = "NEEDS_REVIEW"
        record.message = "Emission factor cannot be negative."
    return record