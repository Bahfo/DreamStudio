from fabric import Connection

import os
import json


class ConnectionManager:
    def __init__(self, file_path="connections.json"):
        self.filepath = file_path

        self._check_for_file_existence()

        self.data = self.load()

    def _check_for_file_existence(self):
        if os.path.exists(self.filepath):
            return self.filepath

        else:
            data = {"connections": []}
            with open(self.filepath, "w") as f:
                json.dump(data, f)

    def load(self):
        try:
            with open(self.filepath, "r") as file:
                data = json.load(file)
                if not isinstance(data, dict):
                    return {"connections": []}

                if "connections" not in data:
                    data["connections"] = []

                if not isinstance(data["connections"], list):
                    data["connections"] = []

                return data
        except Exception as e:
            return {"connections": []}

    def save(self):
        with open(self.filepath, "w") as file:
            json.dump(self.data, file)

    def add_connection(self, connection_data: dict):
        required = ["name", "host", "username"]

        for key in required:
            if key not in connection_data:
                raise ValueError(f"{key} is not found in {connection_data}")

        for connection in self.data["connections"]:
            if connection["name"] == connection_data["name"]:
                raise ValueError("Duplicated connection exists")

        if "key_path" in connection_data:
            connection_data["key_path"] = os.path.expanduser(
                connection_data["key_path"]
            )

        self.data["connections"].append(connection_data)
        self.save()

    def get_connection(self, name: str):
        for connection in self.data["connections"]:
            if connection["name"] == name:
                return connection
        if not self.data["connectons"]["name"]:
            raise ValueError("Connection not found")

    def list_connections(self):
        names = []

        for connection in self.data["connections"]:
            names.append(connection["name"])

        return names


class ConnectionSession:
    def __init__(self, config: dict):
        self.connection = None
        self.is_connected = False
        self.config = config

        self.connection_name = self.config["name"]
        self.connection_host = self.config["host"]
        self.connection_user_name = self.config["username"]
        # Extract keypath if available
        self.connection_key_path = (
            self.config["key_path"] if "key_path" in self.config else None
        )
        self.connection_port = self.config["port"] if "port" in self.config else 22

    def connect(self):
        try:
            if self.connection_key_path is not None:
                connection_kwargs = {"key_filename": self.connection_key_path}
            else:
                connection_kwargs = {}

            self.connection = Connection(
                host=self.connection_host,
                user=self.connection_user_name,
                port=self.connection_port,
                connect_kwargs=connection_kwargs,
            )

            self.connection.run("echo connected", hide=True)
            self.is_connected = True

        except Exception as e:
            self.is_connected = False
            self.connection = None
            raise Exception(
                f"Error during connection: cannot connect to {self.connection_name}. ERROR: {e}"
            )

    def run_command(self):
        pass


class CommandLine:
    def __init__(self, session):
        self.session = session

        self.history = []
        self.history_index = -1

        self.commands = {
            "clear": self._clear,
        }

    def execute(self, line: str):
        line = line.strip()

        if not line:
            return None

        # store history
        self._add_history(line)

        # custom commands starting with !
        if line.startswith("!"):
            return self._handle_custom(line)

        # registered local commands
        cmd = line.split()[0]

        if cmd in self.commands:
            return self.commands[cmd](line)

        # fallback: remote execution
        return self.session.run_command(line)

    def _clear(self, line=None):
        return {"type": "clear"}

    def _handle_custom(self, line: str):
        cmd = line[1:].strip()

        if cmd == "deploy":
            self.session.run_command("git pull")
            self.session.run_command("systemctl restart app")
            return {"type": "output", "data": "Deploy executed"}

        if cmd == "status":
            return self.session.run_command("uptime")

        return {"type": "error", "data": f"Unknown custom command: {cmd}"}

    def _add_history(self, line: str):
        self.history.append(line)
        self.history_index = len(self.history)

    def get_previous_command(self):
        if not self.history:
            return ""

        if self.history_index > 0:
            self.history_index -= 1

        return self.history[self.history_index]

    def get_next_command(self):
        if not self.history:
            return ""

        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            return self.history[self.history_index]

        return ""
