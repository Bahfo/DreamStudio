# FTM: File Tracking Manager
# Copyright 2026 - DreamStudio
# Written by Bahaa Nofal

"""

"""

#################################
# Definitions
#################################
error_message_no_command = """Bad command. Perhaps you check the list of commands?
Type 'show_commands' to view all `ftm` commands. Type `help` to view article help."""

help_message = """COPYRIGHT 2026 DREAMSTUDIO. ALL RIGHTS RESERVED
A FILE TRACK MANAGER IMPLEMENTED WITH THE SAME `GIT` STRUCTURE FOR DREAMSTUDIO"""


import re
import os
import sys
import zlib
import fnmatch
import hashlib
import argparse
import configparser

from datetime import datetime
from math import ceil

argparser = argparse.ArgumentParser(description="File Track Manager (ftm)")
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True


def main(argv = sys.argv[1:]):
    args = argparser.parse_args(argv)

    match args.command:
        case "add"          : ftm_add(args)
        case "cat-file"     : ftm_cat_file(args)
        case "check-ignore" : ftm_check_ignore(args)
        case "checkout"     : ftm_checkout(args)
        case "commit"       : ftm_commit(args)
        case "hash-object"  : ftm_hash_object(args)
        case "init"         : ftm_init(args)
        case "log"          : ftm_log(args)
        case "ls-files"     : ftm_ls_files(args)
        case "ls-tree"      : ftm_ls_tree(args)
        case "rev-parse"    : ftm_rev_parse(args)
        case "rm"           : ftm_rm(args)
        case "show-ref"     : ftm_show_ref(args)
        case "status"       : ftm_status(args)
        case "tag"          : ftm_tag(args)
        case "show_commands": ftm_show_commands(args)
        case _              : print(error_message_no_command)

def repo_path(repo, *path):
    """Computes the path under the repo's gitdir"""
    return os.path.join(repo.gitdir, *path)

def repo_file(repo, *path, mkdir=False):
    """Creates directory_name(*path) if absent"""
    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)
    
def repo_dir(repo, *path, mkdir=False):
    """Makes a new directory but mkdir *path if absent if mkdir"""
    path = repo_path(repo, *path)

    if os.path.exists(path):
        if (os.path.isdir(path)):
            return path
        else:
            raise Exception(f"No directory is found here at {path}")
    
    if mkdir:
        os.makedirs(path)
        return path
    
    else: return None


class GitRepository(object):
    """Creates a git repository inside the current working directory if found"""

    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception(f"No git repository is found in the current path {path}")
        
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Error: Configuration file missing.")
        
        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception(f"Unsupported Repository Format Version: {vers}")
            
def repo_create(path):
    """Creats a new repository at the given path"""
    
    repo = GitRepository(path, True)
    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception(f"{path} is not a directory")
        
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception(f"{path} is not empty")
        

    assert repo_dir(repo, "branches", mkdir=True)
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)

    # .git/description Creator
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo

def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret