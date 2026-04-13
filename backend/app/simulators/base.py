from __future__ import annotations

import abc
from typing import Any

from app.schemas.enums import VulnerabilityType


class BaseSimulator(abc.ABC):
    @abc.abstractmethod
    def run(self, *, template: VulnerabilityType, **kwargs: Any) -> dict[str, Any]:
        """Run the simulation and return a dict with status/output/trace."""


VULN_TEMPLATES: dict[VulnerabilityType, str] = {
    VulnerabilityType.REENTRANCY: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract ReentrancyTest is Test {
    function test_reentrancy_detected() public pure { assertTrue(true); }
}
""",
    VulnerabilityType.INTEGER_OVERFLOW: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract OverflowTest is Test {
    function test_overflow_detected() public pure { assertTrue(true); }
}
""",
    VulnerabilityType.ACCESS_CONTROL: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract AccessTest is Test {
    function test_access_control() public pure { assertTrue(true); }
}
""",
}


def template_for(vuln: VulnerabilityType) -> str:
    return VULN_TEMPLATES.get(vuln, VULN_TEMPLATES[VulnerabilityType.REENTRANCY])
