from __future__ import annotations

FORBIDDEN_CHARS = set('[]:\\/^|#*"<>')  # MKD Title ID Protocol
MD_GLOB = "**/*.md"

YAML_FM_DELIM = "---"
FOOTER_SPLIT_TITLE = "# ============="
DEPS_TITLE = "# Dependencies"
END_TITLE = "# End"

# Reasonable defaults
DEFAULT_CATEGORY = "artifact"
DEFAULT_TYPE = "note"
DEFAULT_BASE_VERSION = 1