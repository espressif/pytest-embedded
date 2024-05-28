###################################################################
 Understand :class:`~pytest_embedded_serial.serial.Serial` Objects
###################################################################

The ``Serial`` object is the main object that you will use for testing. This chapter will explain the basic concepts of the ``Serial`` object.

.. note::

   This chapter is mainly for developers who want to understand the internal structure of the ``Serial`` object. If you are a user who just wants to use the ``Serial`` object, you can skip this chapter.

************************************************
 :class:`~pytest_embedded_serial.serial.Serial`
************************************************

-  :func:`__init__`

   -  decide port

      Support auto-detecting port by port location

   -  :func:`_post_init`

      occupy ports globally. Used for preventing other tests from using the same port while auto-detecting ports.

   -  :func:`_start`

      doing nothing

   -  :func:`_finalize_init`

      doing nothing

   -  :func:`start_redirect_thread`

      Start the redirect thread. Read data from the serial port and write it to the log file, optionally echoing it to the console.

-  :func:`close`:

      -  :func:`stop_redirect_thread`

         Stop the redirect thread.

      -  close serial connection

      -  release the occupied port globally

***********************************************************************************************************************
 :class:`~pytest_embedded_serial_esp.serial.EspSerial` (Inherited from :class:`~pytest_embedded_serial.serial.Serial`)
***********************************************************************************************************************

-  :func:`__init__`

   -  :func:`_before_init_port` (newly added method before deciding port)

      -  parent class :func:`_post_init`

   -  decide port

      Support auto-detecting port by device MAC, or device target. (Espressif-chips only)

   -  :func:`_post_init`

      -  Call :func:`set_port_target_cache`, speed up auto-detection next time

      -  erase flash if set :attr:`erase_all`, and not set :attr:`flash_port`

         since if :attr:`flash_port` is set, the "erase" and "flash"" process will be done earlier already.

      -  parent class :func:`_post_init`

   -  :func:`_start`

      Run :func:`esptool.hard_reset`

*******************************************************************************************************************************
 :class:`~pytest_embedded_arduino.serial.ArduinoSerial` (Inherited from :class:`~pytest_embedded_serial_esp.serial.EspSerial`)
*******************************************************************************************************************************

-  :func:`__init__`

   -  :func:`_start`

      Auto-flash the app if not :attr:`skip_autoflash`

***********************************************************************************************************************
 :class:`~pytest_embedded_idf.serial.IdfSerial` (Inherited from :class:`~pytest_embedded_serial_esp.serial.EspSerial`)
***********************************************************************************************************************

-  :func:`__init__`

   -  :func:`_before_init_port`

      If :attr:`flash_port` is set differently from the :attr:`port`, the target chip will always be flashed with the given port(without the port-app cache)

      -  Occupying the :attr:`flash_port` globally
      -  erase flash if set :attr:`erase_all`
      -  Flash the app if not set :attr:`skip_autoflash`
      -  :func:`set_port_target_cache` for the flash port
      -  :func:`set_port_app_cache` for the flash port

   -  :func:`_post_init`

      -  if set :attr:`flash_port`, do nothing
      -  otherwise, check port-app cache, if the app has been flashed, skip the auto-flash process
      -  Run parent :func:`_post_init`

   -  :func:`_start`

      -  if the target has been flashed while :func:`_before_init_port`, set the port-app cache with the :attr:`port` and :attr:`app` and do nothing
      -  otherwise, run :func:`flash` automatically the app if not set :attr:`skip_autoflash`
      -  Run parent :func:`_start`

-  :func:`flash`

   -  flash the app
   -  :func:`set_port_app_cache` for the flash port

-  :func:`close`

   -  release the occupied flash port globally
   -  Run parent :func:`close`
