"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Dynamic plugin registration system for DreamStudio languages.

A language plugin is one directory shaped like this:

    <plugin-id>/
        plugin.json
        keywords/<language>.json
        snippets/<language>.json
        provider.py
        vendor/
        bin/

``plugin.json`` is plain JSON:

    {
        "id": "python",
        "display_name": "Python",
        "minimum_studio_version": "1.0",
        "requires": [],
        "keywords": "keywords/python.json",
        "snippets": "snippets/python.json",
        "provider": {"file": "provider.py", "function": "create_provider"},
        "vendor": ["vendor"],
        "native_libraries": ["bin/library.so"]
    }

The IDE scans bundled, user-installed, and ``DS_PLUGIN_PATH`` plugin
directories. Copying and removing plugin directories is owned by the
external installer; this module only discovers, validates, loads, and
registers the plugins it finds.

This module is the only file in the plugin package that imports from
the editor core — it keeps provider code fully decoupled.
"""

from editor import *
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType

from editor.Ironica.language_engine import LanguageRegistry
from editor.utils.file_properties.outline import register_parser, unregister_parser
from editor.utils.notifications.notification_manager import get_notification_manager

logger = logging.getLogger(__name__)

STUDIO_VERSION = "1.0"
PLUGIN_MANIFEST_FILENAME = "plugin.json"
PLUGIN_PATH_ENVIRONMENT = "DS_PLUGIN_PATH"

# ------------------------------------------------------------------
# Path helpers
# ------------------------------------------------------------------


def _get_ironica_dir() -> str:
    try:
        from editor.utils.resource_path import resource_path as _rp

        return _rp(os.path.join("editor", "Ironica"))
    except Exception:
        return os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


_IRONICA_DIR = _get_ironica_dir()
_KEYWORDS_DIR = os.path.join(_IRONICA_DIR, "keywords")
_PLUGINS_PKG_DIR = os.path.dirname(__file__)

_DREAMSTUDIO_HOME = Path.home() / ".dreamstudio"
_USER_PLUGINS_DIR = _DREAMSTUDIO_HOME / "plugins" / "packages"
_PLUGINS_JSON_PATH = _DREAMSTUDIO_HOME / "plugins" / "plugins.json"

_PLUGINS_JSON_VERSION = 1


def _plugin_roots() -> list[str]:
    """Return plugin directories in precedence order.

    Returns:
        Explicit ``DS_PLUGIN_PATH`` directories first, then user-installed
        packages, then the bundled plugin package.
    """
    candidates = [
        candidate.strip()
        for candidate in os.environ.get(PLUGIN_PATH_ENVIRONMENT, "").split(os.pathsep)
        if candidate.strip()
    ]
    candidates.extend([str(_USER_PLUGINS_DIR), _PLUGINS_PKG_DIR])
    roots: list[str] = []
    for candidate in candidates:
        path = os.path.abspath(candidate)
        if path not in roots and os.path.isdir(path):
            roots.append(path)
    return roots


def _is_bundled_root(root: str) -> bool:
    """Return ``True`` when *root* is the bundled plugin package.

    Args:
        root: Directory path being checked.
    """
    return os.path.abspath(root) == os.path.abspath(_PLUGINS_PKG_DIR)


# ------------------------------------------------------------------
# Auto-discovery
# ------------------------------------------------------------------


def _scan_keywords() -> dict[str, str]:
    """Scan ``keywords/*.json`` and return ``{lang_name: relative_json_path}``.

    Paths are stored relative to the Ironica directory so that
    ``plugins.json`` is portable across machines and users.
    """
    result: dict[str, str] = {}
    kw_dir = Path(_KEYWORDS_DIR)
    if not kw_dir.is_dir():
        return result
    for json_file in sorted(kw_dir.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            lang = data.get("lang")
            if lang and isinstance(lang, str):
                result[lang] = os.path.relpath(json_file, _IRONICA_DIR)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping invalid keyword file %s: %s", json_file, exc)
    return result


def _is_plugin_directory(path: Path) -> bool:
    """Return ``True`` when *path* contains a plugin manifest or provider.

    Args:
        path: Directory being inspected.
    """
    return path.is_dir() and (
        (path / PLUGIN_MANIFEST_FILENAME).is_file() or (path / "provider.py").is_file()
    )


def _plugin_directories() -> list[Path]:
    """List plugin directories from every plugin root.

    A root can either be one plugin itself or a folder containing one
    plugin per subdirectory.

    Returns:
        Plugin directories in root-precedence order without duplicates.
    """
    directories: list[Path] = []
    seen: set[str] = set()
    for root in _plugin_roots():
        root_path = Path(root)
        if _is_plugin_directory(root_path):
            key = os.path.abspath(root_path)
            if key not in seen:
                seen.add(key)
                directories.append(root_path)
            continue
        if not root_path.is_dir():
            continue
        for child in sorted(root_path.iterdir()):
            if child.name.startswith((".", "_")):
                continue
            if not _is_plugin_directory(child):
                continue
            key = os.path.abspath(child)
            if key not in seen:
                seen.add(key)
                directories.append(child)
    return directories


def _read_plugin_manifest(plugin_dir: Path) -> dict[str, Any]:
    """Read a plugin manifest without raising on malformed input.

    Args:
        plugin_dir: Directory that may contain ``plugin.json``.

    Returns:
        The manifest dictionary, or an empty dictionary.
    """
    manifest_path = plugin_dir / PLUGIN_MANIFEST_FILENAME
    if not manifest_path.is_file():
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Skipping invalid plugin manifest %s: %s", manifest_path, exc)
        return {}
    if not isinstance(manifest, dict):
        logger.warning(
            "Skipping invalid plugin manifest %s: expected an object", manifest_path
        )
        return {}
    if not manifest:
        logger.warning(
            "Skipping invalid plugin manifest %s: manifest is empty", manifest_path
        )
        return {}
    return manifest


def _keyword_language_id(plugin_root: str, keywords_value: str, fallback: str) -> str:
    """Read the language identifier from a keyword config when available.

    Args:
        plugin_root: Plugin directory used for relative keyword paths.
        keywords_value: Keyword config path from the manifest.
        fallback: Identifier used when the keyword config cannot be read.
    """
    keywords_file = (
        keywords_value
        if os.path.isabs(keywords_value)
        else os.path.join(plugin_root, keywords_value)
    )
    try:
        with open(keywords_file, "r", encoding="utf-8") as handle:
            keywords = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return fallback
    lang = keywords.get("lang") if isinstance(keywords, dict) else None
    return lang if isinstance(lang, str) and lang else fallback


def _manifest_text(
    manifest: dict[str, Any],
    plugin_dir: Path,
    key: str,
    label: str,
    required: bool = True,
) -> Optional[str]:
    """Return validated manifest text, or ``None`` when invalid.

    Args:
        manifest: Parsed plugin manifest.
        plugin_dir: Directory containing ``plugin.json``.
        key: Manifest field name.
        label: Human-readable field name used in diagnostics.
        required: Whether an empty value is rejected.
    """
    value = manifest.get(key, "")
    if value == "" and not required:
        return ""
    if not isinstance(value, str) or not value:
        logger.warning("Skipping %s: %s must be text", plugin_dir, label)
        return None
    return value


def _manifest_list(
    manifest: dict[str, Any],
    plugin_dir: Path,
    key: str,
    label: str,
    item: str = "paths",
) -> Optional[list[str]]:
    """Return a validated list of manifest strings, or ``None`` when invalid.

    Args:
        manifest: Parsed plugin manifest.
        plugin_dir: Directory containing ``plugin.json``.
        key: Manifest field name.
        label: Human-readable field name used in diagnostics.
        item: Human-readable list-item name used in diagnostics.
    """
    value = manifest.get(key, [])
    if not isinstance(value, list) or any(
        not isinstance(entry, str) for entry in value
    ):
        logger.warning("Skipping %s: %s must be a list of %s", plugin_dir, label, item)
        return None
    return list(value)


def _manifest_language_spec(
    plugin_dir: Path, manifest: dict[str, Any]
) -> Optional[tuple[str, dict[str, Any]]]:
    """Convert an explicit manifest into one language specification.

    Args:
        plugin_dir: Directory containing ``plugin.json``.
        manifest: Parsed manifest dictionary.

    Returns:
        A ``(language, spec)`` tuple, or ``None`` when invalid.
    """
    if "id" in manifest:
        plugin_id = _manifest_text(manifest, plugin_dir, "id", "manifest id")
    else:
        plugin_id = plugin_dir.name
    keywords_value = _manifest_text(manifest, plugin_dir, "keywords", "keywords path")
    display_name = _manifest_text(
        manifest, plugin_dir, "display_name", "display name", required=False
    )
    snippets_value = _manifest_text(
        manifest, plugin_dir, "snippets", "snippets path", required=False
    )
    vendor = _manifest_list(manifest, plugin_dir, "vendor", "vendor")
    native_libraries = _manifest_list(
        manifest, plugin_dir, "native_libraries", "native libraries"
    )
    requires = _manifest_list(
        manifest, plugin_dir, "requires", "requirements", "plugin ids"
    )
    minimum_version = _manifest_text(
        manifest,
        plugin_dir,
        "minimum_studio_version",
        "minimum Studio version",
        required=False,
    )
    enabled = manifest.get("enabled", True)
    provider = manifest.get("provider")

    if (
        plugin_id is None
        or keywords_value is None
        or display_name is None
        or snippets_value is None
        or vendor is None
        or native_libraries is None
        or requires is None
        or minimum_version is None
    ):
        return None
    if "language" in manifest:
        lang = _manifest_text(manifest, plugin_dir, "language", "manifest language")
        if lang is None:
            return None
    else:
        lang = _keyword_language_id(
            os.path.abspath(plugin_dir), keywords_value, plugin_id
        )
    if not isinstance(lang, str) or not lang:
        logger.warning("Skipping %s: manifest language must be text", plugin_dir)
        return None
    if not isinstance(provider, dict):
        logger.warning("Skipping %s: provider must be an object", plugin_dir)
        return None
    if not isinstance(provider.get("file"), str) or not provider.get("file"):
        logger.warning("Skipping %s: provider file must be text", plugin_dir)
        return None
    if not isinstance(provider.get("function"), str) or not provider.get("function"):
        logger.warning("Skipping %s: provider function must be text", plugin_dir)
        return None
    if not isinstance(enabled, bool):
        logger.warning("Skipping %s: enabled must be true or false", plugin_dir)
        return None

    spec: dict[str, Any] = {
        "plugin": plugin_id,
        "root": os.path.abspath(plugin_dir),
        "keywords": keywords_value,
        "provider": {"file": provider["file"], "function": provider["function"]},
        "enabled": enabled,
    }
    if display_name:
        spec["display_name"] = display_name
    if manifest.get("snippets"):
        spec["snippets"] = manifest["snippets"]
    if minimum_version:
        spec["minimum_studio_version"] = minimum_version
    if requires:
        spec["requires"] = list(requires)
    if vendor:
        spec["vendor"] = list(vendor)
    if native_libraries:
        spec["native_libraries"] = list(native_libraries)
    return lang, spec


def _legacy_language_spec(
    plugin_dir: Path, bundled: bool, bundled_keywords: dict[str, str]
) -> Optional[tuple[str, dict[str, Any]]]:
    """Describe an older provider directory without a manifest.

    Args:
        plugin_dir: Directory containing ``provider.py``.
        bundled: Whether the directory lives in the bundled package.
        bundled_keywords: Bundled keyword configs by language.
    """
    provider_file = plugin_dir / "provider.py"
    if not provider_file.is_file():
        return None
    lang = plugin_dir.name
    if bundled:
        provider: Any = f"editor.Ironica.plugins.{lang}.provider.create_provider"
        spec: dict[str, Any] = {
            "plugin": lang,
            "root": _IRONICA_DIR,
            "provider": provider,
        }
        keywords = bundled_keywords.get(lang)
        if keywords:
            spec["keywords"] = keywords
        return lang, spec
    return (
        lang,
        {
            "plugin": lang,
            "root": os.path.abspath(plugin_dir),
            "provider": {"file": "provider.py", "function": "create_provider"},
        },
    )


def _conventional_snippet_file(plugin_root: str, lang: str) -> Optional[str]:
    """Find a snippet file using ordinary plugin-layout conventions.

    Args:
        plugin_root: Plugin directory containing an optional snippets folder.
        lang: Registered language identifier.
    """
    config = LanguageRegistry.get_config(lang) or {}
    extensions = config.get("extensions", [])
    candidates = [os.path.join(plugin_root, "snippets", f"{lang}.json")]
    for extension in extensions:
        name = str(extension).lstrip(".")
        if not name:
            continue
        candidates.append(os.path.join(plugin_root, "snippets", f"{name}.json"))
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def _discover_plugin_specs() -> dict[str, dict[str, Any]]:
    """Discover one specification per available language.

    Returns:
        Language specifications in root-precedence order.
    """
    specs: dict[str, dict[str, Any]] = {}
    bundled_keywords = _scan_keywords()

    for plugin_dir in _plugin_directories():
        if (plugin_dir / PLUGIN_MANIFEST_FILENAME).is_file():
            manifest = _read_plugin_manifest(plugin_dir)
            if not manifest:
                continue
            language_spec = _manifest_language_spec(plugin_dir, manifest)
        else:
            bundled = _is_bundled_root(os.path.dirname(os.path.abspath(plugin_dir)))
            language_spec = _legacy_language_spec(plugin_dir, bundled, bundled_keywords)
        if language_spec is None:
            continue
        lang, spec = language_spec
        if lang in specs:
            logger.warning("Duplicate language %r ignored in %s", lang, plugin_dir)
            continue
        specs[lang] = spec

    for lang, keywords in sorted(bundled_keywords.items()):
        if lang not in specs:
            specs[lang] = {"keywords": keywords, "root": _IRONICA_DIR}
    return specs


def _auto_discover() -> dict[str, Any]:
    """Build a plugins config dict by scanning the filesystem.

    Returns:
        A dict with ``"version"`` and ``"plugins"`` keys, suitable for
        writing to ``plugins.json``.
    """
    specs = _discover_plugin_specs()
    plugins = {lang: specs[lang] for lang in sorted(specs)}
    return {"version": _PLUGINS_JSON_VERSION, "plugins": plugins}


# ------------------------------------------------------------------
# Config management
# ------------------------------------------------------------------


def _ensure_plugins_json() -> dict[str, Any]:
    """Auto-discover plugins and write ``plugins.json``.

    Returns:
        The newly written config dict.
    """
    config = _auto_discover()
    try:
        _PLUGINS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_PLUGINS_JSON_PATH, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=4)
        logger.info(
            "Auto-generated plugins.json with %d languages",
            len(config.get("plugins", {})),
        )
    except OSError as exc:
        logger.error("Failed to write plugins.json: %s", exc)
    return config


def _persist_plugins_config(config: dict[str, Any]) -> None:
    """Write *config* to ``plugins.json`` on disk.

    Logs an error on failure but never raises — callers treat this as
    best-effort bookkeeping.
    """
    try:
        _PLUGINS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_PLUGINS_JSON_PATH, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=4)
    except OSError as exc:
        logger.error("Failed to persist plugins.json: %s", exc)


def _merge_spec(spec: dict[str, Any], saved_spec: Any) -> dict[str, Any]:
    """Merge a discovered spec with the saved enablement choice.

    Args:
        spec: Freshly discovered plugin specification.
        saved_spec: Previously saved specification, if any.
    """
    merged = dict(spec)
    if isinstance(saved_spec, dict):
        merged["enabled"] = saved_spec.get("enabled", spec.get("enabled", True))
    elif "enabled" not in merged:
        merged["enabled"] = True
    return merged


def load_plugins_config() -> dict[str, Any]:
    """Load and validate the plugins config, auto-creating if needed.

    The external installer owns plugin directories. This cache records
    discovered specifications and preserves local ``enabled`` choices.
    Languages whose directories disappear are pruned.

    Returns:
        The validated config dict.
    """
    if not _PLUGINS_JSON_PATH.is_file():
        logger.info("plugins.json not found, auto-discovering plugins")
        return _ensure_plugins_json()

    try:
        with open(_PLUGINS_JSON_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("plugins.json is corrupt, regenerating: %s", exc)
        return _ensure_plugins_json()

    if not isinstance(raw, dict) or "plugins" not in raw:
        logger.warning("plugins.json has invalid structure, regenerating")
        return _ensure_plugins_json()

    # Refresh discovered specifications without changing local enablement.
    discovered = _auto_discover()
    saved_plugins = raw.setdefault("plugins", {})
    merged = False
    for lang, spec in discovered.get("plugins", {}).items():
        merged_spec = _merge_spec(spec, saved_plugins.get(lang))
        if saved_plugins.get(lang) != merged_spec:
            saved_plugins[lang] = merged_spec
            merged = True
            logger.info("Updated discovered language %r in plugins.json", lang)
    for lang in list(saved_plugins):
        if lang not in discovered.get("plugins", {}):
            del saved_plugins[lang]
            merged = True
            logger.info("Removed unavailable language %r from plugins.json", lang)
    if merged:
        _persist_plugins_config(raw)

    return raw


# ------------------------------------------------------------------
# Compatibility and requirements
# ------------------------------------------------------------------


def _version_numbers(value: str) -> tuple[int, ...]:
    """Return the numeric release components in a version string.

    Args:
        value: A dotted version such as ``"1.2"``.
    """
    numbers: list[int] = []
    for chunk in str(value).split("."):
        digits = ""
        for character in chunk:
            if not character.isdigit():
                break
            digits += character
        if not digits:
            break
        numbers.append(int(digits))
    return tuple(numbers)


def _studio_supports(minimum_version: Optional[str], lang: str) -> bool:
    """Return whether the running Studio meets a plugin minimum.

    Args:
        minimum_version: Minimum Studio version, or ``None``.
        lang: Language requesting the check, used in diagnostics.
    """
    if not minimum_version:
        return True
    current = _version_numbers(STUDIO_VERSION)
    required = _version_numbers(minimum_version)
    if not required:
        logger.warning(
            "Skipping %r: invalid minimum Studio version %r", lang, minimum_version
        )
        return False
    if current < required:
        logger.warning(
            "Skipping %r: requires Studio %s, running %s",
            lang,
            minimum_version,
            STUDIO_VERSION,
        )
        return False
    return True


def _include_plugin(
    lang: str,
    plugins: dict[str, Any],
    by_plugin: dict[str, str],
    selected: dict[str, Any],
    chain: tuple[str, ...] = (),
) -> Optional[str]:
    """Add one plugin and its requirements to the load order.

    Args:
        lang: Language being considered.
        plugins: All discovered plugin specifications.
        by_plugin: Plugin-id to language mapping.
        selected: Specifications already accepted, in load order.
        chain: Languages above the current requirement.
    """
    if lang in selected:
        return None
    spec = plugins.get(lang)
    if not isinstance(spec, dict):
        return f"{lang}: invalid plugin specification"
    if spec.get("enabled", True) is False:
        return f"{lang}: disabled"
    minimum_version = spec.get("minimum_studio_version")
    if minimum_version is not None and not isinstance(minimum_version, str):
        return f"{lang}: invalid minimum Studio version"
    if not _studio_supports(
        minimum_version if isinstance(minimum_version, str) else None, lang
    ):
        return f"{lang}: requires Studio {minimum_version}"
    requires = spec.get("requires", [])
    if not isinstance(requires, list):
        return f"{lang}: invalid plugin requirements"
    for requirement in requires:
        if not isinstance(requirement, str) or not requirement:
            return f"{lang}: invalid plugin requirement"
        required_lang = by_plugin.get(requirement, requirement)
        if required_lang == lang or required_lang in chain:
            return f"{lang}: circular plugin requirement {requirement!r}"
        problem = _include_plugin(
            required_lang, plugins, by_plugin, selected, chain + (lang,)
        )
        if problem:
            return problem
    selected[lang] = spec
    return None


def _select_plugins(plugins: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Choose loadable plugins in dependency order.

    Args:
        plugins: Discovered plugin specifications by language.
    """
    if not isinstance(plugins, dict):
        return {}, ["Invalid plugin configuration"]
    by_plugin = {
        spec.get("plugin", lang): lang
        for lang, spec in plugins.items()
        if isinstance(spec, dict)
    }
    selected: dict[str, Any] = {}
    warnings: list[str] = []
    for lang in sorted(plugins):
        spec = plugins.get(lang)
        if isinstance(spec, dict) and spec.get("enabled", True) is False:
            continue
        problem = _include_plugin(lang, plugins, by_plugin, selected)
        if problem:
            warnings.append(problem)
    return selected, warnings


# ------------------------------------------------------------------
# Provider import
# ------------------------------------------------------------------


def _plugin_path(root: str, value: Any) -> str:
    """Join a manifest path to its plugin directory.

    Args:
        root: Absolute plugin directory.
        value: Relative or absolute manifest path.
    """
    if not isinstance(value, str) or not value:
        return ""
    if os.path.isabs(value):
        return value
    return os.path.join(root, value)


def _resolve_plugin_path(root: str, value: Any, kind: str) -> Optional[str]:
    """Resolve a manifest path against its plugin directory.

    Args:
        root: Absolute plugin directory.
        value: Relative or absolute path from the manifest.
        kind: Human-readable path purpose used in diagnostics.
    """
    if not isinstance(value, str) or not value:
        return None
    path = value if os.path.isabs(value) else os.path.abspath(os.path.join(root, value))
    if not os.path.exists(path):
        logger.warning("Skipping %s %s: not found at %s", root, kind, path)
        return None
    return path


def _prepare_plugin_environment(plugin_root: str, spec: dict[str, Any]) -> None:
    """Expose a plugin's bundled dependencies to the running process.

    Args:
        plugin_root: Absolute plugin directory.
        spec: Plugin specification from discovery.
    """
    vendor = spec.get("vendor", [])
    if isinstance(vendor, list):
        for entry in vendor:
            path = _resolve_plugin_path(plugin_root, entry, "vendor directory")
            if path and os.path.isdir(path) and path not in sys.path:
                sys.path.append(path)
    native_libraries = spec.get("native_libraries", [])
    if isinstance(native_libraries, list):
        for entry in native_libraries:
            path = _resolve_plugin_path(plugin_root, entry, "native library")
            if path and os.path.isfile(path):
                try:
                    ctypes.CDLL(path)
                except OSError as exc:
                    logger.warning("Native library failed to load %s: %s", path, exc)


def _import_dotted_factory(dotted_path: str) -> Optional[Any]:
    """Import and return the callable at *dotted_path*.

    Args:
        dotted_path: Dotted Python path to a provider factory.

    Returns:
        The factory function, or ``None`` if import fails.
    """
    try:
        module_path, _, attr_name = dotted_path.rpartition(".")
        module = importlib.import_module(module_path)
        factory = getattr(module, attr_name, None)
        return factory if callable(factory) else None
    except Exception as exc:
        logger.error("Failed to import provider factory %s: %s", dotted_path, exc)
        return None


def _import_file_factory(
    plugin_id: str, plugin_root: str, entry: dict[str, Any]
) -> Optional[Any]:
    """Import a provider factory from a file inside a plugin directory.

    Args:
        plugin_id: Plugin identifier used for a unique module name.
        plugin_root: Absolute plugin directory.
        entry: Mapping with ``file`` and ``function`` keys.
    """
    file_name = entry.get("file")
    function_name = entry.get("function")
    if not isinstance(file_name, str) or not file_name:
        return None
    if not isinstance(function_name, str) or not function_name:
        return None
    provider_path = _resolve_plugin_path(plugin_root, file_name, "provider file")
    if provider_path is None or not provider_path.endswith(".py"):
        return None

    safe_id = (
        re.sub(r"[^A-Za-z0-9_]", "_", plugin_id or "plugin").strip("_") or "plugin"
    )
    safe_stem = (
        re.sub(r"[^A-Za-z0-9_]", "_", Path(provider_path).stem).strip("_") or "provider"
    )
    package_name = f"dreamstudio_plugin_{safe_id}"
    module_name = f"{package_name}.{safe_stem}"
    for loaded_name in list(sys.modules):
        if loaded_name == package_name or loaded_name.startswith(package_name + "."):
            del sys.modules[loaded_name]
    package = ModuleType(package_name)
    package.__path__ = [plugin_root]
    sys.modules[package_name] = package

    try:
        spec = spec_from_file_location(module_name, provider_path)
        if spec is None or spec.loader is None:
            return None
        module = module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        factory = getattr(module, function_name, None)
        return factory if callable(factory) else None
    except Exception as exc:
        logger.error("Failed to import provider file %s: %s", provider_path, exc)
        return None


def _import_factory(
    provider: Any, plugin_id: str = "", plugin_root: str = ""
) -> Optional[Any]:
    """Import a provider factory from either a dotted path or plugin file.

    Args:
        provider: Dotted path or ``{"file", "function"}`` mapping.
        plugin_id: Plugin identifier for file-based module names.
        plugin_root: Plugin directory for file-based imports.
    """
    if isinstance(provider, dict):
        return _import_file_factory(plugin_id, plugin_root, provider)
    if isinstance(provider, str):
        return _import_dotted_factory(provider)
    logger.error("Invalid provider reference %r", provider)
    return None


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------


def _register_outline_parser(lang: str, provider: Optional[Any]) -> None:
    """Connect a provider's outline implementation to the outline backend.

    Args:
        lang: Language identifier receiving outline support.
        provider: Intelligence provider created for the language.
    """
    if provider is None:
        return
    try:
        if provider.has_outline():
            register_parser(lang, provider.get_outline)
    except Exception as exc:
        logger.warning("Outline registration failed for %r: %s", lang, exc)


def _register_snippets(lang: str, plugin_root: str, spec: dict[str, Any]) -> None:
    """Attach snippet bodies for a language when a snippet file exists.

    Args:
        lang: Registered language identifier.
        plugin_root: Plugin directory used for relative snippet paths.
        spec: Plugin specification from discovery.
    """
    snippet_file = _plugin_path(plugin_root, spec.get("snippets", ""))
    if not snippet_file:
        snippet_file = _conventional_snippet_file(plugin_root, lang) or ""
    if not snippet_file:
        return
    LanguageRegistry.register_snippet_path(lang, snippet_file)


def _register_one(lang: str, spec: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Register a single language from its config spec.

    Args:
        lang: Language identifier (e.g. ``"python"``).
        spec: Plugin spec with ``"keywords"`` and optional ``"provider"`` paths.

    Returns:
        ``(success, warning_message_or_None)``
    """
    if spec.get("enabled", True) is False:
        logger.info("Skipping disabled language %r", lang)
        return True, None

    plugin_root = _plugin_path(_IRONICA_DIR, spec.get("root", _IRONICA_DIR))
    if not plugin_root:
        return False, f"{lang}: missing plugin directory"
    plugin_root = os.path.abspath(plugin_root)
    json_path = _plugin_path(plugin_root, spec.get("keywords", ""))
    if not json_path:
        return False, f"{lang}: no keywords path in spec"

    _prepare_plugin_environment(plugin_root, spec)
    provider = None
    provider_reference = spec.get("provider")
    if provider_reference:
        factory = _import_factory(
            provider_reference, str(spec.get("plugin", lang)), plugin_root
        )
        if factory is not None:
            try:
                provider = factory()
            except Exception as exc:
                logger.error("Provider factory for %r failed: %s", lang, exc)
                return False, f"{lang}: provider factory failed: {exc}"

    try:
        success = LanguageRegistry.register_language(json_path, provider)
    except Exception as exc:
        logger.error("Failed to register language %r: %s", lang, exc)
        return False, f"{lang}: registration raised {exc}"

    label = spec.get("display_name") or lang.capitalize()
    if success:
        _register_snippets(lang, plugin_root, spec)
        _register_outline_parser(lang, provider)
        logger.info("Language plugin registered: %s", lang)
        get_notification_manager().add_success(
            f"{label} Support Loaded",
            f"{label} language support initialized successfully.",
            "Plugins",
        )
        return True, None

    msg = f"{label} language plugin registration returned False"
    logger.warning(msg)
    get_notification_manager().add_warning(
        f"{label} Plugin Warning",
        f"{label} language plugin could not be registered. "
        "Syntax highlighting may be unavailable.",
        "Plugins",
    )
    return False, msg


def register_all_languages() -> list[str]:
    """Register every enabled language defined in ``plugins.json``.

    The external installer owns plugin directories. If ``plugins.json``
    is missing, it is auto-generated by scanning the filesystem.

    Returns:
        A list of warning messages (empty on full success).
    """
    config = load_plugins_config()
    plugins = config.get("plugins", {})
    selected, warnings = _select_plugins(plugins)

    for lang, spec in selected.items():
        _ok, warn = _register_one(lang, spec)
        if warn:
            warnings.append(warn)

    return warnings


# ------------------------------------------------------------------
# Legacy API (used by tests)
# ------------------------------------------------------------------


def register_python_language() -> bool:
    """Register the discovered Python language plugin.

    Uses the same discovery, compatibility, and dependency checks as normal
    startup. This helper remains for tests that need only Python.

    Returns:
        ``True`` on success, ``False`` on any failure.
    """
    try:
        spec = _discover_plugin_specs().get("python")
        if not isinstance(spec, dict):
            raise FileNotFoundError("No Python plugin directory was discovered")
        selected, warnings = _select_plugins({"python": spec})
        if "python" not in selected:
            raise RuntimeError(
                "; ".join(warnings) or "Python plugin was not selectable"
            )
        success, _warning = _register_one("python", selected["python"])
        return success
    except Exception as exc:
        logger.error("Failed to register Python language plugin: %s", exc)
        get_notification_manager().add_error(
            "Python Plugin Error",
            f"Python language plugin failed to initialize: {exc}. "
            "Code intelligence disabled.",
            "Plugins",
        )
        return False


def unregister_python_language() -> bool:
    """Remove the Python language from the LanguageRegistry.

    Returns:
        ``True`` if Python was registered and has been removed.
    """
    try:
        unregister_parser("python")
    except Exception as exc:
        logger.debug("Python outline parser was not removed: %s", exc)
    return LanguageRegistry.unregister_language("python")
