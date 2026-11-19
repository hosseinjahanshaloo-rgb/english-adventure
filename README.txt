English Adventure - Mobile (Kivy)  |  Grade 8 / Prospect 2, lessons 1-7

1) Test on your computer first
   pip install -r requirements.txt
   python main.py            (opens a phone-sized window)

2) Build the Android APK  (Linux, WSL2 on Windows, or Google Colab)
   pip install buildozer cython
   buildozer android debug   (first build downloads the SDK/NDK, ~20-40 min)
   -> APK appears in bin/ ; copy it to the phone and install it.

CONTENT
 data/lesson01..07.json  = built from the Prospect 2 student book (1405 edition): lesson titles, vocabulary
 (Photo Dictionary + lesson words), example sentences from the conversations/practices, and grammar
 questions based on each lesson's Key Language. Persian meanings and the grammar questions were written
 for this app - please review them. Avoid ( ) and / inside Persian text (they display in the wrong order).
 Rebuild rules: Match Game needs >= 6 words, Listen & Choose >= 4, every Persian meaning must be unique per lesson.

PRONUNCIATION
 audio/<word>.ogg  = recorded pronunciation of every word and sentence (played offline).
 After you edit a lesson, regenerate with:  python make_audio.py
 (needs Linux: sudo apt install espeak-ng mbrola mbrola-us1 vorbis-tools)
 You can also replace any audio/<word>.ogg with a real human recording (same file name).

SOUND EFFECTS
 sounds/*.wav (made by make_sounds.py). Sound effects can be turned off from the main menu.
