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


import requests
import urllib.parse
from steam import webauth
from PyQt5 import QtWidgets, QtGui
import json
import os
try:
    from . import PyUIs
except ImportError:
    # noinspection PyUnresolvedReferences
    import PyUIs


class Empty:
    pass


def refresh_session(sa, mafiles_path, manifest):
    url = 'https://api.steampowered.com/IMobileAuthService/GetWGToken/v0001'
    try:
        r = requests.post(url, data={'access_token': urllib.parse.quote_plus(sa.secrets['Session']['OAuthToken'])})
        response = json.loads(r.text)['response']
        token = str(sa.secrets['Session']['SteamID']) + "%7C%7C" + response['token']
        token_secure = str(sa.secrets['Session']['SteamID']) + "%7C%7C" + response['token_secure']
        sa.secrets['Session']['SteamLogin'] = token
        sa.secrets['Session']['SteamLoginSecure'] = token_secure
        with open(os.path.join(mafiles_path, manifest['entries'][0]['filename']), 'w') as maf:
            maf.write(json.dumps(sa.secrets))
        return 0
    except requests.exceptions.ConnectionError:
        return 1
    except json.JSONDecodeError:
        return 2
    except KeyError:
        return 2


def full_refresh(sa, main_window):
    mwa = get_mobilewebauth(sa, main_window, True)
    if not mwa:
        return False
    try:
        sa.secrets['Session']
    except KeyError:
        sa.secrets['Session'] = {'SteamID': mwa.steam_id}
    sa.secrets['Session']['OAuthToken'] = mwa.oauth_token
    sa.secrets['Session']['SessionID'] = mwa.session_id
    return True


# noinspection PyArgumentList
def get_mobilewebauth(sa, main_window, force_login=False):
    endfunc = Empty()
    endfunc.endfunc = False
    login_dialog = QtWidgets.QDialog()
    login_ui = PyUIs.LoginDialog.Ui_Dialog()
    login_ui.setupUi(login_dialog)
    login_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
    login_ui.lineEdit.setDisabled(force_login)
    if sa:
        login_ui.lineEdit.setText(sa.secrets['account_name'])
    while True:
        # noinspection PyUnusedLocal
        required = None
        login_dialog.exec_()
        if endfunc.endfunc:
            return
        user = webauth.MobileWebAuth(username=login_ui.lineEdit.text(), password=login_ui.lineEdit_2.text())
        username = login_ui.lineEdit.text()
        try:
            user.login()
        except webauth.HTTPError:
            main_window.error_popup_event.emit('Connection Error', '')
            return
        except KeyError:
            login_ui.label_3.setText('Username and password required.')
        except webauth.LoginIncorrect as e:
            if 'is incorrect' in str(e):
                login_ui.label_3.setText('Incorrect username and/or password.')
            else:
                login_ui.label_3.setText('Incorrect username and/or password,\n or too many attempts.')
            print(e)
        except webauth.CaptchaRequired:
            required = 'captcha'
            break
        except webauth.EmailCodeRequired:
            required = 'email'
            break
        except webauth.TwoFactorCodeRequired:
            required = '2FA'
            break
    captcha = ''
    twofactor_code = ''
    email_code = ''
    while True:
        if required == 'captcha':
            captcha_dialog = QtWidgets.QDialog()
            captcha_ui = PyUIs.CaptchaDialog.Ui_Dialog()
            captcha_ui.setupUi(captcha_dialog)
            captcha_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(requests.get(user.captcha_url).text)
            captcha_ui.label_2.setPixmap(pixmap)
            while True:
                captcha_dialog.exec_()
                if endfunc.endfunc:
                    return
                captcha = captcha_ui.lineEdit.text()
                try:
                    user.login(captcha=captcha, email_code=email_code, twofactor_code=twofactor_code)
                    break
                except webauth.CaptchaRequired:
                    captcha_ui.label_3.setText('Incorrect')
                except webauth.LoginIncorrect as e:
                    captcha_ui.label_3.setText(str(e))
                except webauth.EmailCodeRequired:
                    required = 'email'
                    break
                except webauth.TwoFactorCodeRequired:
                    required = '2FA'
                    break
        elif required == 'email':
            code_dialog = QtWidgets.QDialog()
            code_ui = PyUIs.PhoneDialog.Ui_Dialog()
            code_ui.setupUi(code_dialog)
            code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
            code_dialog.setWindowTitle('Email code')
            code_ui.label.setText('Enter the email code you have received:')
            while True:
                code_dialog.exec_()
                if endfunc.endfunc:
                    return
                email_code = code_ui.lineEdit.text()
                try:
                    user.login(email_code=email_code, captcha=captcha)
                    break
                except webauth.EmailCodeRequired:
                    code_ui.label_2.setText('Invalid code')
                except webauth.LoginIncorrect as e:
                    code_ui.label_2.setText(str(e))
                except webauth.CaptchaRequired:
                    required = 'captcha'
                    break
        elif required == '2FA':
            code_dialog = QtWidgets.QDialog()
            code_ui = PyUIs.PhoneDialog.Ui_Dialog()
            code_ui.setupUi(code_dialog)
            code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
            code_dialog.setWindowTitle('2FA code')
            code_ui.label.setText('Enter a two-factor code for Steam:')
            while True:
                if sa and username == sa.secrets['account_name']:
                    twofactor_code = sa.get_code()
                else:
                    code_dialog.exec_()
                    if endfunc.endfunc:
                        return
                    twofactor_code = code_ui.lineEdit.text()
                try:
                    user.login(twofactor_code=twofactor_code, captcha=captcha)
                    break
                except webauth.TwoFactorCodeRequired:
                    code_ui.label_2.setText('Invalid Code')
                except webauth.LoginIncorrect as e:
                    code_ui.label_2.setText(str(e))
                except webauth.CaptchaRequired:
                    required = 'captcha'
                    break
        if user.complete:
            break
    return user
