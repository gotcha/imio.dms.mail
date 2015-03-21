from plone.dexterity.browser.edit import DefaultEditForm
from ..utils import voc_selected_org_suffix_users


def filter_task_assigned_users(group):
    """
        Filter assigned_user in dms incoming mail
    """
    return voc_selected_org_suffix_users(group, ['editeur'])


class TaskEdit(DefaultEditForm):
    """
      Edit view override of update
    """
    def update(self):
        super(TaskEdit, self).update()
        self.fields['ITask.assigned_group'].field.slave_fields[0]['vocab_method'] = filter_task_assigned_users
