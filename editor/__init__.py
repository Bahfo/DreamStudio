"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Unified import hub for DreamStudio.

Every project module starts with a single ``from editor import *`` and
receives the standard library and PyQt6 names below. This file must
ONLY contain external (standard library / PyQt6) imports - never local
project imports - so importing any ``editor.*`` submodule stays free of
circular imports and of GUI-side effects.

Deliberately excluded here (kept as local imports where used):
heavy or platform-specific stacks such as ``PyQt6.QtWebEngineWidgets``,
``tkinter``, ``pty`` and ``datetime``.
"""

import ast
import atexit
import bisect
import builtins
import cmd
import codecs
import concurrent.futures
import copy
import ctypes
import fnmatch
import getpass
import hashlib
import html
import importlib
import importlib.metadata
import inspect
import io
import json
import keyword
import logging
import os
import pathlib
import pickle
import platform
import re
import shutil
import signal
import socket
import stat
import struct
import subprocess
import sys
import sysconfig
import tempfile
import textwrap
import threading
import time
import tokenize
import traceback
import types
import urllib.error
import urllib.request
import weakref
import zipfile

from abc import ABC, abstractmethod
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from enum import Enum, IntEnum
from itertools import islice
from pathlib import Path
from typing import *

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtSvg import *
from PyQt6.Qsci import *
