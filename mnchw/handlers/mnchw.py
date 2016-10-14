# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _
from django.utils.timezone import now
from fuzzywuzzy import process
import parsley

from handlers.fuzzy import FuzzySubKeywordHandler
from locations.models import Location
from mnchw.models import NonCompliance, Report, Shortage
from reporters.models import PersistantConnection, Reporter, Role

commodity_codes = [choice[0] for choice in Report.IM_COMMODITIES]
reason_codes = [choice[0] for choice in NonCompliance.NC_REASONS]

grammar = parsley.makeGrammar('''
commodity_code = <letterOrDigit+>:code -> code
commodity_amt_pair = commodity_code:code ws <digit+>:amt -> (code, int(amt))
shortage_list_item = commodity_code:code ws -> code
report_list_item = commodity_amt_pair:pair ws -> pair
shortage_list = shortage_list_item+
report_list = report_list_item+
noncompliance = <digit+>:location_code ws <digit>:reason_code ws <digit+>:cases -> (location_code, reason_code, int(cases))
register = <digit+>:location_code ws <letterOrDigit+>:role_code ws <anything*>:full_name -> (location_code, role_code, full_name)
''', {})

ERROR_MESSAGES = {
    u'not_registered': _(u'Please register your number with RapidSMS before sending this report'),
    u'invalid_location': _(u'You sent an incorrect location code: %(location_code)s. You sent: %(text)s'),
    u'invalid_role': _(u'You sent an incorrect role code: %(role_code)s. You sent: %(text)s'),
    u'invalid_reason': _(u'You sent an incorrect reason: %(reason_code)s. You sent: %(text)s'),
    u'invalid_message': _(u'Your message is incorrect. Please send MNCHW HELP for help. You sent: %(text)s'),
}

HELP_MESSAGES = {
    None: _(u'Send MNCHW HELP NC for noncompliance help. Send MNCHW HELP REGISTER for registration help. Send MNCHW HELP REPORT for report help. Send MNCHW SHORTAGE HELP for shortage help'),
    u'nc': _(u'Send MNCHW NC location-code reason-code number-of-cases'),
    u'register': _(u'Send MNCHW REGISTER location-code role-code full-name'),
    u'report': _(u'Send MNCHW REPORT location-code commodity amount commodity amount commodity amount...'),
    u'shortage': _(u'Send MNCHW SHORTAGE location-code commodity commodity commodity...'),
}

RESPONSE_MESSAGES = {
    u'nc': _(u'Thank you for your MNCHW non-compliance report. Reason=%(reason)s, Cases=%(cases)d, Location=%(location)s %(location_type)s'),
    u'register': _(u'Hello %(name)s! You are now registered as %(role)s at %(location)s %(location_type)s'),
    u'already_registered': _(u'Hello %(name)s! You are already registered as a %(role)s at %(location)s %(location_type)s'),
    u'report': _(u'Thank you %(name)s. Received MNCHW report for %(location)s %(location_type)s: %(pairs)s'),
    u'shortage': _(u'Thank you for your MNCHW shortage report. Location=%(location)s %(location_type)s, commodity=%(commodity)s'),
}


class MNCHWHandler(FuzzySubKeywordHandler):
    '''Processes messages for the MNCHW app'''
    keyword = u'mnchw'
    subkeywords = [u'help', u'nc', u'register', u'report', u'shortage']

    def handle(self, text):
        # save connection
        connection = PersistantConnection.from_message(self.msg)
        self.persistent_connection = connection

        # mark connection as seen
        connection.seen()

        super(MNCHWHandler, self).handle(text)

    def handle_help(self, text):
        text = text.strip()

        if text == u'':
            self.respond(HELP_MESSAGES[None])
            return

        key = process.extractOne(text, self.subkeywords, score_cutoff=50)
        if key is None:
            self.respond(HELP_MESSAGES[None])
            return

        self.respond(HELP_MESSAGES[key[0]])

    def handle_nc(self, text):
        text = text.strip()

        if text == u'':
            self.respond(HELP_MESSAGES[u'nc'])
            return

        if self.persistent_connection.reporter is None:
            self.respond(ERROR_MESSAGES[u'not_registered'])
            return

        try:
            location_code, reason_code, cases = grammar(text).noncompliance()
        except parsley.ParseError:
            self.respond(ERROR_MESSAGES[u'invalid_message'] % {
                u'text': self.msg.text})
            return

        location = Location.get_by_code(location_code)
        if location is None:
            self.respond(ERROR_MESSAGES[u'invalid_location'] % {
                u'location_code': location_code, u'text': self.msg.text})
            return

        if reason_code not in reason_codes:
            self.respond(ERROR_MESSAGES[u'invalid_reason'] % {
                u'reason_code': reason_code, u'text': self.msg.text})

        NonCompliance.objects.create(reporter=self.persistent_connection.reporter,
            location=location, reason=reason_code, cases=cases, time=now(),
            connection=self.persistent_connection)

        self.respond(RESPONSE_MESSAGES[u'nc'] % {
            u'location': location.name, u'reason': report.get_reason_display(),
            u'cases': cases, u'location_type': location.type.name})

    def handle_register(self, text):
        text = text.strip()

        if text == u'':
            self.respond(HELP_MESSAGES[u'register'])
            return

        try:
            location_code, role_code, full_name = grammar(text).register()
        except parsley.ParseError:
            self.respond(ERROR_MESSAGES[u'invalid_message'] % {
                u'text': self.msg.text})
            return

        location = Location.get_by_code(location_code)
        if location is None:
            self.respond(ERROR_MESSAGES[u'invalid_location'] % {
                u'location_code': location_code, u'text': self.msg.text})
            return

        role = Role.get_by_code(role_code)
        if role is None:
            self.respond(ERROR_MESSAGES[u'invalid_role'] % {
                u'role_code': role_code, u'text': self.msg.text})
            return

        kwargs = {u'location': location, u'role': role}
        kwargs[u'alias'], kwargs[u'first_name'], kwargs[u'last_name'] = Reporter.parse_name(full_name)
        rep = Reporter(**kwargs)

        if self.persistent_connection.reporter and Reporter.exists(rep, self.persistent_connection):
            self.respond(RESPONSE_MESSAGES[u'already_registered'] % {
                u'name': rep.first_name, u'role': rep.role.name,
                u'location': rep.location.name,
                u'location_type': rep.location.type.name})
            return

        rep.save()
        self.persistent_connection.reporter = rep
        self.persistent_connection.save()

        self.respond(RESPONSE_MESSAGES[u'register'] % {u'name': rep.first_name,
            u'role': rep.role.code, u'location': rep.location.name,
            u'location_type': rep.location.type.name})

    def handle_report(self, text):
        text = text.strip()

        if text == u'':
            self.respond(HELP_MESSAGES[u'report'])
            return

        if self.persistent_connection.reporter is None:
            self.respond(ERROR_MESSAGES[u'not_registered'])
            return

        try:
            location_code, pairs = text.split(None, 1)
            pairs = grammar(pairs).report_list()
        except (ValueError, parsley.ParseError):
            self.respond(ERROR_MESSAGES[u'invalid_message'] % {
                u'text': self.msg.text})
            return

        location = Location.get_by_code(location_code)
        if location is None:
            self.respond(ERROR_MESSAGES[u'invalid_location'] % {
                u'location_code': location_code, u'text': self.msg.text})
            return

        amounts = []
        commodities = []
        for code, amount in pairs:
            result = process.extractOne(code, commodity_codes, score_cutoff=50)

            if result is None:
                continue

            comm = result[0]
            amounts.append(amount)
            commodities.append(comm.upper())

            Report.objects.create(reporter=self.persistent_connection.reporter,
                time=now(), connection=self.persistent_connection,
                location=location, commodity=comm, immunized=amount)

        response_pairs = u', '.join(u'{}={}'.format(a, b) for a, b in zip(commodities, amounts))
        self.respond(RESPONSE_MESSAGES[u'report'] % {u'location': location.name,
            u'location_type': location.type.name, u'pairs': response_pairs,
            u'name': self.persistent_connection.reporter.first_name})

    def handle_shortage(self, text):
        text = text.strip()

        if text == u'':
            self.respond(HELP_MESSAGES[u'shortage'])
            return

        if self.persistent_connection.reporter is None:
            self.respond(ERROR_MESSAGES[u'not_registered'])
            return

        try:
            location_code, codes = text.split(None, 1)
            codes = grammar(codes).shortage_list()
        except (ValueError, parsley.ParseError):
            self.respond(ERROR_MESSAGES[u'invalid_message'] % {
                u'text': self.msg.text})
            return

        location = Location.get_by_code(location_code)
        if location is None:
            self.respond(ERROR_MESSAGES[u'invalid_location'] % {
                u'location_code': location_code, u'text': self.msg.text})
            return

        results = [process.extractOne(c, codes, score_cutoff=50) for c in codes]
        commodity = None

        for result in results:
            if result is None:
                continue

            comm = result[0]

            if commodity is None:
                commodity = comm

            Shortage.objects.create(time=now(), commodity=comm,
                reporter=self.persistent_connection.reporter, location=location,
                connection=self.persistent_connection)

        self.respond(RESPONSE_MESSAGES[u'shortage'] % {u'location': location.name,
            u'location_type': location.type.name, u'commodity': commodity.upper()})

    def help(self):
        self.respond(HELP_MESSAGES[None])
