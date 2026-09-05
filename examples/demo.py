from pathlib import Path

from aafp_commons.cli import main

raise SystemExit(main(["demo", str(Path("commons-data"))]))

