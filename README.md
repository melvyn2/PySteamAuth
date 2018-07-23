# PySteamAuth

A desktop alternative to the Steam Mobile Authenticator

Requirements
------------
* [Python 3.6](https://www.python.org/)
* [PyQt5](https://www.riverbankcomputing.com/software/pyqt/download5)
* [Requests](http://docs.python-requests.org/en/master/)
* [Steam](https://github.com/ValvePython/steam) (Python Library)
* [PyCryptoDomeX](https://github.com/Legrandin/pycryptodome) (`pip install pycryptodomex`)
* [PyInstaller modified fork:](https://github.com/melvyn2/pyinstaller) `pip install https://github.com/melvyn2/pyinstaller/archive/develop.zip`


Running Directtly
-----------------
First, make sure you have all dependencies installed:

`$ ./make.py deps`

Because PySteamAuth is a python script, you can run it directly (as a module):

`$ python3.6 -m PySteamAuth.PySteamAuth`

Or you can use make.py

`$ make.py run`

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
