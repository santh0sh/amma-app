package io.github.santh0sh.amma;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** Shows the morning notification, and re-arms the alarm (also after reboot / app update). */
public class AlarmReceiver extends BroadcastReceiver {
    static final String CHANNEL = "morning";

    @Override
    public void onReceive(Context ctx, Intent intent) {
        String a = intent.getAction();
        if (AmmaAlarm.ACTION.equals(a)) {
            showNow(ctx);
        }
        AmmaAlarm.schedule(ctx);
    }

    static String line(Context ctx) {
        String fallback = "காலை வணக்கம்! இன்றைய படம் தயார் 🌅";
        try {
            File f = new File(ctx.getFilesDir(), "notify.json");
            if (!f.exists()) return fallback;
            byte[] b = new byte[(int) f.length()];
            try (FileInputStream in = new FileInputStream(f)) { in.read(b); }
            JSONObject o = new JSONObject(new String(b, StandardCharsets.UTF_8));
            String today = new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
            return o.optString(today, fallback);
        } catch (Exception e) {
            return fallback;
        }
    }

    public static void showNow(Context ctx) {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "காலை வணக்கம்",
                    NotificationManager.IMPORTANCE_HIGH);
            ctx.getSystemService(NotificationManager.class).createNotificationChannel(ch);
        }
        Intent open = new Intent(ctx, org.beeware.android.MainActivity.class)
                .setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                .putExtra("amma.open", "card");
        PendingIntent pi = PendingIntent.getActivity(ctx, 1, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        String text = line(ctx);
        NotificationCompat.Builder nb = new NotificationCompat.Builder(ctx, CHANNEL)
                .setSmallIcon(R.drawable.ic_stat_amma)
                .setContentTitle("காலை வணக்கம் அம்மா 🙏")
                .setContentText(text)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(text))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setContentIntent(pi)
                .setAutoCancel(true);
        try {
            NotificationManagerCompat.from(ctx).notify(630, nb.build());
        } catch (SecurityException e) {
            // notification permission not granted yet; the setup screen asks for it
        }
    }
}
