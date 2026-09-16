# Written by Bahaa Nofal - 8/7/2026
# menu.py
"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Modern Visual Studio–style right-click context menu for the file explorer.
Extension-friendly: extensions register actions via the public API and the
menu rebuilds dynamically on each show.
"""

from __future__ import annotations

from editor import *


class MenuItem:
    """Describes a single menu entry."""

    def __init__(
        self,
        item_id: str,
        text: str,
        *,
        shortcut: str = "",
        icon: str = "",
        category: str = "",
        show_for: str = "all",  # "all" | "file" | "dir"
        enabled: bool | Callable = True,
        checked: bool | Callable = False,
        callback: Callable | None = None,
        submenu_items: list | None = None,
    ) -> None:
        self.item_id = item_id
        self.text = text
        self.shortcut = shortcut
        self.icon = icon
        self.category = category
        self.show_for = show_for
        self.enabled = enabled
        self.checked = checked
        self.callback = callback
        self.submenu_items = submenu_items or []

    def to_dict(self) -> dict:
        return {
            "id": self.item_id,
            "text": self.text,
            "shortcut": self.shortcut,
            "icon": self.icon,
            "category": self.category,
            "show_for": self.show_for,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MenuItem:
        return cls(
            item_id=d.get("id", ""),
            text=d.get("text", ""),
            shortcut=d.get("shortcut", ""),
            icon=d.get("icon", ""),
            category=d.get("category", ""),
            show_for=d.get("show_for", "all"),
        )


class MenuSeparator:
    """Describes a separator line in the menu."""

    def __init__(self, category: str = "") -> None:
        self.category = category


class MenuSubmenu:
    """Describes a sub-menu entry."""

    def __init__(
        self,
        text: str,
        items: list,
        *,
        icon: str = "",
        category: str = "",
        show_for: str = "all",
    ) -> None:
        self.text = text
        self.items = items
        self.icon = icon
        self.category = category
        self.show_for = show_for


class MenuRegistry:
    """Holds all registered menu items, separators and submenus.

    Extensions interact with this registry through the public methods.
    The `ExplorerClickMenu` rebuilds its visual tree from the registry
    every time it is shown.
    """

    def __init__(self) -> None:
        self._items: list[MenuItem | MenuSeparator | MenuSubmenu] = []

    def add_action(self, item: MenuItem) -> None:
        """Register a single action item."""
        self._items.append(item)

    def add_separator(self, category: str = "") -> None:
        """Insert a separator."""
        self._items.append(MenuSeparator(category=category))

    def add_submenu(self, sub: MenuSubmenu) -> None:
        """Register a sub-menu."""
        self._items.append(sub)

    def add_raw(self, d: dict) -> None:
        """Add an item from a JSON-like dictionary."""
        typ = d.get("type", "action")
        if typ == "separator":
            self.add_separator(category=d.get("category", ""))
        elif typ == "submenu":
            children = [MenuItem.from_dict(c) for c in d.get("items", [])]
            self.add_submenu(
                MenuSubmenu(
                    text=d.get("text", ""),
                    items=children,
                    icon=d.get("icon", ""),
                    category=d.get("category", ""),
                    show_for=d.get("show_for", "all"),
                )
            )
        else:
            self.add_action(MenuItem.from_dict(d))

    def load_json(self, json_path: str, base_dir: str = "") -> None:
        """Populate the registry from a JSON file.

        *base_dir* is prepended to relative icon paths so icons resolve
        correctly regardless of the current working directory.
        """
        if not os.path.exists(json_path):
            print(f"[menu] registry not found: {json_path}")
            return
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[menu] JSON error: {e}")
            return

        src_dir = os.path.dirname(os.path.abspath(json_path))
        for entry in data:
            self._resolve_icon(entry, src_dir, base_dir)
            self.add_raw(entry)

    @staticmethod
    def _resolve_icon(entry: dict, src_dir: str, base_dir: str) -> None:
        icon = entry.get("icon", "")
        if not icon:
            return
        # already absolute
        if os.path.isabs(icon):
            return
        # try relative to the json file
        candidate = os.path.join(src_dir, icon)
        if os.path.exists(candidate):
            entry["icon"] = candidate
            return
        # fall back to CWD-relative (legacy)
        if os.path.exists(icon):
            entry["icon"] = os.path.abspath(icon)
            return
        # if base_dir is given, try that too
        if base_dir:
            candidate2 = os.path.join(base_dir, icon)
            if os.path.exists(candidate2):
                entry["icon"] = candidate2
                return

    def items_for(self, is_dir: bool) -> list:
        """Return items that should be shown for a file or directory."""
        out: list = []
        for item in self._items:
            if isinstance(item, (MenuSeparator, MenuSubmenu)):
                show = item.show_for if hasattr(item, "show_for") else "all"
            elif isinstance(item, MenuItem):
                show = item.show_for
            else:
                show = "all"

            if show == "all":
                out.append(item)
            elif show == "file" and not is_dir:
                out.append(item)
            elif show == "dir" and is_dir:
                out.append(item)
        return out

    def clear(self) -> None:
        self._items.clear()


class ExplorerClickMenu(QMenu):
    """Right-click context menu with a modern VS Code look.

    Usage::

        registry = MenuRegistry()
        registry.load_json("menu_registry.json")
        # extensions can also call registry.add_action(...) etc.

        menu = ExplorerClickMenu(tree, model, registry, parent=self)
        tree.customContextMenuRequested.connect(menu.show_context_menu)
    """

    def __init__(
        self,
        tree: QTreeView,
        model: QFileSystemModel,
        registry: MenuRegistry,
        *,
        proxy_model=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.tree = tree
        self.model = model
        self.proxy_model = proxy_model or tree.model()
        self.registry = registry

        self.current_path = ""
        self.current_is_dir = False
        self._action_map: dict[str, Callable] = {}
        self._tree_shortcuts: list[QAction] = []

    def register_action(
        self,
        action_id: str,
        callback: Callable,
        *,
        text: str = "",
        shortcut: str = "",
        icon: str = "",
        category: str = "edit",
        show_for: str = "all",
        checked: bool | Callable = False,
    ) -> None:
        self._action_map[action_id] = callback
        self.registry.add_action(
            MenuItem(
                item_id=action_id,
                text=text or action_id,
                shortcut=shortcut,
                icon=icon,
                category=category,
                show_for=show_for,
                callback=callback,
                checked=checked,
            )
        )

    def register_callback(self, action_id: str, callback: Callable) -> None:
        self._action_map[action_id] = callback

    def _resolve_cb(self, item: MenuItem) -> Callable | None:
        """Resolve an item to its callable, or ``None`` when unregistered."""
        if callable(item.callback):
            return item.callback
        callback = self._action_map.get(item.item_id) or self._action_map.get(item.text)
        return callback if callable(callback) else None

    def show_context_menu(self, position) -> None:
        viewport_position = self.tree.viewport().mapFrom(self.tree, position)
        proxy_index = self.tree.indexAt(viewport_position)

        if not proxy_index.isValid():
            return

        if hasattr(self.proxy_model, "mapToSource"):
            source_index = self.proxy_model.mapToSource(proxy_index)
        else:
            source_index = proxy_index

        file_path = self.model.filePath(source_index)
        is_dir = self.model.fileInfo(source_index).isDir()
        self.current_path = file_path
        self.current_is_dir = is_dir

        self.tree.setCurrentIndex(proxy_index)
        self._build(file_path, is_dir)

        self.exec(self.tree.mapToGlobal(position))

    def _build(self, path: str, is_dir: bool) -> None:
        self.clear()
        raw_items = self.registry.items_for(is_dir)

        categories = ["project", "add", "edit", "version_control", "properties"]
        grouped_items = {cat: [] for cat in categories}
        uncategorized = []

        for item in raw_items:
            cat = getattr(item, "category", "").lower()
            if cat in grouped_items:
                grouped_items[cat].append(item)
            else:
                uncategorized.append(item)

        first_section = True

        for cat in categories:
            items_in_cat = grouped_items[cat]
            if not items_in_cat:
                continue

            if not first_section:
                self.addSeparator()
            first_section = False

            for entry in items_in_cat:
                if isinstance(entry, MenuSeparator):
                    self.addSeparator()
                elif isinstance(entry, MenuSubmenu):
                    self._build_submenu(entry)
                elif isinstance(entry, MenuItem):
                    self._add_action(entry)

        if uncategorized:
            if not first_section:
                self.addSeparator()
            for entry in uncategorized:
                if isinstance(entry, MenuSeparator):
                    self.addSeparator()
                elif isinstance(entry, MenuSubmenu):
                    self._build_submenu(entry)
                elif isinstance(entry, MenuItem):
                    self._add_action(entry)

    def _add_action(self, item: MenuItem) -> None:
        action = QAction(item.text, self)

        if item.shortcut:
            action.setShortcut(QKeySequence(item.shortcut))

        icon_path = item.icon
        if icon_path and os.path.exists(icon_path):
            action.setIcon(QIcon(icon_path))

        cb = self._resolve_cb(item) or self._fallback_cb(item.item_id)

        if callable(item.checked):
            action.setCheckable(True)
            action.setChecked(item.checked())
            action.toggled.connect(lambda checked: cb())
        elif item.checked:
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(cb)
        else:
            action.triggered.connect(cb)

        if isinstance(item.enabled, bool):
            action.setEnabled(item.enabled)
        elif callable(item.enabled):
            action.setEnabled(item.enabled())

        self.addAction(action)

    def _build_submenu(self, sub: MenuSubmenu) -> None:
        menu = QMenu(sub.text, self)
        menu.setStyleSheet(self.styleSheet())

        for child in sub.items:
            if isinstance(child, MenuItem):
                act = QAction(child.text, menu)
                if child.shortcut:
                    act.setShortcut(QKeySequence(child.shortcut))
                icon_path = child.icon
                if icon_path and os.path.exists(icon_path):
                    act.setIcon(QIcon(icon_path))
                cb = (
                    child.callback
                    or self._action_map.get(child.item_id)
                    or self._fallback_cb(child.item_id)
                )
                act.triggered.connect(cb)
                menu.addAction(act)

        self.addMenu(menu)

    def _fallback_cb(self, action_id: str) -> Callable:
        return lambda: print(f"No handler for '{action_id}'")

    def _make_callback(self, cb: Callable) -> Callable:
        return lambda: cb()
