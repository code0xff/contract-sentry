"""AI-powered attack campaign generator.

Generates a holistic attack plan + Foundry test suite targeting all
findings in a job. Uses Claude CLI (claude -p) directly.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil

from app.schemas.finding import FindingOut

logger = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 30_000
CLAUDE_TIMEOUT = 300  # seconds

CAMPAIGN_PROMPT = """\
You are a senior smart contract security researcher performing an adversarial red-team audit.

## Contract Under Audit

Name: {contract_name}

{contract_source_section}

## Findings from Static/Dynamic Analysis Tools

{findings_section}

## Your Task

1. Perform INDEPENDENT security analysis beyond the tool findings listed above.
   Consider: chained attacks combining multiple vulnerabilities, business-logic flaws
   the tools may have missed, and realistic exploit preconditions.

2. Design a comprehensive attack campaign covering all confirmed and AI-discovered issues.

3. Write a compilable Foundry test suite that:
   - Uses `pragma solidity ^0.8.20;` and `import "forge-std/Test.sol";`
   - Imports and DEPLOYS the target contract(s) in `setUp()` using `new ContractName(...)`
   - Has ONE `test_` function per attack scenario, named descriptively
     (e.g. `test_ReentrancyDrainsFunds`, `test_AccessControlBypassOwner`)
   - Uses forge-std cheatcodes: `vm.prank`, `vm.deal`, `vm.startPrank`, `vm.expectRevert`
   - ASSERTS exploit success with real state checks (e.g. `assertGt(attacker.balance, 0)`)
     NOT `assertTrue(true)` placeholders
   - If a finding is not exploitable, writes the test to verify it correctly reverts

Respond in this EXACT format — no text outside the tags:

<ATTACK_PLAN>
[Concise markdown (under 500 words):
1. **Confirmed Vulnerabilities** — one bullet per tool finding with exploit rationale
2. **AI-Discovered Issues** — additional issues found through independent analysis
3. **Chained Attacks** — if multiple vulns can be combined for greater impact
4. **Expected Outcomes** — what successful exploits achieve]
</ATTACK_PLAN>

<TEST_CODE>
[Complete Solidity test file — compilable with forge test -vvv]
</TEST_CODE>
"""


def _build_prompt(
    contract_name: str,
    contract_source: str | None,
    project_files: dict[str, str] | None,
    findings: list[FindingOut],
) -> str:
    # Contract source section
    if project_files:
        file_list = "\n".join(f"  - src/{p}" for p in sorted(project_files.keys()))
        # Include first few files' content (truncated)
        combined = ""
        for rel_path, content in sorted(project_files.items()):
            if len(combined) >= MAX_SOURCE_CHARS:
                break
            combined += f"\n// === {rel_path} ===\n{content}"
        if len(combined) > MAX_SOURCE_CHARS:
            combined = combined[:MAX_SOURCE_CHARS] + "\n// ... (truncated)"
        contract_source_section = (
            f"Multi-file project. Files available in test environment:\n{file_list}\n\n"
            f"Source contents:\n```solidity{combined}\n```"
        )
    elif contract_source:
        src = contract_source[:MAX_SOURCE_CHARS]
        if len(contract_source) > MAX_SOURCE_CHARS:
            src += "\n// ... (truncated)"
        contract_source_section = f"```solidity\n{src}\n```"
    else:
        contract_source_section = "(source not available — analyze based on findings only)"

    # Findings section
    if findings:
        lines = []
        for i, f in enumerate(findings, 1):
            lines.append(
                f"{i}. [{f.severity.upper()}] {f.title} ({f.vulnerability_type})\n"
                f"   Location: {f.location or 'N/A'}\n"
                f"   {f.description}"
            )
        findings_section = "\n\n".join(lines)
    else:
        findings_section = "No tool findings — perform independent security analysis."

    return CAMPAIGN_PROMPT.format(
        contract_name=contract_name,
        contract_source_section=contract_source_section,
        findings_section=findings_section,
    )


def _parse_response(raw: str) -> tuple[str, str]:
    plan_match = re.search(r"<ATTACK_PLAN>(.*?)</ATTACK_PLAN>", raw, re.DOTALL)
    code_match = re.search(r"<TEST_CODE>(.*?)</TEST_CODE>", raw, re.DOTALL)
    attack_plan = plan_match.group(1).strip() if plan_match else raw.strip()
    test_code = code_match.group(1).strip() if code_match else ""
    return attack_plan, test_code


async def _via_claude_cli(prompt: str) -> str:
    """Call `claude -p <prompt>` and return stdout."""
    cli = shutil.which("claude")
    if not cli:
        raise RuntimeError("claude CLI not found in PATH — install @anthropic-ai/claude-code")

    proc = await asyncio.create_subprocess_exec(
        cli, "-p", prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=CLAUDE_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"claude CLI timed out after {CLAUDE_TIMEOUT}s")

    if proc.returncode != 0:
        err = stderr.decode(errors="replace")[:500]
        raise RuntimeError(f"claude CLI exited {proc.returncode}: {err}")

    return stdout.decode(errors="replace").strip()


async def generate_campaign(
    job_id: str,
    contract_name: str,
    contract_source: str | None,
    project_files: dict[str, str] | None,
    findings: list[FindingOut],
) -> tuple[str, str]:
    """Return (attack_plan, test_code) generated by Claude CLI."""
    prompt = _build_prompt(contract_name, contract_source, project_files, findings)
    result = await _via_claude_cli(prompt)
    return _parse_response(result)
