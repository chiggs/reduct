#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reduce a toolchain to the bare minimum required set of files.
"""
from __future__ import print_function, with_statement

import sys
import os
import tempfile
import subprocess
import shutil
import argparse
from contextlib import contextmanager

@contextmanager
def tempdir():
    """
    Context manager to create a temporary directory and ensure it's
    removed completely when we're done
    """
    dirname = tempfile.mkdtemp()
    yield dirname
    try:
        shutil.rmtree(dirname)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise

def strace_iter(*args):
    """
    Perform the strace and then yields each line of the recorded
    strace
    """
    with tempdir() as dirname:
        opfile = os.path.join(dirname, "strace_output.log")

        cmd = ["strace", "-f", "-e", "trace=file", "-o", "%s" % opfile]
        cmd.extend(args)
        print("Running: %s" % " ".join(cmd))
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as exc:
            print(repr(exc))

        with open(opfile, 'r') as strace:
            for line in strace:
                yield line

def reduct(source, destination, dryrun, *args):
    """
    Perform the reduct

    Args:
        source (string): The source directory containing the tool to reduce

        destination (string): Where to copy the reduced toolchain to
    """
    def copy_full(sourcefile):
        chunk = sourcefile[len(source):].lstrip("/")
        dirname = os.path.dirname(chunk)
        target = os.path.join(destination, dirname)
        if not os.path.isdir(target):
            print("Making dirs to %s" % target)
            if not dryrun:
                os.makedirs(target)
        if not os.path.isfile(os.path.join(target, os.path.split(chunk)[-1])):
            print("Copying %s" % sourcefile)
            if not dryrun:
                shutil.copy2(sourcefile, target)
        else:
            print("Already exists: %s" % os.path.join(target, os.path.split(chunk)[-1]))

    def make_link(sourcelink):
        link_target = os.path.realpath(sourcelink)

        # First of all ensure the target exists
        if link_target.startswith(source):
            handle_file(link_target)

        # Extract the common prefix and create a relative symlink
        chunk = sourcelink[len(source):].lstrip("/")
        dirname = os.path.dirname(chunk)
        target = os.path.join(destination, dirname)
        filename = os.path.split(sourcelink)[-1]
        link_name = os.path.join(os.path.join(destination, dirname), filename)

        if not os.path.isdir(target):
            print("Making dirs to %s" % target)
            if not dryrun:
                os.makedirs(target)

        new_target_dir = os.path.relpath(os.path.dirname(link_target),
                                         os.path.dirname(sourcelink))
        new_target = os.path.join(new_target_dir, os.path.split(link_target)[-1])
        if not os.path.isfile(link_name):
            print("Making softlink from %s -> %s" % (link_name, new_target))
            if not dryrun:
                os.symlink(new_target, link_name)
        else:
            print("Already exists: %s" % (link_name))

    def handle_file(path):
        if os.path.islink(path):
            make_link(path)
        else:
            copy_full(path)

    if not os.path.isdir(destination):
        print("Making dirs to %s" % destination)
        if not dryrun:
            os.makedirs(destination)

    print("Executing: %s" % (" ".join(args)))

    for line in strace_iter(*args):
        try:
            syscall = line.split()[1]
        except IndexError:
            print("Failed on %s" % line)
            break
        left = syscall.find("\"") + 1
        right = left + syscall[left:].find("\"")
        path = syscall[left:right]
        path = os.path.realpath(os.path.abspath(path))
        if not os.path.isfile(path):
            print("%s isn't a file (%s)" % (path, syscall))
            continue
        if path.startswith(source):
            handle_file(path)
        else:
            print("Ignoring %s (doesn't start with %s)" % (path, source))


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', dest='source', type=str, required=True,
                   help='Source directory containing the tool')
    parser.add_argument('--dest', dest='dest', type=str, required=True,
                   help='Destination directory for the reducted tool')
    parser.add_argument('--dry', dest='dryrun', action='store_true', default=False,
                   help='Dry run without modifying any files')

    args, extra = parser.parse_known_args(args=argv)

    if not os.path.isdir(args.source):
        parser.print_help()
        sys.exit(1)

    reduct(args.source, args.dest, args.dryrun, *extra)

if __name__ == "__main__":
    main()

