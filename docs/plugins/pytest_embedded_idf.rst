pytest\_embedded\_idf package
=============================

Submodules
----------

pytest\_embedded\_idf.app module
--------------------------------

.. automodule:: pytest_embedded_idf.app
   :members:
   :undoc-members:
   :show-inheritance:

pytest\_embedded\_idf.serial module
-----------------------------------

.. automodule:: pytest_embedded_idf.serial
   :members:
   :undoc-members:
   :show-inheritance:

Fixtures
--------

- ``app``: :py:class:`pytest_embedded_idf.app.IdfApp` instance
  
   Provide more information about idf app, like partition table, sdkconfig, and flash files, etc.

Fixtures when Satisfy Optional Dependency ``pytest-embedded-serial-esp``
------------------------------------------------------------------------

- ``serial``: :py:class:`pytest_embedded_idf.serial.IdfSerial` instance

   Provide auto flash functionality

Added CLI Options
-----------------

- `--part-tool`: Partition tool path, used for parsing partition table
