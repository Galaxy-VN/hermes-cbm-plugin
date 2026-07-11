"""Pytest configuration — makes the plugin importable as 'cbm'."""
import sys
import os
import types

# The plugin directory IS the cbm package when installed to ~/.hermes/plugins/cbm/.
# For local development, we register it as 'cbm' in sys.modules.
_plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if "cbm" not in sys.modules:
    cbm = types.ModuleType("cbm")
    cbm.__path__ = [_plugin_root]
    cbm.__file__ = os.path.join(_plugin_root, "__init__.py")
    cbm.__package__ = "cbm"
    sys.modules["cbm"] = cbm
