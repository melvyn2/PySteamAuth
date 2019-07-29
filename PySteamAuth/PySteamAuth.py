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


import json
import signal
import sys
import shutil
import os
import subprocess
import requests
from steam import guard
from PyQt5 import QtWidgets, QtGui, QtCore

import PyUIs
import ConfirmationHandler
import AccountHandler
import Common


if not(sys.version_info.major == 3 and sys.version_info.minor >= 6):
    raise SystemExit('ERROR: Requires python >= 3.6')


class Empty(object):
    pass


def code_update(sa, code_box, code_bar):
    time = code_bar.value() - 1
    if time == 0:
        code_box.setText(sa.get_code())
        code_box.setAlignment(QtCore.Qt.AlignCenter)
        time = 30 - (sa.get_time() % 30)
    code_bar.setValue(time)


def restart():
    if getattr(sys, 'frozen', False):
        os.execl(sys.executable, sys.executable)
    else:
        os.execl(sys.executable, sys.executable, os.path.abspath(__file__))


def open_path(path):
    if sys.platform in ['windows', 'win32']:
        subprocess.Popen(['explorer', '/select', path])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", path])
    else:
        subprocess.Popen(["xdg-open", path])


def save_mafiles(sa=None):
    with open(os.path.join(mafiles_folder_path, 'manifest.json'), 'w') as manifest_file:
        json.dump(manifest, manifest_file)
    if sa:
        with open(os.path.join(mafiles_folder_path, mafile_name), 'w') as mafile:
            json.dump(sa.secrets, mafile)


def refresh_session_handler():
    pass


def backup_codes_popup(sa):
    if not sa.backend:
        mwa = AccountHandler.get_mobilewebauth(sa)
        if not mwa:
            return
        sa.backend = mwa
    try:
        sa.create_emergency_codes()
        endfunc = Empty()
        endfunc.endfunc = False
        code_dialog = QtWidgets.QDialog()
        code_ui = PyUIs.PhoneDialog.Ui_Dialog()
        code_ui.setupUi(code_dialog)
        code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
        code_dialog.exec_()
        if endfunc.endfunc:
            return
        codes = sa.create_emergency_codes(code_ui.codeBox.text())
        codes = '\n'.join(codes)
    except guard.SteamAuthenticatorError as e:
        Common.error_popup(str(e))
        return
    if len(codes) > 0:
        bcodes_dialog = QtWidgets.QDialog()
        bcodes_ui = PyUIs.BackupCodesCreatedDialog.Ui_Dialog()
        bcodes_ui.setupUi(bcodes_dialog)
        bcodes_ui.copyButton.clicked.connect(lambda: (bcodes_ui.codeBox.selectAll(), bcodes_ui.codeBox.copy()))
        bcodes_ui.codeBox.setText(codes)
        bcodes_dialog.exec_()
    else:
        Common.error_popup('No codes were generated or invalid code', 'Warning:')


def backup_codes_delete(sa):
    if not sa.backend:
        mwa = AccountHandler.get_mobilewebauth(sa)
        if not mwa:
            return
        sa.backend = mwa
    endfunc = Empty()
    endfunc.endfunc = False
    bcodes_dialog = QtWidgets.QDialog()
    bcodes_ui = PyUIs.BackupCodesDeleteDialog.Ui_Dialog()
    bcodes_ui.setupUi(bcodes_dialog)
    bcodes_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
    bcodes_dialog.exec_()
    if endfunc.endfunc:
        return
    try:
        sa.destroy_emergency_codes()
    except guard.SteamAuthenticatorError as e:
        Common.error_popup(str(e))


def test_mafiles(path, entry=False):
    try:
        manifest_file = open(os.path.join(path, 'manifest.json'))
    except IOError:
        return False
    test_manifest = json.load(manifest_file)
    if entry:
        try:
            with open(os.path.join(path, test_manifest['entries'][entry]['filename'])) as maf_file:
                maf = json.loads(maf_file.read())
            sa = guard.SteamAuthenticator(secrets=maf)
            sa.get_code()
        except (IOError, json.decoder.JSONDecodeError, guard.SteamAuthenticatorError):
            manifest_file.close()
            return False
        manifest_file.close()
        return True
    else:
        valid_entries = []
        for i in test_manifest['entries']:
            try:
                with open(os.path.join(path, i['filename'])) as maf_file:
                    maf = json.loads(maf_file.read())
                sa = guard.SteamAuthenticator(secrets=maf)
                sa.get_code()
                valid_entries.append(i)
            except (IOError, json.decoder.JSONDecodeError, guard.SteamAuthenticatorError):
                continue
        manifest_file.close()
        return valid_entries


def set_autoaccept(timer, sa, trades, markets):
    if trades or markets:
        timer.timeout.connect(lambda: accept_all(sa, trades, markets, False), QtCore.Qt.QueuedConnection)
        timer.start()
    else:
        timer.stop()


def accept_all(sa, trades=True, markets=True, others=True):
    AccountHandler.refresh_session(sa)
    confs = ConfirmationHandler.fetch_confirmations(sa)
    for i in range(len(confs)):
        if (not trades) and (confs[i].type == 2):
            del confs[i]
        if (not markets) and (confs[i].type == 3):
            del confs[i]
        if (not others) and not (confs[i].type in [2, 3]):
            del confs[i]
    if len(confs) == 0:
        return True
    return ConfirmationHandler.confirm_multi(sa, confs, 'allow')


def open_conf_dialog(sa):
    if not AccountHandler.refresh_session(sa):
        return
    info = Empty()
    info.index = 0
    info.confs = ConfirmationHandler.fetch_confirmations(sa)
    if len(info.confs) == 0:
        Common.error_popup('Nothing to confirm.', '  ')
        main_ui.confListButton.setText('Confirmations')
        return
    conf_dialog = QtWidgets.QDialog()
    conf_ui = PyUIs.ConfirmationDialog.Ui_Dialog()
    conf_ui.setupUi(conf_dialog)
    default_pixmap = QtGui.QPixmap(':/icons/placeholder.png')

    def load_info():
        if len(info.confs) == 0:
            conf_dialog.hide()
            conf_dialog.close()
            conf_dialog.deleteLater()
            Common.error_popup('Nothing to confirm.', '  ')
            main_ui.confListButton.setText('Confirmations')
            return
        while True:
            try:
                conf = info.confs[info.index]
                break
            except IndexError:
                info.index -= 1
        conf_ui.titleLabel.setText(conf.description)
        conf_ui.infoLabel.setText('{0}\nTime: {1}\nID: {2}\nType: {3}'
            .format(conf.sub_description, conf.time, conf.id, conf.type_str))
        if conf.icon_url:
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(requests.get(conf.icon_url).content)
            conf_ui.iconLabel.setPixmap(pixmap)
        else:
            conf_ui.iconLabel.setPixmap(default_pixmap)
        conf_ui.backButton.setDisabled(info.index == 0)
        conf_ui.nextButton.setDisabled(info.index == (len(info.confs) - 1))

    def accept():
        AccountHandler.refresh_session(sa)
        if not info.confs[info.index].accept(sa):
            Common.error_popup('Failed to accept confirmation.')
        info.confs = ConfirmationHandler.fetch_confirmations(sa)
        load_info()

    def deny():
        AccountHandler.refresh_session(sa)
        if not info.confs[info.index].deny(sa):
            Common.error_popup('Failed to accept confirmation.')
        info.confs = ConfirmationHandler.fetch_confirmations(sa)
        load_info()

    def refresh_confs():
        AccountHandler.refresh_session(sa)
        info.confs = ConfirmationHandler.fetch_confirmations(sa)
        load_info()

    load_info()
    conf_ui.refreshButton.clicked.connect(refresh_confs)
    conf_ui.nextButton.clicked.connect(lambda: (setattr(info, 'index', ((info.index + 1) if info.index <
                                                                (len(info.confs) - 1) else info.index)), load_info()))
    conf_ui.backButton.clicked.connect(lambda: (setattr(info, 'index', ((info.index - 1) if info.index > 0
                                                                       else info.index)), load_info()))
    conf_ui.acceptButton.clicked.connect(accept)
    conf_ui.denyButton.clicked.connect(deny)
    conf_dialog.exec_()


def add_authenticator():
    endfunc = Empty()
    endfunc.endfunc = False
    mwa = AccountHandler.get_mobilewebauth()
    if not mwa:
        return
    sa = guard.SteamAuthenticator(backend=mwa)
    if not sa.has_phone_number():
        code_dialog = QtWidgets.QDialog()
        code_ui = PyUIs.PhoneDialog.Ui_Dialog()
        code_ui.setupUi(code_dialog)
        code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
        code_dialog.setWindowTitle('Phone number')
        code_ui.actionBox.setText('This account is missing a phone number. Type yours below to add it.\n'
                              'Eg. +1 123-456-7890')
        code_dialog.exec_()
        if endfunc.endfunc:
            return
        if sa.add_phone_number(code_ui.codeBox.text().replace('-', '')):
            code_dialog = QtWidgets.QDialog()
            code_ui = PyUIs.PhoneDialog.Ui_Dialog()
            code_ui.setupUi(code_dialog)
            code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
            code_dialog.exec_()
            if endfunc.endfunc:
                return
            if not sa.confirm_phone_number(code_ui.codeBox.text()):
                Common.error_popup('Failed to confirm phone number')
                return
        else:
            Common.error_popup('Failed to add phone number.')
            return
    try:
        sa.add()
    except guard.SteamAuthenticatorError as e:
        if 'DuplicateRequest' in str(e):
            code_dialog = QtWidgets.QDialog()
            code_ui = PyUIs.PhoneDialog.Ui_Dialog()
            code_ui.setupUi(code_dialog)
            code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
            code_dialog.setWindowTitle('Remove old authenticator')
            code_ui.actionBox.setText('There is already an authenticator associated with this account.'
                                  ' Enter its revocation code to remove it.')
            code_dialog.exec_()
            if endfunc.endfunc:
                return
            sa.secrets = {'revocation_code': code_ui.codeBox.text()}
            sa.revocation_code = code_ui.codeBox.text()
            try:
                sa.remove()
                sa.add()
            except guard.SteamAuthenticatorError as e:
                Common.error_popup(str(e))
                return
        else:
            Common.error_popup(e)
            return
    if os.path.isdir(mafiles_folder_path):
        if any('maFile' in x for x in os.listdir(mafiles_folder_path)) or 'manifest.json'\
                in os.listdir(mafiles_folder_path):
            Common.error_popup('The maFiles folder in the app folder is not empty.\nPlease remove it.')
            return
        else:
            shutil.rmtree(mafiles_folder_path)
    os.mkdir(mafiles_folder_path)
    with open(os.path.join(mafiles_folder_path, mwa.steam_id + '.maFile'), 'w') as maf:
        maf.write(json.dumps(sa.secrets))
    with open(os.path.join(mafiles_folder_path, 'manifest.json'), 'w') as manifest_file:
        manifest_file.write(json.dumps(
            {'periodic_checking': False, 'first_run': False, 'encrypted': False, 'periodic_checking_interval': 5,
            'periodic_checking_checkall': False, 'auto_confirm_market_transactions': False,
            'entries': [{'steamid': mwa.steam_id, 'encryption_iv': None, 'encryption_salt': None,
                        'filename': mwa.steam_id + '.maFile'}], 'auto_confirm_trades': False}))
    Common.error_popup('This is your revocation code. Write it down physically and keep it. You will need it in case'
                ' you lose your authenticator.', sa.secrets['revocation_code'])
    code_dialog = QtWidgets.QDialog()
    code_ui = PyUIs.PhoneDialog.Ui_Dialog()
    code_ui.setupUi(code_dialog)
    code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
    while True:
        code_dialog.exec_()
        if endfunc.endfunc:
            return
        try:
            sa.finalize(code_ui.codeBox.text())
            break
        except guard.SteamAuthenticatorError as e:
            code_ui.msgBox.setText(str(e))


def remove_authenticator(sa):
    if not sa.backend:
        mwa = AccountHandler.get_mobilewebauth(sa)
        if not mwa:
            return
        sa.backend = mwa
    endfunc = Empty()
    endfunc.endfunc = False
    code_dialog = QtWidgets.QDialog()
    code_ui = PyUIs.PhoneDialog.Ui_Dialog()
    code_ui.setupUi(code_dialog)
    code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
    code_dialog.setWindowTitle('Remove authenticator')
    code_ui.actionBox.setText('Type \'yes\' into the box below to remove your\nauthenticator.')
    code_ui.msgBox.setText('Note that you will receive a 15-day\ntrade hold upon deactivating your authenticator.')
    for i in code_ui.buttonBox.buttons():
        if code_ui.buttonBox.buttonRole(i) == QtWidgets.QDialogButtonBox.AcceptRole:
            i.setEnabled(False)
    code_ui.codeBox.textChanged.connect(lambda x: [(b.setEnabled(x.lower() == 'yes')
                                                    if code_ui.buttonBox.buttonRole(b) ==
                                                    QtWidgets.QDialogButtonBox.AcceptRole else None)
                                                   for b in code_ui.buttonBox.buttons()])
    code_dialog.exec_()
    if endfunc.endfunc:
        return
    try:
        sa.remove()
    except guard.SteamAuthenticatorError as e:
        Common.error_popup(str(e))
        return
    os.remove(os.path.join(mafiles_folder_path, mafile_name))
    del manifest['entries'][manifest_entry_index]
    save_mafiles()
    restart()


def copy_mafiles():
    while True:
        file_dialog = QtWidgets.QFileDialog()
        f = str(file_dialog.getExistingDirectory(caption='Select your maFiles folder.'))
        if f == '':
            break
        if not test_mafiles(f):
            Common.error_popup('The selected folder does not contain valid maFiles.')
            continue
        if os.path.isdir(mafiles_folder_path):
            if any('maFile' in x for x in os.listdir(mafiles_folder_path)) or 'manifest.json'\
                    in os.listdir(mafiles_folder_path):
                Common.error_popup('The maFiles folder at {} is not empty.\nPlease remove it.'.format(mafiles_folder_path))
                continue
            else:
                shutil.rmtree(mafiles_folder_path)
        shutil.copytree(f, mafiles_folder_path)
        break


# inspection PyUnresolvedReferences
def main(argv):  # TODO debug menubar actions
    global mafiles_folder_path, mafile_name, manifest_entry_index, app, manifest, main_window, main_ui
    base_path = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False)\
        else os.path.dirname(os.path.abspath(__file__))
    if test_mafiles(os.path.join(base_path, 'maFiles')):
        mafiles_folder_path = os.path.join(base_path, 'maFiles')
    elif test_mafiles(os.path.expanduser(os.path.join('~', '.maFiles'))) and '--dbg' not in argv:
        mafiles_folder_path = os.path.expanduser(os.path.join('~', '.maFiles'))
    else:
        mafiles_folder_path = os.path.join(base_path, 'maFiles') if os.path.basename(os.path.normpath(base_path)) ==\
                                      'PySteamAuth' else os.path.expanduser(os.path.join('~', '.maFiles'))
    # TODO Generally fix the above

    app = QtWidgets.QApplication(argv)
    signal.signal(signal.SIGINT, lambda x, y: app.exit(0))
    signal.signal(signal.SIGTERM, lambda x, y: app.exit(0))
    if '--test' in argv:
        QtCore.QTimer.singleShot(3, app.quit)
    while True:
        try:
            with open(os.path.join(mafiles_folder_path, 'manifest.json')) as manifest_file:
                manifest = json.loads(manifest_file.read())  # TODO add encryption support
            valid_entries = test_mafiles(mafiles_folder_path)
            if len(valid_entries) == 0:
                raise ValueError('No valid Manifest Entries found!')
            manifest_entry_index = 0
            if len(manifest['entries']) > 1:
                if ('selected_account' in manifest) and manifest['selected_account'] < len(manifest['entries']):
                    manifest_entry_index = manifest['selected_account']
                else:
                    ac_dialog = QtWidgets.QDialog()
                    ac_ui = PyUIs.AccountChoserDialog.Ui_Dialog()
                    ac_ui.setupUi(ac_dialog)
                    for i in valid_entries:
                        try:
                            entry = [None, str(i['steamid']), i['filename']]
                            with open(os.path.join(mafiles_folder_path, i['filename'])) as ma_file:
                                entry[0] = json.load(ma_file)['account_name']
                            ac_ui.accountSelectList.addTopLevelItem(QtWidgets.QTreeWidgetItem(entry))
                        except (json.JSONDecodeError, IOError):
                            continue
                    # noinspection PyUnresolvedReferences
                    ac_dialog.rejected.connect(sys.exit)
                    ac_ui.accountSelectList.itemSelectionChanged.connect(
                        lambda: ac_ui.buttonBox.setDisabled(len(ac_ui.accountSelectList.selectedItems()) != 1))
                    ac_dialog.exec_()
                    manifest_entry_index = ac_ui.accountSelectList.selectedIndexes()[0].row()
                    manifest['selected_account'] = manifest_entry_index
            mafile_name = manifest['entries'][manifest_entry_index]['filename']
            with open(os.path.join(mafiles_folder_path, mafile_name), 'r+') as ma_file:
                maf = json.load(ma_file)
                if 'device_id' not in maf:
                    maf['device_id'] = guard.generate_device_id(maf['steamid'])
                    ma_file.seek(0)
                    ma_file.write(json.dumps(maf))
                    ma_file.truncate()
            if not test_mafiles(mafiles_folder_path, manifest_entry_index):
                raise IOError()
            break
        except (IOError, ValueError, TypeError, IndexError, KeyError) as e:
            if os.path.isdir(mafiles_folder_path):
                if any('maFile' in x for x in os.listdir(mafiles_folder_path)) or 'manifest.json'\
                        in os.listdir(mafiles_folder_path):
                    Common.error_popup('Failed to load maFile: ' + str(e))
            setup_dialog = QtWidgets.QDialog()
            setup_ui = PyUIs.SetupDialog.Ui_Dialog()
            setup_ui.setupUi(setup_dialog)
            setup_ui.setupButton.clicked.connect(lambda: (setup_dialog.accept(), add_authenticator()))
            setup_ui.importButton.clicked.connect(lambda: (copy_mafiles(), setup_dialog.accept()))
            setup_ui.quitButton.clicked.connect(sys.exit)
            if '--test' in argv:
                QtCore.QTimer.singleShot(10, sys.exit)
            setup_dialog.exec_()
    sa = guard.SteamAuthenticator(maf)
    main_window = QtWidgets.QMainWindow()
    main_ui = PyUIs.MainWindow.Ui_MainWindow()
    main_ui.setupUi(main_window)
    main_window.setWindowTitle('PySteamAuth - ' + sa.secrets['account_name'])
    main_ui.codeBox.setText(sa.get_code())
    main_ui.codeBox.setAlignment(QtCore.Qt.AlignCenter)
    main_ui.copyButton.clicked.connect(lambda: (main_ui.codeBox.selectAll(), main_ui.codeBox.copy()))
    main_ui.codeTimeBar.setTextVisible(False)
    main_ui.codeTimeBar.valueChanged.connect(main_ui.codeTimeBar.repaint)
    main_ui.tradeCheckBox.setChecked(manifest['auto_confirm_trades'])
    main_ui.marketCheckBox.setChecked(manifest['auto_confirm_market_transactions'])
    main_ui.confAllButton.clicked.connect(lambda: accept_all(sa))
    main_ui.confListButton.clicked.connect(lambda: open_conf_dialog(sa))
    main_ui.removeButton.clicked.connect(lambda: remove_authenticator(sa))
    main_ui.createBCodesButton.clicked.connect(lambda: backup_codes_popup(sa))
    main_ui.removeBCodesButton.clicked.connect(lambda: backup_codes_delete(sa))
    main_ui.actionOpen_Current_maFile.triggered.connect(lambda c: open_path(os.path.join(mafiles_folder_path,
                                                                                         mafile_name)))
    main_ui.actionSwitch.triggered.connect(lambda c: (manifest.pop('selected_account'), save_mafiles(sa),
                                                      restart()))

    code_timer = QtCore.QTimer(main_window)
    code_timer.setInterval(1000)
    code_timer.timeout.connect(lambda: code_update(sa, main_ui.codeBox, main_ui.codeTimeBar))
    main_ui.codeTimeBar.setValue(30 - (sa.get_time() % 30))
    code_timer.start()

    aa_timer = QtCore.QTimer(main_window)
    aa_timer.setInterval(5000)
    set_autoaccept(aa_timer, sa, main_ui.tradeCheckBox.isChecked(), main_ui.marketCheckBox.isChecked())
    main_ui.tradeCheckBox.stateChanged.connect(lambda: set_autoaccept(aa_timer, sa, main_ui.tradeCheckBox.isChecked(),
                                                                      main_ui.marketCheckBox.isChecked()))
    main_ui.marketCheckBox.stateChanged.connect(lambda: set_autoaccept(aa_timer, sa, main_ui.tradeCheckBox.isChecked(),
                                                                       main_ui.marketCheckBox.isChecked()))

    main_window.show()
    main_window.raise_()

    if '--test' in argv:
        QtCore.QTimer.singleShot(3, app.quit)

    app.exec_()

    save_mafiles(sa)


if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        sys.exit()
