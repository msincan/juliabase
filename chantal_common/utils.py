#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Chantal, the samples database.
#
# Copyright (C) 2010 Forschungszentrum Jülich, Germany,
#                    Marvin Goblet <m.goblet@fz-juelich.de>,
#                    Torsten Bronger <t.bronger@fz-juelich.de>
#
# You must not use, install, pass on, offer, sell, analyse, modify, or
# distribute this software without explicit permission of the copyright holder.
# If you have received a copy of this software without the explicit permission
# of the copyright holder, you must destroy it immediately and completely.


from __future__ import absolute_import

import codecs, re, os.path, time
from smtplib import SMTPException
from functools import update_wrapper
import dateutil.tz
import django.http
import django.contrib.auth.models
from django.conf import settings
from django.utils.encoding import iri_to_uri
from django.forms.util import ErrorList, ValidationError
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import translation
from django.utils.translation import ugettext


class HttpResponseUnauthorized(django.http.HttpResponse):
    u"""The response sent back in case of a permission error.  This is another
    missing response class in Django.  I have no clue why they leave out such
    trivial code.
    """
    status_code = 401


class HttpResponseSeeOther(django.http.HttpResponse):
    u"""Response class for HTTP 303 redirects.  Unfortunately, Django does the
    same wrong thing as most other web frameworks: it knows only one type of
    redirect, with the HTTP status code 302.  However, this is very often not
    desirable.  In Django-RefDB, we've frequently the use case where an HTTP
    POST request was successful, and we want to redirect the user back to the
    main page, for example.

    This must be done with status code 303, and therefore, this class exists.
    It can simply be used as a drop-in replacement of HttpResponseRedirect.
    """
    status_code = 303

    def __init__(self, redirect_to):
        super(HttpResponseSeeOther, self).__init__()
        self["Location"] = iri_to_uri(redirect_to)


entities = {}
for line in codecs.open(os.path.join(os.path.dirname(__file__), "entities.txt"), encoding="utf-8"):
    entities[line[:12].rstrip()] = line[12]
entity_pattern = re.compile(r"&[A-Za-z0-9]{2,8};")

def substitute_html_entities(text):
    u"""Searches for all ``&entity;`` named entities in the input and replaces
    them by their unicode counterparts.  For example, ``&alpha;``
    becomes ``α``.  Escaping is not possible unless you spoil the pattern with
    a character that is later removed.  But this routine doesn't have an
    escaping mechanism.

    :Parameters:
      - `text`: the user's input to be processed

    :type text: unicode

    :Return:
      ``text`` with all named entities replaced by single unicode characters

    :rtype: unicode
    """
    result = u""
    position = 0
    while position < len(text):
        match = entity_pattern.search(text, position)
        if match:
            start, end = match.span()
            character = entities.get(text[start+1:end-1])
            result += text[position:start] + character if character else text[position:end]
            position = end
        else:
            result += text[position:]
            break
    return result


def get_really_full_name(user):
    u"""Unfortunately, Django's ``get_full_name`` method for users returns the
    empty string if the user has no first and surname set.  However, it'd be
    sensible to use the login name as a fallback then.  This is realised here.

    :Parameters:
      - `user`: the user instance
    :type user: ``django.contrib.auth.models.User``

    :Return:
      The full, human-friendly name of the user

    :rtype: unicode
    """
    return user.get_full_name() or unicode(user)


def append_error(form, error_message, fieldname="__all__"):
    u"""This function is called if a validation error is found in form data
    which cannot be found by the ``is_valid`` method itself.  The reason is
    very simple: For many types of invalid data, you must take other forms in
    the same view into account.

    See, for example, `split_after_deposition.is_referentially_valid`.

    :Parameters:
      - `form`: the form to which the erroneous field belongs
      - `error_message`: the message to be presented to the user
      - `fieldname`: the name of the field that triggered the validation
        error.  It is optional, and if not given, the error is considered an
        error of the form as a whole.

    :type form: ``forms.Form`` or ``forms.ModelForm``.
    :type fieldname: str
    :type error_message: unicode
    """
    # FixMe: Is it really a good idea to call ``is_valid`` here?
    # ``append_error`` is also called in ``clean`` methods after all.
    form.is_valid()
    form._errors.setdefault(fieldname, ErrorList()).append(error_message)


dangerous_markup_pattern = re.compile(r"([^\\]|\A)!\[|[\n\r][-=]")
def check_markdown(text):
    u"""Checks whether the Markdown input by the user contains only permitted
    syntax elements.  I forbid images and headings so far.

    :Parameters:
      - `text`: the Markdown input to be checked

    :Exceptions:
      - `ValidationError`: if the ``text`` contained forbidden syntax
        elements.
    """
    if dangerous_markup_pattern.search(text):
        raise ValidationError(_(u"You mustn't use image and headings syntax in Markdown markup."))


class _AddHelpLink(object):
    u"""Internal helper class in order to realise the `help_link` function
    decorator.
    """

    def __init__(self, original_view_function, help_link):
        self.original_view_function = original_view_function
        self.help_link = help_link
        update_wrapper(self, original_view_function)

    def __call__(self, request, *args, **kwargs):
        request.chantal_help_link = self.help_link
        return self.original_view_function(request, *args, **kwargs)


def help_link(link):
    u"""Function decorator for views functions to set a help link for the view.
    The help link is embedded into the top line in the layout, see the template
    ``base.html``.  Currently, it is prepended with ``"/trac/chantal/wiki/"``.

    :Parameters:
      - `link`: the relative URL to the help page.

    :type link: str
    """

    def decorate(original_view_function):
        return _AddHelpLink(original_view_function, link)

    return decorate


from django.conf import settings
if settings.WITH_EPYDOC:
    help_link = lambda x: lambda y: y


def successful_response(request, success_report=None, view=None, kwargs={}, query_string=u"", forced=False):
    u"""After a POST request was successfully processed, there is typically a
    redirect to another page – maybe the main menu, or the page from where the
    add/edit request was started.

    The latter is appended to the URL as a query string with the ``next`` key,
    e.g.::

        /chantal/6-chamber_deposition/08B410/edit/?next=/chantal/samples/08B410a

    This routine generated the proper ``HttpResponse`` object that contains the
    redirection.  It always has HTTP status code 303 (“see other”).

    :Parameters:
      - `request`: the current HTTP request
      - `success_report`: an optional short success message reported to the
        user on the next view
      - `view`: the view name/function to redirect to; defaults to the main
        menu page (same when ``None`` is given)
      - `kwargs`: group parameters in the URL pattern that have to be filled
      - `query_string`: the *quoted* query string to be appended, without the
        leading ``"?"``
      - `forced`: If ``True``, go to ``view`` even if a “next” URL is
        available.  Defaults to ``False``.  See `bulk_rename.bulk_rename` for
        using this option to generate some sort of nested forwarding.

    :type request: ``HttpRequest``
    :type success_report: unicode
    :type view: str or function
    :type kwargs: dict
    :type query_string: unicode
    :type forced: bool

    :Return:
      the HTTP response object to be returned to the view's caller

    :rtype: ``HttpResponse``
    """
    if success_report:
        messages.success(request, success_report)
    next_url = request.GET.get("next")
    if next_url is not None:
        if forced:
            # FixMe: Pass "next" to the next URL somehow in order to allow for
            # really nested forwarding.  So far, the “deeper” views must know
            # by themselves how to get back to the first one (which is the case
            # for all current Chantal views).
            pass
        else:
            # FixMe: So far, the outmost next-URL is used for the See-Other.
            # However, this is wrong behaviour.  Instead, the
            # most-deeply-nested next-URL must be used.  This could be achieved
            # by iterated unpacking.
            return HttpResponseSeeOther(next_url)
    if query_string:
        query_string = "?" + query_string
    # FixMe: Once chantal_common has gotten its main menu view, this must be
    # used here as default vor ``view`` instead of the bogus ``None``.
    return HttpResponseSeeOther(django.core.urlresolvers.reverse(view or None, kwargs=kwargs) + query_string)


def unicode_strftime(timestamp, format_string):
    u"""Formats a timestamp to a string.  Unfortunately, the built-in method
    ``strftime`` of ``datetime.datetime`` objects is not unicode-safe.
    Therefore, I have to do a conversion into an UTF-8 intermediate
    representation.  In Python 3.0, this problem is probably gone.

    :Parameters:
      - `timestamp`: the timestamp to be converted
      - `format_string`: The format string that contains the pattern (i.e. all
        the ``"%..."`` sequences) according to which the timestamp should be
        formatted.  Note that if it should be translatable, you mast do this in
        the calling context.

    :type timestamp: ``datetime.datetime``
    :type format_string: unicode

    :Return:
      the formatted timestamp, as a Unicode string

    :rtype: unicode
    """
    return timestamp.strftime(format_string.encode("utf-8")).decode("utf-8")


def adjust_timezone_information(timestamp):
    u"""Adds proper timezone information to the timestamp.  It assumes that the
    timestamp has no previous ``tzinfo`` set, but it refers to the
    ``TIME_ZONE`` Django setting.  This is the case with the PostgreSQL backend
    as long as http://code.djangoproject.com/ticket/2626 is not fixed.

    FixMe: This is not tested with another database backend except PostgreSQL.

    :Parameters:
      - `timestamp`: the timestamp whose ``tzinfo`` should be modified

    :type timestamp: ``datetime.datetime``

    :Return:
      the timestamp with the correct timezone setting

    :rtype: ``datetime.datetime``
    """
    return timestamp.replace(tzinfo=dateutil.tz.tzlocal())


def send_email(subject, content, recipients, format_dict=None):
    u"""Sends one email to a user.  Both subject and content are translated to
    the recipient's language.  To make this work, you must tag the original
    text with a dummy ``_`` function in the calling content, e.g.::

        _ = lambda x: x
        send_mail(_("Error notification"), _("An error has occured."), user)
        _ = ugettext

    If you need to use string formatting à la

    ::

        ``"Hello {name}".format(name=user.name)``,

    you must pass a dictionary like ``{"name": user.name}`` to this function.
    String formatting must be done here, otherwise, translating wouldn't work.

    :Parameters:
      - `subject`: the subject of the email
      - `content`: the content of the email; it may contain substitution tags
      - `recipients`: the recipients of the email
      - `format_dict`: the substitions used for the ``format`` string method
        for both the subject and the content

    :type subject: unicode
    :type content: unicode
    :type recipient: ``django.contrib.auth.models.User`` or list of
      ``django.contrib.auth.models.User``
    :type format_dict: dict mapping unicode to unicode
    """
    current_language = translation.get_language()
    if not isinstance(recipients, list):
        recipients = [recipients]
    if settings.DEBUG:
        recipients = list(django.contrib.auth.models.User.objects.filter(username=settings.DEBUG_EMAIL_REDIRECT_USERNAME))
    for recipient in recipients:
        translation.activate(recipient.chantal_user_details.language)
        subject, content = ugettext(subject), ugettext(content)
        if format_dict is not None:
            subject = subject.format(**format_dict)
            content = content.format(**format_dict)
        cycles_left = 3
        while cycles_left:
            try:
                send_mail(subject, content, settings.DEFAULT_FROM_EMAIL, [recipient.email])
            except SMTPException:
                cycles_left -= 1
                time.sleep(0.3)
            else:
                break
    translation.activate(current_language)
