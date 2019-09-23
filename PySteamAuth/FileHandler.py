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

import os
import time
import hashlib
from PyQt5 import QtWidgets, QtCore
from bpylist import archiver
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend


class Empty(object):
    pass


def decrypt_entry(entry, entry_data):
    def _handle_pw():
        password_ui.passwordBox.setDisabled(True)
        try:
            mafile_json = password_ui.passwordBox.text()
            # mafile_json = decrypt_data(entry_data, password_ui.passwordBox.text(), entry['encryption_salt'],
            #                            entry['encryption_iv']).decode('ascii')
            setattr(returnholder, 'value', mafile_json)
        except (UnicodeDecodeError, ValueError):
            pw_wrong_anim.start()
            QtCore.QTimer.singleShot(pw_wrong_anim.duration(), lambda: password_ui.passwordBox.setDisabled(False))
        else:
            password_dialog.close()
            return mafile_json
    returnholder = Empty()
    password_dialog = QtWidgets.QDialog()
    password_ui = PyUIs.PasswordDialog.Ui_Dialog()
    password_ui.setupUi(password_dialog)
    password_dialog.setWindowTitle('Password')
    password_ui.msgLabel.setText('Please enter the password for the entry ' + entry['steamid'])
    password_ui.passwordBox.setEchoMode(QtWidgets.QLineEdit.Password)
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
    password_ui.buttonBox.rejected.connect(lambda: setattr(returnholder, 'value', False))
    password_ui.acceptButton.clicked.connect(_handle_pw())
    password_dialog.exec_()
    return getattr(returnholder, 'value', None)


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
