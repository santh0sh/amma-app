#!/usr/bin/env bash
# Install the APK on the CI emulator, open it, and capture screenshots + log.
set -x
adb install -r amma.apk
adb shell pm grant io.github.santh0sh.amma android.permission.POST_NOTIFICATIONS || true
adb logcat -c
adb shell am start -n io.github.santh0sh.amma/org.beeware.android.MainActivity
sleep 75
adb exec-out screencap -p > app-screenshot.png
# second tab (calendar) and stories, by tapping the bottom bar
W=$(adb shell wm size | grep -o '[0-9]*x[0-9]*' | tail -1 | cut -dx -f1); H=$(adb shell wm size | grep -o '[0-9]*x[0-9]*' | tail -1 | cut -dx -f2)
Y=$((H*96/100))
adb shell input tap $((W*3/8)) $Y; sleep 5; adb exec-out screencap -p > app-screenshot-calendar.png
adb shell input tap $((W*5/8)) $Y; sleep 8; adb exec-out screencap -p > app-screenshot-stories.png
adb shell input tap $((W*7/8)) $Y; sleep 4; adb exec-out screencap -p > app-screenshot-setup.png
# tap an element by its visible text using the accessibility dump (WebView content included)
tapText(){ adb shell dumpsys activity activities | grep -m1 -E 'mResumedActivity|topResumedActivity'; adb shell uiautomator dump /sdcard/ui.xml; adb shell cat /sdcard/ui.xml > ui.xml; cp ui.xml "ui-$(date +%s).xml.txt"; wc -c ui.xml; adb shell dumpsys activity activities | grep -m1 -E 'mResumedActivity|topResumedActivity' 
  b=$(python3 - "$1" <<'PY'
import re,sys
x=open("ui.xml",encoding="utf-8",errors="replace").read()
for m in re.finditer(r'<node [^>]*>',x):
    n=m.group(0)
    if sys.argv[1] in n:
        a=re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',n)
        if a:
            x1,y1,x2,y2=map(int,a.groups());print((x1+x2)//2,(y1+y2)//2);break
PY
); echo "tapText $1 -> $b"; [ -n "$b" ] && adb shell input tap $b; }
# reader + TTS: open the stories tab, the first story, then the speaker button
adb shell input tap $((W*5/8)) $Y; sleep 4
tapText "பொன்னியின்" || true; sleep 25; adb exec-out screencap -p > app-screenshot-reader.png
tapText "🔊" || true; sleep 6; adb exec-out screencap -p > app-screenshot-tts.png
# share + download from the Today card
adb shell input tap $((W*1/8)) $Y; sleep 3
adb shell input swipe $((W/2)) $((H*70/100)) $((W/2)) $((H*30/100)) 400; sleep 2
tapText "பதிவிறக்கு" || true; sleep 3; adb exec-out screencap -p > app-screenshot-download.png
adb shell ls /sdcard/Pictures/Amma/ || true
tapText "WhatsApp" || true; sleep 4; adb exec-out screencap -p > app-screenshot-share.png
adb shell input keyevent KEYCODE_BACK; sleep 2
adb shell am broadcast -a io.github.santh0sh.amma.MORNING -n io.github.santh0sh.amma/io.github.santh0sh.amma.AlarmReceiver; sleep 3
adb shell cmd statusbar expand-notifications; sleep 3; adb exec-out screencap -p > app-screenshot-notification.png
adb logcat -d > logcat.txt
grep -E "tts|TextToSpeech|python.stdout|python.stderr|AndroidRuntime" logcat.txt | tail -80
exit 0
