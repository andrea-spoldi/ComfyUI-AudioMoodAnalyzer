from .analyzer_nodes import NODE_CLASS_MAPPINGS as _A, NODE_DISPLAY_NAME_MAPPINGS as _DA
from .mood_json_nodes import NODE_CLASS_MAPPINGS as _B, NODE_DISPLAY_NAME_MAPPINGS as _DB
from .formatter_nodes import NODE_CLASS_MAPPINGS as _C, NODE_DISPLAY_NAME_MAPPINGS as _DC
from .clap_node import NODE_CLASS_MAPPINGS as _D, NODE_DISPLAY_NAME_MAPPINGS as _DD
from .composition_node import NODE_CLASS_MAPPINGS as _E, NODE_DISPLAY_NAME_MAPPINGS as _DE

NODE_CLASS_MAPPINGS = {**_A, **_B, **_C, **_D, **_E}
NODE_DISPLAY_NAME_MAPPINGS = {**_DA, **_DB, **_DC, **_DD, **_DE}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
