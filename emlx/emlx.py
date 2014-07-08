#!/usr/bin/env python

import plistlib, email, mailbox

class EmlxMessage(object):
    msg = None
    plist = None
    
    def __init__(self, message=None):
        if isinstance(message, bytes):
            start = end = 0
            end = message.find(b'\n')
            if end is -1:
                return
            msg_size = int(message[start:end])
            
            start = end + 1
            end = start + msg_size
            if start > 0 and end > 0:
                self.msg = email.message_from_bytes(message[start:end])
            if start > 0 and end > 0:
                xml = message[end:]
                if xml:
                    self.plist = plistlib.loads(xml)
    
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
        if 'date-sent' in self.plist and self.plist['date-sent'] is not 0:
            date = self.plist['date-sent']
        return date

    @property
    def date_received(self):
        date = None
        if 'date-received' in self.plist and self.plist['date-received'] is not 0:
            date = self.plist['date-received']
        return date

    @property
    def date_last_viewed(self):
        date = None
        if 'date-last-viewed' in self.plist and self.plist['date-last-viewed'] is not 0:
            date = self.plist['date-last-viewed']
        return date
    
    def __bytes__(self):
        msg = bytes(self.msg)
        msg_size = bytes(str(len(msg)).encode("utf8"))
        meta = plistlib.dumps(self.plist)
        return (msg_size + b"\n" + msg + meta)
        
    def __str__(self):
        if not self.msg:
            return ""
        return str(self.msg)
    
    def __unicode__(self):
        if not self.msg:
            return ""
        return unicode(self.msg)
    
    def get_maildir_message(self):
        m = mailbox.MaildirMessage(self.msg)
        m.set_subdir("new")
        
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
        if self.date_received is not None:
            m.set_date(self.date_received)
        
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
