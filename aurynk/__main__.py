"""Entry point for running aurynk as a module: python -m aurynk or as a script"""

import sys

from aurynk.launcher import main


if __name__ == "__main__":
    sys.exit(main(sys.argv))
