"""Tests for parsing functions in optimize.py."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from optimize import parse_run_log, extract_design_from_response, extract_description


class TestParseRunLog:
    def test_normal_output(self):
        log = (
            "---\n"
            "predicted_weight_g:     312.45\n"
            "total_harvest_kg:       7.81\n"
            "constraints_pass:       True\n"
        )
        weight, constraints = parse_run_log(log)
        assert weight == 312.45
        assert constraints == "pass"

    def test_constraints_fail(self):
        log = "predicted_weight_g:     100.0\nconstraints_pass:       False\n"
        weight, constraints = parse_run_log(log)
        assert weight == 100.0
        assert constraints == "fail"

    def test_empty_log(self):
        weight, constraints = parse_run_log("")
        assert weight == 0.0
        assert constraints == "fail"

    def test_malformed_weight(self):
        log = "predicted_weight_g:     not_a_number\nconstraints_pass:       True\n"
        weight, constraints = parse_run_log(log)
        assert weight == 0.0
        assert constraints == "pass"

    def test_missing_constraints_line(self):
        log = "predicted_weight_g:     250.0\n"
        weight, constraints = parse_run_log(log)
        assert weight == 250.0
        assert constraints == "fail"  # default


class TestExtractDesignFromResponse:
    def test_single_code_block(self):
        response = 'Some text\n```python\nPARAMS = {"x": 1}\n```\nMore text'
        result = extract_design_from_response(response)
        assert result == 'PARAMS = {"x": 1}'

    def test_multiple_code_blocks_takes_last(self):
        response = (
            "```python\nsnippet = 1\n```\n"
            "```python\nPARAMS = {\"full\": \"file\"}\n```"
        )
        result = extract_design_from_response(response)
        assert result == 'PARAMS = {"full": "file"}'

    def test_no_code_block(self):
        response = "Just some text without code blocks"
        result = extract_design_from_response(response)
        assert result is None

    def test_non_python_code_block(self):
        response = "```json\n{}\n```"
        result = extract_design_from_response(response)
        assert result is None


class TestExtractDescription:
    def test_normal_description(self):
        response = "REASONING: some reason\nDESCRIPTION: increased tank diameter"
        result = extract_description(response)
        assert result == "increased tank diameter"

    def test_sanitizes_tabs(self):
        response = "DESCRIPTION: change\twith\ttabs"
        result = extract_description(response)
        assert "\t" not in result

    def test_sanitizes_commas(self):
        response = "DESCRIPTION: change, with, commas"
        result = extract_description(response)
        assert "," not in result

    def test_missing_description(self):
        response = "REASONING: no description line here"
        result = extract_description(response)
        assert result == "AI-proposed design change"

    def test_empty_response(self):
        result = extract_description("")
        assert result == "AI-proposed design change"
