# YAMLine scripting language
## 1. Intent
YAMLine is simple scripting language that is tightly connected with a Python 
programming language. YAMLine is inspired both by 
[Ansible Playbooks](http://docs.ansible.com/ansible/latest/playbooks_intro.html#playbook-language-example)
and [Jenkins Pipelines](https://jenkins.io/doc/book/pipeline/).
A general intent is to create a scripting language that will mimic [Deployment Pipelines](https://en.wikipedia.org/wiki/Continuous_delivery#Deployment_pipeline)
but may be used for a more general tasks.

Under the hood the YAMLine just sequentially executes the Python callables.
An example:
```yaml
name: Unittest test template

metadata:
  mapping:
    key1: value1
    key2: value2
  sequence:
    - String
    - 1
    - 1.0
  string: "String"
  ineger: 1
  floating: 1.0

values:
  mapping_value:
    key1: value1
    key2: value2
  sequence:
   - 1
   - 2
  string: "String"
  ineger: 1
  floating: 1.0

try:
  - name: Test values setup
    try:
    - name: Print all values
      strategy: module://strategies/basic/print_params
      args:
      - "{{ mapping_value }}"
      - "{{ sequence }}"
      kwargs:
        mapping_value: "{{ mapping_value }}"

    else:
    - name: Test subblock
      try:
      - name: Print subblock
        strategy: module://strategies/basic/print_params
        args:
          - subblock argument 1
          - subblock argument 2
        kwargs:
          in_else: Hallo from else subblock
      else:
      - name: Print subblock
        strategy: module://strategies/basic/print_params
        args:
          - else subblock argument 1
          - else subblock argument 2
        kwargs:
          in_else: Hallo from else else subblock

    - name: Test in else block works
      strategy: module://strategies/basic/print_params
      args:
        - else subblock argument 1
        - else subblock argument 2
      kwargs:
        in_else: Hallo from else block1
      when: "len({{ last_sequence }}) > 0"

    finally:
    - name: Test that finally works
      strategy: module://strategies/basic/print_params
      args:
        - finally argument 1
        - finally argument 2
      kwargs:
        in_finally: Hallo from finally
        
else:
  - name: Test that else block works
    strategy: module://strategies/basic/print_params
    args:
      - else argument 1
      - else argument 2
    kwargs:
      in_else: Hallo from else block
when: "len({{ sequence }}) > 0"
```
## 2. Elements
YAMLines created from following elements:
* Pipeline. This is generally a `.yml` or `.yaml` file with the script.
* Stage. This is any YAML mapping that has `try` key.
* Step. This is any YAML mapping that has `strategy` key.
* Import. This is any YAML mapping that has `import` key.
### 2.1. Pipeline
Pipelines are similar to Stages but internally they have no parent. So they are
root of execution path.

Pipelines may provide `values` key. This values will be set to an instance of 
the `VarsBorg` class before executing other Pipeline elements.
### 2.2. Stage
A stage is any YAMLine element with mandatory `try` key and optional
keys `except`, `else`, `finally`, `name`, `when`. This keys mostly mimics Python exception 
handling mechanism with one major difference: 
__*named exceptions are not supported*__.

Any inner element of the `try`, `except`, `else`, `finally` SHOULD be the 
Step or Stage element.

Additional keys have special meaning:
* `name` - specifies a name for referencing by Import element.
* `when` - specifies a logical expression that if provided and when evaluated 
should return `True` for Stage to be executed.

An example of the Stage:
```yaml
  - name: some_complex_stage
    try:
    - name: Calculate something
      strategy: module://strategies/basic/calculate
    except:
    - name: Raise exception
      strategy: module://strategies/basic/raise_last
    else:
    - try:
      - name: Calculate something
        strategy: module://strategies/basic/calculate
      except:
      - name: Re-Print something
        strategy: module://strategies/basic/print_last
    finally:
    - name: Print something
      strategy: module://strategies/basic/print_last
    when: '{{ some_value }} >= 0'
```
### 2.3. Step
A Step is any YAMLine element with mandatory `strategy` key and optional
keys `sets`, `args`, `kwargs`, `name`, `when`.

`strategy` specifies Python callable to be executed by `module://` URI scheme.

E.g. `module://strategies/database/additional_info`
where `additional_info` is Python callable name and `strategies/database` is 
a relative path to module containing callable.

Additional keys have special meaning:
* `sets` - a single name or list of names that will be set to a value or 
a list of values that will be returned by `strategy` execution.
* `args` - single positional argument or list of positional arguments that 
the Python callable will be called with.
* `kwargs` - a mapping with keyword argument that the Python callable will be
called with.
* `name` - specifies a name for referencing by Import element.
* `when` - specifies a logical expression that if provided and when evaluated 
should return `True` for Step to be executed.

An example of the Step:
```yaml
- name: Prepare timelines object for plotting
  strategy: module://strategies/reporting/prepare_timelines_object
  sets: 
    - "{{ data_to_plot }}"
    - "{{ data_to_print }}"
  args:
    - "{{ clear_experience }}"
    - "{{ results_aggregator }}"
    - 1000
  kwargs:
    title: Server BaseApp CPU Utilization
    x_axis_label: Time
    y_axis_label: CPU Load (%)
    yamline_id: "{{ yamline_id }}"
    yamline_name: "{{ yamline_name }}"
```
### 2.4. Import
If element contains `import` key then such an element is treated other way.
Pipeline executor parses URI `import://` scheme and pastes element referenced 
in URI to current Pipeline.

Imported elements work the same way as if they were copy-pasted in text editor.

An example of Import:
```yaml
- name: Set last test run as ID under test
  import: import://YAMLines/121000_per_commit/120000_mixin.yaml/last_run_id_by_name_and_run_name
```

In the above example `YAMLines/121000_per_commit/120000_mixin.yaml` refers to 
a relative path to a YAMLine file and `last_run_id_by_name_and_run_name` refers
to a `name` of a YAMLine element to import.

An example content of `120000_mixin.yaml` file:
```yaml
- name: last_run_id_by_name_and_run_name
  strategy: module://strategies/database/get_last_run_id
  sets: "{{ under_test_id }}"
  kwargs:
    engine: "{{ db_engine }}"
    columns: "{{ db_columns_to_match }}"
```

## 3. Shared variables
To send data between elements Pipeline uses instance of a `VarsBorg` class.
This class works like a singletone.

If a Step sets `under_test_id` value with following key:
```yaml
- name: last_run_id_by_name_and_run_name
  strategy: module://strategies/database/get_last_run_id
  sets: "{{ under_test_id }}"
```
then Pipeline that will be executed after `last_run_id_by_name_and_run_name` 
may get `under_test_id` value by referencing it with variable syntax: 
`{{ VARIABLE_NAME }}.

```yaml
- name: Fetch series under test
  strategy: module://strategies/database/get_series_by_id_and_uri
  sets: "{{ under_test_id }}"
  kwargs:
    run_id: "{{ under_test_id }}"
```
in the above example step "re-sets" `under_test_id` with a return value of 
the `get_series_by_id_and_uri` Python callable. 

If one will design `under_test_id` to be a list or any other mutable 
collection then it may be used to aggregate result in it.

## 4. Tool
YAMLine provides a command line tool to run .yaml/.yml files as Pipelines.
If you provide a list of YAML files then all files will be executed in a given 
order. Note that instance of a `VarsBorg` class will reset between runs (e.g. 
you have no builtin way to send data between files). 

Tool will run all files even if exception will happen during execution of 
a single Pipeline.

Basic usage:
```bash
$ python2 -m yamline.tool specifications/test1.yaml specifications/test2.yaml 

WHILE EXECUTING specifications/test1.yaml FOLLOWING EXCEPTION HAPPENED:

Traceback (most recent call last):
  File "/usr/local/lib/python2.7/dist-packages/yamline/tool.py", line 67, in _execute_normal
    ...
    ...
  File "strategies/basic.py", line 35, in zero
    a = 1 / 0
ZeroDivisionError: integer division or modulo by zero

END OF THE specifications/test1.yaml EXCEPTION TRACEBACK

============================== EXECUTION RESULTS ==============================
YAMLINE: specifications/test1.yaml - FAILED
YAMLINE: specifications/test2.yaml - OK
```
If running other files after a single failure is not a desirable then 
`--failfast` key may be provided. Tool will stop execution immediately if 
any errors.

```bash
$ python2 -m yamline.tool specifications/test1.yaml specifications/test2.yaml --failfast
Traceback (most recent call last):
  File "/usr/lib/python2.7/runpy.py", line 174, in _run_module_as_main
    ...
    ...
  File "strategies/basic.py", line 35, in zero
    a = 1 / 0
ZeroDivisionError: integer division or modulo by zero
$
```

## 5. Aliases
YAMLine provides ability to provide aliases to literals. This is intended to 
provide better user experience and clarity. Implementing aliases may provide
better domain description and understanding by the YAMLine script creators.

To override default name with aliases use `--alias {PATH_TO_ALIAS_FILE}` 
yamline.tool key.
```bash
$ python2 -m yamline.tool specifications/test1.yaml specifications/test2.yaml --failfast --alias specifications/aliases_pipe.yaml
```

The conent of `aliases_pipe.yaml` file may be following:
```yaml

---
WHEN: if

STEP_NAME: description
STEP_STRATEGY: strategy
STEP_SETS: sets
STEP_ARGS: args
STEP_KWARGS: kwargs

STAGE_NAME: stage description
STAGE_TRY: stage
STAGE_EXCEPT: error
STAGE_ELSE: pass
STAGE_FINALLY: always
STAGE_WHEN: if

PIPELINE_ALIASES: aliases
PIPELINE_IMPORT: import
PIPELINE_METADATA: metadata
PIPELINE_VALUES: variables

URI_SCHEME_STRATEGY: module
URI_SCHEME_IMPORT: import
```