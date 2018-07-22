#!/usr/bin/env python3.6

#   Copyright (C) 2018 melvyn2
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
import glob
import os
import pkgutil
import shutil
import sys
import fnmatch
import struct


if sys.platform == 'win32':
	print('WARNING: 32-bit versions of Windows may cause issues.'
			' If problems occur, try using a 64-bit OS to see if that resolves your issue.')

if not(sys.version_info.major == 3 and sys.version_info.minor == 6):
	raise SystemExit('ERROR: Requires python 3.6')


def clean():
	delete(os.path.join('build', sys.platform))
	delete(os.path.join('bin', sys.platform))

	for r, d, f in os.walk('.'):
		for t in fnmatch.filter(f, '*.pyc'):
			delete(os.path.join(r, t))


def delete(obj):
	try:
		if os.path.isdir(obj):
			shutil.rmtree(obj)
		else:
			os.remove(obj)
	except OSError as e:
		if e.errno != 2:
			print(e)


def patch_osx_app():
	app_path = os.path.abspath(os.path.join('bin', 'darwin', 'PySteamAuth.app'))
	folder_path = os.path.abspath(os.path.join('bin', 'darwin', 'PySteamAuth'))
	qtwe_core_dir = os.path.join(os.sep, 'usr', 'local', 'lib', 'python3.6',
									'site-packages', 'PyQt5', 'Qt', 'lib',
									'QtWebengineCore.framework')

	proc_app = 'QtWebEngineProcess.app'
	shutil.copytree(os.path.join(qtwe_core_dir, 'Helpers', proc_app),
					os.path.join(app_path, 'Contents', 'MacOS', proc_app))
	shutil.copytree(os.path.join(qtwe_core_dir, 'Helpers', proc_app),
					os.path.join(folder_path, proc_app))

	for f in glob.glob(os.path.join(qtwe_core_dir, 'Resources', '*')):
		dest = os.path.join(app_path, 'Contents', 'Resources')
		if os.path.isdir(f):
			shutil.copytree(f, os.path.join(dest, os.path.basename(os.path.normpath(f))))
		else:
			shutil.copy(f, dest)

	for f in glob.glob(os.path.join(qtwe_core_dir, 'Resources', '*')):
		if os.path.isdir(f):
			shutil.copytree(f, os.path.join(folder_path, os.path.basename(os.path.normpath(f))))
		else:
			shutil.copy(f, folder_path)


action = sys.argv[1].lower() if len(sys.argv) >= 2 else None

if action == 'build':
	clean()
	try:
		from PyInstaller.__main__ import run as freeze
		if ('linux' in sys.platform or '--force-onefile' in sys.argv) and '--force-ondir' not in sys.argv:
			freeze(['--distpath', os.path.join('bin', sys.platform), '--workpath', os.path.join('build', sys.platform),
					'PySteamAuth-File.spec'])
		else:
			freeze(['--distpath', os.path.join('bin', sys.platform), '--workpath', os.path.join('build', sys.platform),
					'PySteamAuth-Folder.spec'])
			if sys.platform == 'darwin':
				print('Patching folder and .app bundle... ')
				patch_osx_app()
		print('You can find your built executable(s) in the \'bin' + os.sep + sys.platform + '\' directory.')
	except ImportError:
		print('PyInstaller is missing.')
		sys.exit(1)

elif action == 'install':
	if sys.platform == 'darwin':
		if not os.path.isdir(os.path.join('bin', sys.platform, 'PySteamAuth.app')):
			print('You must build the program first, like so:\n    {0} build <program>'.format(sys.argv[0]))
			sys.exit()
		elif len(sys.argv) == 3:
			installdir = os.path.expanduser(os.path.join(('~' if '--user' in sys.argv else os.sep),
				'Applications', 'PySteamAuth.app'))
		else:
			installdir = os.path.join(os.sep, 'Applications', 'PySteamAuth.app')
		if os.path.isdir(installdir):
			update = input('You already have a copy of PySteamAuth at {0}. '
				'Would you like to remove it and continue? (y/n) '.format(installdir))
			if update == 'y':
				delete(installdir)
			else:
				print('Aborted.')
				sys.exit()
		shutil.copytree(os.path.join('bin', sys.platform, 'PySteamAuth.app'), installdir)
		print('The PySteamAuth application bundle has been installed in the directory {0}'
			' under the name \'PySteamAuth.app\'.'.format(installdir))
	elif 'linux' in sys.platform:
		if not os.path.isfile(os.path.join('dist', 'PySteamAuth')):
			print('You must build the program first, like so:\n    {0} build'.format(sys.argv[0]))
			sys.exit()
		elif len(sys.argv) == 3:
			installdir = os.path.expanduser(os.path.join('~' if '--user' in sys.argv else
				(os.sep, 'usr', 'local'), 'bin'))
		else:
			installdir = os.path.join(os.sep, 'usr', 'local', 'bin')

		if os.path.isfile(os.path.join(installdir, 'PySteamAuth')):
			update = input('You already have a copy of PySteamAuth at {0}. '
							'Would you like to remove it and continue? (y/n) '.format(os.path.join(installdir, 'PySteamAuth')))
			if update == 'y':
				delete(os.path.join(installdir, 'PySteamAuth'))
			else:
				print('Aborted.')
				sys.exit()
		shutil.copy(os.path.join('bin', sys.platform, 'PySteamAuth'), os.path.join(os.sep, 'usr', 'local', 'bin'))
		print('PySteamAuth has been installed in the directory {0} under the name \'PySteamAuth\'.'.format(installdir))
		if '--user' in sys.argv:
			print('Make sure that \'~/bin\' is in your PATH.')

	elif sys.platform in ['windows', 'win32']:
		if not os.path.isfile(os.path.join('dist', 'PySteamAuth.exe')):
			print('You must build the program first, like so:\n    {0} build'.format(sys.argv[0]))
			sys.exit()
		elif len(sys.argv) == 3:
			print('--user is not supported on windows.')
			sys.exit()
		else:
			installdir = os.path.join(os.sep, 'Program Files' + (' (x86)' if struct.calcsize('P') == 4 else ''), 'PySteamAuth')

		if os.path.isdir(installdir):
			update = input('You already have a copy of PySteamAuth at {0}. '
							'Would you like to remove it and continue? (y/n) '.format(
								os.path.join(installdir, 'PySteamAuth')))
			if update == 'y':
				delete(installdir)
			else:
				print('Aborted.')
				sys.exit()
		shutil.copytree(os.path.join('bin', sys.platform), installdir)
		print('PySteamAuth has been installed in the directory {0} under the name \'PySteamAuth\'.'.format(
			installdir))
	else:
		print('Unrecognized OS. \'{0} build <program>\' will build the executable and put it in the '
				'\'dist\' directory.'.format(sys.argv[0]))


elif action == 'run':
	from PySteamAuth import PySteamAuth
	PySteamAuth.main()

elif action == 'clean':
	clean()

elif action == 'deps':
	missing = []
	deps = ['Cryptodome', 'PyInstaller', 'PyQt5', 'requests', 'steam']
	installed_packages = [x[1] for x in list(pkgutil.iter_modules())]
	for i in deps:
		if i not in installed_packages:
			missing.append(i)
	if 'PyInstaller' not in missing:
		import PyInstaller
		if PyInstaller.__version__[:8] != '3.4.dev0':
			missing.append('PyInstaller')
	import setuptools
	if setuptools.__version__ < '39':
		missing.append('setuptools')
	if len(missing) > 0:
		print('You are missing or need to upgrade/patch the following: ' + ', '.join(missing))
		if '-y' in sys.argv or input('Install them or it? (y/n) ') == 'y':
			to_install = ['https://github.com/pyinstaller/pyinstaller/archive/develop.zip' if x == 'PyInstaller'
				else ('pycryptodomex' if x == 'Cryptodome' else x) for x in missing]
			try:
				import pip
				# noinspection PyUnresolvedReferences
				pip.main(['install', '--upgrade'] + to_install)
			except AttributeError:
				try:
					# noinspection PyProtectedMember
					import pip._internal
					# noinspection PyProtectedMember
					pip._internal.main(['install', '--upgrade'] + to_install)
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
	if 'PyInstaller' not in missing:
		import PyInstaller

		if PyInstaller.__version__[:8] != '3.4.dev0':
			missing.append('PyInstaller')
	import setuptools

	if setuptools.__version__ < '39':
		missing.append('setuptools')

	print('Not all packages were successfully installed.' if missing else 'You have all dependencies installed!')

else:
	print('Invalid option\nPossible options: build, install [--user], run, clean, deps [-y]')
