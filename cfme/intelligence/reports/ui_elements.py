# -*- coding: utf-8 -*-
from collections import Sequence, Mapping, Callable
from contextlib import contextmanager
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Calendar, Form, Region, Table, Select, fill
from utils import lazycache
from utils.log import logger


class NotDisplayedException(Exception):
    pass


class PivotCalcSelect(object):
    """This class encapsulates those JS pseudo-selects in Edit Report/Consolidation"""
    _entry = "//div[@class='dhx_combo_box']"
    _arrow = "//img[@class='dhx_combo_img']"
    _box = "//div[contains(@class, 'dhx_combo_list')]"
    _box_items = ".//div/div"
    _box_checkbox = ".//div/div[text()='{}']/preceding-sibling::*[1][@type='checkbox']"

    def __init__(self, root_el_id):
        self._id = root_el_id
        self._close_box = True

    @property
    def id(self):
        return self._id

    @classmethod
    def all(cls):
        """For debugging purposes"""
        return [
            cls(sel.get_attribute(x, "id"))
            for x
            in sel.elements("//td[contains(@id, 'pivotcalc_id_')]")
        ]

    def _get_root_el(self):
        return sel.element((By.ID, self._id))

    def _get_entry_el(self):
        return sel.element(self._entry, root=self._get_root_el())

    def _get_arrow_el(self):
        return sel.element(self._arrow, root=self._get_entry_el())

    def _open_box(self):
        self.close_all_boxes()
        sel.click(self._get_arrow_el())

    @classmethod
    def close_all_boxes(cls):
        """No other solution as the boxes have no ID"""
        for box in sel.elements(cls._box):
            sel.browser().execute_script(
                "if(arguments[0].style.display != 'none') arguments[0].style.display = 'none';", box
            )

    def _get_box(self):
        """Caching of the opened box"""
        if getattr(self, "_box_id", None) is None:
            self._open_box()
            for box in sel.elements(self._box):
                try:
                    sel.move_to_element(box)
                    if sel.is_displayed(box):
                        self._box_id = box.id
                        return box
                except sel.NoSuchElementException:
                    pass
            else:
                raise Exception("Could not open the box!")
        else:
            el = WebElement(sel.browser(), self._box_id)
            try:
                el.tag_name
                if not sel.is_displayed(el):
                    raise NotDisplayedException()
                return el
            except (StaleElementReferenceException, NoSuchElementException, NotDisplayedException):
                del self._box_id
                return self._get_box()

    def _get_box_items(self):
        return [sel.text(item) for item in sel.elements(self._box_items, root=self._get_box())]

    def _get_checkbox_of(self, name):
        return sel.element(self._box_checkbox.format(name), root=self._get_box())

    def clear_selection(self):
        for item in self._get_box_items():
            sel.uncheck(self._get_checkbox_of(item))
        if self._close_box:
            self.close_all_boxes()

    def items(self):
        result = self._get_box_items()
        if self._close_box:
            self.close_all_boxes()
        return result

    def check(self, item):
        return sel.check(self._get_checkbox_of(item))

    def uncheck(self, item):
        return sel.uncheck(self._get_checkbox_of(item))

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, str(repr(self._id)))

    def __str__(self):
        return repr(self)


@fill.method((PivotCalcSelect, basestring))
def _fill_pcs_str(o, s):
    logger.info("  Filling {} with string {}".format(str(o), str(s)))
    o.clear_selection()
    o.check(s)
    o.close_all_boxes()


@fill.method((PivotCalcSelect, Sequence))
def _fill_pcs_seq(o, l):
    logger.info("  Filling {} with sequence {}".format(str(o), str(l)))
    o.clear_selection()
    for name in l:
        o.check(name)
    o.close_all_boxes()


@fill.method((PivotCalcSelect, Callable))
def _fill_pcs_callable(o, c):
    logger.info("  Filling {} with callable {}".format(str(o), str(c)))
    for item in o.items():
        logger.info("    Calling callable on item {}".format(item))
        result = bool(c(item))
        logger.info("      Setting item {} to {}".format(item, str(result)))
        if result is True:
            o.check(item)
        else:
            o.uncheck(item)
    o.close_all_boxes()


@fill.method((PivotCalcSelect, Mapping))
def _fill_pcs_map(o, m):
    logger.info("  Filling {} with mapping {}".format(str(o), str(m)))
    for item, value in m.iteritems():
        value = bool(value)
        logger.info("  Setting item {} to {}".format(item, str(value)))
        if value:
            o.check(item)
        else:
            o.uncheck(item)
    o.close_all_boxes()


class RecordGrouper(object):
    """This class encapsulates the grouping editing in Edit Report/Consolidation"""
    def __init__(self, table_loc):
        self._table_loc = table_loc
        self.table = Table(table_loc)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, str(repr(self._table_loc)))


@fill.method((RecordGrouper, Mapping))
def _fill_recordgrouper(rg, d):
    logger.info("  Filling {} with data {}".format(str(rg), str(d)))
    for row_column_name, content in d.iteritems():
        row = rg.table.find_row("column_name", row_column_name)
        fill(PivotCalcSelect(sel.get_attribute(row.calculations, "id")), content)


class ColumnStyleTable(object):
    """We cannot inherit Table because it does too much WebElement chaining. This avoids that
    with using xpath-only locating making it much more reliable.

    Args:
        div_id: `id` of `div` where the table is located in.
    """
    def __init__(self, div_id):
        self._div_id = div_id

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, str(repr(self._div_id)))

    def get_style_select(self, name, id=0):
        """Return Select element with selected style.

        Args:
            name: Text written in leftmost column of the wanted row.
            id: Sequential id in the sub-row, 0..2.
        Returns: :py:class:`cfme.web_ui.Select`.
        """
        return Select(
            "//div[@id='{}']//table/tbody/tr/td[contains(@class, 'key') and .=' {}']/.."
            "/td[not(contains(@class, 'key'))]"
            "/select[@id[substring(., string-length() -1) = '_{}'] and contains(@id, 'style_')]"
            .format(self._div_id, name, id)
        )

    def get_if_select(self, name, id=0):
        """Return Select element with operator selection.

        Args:
            name: Text written in leftmost column of the wanted row.
            id: Sequential id in the sub-row, 0..2.
        Returns: :py:class:`cfme.web_ui.Select`.
        """
        return Select(
            "//div[@id='{}']//table/tbody/tr/td[contains(@class, 'key') and .=' {}']/.."
            "/td[not(contains(@class, 'key'))]"
            "/select[@id[substring(., string-length() -1) = '_{}'] and contains(@id, 'styleop')]"
            .format(self._div_id, name, id)
        )

    def get_if_input(self, name, id=0):
        """Return the `input` element with value selection.

        Args:
            name: Text written in leftmost column of the wanted row.
            id: Sequential id in the sub-row, 0..2.
        Returns: :py:class:`str` with locator.
        """
        return (
            "//div[@id='{}']//table/tbody/tr/td[contains(@class, 'key') and .=' {}']/.."
            "/td[not(contains(@class, 'key'))]"
            "/input[@id[substring(., string-length() -1) = '_{}'] and contains(@id, 'styleval')]"
            .format(self._div_id, name, id)
        )


@fill.method((ColumnStyleTable, Mapping))
def _fill_cst_map(cst, d):
    logger.info("  Filling {} with mapping {}".format(str(cst), str(d)))
    for key, values in d.iteritems():
        if not isinstance(values, Sequence) and not isinstance(values, basestring):
            values = [values]
        assert 1 <= len(values) <= 3, "Maximum 3 formatters"
        for i, value in enumerate(values):
            if isinstance(value, basestring):
                value = [value, "Default"]  # Default value when just string used.
            assert 2 <= len(value) <= 3, "Must be string or 2-or-3-tuple"
            fill(cst.get_style_select(key, i), value[0])
            fill(cst.get_if_select(key, i), value[1])
            if len(value) == 3:
                fill(cst.get_if_input(key, i), value[2])


class ColumnHeaderFormatTable(Table):
    """Used to fill the table with header names and value formatting."""
    pass


@fill.method((ColumnHeaderFormatTable, Mapping))
def __fill_chft_map(chft, d):
    logger.info("  Filling {} with mapping {}".format(str(chft), str(d)))
    for key, value in d.iteritems():
        row = chft.find_row("column_name", key)
        if isinstance(value, dict):
            header = value.get("header", None)
            format = value.get("format", None)
        elif isinstance(value, basestring):
            header = value
            format = None
        elif isinstance(value, Sequence):
            if len(value) == 1:
                header = value[0]
            elif len(value) == 2:
                header, format = value
            else:
                raise ValueError("Wrong sequence length")
        else:
            raise Exception()
        logger.info("   Filling values {}, {}".format(str(header), str(format)))
        fill(sel.element(".//input", root=row.header), header)
        fill(Select(sel.element(".//select", root=row.format)), format)


class MenuShortcuts(object):
    """This class operates the web ui object that handles adding new menus and shortcuts.

    Args:
        select_loc: Locator pointing to the selector.
    """
    def __init__(self, select_loc):
        self._select_loc = select_loc

    @property
    def select(self):
        return Select(self._select_loc)

    @property
    def opened_boxes_ids(self):
        """Return ids of all opened boxes."""
        return [
            # it's like 's_3'
            int(sel.get_attribute(el, "id").rsplit("_", 1)[-1])
            for el
            in sel.elements("//div[@title='Drag this Shortcut to a new location']")
            if sel.is_displayed(el)
        ]

    def close_box(self, id):
        sel.click("//a[@id='s_{}_close']".format(id))

    def get_text_of(self, id):
        return sel.get_attribute("//input[@id='shortcut_desc_{}']".format(id), "value")

    def set_text_of(self, id, text):
        sel.set_text("//input[@id='shortcut_desc_{}']".format(id), text)

    @lazycache
    def mapping(self):
        """Determine mapping Menu item => menu item id.

        Needed because the boxes with shortcuts are accessible only via ids.
        Need to close boxes because boxes displayed are not in the Select.
        """
        # Save opened boxes
        closed_boxes = []
        for box_id in self.opened_boxes_ids:
            closed_boxes.append((self.get_text_of(box_id), box_id))
            self.close_box(box_id)
        # Check the select
        result = {}
        for option in self.select.options:
            try:
                result[sel.text(option)] = int(sel.get_attribute(option, "value"))
            except (ValueError, TypeError):
                pass
        # Restore box layout
        for name, id in closed_boxes:
            sel.select(self.select, sel.ByValue(str(id)))
            self.set_text_of(id, name)

        return result

    def clear(self):
        """Clear the selection."""
        for id in self.opened_boxes_ids:
            self.close_box(id)

    def add(self, menu, alias=None):
        """Add a new shortcut.

        Args:
            menu: What menu item to select.
            alias: Optional alias for this menu item.
        """
        if menu not in self.mapping:
            raise NameError("Unknown menu location {}!".format(menu))
        sel.select(self.select, sel.ByValue(str(self.mapping[menu])))
        if alias is not None:
            self.set_text_of(self.mapping[menu], alias)


@fill.method((MenuShortcuts, Mapping))
def _fill_ms_map(ms, d):
    ms.clear()
    for menu, alias in d.iteritems():
        ms.add(menu, alias)


@fill.method((MenuShortcuts, Sequence))
def _fill_ms_seq(ms, seq):
    ms.clear()
    for menu in seq:
        ms.add(menu)


@fill.method((MenuShortcuts, basestring))
def _fill_ms_str(ms, s):
    fill(ms, [s])


class Timer(object):
    form = Form(fields=[
        ("run", Select("//select[@id='timer_typ']")),
        ("hours", Select("//select[@id='timer_hours']")),
        ("days", Select("//select[@id='timer_days']")),
        ("weeks", Select("//select[@id='timer_weeks']")),
        ("months", Select("//select[@id='timer_months']")),
        ("time_zone", Select("//select[@id='time_zone']")),
        ("start_date", Calendar("miq_date_1")),
        ("start_hour", Select("//select[@id='start_hour']")),
        ("start_min", Select("//select[@id='start_min']")),
    ])


@fill.method((Timer, Mapping))
def _fill_timer_map(t, d):
    return fill(t.form, d)


class ExternalRSSFeed(object):
    form = Region(locators=dict(
        rss_url=Select("//select[@id='rss_url']"),
        txt_url="//input[@id='txt_url']"
    ))


@fill.method((ExternalRSSFeed, basestring))
def _fill_rss_str(erf, s):
    try:
        sel.select(erf.form.rss_url, s)
    except NoSuchElementException:
        sel.select(erf.form.rss_url, "<Enter URL Manually>")
        sel.send_keys(erf.form.txt_url, s)


class DashboardWidgetSelector(object):
    _button_open_close = ".//img[contains(@src, 'combo_select.gif')]"
    _combo_list = "//div[contains(@class, 'dhx_combo_list') and div/div[.='Add a Widget']]"
    _selected = (".//div[@id='modules']//div[contains(@id, 'w_')]/div/h2/div"
        "/span[contains(@class, 'modtitle_text')]")
    _remove_button = ".//div[@id='modules']//div[contains(@id, 'w_')]/div"\
        "/h2[div/span[contains(@class, 'modtitle_text') and .='{}']]/a[@title='Remove this widget']"

    def __init__(self, root_loc="//div[@id='form_widgets_div']"):
        self._root_loc = root_loc

    def _open_close_combo(self):
        sel.click(sel.element(self._button_open_close, root=sel.element(self._root_loc)))

    @property
    def _is_combo_opened(self):
        return sel.is_displayed(self._combo_list)

    def _open_combo(self):
        if not self._is_combo_opened:
            self._open_close_combo()

    def _close_combo(self):
        if self._is_combo_opened:
            self._open_close_combo()

    @property
    @contextmanager
    def combo(self):
        self._open_combo()
        yield sel.element(self._combo_list)
        self._close_combo()

    @property
    def selected_items(self):
        self._close_combo()
        return [
            sel.text(item).encode("utf-8")
            for item
            in sel.elements(self._selected, root=sel.element(self._root_loc))
        ]

    def deselect(self, *items):
        self._close_combo()
        for item in items:
            sel.click(
                sel.element(
                    self._remove_button.format(item),
                    root=sel.element(self._root_loc)))

    def select(self, *items):
        for item in items:
            if item not in self.selected_items:
                with self.combo as combo:
                    sel.click(
                        sel.element("./div/div[contains(., '{}')]".format(item), root=combo))

    def clear(self):
        for item in self.selected_items:
            self.deselect(item)


@fill.method((DashboardWidgetSelector, Sequence))
def _fill_dws_seq(dws, seq):
    dws.clear()
    dws.select(*seq)


@fill.method((DashboardWidgetSelector, basestring))
def _fill_dws_str(dws, s):
    fill(dws, [s])
