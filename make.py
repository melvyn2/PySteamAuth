#!/usr/bin/env python3

#    Copyright (c) 2018 melvyn2
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import errno
import glob
import pkgutil
import shutil
import subprocess
import sys
import struct


if not(sys.version_info.major == 3 and sys.version_info.minor >= 6):
    raise SystemExit('ERROR: Requires python >= 3.6')


def clean():
    delete(os.path.join('build', sys.platform))
    delete(os.path.join('bin', sys.platform))

    for f in glob.iglob(os.path.join(os.path.dirname(os.path.abspath(__file__)), '*.pyc'), recursive=True):
        delete(f)


def delete(obj):
    try:
        if os.path.isdir(obj):
            shutil.rmtree(obj)
        else:
            os.remove(obj)
    except OSError as err:
        if err.errno != 2:
            raise err


def build_qt_files():
    psa_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PySteamAuth')
    pyuis_dir = os.path.join(psa_dir, 'PyUIs')
    uis_dir = os.path.join(psa_dir, 'UIs')
    shutil.rmtree(pyuis_dir)
    os.mkdir(pyuis_dir)
    built_files = []
    for f in glob.iglob(os.path.join(uis_dir, '*.ui')):
        subprocess.call([sys.executable, '-m', 'PyQt5.uic.pyuic', f, '-o',
                         os.path.join(pyuis_dir, os.path.basename(f).replace('.ui', '.py'))])
        built_files.append(os.path.basename(f).replace('.ui', ''))
    for f in glob.iglob(os.path.join(uis_dir, '*.qrc')):
        subprocess.call([sys.executable, '-m', 'PyQt5.pyrcc_main', f, '-o',
                         os.path.join(pyuis_dir, os.path.basename(f).replace('.qrc', '_rc.py'))])
        built_files.append(os.path.basename(f).replace('.qrc', '_rc'))
    with open(os.path.join(pyuis_dir, '__init__.py'), 'w') as f:
        f.write('from . import ' + ', '.join(sorted(built_files)))
    print('Built', len(built_files), 'PyUI files.')


action = sys.argv[1].lower() if len(sys.argv) >= 2 else None

if action == 'build':  # TODO add travis & appveyor CI
    clean()
    if '--dont-build-qt' not in sys.argv:
        build_qt_files()
    try:
        from PyInstaller.__main__ import run as freeze
        if '--compact' in sys.argv:
            freeze(['--distpath', os.path.join('bin', sys.platform), '--workpath', os.path.join('build', sys.platform),
                    'PySteamAuth-File.spec'])
        else:
            freeze(['--distpath', os.path.join('bin', sys.platform), '--workpath', os.path.join('build', sys.platform),
                    'PySteamAuth-Folder.spec'])
        print('You can find your built executable(s) in the \'bin' + os.sep + sys.platform + '\' directory.')
    except ImportError:
        print('PyInstaller is missing.')
        sys.exit(1)

elif action == 'install':
    try:
        if sys.platform == 'darwin':
            if not os.path.isdir(os.path.join('bin', sys.platform, 'PySteamAuth.app')):
                print('You must build the program first, like so:\n    {0} build'.format(sys.argv[0]))
                sys.exit()

            if os.path.isdir(os.path.join(os.sep, 'Applications', 'PySteamAuth.app')):
                if '-y' in sys.argv or (input('You already have a copy of PySteamAuth installed. '
                                              'Would you like to remove it and continue? [Y/n] ') in ['y', '']):
                    delete(os.path.join(os.sep, 'Applications', 'PySteamAuth.app'))
                else:
                    print('Aborted.')
                    sys.exit()
            shutil.copytree(os.path.join('bin', sys.platform, 'PySteamAuth.app'), os.path.join(os.sep, 'Applications'))
            print('PySteamAuth has been installed to /Applications')
        elif 'linux' in sys.platform:
            if not os.path.exists(os.path.join('dist', sys.platform, 'PySteamAuth')):
                print('You must build the program first, like so:\n    {0} build'.format(sys.argv[0]))
                sys.exit()
            if os.path.exists(os.path.join(os.sep, 'usr', 'local', 'bin', 'PySteamAuth')):
                if '-y' in sys.argv or (input('You already have a copy of PySteamAuth installed. '
                                              'Would you like to remove it and continue? [Y/n] ') in ['y', '']):
                    delete(os.path.join(os.sep, 'usr', 'local', 'opt', 'PySteamAuth'))
                    delete(os.path.join(os.sep, 'usr', 'local', 'bin', 'PySteamAuth'))
                else:
                    print('Aborted.')
                    sys.exit()
            if os.path.isdir(os.path.join('dist', sys.platform, 'PySteamAuth')):
                shutil.copytree(os.path.join('dist', sys.platform, 'PySteamAuth'),
                                os.path.join(os.sep, 'usr', 'local', 'opt', 'PySteamAuth'))
                os.symlink(os.path.join(os.sep, 'usr', 'local', 'opt', 'PySteamAuth', 'PySteamAuth'),
                           os.path.join(os.sep, 'usr', 'local', 'bin', 'PySteamAuth'))
                print('PySteamAuth has been installed to /usr/local/opt/PySteamAuth and symlinked into /usr/local/bin.')
            else:
                shutil.copy2(os.path.join('dist', sys.platform, 'PySteamAuth'),
                             os.path.join(os.sep, 'usr', 'local', 'bin'))
                print('PySteamAuth has been installed to /usr/local/bin.')
            if os.path.join(os.sep, 'usr', 'local', 'bin') not in os.environ['PATH']:
                print('/usr/local/bin is not in your $PATH')
        elif sys.platform in ['windows', 'win32']:
            if not os.path.exists(os.path.join('dist', sys.platform, 'PySteamAuth')):
                print('You must build the program first, like so:\n    {0} build'.format(sys.argv[0]))
                sys.exit()
            pf = 'Program Files' + (' (x86)' if struct.calcsize('P') == 4 else '')
            if os.path.isdir(os.path.join(os.sep, pf, 'PySteamAuth')):
                if '-y' in sys.argv or\
                        (input('You already have a copy of PySteamAuth at \\{0}\\PySteamAuth. '
                               'Would you like to remove it and continue? [Y/n] '.format(pf)) in ['y', '']):
                    delete(os.path.join(os.sep, pf, 'PySteamAuth'))
                else:
                    print('Aborted.')
                    sys.exit()
            if os.path.isdir(os.path.join('dist', sys.platform, 'PySteamAuth')):
                shutil.copytree(os.path.join('dist', sys.platform, 'PySteamAuth'),
                                os.path.join(os.sep, pf, 'PySteamAuth'))
            else:
                os.mkdir(os.path.join('dist', sys.platform, 'PySteamAuth'))
                shutil.copy2(os.path.join('dist', sys.platform, 'PySteamAuth.exe'),
                             os.path.join(os.sep, pf, 'PySteamAuth'))
            os.link(os.path.join(os.sep, pf, 'PySteamAuth', 'PySteamAuth.exe'),
                    os.path.join(os.environ['userprofile'], 'Start Menu', 'Programs'))
        else:
            print('Unrecognized OS. \'{0} build <program>\' will build the executable and put it in the '
                  '\'dist\' directory.'.format(sys.argv[0]))
    except IOError as e:
        if e.errno in [errno.EACCES, errno.EPERM]:
            print('Permission denied; Try with sudo?')


elif action == 'run':
    if '--dont-rebuild-ui' not in sys.argv:
        build_qt_files()
    from PySteamAuth import PySteamAuth
    PySteamAuth.main()

elif action == 'clean':
    clean()

elif action == 'deps':
    missing = []
    deps = ['PyInstaller', 'PyQt5', 'requests', 'steam']
    installed_packages = [x[1] for x in list(pkgutil.iter_modules())]
    for i in deps:
        if i not in installed_packages:
            missing.append(i)
    import setuptools
    if setuptools.__version__ < '39':
        missing.append('setuptools')
    if len(missing) > 0:
        print('You are missing or need to upgrade/patch the following: ' + ', '.join(missing))
        if '-y' in sys.argv or input('Install them or it? (y/n) ') == 'y':
            try:
                import pip
                # noinspection PyUnresolvedReferences
                pip.main(['install', '--upgrade'] + missing)
            except AttributeError:
                try:
                    # noinspection PyProtectedMember
                    import pip._internal
                    # noinspection PyProtectedMember
                    pip._internal.main(['install', '--upgrade'] + missing)
                except ImportError:
                    print('Pip is missing.')
                    sys.exit(1)
            except ImportError:
                print('Pip is missing.')
                sys.exit(1)
        else:
            print('Aborted.')
            sys.exit(0)

    missing = []
    installed_packages = [x[1] for x in list(pkgutil.iter_modules())]
    for i in deps:
        if i not in installed_packages:
            missing.append(i)
    import importlib
    importlib.reload(setuptools)
    if setuptools.__version__ < '39':
        missing.append('setuptools')

    print(('Not all packages were successfully installed: ' + ', '.join(missing)) if missing else
          'You have all dependencies installed!')


elif action == 'pyqt-build':
    build_qt_files()

else:
    print('Invalid option\nPossible options: build [--compact], install, run [--dont-rebuild-ui], clean, deps [-y],'
          ' pyqt-build')
