pytest\_embedded\_qemu package
===================================

.. warning::

   For now this plugin only support esp32 targets.

Submodules
----------

pytest\_embedded\_qemu.app module
---------------------------------------

.. automodule:: pytest_embedded_qemu.app
   :members:
   :undoc-members:
   :show-inheritance:

pytest\_embedded\_qemu.qemu module
---------------------------------------

.. automodule:: pytest_embedded_qemu.qemu
   :members:
   :undoc-members:
   :show-inheritance:

pytest\_embedded\_qemu.dut module
--------------------------------------

.. automodule:: pytest_embedded_qemu.dut
   :members:
   :undoc-members:
   :show-inheritance:

Fixtures
--------

- ``qemu``: :py:class:`pytest_embedded_qemu.qemu.Qemu` instance

- ``dut``: :py:class:`pytest_embedded_qemu.dut.QemuDut` instance

Fixtures when Satisfy Optional Dependency ``pytest-embedded-serial-esp``
------------------------------------------------------------------------

- ``app``: :py:class:`pytest_embedded_qemu.app.QemuApp` instance
  
   Auto generate qemu flash image from idf app if not exists or ``--qemu-image-path`` not set.

Added CLI Options
-----------------

TBD
