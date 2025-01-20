import typing as t

import pytest
from esp_bool_parser import PREVIEW_TARGETS, SUPPORTED_TARGETS


def _expand_target_values(values: t.List[t.List[t.Any]], target_index: int) -> t.List[t.List[t.Any]]:
    """
    Expands target-specific values into individual test cases.
    """
    expanded_values = []
    for value in values:
        target = value[target_index]
        if target == 'supported_targets':
            expanded_values.extend([
                value[:target_index] + [target] + value[target_index + 1 :] for target in SUPPORTED_TARGETS
            ])
        elif target == 'preview_targets':
            expanded_values.extend([
                value[:target_index] + [target] + value[target_index + 1 :] for target in PREVIEW_TARGETS
            ])
        else:
            expanded_values.append(value)
    return expanded_values


def _process_pytest_value(value: t.Union[t.List[t.Any], t.Any], markers_index: int) -> t.Any:
    """
    Processes a single parameter value, converting it to pytest.param if needed.
    """
    if not isinstance(value, (list, tuple)):
        return value

    params, marks = [], []
    for i, element in enumerate(value):
        if i == markers_index:
            if not isinstance(element, tuple):
                element = (element,)
            if isinstance(element, tuple):
                marks.extend(element)
        else:
            params.append(element)

    return pytest.param(*params, marks=tuple(marks))


def idf_parametrize(
    param_names: str, values: t.List[t.Union[t.Any, t.Tuple[t.Any, ...]]], indirect: bool = False
) -> t.Callable[..., None]:
    """
    A decorator to unify pytest.mark.parametrize usage in esp-idf.

    Args:
        param_names (str): Comma-separated parameter names.
        values (list): List of parameter values. Each value can be a string or a tuple.
        indirect (bool): If True, marks parameters as indirect.

    Returns:
        Decorated test function with parametrization applied
    """
    param_list = [name.strip() for name in param_names.split(',')]
    for param in param_list:
        if not param:
            raise ValueError(f'One of the provided parameters name is empty: {param_list}')

    markers_index = param_list.index('markers') if 'markers' in param_list else -1
    target_index = param_list.index('target') if 'target' in param_list else -1

    filtered_params = [name for name in param_list if name != 'markers']

    normalized_values = [[value] if len(param_list) == 1 else list(value) for value in values]

    if target_index != -1:
        normalized_values = _expand_target_values(normalized_values, target_index)

    processed_values = [_process_pytest_value(value, markers_index) for value in normalized_values]

    def decorator(func):
        return pytest.mark.parametrize(','.join(filtered_params), processed_values, indirect=indirect)(func)

    return decorator
