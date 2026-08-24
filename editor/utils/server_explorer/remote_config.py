"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Remote configuration manager for DreamStudio Server Explorer.

Handles reading, writing, and manipulating the ~/.dreamstudio/remote/configs.json
file that stores all server connection configurations. This file is completely
isolated from the main DreamStudio project files for security.
"""

from editor import *

logger = logging.getLogger(__name__)

# Path constants
HOME_DIR = Path.home()
DREAMSTUDIO_HOME = HOME_DIR / ".dreamstudio"
REMOTE_DIR = DREAMSTUDIO_HOME / "remote"
REMOTE_CONFIG_PATH = REMOTE_DIR / "configs.json"

# Default configuration structure
DEFAULT_REMOTE_CONFIG: dict[str, Any] = {
    "version": 1,
    "connections": [],
}


@dataclass
class ServerConnection:
    """Data model for a single server connection configuration."""

    id: str = ""
    name: str = ""
    connection_type: str = "ssh"  # ssh, ftp, docker
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""  # NOTE: Consider encryption in future
    key_file_path: str = ""
    remote_root: str = "/"
    description: str = ""
    last_connected: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServerConnection":
        """Create instance from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def validate(self) -> list[str]:
        """Validate connection configuration. Returns list of error messages."""
        errors = []
        if not self.name:
            errors.append("Connection name is required")
        if not self.host:
            errors.append("Host is required")
        if not self.username:
            errors.append("Username is required")
        if self.port < 1 or self.port > 65535:
            errors.append(f"Invalid port: {self.port}")
        if self.connection_type not in ("ssh", "ftp", "docker"):
            errors.append(f"Invalid connection type: {self.connection_type}")
        return errors


class RemoteConfigManager:
    """
    Manages the ~/.dreamstudio/remote/configs.json file.

    Provides methods to load, save, add, update, and remove server
    connection configurations. All operations are fault-tolerant and
    will recreate missing files or directories as needed.
    """

    def __init__(self) -> None:
        self._config_path = REMOTE_CONFIG_PATH
        self._data: dict[str, Any] = {}
        self._connections: list[ServerConnection] = []
        logger.info("RemoteConfigManager initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> dict[str, Any]:
        """
        Load remote configurations from disk.

        If the file is missing or corrupt, it will be recreated with
        default values.

        Returns:
            The loaded configuration dictionary.
        """
        self._ensure_directory()

        if not self._config_path.is_file():
            logger.warning("Remote config file not found, creating default")
            self._data = copy.deepcopy(DEFAULT_REMOTE_CONFIG)
            self._connections = []
            self.save()
            return self._data

        try:
            with open(self._config_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to parse remote config: %s", exc)
            self._data = copy.deepcopy(DEFAULT_REMOTE_CONFIG)
            self._connections = []
            self.save()
            return self._data

        if not isinstance(raw, dict):
            logger.warning("Remote config is not a dict, regenerating defaults")
            self._data = copy.deepcopy(DEFAULT_REMOTE_CONFIG)
            self._connections = []
            self.save()
            return self._data

        self._data = raw
        self._connections = self._parse_connections(raw.get("connections", []))
        logger.info(
            "Remote config loaded successfully (%d connections)",
            len(self._connections),
        )
        return self._data

    def save(self) -> None:
        """Persist current configuration to disk."""
        self._ensure_directory()

        self._data["connections"] = [conn.to_dict() for conn in self._connections]

        try:
            with open(self._config_path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=4)
            logger.info("Remote config saved")
        except OSError as exc:
            logger.error("Failed to save remote config: %s", exc)

    def get_connections(self) -> list[ServerConnection]:
        """Return all configured server connections."""
        return list(self._connections)

    def get_connection(self, conn_id: str) -> Optional[ServerConnection]:
        """
        Retrieve a specific connection by its ID.

        Args:
            conn_id: The unique identifier of the connection.

        Returns:
            The ServerConnection if found, None otherwise.
        """
        for conn in self._connections:
            if conn.id == conn_id:
                return conn
        return None

    def add_connection(self, connection: ServerConnection) -> bool:
        """
        Add a new server connection.

        Args:
            connection: The ServerConnection to add.

        Returns:
            True if added successfully, False if validation fails or
            duplicate ID exists.
        """
        if not connection.id:
            connection.id = self._generate_id(connection.name)

        # Check for duplicate ID
        if self.get_connection(connection.id) is not None:
            logger.warning("Connection with ID '%s' already exists", connection.id)
            return False

        errors = connection.validate()
        if errors:
            logger.warning("Connection validation failed: %s", errors)
            return False

        self._connections.append(connection)
        self.save()
        logger.info("Connection '%s' added", connection.name)
        return True

    def update_connection(self, conn_id: str, connection: ServerConnection) -> bool:
        """
        Update an existing server connection.

        Args:
            conn_id: The ID of the connection to update.
            connection: The new connection data.

        Returns:
            True if updated successfully, False otherwise.
        """
        for i, existing in enumerate(self._connections):
            if existing.id == conn_id:
                errors = connection.validate()
                if errors:
                    logger.warning("Connection validation failed: %s", errors)
                    return False

                connection.id = conn_id
                self._connections[i] = connection
                self.save()
                logger.info("Connection '%s' updated", connection.name)
                return True

        logger.warning("Connection with ID '%s' not found", conn_id)
        return False

    def remove_connection(self, conn_id: str) -> bool:
        """
        Remove a server connection by its ID.

        Args:
            conn_id: The ID of the connection to remove.

        Returns:
            True if removed successfully, False if not found.
        """
        for i, conn in enumerate(self._connections):
            if conn.id == conn_id:
                self._connections.pop(i)
                self.save()
                logger.info("Connection '%s' removed", conn.name)
                return True

        logger.warning("Connection with ID '%s' not found", conn_id)
        return False

    def connection_count(self) -> int:
        """Return the number of configured connections."""
        return len(self._connections)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_directory(self) -> None:
        """Ensure the remote config directory exists."""
        try:
            REMOTE_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Cannot create remote config directory: %s", exc)
            raise

    def _parse_connections(self, raw_list: list[dict]) -> list[ServerConnection]:
        """Parse raw connection dicts into ServerConnection objects."""
        connections = []
        for raw in raw_list:
            try:
                conn = ServerConnection.from_dict(raw)
                connections.append(conn)
            except Exception as exc:
                logger.warning("Failed to parse connection: %s", exc)
        return connections

    def _generate_id(self, name: str) -> str:
        """Generate a unique ID from a connection name."""
        base = name.lower().replace(" ", "_").replace("-", "_")
        base = "".join(c for c in base if c.isalnum() or c == "_")

        if not base:
            base = "connection"

        candidate = base
        counter = 1
        while self.get_connection(candidate) is not None:
            candidate = f"{base}_{counter}"
            counter += 1

        return candidate
