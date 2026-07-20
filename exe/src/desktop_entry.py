"""Native bundle entry point for the AtonixCorp developer toolchain."""
import sys

from atonixcorpcli.main import main as cli_main
from atonixcorp_toolbox.main import main as toolbox_main


if len(sys.argv) > 1 and sys.argv[1] == "toolbox":
    sys.argv.pop(1)
    toolbox_main()
else:
    cli_main()
