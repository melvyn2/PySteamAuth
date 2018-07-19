#!/usr/bin/env python2.7

#   Copyright (C) 2018 melvyn2
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, version 3.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import fnmatch
import subprocess

for r, d, f in os.walk('.'):
	for t in fnmatch.filter(f, '*.ui'):
		subprocess.call(['python', '-m', 'PyQt5.uic.pyuic', os.path.abspath(os.path.join(r, t)), '-o',
			os.path.abspath(os.path.join(r, t)).replace('UIs', 'PyUIs').replace('.ui', '.py')])
