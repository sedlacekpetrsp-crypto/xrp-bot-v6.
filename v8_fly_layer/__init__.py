import importlib.util
import pathlib
import sys

# A package directory takes precedence over the legacy v8_fly_layer.py module.
# Load that legacy module under a private name, re-export its public API, then
# wrap install() so the no-flip exit patch is guaranteed to be active.
_legacy_path = pathlib.Path(__file__).resolve().parent.parent / "v8_fly_layer.py"
_spec = importlib.util.spec_from_file_location("_v8_fly_layer_legacy", _legacy_path)
_legacy = importlib.util.module_from_spec(_spec)
sys.modules["_v8_fly_layer_legacy"] = _legacy
_spec.loader.exec_module(_legacy)

for _name, _value in _legacy.__dict__.items():
    if not _name.startswith("__"):
        globals()[_name] = _value

_original_install = _legacy.install


def install(module):
    _original_install(module)
    from v8_fly_no_flip import patch as _no_flip_patch
    _no_flip_patch(module)
    print("V8_NO_FLIP_INSTALL_ACTIVE", getattr(module, "FLY_LAYER_BUILD", None), flush=True)
