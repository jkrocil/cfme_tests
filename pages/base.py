# -*- coding: utf-8 -*-

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from pages.page import Page
from selenium.webdriver.common.by import By

class Base(Page):
    '''
    Base class for global project specific functions
    '''
    @property
    def page_title(self):
        WebDriverWait(self.selenium, self.timeout).until(lambda s: self.selenium.title)
        return self.selenium.title

    @property
    def header(self):
        return Base.HeaderRegion(self.testsetup)

    @property
    def flash(self):
        return Base.FlashRegion(self)

    @property
    def is_logged_in(self):
        return self.header.is_logged_in

    @property
    def current_subpage(self):
        submenu_name = self.selenium.find_element_by_tag_name("body").get_attribute("id")
        return self.submenus[submenu_name](self.testsetup) #IGNORE:E1101

    @property
    def csrf_token(self):
        csrf_meta = self.selenium.find_element_by_css_selector("meta[name=csrf-token]")
        return csrf_meta.get_attribute('content')

    @csrf_token.setter
    def csrf_token(self, value):
        # Changing the CSRF Token on the fly via the DOM by iterating
        # over the meta tags
        script = '''
            var elements = document.getElementsByTagName("meta");
            for (var i=0, element; element = elements[i]; i++) {
                var ename = element.getAttribute("name");
                if (ename != null && ename.toLowerCase() == "csrf-token") {
                    element.setAttribute("content", "%s");
                    break;
                }
            }
        ''' % value
        self.selenium.execute_script(script)

    def go_to_login_page(self):
        self.selenium.get(self.base_url)

    class HeaderRegion(Page):
        # LoggedIn
        _logout_link_locator = (By.CSS_SELECTOR, "a[title='Click to Logout']")
        _user_indicator_locator = (By.CSS_SELECTOR, "div#page_header_div li.dropdown")
        _user_options_button_locator = (By.CSS_SELECTOR, "div#page_header_div b.caret")
        _user_options_locator = (By.CSS_SELECTOR, "ul#user_options_div")

        _site_navigation_menus_locator = (By.CSS_SELECTOR, "div.navbar > ul > li")
        _site_navigation_min_number_menus = 1

        @property
        def is_logout_visible(self):
            return self.is_element_visible(*self._logout_link_locator)

        @property
        def is_logged_in(self):
            return self.is_element_visible(*self._user_indicator_locator)

        @property
        def username(self):
            if self.is_logged_in:
                user_indicator = self.get_element(*self._user_indicator_locator)
                return user_indicator.text.split('|')[0].strip()
            else:
                return None

        def logout(self):
            options_button = self.selenium.find_element(*self._user_options_button_locator)
            options = self.selenium.find_element(*self._user_options_locator)
            logout_link = options.find_element(*self._logout_link_locator)
            ActionChains(self.selenium).move_to_element(options_button).click().move_to_element(logout_link).click().perform()
            from pages.login import LoginPage
            return LoginPage(self.testsetup)

        def site_navigation_menu(self, value):
            # used to access on specific menu
            for menu in self.site_navigation_menus:
                if menu.name == value:
                    return menu
            raise Exception("Menu not found: '%s'. Menus: %s" % (value, [menu.name for menu in self.site_navigation_menus]))

        @property
        def site_navigation_menus(self):
            # returns a list containing all the site navigation menus
            WebDriverWait(self.selenium, self.timeout).until(
                    lambda s: len(s.find_elements(*self._site_navigation_menus_locator))
                    >= self._site_navigation_min_number_menus)
            from pages.regions.header_menu import HeaderMenu
            return [HeaderMenu(self.testsetup, web_element) for web_element in self.selenium.find_elements(*self._site_navigation_menus_locator)]

    class FlashRegion(Page):
        # This whole class has no idea that there can be multiple flash messages :(
        _flash_div_locator = (By.CSS_SELECTOR, "div#flash_text_div")
        _flash_message_locator = (By.CSS_SELECTOR, "ul li")

        def __init__(self, page):
            self.page = page

        @property
        def div(self):
            self.page._wait_for_visible_element(*self._flash_div_locator)
            return self.page.get_element(*self._flash_div_locator)

        @property
        def message_item(self):
            return self.div.find_element(*self._flash_message_locator)

        @property
        def message(self):
            return self.message_item.text

        @property
        def is_error(self):
            return 'error' in self.message_item.get_attribute('class')

        def click(self):
            self.message_item.click()
