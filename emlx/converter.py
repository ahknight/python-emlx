#!/usr/bin/env python3.4

import os
import sys
import time
from mailbox import Maildir

import emlx
from .progress import Progress

def import_message(path, mailbox):
    f = open(path, "rb")
    data = f.read()
    f.close()
    msg = emlx.EmlxMessage(data)
    mailbox.add(msg.get_maildir_message())

def enumerate_messages(path):
    if os.path.isdir(path) is False:
        return [path]
    
    paths = []
    for root, dirs, files in os.walk(path):
        if len(files):
            paths.extend([os.path.join(root, name) for name in files if name.endswith(".emlx")])
    return paths

def main():
    if len(sys.argv) == 1:
        print("usage: emlx-to-maildir.py path [path ...] maildir")
        print("  Paths can be a mix of emlx files and directories to be searched for emlx files.")
        sys.exit(1)

    input_paths = []
    for path in sys.argv[1:-1]:
        input_paths.extend(enumerate_messages(path))

    output_path = sys.argv[-1:][0]

    maildir = Maildir(output_path, create=True)

    p = Progress(len(input_paths), unit="m")
    last = time.time()

    for path in input_paths:
        import_message(path, maildir)
        p.increment()
        if time.time() > (last + 0.5):
            last = time.time()
            print("[%02d%%] %-8s %-5s" % (p.percentage(), p.overall_rate_str(), p.time_remaining_str()), end="\r")
    
    print("[%02d%%] %-8s %-5s" % (100, p.overall_rate_str(), p.time_elapsed_str()))

if __name__ == "__main__":
    main()
