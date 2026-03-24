"""Service package exports are intentionally lazy.

Importing concrete services at package import time pulls in optional platform
dependencies such as GTK and zeroconf. Keep this module lightweight so the
cross-platform desktop host can import `aurynk.services.*` on Windows without
requiring Linux-only stacks.
"""

__all__ = []
