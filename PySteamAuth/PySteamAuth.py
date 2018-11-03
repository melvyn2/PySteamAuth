#!/usr/bin/env python3.6

#   Copyright (C) 2018  melvyn2
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

import json
import sys
import shutil
import os
import re
import multiprocessing
import time as timemodule
import webbrowser
import requests
import requests.cookies
import urllib.parse
import binascii
from steam import guard, webauth
from PyQt5 import QtWidgets, QtCore, QtGui, QtWebEngineWidgets, QtNetwork
try:
	from . import PyUIs
except ImportError:
	# noinspection PyUnresolvedReferences
	import PyUIs


if not(sys.version_info.major == 3 and sys.version_info.minor >= 6):
	raise SystemExit('ERROR: Requires python >= 3.6')


class Empty(object):
	pass


class Confirmation(object):
	def __init__(self, conf_id, conf_key, conf_type, conf_creator, conf_description):
		self.id = conf_id
		self.key = conf_key
		self.type = conf_type
		self.creator = conf_creator
		self.description = conf_description


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
			timemodule.sleep(1)


def restart():
	timer_thread.terminate()
	try:
		auto_accept_thread.terminate()
	except (NameError, AttributeError):
		pass
	if getattr(sys, 'frozen', False):
		os.execl(sys.executable, sys.executable)
	else:
		os.execl(sys.executable, sys.executable,
				os.path.join(os.path.dirname(os.path.abspath(__file__)), __file__))


# noinspection PyArgumentList
def error_popup(message, header=None):
	if multiprocessing.current_process().name != 'MainProcess':
		print(header if header else 'Error: ', message)
		return
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
		mwa = get_mobilewebauth(sa)
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
		mwa = get_mobilewebauth(sa)
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
	except (IOError, guard.SteamAuthenticatorError):
		return False
	return True


def refresh_session(sa):
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
		return True
	except requests.exceptions.ConnectionError:
		return False


def auto_accept(sa, trades, markets):
	if trades or markets:
		while True:
			accept_all(sa, trades, markets)
			timemodule.sleep(5)


def set_auto_accept(sa, trades_checkbox, markets_checkbox):
	global auto_accept_thread
	try:
		auto_accept_thread.terminate()
	except (NameError, AttributeError):
		pass
	auto_accept_thread = multiprocessing.Process(target=auto_accept, args=(sa, trades_checkbox.isChecked(),
																			markets_checkbox.isChecked()))
	auto_accept_thread.start()

	manifest['auto_confirm_trades'] = trades_checkbox.isChecked()
	manifest['auto_confirm_market_transactions'] = markets_checkbox.isChecked()
	with open(os.path.join(mafiles_path, 'manifest.json'), 'w') as manifest_file:
		manifest_file.write(json.dumps(manifest))


def fetch_confirmations(sa):
	if not refresh_session(sa):
		error_popup('Failed to refresh session.', 'Warning:')
	conf_url = 'https://steamcommunity.com/mobileconf/conf?' + generate_query('conf', sa)
	jar = requests.cookies.RequestsCookieJar()
	jar.set('mobileClientVersion', '0 (2.1.3)', path='/', domain='.steamcommunity.com')
	jar.set('mobileClient', 'android', path='/', domain='.steamcommunity.com')
	jar.set('steamid', str(sa.secrets['Session']['SteamID']), path='/', domain='.steamcommunity.com')
	jar.set('steamLogin', str(sa.secrets['Session']['SteamLogin']), path='/', domain='.steamcommunity.com')
	jar.set('steamLoginSecure', str(sa.secrets['Session']['SteamLoginSecure']), path='/', domain='.steamcommunity.com')
	jar.set('Steam_Language', 'english', path='/', domain='.steamcommunity.com')
	jar.set('sessionid', str(sa.secrets['Session']['SessionID']), path='/', domain='.steamcommunity.com')
	try:
		r = requests.get(conf_url, cookies=jar)
	except requests.exceptions.ConnectionError:
		error_popup('Connection Error.')
		return []
	conf_regex = '<div class=\"mobileconf_list_entry\" id=\"conf[0-9]+\" data-confid=\"(\\d+)\" ' + \
		'data-key=\"(\\d+)\" data-type=\"(\\d+)\" data-creator=\"(\\d+)\"'
	conf_desc_regex = '<div>((Confirm|Trade|Sell -) .+)</div>'
	if '<div>Nothing to confirm</div>' in r.text:
		return []
	confs = re.findall(conf_regex, r.text)
	descs = re.findall(conf_desc_regex, r.text)
	ret = []
	for i in range(len(confs)):
		ret.append(Confirmation(confs[i][0], confs[i][1], confs[i][2], confs[i][3], re.sub('[<].*[>]', '', descs[i][0])))
	return ret


def accept_all(sa, trades=True, market=True):
	data = 'op=allow&' + generate_query('allow', sa)
	confs = fetch_confirmations(sa)
	if len(confs) == 0:
		return
	if not refresh_session(sa):
		error_popup('Failed to refresh session.', 'Warning:')
	jar = requests.cookies.RequestsCookieJar()
	jar.set('mobileClientVersion', '0 (2.1.3)', path='/', domain='.steamcommunity.com')
	jar.set('mobileClient', 'android', path='/', domain='.steamcommunity.com')
	jar.set('steamid', str(sa.secrets['Session']['SteamID']), path='/', domain='.steamcommunity.com')
	jar.set('steamLogin', str(sa.secrets['Session']['SteamLogin']), path='/', domain='.steamcommunity.com')
	jar.set('steamLoginSecure', str(sa.secrets['Session']['SteamLoginSecure']), path='/', domain='.steamcommunity.com')
	jar.set('Steam_Language', 'english', path='/', domain='.steamcommunity.com')
	jar.set('sessionid', str(sa.secrets['Session']['SessionID']), path='/', domain='.steamcommunity.com')
	for i in range(len(confs)):
		if (not trades) and confs[i].type == 2:
			del confs[i]
		if (not market) and confs[i].type == 3:
			del confs[i]
	if len(confs) == 0:
		return
	elif len(confs) == 1:
		url = 'https://steamcommunity.com/mobileconf/ajaxop?'
		data += '&cid=' + confs[0].id + '&ck=' + confs[0].key
		requests.get(url + data, cookies=jar)
	else:
		url = 'https://steamcommunity.com/mobileconf/multiajaxop'
		for i in confs:
			data += '&cid[]=' + i.id + '&ck[]=' + i.key
		requests.post(url, data=data, cookies=jar)


# noinspection PyArgumentList
def open_conf_dialog(sa):
	if not refresh_session(sa):
		error_popup('Failed to refresh session.', 'Warning:')
	conf_dialog = QtWidgets.QDialog()
	conf_ui = PyUIs.ConfirmationDialog.Ui_Dialog()
	conf_ui.setupUi(conf_dialog)
	conf_dialog.setFixedSize(conf_dialog.size())
	conf_ui.pushButton.clicked.connect(conf_ui.webEngineView.reload)
	web_profile = QtWebEngineWidgets.QWebEngineProfile(conf_ui.webEngineView)
	mcv = QtNetwork.QNetworkCookie(b'mobileClientVersion', b'0 (2.1.3)')
	mcv.setDomain('.steamcommunity.com')
	mcv.setPath('/')
	web_profile.cookieStore().setCookie(mcv)
	stmid = QtNetwork.QNetworkCookie(b'steamid', bytes(str(sa.secrets['Session']['SteamID']), 'ascii'))
	stmid.setDomain('.steamcommunity.com')
	stmid.setPath('/')
	web_profile.cookieStore().setCookie(stmid)
	stmli = QtNetwork.QNetworkCookie(b'steamLogin', bytes(sa.secrets['Session']['SteamLogin'], 'ascii'))
	stmli.setDomain('.steamcommunity.com')
	stmli.setPath('/')
	stmli.setHttpOnly(True)
	web_profile.cookieStore().setCookie(stmli)
	stmlis = QtNetwork.QNetworkCookie(b'steamLoginSecure', bytes(sa.secrets['Session']['SteamLoginSecure'], 'ascii'))
	stmlis.setDomain('.steamcommunity.com')
	stmlis.setPath('/')
	stmlis.setHttpOnly(True)
	stmlis.setSecure(True)
	web_profile.cookieStore().setCookie(stmlis)
	sid = QtNetwork.QNetworkCookie(b'sessionid', bytes(sa.secrets['Session']['SessionID'], 'ascii'))
	sid.setDomain('.steamcommunity.com')
	sid.setPath('/')
	web_profile.cookieStore().setCookie(sid)
	url = 'https://steamcommunity.com/mobileconf/conf?' + generate_query('conf', sa)
	web_profile.cookieStore().loadAllCookies()
	page = QtWebEngineWidgets.QWebEnginePage(web_profile, conf_ui.webEngineView)
	conf_ui.webEngineView.setPage(page)
	tradeid = Empty()
	tradeid.id = ''
	conf_ui.webEngineView.urlChanged.connect(lambda x: setattr(tradeid, 'id', get_tradeid_from_url(x)))
	loop = QtCore.QEventLoop()
	conf_ui.webEngineView.loadFinished.connect(lambda: (loop.quit(), conf_ui.webEngineView.page().runJavaScript('''
while(document.getElementsByClassName("responsive_header").length > 0){
	document.getElementsByClassName("responsive_header")[0].parentNode.removeChild(document.getElementsByClassName("responsive_header")[0]);
}
function sleep(ms) {
	return new Promise(resolve => setTimeout(resolve, ms));
}
async function reload() {
	await sleep(2000)
	location.reload(true);
}
window.GetValueFromLocalURL =
	function(url, timeout, success, error, fatal) {{
		if(url.indexOf('steammobile://steamguard?op=conftag&arg1=allow') !== -1) {{
			success('{0}');
			reload();
		}} else if(url.indexOf('steammobile://steamguard?op=conftag&arg1=cancel') !== -1) {{
			success('{1}');
			reload();
		}} else if(url.indexOf('steammobile://steamguard?op=conftag&arg1=details') !== -1) {{
			success('{2}');
		}}
	}}'''.replace('{0}', generate_query('allow', sa)).replace('{1}', generate_query('cancel', sa))
		.replace('{2}', generate_query('details' + tradeid.id, sa)))))
	conf_ui.webEngineView.load(QtCore.QUrl(url))
	loop.exec_()
	conf_ui.webEngineView.show()
	conf_dialog.show()
	conf_dialog.exec_()
	main_ui.pushButton_2.setText('Confirmations')


# noinspection PyArgumentList
def get_mobilewebauth(sa=None):
	endfunc = Empty()
	endfunc.endfunc = False
	login_dialog = QtWidgets.QDialog()
	login_ui = PyUIs.LoginDialog.Ui_Dialog()
	login_ui.setupUi(login_dialog)
	login_ui.buttonBox.rejected.connect(lambda: setattr(endfunc, 'endfunc', True))
	if sa:
		login_ui.lineEdit.setText(sa.secrets['account_name'])
	while True:
		# noinspection PyUnusedLocal
		required = None
		login_dialog.exec_()
		user = webauth.MobileWebAuth(username=login_ui.lineEdit.text(), password=login_ui.lineEdit_2.text())
		username = login_ui.lineEdit.text()
		try:
			user.login()
		except webauth.HTTPError:
			error_popup('Connection Error')
			return
		except KeyError:
			login_ui.label_3.setText('Username and password required.')
		except webauth.LoginIncorrect as e:
			if 'is incorrect' in e:
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
		if endfunc.endfunc:
			return
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


# noinspection PyArgumentList
def add_authenticator():
	endfunc = Empty()
	endfunc.endfunc = False
	mwa = get_mobilewebauth()
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
		if 'DuplicateRequest' in e:
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
		mwa = get_mobilewebauth(sa)
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
													if code_ui.buttonBox.buttonRole(b) == QtWidgets.QDialogButtonBox.AcceptRole else None)
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
		mafiles_path = os.path.join(base_path, 'maFiles') if os.path.basename(os.path.normpath(base_path)) == 'PySteamAuth' \
			else os.path.expanduser(os.path.join('~', '.maFiles'))
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
	main_window = QtWidgets.QMainWindow()
	main_ui = PyUIs.MainWindow.Ui_MainWindow()
	main_ui.setupUi(main_window)
	main_ui.textEdit.setText(sa.get_code())
	main_ui.progressBar.setTextVisible(False)
	main_ui.progressBar.valueChanged.connect(main_ui.progressBar.repaint)
	main_ui.checkBox.stateChanged.connect(lambda: set_auto_accept(sa, main_ui.checkBox, main_ui.checkBox_2))
	main_ui.checkBox_2.stateChanged.connect(lambda: set_auto_accept(sa, main_ui.checkBox, main_ui.checkBox_2))
	main_ui.checkBox.setChecked(manifest['auto_confirm_trades'])
	main_ui.checkBox_2.setChecked(manifest['auto_confirm_market_transactions'])
	main_ui.pushButton_1.clicked.connect(lambda: accept_all(sa))
	main_ui.pushButton_2.clicked.connect(lambda: (main_ui.pushButton_2.setText('Opening...'), open_conf_dialog(sa)))
	main_ui.pushButton_3.clicked.connect(lambda: remove_authenticator(sa))
	main_ui.pushButton_4.clicked.connect(lambda: backup_codes_popup(sa))
	main_ui.pushButton_5.clicked.connect(lambda: backup_codes_delete(sa))
	main_ui.pushButton_6.clicked.connect(lambda: webbrowser.open('file://' + mafiles_path.replace('\\', '/')))
	main_window.setFixedSize(main_window.size())
	timer_thread = TimerThread(sa, 30 - (sa.get_time() % 30))
	timer_thread.bar_update.connect(main_ui.progressBar.setValue)
	timer_thread.code_update.connect(main_ui.textEdit.setText)
	timer_thread.start()
	main_window.show()
	app.exec_()

	timer_thread.terminate()
	try:
		auto_accept_thread.terminate()
	except (NameError, AttributeError):
		pass


if __name__ == '__main__':
	sys.exit(main())
