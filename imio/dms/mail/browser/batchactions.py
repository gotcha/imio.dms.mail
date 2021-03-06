# -*- coding: utf-8 -*-
"""Batch actions views."""

from operator import methodcaller

from zope import schema
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.lifecycleevent import modified

from AccessControl import getSecurityManager
from plone import api
from plone.supermodel import model
from plone.formwidget.masterselect import MasterSelectField
from z3c.form.form import Form
from z3c.form import button
from z3c.form.browser.select import SelectFieldWidget
from z3c.form.field import Fields
from z3c.form.interfaces import HIDDEN_MODE

from Products.CMFPlone import PloneMessageFactory as PMF
from Products.CMFPlone.utils import safe_unicode

from collective.task.behaviors import ITask
from collective.task import _ as TMF

from .. import _
from ..dmsmail import IImioDmsIncomingMail
from ..utils import get_selected_org_suffix_users


class IIMBatchActionsFormSchema(model.Schema):

    uids = schema.TextLine(
        title=u"uids",
        description=u''
    )

    referer = schema.TextLine(
        title=u'referer',
        required=False,
    )


class DashboardBatchActionForm(Form):

    label = _(u"Batch action form")
    fields = Fields(IIMBatchActionsFormSchema)
    fields['uids'].mode = HIDDEN_MODE
    fields['referer'].mode = HIDDEN_MODE
    ignoreContext = True
    brains = []

    def update(self):
        form = self.request.form
        if 'form.widgets.uids' in form:
            uids = form['form.widgets.uids']
        else:
            uids = self.request.get('uids', '')
            form['form.widgets.uids'] = uids

        if 'form.widgets.referer' not in form:
            form['form.widgets.referer'] = self.request.get('referer', '').replace('@', '&').replace('!', '#')

        self.brains = self.brains or brains_from_uids(uids)

#    @button.buttonAndHandler(PMF(u'Cancel'), name='cancel')
#    def handleCancel(self, action):
#        self.request.response.redirect(self.request.get('HTTP_REFERER'))


def brains_from_uids(uids):
    """ Returns a list of brains from a string containing uids separated by comma """
    uids = uids.split(',')
    catalog = api.portal.get_tool('portal_catalog')
    brains = catalog(UID=uids)
    return brains

# IM batch actions


def getAvailableTransitionsVoc(brains):
    """ Returns available transitions common for all brains """
    wtool = api.portal.get_tool(name='portal_workflow')
    terms = []
    transitions = None
    for brain in brains:
        obj = brain.getObject()
        if transitions is None:
            transitions = set([tr['id'] for tr in wtool.getTransitionsFor(obj)])
        else:
            transitions &= set([tr['id'] for tr in wtool.getTransitionsFor(obj)])
    if transitions:
        for tr in transitions:
            terms.append(SimpleTerm(tr, tr, PMF(safe_unicode(tr))))
    return SimpleVocabulary(terms)


class TransitionBatchActionForm(DashboardBatchActionForm):

    buttons = DashboardBatchActionForm.buttons.copy()
    label = _(u"Batch state change")

    def update(self):
        super(TransitionBatchActionForm, self).update()
        self.voc = getAvailableTransitionsVoc(brains_from_uids(self.request.form['form.widgets.uids']))
        self.fields += Fields(schema.Choice(
            __name__='transition',
            title=_(u'Transition'),
            vocabulary=self.voc,
            description=(len(self.voc) == 0 and
                         _(u'No common or available transition. Modify your selection.') or u''),
            required=len(self.voc) > 0))
        self.fields += Fields(schema.Text(
            __name__='comment',
            title=_(u'Comment'),
            description=_(u'Optional comment to display in history'),
            required=False))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply', condition=lambda fi: len(fi.voc))
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        if data['transition']:
            for brain in self.brains:
                obj = brain.getObject()
                api.content.transition(obj=obj, transition=data['transition'],
                                       comment=self.request.form.get('form.widgets.comment', ''))
        self.request.response.redirect(self.request.form['form.widgets.referer'])


class OldTreatingGroupBatchActionForm(DashboardBatchActionForm):

    def update(self):  # pragma: no cover
        super(TreatingGroupBatchActionForm, self).update()
        #voc = getAvailableTreatingGroupVoc(brains_from_uids(self.request.form['form.widgets.uids']))
        im_fields = Fields(IImioDmsIncomingMail)
        self.fields += im_fields.select('treating_groups')
        task_fields = Fields(ITask)
        self.fields += task_fields.select('assigned_user')
        fld = self.fields['treating_groups'].field
        fld.slave_fields[0]['name'] = 'assigned_user'
        fld.slave_fields[0]['slaveID'] = '#form-widgets-assigned_user'

        super(DashboardBatchActionForm, self).update()

#    def updateWidgets(self):
#        super(TreatingGroupBatchActionForm, self).updateWidgets()


def checkSelectionAboutTreatingGroup(brains):
    """ Check all brains to verify treating_groups change permission """
    pb = False
    sm = getSecurityManager()
    for brain in brains:
        obj = brain.getObject()
        if not sm.checkPermission('imio.dms.mail : Write treating group field', obj):
            pb = True
            break
    return pb


class TreatingGroupBatchActionForm(DashboardBatchActionForm):

    label = _(u"Batch treating group change")

    def update(self):
        super(TreatingGroupBatchActionForm, self).update()
        self.pb = checkSelectionAboutTreatingGroup(brains_from_uids(self.request.form['form.widgets.uids']))
        self.fields += Fields(schema.Choice(
            __name__='treating_group',
            title=_(u"Treating groups"),
            description=(self.pb and
                         _(u"You can't change this field on selected items. Modify your selection.") or u''),
            required=(self.pb and False or True),
            vocabulary=(self.pb and SimpleVocabulary([]) or u'collective.dms.basecontent.treating_groups'),
        ))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply', condition=lambda fi: not fi.pb)
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        if data['treating_group']:
            for brain in self.brains:
                obj = brain.getObject()
                obj.treating_groups = data['treating_group']
                modified(obj)
        self.request.response.redirect(self.request.form['form.widgets.referer'])


class RecipientGroupBatchActionForm(DashboardBatchActionForm):

    label = _(u"Batch recipient groups change")
    id = 'recipientgroup-batchaction-form'

    def update(self):
        super(RecipientGroupBatchActionForm, self).update()
        self.fields += Fields(MasterSelectField(
            __name__='action_choice',
            title=_(u'Batch action choice'),
            vocabulary=SimpleVocabulary([SimpleTerm(value=u'add', title=_(u'Add items')),
                                         SimpleTerm(value=u'remove', title=_(u'Remove items')),
                                         SimpleTerm(value=u'replace', title=_(u'Replace some items by others')),
                                         SimpleTerm(value=u'overwrite', title=_(u'Overwrite'))]),
            slave_fields=(
                {'name': 'removed_values',
                 'slaveID': '#form-widgets-removed_values',
                 'action': 'hide',
                 'hide_values': (u'add', u'overwrite'),
                 'siblings': True,
                 },
                {'name': 'added_values',
                 'slaveID': '#form-widgets-added_values',
                 'action': 'hide',
                 'hide_values': (u'remove'),
                 'siblings': True,
                 },
            ),
            required=True,
            default=u'add'
        ))
        self.fields += Fields(schema.List(
            __name__='removed_values',
            title=_(u"Removed values"),
            description=_(u"Select the values to remove (CTRL+click)"),
            required=False,
            value_type=schema.Choice(vocabulary=u'collective.dms.basecontent.recipient_groups'),
        ))
        self.fields += Fields(schema.List(
            __name__='added_values',
            title=_(u"Added values"),
            description=_(u"Select the values to add (CTRL+click)"),
            required=False,
            value_type=schema.Choice(vocabulary=u'collective.dms.basecontent.recipient_groups'),
        ))
        self.fields["removed_values"].widgetFactory = SelectFieldWidget
        self.fields["added_values"].widgetFactory = SelectFieldWidget

        super(DashboardBatchActionForm, self).update()

#        self.widgets['action_choice'].size = 4
        self.widgets['removed_values'].multiple = 'multiple'
        self.widgets['removed_values'].size = 5
        self.widgets['added_values'].multiple = 'multiple'
        self.widgets['added_values'].size = 5

    @button.buttonAndHandler(_(u'Apply'), name='apply')
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        if ((data.get('removed_values', None) and data['action_choice'] in ('remove', 'replace')) or
                (data.get('added_values', None)) and data['action_choice'] in ('add', 'replace', 'overwrite')):
            for brain in self.brains:
                obj = brain.getObject()
                if data['action_choice'] in ('overwrite'):
                    items = set(data['added_values'])
                else:
                    items = set(obj.recipient_groups or [])
                    if data['action_choice'] in ('remove', 'replace'):
                        items = items.difference(data['removed_values'])
                    if data['action_choice'] in ('add', 'replace'):
                        items = items.union(data['added_values'])
                obj.recipient_groups = list(items)
                modified(obj)
        self.request.response.redirect(self.request.form['form.widgets.referer'])


def getAvailableAssignedUserVoc(brains, attribute):
    """ Returns available assigned users common for all brains. """
    terms = []
    users = None
    for brain in brains:
        #obj = brain.getObject()
        if not getattr(brain, attribute):
            return SimpleVocabulary([])
        if users is None:
            users = set(get_selected_org_suffix_users(getattr(brain, attribute), ['editeur', 'validateur']))
        else:
            users &= set(get_selected_org_suffix_users(getattr(brain, attribute), ['editeur', 'validateur']))
    if users:
        for member in sorted(users, key=methodcaller('getUserName')):
            terms.append(SimpleTerm(
                value=member.getUserName(),  # login
                token=member.getId(),  # id
                title=member.getUser().getProperty('fullname') or member.getUserName()))  # title
    return SimpleVocabulary(terms)


class AssignedUserBatchActionForm(DashboardBatchActionForm):

    label = _(u"Batch assigned user change")
    master = 'treating_groups'
    err_msg = _(u'No common or available treating group, or no available assigned user. '
                'Modify your selection.')

    def update(self):
        super(AssignedUserBatchActionForm, self).update()
        self.voc = getAvailableAssignedUserVoc(self.brains, self.master)
        self.fields += Fields(schema.Choice(
            __name__='assigned_user',
            title=TMF(u'Assigned user'),
            vocabulary=self.voc,
            description=(len(self.voc) == 0 and self.err_msg or u''),
            required=(len(self.voc) and True or False)))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply', condition=lambda fi: len(fi.voc))
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        if data['assigned_user']:
            for brain in self.brains:
                obj = brain.getObject()
                obj.assigned_user = data['assigned_user']
                modified(obj)
        self.request.response.redirect(self.request.form['form.widgets.referer'])

# Task batch actions


class AssignedGroupBatchActionForm(DashboardBatchActionForm):

    label = _(u"Batch assigned group change")

    def update(self):
        super(AssignedGroupBatchActionForm, self).update()
        #self.pb = checkSelectionAboutTreatingGroup(brains_from_uids(self.request.form['form.widgets.uids']))
        self.pb = False
        self.fields += Fields(schema.Choice(
            __name__='assigned_group',
            title=TMF(u"Assigned group"),
            description=(self.pb and
                         _(u"You can't change this field on selected items. Modify your selection.") or u''),
            required=(self.pb and False or True),
            vocabulary=(self.pb and SimpleVocabulary([]) or u'collective.dms.basecontent.treating_groups'),
        ))

        super(DashboardBatchActionForm, self).update()

    @button.buttonAndHandler(_(u'Apply'), name='apply', condition=lambda fi: not fi.pb)
    def handleApply(self, action):
        """Handle apply button."""
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
        if data['assigned_group']:
            for brain in self.brains:
                obj = brain.getObject()
                obj.assigned_group = data['assigned_group']
                modified(obj)
        self.request.response.redirect(self.request.form['form.widgets.referer'])


class TaskAssignedUserBatchActionForm(AssignedUserBatchActionForm):

    master = 'assigned_group'
    err_msg = _(u'No common or available assigned group, or no available assigned user. '
                'Modify your selection.')
