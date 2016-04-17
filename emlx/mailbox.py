import os
import logging

from emlx.message import EmlxMessage

# For partial message reassembly
import email
from email.policy import EmailPolicy

# Just enough to get a regular message back out without
# significantly altering the message payload.
minimal_policy = EmailPolicy(linesep="\r\n", refold_source="none")
APPLE_MARKER = "X-Apple-Content-Length"


class AMMessageRef(object):
    mailbox = None
    msgid = 0
    partial = False
    
    def __repr__(self):
        return "<AMMessageRef msgid=%r partial=%r path=%s>" % (self.msgid, self.partial, self.msg_path)
    
    def __init__(self, mailbox, msgid, partial=False):
        self.mailbox = mailbox
        self.msgid = msgid
        self.partial = partial
    
    @property
    def msg_dir(self):
        msgid = str(self.msgid)
        excess = []
        if len(msgid) > 3:
            excess = list(msgid)[:-3]
            excess.reverse()
        
        path = self.mailbox.messages_path
        path = os.path.join(path, *excess)
        return path
    
    @property
    def msg_path(self):
        filename = str(self.msgid)
        if self.partial:
            filename += ".partial"
        filename += ".emlx"
        
        path = self.msg_dir
        path = os.path.join(path, "Messages")
        path = os.path.join(path, filename)
        return path
    
    def part_path(self, partno):
        partname = "%s.%s.emlxpart" % (self.msgid, str(partno))
        msg_dir, excess = os.path.split(self.msg_path)
        return os.path.join(msg_dir, partname)
    
    def get_message(self):
        path = self.msg_path
        if path is None or len(path) == 0:
            return None
        
        try:
            f = open(path, "rb")
            data = f.read()
            f.close()
        except Exception as e:
            log.exception("get_message: %r", e)
            return None
        
        # Parse EMLX data
        msg = EmlxMessage(data)
        
        if self.partial:
            logging.debug("%s: rebuilding partial message" % path)
            
            # Parse the email
            email_msg = email.message_from_bytes(msg.content, policy=minimal_policy)

            # Iterate over the MIME payloads and look
            # for the stub header.
            def load_parts(message, prefix):
                parts_needed = 0
                parts_loaded = 0
                
                parts = message.get_payload()
                for part in parts:
                    partno = parts.index(part) + 1
                    
                    if part.is_multipart():
                        load_parts(part, "%s.%d" % (prefix, partno))
                    
                    elif part[APPLE_MARKER]:
                        parts_needed += 1
                        
                        part_path = "%s.%d.emlxpart" % (prefix, partno)
                        logging.debug("%s: loading part %d" % (part_path, partno))
                        
                        try:
                            f = open(part_path, "rb")
                            part_data = f.read()
                            f.close()
                            
                            part.set_payload(part_data)
                            del part[APPLE_MARKER]
                            
                            parts_loaded +=1
                        
                        except Exception as e:
                            logging.exception("%s: error loading message part %d" % (path, partno))
                
                if parts_loaded != parts_needed:
                    logging.warning("%s: message may be incomplete (found %d parts of %d)" % (
                        prefix,
                        parts_loaded,
                        parts_needed)
                    )
                else:
                    logging.info("%s: sucessfully reassembled (%d parts)" % (prefix, parts_loaded))
            
            dir_name = os.path.dirname(path)
            prefix = os.path.join(dir_name, str(self.msgid))
            load_parts(email_msg, prefix)
            
            msg_bytes = email_msg.as_bytes()
            msg.content = msg_bytes
        
        return msg


class AMMailbox(object):
    parent = None
    path = None
    
    def __init__(self, path, parent=None):
        self.path = path
        self.parent = parent
    
    def __str__(self):
        return str(self.name)
    
    def __unicode__(self):
        return unicode(self.name)
    
    def __repr__(self):
        return "<AMMailbox name='%s'>" % self.name
    
    @property
    def name(self):
        path = os.path.normpath(self.path)
        name = os.path.basename(path)
        base, ext = os.path.splitext(name)
        
        if self.parent is not None:
            return "%s/%s" % (self.parent.name, base)
        return base
    
    @property
    def children(self):
        boxes = []
        for dirent in os.scandir(self.path):
            if dirent.is_dir() and dirent.name[-5:] == ".mbox":
                boxes.append(AMMailbox(dirent.path, parent=self))
        return boxes
    
    @property
    def all_children(self):
        boxes = []
        for box in self.children:
            boxes.append(box)
            boxes.extend(box.all_children)
        return boxes
    
    def _messages_at_path(self, path):
        messages_path = os.path.join(path, "Messages")
        messages = []
        
        # logging.debug("looking for messages in %s", messages_path)
        if os.path.exists(messages_path):
            if os.path.isdir(messages_path):
                for dirent in os.scandir(messages_path):
                    if dirent.is_file():
                        (name, ext) = os.path.splitext(dirent.name)
                        if ext == ".emlx":
                            (msgid, partial) = os.path.splitext(name)
                            msg = AMMessageRef(self, msgid, partial=(len(partial) != 0))
                            messages.append(msg)
                            # logging.debug("FOUND MESSAGE: %s", msg)
                    
            else:
                logging.debug("%s: not a directory; not considering for messages", messages_path)
        
        # Scan for tries and get their messages
        for dirent in os.scandir(path):
            if len(dirent.name) == 1 and dirent.name[0] in "0123456789":
                # logging.debug(" inspecting trie %s", dirent.name)
                trie_branch = os.path.join(path, dirent.name)
                messages.extend(self._messages_at_path(trie_branch))
        
        # logging.debug("found %d messages at %s", len(messages), messages_path)
        return messages
    
    @property
    def messages_path(self):
        data_dir = None
        # Our messages will be in a dir named with a GUID.
        for dirent in os.scandir(self.path):
            # GUID or GUID.noindex
            if len(dirent.name) == 36 or len(dirent.name) == 44:
                # logging.debug("looking for Data in %s", dirent.name)
                data_path = os.path.join(dirent.path, "Data")
                if os.path.isdir(data_path):
                    data_dir = data_path
                    break
        return data_dir
    
    def messages(self):
        data_dir = self.messages_path
                
        if data_dir is None:
            # logging.debug("%s: no messages found", self.path)
            return []
        
        messages = self._messages_at_path(data_dir)
        
        # logging.debug("found %d messages", len(messages))
        return messages
