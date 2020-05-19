#	lspJump - a gedit plugin to browse code using the LSP protocol (https://microsoft.github.io/language-server-protocol/)
#	Copyright (C) 2020  Florian Evaldsson

#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.

#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.

#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <https://www.gnu.org/licenses/>.

from lspJump.LspNavigator import LspNavigator

LSP_BIN = "/usr/bin/ccls"

PROJECT_PATH = ''

keyJumpDef = "F3"
keyJumpRef = "F4"
keyJumpBack = "<Alt>b"
keyJumpNext = "<Alt>n"
keyProjDir = "F5"

historymax = 100

LSP_NAVIGATOR=None
