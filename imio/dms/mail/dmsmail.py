# -*- coding: utf-8 -*-
import copy

from zope import schema
from zope.component import getUtility
from zope.interface import implements
from zope.schema.fieldproperty import FieldProperty
#from plone.autoform.interfaces import IFormFieldProvider
from zope.schema.vocabulary import SimpleVocabulary
from z3c.form.interfaces import HIDDEN_MODE
from Products.CMFPlone.utils import base_hasattr
from plone import api
from plone.autoform import directives
from plone.dexterity.browser.add import DefaultAddView, DefaultAddForm
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.registry.interfaces import IRegistry
from plone.app.dexterity.behaviors.metadata import IDublinCore
from plone.app.dexterity.behaviors.metadata import IBasic
from plone.formwidget.datetime.z3cform.widget import DatetimeFieldWidget
from AccessControl import getSecurityManager

from collective.contact.plonegroup.browser.settings import SelectedOrganizationsElephantVocabulary
from collective.dms.basecontent.browser.views import DmsDocumentEdit, DmsDocumentView
from collective.dms.mailcontent.dmsmail import (IDmsIncomingMail, DmsIncomingMail, IDmsOutgoingMail,
                                                originalMailDateDefaultValue)
from collective.dms.basecontent.relateddocs import RelatedDocs
from collective.task.field import LocalRoleMasterSelectField
from dexterity.localrolesfield.field import LocalRolesField, LocalRoleField

from browser.settings import IImioDmsMailConfig
from utils import voc_selected_org_suffix_users

from . import _


def filter_dmsincomingmail_assigned_users(org_uid):
    """
        Filter assigned_user in dms incoming mail
    """
    return voc_selected_org_suffix_users(org_uid, ['editeur', 'validateur'])


class IImioDmsIncomingMail(IDmsIncomingMail):
    """
        Extended schema for mail type field
    """

    treating_groups = LocalRoleMasterSelectField(
        title=_(u"Treating groups"),
        required=True,
        vocabulary=u'collective.dms.basecontent.treating_groups',
        slave_fields=(
            {'name': 'ITask.assigned_user',
             'slaveID': '#form-widgets-ITask-assigned_user',
             'action': 'vocabulary',
             'vocab_method': filter_dmsincomingmail_assigned_users,
             'control_param': 'org_uid',
             'initial_trigger': True,
             },
        )
    )
    # Using write_permission hides field. Using display in edit view is preferred
    # directives.write_permission(treating_groups='imio.dms.mail.write_treating_group_field')

    recipient_groups = LocalRolesField(
        title=_(u"Recipient groups"),
        required=False,
        value_type=schema.Choice(vocabulary=u'collective.dms.basecontent.recipient_groups')
    )

    mail_type = schema.Choice(
        title=_("Mail type"),
#        description = _("help_mail_type",
#            default=u"Enter the mail type"),
        required=True,
        vocabulary=u'imio.dms.mail.IMActiveMailTypesVocabulary',
        default=None,
    )

    #password = schema.Password(
    #    title=_(u"Password"),
    #    description=_(u"Your password."),
    #    required=True,
    #    default='password'
    #)

    # doesn't work well if IImioDmsIncomingMail is a behavior instead a subclass
    directives.order_before(sender='recipient_groups')
    directives.order_before(mail_type='recipient_groups')
    directives.order_before(original_mail_date='recipient_groups')
    directives.order_before(reception_date='recipient_groups')
    directives.order_before(internal_reference_no='recipient_groups')
    directives.order_before(external_reference_no='recipient_groups')
    directives.order_before(notes='recipient_groups')
    directives.order_before(treating_groups='recipient_groups')

    directives.omitted('reply_to', 'related_docs', 'recipients', 'notes')
    #directives.widget(recipient_groups=SelectFieldWidget)

# Compatibility with old vocabularies
TreatingGroupsVocabulary = SelectedOrganizationsElephantVocabulary
RecipientGroupsVocabulary = SelectedOrganizationsElephantVocabulary


class ImioDmsIncomingMailSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):
        return (IImioDmsIncomingMail, )

#alsoProvides(IImioDmsIncomingMail, IFormFieldProvider) #needed for behavior


class ImioDmsIncomingMail(DmsIncomingMail):
    """
    """
    implements(IImioDmsIncomingMail)
    __ac_local_roles_block__ = False

    treating_groups = FieldProperty(IImioDmsIncomingMail[u'treating_groups'])
    recipient_groups = FieldProperty(IImioDmsIncomingMail[u'recipient_groups'])


def ImioDmsIncomingMailUpdateFields(the_form):
    """
        Fields update method for add and edit
    """
    the_form.fields['original_mail_date'].field = copy.copy(the_form.fields['original_mail_date'].field)
    settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
    if settings.original_mail_date_required:
        the_form.fields['original_mail_date'].field.required = True
    else:
        the_form.fields['original_mail_date'].field.required = False


def ImioDmsIncomingMailUpdateWidgets(the_form):
    """
        Widgets update method for add and edit
    """
    current_user = api.user.get_current()
    if not current_user.has_role('Manager') and not current_user.has_role('Site Administrator'):
        the_form.widgets['internal_reference_no'].mode = 'hidden'
        # we empty value to bypass validator when creating object
        if the_form.context.portal_type != 'dmsincomingmail':
            the_form.widgets['internal_reference_no'].value = ''

    for field in ['ITask.assigned_group', 'ITask.enquirer', 'IVersionable.changeNote']:
        the_form.widgets[field].mode = HIDDEN_MODE

    if the_form.widgets['original_mail_date'].field.required:
        if the_form.widgets['original_mail_date'].value == ('', '', ''):  # field value is None
            date = originalMailDateDefaultValue(None)
            the_form.widgets['original_mail_date'].value = (date.year, date.month, date.day)
    else:
        # if the context original_mail_date is already set, the widget value is good and must be kept
        if not base_hasattr(the_form.context, 'original_mail_date') or the_form.context.original_mail_date is None:
            the_form.widgets['original_mail_date'].value = ('', '', '')


class IMEdit(DmsDocumentEdit):
    """
        Edit form redefinition to customize fields.
    """

    def updateFields(self):
        super(IMEdit, self).updateFields()
        ImioDmsIncomingMailUpdateFields(self)
        #sm = getSecurityManager()
        #if not sm.checkPermission('imio.dms.mail : Write treating group field', self.context):
        #    self.fields['treating_groups'].field = copy.copy(self.fields['treating_groups'].field)
        #    self.fields['treating_groups'].field.required = False

    def updateWidgets(self):
        super(IMEdit, self).updateWidgets()
        ImioDmsIncomingMailUpdateWidgets(self)
        sm = getSecurityManager()
        incomingmail_fti = api.portal.get_tool('portal_types').dmsincomingmail
        behaviors = incomingmail_fti.behaviors
        display_fields = []
        if not sm.checkPermission('imio.dms.mail : Write incoming mail field', self.context):
            if IDublinCore.__identifier__ in behaviors:
                display_fields = [
                    'IDublinCore.title',
                    'IDublinCore.description']
            elif IBasic.__identifier__ in behaviors:
                display_fields = [
                    'IBasic.title',
                    'IBasic.description']

            display_fields.extend([
                'sender',
                'mail_type',
                'reception_date',
                'original_mail_date',
            ])

        if not sm.checkPermission('imio.dms.mail : Write treating group field', self.context):
            # cannot do disabled = True because ConstraintNotSatisfied: (True, 'disabled')
            #self.widgets['treating_groups'].__dict__['disabled'] = True
            self.widgets['treating_groups'].terms.terms = SimpleVocabulary(
                [t for t in self.widgets['treating_groups'].terms.terms if t.token == self.context.treating_groups])

        for field in display_fields:
            self.widgets[field].mode = 'display'

        # disable left column
        self.request.set('disable_plone.leftcolumn', 1)

        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        if settings.assigned_user_check and not self.context.assigned_user \
                and api.content.get_state(obj=self.context) == 'proposed_to_service_chief':
            self.widgets['ITask.assigned_user'].field = copy.copy(self.widgets['ITask.assigned_user'].field)
            self.widgets['ITask.assigned_user'].field.description = _(u'You must select an assigned user before you'
                                                                      ' can propose to an agent !')

    #def applyChanges(self, data):
    #    """ We need to remove a disabled field from data """
    #    sm = getSecurityManager()
    #    if not sm.checkPermission('imio.dms.mail : Write treating group field', self.context):
    #        del data['treating_groups']
    #    super(IMEdit, self).applyChanges(data)


class IMView(DmsDocumentView):
    """
        View form redefinition to customize fields.
    """

    def updateWidgets(self, prefix=None):
        super(IMView, self).updateWidgets()
        # this is added to escape treatment when displaying single widget in column
        #if prefix == 'escape':
        #    return
        for field in ['ITask.assigned_group', 'ITask.enquirer']:
            self.widgets[field].mode = HIDDEN_MODE

        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        if settings.assigned_user_check and not self.context.assigned_user \
                and api.content.get_state(obj=self.context) == 'proposed_to_service_chief':
            self.widgets['ITask.assigned_user'].field = copy.copy(self.widgets['ITask.assigned_user'].field)
            self.widgets['ITask.assigned_user'].field.description = _(u'You must select an assigned user before you'
                                                                      ' can propose to an agent !')


class CustomAddForm(DefaultAddForm):

    portal_type = 'dmsincomingmail'

    def updateFields(self):
        super(CustomAddForm, self).updateFields()
        ImioDmsIncomingMailUpdateFields(self)

    def updateWidgets(self):
        super(CustomAddForm, self).updateWidgets()
        ImioDmsIncomingMailUpdateWidgets(self)


class AddIM(DefaultAddView):

    form = CustomAddForm


class IImioDmsOutgoingMail(IDmsOutgoingMail):
    """
        Extended schema for mail type field
    """

    treating_groups = LocalRoleField(
        title=_(u"Treating groups"),
        required=True,
        vocabulary=u'collective.dms.basecontent.treating_groups',
    )

    recipient_groups = LocalRolesField(
        title=_(u"Recipient groups"),
        required=False,
        value_type=schema.Choice(vocabulary=u'collective.dms.basecontent.recipient_groups')
    )

    linked_mails = RelatedDocs(
        title=_(u"Linked mails"),
        required=False,
        portal_types=('dmsincomingmail', 'dmsoutgoingmail'))

    outgoing_date = schema.Datetime(title=_(u'Outgoing Date'), required=False)
    directives.widget(outgoing_date=DatetimeFieldWidget)

    directives.order_before(treating_groups='linked_mails')
    directives.order_before(sender='linked_mails')
    directives.order_before(recipients='linked_mails')
    directives.order_before(mail_date='linked_mails')
    directives.order_before(recipient_groups='linked_mails')
    directives.order_before(reply_to='linked_mails')
    directives.order_before(outgoing_date='linked_mails')
    directives.order_before(internal_reference_no='linked_mails')
    directives.order_before(notes='linked_mails')
    directives.order_before(linked_mails='linked_mails')
    directives.omitted('related_docs')


class ImioDmsOutgoingMailSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):
        return (IImioDmsOutgoingMail, )
