#!/usr/bin/env python

import argparse
import logging
import os
import sys
import time

from maildir_lite import Maildir
from emlx.mailbox import AMMailbox

from clint.textui import progress, colored


def main(argc, argv):
    global STOP
    
    logging.basicConfig(format="%(message)s", level=logging.WARNING, stream=sys.stdout)
    PROGRAM = os.path.basename(argv[0])
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="converts Apple Mail mailboxes into maildir-format mailboxes",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument("-q", "--quiet",
                            action="store_true", help="no output")
    parser.add_argument("-v", "--verbose", default=0,
                            action="count", help="show per-message progress and status")
    parser.add_argument("-d", "--debug",
                            action="store_true", help="show everything. everything.")
    parser.add_argument("-m", "--maildir", default="~/Maildir/",
                            help="path to maildir to import messages into (will create if nonexistant)")
    parser.add_argument("-n", "--dry-run",
                            action="store_true", help="simulate actions only")
    parser.add_argument("-r", "--recursive",
                            action="store_true", help="also import all subfolders")
    parser.add_argument("-p", "--preserve",
                            action="store_true", help="preserve folder structure (only makes sense with --recursive)")
    parser.add_argument("-l", "--fs",
                            action="store_true", help="use FS layout for maildir subfolders instead of Maildir++")
    parser.add_argument("source", nargs="+")
    
    args = parser.parse_args()
    logging.info(args)
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug output enabled.")
    if args.verbose:
        if logging.getLogger().getEffectiveLevel() != logging.DEBUG:
            logging.getLogger().setLevel(logging.INFO)
    if args.quiet:
        if logging.getLogger().getEffectiveLevel() != logging.DEBUG:
            logging.getLogger().setLevel(logging.ERROR)
    
    paths = args.source
    if len(paths) == 0:
        paths = [os.path.expanduser("~/Library/Mail/")]
    
    
    ### Process the paths
    
    for path in paths:
        if not os.path.isdir(path):
            logging.warning("path is not a directory: %s", path)
            continue
        
        # See if the path is a mailbox container
        v3_path = os.path.join(path, "V3")
        if os.path.isdir(v3_path):
            logging.debug("has V3 data")
            path = v3_path
            
            local_mailboxes = os.path.join(path, "Mailboxes")
            if os.path.isdir(local_mailboxes):
                path = local_mailboxes
        
        # Load what should be a mailbox at this point
        logging.info("processing source path: %s", path)
        
        mailboxes = AMMailbox(path)
        logging.info("%s: found %d messages.", str(mailboxes), len(mailboxes.messages()))
        
        sources = [mailboxes]
        if args.recursive:
            sources.extend(mailboxes.all_children)
        logging.debug("sources: %r" % sources)
        
        # if len(sources) == 0:
        #     logging.warning("no mailboxes found")
        #     sys.exit()
        
        # Scan for the total number of messags to import.
        total_count = 0
        for box in sources:
            total_count += len(box.messages())
        
        # if total_count == 0:
        #     logging.warning("no messages found")
        #     sys.exit()
        
        if args.dry_run == False:
            maildir = Maildir(args.maildir, create=True, lazy=True, fs_layout=args.fs)
        
        for box in sources:
            logging.info("%s: starting import" % box.name)
            
            if STOP:
                break
            
            if args.preserve:
                box_maildir = maildir.create_folder(box.name)
            else:
                box_maildir = maildir
            logging.info("writing messages to %s" % box_maildir.name)
            
            for msg in progress.bar(box.messages(), expected_size=len(box.messages()), label="Importing %s: " % box.name):
                if STOP:
                    break
                if args.dry_run == False:
                    m = msg.get_message()
                    box_maildir.add_message(m.get_maildir_message())
                else:
                    if msg.partial:
                        m = msg.get_message()
                    

def start():
    global STOP
    
    import signal
    def signal_handler(sig, frame):
        global STOP
        if STOP:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            os.kill(os.getpid(), signal.SIGTERM)
        STOP = True
    signal.signal(signal.SIGINT, signal_handler)
    
    # You might be a C developer if...
    STOP = False
    argc = len(sys.argv)
    argv = sys.argv
    
    sys.exit(main(argc, argv))
    
if __name__ == "__main__":
    start()
