#!/usr/bin/env python3
"""
Output Validation System for MCP Agent

This module provides intelligent output validation that can detect errors
and validate expected behavior without relying on exact string matches.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationResult(Enum):
    """Validation result types."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    UNKNOWN = "unknown"


@dataclass
class ValidationRule:
    """A validation rule for checking output."""
    name: str
    expected_patterns: List[str]  # Patterns that should be present
    error_patterns: List[str]     # Patterns that indicate errors
    warning_patterns: List[str]   # Patterns that indicate warnings
    required_elements: List[str]  # Elements that must be present
    forbidden_elements: List[str] # Elements that should not be present


class OutputValidator:
    """
    Intelligent output validator that can detect errors and validate
    expected behavior without exact string matching.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ai_showmaker.output_validator")
        self.validation_rules = self._initialize_validation_rules()
    
    def _initialize_validation_rules(self) -> Dict[str, ValidationRule]:
        """Initialize validation rules for different command types."""
        return {
            "directory_creation": ValidationRule(
                name="Directory Creation",
                expected_patterns=[
                    r"created", r"mkdir", r"directory", r"success", r"exit code: 0"
                ],
                error_patterns=[
                    r"error", r"failed", r"permission denied", r"already exists",
                    r"no such file", r"cannot create", r"exit code: [1-9]"
                ],
                warning_patterns=[
                    r"warning", r"already exists", r"directory exists"
                ],
                required_elements=[],
                forbidden_elements=[]
            ),
            "directory_listing": ValidationRule(
                name="Directory Listing",
                expected_patterns=[
                    r"ls", r"directory", r"contents", r"files", r"directories",
                    r"total", r"drwx", r"-rwx", r"\.", r"\.\.", r"exit code: 0"
                ],
                error_patterns=[
                    r"error", r"failed", r"no such file", r"permission denied",
                    r"cannot access", r"exit code: [1-9]"
                ],
                warning_patterns=[
                    r"warning", r"cannot read", r"access denied"
                ],
                required_elements=[],
                forbidden_elements=[]
            ),
            "file_creation": ValidationRule(
                name="File Creation",
                expected_patterns=[
                    r"created", r"touch", r"file", r"success", r"exit code: 0",
                    r"write", r"saved"
                ],
                error_patterns=[
                    r"error", r"failed", r"permission denied", r"cannot create",
                    r"no space left", r"exit code: [1-9]"
                ],
                warning_patterns=[
                    r"warning", r"already exists", r"overwrite"
                ],
                required_elements=[],
                forbidden_elements=[]
            ),
            "command_execution": ValidationRule(
                name="Command Execution",
                expected_patterns=[
                    r"executed", r"success", r"exit code: 0", r"completed"
                ],
                error_patterns=[
                    r"error", r"failed", r"command not found", r"permission denied",
                    r"exit code: [1-9]", r"cannot execute"
                ],
                warning_patterns=[
                    r"warning", r"deprecated", r"obsolete"
                ],
                required_elements=[],
                forbidden_elements=[]
            ),
            "file_reading": ValidationRule(
                name="File Reading",
                expected_patterns=[
                    r"read", r"content", r"file", r"success", r"exit code: 0"
                ],
                error_patterns=[
                    r"error", r"failed", r"no such file", r"permission denied",
                    r"cannot read", r"exit code: [1-9]"
                ],
                warning_patterns=[
                    r"warning", r"empty file", r"binary file"
                ],
                required_elements=[],
                forbidden_elements=[]
            )
        }
    
    def validate_output(self, output: str, command_type: str, context: Dict[str, Any] = None) -> Tuple[ValidationResult, str, Dict[str, Any]]:
        """
        Validate command output and return validation result.
        
        Args:
            output: The command output to validate
            command_type: Type of command (e.g., "directory_creation", "file_reading")
            context: Additional context (e.g., expected file name, directory path)
        
        Returns:
            Tuple of (ValidationResult, message, details)
        """
        if command_type not in self.validation_rules:
            return ValidationResult.UNKNOWN, "Unknown command type", {}
        
        rule = self.validation_rules[command_type]
        output_lower = output.lower()
        
        # Check for error patterns first
        for pattern in rule.error_patterns:
            if re.search(pattern, output_lower, re.IGNORECASE):
                return ValidationResult.ERROR, f"Error detected: {pattern}", {
                    "matched_pattern": pattern,
                    "output_snippet": self._extract_context(output, pattern)
                }
        
        # Check for warning patterns
        warnings = []
        for pattern in rule.warning_patterns:
            if re.search(pattern, output_lower, re.IGNORECASE):
                warnings.append(pattern)
        
        # Check for expected patterns
        expected_matches = []
        for pattern in rule.expected_patterns:
            if re.search(pattern, output_lower, re.IGNORECASE):
                expected_matches.append(pattern)
        
        # Validate context-specific requirements
        context_validation = self._validate_context(output, context, command_type)
        
        # Determine overall result
        if context_validation.get("has_error", False):
            return ValidationResult.ERROR, context_validation["message"], context_validation
        
        if warnings:
            return ValidationResult.WARNING, f"Warnings detected: {', '.join(warnings)}", {
                "warnings": warnings,
                "expected_matches": expected_matches,
                "context_validation": context_validation
            }
        
        if expected_matches:
            return ValidationResult.SUCCESS, f"Validation successful. Expected patterns found: {', '.join(expected_matches)}", {
                "expected_matches": expected_matches,
                "context_validation": context_validation
            }
        
        return ValidationResult.UNKNOWN, "No clear validation patterns found", {
            "context_validation": context_validation
        }
    
    def _validate_context(self, output: str, context: Dict[str, Any], command_type: str) -> Dict[str, Any]:
        """Validate output against specific context requirements."""
        if not context:
            return {"has_error": False}
        
        output_lower = output.lower()
        errors = []
        warnings = []
        
        # Check for expected file/directory names
        if "expected_name" in context:
            expected_name = context["expected_name"].lower()
            if expected_name not in output_lower:
                errors.append(f"Expected '{expected_name}' not found in output")
        
        # Check for expected content
        if "expected_content" in context:
            expected_content = context["expected_content"].lower()
            if expected_content not in output_lower:
                errors.append(f"Expected content not found in output")
        
        # Check for forbidden content
        if "forbidden_content" in context:
            forbidden_content = context["forbidden_content"].lower()
            if forbidden_content in output_lower:
                errors.append(f"Forbidden content '{forbidden_content}' found in output")
        
        # Check for exit codes
        exit_code_match = re.search(r"exit code: (\d+)", output_lower)
        if exit_code_match:
            exit_code = int(exit_code_match.group(1))
            if exit_code != 0:
                errors.append(f"Command failed with exit code {exit_code}")
        
        # Check for empty output when content is expected
        if command_type in ["file_reading", "directory_listing"] and not output.strip():
            warnings.append("Empty output received")
        
        return {
            "has_error": len(errors) > 0,
            "has_warning": len(warnings) > 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _extract_context(self, output: str, pattern: str, context_lines: int = 2) -> str:
        """Extract context around a matched pattern."""
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                return '\n'.join(lines[start:end])
        return output[:200] + "..." if len(output) > 200 else output
    
    def validate_directory_creation(self, output: str, directory_name: str = None) -> Tuple[ValidationResult, str, Dict[str, Any]]:
        """Validate directory creation output."""
        context = {"expected_name": directory_name} if directory_name else None
        return self.validate_output(output, "directory_creation", context)
    
    def validate_directory_listing(self, output: str, expected_items: List[str] = None) -> Tuple[ValidationResult, str, Dict[str, Any]]:
        """Validate directory listing output."""
        context = {"expected_content": ", ".join(expected_items)} if expected_items else None
        return self.validate_output(output, "directory_listing", context)
    
    def validate_file_creation(self, output: str, file_name: str = None) -> Tuple[ValidationResult, str, Dict[str, Any]]:
        """Validate file creation output."""
        context = {"expected_name": file_name} if file_name else None
        return self.validate_output(output, "file_creation", context)
    
    def validate_command_execution(self, output: str) -> Tuple[ValidationResult, str, Dict[str, Any]]:
        """Validate general command execution output."""
        return self.validate_output(output, "command_execution")
    
    def validate_file_reading(self, output: str, expected_content: str = None) -> Tuple[ValidationResult, str, Dict[str, Any]]:
        """Validate file reading output."""
        context = {"expected_content": expected_content} if expected_content else None
        return self.validate_output(output, "file_reading", context)
