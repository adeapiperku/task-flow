"""
Domain validators for the task flow application.

This module contains reusable validation logic that can be used across
different domain models and services.
"""
from typing import Any, Dict, Optional, TypeVar, Generic, Type
from enum import Enum
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationError(Exception):
    """Raised when a validation fails."""
    message: str
    field: Optional[str] = None
    code: Optional[str] = None


class ConditionOperator(str, Enum):
    """Supported condition operators for rule evaluation."""
    EQUALS = "eq"
    NOT_EQUALS = "neq"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    CONTAINS = "contains"
    STARTS_WITH = "startswith"
    ENDS_WITH = "endswith"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    NOT_NULL = "not_null"


def evaluate_condition(
    field: str,
    operator: str,
    expected_value: Any,
    context: Dict[str, Any]
) -> bool:
    """
    Evaluate a condition against a context dictionary.

    Args:
        field: The field name to evaluate in the context
        operator: The comparison operator to use
        expected_value: The expected value to compare against
        context: The context dictionary containing field values

    Returns:
        bool: True if the condition is met, False otherwise

    Raises:
        ValueError: If the operator is not supported
    """
    value = context.get(field)
    
    try:
        if operator == ConditionOperator.EQUALS:
            return value == expected_value
        elif operator == ConditionOperator.NOT_EQUALS:
            return value != expected_value
        elif operator == ConditionOperator.GREATER_THAN:
            return value > expected_value
        elif operator == ConditionOperator.LESS_THAN:
            return value < expected_value
        elif operator == ConditionOperator.CONTAINS:
            return expected_value in value if value is not None else False
        elif operator == ConditionOperator.STARTS_WITH:
            return value.startswith(expected_value) if value is not None else False
        elif operator == ConditionOperator.ENDS_WITH:
            return value.endswith(expected_value) if value is not None else False
        elif operator == ConditionOperator.IN:
            return value in expected_value if value is not None else False
        elif operator == ConditionOperator.NOT_IN:
            return value not in expected_value if value is not None else True
        elif operator == ConditionOperator.IS_NULL:
            return value is None
        elif operator == ConditionOperator.NOT_NULL:
            return value is not None
        else:
            raise ValueError(f"Unsupported operator: {operator}")
    except (TypeError, AttributeError) as e:
        # Handle type errors during comparison
        return False


def validate_not_empty(value: Any, field_name: str) -> None:
    """Validate that a value is not empty.
    
    Args:
        value: The value to validate
        field_name: The name of the field being validated (for error messages)
        
    Raises:
        ValidationError: If the value is empty
    """
    if not value:
        raise ValidationError(
            f"{field_name} cannot be empty",
            field=field_name,
            code="empty_field"
        )


def validate_max_length(value: str, max_length: int, field_name: str) -> None:
    """Validate that a string does not exceed the maximum length.
    
    Args:
        value: The string to validate
        max_length: The maximum allowed length
        field_name: The name of the field being validated
        
    Raises:
        ValidationError: If the string exceeds the maximum length
    """
    if value and len(value) > max_length:
        raise ValidationError(
            f"{field_name} cannot be longer than {max_length} characters",
            field=field_name,
            code="max_length_exceeded"
        )


def validate_in_enum(value: Any, enum_class: Type[Enum], field_name: str) -> None:
    """Validate that a value is a valid enum member.
    
    Args:
        value: The value to validate
        enum_class: The enum class to validate against
        field_name: The name of the field being validated
        
    Raises:
        ValidationError: If the value is not a valid enum member
    """
    try:
        enum_class(value)
    except ValueError:
        valid_values = [e.value for e in enum_class]
        raise ValidationError(
            f"Invalid value for {field_name}. Must be one of: {', '.join(valid_values)}",
            field=field_name,
            code="invalid_enum_value"
        )
