#!/usr/bin/env python3.4

import os
import sys
import time
from maildir_lite import Maildir

from emlx.message import EmlxMessage
from emlx.progress import Progress


def find_mailboxes(path):
    if os.path.isdir(path) is False:
        return []

    paths = []
    for root, dirs, files in os.walk(path):
        if root.endswith(".mbox") and "Info.plist" in files:
            paths.append(root)
        
        for a_dir in dirs:
            paths.extend(find_mailboxes(a_dir))
    
    return paths


def import_mailbox(path, destination):
    pass


def import_message(path, mailbox):
    """
    Reads a single message at :arg:path and adds it to the Maildir :arg:mailbox.
    """
    f = open(path, "rb")
    data = f.read()
    f.close()
    msg = EmlxMessage(data)
    mailbox.add_message(msg.get_maildir_message())


def enumerate_messages(path):
    """
    Walks :arg:path and returns a list of all files ending with ``.emlx``.
    """
    if os.path.isdir(path) is False:
        return [path]
    
    paths = []
    for root, dirs, files in os.walk(path):
        if len(files):
            paths.extend([os.path.join(root, name) for name in files if name.endswith(".emlx")])
    return paths

from multiprocessing import Pool
# from multiprocessing.dummy import Pool

def import_msg(path):
    global maildir, p, last
    import_message(path, maildir)
    p.increment()
    if time.time() > (last + 0.5):
        last = time.time()
        p.print_status_line("converting")

def main():
    global maildir, p, last
    
    if len(sys.argv) == 1:
        print("usage: emlx-to-maildir.py path [path ...] maildir")
        print("  Paths can be a mix of emlx files and directories to be searched for emlx files.")
        sys.exit(1)

    input_paths = []
    for path in sys.argv[1:-1]:
        input_paths.extend(enumerate_messages(path))

    output_path = sys.argv[-1:][0]

    maildir = Maildir(output_path, create=True)
    maildir.lazy = True

    p = Progress(len(input_paths)/4, unit="m")
    last = time.time()
    
    pool = Pool(4)
    pool.map(import_msg, input_paths)
    pool.close()
    pool.join()
    p.print_status_line()


if __name__ == "__main__":
    main()
