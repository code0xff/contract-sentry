from __future__ import annotations

from unittest.mock import patch

from app.core.compile_check import check_compilation_with_fallback, resolve_missing_imports_by_basename


def test_resolve_missing_imports_by_basename_uses_unique_match() -> None:
    files = {
        "src/Main.sol": 'import "@vendor/Dep.sol";',
        "deps/Dep.sol": "contract Dep {}",
    }

    result = resolve_missing_imports_by_basename(files, ["@vendor/Dep.sol"])

    assert result["files"]["@vendor/Dep.sol"] == "contract Dep {}"
    assert result["auto_resolved"] == [
        {
            "missing_path": "@vendor/Dep.sol",
            "matched_path": "deps/Dep.sol",
        }
    ]
    assert result["ambiguous"] == []


def test_resolve_missing_imports_by_basename_marks_ambiguous_matches() -> None:
    files = {
        "deps/v1/Dep.sol": "contract DepV1 {}",
        "deps/v2/Dep.sol": "contract DepV2 {}",
    }

    result = resolve_missing_imports_by_basename(files, ["@vendor/Dep.sol"])

    assert "@vendor/Dep.sol" not in result["files"]
    assert result["auto_resolved"] == []
    assert result["ambiguous"] == [
        {
            "missing_path": "@vendor/Dep.sol",
            "candidates": ["deps/v1/Dep.sol", "deps/v2/Dep.sol"],
        }
    ]


def test_check_compilation_with_fallback_recompiles_until_success() -> None:
    initial_files = {
        "src/Main.sol": 'import "@vendor/Dep.sol";\nimport "@vendor/Nested.sol";',
        "deps/Dep.sol": "contract Dep {}",
        "deps/Nested.sol": "contract Nested {}",
    }

    with patch(
        "app.core.compile_check.check_compilation",
        side_effect=[
            {"success": False, "missing": ["@vendor/Dep.sol"], "errors": []},
            {"success": False, "missing": ["@vendor/Nested.sol"], "errors": []},
            {"success": True, "missing": [], "errors": []},
        ],
    ) as check:
        result = check_compilation_with_fallback(initial_files, max_passes=3)

    assert check.call_count == 3
    assert result["success"] is True
    assert result["missing"] == []
    assert result["errors"] == []
    assert result["auto_resolved"] == [
        {
            "missing_path": "@vendor/Dep.sol",
            "matched_path": "deps/Dep.sol",
        },
        {
            "missing_path": "@vendor/Nested.sol",
            "matched_path": "deps/Nested.sol",
        },
    ]
    assert result["ambiguous"] == []
    assert result["files"]["@vendor/Dep.sol"] == "contract Dep {}"
    assert result["files"]["@vendor/Nested.sol"] == "contract Nested {}"
