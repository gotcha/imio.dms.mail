# -*- coding: utf-8 -*-
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from zope.i18n import translate
from z3c.table.column import Column
from Products.CMFPlone.utils import safe_unicode
from collective.dms.basecontent.browser.listing import VersionsTitleColumn
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from imio.dms.mail import _

# z3c.table standard columns


class IMVersionsTitleColumn(VersionsTitleColumn):

    def getLinkTitle(self, item):
        obj = item.getObject()
        if not IScanFields.providedBy(obj):
            return
        scan_infos = [
            ('scan_id', item.scan_id or ''),
            ('scan_date', obj.scan_date and obj.toLocalizedTime(obj.scan_date, long_format=1) or ''),
            ('Version', obj.version or ''),
        ]
        scan_infos = ["%s: %s" % (
            translate(name, domain='collective.dms.scanbehavior', context=item.REQUEST), value)
            for (name, value) in scan_infos]

        return 'title="%s"' % '\n'.join(scan_infos)


class AssignedGroupColumn(Column):

    """Column that displays assigned group."""

    header = _("Treating groups")
    weight = 30

    def renderCell(self, item):
        if not item.assigned_group:
            return ''
        factory = getUtility(IVocabularyFactory, 'collective.task.AssignedGroups')
        voc = factory(item)
        return safe_unicode(voc.getTerm(item.assigned_group).title)
