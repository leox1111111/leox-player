package pl.leox.media;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.drawable.Icon;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.MediaMetadata;
import android.media.MediaMetadataRetriever;
import android.media.MediaPlayer;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;

import java.io.File;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Panel odtwarzacza w powiadomieniu, przyciski s\u0142uchawek/Bluetooth,
 * fokus audio i koniec utworu. Wszystkie zdarzenia trafiaj\u0105 do kolejki,
 * kt\u00f3r\u0105 us\u0142uga w Pythonie odczytuje przez poll().
 */
public class LeoxMedia {
    public static final int NOTIF_ID = 1;              // ten sam numer co powiadomienie us\u0142ugi p4a
    static final String CH = "leox_media";
    static final String A_PREV = "pl.leox.media.PREV";
    static final String A_TOGGLE = "pl.leox.media.TOGGLE";
    static final String A_NEXT = "pl.leox.media.NEXT";
    static final String A_CLOSE = "pl.leox.media.CLOSE";

    static final ConcurrentLinkedQueue<String> Q = new ConcurrentLinkedQueue<String>();
    static Context ctx;
    static MediaSession session;
    static AudioManager am;
    static AudioManager.OnAudioFocusChangeListener focusListener;
    static boolean hasFocus = false;
    static String metaKey = "";
    static Bitmap art = null;

    public static String poll() {
        return Q.poll();
    }

    public static int id(Object o) {
        return System.identityHashCode(o);
    }

    public static void init(Context c) {
        if (session != null) return;
        ctx = c;
        session = new MediaSession(c, "LeoxPlayer");
        session.setCallback(new MediaSession.Callback() {
            @Override public void onPlay() { Q.add("play"); }
            @Override public void onPause() { Q.add("pause"); }
            @Override public void onSkipToNext() { Q.add("next"); }
            @Override public void onSkipToPrevious() { Q.add("prev"); }
            @Override public void onStop() { Q.add("quit"); }
            @Override public void onSeekTo(long pos) { Q.add("seek:" + pos); }
        }, new Handler(Looper.getMainLooper()));
        session.setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS
                | MediaSession.FLAG_HANDLES_TRANSPORT_CONTROLS);
        PendingIntent open = openApp();
        if (open != null) session.setSessionActivity(open);

        IntentFilter f = new IntentFilter();
        f.addAction(A_PREV);
        f.addAction(A_TOGGLE);
        f.addAction(A_NEXT);
        f.addAction(A_CLOSE);
        f.addAction(AudioManager.ACTION_AUDIO_BECOMING_NOISY);
        BroadcastReceiver r = new BroadcastReceiver() {
            @Override public void onReceive(Context cx, Intent i) {
                String a = i.getAction();
                if (A_PREV.equals(a)) Q.add("prev");
                else if (A_TOGGLE.equals(a)) Q.add("toggle");
                else if (A_NEXT.equals(a)) Q.add("next");
                else if (A_CLOSE.equals(a)) Q.add("quit");
                else if (AudioManager.ACTION_AUDIO_BECOMING_NOISY.equals(a)) Q.add("pause");
            }
        };
        if (Build.VERSION.SDK_INT >= 33) {
            c.registerReceiver(r, f, 4);               // Context.RECEIVER_NOT_EXPORTED
        } else {
            c.registerReceiver(r, f);
        }

        am = (AudioManager) c.getSystemService(Context.AUDIO_SERVICE);
        focusListener = new AudioManager.OnAudioFocusChangeListener() {
            @Override public void onAudioFocusChange(int change) {
                if (change == AudioManager.AUDIOFOCUS_LOSS) { hasFocus = false; Q.add("focus_loss"); }
                else if (change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT) Q.add("focus_pause");
                else if (change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK) Q.add("focus_duck");
                else if (change == AudioManager.AUDIOFOCUS_GAIN) { hasFocus = true; Q.add("focus_gain"); }
            }
        };

        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CH, "Odtwarzanie",
                    NotificationManager.IMPORTANCE_LOW);
            ch.setShowBadge(false);
            ch.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            nm().createNotificationChannel(ch);
        }
    }

    static NotificationManager nm() {
        return (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
    }

    static PendingIntent openApp() {
        Intent launch = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName());
        if (launch == null) return null;
        return PendingIntent.getActivity(ctx, 10, launch,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    static PendingIntent action(String a, int code) {
        Intent i = new Intent(a);
        i.setPackage(ctx.getPackageName());
        return PendingIntent.getBroadcast(ctx, code, i,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    /** Odtwarzacz zg\u0142asza koniec utworu i b\u0142\u0119dy do kolejki (done:ID, err:ID). */
    public static void watch(final MediaPlayer mp) {
        final int mid = System.identityHashCode(mp);
        mp.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
            @Override public void onCompletion(MediaPlayer m) { Q.add("done:" + mid); }
        });
        mp.setOnErrorListener(new MediaPlayer.OnErrorListener() {
            @Override public boolean onError(MediaPlayer m, int what, int extra) {
                Q.add("err:" + mid + ":" + what + "/" + extra);
                return true;
            }
        });
        if (Build.VERSION.SDK_INT >= 21) {
            mp.setAudioAttributes(new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build());
        }
    }

    @SuppressWarnings("deprecation")
    public static boolean requestFocus() {
        if (am == null) return true;
        if (hasFocus) return true;
        int r = am.requestAudioFocus(focusListener, AudioManager.STREAM_MUSIC,
                AudioManager.AUDIOFOCUS_GAIN);
        hasFocus = r == AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
        return hasFocus;
    }

    @SuppressWarnings("deprecation")
    public static void abandonFocus() {
        if (am != null && hasFocus) am.abandonAudioFocus(focusListener);
        hasFocus = false;
    }

    static Bitmap loadArt(String artPath, String srcPath) {
        try {
            if (artPath != null && artPath.length() > 0 && new File(artPath).exists()) {
                BitmapFactory.Options o = new BitmapFactory.Options();
                o.inJustDecodeBounds = true;
                BitmapFactory.decodeFile(artPath, o);
                int s = 1;
                while (Math.max(o.outWidth, o.outHeight) / s > 768) s *= 2;
                BitmapFactory.Options o2 = new BitmapFactory.Options();
                o2.inSampleSize = s;
                return BitmapFactory.decodeFile(artPath, o2);
            }
            if (srcPath != null && srcPath.startsWith("/") && new File(srcPath).exists()) {
                MediaMetadataRetriever mr = new MediaMetadataRetriever();
                try {
                    mr.setDataSource(srcPath);
                    byte[] pic = mr.getEmbeddedPicture();
                    if (pic != null) {
                        BitmapFactory.Options o = new BitmapFactory.Options();
                        o.inJustDecodeBounds = true;
                        BitmapFactory.decodeByteArray(pic, 0, pic.length, o);
                        int s = 1;
                        while (Math.max(o.outWidth, o.outHeight) / s > 768) s *= 2;
                        BitmapFactory.Options o2 = new BitmapFactory.Options();
                        o2.inSampleSize = s;
                        return BitmapFactory.decodeByteArray(pic, 0, pic.length, o2);
                    }
                } finally {
                    try { mr.release(); } catch (Exception e) { }
                }
            }
        } catch (Throwable t) { }
        return null;
    }

    /** Od\u015bwie\u017ca sesj\u0119 multimedi\u00f3w i powiadomienie z przyciskami. */
    public static void update(String title, String artist, long durMs, long posMs,
                              boolean playing, float speed, String artPath, String srcPath) {
        if (session == null) return;
        if (title == null) title = "";
        if (artist == null) artist = "";
        String key = title + "|" + artist + "|" + durMs + "|" + artPath + "|" + srcPath;
        if (!key.equals(metaKey)) {
            metaKey = key;
            art = loadArt(artPath, srcPath);
            MediaMetadata.Builder mb = new MediaMetadata.Builder()
                    .putString(MediaMetadata.METADATA_KEY_TITLE, title)
                    .putString(MediaMetadata.METADATA_KEY_ARTIST, artist)
                    .putLong(MediaMetadata.METADATA_KEY_DURATION, durMs > 0 ? durMs : -1);
            if (art != null) mb.putBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART, art);
            session.setMetadata(mb.build());
        }
        long acts = PlaybackState.ACTION_PLAY | PlaybackState.ACTION_PAUSE
                | PlaybackState.ACTION_PLAY_PAUSE | PlaybackState.ACTION_SKIP_TO_NEXT
                | PlaybackState.ACTION_SKIP_TO_PREVIOUS | PlaybackState.ACTION_STOP;
        if (durMs > 0) acts |= PlaybackState.ACTION_SEEK_TO;
        session.setPlaybackState(new PlaybackState.Builder()
                .setActions(acts)
                .setState(playing ? PlaybackState.STATE_PLAYING : PlaybackState.STATE_PAUSED,
                        posMs, playing ? speed : 0f)
                .build());
        if (!session.isActive()) session.setActive(true);

        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(ctx, CH) : new Notification.Builder(ctx);
        b.setSmallIcon(android.R.drawable.ic_media_play)
                .setContentTitle(title)
                .setContentText(artist)
                .setShowWhen(false)
                .setOngoing(true)
                .setVisibility(Notification.VISIBILITY_PUBLIC)
                .setDeleteIntent(action(A_CLOSE, 24));
        PendingIntent open = openApp();
        if (open != null) b.setContentIntent(open);
        if (art != null) b.setLargeIcon(art);
        b.addAction(new Notification.Action.Builder(
                Icon.createWithResource(ctx, android.R.drawable.ic_media_previous),
                "Poprzedni", action(A_PREV, 21)).build());
        b.addAction(new Notification.Action.Builder(
                Icon.createWithResource(ctx, playing ? android.R.drawable.ic_media_pause
                        : android.R.drawable.ic_media_play),
                playing ? "Pauza" : "Graj", action(A_TOGGLE, 22)).build());
        b.addAction(new Notification.Action.Builder(
                Icon.createWithResource(ctx, android.R.drawable.ic_media_next),
                "Nast\u0119pny", action(A_NEXT, 23)).build());
        b.addAction(new Notification.Action.Builder(
                Icon.createWithResource(ctx, android.R.drawable.ic_menu_close_clear_cancel),
                "Zamknij", action(A_CLOSE, 24)).build());
        b.setStyle(new Notification.MediaStyle()
                .setMediaSession(session.getSessionToken())
                .setShowActionsInCompactView(0, 1, 2));
        Notification n = b.build();
        try {
            if (ctx instanceof Service) ((Service) ctx).startForeground(NOTIF_ID, n);
            else nm().notify(NOTIF_ID, n);
        } catch (Throwable t) {
            try { nm().notify(NOTIF_ID, n); } catch (Throwable t2) { }
        }
    }

    /** Usuwa powiadomienie (koniec, zamkni\u0119cie). Us\u0142uga \u017cyje dalej i czeka na polecenia. */
    @SuppressWarnings("deprecation")
    public static void remove() {
        abandonFocus();
        metaKey = "";
        try {
            if (session != null) {
                session.setPlaybackState(new PlaybackState.Builder()
                        .setState(PlaybackState.STATE_STOPPED, 0, 0f).build());
                session.setActive(false);
            }
        } catch (Throwable t) { }
        try {
            if (ctx instanceof Service) ((Service) ctx).stopForeground(true);
        } catch (Throwable t) { }
        try { nm().cancel(NOTIF_ID); } catch (Throwable t) { }
    }
}
