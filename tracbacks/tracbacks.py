# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 The Open Planning Project
# Lines marked with #tino are NOT copyrighted.
#
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import re

from trac.core import *
from trac.resource import ResourceNotFound
from trac.ticket import ITicketChangeListener, Ticket
from trac.util.html import html as tag


try:
    basestring
except NameError:
    basestring = str


class TracBacksPlugin(Component):

    implements(ITicketChangeListener)

    TRACBACK_MAGIC_NUMBER = "{{{\n#!html\n<div class=\"tracback\"></div>\n}}}\n"
    TRACBACK_PREFIX = "This ticket has been referenced in ticket #"

    RE_TICKET = r"(?:^|\b|\s)(?:[#]|ticket:)(\d+)(?:\s|\b|$)"	#tino
    RE_DACT_1 = r"(\{\{\{((?!\{\{\{).)*?\}\}\})"		#tino
    RE_DACT_2 = r"`.*?`"					#tino

    re_0 = re.compile(RE_TICKET, re.DOTALL|re.VERBOSE)		#tino
    re_1 = re.compile(RE_DACT_1, re.DOTALL|re.VERBOSE)		#tino
    re_2 = re.compile(RE_DACT_2, re.DOTALL|re.VERBOSE)		#tino

    EXCERPT_CHARACTERS = 80
    WEED_BUFFER = 2

    def ticket_created(self, ticket):
        # Check for tracbacks on ticket creation.
        self.ticket_changed(ticket, ticket.values.get('description'),
                            ticket.values.get('reporter'), None)

    def ticket_changed(self, ticket, comment, author, old_values):

        if not isinstance(comment, basestring):
            return

        redacted	= self.redact(self.re_1, comment)	#tino
        redacted	= self.redact(self.re_2, redacted)	#tino
        tickets_referenced = self.re_0.findall(redacted)
        # convert from strings to ints and discard duplicates
        tickets_referenced = set(int(t) for t in tickets_referenced)
        # remove possible self-reference
        tickets_referenced.discard(ticket.id)

        # put trackbacks on the tickets that we found
        if self.is_tracback(comment): # prevent infinite recursion
            return
        for ticket_to_tracback in tickets_referenced:
            try:
                t = Ticket(self.env, ticket_to_tracback)
            except ResourceNotFound: # referenced ticket does not exist
                continue

            tracback = self.create_tracbacks(ticket, t, comment, redacted)
            t.save_changes(author, tracback)

    #tino replace everything we do not want with spaces
    #tino this keeps the offsets in sync with the original
    def redact(self,re,s):					#tino
        while True:						#tino
            m   = re.search(s)					#tino
            if not m: return s					#tino
            x   = m.start(0)					#tino
            y   = m.end(0)					#tino
            s   = s[0:x] + ' ' * (y-x) + s[y:]			#tino

    def ticket_deleted(self, ticket):
        pass

    def is_tracback(self, comment):
        return comment.startswith(self.TRACBACK_MAGIC_NUMBER)

    #tino get the position of all #id or ticket:id references
    def find_ref(self, comment, id):				#tino
        id = str(id)						#tino
        for m in self.re_0.finditer(comment):			#tino
            if m.group(1) == id:				#tino
                yield [m.start(1),len(m.group(0))]		#tino

    def create_tracbacks(self, ticket, ticket_to_tracback, comment, redacted):
        tracback = self.TRACBACK_MAGIC_NUMBER + self.TRACBACK_PREFIX + str(ticket.id) + ":"

        excerpts = []

        index = -1
        for [index,more] in self.find_ref(comment, ticket_to_tracback.id):	#tino

                start = index - self.EXCERPT_CHARACTERS
                end = index + more + self.EXCERPT_CHARACTERS

                left_ellipsis = "..."
                right_ellipsis = "..."

                if start <= 2:					#tino
                    left_ellipsis = ""
                    start = 0

                if end >= len(comment)-2:			#tino
                    right_ellipsis = ""

                excerpt = comment[start:end]
                excerpt = excerpt.replace("\n", ' ')		#tino
                excerpt = excerpt.replace("\r", ' ')		#tino

                # There's probably a better way to say this in python, but Tim doesn't know
                # how to do it. (He's tried """ but something's foobar'ed.)
                excerpts.append("\n> %s%s%s\n" % (left_ellipsis, excerpt, right_ellipsis))

        tracback += ''.join(excerpts)
        return tracback

