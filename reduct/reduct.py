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
    dirname = tempfile.mkdtemp()
    yield dirname
    try:
        shutil.rmtree(dirname)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise

def do_strace(*args):
    """
    Perform the strace and return the strace output
    """
    with tempdir() as dirname:
        opfile = os.path.join(dirname, "strace_output.log")

        cmd = ["strace", "-f", "-e", "trace=open,execve", "-o", "%s" % opfile]
        cmd.extend(args)
        print("Running: %s" % " ".join(cmd))
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as exc:
            print(repr(exc))

        with open(opfile, 'r') as strace:
            result = strace.read()
    return result


def reduct(source, destination, *args):
    """
    Perform the reduct
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

    if not os.path.isdir(destination):
        os.makedirs(destination)

    print("Executing: %s" % (" ".join(args)))
    strace = do_strace(*args)
    print("Processing strace...")

    for line in strace.split("\n"):
        try:
            syscall = line.split()[1]
        except IndexError:
            break
        path = syscall[syscall.find("\"")+1:syscall.rfind("\"")]
        if not os.path.isfile(path):
            continue
        if path.startswith(source):
            copy_full(path)

def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', dest='source', type=str, required=True,
                   help='Source directory containing the tool')
    parser.add_argument('--dest', dest='dest', type=str, required=True,
                   help='Destination directory for the redacted tool')
    args, extra = parser.parse_known_args(args=argv)

    if not os.path.isdir(args.source):
        parser.print_help()
        sys.exit(1)

    reduct(args.source, args.dest, *extra)

if __name__ == "__main__":
    main()
