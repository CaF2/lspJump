# lspJump

A gedit plugin to browse code using the LSP protocol (https://microsoft.github.io/language-server-protocol/)

## License

GPLv3.0 See LICENSE.txt

## Requires

* ccls (https://github.com/MaskRay/ccls) (C,C++,Objective-C)

Maybe other languages work? You can change in settings.py if you want to try another server.

## Installation

Clone this project into 

```
mkdir -p ~/.local/share/gedit/plugins
cd ~/.local/share/gedit/plugins
git clone https://github.com/CaF2/lspJump.git
```

Open gedit and do

* gedit -> settings -> plugins -> check lspJump

## Usage example

* Open a file with gedit within a "project folder".
* Hit "F5" and write the path to the folder with "compile_commands.json"
* Press "change"
* F3 (go to definition) and F4 (show references) should now work if you have clicked somewhere in your code
* To go back press "alt+b", to go forwards press "alt+n"

## Note

* To make the "compile_commands.json", you man use bear (https://github.com/rizsotto/Bear)

Example:

```
bear make -B
```

* LSP communicates with the plugin using a pipe (->stdin), as a design decision it does not run by default.

## Thanks to (based on):

gtagJump (https://github.com/utisam/gtagJump)
* Masatoshi Tsushima
* Jacek Pliszka

pylspclient (https://github.com/yeger00/pylspclient)
* Avi Yeger
