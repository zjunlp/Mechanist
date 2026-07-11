---
name: automatic-circuit-discovery
description: >
  Activates when working on mechanistic interpretability of transformers, specifically for automated circuit
  discovery in transformer models using computational graph editing and analysis.
---

## Demo Scripts

### `scripts/acdc_run_demo.py`

```python
#!/usr/bin/env python3
"""
Simple runnable script demonstrating how to run the main ACDC pipeline programmatically.

This script shows how to import and execute the main function in the ACDC library,
which runs the automated circuit discovery for a default configuration.

Requires:
    - Python 3.8+ environment with the Automatic-Circuit-Discovery repo installed via Poetry
    - System dependencies (graphviz, etc.) installed per instructions

Usage:
    python scripts/acdc_run_demo.py
"""

import sys
import os
import argparse
from acdc import main as acdc_main_module

def main():
    """
    Runs the main ACDC experiment pipeline, simulating the command line interface call.
    Prints progress and handles basic errors.
    """

    try:
        # The main.py in acdc offers a CLI main function, here we call directly
        # It can take command-line like arguments, but defaults should run a demo
        # For example: python acdc/main.py --help for CLI instructions

        # We run it with no additional args to start the default pipeline/demo
        print("Starting ACDC main pipeline demo run...")
        sys.argv = ['acdc/main.py']  # Reset argv for main.py
        acdc_main_module.main()
        print("ACDC main pipeline finished successfully.")

    except Exception as e:
        print(f"Error running ACDC main pipeline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```
