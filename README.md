# PySteamAuth

A desktop alternative to the Steam Mobile Authenticator

DISCLAIMER
----------
ALWAYS KEEP COPIES OF YOUR AUTHENTICATOR FILES AND REVOCATION CODE!

This program is still in development and is very unstable. Use at your own risk.

Pre-built Downloads
-------------------
Downloads are avalible in [releases](https://github.com/melvyn2/PySteamAuth/releases)

These are built on travis-ci on every commit. If they don't work, please
open an issue.

Windows builds will be added soon™.

Requirements
------------
* [Python 3](https://www.python.org/)
* [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5)
* [Requests](http://docs.python-requests.org/en/master/)
* [Steam](https://github.com/ValvePython/steam)==1.0.0a4
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
macOS) with other files required for PSA to run in `dist`.

Contributing
------------
* Testing! Simply test this program out and report bugs/missing features.
* Development: add features, fix bugs, and work on TODOs.
* Translations: coming soon

An app icon would also be handy, if you have any ideas for one.

Credits
-------
* [rossengeorgiev](https://github.com/rossengeorgiev) for steam (the 
library)
* [Geel](https://github.com/geel9/) for 
[SteamAuth](https://github.com/geel9/SteamAuth/), who's code helped a 
lot for making confirmations work
* [Valve](https://www.valvesoftware.com/) for [Steam](https://steamcommunity.com)