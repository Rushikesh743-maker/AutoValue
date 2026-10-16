"""
Validator module checking records against the CanonicalCarListing contract.
"""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from pydantic import ValidationError
from ..schemas.canonical import CanonicalCarListing


@dataclass
class ValidationResult:
    """Outcome of validating a listing record."""
    is_valid: bool
    record: Optional[CanonicalCarListing] = None
    errors: Optional[List[str]] = None
    raw_input: Optional[Dict[str, Any]] = None


class ListingValidator:
    """
    Validates dictionary or raw objects against CanonicalCarListing schema rules.
    """

    def validate_record(self, data: Dict[str, Any]) -> ValidationResult:
        try:
            canonical = CanonicalCarListing(**data)
            return ValidationResult(
                is_valid=True,
                record=canonical,
                raw_input=data
            )
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            return ValidationResult(
                is_valid=False,
                errors=error_messages,
                raw_input=data
            )
        except Exception as ex:
            return ValidationResult(
                is_valid=False,
                errors=[str(ex)],
                raw_input=data
            )

    def validate_batch(self, records: List[Dict[str, Any]]) -> Tuple[List[CanonicalCarListing], List[ValidationResult]]:
        """
        Validates a collection of records, returning (valid_records, rejected_results).
        """
        valid_records: List[CanonicalCarListing] = []
        rejected: List[ValidationResult] = []

        for r in records:
            res = self.validate_record(r)
            if res.is_valid and res.record:
                valid_records.append(res.record)
            else:
                rejected.append(res)

        return valid_records, rejected
