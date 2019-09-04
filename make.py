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
import shutil
import subprocess
import sys
import struct
import time


if not(sys.version_info.major == 3 and sys.version_info.minor >= 6):
    raise SystemExit('ERROR: Requires python >= 3.6')


def clean():
    delete(os.path.join('build', 'PySteamAuth.build'))
    delete(os.path.join('build', 'PySteamAuth.dist'))
    delete(os.path.join('build', 'PySteamAuth.app'))
    delete('dist')
    delete('pkg')

    for f in glob.iglob(os.path.join(os.path.dirname(os.path.abspath(__file__)), '**', '*.pyc'), recursive=True):
        delete(f)
    for root, dirnames, filenames in os.walk('.'):
        for dirname in dirnames:
            if dirname == '__pycache__':
                delete(os.path.join(root, dirname))


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
    delete(pyuis_dir)
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

if action == 'build':
    if '--dont-clean' not in sys.argv:
        clean()
    if '--dont-build-qt' not in sys.argv:
        build_qt_files()
    os.chdir('build')
    try:
        pre_time = time.time()
        args = [sys.executable, '-m', 'nuitka', '--standalone', '--follow-imports',
                os.path.join('..', 'PySteamAuth', 'PySteamAuth.py')]
        if sys.platform == 'linux':
            args.append('--plugin-enable=qt-plugins=sensible,platformthemes')
        else:
            args.append('--plugin-enable=qt-plugins=sensible,styles')
        if sys.platform == 'win32':
            args.append('--windows-disable-console')
            args.append('--assume-yes-for-downloads')
            args.append('--plugin-enable=gevent')
        if '-v' in sys.argv:
            args.append('--show-progress')
        sp = subprocess.check_output(args, shell=(True if sys.platform == 'win32' else False))
        print('Nuitka compilation took', time.time() - pre_time, 'seconds')
    except subprocess.CalledProcessError:
        print('Nuitka compilation failed')
        sys.exit(1)

    try:
        version = subprocess.check_output(['git', 'describe', '--exact-match'], stderr=subprocess.PIPE) \
            .decode('utf-8').strip()
    except FileNotFoundError:
        version = '0.0'
        print('Git is not installed; using default version value')
    except subprocess.CalledProcessError:
        try:
            version = 'git' + \
                      subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], stderr=subprocess.PIPE) \
                          .decode('utf-8').strip()
        except subprocess.CalledProcessError:
            version = '0.0'
            print('Not a git repo; using default version value')

    if sys.platform == 'darwin':
        os.mkdir('PySteamAuth.app')
        os.mkdir(os.path.join('PySteamAuth.app', 'Contents'))
        with open('Info.template.plist') as info_f:
            info_plist = info_f.read()
        try:
            username = subprocess.check_output(['git', 'config', 'user.name'], stderr=subprocess.PIPE) \
                .decode('utf-8')\
                .replace(' ', '')\
                .replace('\n', '')
            if username == '':
                username = 'example'
        except FileNotFoundError:
            username = 'example'
            print('Git is not installed; using default package id')
        except subprocess.CalledProcessError:
            username = 'example'
            print('Could not fetch git username; using default package id')
        with open(os.path.join('PySteamAuth.app', 'Contents', 'Info.plist'), 'w') as info_f:
            info_f.write(info_plist
                         .replace('${USERNAME}', username)
                         .replace('${VERSION}', version))
        os.rename('PySteamAuth.dist', os.path.join('PySteamAuth.app', 'Contents', 'MacOS'))
        os.chdir('..')
        os.mkdir('dist')
        os.rename(os.path.join('build', 'PySteamAuth.app'), os.path.join('dist', 'PySteamAuth.app'))
    else:
        os.chdir('..')
        os.rename(os.path.join('build', 'PySteamAuth.dist'), 'dist')
    if '--zip' in sys.argv:
        try:
            os.mkdir('pkg')
        except FileExistsError:
            pass
        import platform
        archive_name = 'PySteamAuth-' + version + '-' + sys.platform + '-' + platform.machine()
        shutil.make_archive(os.path.join('pkg', archive_name), format='zip', root_dir='dist')

elif action == 'install':
    try:
        if sys.platform == 'darwin':
            if not os.path.isdir(os.path.join('bin', sys.platform, 'PySteamAuth.app')):
                print('You must build the program first, like so:\n    {0} build'.format(sys.argv[0]))
                sys.exit()

            if os.path.isdir(os.path.join(os.sep, 'Applications', 'PySteamAuth.app')):
                if '-y' in sys.argv or (input('You already have a copy of PySteamAuth installed. '
                                              'Would you like to remove it and continue? [Y/n] ').lower() in ['y', '']):
                    delete(os.path.join(os.sep, 'Applications', 'PySteamAuth.app'))
                else:
                    print('Aborted.')
                    sys.exit()
            shutil.copytree(os.path.join('bin', sys.platform, 'PySteamAuth.app'), os.path.join(os.sep, 'Applications'))
            print('PySteamAuth.app has been installed to /Applications')

        elif sys.platform == 'linux':
            if not os.path.exists(os.path.join('dist', sys.platform, 'PySteamAuth')):
                print('You must build the program first, like so:\n    {0} build'.format(sys.argv[0]))
                sys.exit()
            if os.path.exists(os.path.join(os.sep, 'usr', 'local', 'bin', 'PySteamAuth')):
                if '-y' in sys.argv or (input('You already have a copy of PySteamAuth installed. '
                                              'Would you like to remove it and continue? [Y/n] ').lower() in ['y', '']):
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
        elif sys.platform == 'win32':
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
            raise SystemExit('Permission denied; Try with sudo?')
        else:
            raise e


elif action == 'run':
    if '--dont-rebuild-ui' not in sys.argv:
        build_qt_files()
    argv = list(filter('--dont-rebuild-ui'.__ne__, sys.argv[2:]))
    os.execl(sys.executable, sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PySteamAuth',
                                                          'PySteamAuth.py'), *argv)

elif action == 'clean':
    clean()

elif action == 'deps':
    subprocess.call([sys.executable, '-m', 'pip', 'install', '-U', '-r', 'requirements.txt'])

elif action == 'pyqt-build':
    build_qt_files()

elif action == 'test':
    if sys.platform != 'win32':
        try:
            subprocess.check_call(['sudo', '-n', 'true'])
        except subprocess.CalledProcessError:
            raise SystemExit('Failed to use sudo non-interactively')
        if sys.platform == 'darwin':
            os.environ['PATH'] += ':/opt/X11/bin'
        xvfb_proc = subprocess.Popen(['sudo', '-n', 'Xvfb', ':99'])
        os.environ['DISPLAY'] = ':99'
    try:
        python_rc = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                 'PySteamAuth', 'PySteamAuth.py'), '--test'],
                                   timeout=30).returncode
        print('Python test return code:', python_rc)
    except subprocess.TimeoutExpired:
        print('Python test timed out; using exit code 3')
        python_rc = 3

    if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')):
        try:
            if sys.platform == 'darwin':
                compiled_rc = subprocess.run([os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist',
                                                           'PySteamAuth.app', 'Contents', 'MacOS', 'PySteamAuth'),
                                              '--test'], timeout=30).returncode
            elif sys.platform == 'win32':
                compiled_rc = subprocess.run([os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist',
                                                           'PySteamAuth.exe'), '--test'], timeout=30).returncode
            else:
                compiled_rc = subprocess.run([os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist',
                                                           'PySteamAuth'), '--test'], timeout=30).returncode
            print('Compiled test exit code:', compiled_rc)
        except subprocess.TimeoutExpired:
            print('Compiled test timed out; using exit code 3')
            compiled_rc = 3
        final_code = max(abs(python_rc), abs(compiled_rc))
    else:
        final_code = python_rc

    try:
        # noinspection PyUnboundLocalVariable
        subprocess.run(['sudo', '-n', 'kill', str(xvfb_proc.pid)])
    except NameError:
        pass
    sys.exit(final_code)

elif action == 'deploy':
    if not glob.glob(os.path.join('pkg', '*.zip')):
        print('Nothing to upload')
        sys.exit(0)

    if sys.platform == 'win32':
        if os.path.isfile(os.path.expanduser(os.path.join('~', 'go', 'bin', 'github-release.exe'))):
            gh_release = os.path.expanduser(os.path.join('~', 'go', 'bin', 'github-release.exe'))
        elif shutil.which('github-release.exe'):
            gh_release = shutil.which('github-release.exe')
        else:
            raise SystemExit('Could not find github-release')
    else:
        if os.path.isfile(os.path.expanduser(os.path.join('~', 'go', 'bin', 'github-release'))):
            gh_release = os.path.expanduser(os.path.join('~', 'go', 'bin', 'github-release'))
        elif shutil.which('github-release'):
            gh_release = shutil.which('github-release')
        else:
            raise SystemExit('Could not find github-release')
    print('Using github-release at', gh_release)

    set_target = True
    if '-t' in sys.argv:
        try:
            tag = sys.argv[sys.argv.index('-t') + 1]
        except IndexError:
            raise SystemExit('No tag supplied')
    else:
        try:
            tag = subprocess.run(['git', 'describe', '--exact-match'], check=True, stderr=subprocess.PIPE,
                                 stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
        except FileNotFoundError:
            raise SystemExit('Failed to find git')
        except subprocess.CalledProcessError as e:
            if b'no tag exactly matches' in e.stderr:
                try:
                    tag = 'pre-' + subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], check=True,
                                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE) \
                                                  .stdout.decode('utf-8').strip()
                except subprocess.CalledProcessError as e1:
                    raise SystemExit('Failed to create tag\n' + e1.stderr.decode('utf-8'))
            else:
                raise SystemExit('Failed to fetch tag\n' + e.stderr.decode('utf-8'))
        else:
            set_target = False

    prerelease = tag.startswith('pre-')
    print('Using tag', tag)

    if prerelease and '-f' not in sys.argv:
        try:
            if subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('utf-8').strip() \
                    != 'master':
                print('Not on master branch or tag; use -f to force')
                sys.exit(0)
        except subprocess.CalledProcessError:
            raise SystemExit('Failed to check branch')

    try:
        subprocess.run([gh_release, 'info', '--user', 'melvyn2', '--repo', 'PySteamAuth',
                        '--tag', tag], check=True, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise SystemExit('Failed to find github-release')
    except subprocess.CalledProcessError as e:
        if b'could not find the release corresponding to tag' in e.stderr:
            try:
                commit_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
                subprocess.check_call([gh_release, 'release', '--user', 'melvyn2', '--repo', 'PySteamAuth',
                                       '--security-token', os.environ['GITHUB_TOKEN'], '--tag', tag,
                                       '--description', ' '] + (['--pre-release'] if prerelease else []) +
                                      (['--target', commit_sha] if set_target else []))
            except subprocess.CalledProcessError:
                raise SystemExit('Failed to create release')
            except FileNotFoundError:
                raise SystemExit('Failed to find git')
            else:
                print('Created release')
        else:
            raise SystemExit('Failed to check release')

    for i in glob.glob(os.path.join('pkg', '*.zip')):
        try:
            subprocess.check_call([gh_release, 'upload', '--user', 'melvyn2', '--repo', 'PySteamAuth',
                                   '--security-token', os.environ['GITHUB_TOKEN'], '--file', i, '--tag', tag,
                                   '--name', os.path.basename(i)])
        except subprocess.CalledProcessError:
            raise SystemExit('Failed to upload' + i)
        else:
            print('Uploaded', i)

else:
    print('Invalid usage')
    print('Possible options: build [--zip] [-v] [--dont-rebuild-ui], install, run [--dont-rebuild-ui],'
          ' clean, deps, pyqt-build')
