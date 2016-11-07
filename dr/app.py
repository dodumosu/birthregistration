# -*- coding: utf-8 -*-
import re

from django.utils.translation import ugettext as _
from fuzzywuzzy import process
import parsley
from rapidsms.apps.base import AppBase

from dr.models import FIELD_MAP, DeathReport
from reporters.models import PersistantConnection, Reporter, Role


grammar = parsley.makeGrammar('''
register = <digit+>:location_code ws <letterOrDigit+>:role_code ws <anything*>:full_name -> (location_code, role_code, full_name)
''', {})

ERROR_MESSAGES = {
    u'not_registered': _(u'Please register your number with RapidSMS before sending this report'),
    u'invalid_location': _(u'You sent an incorrect location code: %(location_code)s. You sent: %(text)s'),
    u'invalid_role': _(u'You sent an incorrect role code: %(role_code)s. You sent: %(text)s'),
    u'invalid_message': _(u'Your message is incorrect. Please send MNCHW HELP for help. You sent: %(text)s'),
}

HELP_MESSAGES = {
    None: _(u'Send DR HELP REGISTER for registration help. Send DR HELP REPORT for report help.'),
    u'register': _(u'Send DR REGISTER location-code role-code full-name.'),
    u'report': _(u'Please consult your training manual for how to send your report.'),
}

RESPONSE_MESSAGES = {
    u'register': _(u'Hello %(name)s! You are now registered as %(role)s at %(location)s %(location_type)s'),
    u'report': _(u'Thank you %(name)s. Received DR report for %(location)s %(location_type)s.')
}


class DeathRegistrationApp(AppBase):
    keyword = u'dr'
    subkeywords = [u'help', u'register', u'report']
    min_ratio = 70

    def parse(self, message):
        connection = PersistantConnection.from_message(message)
        message.persistant_connection = connection
        message.reporter = connection.reporter

        if message.reporter:
            message.persistance_dict = {u'reporter': message.reporter}
        else:
            message.persistance_dict = {u'connection': message.connection}

        connection.seen()

    def handle(self, message):
        text = message.text.lower().strip()

        if text.startswith(self.keyword):
            try:
                text = re.sub(self.keyword, u'', message.text, count=1)
                parts = text.split(None, 1)
            except ValueError:
                self.help(message)
                return True

            if len(parts) == 0:
                self.help(message)
                return True
            elif len(parts) == 1:
                subkeyword = parts[0]
                message_text = u''
            else:
                subkeyword, message_text = parts

            result = process.extractOne(subkeyword, self.subkeywords,
                score_cutoff=self.min_ratio)
            if result is None:
                self.help(message)
                return True

            handler_name, score = result
            handler = getattr(self, u'handle_{}'.format(handler_name))
            handler(message, message_text)
            return True

        return False

    def handle_register(self, message, message_text):
        text = message_text.strip()

        if text == u'':
            message.respond(HELP_MESSAGES[u'register'])
            return

        try:
            location_code, role_code, full_name = grammar(text).register()
        except parsley.ParseError:
            message.respond(ERROR_MESSAGES[u'invalid_message'] % {
                u'text': message.text})
            return

        location = Location.get_by_code(location_code)
        if location is None:
            message.respond(ERROR_MESSAGES[u'invalid_location'] % {
                u'location_code': location_code, u'text': message.text})
            return

        role = Role.get_by_code(role_code)
        if role is None:
            message.respond(ERROR_MESSAGES[u'invalid_role'] % {
                u'role_code': role_code, u'text': message.text})
            return

        kwargs = {u'location': location, u'role': role}
        kwargs[u'alias'], kwargs[u'first_name'], kwargs[u'last_name'] = Reporter.parse_name(full_name)
        rep = Reporter(**kwargs)

        if message.persistant_connection.reporter and Reporter.exists(rep, message.persistant_connection):
            message.respond(RESPONSE_MESSAGES[u'already_registered'] % {
                u'name': rep.first_name, u'role': rep.role.name,
                u'location': rep.location.name,
                u'location_type': rep.location.type.name})
            return

        rep.save()
        message.persistant_connection.reporter = rep
        message.persistant_connection.save()

        message.respond(RESPONSE_MESSAGES[u'register'] % {u'name': rep.first_name,
            u'role': rep.role.code, u'location': rep.location.name,
            u'location_type': rep.location.type.name})

    def handle_report(self, message, message_text):
        text = message_text.strip()

        if text == u'':
            message.respond(HELP_MESSAGES[u'register'])
            return

        pass

    def help(self, message):
        message.respond(HELP_MESSAGES[None])
