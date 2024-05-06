# lspJump

GEdit plugin to browse code using the LSP protocol (https://microsoft.github.io/language-server-protocol/)

## License

GPLv3.0 See LICENSE.txt

## Requires

This plugin also requires a language server for your programming language. These ones are currently verified to work (tested by me):

* ccls (https://github.com/MaskRay/ccls) (C,C++,Objective-C)
* pyls (https://github.com/palantir/python-language-server) (Python)
* For other examples, see lspjumpsettings.xml.template

Other language servers could work. To see if your programming language have support from a language server check (https://microsoft.github.io/language-server-protocol/implementors/servers/) or search using a search engine. You can change in settings (F5) if you want to try another server.

To change to another language, simply type something like "/usr/bin/pyls" in the settings. If it also requires some additional arguments add them in the "Binary arguments text box". There each argument is separated with a space.

## Installation

Clone this project into 

```
mkdir -p ~/.local/share/gedit/plugins
cd ~/.local/share/gedit/plugins
git clone https://github.com/CaF2/lspJump.git
```

If it is the first time you use lspJump do also:
```
cd ~/.local/share/gedit/plugins/lspJump
cp lspJumpsettings.xml.template lspJumpsettings.xml
```

Open gedit and do

* gedit -> settings -> plugins -> check lspJump

## Usage example

* Open a file with gedit within a "project folder".
* Hit "F5"
* Select a profile. In this example we use "Ccls" which supports C,C++
* Write the path to the folder with "compile_commands.json". You can also try "Search project dir"
* Press "Change"
* F3 (go to definition) and F4 (show references) should now work if you have clicked somewhere in your code
* To go back press "alt+r", to go forwards press "alt+shift+r"

## What should work

* Go to definition (F3)
* Show references (F4)
* Hover to see information
* Tab completion (Ctrl+e)

## Note for Makefile users

* To make the "compile_commands.json", you may use bear (https://github.com/rizsotto/Bear)

Example:

```
bear -- make -B
```

* LSP communicates with the plugin using a pipe (->stdin), as a design decision it does not run by default.

## Configuration

The graphical menues should work, otherwise the configuration file for this plugin is located here: 

```
~/.local/share/gedit/plugins/lspJump/lspJumpsettings.xml
```

The first language mentioned is the default language

## Thanks to (based on):

gtagJump (https://github.com/utisam/gtagJump)
* Masatoshi Tsushima
* Jacek Pliszka

pylspclient (https://github.com/yeger00/pylspclient)
* Avi Yeger
