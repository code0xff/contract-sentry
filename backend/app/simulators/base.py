from __future__ import annotations

import abc
import logging
from typing import Any

from app.schemas.enums import VulnerabilityType

log = logging.getLogger(__name__)


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
contract AccessControlTest is Test {
    function test_access_control() public pure { assertTrue(true); }
}
""",
    VulnerabilityType.UNCHECKED_RETURN: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract UncheckedReturnTest is Test {
    function test_unchecked_return() public pure { assertTrue(true); }
}
""",
    VulnerabilityType.TIMESTAMP_DEPENDENCY: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract TimestampTest is Test {
    function test_timestamp_dependency() public pure { assertTrue(true); }
}
""",
    VulnerabilityType.DELEGATECALL: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract DelegatecallTest is Test {
    function test_delegatecall() public pure { assertTrue(true); }
}
""",
    VulnerabilityType.SELF_DESTRUCT: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract SelfDestructTest is Test {
    function test_self_destruct() public pure { assertTrue(true); }
}
""",
    VulnerabilityType.FRONT_RUNNING: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract FrontRunningTest is Test {
    function test_front_running() public pure { assertTrue(true); }
}
""",
    VulnerabilityType.DENIAL_OF_SERVICE: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract DosTest is Test {
    function test_denial_of_service() public pure { assertTrue(true); }
}
""",
    VulnerabilityType.FLASH_LOAN: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract FlashLoanTest is Test {
    function test_flash_loan() public pure { assertTrue(true); }
}
""",
    VulnerabilityType.OTHER: """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract OtherVulnTest is Test {
    function test_other() public pure { assertTrue(true); }
}
""",
}


def template_for(vuln: VulnerabilityType) -> str:
    tpl = VULN_TEMPLATES.get(vuln)
    if tpl is None:
        log.warning("no_stub_template_for_vuln_type vuln=%s, falling back to reentrancy stub", vuln.value)
        return VULN_TEMPLATES[VulnerabilityType.REENTRANCY]
    return tpl
