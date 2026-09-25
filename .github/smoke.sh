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
adb shell input tap $((W*1/8)) $Y; sleep 3
adb shell am broadcast -a io.github.santh0sh.amma.MORNING -n io.github.santh0sh.amma/io.github.santh0sh.amma.AlarmReceiver; sleep 3
adb shell cmd statusbar expand-notifications; sleep 3; adb exec-out screencap -p > app-screenshot-notification.png
adb logcat -d > logcat.txt
grep -E "python.stdout|python.stderr|AndroidRuntime" logcat.txt | tail -80
exit 0
