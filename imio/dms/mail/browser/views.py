# -*- coding: utf-8 -*-
from zope.i18n import translate

import json
from zope.interface import implements

from Products.CMFPlone.browser.ploneview import Plone
from Products.Five import BrowserView
from plone import api

from imio.helpers.fancytree.views import BaseRenderFancyTree
from eea.faceted.vocabularies.autocomplete import IAutocompleteSuggest

from imio.dms.mail import _


class PloneView(Plone):
    """
        Redefinition of plone view
    """

    def showEditableBorder(self):
        """Determine if the editable border (green bar) should be shown
        """
        return True


class CreateFromTemplateForm(BaseRenderFancyTree):

    """Create a document from a collective.documentgenerator template."""

    def label(self):
        return translate(
            _(u"${title}: create from template",
              mapping={'title': self.context.Title()}),
            context=self.request)

    def get_action_name(self):
        return translate(_("Choose this template"), context=self.request)

    def get_query(self):
        portal = api.portal.get()
        path = '/'.join(portal.getPhysicalPath()) + '/models'
        return {
            'path': {'query': path, 'depth': -1},
            'portal_type': (
                'Folder',
                'ConfigurablePODTemplate',
                'PODTemplate',
                'StyleTemplate',
                # 'SubTemplate',
                ),
        }

    def redirect_url(self, uid):
        """Redirect to document generation from selected template."""
        url = self.context.absolute_url()
        params = [
            "template_uid={}".format(uid),
            "output_format=odt",
        ]
        return  "{}/document-generation?{}".format(url, "&".join(params))


def parse_query(text):
    """ Copied from plone.app.vocabularies.catalog.parse_query but cleaned.
    """
    for char in '?-+*()':
        text = text.replace(char, ' ')
    query = {'SearchableText': " AND ".join(x + "*" for x in text.split())}
    return query


class ContactSuggest(BrowserView):
    """ Contact Autocomplete view """
    implements(IAutocompleteSuggest)

    label = u"Contact"

    def __call__(self):
        result = []
        query = self.request.get('term')
        if not query:
            return json.dumps(result)

        self.request.response.setHeader("Content-type", "application/json")
        query = parse_query(query)
        hp, org_bis = [], []
        all_str = _('All under')
        # search held_positions
        crit = {'portal_type': 'held_position', 'sort_on': 'sortable_title'}
        crit.update(query)
        brains = self.context.portal_catalog(**crit)
        for brain in brains:
            hp.append({'id': brain.UID, 'text': brain.get_full_title})
        # search organizations
        crit = {'portal_type': ('organization'), 'sort_on': 'sortable_title'}
        crit.update(query)
        brains = self.context.portal_catalog(**crit)
        make_bis = (len(hp) + len(brains)) > 1 and True or False
        for brain in brains:
            result.append({'id': brain.UID, 'text': brain.get_full_title})
            if make_bis:
                org_bis.append({'id': 'l:%s' % brain.UID, 'text': '%s [%s]' % (brain.get_full_title, all_str)})
        result += hp
        # search persons
        crit = {'portal_type': ('person'), 'sort_on': 'sortable_title'}
        crit.update(query)
        brains = self.context.portal_catalog(**crit)
        for brain in brains:
            result.append({'id': brain.UID, 'text': brain.get_full_title})
        # add organizations bis
        result += org_bis
        return json.dumps(result)
