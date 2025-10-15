cd /d "%~dp0"
python ssu2_improved.py backup E:\Steam\userdata\31082404 -o D:\SteamShots >> output.txt 2>&1
python ssu2_improved.py update >> output.txt 2>&1
python ssu2_improved.py rename D:\SteamShots >> output.txt 2>&1
python ssu2_improved.py sort D:\SteamShots >> output.txt 2>&1
python ssu2_improved.py sort C:\Users\PatrickJr\Dropbox\SteamScreenshots >> output.txt 2>&1
python ssu2_improved.py update >> output.txt 2>&1
python ssu2_improved.py rename C:\Users\PatrickJr\Dropbox\SteamScreenshots >> output.txt 2>&1
python ssu2_improved.py merge C:\Users\PatrickJr\Dropbox\SteamScreenshots D:\SteamShots >> output.txt 2>&1
python ssu2_improved.py gallery -d D:\SteamShots -o gallery.html >> output.txt 2>&1
pause
