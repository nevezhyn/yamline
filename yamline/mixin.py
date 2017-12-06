import importlib
import re
import yaml

import yamline.literals as literals


def get_pipeline(spec_path, alias_path=None):
    spec = parse_file(spec_path)
    if alias_path:
        aliases = parse_file(alias_path)
    else:
        aliases = parse_yaml_string(literals.DEFAULT_MAPPING)
    set_aliases(aliases)
    borg = VarsBorg()
    borg.reset()
    return Pipeline(spec)


def get_pipeline_item(item_spec, parent_obj):
    if literals.STAGE_TRY in item_spec:
        return Stage(item_spec, parent_obj)

    if literals.STEP_STRATEGY in item_spec:
        return Step(item_spec)

    if literals.URI_SCHEME_IMPORT in item_spec:
        import_str = _parse_uri(item_spec[literals.URI_SCHEME_IMPORT])
        return get_pipeline_item(import_str, parent_obj)


def parse_array(spec, obj):
    return [get_pipeline_item(item_spec, obj) for item_spec in spec]


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
            self._sets_name = _extract_vars_from_list(self._spec_sets)

        self._result = None

    def execute(self):
        if self._callable_instance:
            if self._is_conditional_step:
                if evaluate_when(self._spec_when_condition):
                    self._commit_call()
            else:
                self._commit_call()
            return self

        raise RuntimeError('Nothing to execute. Callable is not set!')

    def _commit_call(self):
        args, kwargs = [], {}

        if self._spec_args:
            args = parse_args(self._spec_args)

        if self._spec_kwargs:
            kwargs = _parse_kwargs(self._spec_kwargs)

        self._result = self._callable_instance(*args, **kwargs)

        if self._sets_name:
            _set_shared_var(self._sets_name, self._result)


class Stage(object):
    """
    The Block object is an ordered collection of routines. Blocks control flow
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

        self._try = parse_array(self._spec_try, self)
        self._except = parse_array(self._spec_except, self)
        self._else = parse_array(self._spec_else, self)
        self._finally = parse_array(self._spec_finally, self)

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
            when = evaluate_when(self._spec_when)
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
    def __init__(self, pipeline_spec):
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
    """This class holds all shared variables."""
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
        self.__shared_vars = dict()
        return self


def evaluate_when(spec_when):
    if isinstance(spec_when, str) and re.search(VAR_REGEXP, spec_when):
        shared_vars = VarsBorg()
        var_name = _extract_var_name(spec_when)
        var_placeholder = _extract_var_placeholder(spec_when)
        full_name = 'shared_vars.' + var_name
        return bool(eval(spec_when.replace(var_placeholder, full_name)))

    if isinstance(spec_when, str):
        return bool(eval(spec_when))

    return bool(spec_when)


def parse_args(spec_args):
    args = []
    shared_vars = VarsBorg()
    for item in spec_args:
        if isinstance(item, str) and re.search(VAR_REGEXP, item):
            var_name = _extract_var_name(item)
            args.append(getattr(shared_vars, var_name))
        else:
            args.append(item)
    return args


def _parse_kwargs(spec_kwargs):
    kwargs = {}
    shared_vars = VarsBorg()
    for key, value in spec_kwargs.items():
        if isinstance(value, str) and re.search(VAR_REGEXP, value):
            var_name = _extract_var_name(value)
            kwargs[key] = getattr(shared_vars, var_name)
        else:
            kwargs[key] = value
    return kwargs


def _get_callable(authority):
    callable_path = authority.split('/')
    callable_name = callable_path[-1]
    import_path = ".".join(callable_path[:-1])
    module_instance = importlib.import_module(import_path)

    attribute = getattr(module_instance, callable_name)

    if callable(attribute):
        return attribute

    raise RuntimeError('Strategy is not callable!')


def _get_element(authority):
    path_elements = authority.split('/')
    name = path_elements[-1]

    if name.endswith('.yaml'):
        file_path = authority
        resutl = parse_file(file_path)
        if not isinstance(resutl, dict):
            raise RuntimeError('Parsing error! Only Pipelines may '
                               'be imported as .yaml files!')
        return resutl

    file_path = '/'.join(path_elements[:-1])
    file_spec = parse_file(file_path)

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


def _extract_var_name(str_to_parse):
    if str_to_parse and re.search(VAR_REGEXP, str_to_parse):
        var_name = re.search(VAR_REGEXP, str_to_parse).group().strip()
        return var_name


def _extract_vars_from_list(vars_list):
    return [_extract_var_name(var) for var in vars_list]


def _extract_var_placeholder(str_to_parse):
    if str_to_parse and re.search(VAR_REGEXP, str_to_parse):
        var_placeholder_str = re.search(VAR_PLACEHOLDER_REGEXP,
                                        str_to_parse).group().strip()
        return var_placeholder_str


def _set_shared_var(var_name, var_value):
    if isinstance(var_name, str):
        setattr(VarsBorg(), var_name, var_value)

    if isinstance(var_name, list) or isinstance(var_name, tuple):
        if len(var_name) != len(var_value):
            raise RuntimeError('List set names and values mismatch!')
        for var, result in zip(var_name, var_value):
            setattr(VarsBorg(), var, result)
        return


def _parse_uri(uri):
    scheme, authority = uri.split('://')

    if scheme == literals.URI_SCHEME_STRATEGY:
        return _get_callable(authority)

    if scheme == literals.URI_SCHEME_IMPORT:
        return _get_element(authority)


VAR_REGEXP = '(?<={{).*(?=}})'
VAR_PLACEHOLDER_REGEXP = '{{.*}}'


def parse_yaml_string(spec_str):
    return yaml.load(spec_str)


def validate_aliases():
    for required_literal in literals.REQUIRED_KEYS:
        if required_literal not in literals.__dict__:
            defaults = parse_yaml_string(literals.DEFAULT_MAPPING)
            setattr(literals, required_literal, defaults[required_literal])
            raise RuntimeError(
                "Parsing error! No alias for '{}'".format(required_literal))


def set_aliases(aliases):
    for literal, alias in aliases.items():
        setattr(literals, literal, alias)
    validate_aliases()


def parse_file(path):
    if isinstance(path, file):
        spec_str = path.read()
        try:
            return parse_yaml_string(spec_str)
        except:
            raise

    with open(path) as yaml_file:
        spec_str = yaml_file.read()
        try:
            return parse_yaml_string(spec_str)
        except:
            raise
