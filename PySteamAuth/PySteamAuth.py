#!/usr/bin/env python3.6

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
import sys
import shutil
import os
import time as pytime
import webbrowser
import urllib.parse
import binascii
import requests
from steam import guard
from PyQt5 import QtWidgets, QtGui, QtCore
try:
    from . import PyUIs, ConfirmationHandler, AccountHandler
except ImportError:
    # noinspection PyUnresolvedReferences
    import PyUIs
    # noinspection PyUnresolvedReferences
    import ConfirmationHandler
    # noinspection PyUnresolvedReferences
    import AccountHandler


if not(sys.version_info.major == 3 and sys.version_info.minor >= 6):
    raise SystemExit('ERROR: Requires python ≥ 3.6')


class Empty(object):
    pass


class QMainWindow(QtWidgets.QMainWindow):
    error_popup_event = QtCore.pyqtSignal(str, str)
    relogin_event = QtCore.pyqtSignal(guard.SteamAuthenticator)

    def __init__(self, parent=None):
        super(QMainWindow, self).__init__(parent)


class TimerThread(QtCore.QThread):
    bar_update = QtCore.pyqtSignal(int)
    code_update = QtCore.pyqtSignal(str)

    def __init__(self, sa, time):
        QtCore.QThread.__init__(self)
        self.time = time
        self.sa = sa

    # noinspection PyUnresolvedReferences
    def run(self):
        while True:
            self.bar_update.emit(self.time)
            if self.time == 0:
                self.code_update.emit(self.sa.get_code())
                self.time = 30 - (self.sa.get_time() % 30)
            self.time -= 1
            pytime.sleep(1)


def restart():
    timer_thread.terminate()
    try:
        auto_accept_thread.running = False
        auto_accept_thread.wait()
    except (NameError, AttributeError):
        pass
    if getattr(sys, 'frozen', False):
        os.execl(sys.executable, sys.executable)
    else:
        os.execl(sys.executable, sys.executable, os.path.join(os.path.abspath(__file__)))


# noinspection PyArgumentList
def error_popup(message, header=''):
    error_dialog = QtWidgets.QDialog()
    error_ui = PyUIs.ErrorDialog.Ui_Dialog()
    error_ui.setupUi(error_dialog)
    if header:
        error_ui.label.setText(str(header))
        error_dialog.setWindowTitle(str(header))
    error_ui.label_2.setText(str(message))
    error_dialog.exec_()


def get_tradeid_from_url(url):
    try:
        return str(url).split('#')[1].replace('conf_', '')
    except IndexError:
        return ''


def generate_query(tag, sa):
    return 'p={0}&a={1}&k={2}&t={3}&m=android&tag={4}'\
        .format(sa.secrets['device_id'], sa.secrets['Session']['SteamID'],
                urllib.parse.quote_plus(binascii.b2a_base64(sa.get_confirmation_key(tag))), sa.get_time(), tag)


# noinspection PyArgumentList
def backup_codes_popup(sa):
    if not sa.medium:
        mwa = AccountHandler.get_mobilewebauth(sa, error_popup)
        if not mwa:
            return
        sa.medium = mwa
    try:
        codes = sa.create_emergency_codes()
        codes = ' '.join(codes)
    except guard.SteamAuthenticatorError as e:
        error_popup(e)
        return
    if len(codes) > 0:
        bcodes_dialog = QtWidgets.QDialog()
        bcodes_ui = PyUIs.BackupCodesDialog.Ui_Dialog()
        bcodes_ui.setupUi(bcodes_dialog)
        bcodes_ui.label_2.setText(codes)
        bcodes_dialog.exec_()
    else:
        error_popup('No codes were generated', 'Warning:')


# noinspection PyArgumentList
def backup_codes_delete(sa):
    if not sa.medium:
        mwa = AccountHandler.get_mobilewebauth(sa, error_popup)
        if not mwa:
            return
        sa.medium = mwa
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
        error_popup(e)


def test_mafiles(path):
    try:
        with open(os.path.join(path, 'manifest.json')) as manifest_file:
            test_manifest = json.loads(manifest_file.read())
        with open(os.path.join(path, test_manifest['entries'][0]['filename'])) as maf_file:
            maf = json.loads(maf_file.read())
        sa = guard.SteamAuthenticator(secrets=maf)
        sa.get_code()
    except (IOError, json.decoder.JSONDecodeError, guard.SteamAuthenticatorError):
        return False
    return True


class AutoAcceptThread(QtCore.QThread):
    error_signal = QtCore.pyqtSignal(str, str)
    stop_signal = QtCore.pyqtSignal()

    def __init__(self, sa, trades, markets):
        QtCore.QThread.__init__(self)
        self.sa = sa
        self.trades = trades
        self.markets = markets
        self.running = True

    # noinspection PyUnresolvedReferences
    def run(self):
        if self.trades or self.markets:
            error_timer = 15
            while self.running:
                if error_timer < 15:
                    error_timer += 5
                result = accept_all(self.sa, self.trades, self.markets, False)
                if not result and (error_timer < 15):
                    self.error_signal.emit('An error occured 2 times in 15 seconds.\nStopping Auto-accept proccess.',
                                           '')
                    self.stop_signal.emit()
                    break
                elif not result:
                    self.error_signal.emit('Error auto-accepting confirmation(s).', '')
                    error_timer = 0
                for i in range(50):
                    if self.running:
                        pytime.sleep(0.1)


# noinspection PyUnresolvedReferences
def set_auto_accept(sa, trades_checkbox, markets_checkbox):
    global auto_accept_thread
    try:
        auto_accept_thread.running = False
        auto_accept_thread.wait()
    except (NameError, AttributeError):
        pass
    manifest['auto_confirm_trades'] = trades_checkbox.isChecked()
    manifest['auto_confirm_market_transactions'] = markets_checkbox.isChecked()
    auto_accept_thread = AutoAcceptThread(sa, trades_checkbox.isChecked(), markets_checkbox.isChecked())
    auto_accept_thread.error_signal.connect(error_popup)
    auto_accept_thread.stop_signal.connect(lambda: (main_ui.tradeCheckBox.setChecked(False),
                                                    main_ui.marketCheckBox.setChecked(False)))
    auto_accept_thread.start()
    with open(os.path.join(mafiles_path, 'manifest.json'), 'w') as manifest_file:
        manifest_file.write(json.dumps(manifest))


def accept_all(sa, trades=True, markets=True, others=True):
    confs = ConfirmationHandler.fetch_confirmations(sa, main_window, mafiles_path, manifest)
    for i in range(len(confs)):
        if (not trades) and confs[i].type == 2:
            del confs[i]
        if (not markets) and confs[i].type == 3:
            del confs[i]
        if (not others) and confs[i].type not in [2, 3]:
            del confs[i]
    if len(confs) == 0:
        return True
    return ConfirmationHandler.confirm(sa, confs, 'allow', error_popup, mafiles_path, manifest)


def open_conf_dialog(sa):
    refreshed = AccountHandler.refresh_session(sa, mafiles_path, manifest)
    if refreshed == 1:
        error_popup('Failed to refresh session (connection error).', 'Warning:')
    elif refreshed == 2:
        error_popup('Steam session expired. You will be prompted to sign back in.')
        AccountHandler.full_refresh(sa, main_window)
    info = Empty()
    info.index = 0
    info.confs = ConfirmationHandler.fetch_confirmations(sa, main_window, mafiles_path, manifest)
    if len(info.confs) == 0:
        error_popup('Nothing to confirm.', '  ')
        main_ui.confListButton.setText('Confirmations')
        return
    conf_dialog = QtWidgets.QDialog()
    conf_ui = PyUIs.ConfirmationDialog.Ui_Dialog()
    conf_ui.setupUi(conf_dialog)
    conf_dialog.setFixedSize(conf_dialog.size())
    default_pixmap = QtGui.QPixmap(':/icons/placeholder.png')

    def load_info():
        while True:
            if len(info.confs) == 0:
                conf_dialog.hide()
                conf_dialog.deleteLater()
                error_popup('Nothing to confirm.', '  ')
                main_ui.confListButton.setText('Confirmations')
                return
            try:
                conf = info.confs[info.index]
                break
            except IndexError:
                info.index -= 1
        conf_ui.titleLabel.setText(conf.description)
        conf_ui.infoLabel.setText('{0}\n{1}\nID: {2}\nType: {3}'
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
        if not info.confs[info.index].accept(sa, error_popup, mafiles_path, manifest):
            error_popup('Failed to accept confirmation.')
        info.confs = ConfirmationHandler.fetch_confirmations(sa, main_window, mafiles_path, manifest)
        load_info()

    def deny():
        if not info.confs[info.index].deny(sa, error_popup, mafiles_path, manifest):
            error_popup('Failed to accept confirmation.')
        info.confs = ConfirmationHandler.fetch_confirmations(sa, main_window, mafiles_path, manifest)
        load_info()

    load_info()
    conf_ui.refreshButton.clicked.connect(lambda: (setattr(info, 'confs', ConfirmationHandler.fetch_confirmations
                                          (sa, main_window, mafiles_path, manifest)), load_info()))
    conf_ui.nextButton.clicked.connect(lambda: (setattr(info, 'index', ((info.index + 1) if info.index <
                                                                (len(info.confs) - 1) else info.index)), load_info()))
    conf_ui.backButton.clicked.connect(lambda: (setattr(info, 'index', ((info.index - 1) if info.index > 0
                                                                       else info.index)), load_info()))
    conf_ui.acceptButton.clicked.connect(accept)
    conf_ui.denyButton.clicked.connect(deny)
    conf_dialog.exec_()
    main_ui.confListButton.setText('Confirmations')


# noinspection PyArgumentList
def add_authenticator():
    endfunc = Empty()
    endfunc.endfunc = False
    mwa = AccountHandler.get_mobilewebauth(None, error_popup)
    if not mwa:
        return
    sa = guard.SteamAuthenticator(medium=mwa)
    if not sa.has_phone_number():
        code_dialog = QtWidgets.QDialog()
        code_ui = PyUIs.PhoneDialog.Ui_Dialog()
        code_ui.setupUi(code_dialog)
        code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
        code_dialog.setWindowTitle('Phone number')
        code_ui.label.setText('This account is missing a phone number. Type yours below to add it.\n'
                              'Format: +cC PhoneNumber Eg. +1 123-456-7890')
        code_dialog.exec_()
        if endfunc.endfunc:
                return
        if sa.add_phone_number(code_ui.lineEdit.text().replace('-', '')):
            code_dialog = QtWidgets.QDialog()
            code_ui = PyUIs.PhoneDialog.Ui_Dialog()
            code_ui.setupUi(code_dialog)
            code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
            code_dialog.exec_()
            if endfunc.endfunc:
                return
            if not sa.confirm_phone_number(code_ui.lineEdit.text()):
                error_popup('Failed to confirm phone number')
                return
        else:
            error_popup('Failed to add phone number.')
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
            code_ui.label.setText('There is already an authenticator associated with\nthis account.'
                                  ' Enter its revocation code to remove it.')
            code_dialog.exec_()
            if endfunc.endfunc:
                return
            sa.secrets = {'revocation_code': code_ui.lineEdit.text()}
            sa.revocation_code = code_ui.lineEdit.text()
            try:
                sa.remove()
                sa.add()
            except guard.SteamAuthenticatorError as e:
                error_popup(e)
                return
        else:
            error_popup(e)
            return
    if os.path.isdir(mafiles_path):
        if any('maFile' in x for x in os.listdir(mafiles_path)) or 'manifest.json' in os.listdir(mafiles_path):
            error_popup('The maFiles folder in the app folder is not empty.\nPlease remove it.')
            return
        else:
            shutil.rmtree(mafiles_path)
    os.mkdir(mafiles_path)
    with open(os.path.join(mafiles_path, mwa.steam_id + '.maFile'), 'w') as maf:
        maf.write(json.dumps(sa.secrets))
    with open(os.path.join(mafiles_path, 'manifest.json'), 'w') as manifest_file:
        manifest_file.write(json.dumps(
            {'periodic_checking': False, 'first_run': True, 'encrypted': False, 'periodic_checking_interval': 5,
            'periodic_checking_checkall': False, 'auto_confirm_market_transactions': False,
            'entries': [{'steamid': mwa.steam_id, 'encryption_iv': None, 'encryption_salt': None,
                        'filename': mwa.steam_id + '.maFile'}], 'auto_confirm_trades': False}))
    revoc_dialog = QtWidgets.QDialog()
    revoc_ui = PyUIs.ErrorDialog.Ui_Dialog()
    revoc_ui.setupUi(revoc_dialog)
    revoc_ui.label.setText(sa.secrets['revocation_code'])
    revoc_ui.label_2.setText('This is your revocation code. Write it down physically and keep it.\n' +
                            'You will need it in case you lose your authenticator.')
    revoc_dialog.exec_()
    code_dialog = QtWidgets.QDialog()
    code_ui = PyUIs.PhoneDialog.Ui_Dialog()
    code_ui.setupUi(code_dialog)
    code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
    while True:
        code_dialog.exec_()
        if endfunc.endfunc:
            return
        try:
            sa.finalize(code_ui.lineEdit.text())
            break
        except guard.SteamAuthenticatorError:
            code_ui.label_2.setText('Invalid code')


# noinspection PyArgumentList
def remove_authenticator(sa):
    if not sa.medium:
        mwa = AccountHandler.get_mobilewebauth(sa, error_popup)
        if not mwa:
            return
        sa.medium = mwa
    endfunc = Empty()
    endfunc.endfunc = False
    code_dialog = QtWidgets.QDialog()
    code_ui = PyUIs.PhoneDialog.Ui_Dialog()
    code_ui.setupUi(code_dialog)
    code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
    code_dialog.setWindowTitle('Remove authenticator')
    code_ui.label.setText('Type \'yes\' into the box below to remove your\nauthenticator. '
                          'Note that you will receive a 15-day\ntrade hold upon deactivating your authenticator.')
    for i in code_ui.buttonBox.buttons():
        if code_ui.buttonBox.buttonRole(i) == QtWidgets.QDialogButtonBox.AcceptRole:
            i.setEnabled(False)
    code_ui.lineEdit.textChanged.connect(lambda x: [(b.setEnabled(x.lower() == 'yes')
                                                    if code_ui.buttonBox.buttonRole(b) ==
                                                    QtWidgets.QDialogButtonBox.AcceptRole else None)
                                                    for b in code_ui.buttonBox.buttons()])
    code_dialog.exec_()
    if endfunc.endfunc:
        return

    try:
        sa.remove()
    except guard.SteamAuthenticatorError as e:
        error_popup(e)
        return
    shutil.rmtree(mafiles_path)
    restart()


# noinspection PyArgumentList
def copy_mafiles():
    while True:
        file_dialog = QtWidgets.QFileDialog()
        f = str(file_dialog.getExistingDirectory(caption='Select your maFiles folder.'))
        if f == '':
            break
        if not test_mafiles(f):
            error_popup('The selected folder does not contain valid maFiles.')
            continue
        if os.path.isdir(mafiles_path):
            if any('maFile' in x for x in os.listdir(mafiles_path)) or 'manifest.json' in os.listdir(mafiles_path):
                error_popup('The maFiles folder in the app folder is not empty.\nPlease remove it.')
                continue
            else:
                shutil.rmtree(mafiles_path)
        shutil.copytree(f, mafiles_path)
        break


# noinspection PyUnresolvedReferences,PyArgumentList
def main():
    global mafiles_path, app, manifest, timer_thread, main_window, main_ui
    base_path = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False)\
        else os.path.dirname(os.path.abspath(__file__))
    if test_mafiles(os.path.join(base_path, 'maFiles')):
        mafiles_path = os.path.join(base_path, 'maFiles')
    elif test_mafiles(os.path.expanduser(os.path.join('~', '.maFiles'))) and '--dbg' not in sys.argv:
        mafiles_path = os.path.expanduser(os.path.join('~', '.maFiles'))
    else:
        mafiles_path = os.path.join(base_path, 'maFiles') if os.path.basename(os.path.normpath(base_path)) ==\
                                      'PySteamAuth' else os.path.expanduser(os.path.join('~', '.maFiles'))
    app = QtWidgets.QApplication(sys.argv)
    while True:
        try:
            with open(os.path.join(mafiles_path, 'manifest.json')) as manifest_file:
                manifest = json.loads(manifest_file.read())
            with open(os.path.join(mafiles_path, manifest['entries'][0]['filename'])) as maf_file:
                maf = json.loads(maf_file.read())
            if not test_mafiles(mafiles_path):
                raise IOError()
            break
        except (IOError, ValueError, TypeError, IndexError, KeyError):
            if os.path.isdir(mafiles_path):
                if any('maFile' in x for x in os.listdir(mafiles_path)) or 'manifest.json' in os.listdir(mafiles_path):
                    error_popup('Failed to load maFiles.')
            setup_dialog = QtWidgets.QDialog()
            setup_ui = PyUIs.SetupDialog.Ui_Dialog()
            setup_ui.setupUi(setup_dialog)
            setup_ui.pushButton.clicked.connect(lambda: (setup_dialog.accept(), add_authenticator()))
            setup_ui.pushButton_2.clicked.connect(lambda: (copy_mafiles(), setup_dialog.accept()))
            setup_ui.pushButton_3.clicked.connect(sys.exit)
            setup_dialog.setFixedSize(setup_dialog.size())
            setup_dialog.exec_()
    sa = guard.SteamAuthenticator(maf)
    main_window = QMainWindow()
    main_ui = PyUIs.MainWindow.Ui_MainWindow()
    main_ui.setupUi(main_window)
    main_ui.codeBox.setText(sa.get_code())
    main_ui.codeTimeBar.setTextVisible(False)
    main_ui.codeTimeBar.valueChanged.connect(main_ui.codeTimeBar.repaint)
    main_ui.tradeCheckBox.setChecked(manifest['auto_confirm_trades'])
    main_ui.marketCheckBox.setChecked(manifest['auto_confirm_market_transactions'])
    main_ui.tradeCheckBox.stateChanged.connect(lambda: set_auto_accept(sa, main_ui.tradeCheckBox,
                                                                       main_ui.marketCheckBox))
    main_ui.marketCheckBox.stateChanged.connect(lambda: set_auto_accept(sa, main_ui.tradeCheckBox,
                                                                        main_ui.marketCheckBox))
    main_ui.confAllButton.clicked.connect(lambda: accept_all(sa))
    main_ui.confListButton.clicked.connect(lambda: (main_ui.confListButton.setText('Opening...'), open_conf_dialog(sa)))
    main_ui.removeButton.clicked.connect(lambda: remove_authenticator(sa))
    main_ui.createBCodesButton.clicked.connect(lambda: backup_codes_popup(sa))
    main_ui.removeBCodesButton.clicked.connect(lambda: backup_codes_delete(sa))
    main_ui.openFolderButton.clicked.connect(lambda: webbrowser.open('file://' + mafiles_path.replace('\\', '/')))
    main_ui.copyButton.clicked.connect(lambda: (main_ui.codeBox.selectAll(), main_ui.codeBox.copy()))
    main_window.setFixedSize(main_window.size())
    main_window.error_popup_event.connect(error_popup)
    main_window.relogin_event.connect(lambda s: (AccountHandler.full_refresh(s, QMainWindow),
                                                 setattr(auto_accept_thread, 'running', False),
                                                 main_ui.tradeCheckBox.setChecked(False),
                                                 main_ui.marketCheckBox.setChecked(False)))
    timer_thread = TimerThread(sa, 30 - (sa.get_time() % 30))
    timer_thread.bar_update.connect(main_ui.codeTimeBar.setValue)
    timer_thread.code_update.connect(main_ui.codeBox.setText)
    timer_thread.start()
    set_auto_accept(sa, main_ui.tradeCheckBox, main_ui.marketCheckBox)

    main_window.show()
    main_window.raise_()
    app.exec_()

    timer_thread.terminate()
    try:
        auto_accept_thread.running = False
        auto_accept_thread.wait()
    except (NameError, AttributeError):
        pass


if __name__ == '__main__':
    sys.exit(main())
