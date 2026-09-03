#!/usr/bin/env python3
import fcntl
import os
import sys

# Minimal Bubblewrap-shaped test seam. It reproduces the confinement failure by
# making its inherited output descriptors non-blocking before execing the
# command after `--`. The production launcher must restore blocking semantics.
for descriptor in (1, 2):
    flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
    fcntl.fcntl(descriptor, fcntl.F_SETFL, flags | os.O_NONBLOCK)

delimiter = sys.argv.index("--")
os.execvpe(sys.argv[delimiter + 1], sys.argv[delimiter + 1:], os.environ)
