# PySteamAuth

A desktop alternative to the Steam Mobile Authenticator

DISCLAIMER
----------
ALWAYS KEEP COPIES OF YOUR AUTHENTICATOR FILES AND REVOCATION CODE!

This program is still in development and is very unstable. Use at your own risk.

Pre-built Downloads
-------------------
 Downloads are not availible yet as CI/CD is still not set up and manual
  builds aren't fun. You can still build it yourself.

Requirements
------------
* [Python 3](https://www.python.org/)
* [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5)
* [Requests](http://docs.python-requests.org/en/master/)
* [Steam](https://github.com/ValvePython/steam) (PyPI package is outdated, install from repo)
* [lxml](https://github.com/lxml/lxml)
* [PyInstaller](https://github.com/pyinstaller/pyinstaller/)


Running Directly
-----------------
First, make sure you have all dependencies installed, and build the PyQt dialogs:

`$ ./make.py deps && ./make.py pyqt-build`

Because PySteamAuth is a python script, you can run it directly:

`$ python3.6 PySteamAuth/PySteamAuth.py`

Or you can use `make.py`:

`$ ./make.py run`

Building
--------

First, make sure you have all dependencies installed:

`$ ./make.py deps`

Then, build it:

`$ ./make.py build`

The executable will be packaged into a folder (or an app bundle on 
macOS) with other files required for PSA to run. If you require 
portability, using

`$ ./make.py build --compact`

will package everything into a single executable, which is also smaller,
but has a longer startup time.

Contributing
------------
* Testing! Simply test this program out and report bugs/missing features.

* Development: add features, fix bugs, and work on TODOs.
