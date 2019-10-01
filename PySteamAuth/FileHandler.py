#    Copyright (c) 2019 melvyn2
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

import PyUIs
import Common

import sys
import os
import json
import hashlib

from PyQt5 import QtWidgets, QtCore
from steam import guard
from bpylist import archiver
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend


class Empty(object):
    pass


mafiles_path = ''
manifest = {}
manifest_password = ''  # Let's hope memory protection is good enough

def set_mafile_location():
    global mafiles_path
    if os.path.isfile(os.path.join(os.path.dirname(__file__), 'maFiles', 'manifest.json')) \
       or '--dbg' in sys.argv:
        mafiles_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'maFiles'))
    elif os.path.isfile(os.path.join(os.path.expanduser('~'), 'maFiles', 'manifest.json')):
        mafiles_path = os.path.abspath(os.path.join(os.path.expanduser('~'), 'maFiles'))
    else:
        mafiles_path = os.path.abspath(os.path.join(os.path.expanduser('~'), '.maFiles'))


def load_manifest():
    global manifest
    with open(os.path.join(mafiles_path, 'manifest.json')) as f:
        manifest = json.load(f)
    if not manifest.get('selected_account', False):
        manifest.update({'selected_account': 0})

def load_entry(index=-1):
    if index == -1:
        index = manifest['selected_account']

    if manifest['encrypted']:
        # secrets = decrypt_entry(index)
        secrets = {}
    else:
        try:
            with open(os.path.join(mafiles_path, manifest['entries'][index]['filename'])) as f:
                secrets = json.load(f)
        except IOError:
            Common.error_popup('Failed to load entry')
            return None
        except json.JSONDecodeError:
            Common.error_popup('Failed to decode entry')
            return None
    if not secrets.get('device_id', False):
        secrets.update({'device_id': guard.generate_device_id(manifest['entries'][index]['steamid'])})
        save_entry(index)
    return secrets


def save_entry(secrets, index=-1):
    if index == -1:
        index = manifest['selected_account']
    if manifest['encrypted']:


def request_password(handler):
    def _handle_pw():
        nonlocal password
        password_ui.passwordBox.setDisabled(True)
        try:
            with open(os.path.join(mafiles_path, entry['filename']), 'rb') as f:
                password = json.loads(decrypt_data(f.read(), password_ui.passwordBox.text(), entry['encryption_salt'],
                                    entry['encryption_iv']).decode('ascii'))
                password_dialog.close()
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            pw_wrong_anim.start()
            QtCore.QTimer.singleShot(pw_wrong_anim.duration(), lambda: password_ui.passwordBox.setDisabled(False))
        except IOError:
            Common.error_popup('Failed to read encrypted entry data')
            password_dialog.close()
    password = None
    password_dialog = QtWidgets.QDialog()
    password_ui = PyUIs.PasswordDialog.Ui_Dialog()
    password_ui.setupUi(password_dialog)
    pre_anim = password_ui.passwordBox.geometry()
    pw_wrong_anim = QtCore.QPropertyAnimation(password_ui.passwordBox, b'geometry')
    pw_wrong_anim.setDuration(750)
    pw_wrong_anim.setKeyValueAt(0, password_ui.passwordBox.geometry().adjusted(3, 0, 5, 0))
    pw_wrong_anim.setKeyValueAt(0.1, password_ui.passwordBox.geometry().adjusted(-6, 0, -6, 0))
    pw_wrong_anim.setKeyValueAt(0.2, password_ui.passwordBox.geometry().adjusted(6, 0, 6, 0))
    pw_wrong_anim.setKeyValueAt(0.3, password_ui.passwordBox.geometry().adjusted(-6, 0, -6, 0))
    pw_wrong_anim.setKeyValueAt(0.4, password_ui.passwordBox.geometry().adjusted(6, 0, 6, 0))
    pw_wrong_anim.setKeyValueAt(0.5, password_ui.passwordBox.geometry().adjusted(-6, 0, -6, 0))
    pw_wrong_anim.setKeyValueAt(0.6, password_ui.passwordBox.geometry().adjusted(6, 0, 6, 0))
    pw_wrong_anim.setKeyValueAt(0.7, password_ui.passwordBox.geometry().adjusted(-6, 0, -6, 0))
    pw_wrong_anim.setKeyValueAt(0.8, password_ui.passwordBox.geometry().adjusted(6, 0, 6, 0))
    pw_wrong_anim.setKeyValueAt(1, pre_anim)
    password_ui.acceptButton.clicked.connect(_handle_pw)
    password_dialog.exec_()
    _handle_pw()


def decrypt_entry(index):
    def _handle_pw():
        nonlocal data
        password_ui.passwordBox.setDisabled(True)
        try:
            with open(os.path.join(mafiles_path, entry['filename']), 'rb') as f:
                data = json.loads(decrypt_data(f.read(), password_ui.passwordBox.text(), entry['encryption_salt'],
                                    entry['encryption_iv']).decode('ascii'))
                password_dialog.close()
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            pw_wrong_anim.start()
            QtCore.QTimer.singleShot(pw_wrong_anim.duration(), lambda: password_ui.passwordBox.setDisabled(False))
        except IOError:
            Common.error_popup('Failed to read encrypted entry data')
            password_dialog.close()
    data = None
    entry = manifest['entries'][index]
    password_dialog = QtWidgets.QDialog()
    password_ui = PyUIs.PasswordDialog.Ui_Dialog()
    password_ui.setupUi(password_dialog)
    password_ui.msgLabel.setText('Please enter the password for the entry ' + entry['steamid'])
    pre_anim = password_ui.passwordBox.geometry()
    pw_wrong_anim = QtCore.QPropertyAnimation(password_ui.passwordBox, b'geometry')
    pw_wrong_anim.setDuration(750)
    pw_wrong_anim.setKeyValueAt(0, password_ui.passwordBox.geometry().adjusted(3, 0, 5, 0))
    pw_wrong_anim.setKeyValueAt(0.1, password_ui.passwordBox.geometry().adjusted(-6, 0, -6, 0))
    pw_wrong_anim.setKeyValueAt(0.2, password_ui.passwordBox.geometry().adjusted(6, 0, 6, 0))
    pw_wrong_anim.setKeyValueAt(0.3, password_ui.passwordBox.geometry().adjusted(-6, 0, -6, 0))
    pw_wrong_anim.setKeyValueAt(0.4, password_ui.passwordBox.geometry().adjusted(6, 0, 6, 0))
    pw_wrong_anim.setKeyValueAt(0.5, password_ui.passwordBox.geometry().adjusted(-6, 0, -6, 0))
    pw_wrong_anim.setKeyValueAt(0.6, password_ui.passwordBox.geometry().adjusted(6, 0, 6, 0))
    pw_wrong_anim.setKeyValueAt(0.7, password_ui.passwordBox.geometry().adjusted(-6, 0, -6, 0))
    pw_wrong_anim.setKeyValueAt(0.8, password_ui.passwordBox.geometry().adjusted(6, 0, 6, 0))
    pw_wrong_anim.setKeyValueAt(1, pre_anim)
    password_ui.acceptButton.clicked.connect(_handle_pw)
    password_dialog.exec_()
    _handle_pw()
    return data


def encrypt_entry():
    def _handle_pw():
        with open(os.path.join(mafiles_path, 'manifes'))  # TODO use globle manifest
        try:
            data = json.dumps(secrets, ensure_ascii=True).encode('ascii')
            iv = os.urandom(16)
            salt = os.urandom(8)
            with open(os.path.join(mafiles_path, entry['filename']), 'wb') as f:
                f.write(encrypt_data(data, password_ui.passwordBox.text(), salt, iv))
        except (UnicodeEncodeError, ValueError):
            Common.error_popup('Failed to encrypt entry')
        except IOError:
            Common.error_popup('Failed to write encrypted entry to file')
    password_dialog = QtWidgets.QDialog()
    password_ui = PyUIs.PasswordDialog.Ui_Dialog()
    password_ui.setupUi(password_dialog)
    password_ui.msgLabel.setText('Please enter a password to encrypt your authenticator files')
    password_ui.acceptButton.clicked.connect(_handle_pw())
    password_dialog.exec_()


def encrypt_data(data, password, salt, iv):
    padder = PKCS7(128).padder()
    packeddata = padder.update(data) + padder.finalize()
    key = hashlib.pbkdf2_hmac('sha1', password, salt, 50000, 32)
    encryptor = Cipher(AES(key), CBC(iv), backend=default_backend()).encryptor()
    return encryptor.update(packeddata) + encryptor.finalize()


def decrypt_data(ciphertext, password, salt, iv):
    key = hashlib.pbkdf2_hmac('sha1', password, salt, 50000, 32)
    decryptor = Cipher(AES(key), CBC(iv), backend=default_backend()).decryptor()
    packeddata = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    return unpadder.update(packeddata) + unpadder.finalize()


# noinspection PyUnresolvedReferences
def convert_to_ios_format(secrets, steamid, path):
    sec_dict = {}
    sec_dict.update({'shared_secret': secrets['shared_secret']})
    sec_dict.update({'token_gid': secrets['token_gid']})
    sec_dict.update({'identity_secret': secrets['identity_secret']})
    sec_dict.update({'serial_number': secrets['serial_number']})
    sec_dict.update({'revocation_code': secrets['revocation_code']})
    sec_dict.update({'steamguard_scheme': 2})
    sec_dict.update({'steamid': steamid})
    sec_dict.update({'uri': secrets['uri']})
    sec_dict.update({'account_name': secrets['account_name']})
    sec_dict.update({'secret_1': secrets['secret_1']})
    sec_dict.update({'server_time': secrets['server_time']})
    sec_dict.update({'status': 1})
    try:
        with open(os.path.join(path, 'Steamguard-{}.plist'.format(steamid)), 'wb') as f:
            f.write(archiver.archive(sec_dict))
    except archiver.ArchiverError:
        Common.error_popup('Conversion to ios format failed')
        return False
    except IOError:
        Common.error_popup('Failed to write to file')
