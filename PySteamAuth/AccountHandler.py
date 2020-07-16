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

import requests
import urllib.parse
from steam import webauth, guard
from PyQt5 import QtWidgets, QtGui

import PyUIs
import Common


class Empty:
    pass

# TODO move global sa into a file level global here


# TODO trigger only on steammobile://lostauth
def refresh_session(sa: guard.SteamAuthenticator, recursed: bool = False):
    url = 'https://api.steampowered.com/IMobileAuthService/GetWGToken/v0001'
    try:
        r = requests.post(url, data={'access_token': urllib.parse.quote_plus(sa.secrets['Session']['OAuthToken'])})
        response = json.loads(r.text)['response']
        sa.secrets['Session']['SteamLogin'] = str(sa.secrets['Session']['SteamID']) + "%7C%7C" + response['token']
        sa.secrets['Session']['SteamLoginSecure'] = str(sa.secrets['Session']['SteamID']) + "%7C%7C" +\
            response['token_secure']
        return True
    except requests.exceptions.ConnectionError:
        Common.error_popup('Failed to refresh session (connection error).', 'Warning')
        return False
    except (json.JSONDecodeError, KeyError) as e:
        print(e)
        if recursed:
            Common.error_popup('Failed to use newly generated token.')
        else:
            Common.error_popup('Steam session token expired. You will be prompted to sign back in.')
            if full_refresh(sa):
                return refresh_session(sa, recursed=True)
            else:
                return False


def full_refresh(sa: guard.SteamAuthenticator):
    mwa = get_mobilewebauth(sa, True)
    if not mwa:
        return False
    if 'Session' not in sa.secrets:
        sa.secrets['Session'] = {'SteamID': mwa.steam_id}
    sa.secrets['Session']['OAuthToken'] = mwa.oauth_token
    sa.secrets['Session']['SessionID'] = mwa.session_id
    return True


def get_mobilewebauth(sa: guard.SteamAuthenticator = None, force_username: bool = True):
    if getattr(sa, 'backend', False) and sa.backend.logged_on:
        return sa.backend
    if 'Session' in sa.secrets.keys():
        token = sa.secrets['Session'].get('OAuthToken', False)

        if token:
            try:
                sa.backend = webauth.MobileWebAuth(username=sa.secrets['account_name'])
                sa.backend.oauth_login(oauth_token=sa.secrets['Session']['OAuthToken'],
                                       steam_id=sa.secrets['Session']['SteamID'])
            except webauth.LoginIncorrect:
                pass
            except webauth.WebAuthException:
                Common.error_popup('Failed to decode login response')
                pass
            else:
                return sa
    endfunc = Empty()
    endfunc.endfunc = False
    login_dialog = QtWidgets.QDialog()
    login_ui = PyUIs.LogInDialog.Ui_Dialog()
    login_ui.setupUi(login_dialog)
    login_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
    login_ui.usernameBox.setDisabled((force_username and (sa is not None)))
    if sa:
        login_ui.usernameBox.setText(sa.secrets['account_name'])
    # noinspection PyUnusedLocal
    required = None
    while True:
        login_dialog.exec_()
        if endfunc.endfunc:
            return
        user = webauth.MobileWebAuth(username=login_ui.usernameBox.text(), password=login_ui.passwordBox.text())
        username = login_ui.usernameBox.text()
        try:
            user.login()
        except webauth.HTTPError:
            Common.error_popup('Connection Error')
            return
        except KeyError:
            login_ui.msgBox.setText('Username and password required.')
        except webauth.LoginIncorrect as e:
            if 'is incorrect' in str(e):
                login_ui.msgBox.setText('Incorrect username and/or password.')
            else:
                login_ui.msgBox.setText('Incorrect username and/or password,\n or too many attempts.')
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
            pixmap.loadFromData(requests.get(user.captcha_url).content)
            captcha_ui.captchaLabel.setPixmap(pixmap)
            while True:
                captcha_dialog.exec_()
                if endfunc.endfunc:
                    return
                captcha = captcha_ui.captchaInputBox.text()
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
            code_ui.actionBox.setText('Enter the email code you have received:')
            while True:
                code_dialog.exec_()
                if endfunc.endfunc:
                    return
                email_code = code_ui.codeBox.text()
                try:
                    user.login(email_code=email_code, captcha=captcha)
                    break
                except webauth.EmailCodeRequired:
                    code_ui.msgBox.setText('Invalid code')
                except webauth.LoginIncorrect as e:
                    code_ui.msgBox.setText(str(e))
                except webauth.CaptchaRequired:
                    required = 'captcha'
                    break
        elif required == '2FA':
            code_dialog = QtWidgets.QDialog()
            code_ui = PyUIs.PhoneDialog.Ui_Dialog()
            code_ui.setupUi(code_dialog)
            code_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
            code_dialog.setWindowTitle('2FA code')
            code_ui.actionBox.setText('Enter a two-factor code for Steam:')
            while True:
                if sa and username == sa.secrets['account_name']:
                    twofactor_code = sa.get_code()
                else:
                    code_dialog.exec_()
                    if endfunc.endfunc:
                        return
                    twofactor_code = code_ui.codeBox.text()
                try:
                    user.login(twofactor_code=twofactor_code, captcha=captcha)
                    break
                except webauth.TwoFactorCodeRequired:
                    code_ui.msgBox.setText('Invalid Code')
                except webauth.LoginIncorrect as e:
                    code_ui.msgBox.setText(str(e))
                except webauth.CaptchaRequired:
                    required = 'captcha'
                    break
        if user.logged_on:
            break
    # sa.backend = user
    # sa.secrets['Session']['OAuthToken'] = user.oauth_token
    # sa.secrets['Session']['SteamID'] = user.steam_id
    # TODO save these on app close
    return user
