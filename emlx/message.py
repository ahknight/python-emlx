#!/usr/bin/env python

import plistlib  # 3.4+
from maildir_lite import MaildirMessage


class EmlxMessage(object):
    content = b""
    content_size = 0
    plist = {}
    
    def __init__(self, message=None):
        if isinstance(message, bytes):
            # The size of the message is the first line of the file.
            start = end = 0
            end = message.find(b'\n')
            if end is -1:
                return
            self.content_size = int(message[start:end])
            
            # Read in the message portion.
            start = end + 1
            end = start + self.content_size
            if start > 0 and end > 0:
                self.content = message[start:end]
            
            # Read in the plist metadata at the end.
            if start > 0 and end > 0:
                meta = message[end:]
                if meta:
                    self.plist = plistlib.loads(meta)
    
    def __str__(self):
        if not self.content:
            return ""
        return str(self.content)
    
    def __bytes__(self):
        content_size = str(self.content_size).encode("utf8")
        meta = plistlib.dumps(self.plist)
        return (content_size + b"\n" + self.content + meta)
    
    def as_string(self, *args, **kwargs):
        return str(self)
    
    def as_bytes(self, *args, **kwargs):
        return bytes(self)
    
    @property
    def flags(self):
        attrs = {}
        
        if 'flags' in self.plist:
            flags = int(self.plist['flags'])
            attrs['read']               = (flags & 1 << 0) > 0
            attrs['deleted']            = (flags & 1 << 1) > 0
            attrs['answered']           = (flags & 1 << 2) > 0
            attrs['encrypted']          = (flags & 1 << 3) > 0
            attrs['flagged']            = (flags & 1 << 4) > 0
            attrs['recent']             = (flags & 1 << 5) > 0
            attrs['draft']              = (flags & 1 << 6) > 0
            attrs['initial']            = (flags & 1 << 7) > 0
            attrs['forwarded']          = (flags & 1 << 8) > 0
            attrs['redirected']         = (flags & 1 << 9) > 0
            attrs['attachments']        = (flags & 3 << 10) >> 10 # (6 bits)
            attrs['priority']           = (flags & 7 << 16) >> 16 # (7 bits)
            attrs['signed']             = (flags & 1 << 23) > 0
            attrs['junk']               = (flags & 1 << 24) > 0
            attrs['not junk']           = (flags & 1 << 25) > 0
            attrs['font size delta']    = (flags & 7 << 26) >> 7 # (3 bits)
            attrs['junk set']           = (flags & 1 << 29) > 0
            attrs['highlight text in toc'] = (flags & 1 << 30) > 0
            attrs['(unused)']           = (flags & 1 << 31) > 0
            
        return attrs
    
    @property
    def date_sent(self):
        date = None
        DATE_SENT = 'date-sent'
        if DATE_SENT in self.plist and self.plist[DATE_SENT] is not 0:
            date = self.plist[DATE_SENT]
        return date

    @property
    def date_received(self):
        date = None
        DATE_RECEIVED = 'date-received'
        if DATE_RECEIVED in self.plist and self.plist[DATE_RECEIVED] is not 0:
            date = self.plist[DATE_RECEIVED]
        return date

    @property
    def date_last_viewed(self):
        date = None
        DATE_LAST_VIEWED = 'date-last-viewed'
        if DATE_LAST_VIEWED in self.plist and self.plist[DATE_LAST_VIEWED] is not 0:
            date = self.plist[DATE_LAST_VIEWED]
        return date
    
    def get_maildir_message(self):
        m = MaildirMessage(self.content)
        m.set_subdir("new")
        
        if self.date_received is not None:
            m.set_date(self.date_received)
        
        flags_dict = self.flags
        if flags_dict['draft']:
            m.add_flag('D')
        if flags_dict['flagged']:
            m.add_flag('F')
        if flags_dict['forwarded'] or flags_dict['redirected']:
            m.add_flag('P')
        if flags_dict['answered']:
            m.add_flag('R')
        if flags_dict['read']:
            m.add_flag('S')
        if flags_dict['deleted']:
            m.add_flag('T')
        
        return m

if __name__ == "__main__":
    import sys
    f = open(sys.argv[1], "rb")
    original = f.read()
    f.close()
    m = EmlxMessage(original)
    
    generated = bytes(m)
    print(original)
    print()
    print(generated)
