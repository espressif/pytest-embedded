import typing as t
from contextvars import ContextVar

import pytest
from esp_bool_parser import PREVIEW_TARGETS, SUPPORTED_TARGETS
from esp_bool_parser.bool_parser import parse_bool_expr

supported_targets = ContextVar('supported_targets', default=SUPPORTED_TARGETS)
preview_targets = ContextVar('preview_targets', default=PREVIEW_TARGETS)


def _expand_target_values(values: list[list[t.Any]], target_index: int) -> list[list[t.Any]]:
    """
    Expands target-specific values into individual test cases.
    """
    expanded_values = []
    for value in values:
        target = value[target_index]
        if target == 'supported_targets':
            expanded_values.extend(
                [[*value[:target_index], target, *value[target_index + 1 :]] for target in supported_targets.get()]
            )
        elif target == 'preview_targets':
            expanded_values.extend(
                [[*value[:target_index], target, *value[target_index + 1 :]] for target in preview_targets.get()]
            )
        else:
            expanded_values.append(value)
    return expanded_values


def _process_pytest_value(value: list[t.Any] | t.Any, param_count: int) -> t.Any:
    """
    Processes a single parameter value, converting it to pytest.param if needed.
    """
    if not isinstance(value, list | tuple):
        return value

    if len(value) > param_count + 1:
        raise ValueError(f'Expected at most {param_count + 1} elements (params + marks), got {len(value)}')

    params, marks = [], []
    if len(value) > param_count:
        mark_values = value[-1]
        marks.extend(mark_values if isinstance(mark_values, tuple | list) else (mark_values,))

    params.extend(value[:param_count])

    return pytest.param(*params, marks=tuple(marks))


def idf_parametrize(
    param_names: str,
    values: list[t.Any | tuple[t.Any, ...]],
    indirect: (bool | t.Sequence[str]) = False,
) -> t.Callable[..., None]:
    """
    A decorator to unify pytest.mark.parametrize usage in esp-idf.

    Args:
        param_names: A comma-separated string of parameter names that will be passed to
            the test function.
        values: A list of parameter values where each value corresponds to the parameters
            defined in param_names.
        indirect: A list of arguments names (subset of argnames) or a boolean. If True
            the list contains all names from the argnames. Each argvalue corresponding to an
            argname in this list will be passed as request.param to its respective argname
            fixture function so that it can perform more expensive setups during the setup
            phase of a test rather than at collection time.

    Returns:
        Decorated test function with parametrization applied
    """
    param_list = [name.strip() for name in param_names.split(',')]
    for param in param_list:
        if not param:
            raise ValueError(f'One of the provided parameters name is empty: {param_list}')

    param_count = len(param_list)
    param_list[:] = [_p for _p in param_list if _p not in ('markers',)]
    target_index = param_list.index('target') if 'target' in param_list else -1
    normalized_values = [[value] if param_count == 1 else list(value) for value in values]
    param_count = len(param_list)

    if target_index != -1:
        normalized_values = _expand_target_values(normalized_values, target_index)

    processed_values = [_process_pytest_value(value, param_count) for value in normalized_values]

    def decorator(func):
        return pytest.mark.parametrize(','.join(param_list), processed_values, indirect=indirect)(func)

    return decorator


ValidTargets = t.Literal['supported_targets', 'preview_targets', 'all']


def soc_filtered_targets(soc_statement: str, targets: ValidTargets = 'all') -> list[str]:
    """Filters targets based on a given SOC (System on Chip) statement.

    Args:
        soc_statement (str): A boolean expression used to filter targets.
        targets (ValidTargets, optional): Specifies which target set to filter.
            - "supported_targets": Filters only supported targets.
            - "preview_targets": Filters only preview targets.
            - "all": Filters both supported and preview targets.
            Defaults to "all".

    Returns:
        List[str]: A list of targets that satisfy the given SOC statement.
    """
    target_list = []
    target_list.extend(supported_targets.get()) if targets in ['all', 'supported_targets'] else []
    target_list.extend(preview_targets.get()) if targets in ['all', 'preview_targets'] else []

    stm = parse_bool_expr(soc_statement)

    result = []
    for target in target_list:
        if stm.get_value(target, ''):
            result.append(target)
    return result
