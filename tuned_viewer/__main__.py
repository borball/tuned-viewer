"""
Entry point for running tuned-viewer as a module.

Usage: python -m tuned_viewer [command] [args]
"""

from .cli import main

if __name__ == '__main__':
    exit(main())