# -*- coding: utf-8 -*-
from functools import partial

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTree, flash, form_buttons, mixins, toolbar, Region
from utils import version
from utils.browser import ensure_browser_open
from utils.log import logger

pol_btn = partial(toolbar.select, "Policy")


class PolicyProfileAssignable(object):
    """This class can be inherited by anything that provider load_details method.

    It provides functionality to assign and unassign Policy Profiles"""
    manage_policies_tree = CheckboxTree("//div[@id='protect_treebox']/ul")

    @property
    def assigned_policy_profiles(self):
        try:
            return self._assigned_policy_profiles
        except AttributeError:
            self._assigned_policy_profiles = set([])
            return self._assigned_policy_profiles

    def assign_policy_profiles(self, *policy_profile_names):
        """ Assign Policy Profiles to this object.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        map(self.assigned_policy_profiles.add, policy_profile_names)
        self._assign_unassign_policy_profiles(True, *policy_profile_names)

    def unassign_policy_profiles(self, *policy_profile_names):
        """ Unssign Policy Profiles to this object.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        for pp_name in policy_profile_names:
            try:
                self.assigned_policy_profiles.remove(pp_name)
            except KeyError:
                pass
        self._assign_unassign_policy_profiles(False, *policy_profile_names)

    def _assign_unassign_policy_profiles(self, assign, *policy_profile_names):
        """DRY function for managing policy profiles.

        See :py:func:`assign_policy_profiles` and :py:func:`assign_policy_profiles`

        Args:
            assign: Wheter to assign or unassign.
            policy_profile_names: :py:class:`str` with Policy Profile names.
        """
        self.load_details(refresh=True)
        pol_btn("Manage Policies")
        for policy_profile in policy_profile_names:
            if assign:
                self.manage_policies_tree.check_node(policy_profile)
            else:
                self.manage_policies_tree.uncheck_node(policy_profile)
        sel.move_to_element({
            version.LOWEST: '#tP',
            "5.5": "//h3[1]"})
        form_buttons.save()
        flash.assert_no_errors()


class TagMixin(object):
    """Mixin class that enables an object to assign and unassign tags to itself

    Requirements:
        Subclass of this mixin must:
         - implement the 'load_details' method  - to navigate to the summary page of the object
           (preferably by inheriting GetDetailMixin)
         - implement the 'select' method - to mark a checkbox of the object either through
           a quadicon or through a list table
    """

    def load_details(self, refresh=False):
        raise NotImplementedError()

    def select(self):
        raise NotImplemented()

    def add_tag(self, tag, single_value=False, detail=True):
        if detail:
            self.load_details(refresh=True)
        else:
            self._nav_mark_only(self)
        mixins.add_tag(tag, single_value=single_value, navigate=True)

    def remove_tag(self, tag, detail=True):
        if detail:
            self.load_details(refresh=True)
        else:
            self._nav_mark_only(self)
        mixins.remove_tag(tag)

    def get_tags(self, tag="My Company Tags", detail=True):
        if detail:
            self.load_details(refresh=True)
        else:
            self._nav_mark_only(self)
        return mixins.get_tags(tag=tag)


class GetDetailMixin(object):
    """Mixin class that enables an object to fetch data from its summary page

    Requirements:
        Subclass of this mixin must:
         - have its 'title_text' set, otherwise its 'name' is used instead;
           it's necessary for header lookup
           (e.g. name / title_text 'ose3' -> header 'ose3 (Summary)')
         - implement the '_nav_to_detail' method used to navigate to the summary page of the object
    """
    details_page = Region(infoblock_type='detail')

    def _nav_to_detail(self):
        raise NotImplementedError()

    def _on_detail_page(self):
        """ Returns ``True`` if on the detail page, ``False`` if not.

        Depends on instance's 'title_text' or 'name' attribute.
        """
        if 'title_text' in self.dict:
            title_text = self.title_text
        elif 'name' in self.dict:
            title_text = self.name
        else:
            raise NotImplementedError()
        ensure_browser_open()
        return sel.is_displayed('//div//h1[contains(., "{} (Summary)")]'.format(title_text))

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            logger.debug("load_details: not on details already")
            self._nav_to_detail()
        elif refresh:
            toolbar.refresh()

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        self.load_details(refresh=True)
        return self.details_page.infoblock.text(*ident)
