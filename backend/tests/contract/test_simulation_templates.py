from __future__ import annotations

from app.simulators.foundry_simulator import DEFI_TEMPLATES


def test_templates_have_required_keys():
    for name, tpl in DEFI_TEMPLATES.items():
        assert "description" in tpl, f"template {name!r} missing 'description'"
        assert "scaffold" in tpl, f"template {name!r} missing 'scaffold'"


def test_known_templates_present():
    assert "flash_loan" in DEFI_TEMPLATES
    assert "reentrancy" in DEFI_TEMPLATES
