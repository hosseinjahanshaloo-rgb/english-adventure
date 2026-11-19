[app]
title = English Adventure
package.name = englishadventure
package.domain = org.englishadventure
source.dir = .
source.include_exts = py,json,ttf,wav,mp3,ogg
source.exclude_dirs = __pycache__,bin,.buildozer
version = 0.2.0
requirements = python3==3.11.5,hostpython3==3.11.5,kivy==2.3.0,arabic-reshaper==3.0.0,python-bidi==0.4.2,six,plyer,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = VIBRATE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
