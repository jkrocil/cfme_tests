# -*- coding: utf-8 -*-

""" Module dealing with Configure/Tasks section.
"""
import attr

from navmazing import NavigateToAttribute
from widgetastic.utils import Version, VersionPick
from widgetastic.widget import View
from widgetastic_manageiq import BootstrapSelect, Button, CheckboxSelect, Table
from widgetastic_patternfly import Dropdown, Tab, FlashMessages

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError


table_loc = '//div[@id="gtl_div"]//table'

# Tasks table >= 5.9:
# (checkbox) | (status icon) | Started | Queued | State | Message | Task Name | User  | Server |
# -----------+---------------+---------+--------+-------+---------+-----------+-------+--------+
# dynamic    | dynamic       | opt     | opt    | opt   | stat    | opt       | stat  | stat   |
# started and queued = mm/dd/yy hh:mm:ss UTC


# Tasks table < 5.9:
# (checkbox) | (status icon) | Updated | Started | State | Message | Task Name | User  |
# -----------+---------------+---------+---------+-------+---------+-----------+-------+
# dynamic    | dynamic       | opt     | opt     | opt   | stat    | opt       | stat  |
# updated and started = mm/dd/yy hh:mm:ss UTC


#  TYPES = ['container', 'vm', 'host', 'datastore', 'cluster']
#  ^ obsolete, this should be handled inside the tests
STATUSES = ['queued', 'running', 'ok', 'error', 'warning']
STATE_FINISHED = 'finished'
# STATES = many (must be loaded dynamically)


# TODO ack 'analysis_finished'
@attr.s
class Task(BaseEntity):
    name = attr.ib()
    started = attr.ib()
    user = attr.ib(default='admin')
    server = attr.ib(default='EVM')    # >= 5.9 only
    tab = attr.ib(default='alltasks')

    @property
    def _row(self):
        view = navigate_to(self.parent, self.tab)
        row = view.table.row(task_name=self.name, started=self.started)
        return row

    @property
    def status(self):
        # TODO cache when state finished
        view = navigate_to(self.parent, self.tab)
        pass

    @property
    def updated(self):
        # TODO cache when state finished
        return self.row.updated if self.appliance.version < '5.9' else None

    @property
    def queued(self):
        # TODO cache when state finished
        return self.row.queued if self.appliance.version >= '5.9' else None

    @property
    def state(self):
        # TODO cache when state finished
        return self.row.state

    @property
    def message(self):
        # TODO cache when finished
        view = navigate_to(self.parent, self.tab)
        pass

    @property
    def exists(self):
        try:
            self._row
            return True
        except InderError:
            return False

    @property
    def is_finished(self):
        if self.state.lower() == STATE_FINISHED:
            return True
        return False

#    # throw exception if error in message
#    message = row.message.text.lower()
#    if 'error' in message:
#        raise Exception("Task {} error: {}".format(task_name, message))
#    elif 'timed out' in message:
#        raise TimedOutError("Task {} timed out: {}".format(task_name, message))
#    elif 'failed' in message:
#        raise Exception("Task {} has a failure: {}".format(task_name, message))
#
#    if clear_tasks_after_success:
#        # Remove all finished tasks so they wouldn't poison other tests
#        delete_all_tasks(destination)
#
#    return True

    def wait_finished(self, delay=5, timeout='5m'):
        view = navigate_to(self.parent, self.tab)
        wait_for(
            lambda: self.is_finished, delay=delay, timeout=timeout,
            fail_func=lambda: view.toolbar.reload.click)

    # TODO refactor
    def is_task_finished(destination, task_name, expected_status, clear_tasks_after_success=True):
        view = navigate_to(Tasks, destination)
        tab_view = getattr(view.tabs, destination.lower())
        try:
            row = tab_view.table.row(task_name=task_name, state=expected_status)
        except IndexError:
            logger.warn('IndexError exception suppressed when searching for task row, no match found.')
            return False

        # throw exception if error in message
        message = row.message.text.lower()
        if 'error' in message:
            raise Exception("Task {} error: {}".format(task_name, message))
        elif 'timed out' in message:
            raise TimedOutError("Task {} timed out: {}".format(task_name, message))
        elif 'failed' in message:
            raise Exception("Task {} has a failure: {}".format(task_name, message))

        if clear_tasks_after_success:
            # Remove all finished tasks so they wouldn't poison other tests
            delete_all_tasks(destination)

        return True

    # TODO refactor
    # This must be replaced with proper filtering through collection
    # and simply checking if the matching task `is_finished`
    # Clearing the tasks should be a thing of the past; we don't need to do that if we filter
    # correctly
    # ---- update
    # the tab and task name information needs to be moved out of here into wherever the
    # smartstate analysis is initiated
    def is_analysis_finished(name, task_type='vm', clear_tasks_after_success=True):
        """ Check if analysis is finished - if not, reload page"""

        tabs_data = {
            'container': {
                'tab': 'AllTasks',
                'task': '{}',
                'state': 'finished'
            },
            'vm': {
                'tab': 'AllTasks',
                'task': 'Scan from Vm {}',
                'state': 'finished'
            },
            'host': {
                'tab': 'MyOtherTasks',
                'task': "SmartState Analysis for '{}'",
                'state': 'Finished'
            },
            'datastore': {
                'tab': 'MyOtherTasks',
                'task': 'SmartState Analysis for [{}]',
                'state': "Finished"
            },
            'cluster': {
                'tab': 'MyOtherTasks',
                'task': 'SmartState Analysis for [{}]',
                'state': "Finished"}
        }[task_type]
        return is_task_finished(destination=tabs_data['tab'],
                                task_name=tabs_data['task'].format(name),
                                expected_status=tabs_data['state'],
                                clear_tasks_after_success=clear_tasks_after_success)


@attr.s
class TaskCollection(BaseCollection):
    """Collection object for :py:class:`cfme.configure.tasks.Task`."""
    ENTITY = Task
    tab = attr.ib(default='AllOtherTasks')

    def __init__(self, tab):
        """
        Args:
            tab: One of ['MyTasks', 'MyOtherTasks', 'AllTasks', 'AllOtherTasks'];
                 Set to 'AllOtherTasks' by default to display all tasks.
        """

    def instantiate():
        """ Represents a ManageIQ task

        Args:
            name: Name of the task
            updated: 'mm/dd/yy hh:mm:ss UTC' time of last update
            started: 'mm/dd/yy hh:mm:ss UTC' time of the task's start
            message: Message of the task
            user: User who initiated the task
            collection: Collection associated with the task; TaskCollection by default
            appliance: Appliance associated with the task; Current appliance by default


        """

    def switch_tab(self, tab):
        self.tab = tab

    def set_filter(zone=None, user=None, time_period=None, status=None, state=None, apply=True):
        # fill the view
        def _filter(
                zone=None,
                user=None,
                time_period=None,
                task_status_queued=None,
                task_status_running=None,
                task_status_ok=None,
                task_status_error=None,
                task_status_warn=None,
                task_state=None):
            """ Does filtering of the results in table. Needs to be on the correct page before called.

            If there was no change in the form and the apply button does not appear, nothing happens.

            Args:
                zone: Value for 'Zone' select
                user: Value for 'User' select
                time_period: Value for 'Time period' select.
                task_status_*: :py:class:`bool` values for checkboxes
                task_state: Value for 'Task State' select.
            """
            fill(filter_form, locals())
            try:
                wait_for(lambda: sel.is_displayed(buttons.apply), num_sec=5)
                sel.click(buttons.apply)
            except TimedOutError:
                pass

    def reset_filter(self):
        # fill(, reset=True)
        pass

    def set_default_filter(self):
        # fill(, default=True)
        pass

    def find(self, name, started, task_name, user):
        # Look for exact time
        pass

    def find_closest(self, name, started_after, task_name, user):
        # Look for nearest time
        pass

    def all(self, tab):
        view = navigate_to(self, 'All')
        # TODO row.name etc
        tasks = [self.instantiate(name=name, started=started, user=user, tab=self.tab)
                 for item in view.table.rows]
        return tasks

    def delete(self, *tasks):
        pass

    def delete_all(self):
        """Deletes all currently visible on page"""
        view = navigate_to(self, self.tab)
        view.delete.item_select('Delete All', handle_alert=True)


class TasksView(BaseLoggedInPage):
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')
    # Toolbar
    delete = Dropdown('Delete Tasks')  # dropdown just has icon, use element title
    reload = Button(title='Reload the current display')

    @View.nested
    class tabs(View):  # noqa
        # Extra Toolbar
        # Only on 'All' type tabs, but for access it doesn't make sense to access the tab for a
        # toolbar button
        cancel = Button(title='Cancel the selected task')

        # Form Buttons
        apply = Button('Apply')
        reset = Button('Reset')
        default = Button('Default')

        # Filters
        zone = BootstrapSelect(id='chosen_zone')
        period = BootstrapSelect(id='time_period')
        user = BootstrapSelect(id='user_choice')
        # This checkbox search_root captures all the filter options
        # It will break for status if/when there is second checkbox selection field added
        # It's the lowest level div with an id that captures the status checkboxes
        status = CheckboxSelect(search_root='tasks_options_div')
        state = BootstrapSelect(id='state_choice')

        @View.nested
        class mytasks(Tab):  # noqa
            TAB_NAME = VersionPick({
                Version.lowest(): 'My VM and Container Analysis Tasks',
                '5.9': 'My Tasks',
            })
            table = Table(table_loc)

        @View.nested
        class myothertasks(Tab):  # noqa
            TAB_NAME = VersionPick({'5.9': 'My Tasks',
                                    Version.lowest(): 'My Other UI Tasks'})
            table = Table(table_loc)

        @View.nested
        class alltasks(Tab):  # noqa
            TAB_NAME = VersionPick({'5.9': 'All Tasks',
                                    Version.lowest(): "All VM and Container Analysis Tasks"})
            table = Table(table_loc)

        @View.nested
        class allothertasks(Tab):  # noqa
            # Consolidated into 'All Tasks' in 5.9
            TAB_NAME = VersionPick({
                Version.lowest(): 'All Other Tasks',
                '5.9': 'All Tasks',
            })
            table = Table(table_loc)

    @property
    def is_displayed(self):
        return (
            self.tabs.mytasks.is_displayed and
            self.tabs.myothertasks.is_displayed and
            self.tabs.alltasks.is_displayed and
            self.tabs.allothertasks.is_displayed)


@navigator.register(TaskCollection, 'MyTasks')
class MyTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.mytasks.select()

    def am_i_here(self):
        return self.view.tabs.mytasks.is_active()


@navigator.register(TaskCollection, 'MyOtherTasks')
class MyOtherTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.myothertasks.select()

    def am_i_here(self):
        return self.view.tabs.myothertasks.is_active()


@navigator.register(TaskCollection, 'AllTasks')
class AllTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.alltasks.select()

    def am_i_here(self):
        return self.view.tabs.alltasks.is_active()


@navigator.register(TaskCollection, 'AllOtherTasks')
class AllOtherTasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToAttribute('appliance.server', 'Tasks')

    def step(self, *args, **kwargs):
        self.view.tabs.allothertasks.select()

    def am_i_here(self):
        return self.view.tabs.allothertasks.is_active()
