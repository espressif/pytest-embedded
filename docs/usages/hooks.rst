#######
 Hooks
#######

``pytest-embedded`` exposes pytest hook specifications (registered via ``pytest_addhooks``) for customizing test execution and reporting in ``conftest.py`` or downstream plugins.

***********************************
 ``pytest_custom_unity_case_name``
***********************************

.. code:: python

   @pytest.hookspec(firstresult=True)
   def pytest_custom_unity_case_name(item: pytest.Item, case_name: str) -> str | None: ...

Customize the reported name of each Unity sub-case parsed from DUT output.

Behavior
========

-  **Resolution**: ``firstresult=True`` — the first hook implementation returning a non-``None`` string wins. Returning ``None`` (or providing no implementation) keeps the original Unity ``case_name``.

-  **Invocation timing**: Called during ``pytest_runtest_makereport`` when ``call.when == "call"``.

-  **DUT coverage**: Runs over ``dut.testsuite.testcases`` for all DUTs attached to the item — single ``dut`` fixture, multi-DUT tuple, and any DUTs created via :class:`~pytest_embedded.dut_factory.DutFactory`.

-  **JUnit XML**: Mutates ``case.name`` and its XML ``name`` attribute in place so merged JUnit reports (``--junitxml``) use the finalized name.

-  **Item stash**: Publishes all finalized cases to ``item.stash[pytest_embedded.unity.UnityCasesStashKey]`` as ``list[UnityCase]``.

   -  ``UnityCase`` is a ``NamedTuple(name: str, result: str)``.
   -  ``result`` maps Unity outcomes as ``PASS`` → ``"passed"``, ``FAIL`` → ``"failed"``, ``IGNORE`` → ``"skipped"``.

Example
-------

.. code:: python

   import pytest
   from pytest_embedded.unity import UnityCasesStashKey


   def pytest_custom_unity_case_name(item: pytest.Item, case_name: str) -> str:
       return f"{item.name}::{case_name}"


   @pytest.hookimpl(hookwrapper=True)
   def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
       yield  # wait for pytest-embedded to populate the item stash
       if call.when == "call":
           unity_cases = item.stash.get(UnityCasesStashKey, [])
           for case in unity_cases:
               print(case.name, case.result)
