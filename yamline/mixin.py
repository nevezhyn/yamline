from __future__ import absolute_import

import importlib
import re

import yaml

import yamline.literals as literals
from const import VAR_REGEXP, VAR_PLACEHOLDER_REGEXP


def _extract_var_name(str_to_parse):
    """
    Extracts a variable name from sting given by VAR_REGEXP = '(?<={{).*(?=}})'
    expression.

    Args:
        str_to_parse (str): A string to find a variable in.

    Returns:
        str: An extracted variable name
    """
    if str_to_parse and re.search(VAR_REGEXP, str_to_parse):
        var_name = re.search(VAR_REGEXP, str_to_parse).group().strip()
        return var_name


def _set_shared_var(var_name, var_value):
    """
    A helper function to set a shared variable. It uses a VarsBorg class
    internally.

    Args:
        var_name (str or iterable): Single name as a string or
            iterable of names as strings.
        var_value (object or iterable): Single object or iterable of
            objects.

    Returns:
        None

    Raises:
        RuntimeError: If the length of names iterables doesn't match length of
            values iterable.

    """
    if isinstance(var_name, str):
        setattr(VarsBorg(), var_name, var_value)

    if isinstance(var_name, list) or isinstance(var_name, tuple):
        if len(var_name) != len(var_value):
            raise RuntimeError('List set names and values mismatch!')
        for var, result in zip(var_name, var_value):
            setattr(VarsBorg(), var, result)
        return


def _parse_uri(uri):
    """
    Finds and returns Python callable or YAMLine element given by uri.

    Args:
        uri (str): A string with specification to import.

            eg.:
                strategy://path/to/module.callable

    Returns:
        object: A Python callable is uri is of 'strategy://' scheeme or
            a YAMLine element if 'import://' scheme.
    """

    def _get_yamline_element(authority):
        path_elements = authority.split('/')
        name = path_elements[-1]

        if name.endswith('.yaml') or name.endswith('.yml'):
            file_path = authority
            resutl = _parse_file(file_path)
            if not isinstance(resutl, dict):
                raise RuntimeError('Parsing error! Only Pipelines may '
                                   'be imported as .yaml files!')
            return resutl

        file_path = '/'.join(path_elements[:-1])
        file_spec = _parse_file(file_path)

        for element in file_spec:
            if all((literals.STEP_STRATEGY in element,
                    literals.STEP_NAME in element,
                    element[literals.STEP_NAME] == name)):
                return element

            if all((literals.STAGE_TRY in element,
                    literals.STAGE_NAME in element,
                    element[literals.STAGE_NAME] == name)):
                return element

        error_msg = 'Specified element: "{}" is not found in file: "{}"'
        raise RuntimeError(error_msg.format(name, file_path))

    def _get_python_callable(authority):
        callable_path = authority.split('/')
        callable_name = callable_path[-1]
        import_path = ".".join(callable_path[:-1])
        module_instance = importlib.import_module(import_path)

        attribute = getattr(module_instance, callable_name)

        if callable(attribute):
            return attribute

        raise RuntimeError('Strategy is not callable!')

    scheme, authority = uri.split('://')

    if scheme == literals.URI_SCHEME_STRATEGY:
        return _get_python_callable(authority)

    if scheme == literals.URI_SCHEME_IMPORT:
        return _get_yamline_element(authority)


def _parse_file(path_or_file):
    """
    Converts YAML file or file object to the Python object.

    Args:
        path_or_file (str or file):

    Returns:
        object: Result of yaml.load() execution over file or file object.

    Raises:
        RuntimeError: If any error when executing yaml.load().

    """
    if isinstance(path_or_file, file):
        spec_str = path_or_file.read()
        try:
            return yaml.load(spec_str)
        except Exception as e:
            print(e)
            msg = 'When converting YAML file to Python object ' \
                  'above error happened!'
            raise RuntimeError(msg)

    with open(path_or_file) as yaml_file:
        spec_str = yaml_file.read()
        try:
            return yaml.load(spec_str)
        except Exception as e:
            print(e)
            msg = 'When converting YAML file to Python object ' \
                  'above error happened!'
            raise RuntimeError(msg)


def _evaluate_when(spec_when):
    """
    Evaluates 'when: expression' and returns if when is True or False.

    Args:
        spec_when (str): A string to evaluate. If the string contains YAMLine
            variable (e.g. 'when: {{ var_name }} >= 0') then this YAMLine
            variable will be evaluated before evaluating whole 'spec_when'
            expression.

    Returns:
        bool: a result of evaluating 'bool(eval(spec_when))'

    """

    def _extract_var_placeholder(str_to_parse):
        if str_to_parse and re.search(VAR_REGEXP, str_to_parse):
            var_placeholder_str = re.search(VAR_PLACEHOLDER_REGEXP,
                                            str_to_parse).group().strip()
            return var_placeholder_str

    if isinstance(spec_when, str) and re.search(VAR_REGEXP, spec_when):
        var_name = _extract_var_name(spec_when)
        var_placeholder = _extract_var_placeholder(spec_when)
        full_name = 'shared_vars.' + var_name
        return bool(eval(spec_when.replace(var_placeholder, full_name)))

    if isinstance(spec_when, str):
        return bool(eval(spec_when))

    return bool(spec_when)


class Step(object):
    """Step class basic logic implemented"""

    def __init__(self, step_spec):
        self._spec_strategy = step_spec[literals.STEP_STRATEGY]
        self._spec_name = step_spec.get(literals.STEP_NAME, '')
        self._spec_sets = step_spec.get(literals.STEP_SETS, '')
        self._spec_args = step_spec.get(literals.STEP_ARGS, [])
        self._spec_kwargs = step_spec.get(literals.STEP_KWARGS, {})
        self._spec_when_condition = step_spec.get(literals.WHEN, '')
        self._is_conditional_step = literals.WHEN in step_spec

        self._callable_instance = _parse_uri(self._spec_strategy)
        if isinstance(self._spec_sets, str):
            self._sets_name = _extract_var_name(self._spec_sets)
        if isinstance(self._spec_sets, list):
            self._sets_name = self._from_list()

        self._result = None

    def execute(self):
        if self._callable_instance:
            if self._is_conditional_step:
                if _evaluate_when(self._spec_when_condition):
                    self._commit_call()
            else:
                self._commit_call()
            return self

        raise RuntimeError('Nothing to execute. Callable is not set!')

    def _from_list(self):
        return [_extract_var_name(var) for var in self._spec_sets]

    def _parse_args(self):
        args = []
        shared_vars = VarsBorg()
        for item in self._spec_args:
            if isinstance(item, str) and re.search(VAR_REGEXP, item):
                var_name = _extract_var_name(item)
                args.append(getattr(shared_vars, var_name))
            else:
                args.append(item)
        return args

    def _parse_kwargs(self):
        kwargs = {}
        shared_vars = VarsBorg()
        for key, value in self._spec_kwargs.items():
            if isinstance(value, str) and re.search(VAR_REGEXP, value):
                var_name = _extract_var_name(value)
                kwargs[key] = getattr(shared_vars, var_name)
            else:
                kwargs[key] = value
        return kwargs

    def _commit_call(self):
        args, kwargs = [], {}

        if self._spec_args:
            args = self._parse_args()

        if self._spec_kwargs:
            kwargs = self._parse_kwargs()

        self._result = self._callable_instance(*args, **kwargs)

        if self._sets_name:
            _set_shared_var(self._sets_name, self._result)


class Stage(object):
    """
    The Stage object is an ordered collection of routines. Stages control flow
    replicates the try-except block with some differences.
    """

    def __init__(self, stage_spec, parent):
        self._spec_try = stage_spec[literals.STAGE_TRY]
        self._spec_except = stage_spec.get(literals.STAGE_EXCEPT, [])
        self._spec_else = stage_spec.get(literals.STAGE_ELSE, [])
        self._spec_finally = stage_spec.get(literals.STAGE_FINALLY, [])
        self._spec_name = stage_spec.get(literals.STAGE_NAME, '')
        self._spec_when = stage_spec.get(literals.STAGE_WHEN, '')

        self._is_conditional_stage = literals.WHEN in stage_spec

        self._parent = parent

        self._try = self._parse_array(self._spec_try)
        self._except = self._parse_array(self._spec_except)
        self._else = self._parse_array(self._spec_else)
        self._finally = self._parse_array(self._spec_finally)

    def _parse_array(self, spec):
        return [get_pipeline_item(item_spec, self) for item_spec in spec]

    def raiser(self):
        if self._except:
            for item in self._except:
                item.execute()
            return

        if self._parent:
            self._parent.raiser()
            return

        if self._parent is None:
            raise

    def execute(self):
        if self._is_conditional_stage:
            when = _evaluate_when(self._spec_when)
            if not when:
                return
        try:
            for item in self._try:
                item.execute()
        except:
            self.raiser()

        else:
            for item in self._else:
                item.execute()
        finally:
            for item in self._finally:
                item.execute()


class Pipeline(object):
    """
    Pipeline is a top level YAMLine object. Pipeline is same as a Stage
    class with root stage equals to None and ability to set variables in
    the 'values' block before running the 'execute()' method.
    """

    def __init__(self, pipeline_spec, name=''):
        self._spec_aliases = pipeline_spec.get(literals.PIPELINE_ALIASES, '')
        self._spec_import = pipeline_spec.get(literals.PIPELINE_IMPORT, [])
        self._spec_metadata = pipeline_spec.get(literals.PIPELINE_METADATA, {})
        self._spec_values = pipeline_spec.get(literals.PIPELINE_VALUES, {})

        self._root_stage = get_pipeline_item(pipeline_spec, None)

        self._set_values()

    def _set_values(self):
        for var_name, var_value in self._spec_values.items():
            _set_shared_var(var_name, var_value)

    def execute(self):
        self._root_stage.execute()


class VarsBorg(object):
    """
    This class just holds all shared variables. No special logic in this class,
    just setters and getters.
    'reset()' method gives ability to reset all attributes and values.
    """
    __shared_vars = dict()

    def __init__(self):
        self.__dict__ = self.__shared_vars

    def __setattr__(self, key, value):
        self.__shared_vars[key] = value

    def __getattr__(self, item):
        return self.__shared_vars[item]

    def __delattr__(self, item):
        del self.__shared_vars[item]

    def __contains__(self, item):
        return item in self.__shared_vars

    def __len__(self):
        return len(self.__shared_vars)

    def reset(self):
        """
        Resets all shared attributes and theirs values.

        Returns:
            self: An instance of self with empty dict of shared variables.

        """
        self.__shared_vars = dict()
        return self


def get_pipeline(spec_path, alias_path=None):
    """
    This is a factory of Pipeline objects.

    Args:
        spec_path (str or file): A path to a file or a file object with
            a YAMLine script.
        alias_path (str or file): A path to a file or a file object with
            keywords aliases. This should be a path to a YAML file. If non
            given then default keywords will be used.

    Returns:
        Pipeline: A Pipeline object given by file specified in 'spec_path'
            argument.

    Raises:
        RuntimeError: If the aliases file is given and doesn't contain
            all required keywords.

    """

    def _validate_aliases():
        for required_literal in literals.REQUIRED_KEYS:
            if required_literal not in literals.__dict__:
                defaults = yaml.load(literals.DEFAULT_MAPPING)
                setattr(literals, required_literal, defaults[required_literal])
                raise RuntimeError(
                    "Parsing error! No alias for '{}'".format(
                        required_literal))

    def _set_aliases(aliases):
        """
        Sets aliases to literals. If alias is not provided, then will
        set default alias value.
        """
        for literal, alias in aliases.items():
            setattr(literals, literal, alias)
        _validate_aliases()

    spec = _parse_file(spec_path)

    if alias_path:
        aliases = _parse_file(alias_path)
    else:
        aliases = yaml.load(literals.DEFAULT_MAPPING)

    _set_aliases(aliases)
    borg = VarsBorg()
    borg.reset()
    return Pipeline(spec)


def get_pipeline_item(item_spec, parent_obj):
    """
    This is a factory of YAMLine items.

    Args:
        item_spec (dict): A YAMLine Stage, Step or Import item.
        parent_obj (None or Pipeline or Stage): Specifies reference to a
            parent object.

    Returns:
        Stage: If item_spec includes 'try' key.
        Step: If item_spec includes 'strategy' key.

    """
    if literals.STAGE_TRY in item_spec:
        # If dict with 'try' or alias, then this is Stage
        return Stage(item_spec, parent_obj)

    if literals.STEP_STRATEGY in item_spec:
        # If dict with 'strategy' or alias, then this is Step
        return Step(item_spec)

    if literals.URI_SCHEME_IMPORT in item_spec:
        # This may be any import. Use 'get_pipeline_item' factory.
        import_str = _parse_uri(item_spec[literals.URI_SCHEME_IMPORT])
        return get_pipeline_item(import_str, parent_obj)
