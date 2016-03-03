# encoding: utf-8
from zope.component import adapts, getMultiAdapter, getUtility
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary
from z3c.form.term import MissingChoiceTermsVocabulary, MissingTermsMixin
from z3c.form.interfaces import IContextAware, IDataManager

from AccessControl import getSecurityManager
from Products.CMFCore.interfaces import IContentish
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.CatalogTool import sortable_title
from Products.CMFPlone.utils import base_hasattr
from Products.PluginIndexes.common.UnIndex import _marker as common_marker
from plone import api
from plone.app.contentmenu.menu import ActionsSubMenuItem as OrigActionsSubMenuItem
from plone.app.contentmenu.menu import FactoriesSubMenuItem as OrigFactoriesSubMenuItem
from plone.app.contentmenu.menu import WorkflowMenu as OrigWorkflowMenu
from plone.app.contenttypes.indexers import _unicode_save_string_concat
from plone.indexer import indexer
from plone.rfc822.interfaces import IPrimaryFieldInfo

from collective import dexteritytextindexer
from collective.contact.core.content.organization import IOrganization
from collective.dms.scanbehavior.behaviors.behaviors import IScanFields
from dmsmail import IDmsIncomingMail

from utils import review_levels, highest_review_level, organizations_with_suffixes, get_scan_id

#######################
# Compound criterions #
#######################

default_criterias = {'dmsincomingmail': {'review_state': {'query': ['proposed_to_manager',
                                                                    'proposed_to_service_chief']}},
                     'task': {'review_state': {'query': ['to_assign', 'realized']}}}


def highest_validation_criterion(portal_type):
    """ Return a query criterion corresponding to current user highest validation level """
    groups = api.group.get_groups(user=api.user.get_current())
    highest_level = highest_review_level(portal_type, str([g.id for g in groups]))
    if highest_level is None:
        return default_criterias[portal_type]
    ret = {}
    criterias = review_levels[portal_type][highest_level]
    if 'st' in criterias:
        ret['review_state'] = {'query': criterias['st']}
    if 'org' in criterias:
        organizations = []
        for group in groups:
            if group.id.endswith(highest_level):
                organizations.append(group.id[:-len(highest_level)])
        ret[criterias['org']] = {'query': organizations}
    return ret


class IncomingMailHighestValidationCriterion(object):
    """
        Return catalog criteria following highest validation group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return highest_validation_criterion('dmsincomingmail')


class TaskHighestValidationCriterion(object):
    """
        Return catalog criteria following highest validation group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        return highest_validation_criterion('task')


class IncomingMailInTreatingGroupCriterion(object):
    """
        Return catalog criteria following treating group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, ['validateur', 'editeur', 'lecteur'])
        # if orgs is empty list, nothing is returned => ok
        return {'treating_groups': {'query': orgs}}


class IncomingMailInCopyGroupCriterion(object):
    """
        Return catalog criteria following recipient group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, ['validateur', 'editeur', 'lecteur'])
        # if orgs is empty list, nothing is returned => ok
        return {'recipient_groups': {'query': orgs}}


class TaskInAssignedGroupCriterion(object):
    """
        Return catalog criteria following assigned group member
    """

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        orgs = organizations_with_suffixes(groups, ['validateur', 'editeur', 'lecteur'])
        # if orgs is empty list, nothing is returned => ok
        return {'assigned_group': {'query': orgs}}


################
# GUI cleaning #
################

class ActionsSubMenuItem(OrigActionsSubMenuItem):

    def available(self):
        # plone.api.user.has_permission doesn't work with zope admin
        if not getSecurityManager().checkPermission('Manage portal', self.context):
            return False
        return super(ActionsSubMenuItem, self).available()


class FactoriesSubMenuItem(OrigFactoriesSubMenuItem):

    def available(self):
        # plone.api.user.has_permission doesn't work with zope admin
        if not getSecurityManager().checkPermission('Manage portal', self.context):
            return False
        return super(FactoriesSubMenuItem, self).available()


class WorkflowMenu(OrigWorkflowMenu):

    def getMenuItems(self, context, request):
        if not getSecurityManager().checkPermission('Manage portal', context):
            return []
        return super(WorkflowMenu, self).getMenuItems(context, request)


####################
# Indexes adapters #
####################

@indexer(IContentish)
def mail_type_index(obj):
    """ Index method escaping acquisition """
    if base_hasattr(obj, 'mail_type') and obj.mail_type:
        return obj.mail_type
    return common_marker


@indexer(IDmsIncomingMail)
def mail_date_index(obj):
    # No acquisition pb because mail_date isn't an attr but cannot store None
    if obj.original_mail_date:
        return obj.original_mail_date
    return common_marker


@indexer(IDmsIncomingMail)
def in_out_date_index(obj):
    # No acquisition pb because in_out_date isn't an attr
    return obj.reception_date


@indexer(IOrganization)
def org_sortable_title_index(obj):
    """ Return organization chain concatenated by | """
    # sortable_title(org) returns <plone.indexer.delegate.DelegatingIndexer object> that must be called
    parts = [sortable_title(org)() for org in obj.get_organizations_chain() if org.title]
    parts and parts.append('')
    return '|'.join(parts)


class ScanSearchableExtender(object):
    adapts(IScanFields)
    implements(dexteritytextindexer.IDynamicTextIndexExtender)

    def __init__(self, context):
        self.context = context

    def searchable_text(self):
        items = [self.context.id.endswith('.pdf') and self.context.id[0:-4] or self.context.id]
        tit = (self.context.title and self.context.title != self.context.id and
               (self.context.title.endswith('.pdf') and self.context.title[0:-4] or self.context.title) or u"")
        if tit:
            items.append(tit)
        (sid, sid_long, sid_short) = get_scan_id(self.context)
        if sid:
            if sid != items[0]:
                items.append(sid)
            items.append(sid_long)
            items.append(sid_short)
        if self.context.description:
            items.append(self.context.description)
        return u" ".join(items)

    def __call__(self):
        """ Extend the searchable text with a custom string """
        primary_field = IPrimaryFieldInfo(self.context)
        if primary_field.value is None:
            return self.searchable_text()
        mimetype = primary_field.value.contentType
        transforms = getToolByName(self.context, 'portal_transforms')
        value = str(primary_field.value.data)
        filename = primary_field.value.filename
        try:
            transformed_value = transforms.convertTo('text/plain', value,
                                                     mimetype=mimetype,
                                                     filename=filename)
            if not transformed_value:
                return self.searchable_text()
            ret = _unicode_save_string_concat(self.searchable_text(),
                                              transformed_value.getData())
            if ret.startswith(' '):
                ret = ret[1:]
            return ret
        except:
            return self.searchable_text()


class IdmSearchableExtender(object):
    """
        Extends SearchableText of incoming mail.
        Concatenate the contained dmsmainfiles scan_id infos.
    """
    adapts(IDmsIncomingMail)
    implements(dexteritytextindexer.IDynamicTextIndexExtender)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        brains = self.context.portal_catalog.unrestrictedSearchResults(portal_type='dmsmainfile',
                                                                       path={'query':
                                                                       '/'.join(self.context.getPhysicalPath()),
                                                                       'depth': 1})
        index = []
        for brain in brains:
            sid_infos = get_scan_id(brain)
            if sid_infos[0]:
                index += sid_infos
        if index:
            return u' '.join(index)


#########################
# vocabularies adapters #
#########################

class IMMCTV(MissingChoiceTermsVocabulary):
    """ Managing missing terms for IImioDmsIncomingMail. """

    def complete_voc(self):
        if self.field.getName() == 'mail_type':
            return getUtility(IVocabularyFactory, 'imio.dms.mail.IMMailTypesVocabulary')(self.context)
        elif self.field.getName() == 'assigned_user':
            return getUtility(IVocabularyFactory, 'plone.app.vocabularies.Users')(self.context)
        else:
            return SimpleVocabulary([])

    def getTerm(self, value):
        try:
            return super(MissingTermsMixin, self).getTerm(value)
        except LookupError:
            try:
                return self.complete_voc().getTerm(value)
            except LookupError:
                pass
        if (IContextAware.providedBy(self.widget) and not self.widget.ignoreContext):
            curValue = getMultiAdapter((self.widget.context, self.field), IDataManager).query()
            if curValue == value:
                return self._makeMissingTerm(value)
        raise

    def getTermByToken(self, token):
        try:
            return super(MissingTermsMixin, self).getTermByToken(token)
        except LookupError:
            try:
                return self.complete_voc().getTermByToken(token)
            except LookupError:
                pass
        if (IContextAware.providedBy(self.widget) and not self.widget.ignoreContext):
            value = getMultiAdapter((self.widget.context, self.field), IDataManager).query()
            term = self._makeMissingTerm(value)
            if term.token == token:
                return term
        raise LookupError(token)
