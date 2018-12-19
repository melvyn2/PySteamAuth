# PySteamAuth

A desktop alternative to the Steam Mobile Authenticator

DISCLAIMER
----------
ALWAYS KEEP COPIES OF YOUR AUTHENTICATOR FILES AND REVOCATION CODE!

This program is still in development and is very unstable. Use at your own risk.

[Downloads](https://github.com/melvyn2/PySteamAuth/releases)
 ---------

Requirements
------------
* [Python 3](https://www.python.org/)
* [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5)
* [Requests](http://docs.python-requests.org/en/master/)
* [Steam (Python Library)](https://github.com/ValvePython/steam)
* [PyInstaller (develop branch)](https://github.com/pyinstaller/pyinstaller/tree/develop) `pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip`


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

By default, the script is packaged into a single file for linux:

`$ bin/linux2/PySteamAuth`

and into a folder for other OSes, with `.exe` added at the end for Windows:

`$ bin/[YOUR OS]/PySteamAuth/PySteamAuth`.

You can change this behavior by passing `--force-onefile` or `--force-onedir` to `make.py`.
Packaging into a single file sometimes causes issues, so only use `--force-onefile` when necessary.
When packaged into a folder, the executable cannot be separated from the folder's contents.

Known Issues
------------
* Confirm-all on multiple confirmation fails (use individual confirmation dialog until fixed) (#2)