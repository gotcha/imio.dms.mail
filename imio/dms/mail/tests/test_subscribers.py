# -*- coding: utf-8 -*-
import unittest2 as unittest

import zope.event
from zope.lifecycleevent import ObjectModifiedEvent

from plone.app.testing import setRoles, TEST_USER_ID
from plone.dexterity.utils import createContentInContainer
from plone import api

from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.interfaces import IInternalContact, IExternalContact


class TestDmsmail(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_replace_scanner(self):
        with api.env.adopt_user(username='scanner'):
            imail = createContentInContainer(self.portal['incoming-mail'], 'dmsincomingmail',
                                             **{'title': 'IMail created by scanner'})
            dfile = createContentInContainer(imail, 'dmsmainfile', **{'title': 'File created by scanner'})
        self.assertEquals(imail.Creator(), 'scanner')
        self.assertEquals(imail.owner_info()['id'], 'scanner')
        self.assertEquals(imail.get_local_roles_for_userid('scanner'), ('Owner',))
        self.assertEquals(dfile.Creator(), 'scanner')
        self.assertEquals(dfile.owner_info()['id'], 'scanner')
        self.assertEquals(dfile.get_local_roles_for_userid('scanner'), ('Owner',))
        with api.env.adopt_user(username='encodeur'):
            imail.setTitle('IMail modified by encodeur')
            zope.event.notify(ObjectModifiedEvent(imail))
        self.assertEquals(imail.Creator(), 'encodeur')
        self.assertEquals(imail.owner_info()['id'], 'encodeur')
        self.assertEquals(imail.get_local_roles_for_userid('encodeur'), ('Owner',))
        self.assertEquals(imail.get_local_roles_for_userid('scanner'), ())
        self.assertEquals(dfile.Creator(), 'encodeur')
        self.assertEquals(dfile.owner_info()['id'], 'encodeur')
        self.assertEquals(dfile.get_local_roles_for_userid('encodeur'), ('Owner',))
        self.assertEquals(dfile.get_local_roles_for_userid('scanner'), ())

    def test_mark_organization(self):
        contacts = self.portal.contacts
        plonegroup_org = contacts['plonegroup-organization']
        external = api.content.create(
            type='organization', id='external', container=contacts)
        self.assertTrue(IExternalContact.providedBy(external))
        self.assertFalse(IInternalContact.providedBy(external))

        internal = api.content.create(
            type='organization', id='internal', container=plonegroup_org)
        self.assertTrue(IInternalContact.providedBy(internal))
        self.assertFalse(IExternalContact.providedBy(internal))

        api.content.move(source=internal, target=contacts)
        self.assertTrue(IExternalContact.providedBy(internal))
        self.assertFalse(IInternalContact.providedBy(internal))

        internal = api.content.create(
            type='person', id='person', container=contacts)
        self.assertTrue(IExternalContact.providedBy(external))
        self.assertFalse(IInternalContact.providedBy(external))
