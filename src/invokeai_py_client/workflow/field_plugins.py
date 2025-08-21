"""Field input type detection & construction plugin system.

Overview
========
This module provides an open / closed (extensible without modification) plugin
architecture for discovering and constructing strongly typed workflow input
fields. It replaces legacy hard‑coded ``if/elif`` heuristics with:

1. A prioritized rule registry (``register_detection_rule``) for mapping
   raw node/field metadata to a *field type identifier*.
2. A field builder registry (``register_field_builder``) for turning a detected
   type + metadata + raw value into a concrete ``IvkField`` instance.
3. A thin pluggy hook layer (namespace ``invokeai_fields``) so external
   distributions can inject alternative strategies or override core logic.

Design Goals
------------
* **Open for extension**: New field kinds can be added by *registering* rules &
  builders—no edits to this source file required.
* **Deterministic precedence**: Lower numeric priority executes first.
* **Composable**: Multiple orthogonal detection heuristics cooperate instead of
  one monolithic function.
* **Safe fallback**: Unknown types degrade to string (unless strict mode).
* **Debug visibility**: Opt‑in verbose tracing via ``INVOKEAI_FIELD_DEBUG=1``.
* **Strict validation**: ``INVOKEAI_STRICT_FIELDS=1`` raises on any unresolved
  type or failed builder.

Basic Usage Example
-------------------
Register a custom "seed" integer field and a new hypothetical "guidance" float
type exposed via a custom name pattern:

.. code-block:: python

    from invokeai_py_client.workflow.field_plugins import (
        register_detection_rule, register_field_builder, IvkIntegerField, IvkFloatField
    )

    # 1. Detection rules (lower priority number = earlier evaluation)
    register_detection_rule(
        'integer',
        predicate=lambda node_type, field_name, field_info: field_name == 'seed',
        priority=8,
        name='seed_field'
    )

    register_detection_rule(
        'guidance',
        predicate=lambda node_type, field_name, field_info: field_name == 'guidance_scale',
        priority=15,
        name='guidance_scale_field'
    )

    # 2. Builder for new custom type
    register_field_builder(
        'guidance',
        builder=lambda value, info: IvkFloatField(value=float(value) if value is not None else None,
                                                  minimum=info.get('minimum'), maximum=info.get('maximum'))
    )

    # That's it—workflows containing those fields will now produce typed
    # IvkIntegerField / IvkFloatField instances without modifying core code.

Environment Flags
-----------------
``INVOKEAI_FIELD_DEBUG=1``  -> verbose tracing & warnings.
``INVOKEAI_STRICT_FIELDS=1`` -> raise instead of silently falling back.

Hook Specs
----------
``detect_field_type(node_type, field_name, field_info) -> str | None``
    Return a field type identifier or ``None`` if undecided.
``build_field(field_type, value, field_info) -> IvkField | None``
    Return a constructed field instance or ``None`` to allow fallback.

Fallback Behavior
-----------------
If no detection rule nor plugin identifies a type, ``string`` is assumed (unless
strict). If a builder is missing and strict is enabled an exception is raised.
Otherwise a conservative ``IvkStringField`` is emitted.
"""
from __future__ import annotations

from typing import Any, Optional, Protocol, Callable, Union
import os
import logging
from copy import deepcopy
import pluggy

from invokeai_py_client.ivk_fields import (
    IvkField,
    IvkStringField,
    IvkIntegerField,
    IvkFloatField,
    IvkBooleanField,
    IvkEnumField,
)
from invokeai_py_client.ivk_fields.models import IvkModelIdentifierField
from invokeai_py_client.ivk_fields.resources import IvkBoardField, IvkImageField
from invokeai_py_client.dnn_model.dnn_model_types import BaseDnnModelType, DnnModelType

hookspec = pluggy.HookspecMarker("invokeai_fields")
hookimpl = pluggy.HookimplMarker("invokeai_fields")

# Logger & env flags (cached for perf)
logger = logging.getLogger(__name__)
FIELD_DEBUG = bool(os.getenv("INVOKEAI_FIELD_DEBUG"))
STRICT_FIELDS = bool(os.getenv("INVOKEAI_STRICT_FIELDS"))

# --- Dynamic rule & builder registries (for Open/Closed extensibility) ---
# These allow adding new field types without modifying CoreFieldPlugin code.
FieldTypeProvider = Callable[[str, str, dict[str, Any]], str]

class DetectionRule:
    """Prioritized detection rule entry.

    Attributes
    ----------
    field_type : str | Callable
        Static identifier or provider function.
    predicate : DetectionPredicate
        Match function returning True when rule applies.
    priority : int
        Ordering key (lower = earlier evaluation).
    name : str
        Friendly diagnostic label.
    dynamic : bool
        True when ``field_type`` is a callable provider.
    """
    __slots__ = ("field_type", "predicate", "priority", "name", "dynamic")

    def __init__(self, field_type: Union[str, FieldTypeProvider], predicate: DetectionPredicate, priority: int = 100, name: str | None = None) -> None:
        """Create a rule.

        Parameters
        ----------
        field_type : str | Callable
            Static field type string or callable provider returning a string.
        predicate : DetectionPredicate
            Function deciding whether this rule matches the target field.
        priority : int, default 100
            Lower numbers are evaluated earlier (higher precedence).
        name : str, optional
            Friendly identifier for diagnostics (defaults to predicate name).
        """
        self.field_type = field_type
        self.predicate = predicate
        self.priority = priority
        pred_name = getattr(predicate, '__name__', predicate.__class__.__name__)
        self.name = name or pred_name
        self.dynamic = callable(field_type)

class DetectionPredicate(Protocol):  # pragma: no cover - structural typing helper
    def __call__(self, node_type: str, field_name: str, field_info: dict[str, Any]) -> bool: ...

_dynamic_detection_rules: list[DetectionRule] = []
_dynamic_field_builders: dict[str, FieldBuilder] = {}

class FieldBuilder(Protocol):  # pragma: no cover
    def __call__(self, value: Any, field_info: dict[str, Any]) -> IvkField[Any]: ...

def register_detection_rule(field_type: Union[str, FieldTypeProvider], predicate: DetectionPredicate, *, priority: int = 100, name: str | None = None, first: bool | None = None) -> None:
    """Register a dynamic detection rule.

    Parameters
    ----------
    field_type : str | Callable[[str, str, dict], str]
        Either a static field type identifier or a callable provider (dynamic
        resolver) returning one. Using a callable lets a single rule surface
        multiple related types if needed.
    predicate : DetectionPredicate
        Returns ``True`` when the rule applies.
    priority : int, default 100
        Lower values execute earlier (higher precedence). Stable sort preserves
        insertion order among equal priorities.
    name : str, optional
        Friendly label for debugging output.
    first : bool, optional
        Deprecated shortcut; when ``True`` forces ``priority=0``.

    Notes
    -----
    Rules are evaluated before any built‑in heuristics (because the built‑ins
    are themselves simply pre‑registered rules). Re-registering allows simple
    override by using a smaller priority.
    """
    if first:
        priority = 0
    rule = DetectionRule(field_type, predicate, priority, name)
    _dynamic_detection_rules.append(rule)
    # Keep rules sorted by priority
    _dynamic_detection_rules.sort(key=lambda r: r.priority)
    if FIELD_DEBUG:
        logger.debug(f"Registered detection rule '{rule.name}' for type '{field_type}' (priority {priority})")

def register_field_builder(field_type: str, builder: FieldBuilder, *, override: bool = True) -> None:
    """Register a builder for a field type.

    Parameters
    ----------
    field_type : str
        Identifier produced by detection rules.
    builder : Callable[[Any, dict], IvkField]
        Function creating and returning a concrete ``IvkField``.
    override : bool, default True
        When ``False`` keep the existing builder if already present.

    Notes
    -----
    Builders run after detection. A failing builder (exception) logs a warning
    in debug mode and triggers strict failure if ``INVOKEAI_STRICT_FIELDS`` is
    set.
    """
    if not override and field_type in _dynamic_field_builders:
        return
    _dynamic_field_builders[field_type] = builder
    if FIELD_DEBUG:
        logger.debug(f"Registered field builder for type '{field_type}' (override={override})")


class FieldPluginSpec:
    """Hook specifications for detection & construction.

    Implementations are registered with the pluggy manager under namespace
    ``invokeai_fields``. Using ``firstresult=True`` ensures the first non-None
    implementation short‑circuits further processing for the hook call.
    """

    @hookspec(firstresult=True)
    def detect_field_type(self, node_type: str, field_name: str, field_info: dict[str, Any]) -> Optional[str]:  # pragma: no cover - interface
        """Return field type identifier if recognized (else None)."""

    @hookspec(firstresult=True)
    def build_field(self, field_type: str, value: Any, field_info: dict[str, Any]) -> Optional[IvkField[Any]]:  # pragma: no cover - interface
        """Return constructed IvkField instance for field_type (or None)."""


class CoreFieldPlugin:
    """Core implementation delegating to dynamic registries.

    Detection relies only on the ordered ``_dynamic_detection_rules`` list,
    eliminating hard-coded conditional logic. Building consults the dynamic
    builder map (``_dynamic_field_builders``). This class acts as a bridge
    between the pluggy hook API and the registry primitives, keeping the
    public extension surface minimal & stable.
    """

    @hookimpl
    def detect_field_type(self, node_type: str, field_name: str, field_info: dict[str, Any]) -> Optional[str]:
        """Detect a field type via registered rules.

        Parameters
        ----------
        node_type : str
            Raw workflow node type string.
        field_name : str
            Name of the input field on the node.
        field_info : dict
            The field's metadata dictionary (schema fragment) including
            optional ``value`` and constraints.

        Returns
        -------
        str | None
            Detected field type identifier or ``None`` if no rule matches.
        """
        if FIELD_DEBUG:
            logger.debug(f"Detecting field type: node={node_type}, field={field_name}, info_keys={list(field_info.keys())}")
        for rule in _dynamic_detection_rules:
            try:
                if rule.predicate(node_type, field_name, field_info):
                    resolved = rule.field_type(node_type, field_name, field_info) if rule.dynamic else rule.field_type  # type: ignore[arg-type]
                    if FIELD_DEBUG:
                        logger.debug(f"Rule '{rule.name}' matched -> type '{resolved}' (dynamic={rule.dynamic})")
                    return str(resolved)
            except Exception as e:  # pragma: no cover
                if FIELD_DEBUG:
                    logger.warning(f"Detection rule '{rule.name}' raised {e!r}; continuing")
        if FIELD_DEBUG:
            logger.debug(f"No detection rule matched field: node={node_type}, field={field_name}")
        return None
    
    def _has_integer_constraints(self, field_info: dict[str, Any]) -> bool:
        """Return True if numeric constraints imply an integer domain.

        Parameters
        ----------
        field_info : dict
            Field metadata containing possible constraint keys.

        Returns
        -------
        bool
            ``True`` when constraints (``multiple_of=1`` or integer min/max)
            strongly indicate an integer space.
        """
        # Check for multiple_of constraint
        if "multiple_of" in field_info:
            multiple = field_info["multiple_of"]
            if isinstance(multiple, (int, float)) and multiple == 1:
                return True
        
        # Check if min/max are integers
        minimum = field_info.get("minimum")
        maximum = field_info.get("maximum")
        
        if minimum is not None and maximum is not None:
            if isinstance(minimum, int) and isinstance(maximum, int):
                return True
            # Check for integer-like float bounds
            if isinstance(minimum, float) and isinstance(maximum, float):
                if minimum.is_integer() and maximum.is_integer():
                    return True
        
        return False

    def _normalize_enum_choices(self, field_info: dict[str, Any]) -> list[Any]:
        """Extract a normalized flat list of enum choice values.

        Parameters
        ----------
        field_info : dict
            Field metadata potentially containing ``options`` or ``ui_choices``.

        Returns
        -------
        list
            Ordered list of primitive choice values.
        """
        choices = field_info.get("options", []) or field_info.get("ui_choices", [])
        if isinstance(choices, list):
            norm: list[Any] = []
            for c in choices:
                if isinstance(c, dict) and "value" in c:
                    norm.append(c["value"])
                else:
                    norm.append(c)
            return norm
        return list(choices) if choices else []

    @hookimpl
    def build_field(self, field_type: str, value: Any, field_info: dict[str, Any]) -> Optional[IvkField[Any]]:
        """Construct an ``IvkField`` via the builder registry.

        Parameters
        ----------
        field_type : str
            Previously detected field type identifier.
        value : Any
            Raw value supplied by the workflow schema.
        field_info : dict
            Field metadata used for constraints or validation.

        Returns
        -------
        IvkField | None
            Concrete field instance or ``None`` to allow fallback processing.
        """
        # Deep copy mutable values to ensure immutability
        if isinstance(value, (dict, list)):
            value = deepcopy(value)
        if FIELD_DEBUG:
            logger.debug(f"Building field via registry: type={field_type}, value_type={type(value).__name__}")
        builder = _dynamic_field_builders.get(field_type)
        if builder is not None:
            try:
                return builder(value, field_info)
            except Exception as e:  # pragma: no cover
                if FIELD_DEBUG:
                    logger.warning(f"Builder for type '{field_type}' failed: {e!r}")
                if STRICT_FIELDS:
                    raise
        if STRICT_FIELDS:
            raise ValueError(f"Unknown field type '{field_type}' (strict mode enabled)")
        return None


_pm: pluggy.PluginManager | None = None


def get_field_plugin_manager() -> pluggy.PluginManager:
    """Return (lazily create) the global pluggy plugin manager.

    Returns
    -------
    pluggy.PluginManager
        Configured manager with core plugin registered and entry points loaded.
    """
    global _pm
    if _pm is None:
        pm = pluggy.PluginManager("invokeai_fields")
        pm.add_hookspecs(FieldPluginSpec)
        pm.register(CoreFieldPlugin())
        # Entry point loading (external extensions can register under group name)
        try:  # pragma: no cover - environment dependent
            pm.load_setuptools_entrypoints("invokeai_fields")
        except Exception:
            pass
        _pm = pm
    return _pm


# --- Core rule registration (executed at import time) ---
def _register_core_detection_rules() -> None:
    """Register the built‑in detection heuristics as prioritized rules.

    Notes
    -----
    Executed exactly once at import; users may override by inserting new rules
    with lower priority values or by resetting the manager & registries.
    """
    # Priority guide (lower runs earlier):
    # 0: explicit type
    # 10: field name patterns
    # 20: node primitive types
    # 30-40: value-based
    # 50: enum heuristics
    # 60: numeric constraints fallback

    # Explicit type hint (dynamic resolver) supports arbitrary external types
    register_detection_rule(
        lambda node_type, field_name, field_info: str(field_info["type"]),  # field_type provider
        predicate=lambda node_type, field_name, field_info: "type" in field_info,
        priority=0,
        name="explicit_type_hint",
    )

    # Field name patterns
    register_detection_rule("board", lambda node_type, field_name, field_info: field_name == "board", priority=10, name="field_name_board")
    register_detection_rule("model", lambda node_type, field_name, field_info: field_name == "model" or field_name.endswith("_model"), priority=10, name="field_name_model")
    register_detection_rule("image", lambda node_type, field_name, field_info: field_name == "image", priority=10, name="field_name_image")
    register_detection_rule("enum", lambda node_type, field_name, field_info: field_name == "scheduler", priority=10, name="field_name_scheduler")

    # Node primitive types
    register_detection_rule("string", lambda node_type, field_name, field_info: node_type == "string", priority=20, name="node_primitive_string")
    register_detection_rule("integer", lambda node_type, field_name, field_info: node_type == "integer", priority=20, name="node_primitive_integer")
    register_detection_rule("float", lambda node_type, field_name, field_info: node_type in {"float", "float_math"}, priority=20, name="node_primitive_float")
    register_detection_rule("boolean", lambda node_type, field_name, field_info: node_type == "boolean", priority=20, name="node_primitive_boolean")

    # Value-based
    register_detection_rule("boolean", lambda node_type, field_name, field_info: isinstance(field_info.get("value"), bool), priority=30, name="value_is_bool")
    # Integer detection from value + constraints
    def _value_is_integer(node_type: str, field_name: str, field_info: dict[str, Any]) -> bool:
        v = field_info.get("value")
        if isinstance(v, int) and not isinstance(v, bool):
            return True
        if isinstance(v, float) and v.is_integer():
            # reuse heuristic: numeric constraints imply integer
            return any(k in field_info for k in ("minimum", "maximum", "multiple_of"))
        return False
    register_detection_rule("integer", _value_is_integer, priority=31, name="value_is_integer_like")
    register_detection_rule("float", lambda node_type, field_name, field_info: isinstance(field_info.get("value"), float), priority=32, name="value_is_float")
    register_detection_rule("model", lambda node_type, field_name, field_info: isinstance(field_info.get("value"), dict) and ("key" in field_info["value"] or ("name" in field_info["value"] and "type" in field_info["value"])), priority=35, name="value_is_model_dict")
    register_detection_rule("board", lambda node_type, field_name, field_info: isinstance(field_info.get("value"), dict) and "board_id" in field_info["value"], priority=37, name="value_is_board_dict")
    register_detection_rule("string", lambda node_type, field_name, field_info: isinstance(field_info.get("value"), str), priority=40, name="value_is_string")

    # Enum heuristics
    register_detection_rule("enum", lambda node_type, field_name, field_info: "options" in field_info or "ui_choices" in field_info, priority=50, name="enum_choices_present")

    # Numeric constraints fallback (attempt integer then float)
    def _numeric_constraints_integer(node_type: str, field_name: str, field_info: dict[str, Any]) -> bool:
        if not any(k in field_info for k in ("minimum", "maximum")):
            return False
        mn, mx = field_info.get("minimum"), field_info.get("maximum")
        return isinstance(mn, int) and isinstance(mx, int)
    register_detection_rule("integer", _numeric_constraints_integer, priority=60, name="numeric_constraints_integer")
    register_detection_rule("float", lambda node_type, field_name, field_info: any(k in field_info for k in ("minimum", "maximum")), priority=61, name="numeric_constraints_float")

_register_core_detection_rules()


# ---------------- Core field builders registration -----------------
def _normalize_enum_choices(field_info: dict[str, Any]) -> list[Any]:
    """Top-level helper for enum choice normalization used by enum builder.

    Parameters
    ----------
    field_info : dict
        Metadata possibly containing ``options`` or ``ui_choices``.

    Returns
    -------
    list
        Flat list of concrete values suitable for ``IvkEnumField``.
    """
    choices = field_info.get("options", []) or field_info.get("ui_choices", [])
    if isinstance(choices, list):
        out: list[Any] = []
        for c in choices:
            if isinstance(c, dict) and "value" in c:
                out.append(c["value"])
            else:
                out.append(c)
        return out
    return list(choices) if choices else []


def _builder_string(value: Any, field_info: dict[str, Any]) -> IvkField[Any]:
    """Core string field builder.

    Coerces primitive numeric / boolean types to ``str`` while leaving existing
    string or ``None`` values untouched.
    """
    return IvkStringField(value=str(value) if isinstance(value, (int, float, bool)) else value)


def _builder_integer(value: Any, field_info: dict[str, Any]) -> IvkField[Any]:
    """Core integer field builder with safe float coercion.

    Coerces integer-like floats and enforces ``None`` when coercion not viable.
    Honors optional ``minimum`` / ``maximum`` constraints.
    """
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    int_value: int | None
    if isinstance(value, int) and not isinstance(value, bool):
        int_value = value
    elif value is None:
        int_value = None
    else:
        int_value = int(value) if isinstance(value, float) and value.is_integer() else None
    return IvkIntegerField(value=int_value, minimum=field_info.get("minimum"), maximum=field_info.get("maximum"))


def _builder_float(value: Any, field_info: dict[str, Any]) -> IvkField[Any]:
    """Core float field builder honoring min/max constraints."""
    return IvkFloatField(value=value, minimum=field_info.get("minimum"), maximum=field_info.get("maximum"))


def _builder_boolean(value: Any, field_info: dict[str, Any]) -> IvkField[Any]:
    """Core boolean builder with lenient truthy coercion for non-bool primitives."""
    return IvkBooleanField(value=bool(value) if not isinstance(value, bool) and value is not None else value)


def _builder_model(value: Any, field_info: dict[str, Any]) -> IvkField[Any]:
    """Core model identifier builder.

    Provides defensive defaults and warns (debug mode) when both ``key`` and
    ``name`` are absent.
    """
    if isinstance(value, dict):
        if not value.get("key") and not value.get("name") and FIELD_DEBUG:
            logger.warning(f"Model field missing key and name: {field_info}")
        return IvkModelIdentifierField(
            key=value.get("key", ""),
            hash=value.get("hash", ""),
            name=value.get("name", ""),
            base=value.get("base", "any"),
            type=value.get("type", "main"),
            submodel_type=value.get("submodel_type"),
        )
    return IvkModelIdentifierField(
        key="",
        hash="",
        name=str(value) if value else "",
        base=BaseDnnModelType.Any,
        type=DnnModelType.Main,
    )


def _builder_board(value: Any, field_info: dict[str, Any]) -> IvkField[Any]:
    """Core board field builder extracting ``board_id`` from dict values."""
    if isinstance(value, dict):
        return IvkBoardField(value=value.get("board_id"))
    return IvkBoardField(value=value)


def _builder_image(value: Any, field_info: dict[str, Any]) -> IvkField[Any]:
    """Core image field builder with proper dict handling.

    Accepts:
    - dict: {"image_name": "..."} -> extracts string
    - str or None: passes through
    - other primitives: coerces to string
    """
    if isinstance(value, dict):
        image_name = value.get("image_name")
        if image_name is None and FIELD_DEBUG:
            logger.warning(f"Image field missing image_name key; got {value!r}")
        return IvkImageField(value=image_name)
    if value is None or isinstance(value, str):
        return IvkImageField(value=value)
    # Last‑resort coercion to keep behavior predictable and avoid builder failure
    try:
        return IvkImageField(value=str(value))
    except Exception:
        return IvkImageField(value=None)


def _builder_enum(value: Any, field_info: dict[str, Any]) -> IvkField[Any]:
    """Core enum builder applying normalized choices list."""
    return IvkEnumField(value=value, choices=_normalize_enum_choices(field_info))


def _register_core_field_builders() -> None:
    """Register the standard builders for core primitive & structured types."""
    register_field_builder("string", _builder_string)
    register_field_builder("integer", _builder_integer)
    register_field_builder("float", _builder_float)
    register_field_builder("boolean", _builder_boolean)
    register_field_builder("model", _builder_model)
    register_field_builder("board", _builder_board)
    register_field_builder("image", _builder_image)
    register_field_builder("enum", _builder_enum)


_register_core_field_builders()


def reset_field_plugin_manager() -> None:
    """Reset the global plugin manager (test / dynamic reconfiguration helper)."""
    global _pm
    _pm = None


def register_field_plugin(plugin: object, *, first: bool = False) -> None:
    """Register a *pluggy* style plugin object.

    Parameters
    ----------
    plugin : object
        Instance implementing one or both hook specs.
    first : bool, default False
        When ``True`` the plugin is placed ahead of existing ones, giving it
        higher precedence for hook resolution.
    """
    global _pm
    if _pm is None:
        get_field_plugin_manager()
    assert _pm is not None
    if not first:
        _pm.register(plugin)
        return
    # Rebuild manager with new plugin first while preserving others
    existing = list(_pm.get_plugins())
    pm = pluggy.PluginManager("invokeai_fields")
    pm.add_hookspecs(FieldPluginSpec)
    pm.register(plugin)
    for p in existing:
        if p is plugin:
            continue
        pm.register(p)
    _pm = pm


def detect_field_type(node_type: str, field_name: str, field_info: dict[str, Any]) -> str:
    """Public helper to detect a field type using the plugin manager.

    Parameters
    ----------
    node_type : str
        Node's declared type.
    field_name : str
        The input field name.
    field_info : dict
        Field metadata dictionary.

    Returns
    -------
    str
        Detected field type or ``"string"`` fallback.
    """
    pm = get_field_plugin_manager()
    result = pm.hook.detect_field_type(node_type=node_type, field_name=field_name, field_info=field_info)
    if result is None:
        if STRICT_FIELDS:
            raise ValueError(
                f"Unknown field type (strict): node={node_type}, field={field_name}, info_keys={list(field_info.keys())}"
            )
        if FIELD_DEBUG:
            logger.debug(
                f"No plugin detected field type for: node={node_type}, field={field_name}; falling back to 'string'"
            )
        return "string"  # fallback
    return str(result)


def build_field(node_data: dict[str, Any], field_name: str, field_info: dict[str, Any]) -> IvkField[Any]:
    """High-level convenience builder (detect + construct).

    Parameters
    ----------
    node_data : dict
        The node's ``data`` block (or full node dict containing ``type`` key).
    field_name : str
        Name of the input field to build.
    field_info : dict
        Field metadata (schema fragment) containing optional ``value``.

    Returns
    -------
    IvkField
        Concrete field instance (string fallback if unresolved & non-strict).
    """
    pm = get_field_plugin_manager()
    
    # First detect the field type
    node_type = node_data.get("type", "")
    field_type = detect_field_type(node_type, field_name, field_info)
    
    # Then build the field
    value = field_info.get("value")
    fld = pm.hook.build_field(field_type=field_type, value=value, field_info=field_info)
    if fld is not None:
        return fld  # type: ignore[no-any-return]
    
    # Fallback safety with warning
    if FIELD_DEBUG:
        logger.debug(f"No plugin could build field type '{field_type}', falling back to string")
    
    # Deep copy value if mutable
    if isinstance(value, (dict, list)):
        value = deepcopy(value)
    
    str_value: str | None
    if isinstance(value, str) or value is None:
        str_value = value
    else:
        # Coerce simple primitives to string for fallback clarity
        if isinstance(value, (int, float, bool)):
            str_value = str(value)
        else:
            str_value = None
    return IvkStringField(value=str_value)
