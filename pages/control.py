# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from pages.control_subpages.explorer import Explorer
from pages.regions.taskbar.reload import ReloadMixin
from selenium.webdriver.support.ui import Select
import re


class Control(Base):
    @property
    def submenus(self):
        return {"miq_policy": Control.Explorer,
                "miq_policy_export": Control.ImportExport,
                "miq_policy_log": Control.Log
                }

    Explorer = Explorer

    class Simulation(Base):
        _page_title = "CloudForms Management Engine: Policy Simulation"
        pass  # Le stub

    class Log(Base, ReloadMixin):
        """ Log section of the Control tab

        Cannot download the file. Respectively I know about the workaround but I don't know
        whether it's appropriate.

        """
        _page_title = "CloudForms Management Engine: Control"
        _log_textarea_locator = (By.CSS_SELECTOR, "textarea#logview_data")
        _log_download_locator = (By.CSS_SELECTOR, "div#miq_alone > img[src*='download.png']")

        @property
        def log(self):
            return self.selenium.find_element(*self._log_textarea_locator).text.strip()

        @property
        def download(self):
            return self.selenium.find_element(*self._log_download_locator)

        @property
        def log_lines(self):
            return self.log.split("\n")

        def grep(self, regexp, whole=False):
            """ Applies regular expression on the whole content of log.

            @param whole: If True, re.match is used. Otherwise re.search
            """
            pattern = re.compile(regexp)
            if whole:
                return pattern.match(self.log)
            else:
                return pattern.search(self.log)

        def grep_line(self, regexp, match=False):
            """ Applies a regular expression line by line

            @param match: If True, re.match is used. Otherwise re.search
            """
            pattern = re.compile(regexp)
            match_func = pattern.match if match else pattern.search
            for line in self.log_lines:
                match = match_func(line)
                if match:
                    yield match

    class ImportExport(Base):
        _page_title = 'CloudForms Management Engine: Control'
        _upload_button = (By.ID, "upload_atags")
        _commit_button = (By.CSS_SELECTOR, "a[title='Commit Import']")
        _policy_import_field = (By.ID, "upload_file")
        _select_choices = (By.CSS_SELECTOR, "select#choices_chosen_")

        @property
        def upload(self):
            return self.selenium.find_element(*self._upload_button)

        @property
        def commit(self):
            return self.selenium.find_element(*self._commit_button)

        @property
        def select_choices(self):
            self._wait_for_visible_element(*self._select_choices, visible_timeout=5)
            return Select(self.selenium.find_element(*self._select_choices))

        @property
        def available_profiles(self):
            return [option.text for option in self.select_choices.options]

        def has_profile_available(self, profile_name):
            return profile_name in self.available_profiles

        def click_on_upload(self):
            self.upload.click()
            self._wait_for_results_refresh()
            return Control.ImportExport(self.testsetup)

        def click_on_commit(self):
            self.commit.click()
            self._wait_for_results_refresh()
            return Control.ImportExport(self.testsetup)

        def import_policies(self, import_policy_file):
            self.selenium.find_element(*self._policy_import_field).send_keys(import_policy_file)
            return self.click_on_upload()
