cd /d "%~dp0"
python ssu2.py backup E:\Steam\userdata\31082404 -o D:\SteamShots >> output.txt 2>&1
python ssu2.py update >> output.txt 2>&1
python ssu2.py rename D:\SteamShots >> output.txt 2>&1
python ssu2.py sort D:\SteamShots >> output.txt 2>&1
python ssu2.py sort C:\Users\PatrickJr\Dropbox\SteamScreenshots >> output.txt 2>&1
python ssu2.py update >> output.txt 2>&1
python ssu2.py rename C:\Users\PatrickJr\Dropbox\SteamScreenshots >> output.txt 2>&1
python ssu2.py merge C:\Users\PatrickJr\Dropbox\SteamScreenshots D:\SteamShots >> output.txt 2>&1
python ssu2.py gallery -d D:\SteamShots -o gallery.html >> output.txt 2>&1
pause
