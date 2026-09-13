from models.schemas import AuditRecord


def create_audit_record(record: AuditRecord) -> AuditRecord:
    if record.status == "VERIFIED":
        record.evidence = [
            f"Source: {record.source_document}, row {record.source_row}" + (f", page {record.source_page}" if record.source_page else ""),
            f"Activity: {record.activity}; scope: {record.scope}",
            f"Factor source: {record.factor_source}",
            f"Factor provenance: {record.factor_source_url}; year {record.factor_year}; region {record.factor_region}; type {record.factor_type}",
        ]
    return record