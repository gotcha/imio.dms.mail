# -*- coding: utf-8 -*-
import os
from itertools import cycle
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from collective.dms.batchimport.utils import createDocument
from collective.dms.mailcontent.dmsmail import internalReferenceIncomingMailDefaultValue
from Products.CMFCore.utils import getToolByName
from datetime import datetime


def import_scanned(self, number=2):
    """
        Import some incoming mail for demo site
    """
    now = datetime.now()
    exm = self.REQUEST['PUBLISHED']
    path = os.path.dirname(exm.filepath())
    docs = {
        '59.PDF':
        {
            'c': {'mail_type': 'courrier', 'file_title': '010500000000001.pdf', 'recipient_groups': []},
            'f': {'scan_id': '010500000000001', 'pages_number': 1, 'scan_date': now,
                  'scan_user': 'Opérateur', 'scanner': 'Ricola'}
        },
        '60.PDF':
        {
            'c': {'mail_type': 'courrier', 'file_title': '010500000000002.pdf', 'recipient_groups': []},
            'f': {'scan_id': '010500000000002', 'pages_number': 1, 'scan_date': now,
                  'scan_user': 'Opérateur', 'scanner': 'Ricola'}
        },
    }
    docs_cycle = cycle(docs)

    class Dummy(object):
        def __init__(self, context, request):
            self.context = context
            self.request = request

    portal = getToolByName(self, "portal_url").getPortalObject()
    folder = portal['incoming-mail']
    count = 1
    limit = int(number)
    while(count <= limit):
        doc = docs_cycle.next()
        with open('%s/%s' % (path, doc), 'rb') as fo:
            file_object = NamedBlobFile(fo.read(), filename=unicode(doc))

        irn = internalReferenceIncomingMailDefaultValue(Dummy(portal, portal.REQUEST))
        doc_metadata = docs[doc]['c']
        doc_metadata['internal_reference_no'] = irn
        (document, main_file) = createDocument(
            Dummy(portal, portal.REQUEST),
            folder,
            'dmsincomingmail',
            '',
            file_object,
            owner='scanner',
            metadata=doc_metadata)
        for key, value in docs[doc]['f'].items():
            setattr(main_file, key, value)
        main_file.reindexObject(idxs=('scan_id', 'internal_reference_number'))
        count += 1
    return portal.REQUEST.response.redirect(folder.absolute_url())


def create_main_file(self, filename='', title=''):
    """
        Create a main file on context
    """
    if not filename:
        return "You must pass the filename parameter"
    exm = self.REQUEST['PUBLISHED']
    path = os.path.dirname(exm.filepath())
    filepath = os.path.join(path, filename)
    if not os.path.exists(filepath):
        return "The file path '%s' doesn't exist" % filepath
    with open(filepath, 'rb') as fo:
        file_object = NamedBlobFile(fo.read(), filename=unicode(filename))
        createContentInContainer(self, 'dmsmainfile', title='1', file=file_object)
