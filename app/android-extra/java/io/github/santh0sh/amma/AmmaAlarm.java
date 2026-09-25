package io.github.santh0sh.amma;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;

import java.util.Calendar;

/** Schedules the daily good-morning notification in a 6:30-7:00 AM window (inexact, no special permission). */
public class AmmaAlarm {
    public static final String ACTION = "io.github.santh0sh.amma.MORNING";

    public static void schedule(Context ctx) {
        Calendar c = Calendar.getInstance();
        c.set(Calendar.HOUR_OF_DAY, 6);
        c.set(Calendar.MINUTE, 30);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        if (c.getTimeInMillis() <= System.currentTimeMillis() + 60_000L) {
            c.add(Calendar.DAY_OF_YEAR, 1);
        }
        Intent i = new Intent(ctx, AlarmReceiver.class).setAction(ACTION);
        PendingIntent pi = PendingIntent.getBroadcast(ctx, 630, i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        am.setWindow(AlarmManager.RTC_WAKEUP, c.getTimeInMillis(), 30L * 60_000L, pi);
    }
}
