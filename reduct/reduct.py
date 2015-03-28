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

        cmd = ["strace", "-f", "-e", "trace=open,execve,access", "-o", "%s" % opfile]
        cmd.extend(args)
        print("Running: %s" % " ".join(cmd))
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as exc:
            print(repr(exc))

        with open(opfile, 'r') as strace:
            for line in strace:
                yield line

def reduct(source, destination, *args):
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
            os.makedirs(target)
        if not os.path.isfile(os.path.join(target, os.path.split(chunk)[-1])):
            print("Copying %s" % sourcefile)
            shutil.copy2(sourcefile, target)

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
            os.makedirs(target)

        new_target_dir = os.path.relpath(os.path.dirname(link_target),
                                         os.path.dirname(sourcelink))
        new_target = os.path.join(new_target_dir, os.path.split(link_target)[-1])
        if not os.path.isfile(link_name):
            print("Making softlink from %s -> %s" % (link_name, new_target))
            os.symlink(new_target, link_name)

    def handle_file(path):
        if os.path.islink(path):
            make_link(path)
        else:
            copy_full(path)

    if not os.path.isdir(destination):
        os.makedirs(destination)

    print("Executing: %s" % (" ".join(args)))

    for line in strace_iter(*args):
        try:
            syscall = line.split()[1]
        except IndexError:
            break
        path = syscall[syscall.find("\"")+1:syscall.rfind("\"")]
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            continue
        if path.startswith(source):
            handle_file(path)



def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', dest='source', type=str, required=True,
                   help='Source directory containing the tool')
    parser.add_argument('--dest', dest='dest', type=str, required=True,
                   help='Destination directory for the reducted tool')
    args, extra = parser.parse_known_args(args=argv)

    if not os.path.isdir(args.source):
        parser.print_help()
        sys.exit(1)

    reduct(args.source, args.dest, *extra)

if __name__ == "__main__":
    main()

