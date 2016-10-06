"""Helper functions related to the creation, listing, filtering and destruction of providers

The functions in this module that require the 'filters' parameter, such as list_providers,
list_provider_keys, setup_a_provider etc depend on a (by default global) dict of filters by default.
If you are writing tests or fixtures, you want to depend on those functions as de facto gateways.

The rest of the functions, such as get_mgmt, get_crud etc ignore this global dict and will provide
you with whatever you ask for with no limitations.

The main clue to know what is limited by the filters and what isn't is the 'filters' parameter.
"""
import random
from collections import Mapping, OrderedDict
from copy import copy

from fixtures.pytest_store import store
from cfme.common.provider import BaseProvider
from cfme.containers import provider as container_providers  # NOQA
from cfme.cloud import provider as cloud_providers  # NOQA
from cfme.exceptions import UnknownProviderType
from cfme.infrastructure import provider as infrastructure_providers  # NOQA
from cfme.middleware import provider as middleware_providers  # NOQA
from utils import conf, version
from utils.log import logger

providers_data = conf.cfme_data.get("management_systems", {})
# Dict of active provider filters {name: ProviderFilter}
global_filters = {}


class ProviderFilter(object):
    """ Filter used to obtain only providers matching given requirements

    Args:
        keys: List of acceptable provider keys, all if `None`
        categories: List of acceptable provider categories, all if `None`
        types: List of acceptable provider types, all if `None`
        required_fields: List of required fields,
                         see :py:func:`providers_by_type`
        restrict_version: Checks provider version in yamls if `True`
        required_tags: List of tags that must be set in yamls
        inverted: Inclusive if `False`, exclusive otherwise
    """
    _version_operator_map = OrderedDict([('>=', lambda o, v: o >= v),
                                        ('<=', lambda o, v: o <= v),
                                        ('==', lambda o, v: o == v),
                                        ('!=', lambda o, v: o != v),
                                        ('>', lambda o, v: o > v),
                                        ('<', lambda o, v: o < v)])

    def __init__(self, keys=None, categories=None, types=None, required_fields=None,
                 restrict_version=True, required_tags=None, inverted=False):
        self.keys = keys
        self.categories = categories
        self.types = types
        self.required_fields = required_fields
        self.restrict_version = restrict_version
        self.required_tags = required_tags
        self.inverted = inverted

    def _filter_restricted_version(self, provider):
        restricted_version = provider.data.get('restricted_version', None)
        if restricted_version:
            logger.info('we found a restricted version')
            for op, comparator in ProviderFilter._version_operator_map.items():
                # split string by op; if the split works, version won't be empty
                head, op, ver = restricted_version.partition(op)
                if not ver:  # This means that the operator was not found
                    continue
                if not comparator(version.current_version(), ver):
                    return False
                break
            else:
                raise Exception('Operator not found in {}'.format(restricted_version))
        return True

    def _filter_required_fields(self, provider, required_fields):
        for field_or_fields in required_fields:
            if isinstance(field_or_fields, tuple):
                field_ident, field_value = field_or_fields
            else:
                field_ident, field_value = field_or_fields, None
            if isinstance(field_ident, basestring):
                if field_ident not in provider.data:
                    return False
                else:
                    if field_value:
                        if provider.data[field_ident] != field_value:
                            return False
            else:
                o = provider.data
                try:
                    for field in field_ident:
                        o = o[field]
                    if field_value:
                        if o != field_value:
                            return False
                except (IndexError, KeyError):
                    return False
        return True

    def _filter_tags(self, provider, tags):
        if set(tags) & set(provider.data.tags):
            return True
        return False

    def _filter_test_flags(self, provider, test_flags):
        # check to make sure the provider contains that test_flag
        # if not, do not collect the provider for this particular test.
        if test_flags and test_flags != ['']:
            test_flags = [flag.strip() for flag in test_flags]

            defined_flags = conf.cfme_data.get('test_flags', '').split(',')
            defined_flags = [flag.strip() for flag in defined_flags]

            excluded_flags = provider.data.get('excluded_test_flags', '').split(',')
            excluded_flags = [flag.strip() for flag in excluded_flags]

            allowed_flags = set(defined_flags) - set(excluded_flags)

            if set(test_flags) - allowed_flags:
                logger.info("Filtering Provider %s out because it does not have the right flags, "
                            "%s does not contain %s",
                            provider.data['name'], list(allowed_flags),
                            list(set(test_flags) - allowed_flags))
                return False
        return True

    def _filter_by_version(self, provider):
        try:
            if "since_version" in provider.data:
                # Ignore providers that are not supported in this version yet
                if version.current_version() < provider.data["since_version"]:
                    return False
        except Exception:  # No SSH connection
            return False
        return True

    def __call__(self, provider):
        """ When an instance of this class is called, it will apply this filter on a given provider

        Usage:
            pf = ProviderFilter('cloud_infra', categories=['cloud', 'infra'])
            providers = list_providers([pf])
            pf2 = ProviderFilter(types=['openstack', 'ec2'], required_fields=['small_template'])
            provider_keys = list_provider_keys([pf, pf2])
            ...or...
            pf = ProviderFilter(required_tags=['openstack', 'complete'])
            pf_inverted = ProviderFilter(required_tags=['disabled'], inverted=True)
            providers = setup_a_provider([pf, pf_inverted])

        Returns:
            `True` if provider passed all checks and was not filtered out, `False` otherwise.
            The result is opposite if the 'inverted' attribute is set to `True`.
        """
        if self.keys and provider.key not in self.keys or \
           self.categories is not None and provider.category not in self.categories or \
           self.types is not None and provider.type not in self.types or \
           self.required_fields and not self._filter_required_fields(provider,
                                                                     self.required_fields) or \
           self.restrict_version and not self._filter_restricted_version(provider) or \
           self.required_tags and not self._filter_tags(provider, self.required_tags) or \
           self.rejected_tags and self._filter_tags(provider, self.rejected_tags):
            return self.inverted
        return not self.inverted

    def copy(self):
        return copy(self)


global_filters['enabled_only'] = ProviderFilter(required_tags=['disabled'], inverted=True)


def list_providers(filters=None, use_global_filters=True):
    """ Returns list of provider crud objects, optional filtering (enabled by default)

    Args:
        filters: List if :py:class:`ProviderFilter` or None
        use_global_filters: Will apply global filters as well if `True`, will not otherwise
    """
    filters = filters or []
    if use_global_filters:
        filters = filters + global_filters.items()
    providers = [get_crud(prov_key) for prov_key in providers_data]
    for prov_filter in filters:
        providers = filter(prov_filter, providers)
    return providers


def list_provider_categories():
    """ Returns list of currently known (registered) provider categories
    """
    return [p.category for p in BaseProvider.type_mapping.values()]


def list_provider_types(prov_categories=None):
    """ Returns list of currently known (registered) provider types of given categories

    Args:
        prov_categories: List of provider categories (infra, cloud, ...); not filtered if `None`
    """
    if prov_categories is not None:
        prov_types = [BaseProvider.type_mapping[pc].provider_types.keys() for pc in prov_categories]
    else:
        prov_types = [
            k2 for k in BaseProvider.type_mapping.values() for k2 in k.provider_types.keys()]
    return prov_types


def list_provider_keys(filters=None, use_global_filters=True):
    """ Returns list of provider keys, optional filtering

    Args:
        filters: List if :py:class:`ProviderFilter` or None
        use_global_filters: Will apply global filters as well if `True`, will not otherwise
    """
    return [p.key for p in list_providers(
        filters=filters, use_global_filters=use_global_filters)]


def existing_providers():
    """Lists all known providers that are already set up in the appliance."""
    return [prov for prov in list_providers() if prov.exists]


def _get_provider_class_by_type(prov_type):
    for cls in BaseProvider.type_mapping.itervalues():
        maybe_the_class = cls.provider_types.get(prov_type)
        if maybe_the_class is not None:
            return maybe_the_class
    raise UnknownProviderType("Unknown provider type: {}!".format(prov_type))


def setup_provider(provider_key, validate=True, check_existing=True):
    provider = get_crud(provider_key)
    return provider.create(validate_credentials=True, validate_inventory=validate,
                           check_existing=check_existing)


def setup_a_provider(filters=None, use_global_filters=True, validate=True, check_existing=True):
    """Sets up a single provider robustly.

    Does some counter-badness measures.

    Args:
        filters: List if :py:class:`ProviderFilter` or None
        use_global_filters: Will apply global filters as well if `True`, will not otherwise
        validate: Whether to validate the provider.
        check_existing: Whether to check if the provider already exists.
    """
    # TODO
    providers = list_providers(filters=filters)
    # If we didn't find any nonproblematic providers but we would have found some had we
    # included the problematic ones as well, we gotta clear the list of problematic providers
    problematic_filter = global_filters.get('problematic')
    # if not problematic, blabla TODO
    if not providers and provider_filter.ignore_problematic:
        tmp_filter = provider_filter.copy()
        tmp_filter.ignore_problematic = False
        if list_providers(provider_filter=tmp_filter):
            problematic_providers.clear()
            store.terminalreporter.write_line(
                "Reached the point where all possible providers forthis case are marked as bad. "
                "Clearing the bad provider list for a fresh start and next chance.", yellow=True)

    # If there is a provider that we want to specifically avoid ...
    # If there is only a single provider, then do not do any filtering
    # Specify `do_not_prefer` in provider's yaml to make it an object of avoidance.
    if len(providers) > 1:
        tmp_filter = provider_filter.copy()
        filtered_providers = [
            provider
            for provider
            in providers
            if not provider.data.get("do_not_prefer", False)]
        if filtered_providers:
            # If our filtering yielded any providers, use them, otherwise do not bother with that
            providers = filtered_providers

    # If there is already a suitable provider, don't try to setup a new one.
    already_existing = [prov for prov in providers if prov.exists]
    random.shuffle(already_existing)        # Make the provider load more even by random chaice.
    not_already_existing = [prov for prov in providers if not prov.exists]
    random.shuffle(not_already_existing)    # Make the provider load more even by random chaice.

    # So, make this one loop and it tries the existing providers first, then the nonexisting
    for provider in already_existing + not_already_existing:
        try:
            if provider in already_existing:
                store.terminalreporter.write_line(
                    "Trying to reuse provider {}\n".format(provider.key), green=True)
            else:
                store.terminalreporter.write_line(
                    "Trying to set up provider {}\n".format(provider.key), green=True)
            return setup_provider(validate_credentials=True, validate_inventory=validate,
                                   check_existing=check_existing)
        except Exception as e:
            # In case of a known provider error:
            logger.exception(e)
            message = "Provider {} is behaving badly, marking it as bad. {}: {}".format(
                provider.key, type(e).__name__, str(e))
            logger.warning(message)
            store.terminalreporter.write_line(message + "\n", red=True)
            problematic_providers.add(provider)
            if provider.exists:
                # Remove it in order to not explode on next calls
                provider.delete(cancel=False)
                provider.wait_for_delete()
                message = "Provider {} was deleted because it failed to set up.".format(
                    provider.key)
                logger.warning(message)
                store.terminalreporter.write_line(message + "\n", red=True)
    else:
        raise Exception("No providers could be set up matching the params")


def get_crud(provider_key):
    """
    Creates a Provider object given a management_system key in cfme_data.

    Usage:
        get_crud('ec2east')

    Returns: A Provider object that has methods that operate on CFME
    """
    prov_config = providers_data[provider_key]
    prov_type = prov_config.get('type')

    return _get_provider_class_by_type(prov_type).from_config(prov_config, provider_key)


def get_crud_by_name(provider_name):
    """
    Creates a Provider object given a management_system name in cfme_data.

    Usage:
        get_crud_by_name('My RHEV 3.6 Provider')

    Returns: A Provider object that has methods that operate on CFME
    """
    for provider_key, provider_data in providers_data.items():
        if provider_data.get("name") == provider_name:
            return get_crud(provider_key)
    else:
        raise NameError("Could not find provider {}".format(provider_name))


def get_mgmt(provider_key, providers=None, credentials=None):
    """
    Provides a ``mgmtsystem`` object, based on the request.

    Args:
        provider_key: The name of a provider, as supplied in the yaml configuration files.
            You can also use the dictionary if you want to pass the provider data directly.
        providers: A set of data in the same format as the ``management_systems`` section in the
            configuration yamls. If ``None`` then the configuration is loaded from the default
            locations. Expects a dict.
        credentials: A set of credentials in the same format as the ``credentials`` yamls files.
            If ``None`` then credentials are loaded from the default locations. Expects a dict.
    Return: A provider instance of the appropriate ``mgmtsystem.MgmtSystemAPIBase``
        subclass
    """
    if providers is None:
        providers = providers_data
    # provider_key can also be provider_data for some reason
    # TODO rename the parameter; might break things
    if isinstance(provider_key, Mapping):
        provider_data = provider_key
    else:
        provider_data = providers[provider_key]

    if credentials is None:
        # We need to handle the in-place credentials
        credentials = provider_data['credentials']
        # If it is not a mapping, it most likely points to a credentials yaml (as by default)
        if not isinstance(credentials, Mapping):
            credentials = conf.credentials[credentials]
        # Otherwise it is a mapping and therefore we consider it credentials

    # Munge together provider dict and creds,
    # Let the provider do whatever they need with them
    provider_kwargs = provider_data.copy()
    provider_kwargs.update(credentials)
    if isinstance(provider_key, basestring):
        provider_kwargs['provider_key'] = provider_key
    provider_kwargs['logger'] = logger

    return _get_provider_class_by_type(provider_data['type']).mgmt_class(**provider_kwargs)


class UnknownProvider(Exception):
    def __init__(self, provider_key, *args, **kwargs):
        super(UnknownProvider, self).__init__(provider_key, *args, **kwargs)
        self.provider_key = provider_key

    def __str__(self):
        return ('Unknown provider: "{}"'.format(self.provider_key))
