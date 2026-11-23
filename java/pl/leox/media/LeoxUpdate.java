package pl.leox.media;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageInstaller;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import java.io.FileInputStream;
import java.io.InputStream;
import java.io.OutputStream;

/** Instalacja pobranej aktualizacji (systemowy instalator pakietow). */
public class LeoxUpdate {
    static volatile String status = "";
    static volatile Intent pending;          // okno potwierdzenia, gdy aplikacja byla w tle
    static BroadcastReceiver receiver;

    /** Czy czeka okno potwierdzenia instalacji (pokaz je, gdy aplikacja jest na wierzchu). */
    public static boolean hasPending() {
        return pending != null;
    }

    public static void showPending(Context ctx) {
        Intent i = pending;
        pending = null;
        if (i != null) {
            try { ctx.startActivity(i); } catch (Throwable t) { pending = i; }
        }
    }

    /** Ostatni stan instalacji: "", "ok", "anulowano" albo opis bledu. */
    public static String status() {
        return status;
    }

    /** Czy aplikacja moze instalowac pakiety (Android 8+: "Instaluj nieznane aplikacje"). */
    public static boolean canInstall(Context ctx) {
        if (Build.VERSION.SDK_INT < 26) return true;
        return ctx.getPackageManager().canRequestPackageInstalls();
    }

    /** Otwiera ustawienie "Instaluj nieznane aplikacje" dla tej aplikacji. */
    public static void openInstallSettings(Context ctx) {
        if (Build.VERSION.SDK_INT < 26) return;
        Intent i = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                Uri.parse("package:" + ctx.getPackageName()));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        ctx.startActivity(i);
    }

    /** Wysyla plik APK do instalatora; Android pokaze okno potwierdzenia. Zwraca "" albo blad. */
    public static String install(final Context ctx, String apkPath) {
        return install(ctx, apkPath, true);
    }

    /** silent: Android 12+ instaluje bez pytania, gdy poprzednia wersje zainstalowala ta aplikacja. */
    public static String install(final Context ctx, String apkPath, boolean silent) {
        status = "";
        try {
            final String action = ctx.getPackageName() + ".INSTALL_STATUS";
            if (receiver == null) {
                receiver = new BroadcastReceiver() {
                    @Override public void onReceive(Context c, Intent intent) {
                        int st = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, -999);
                        if (st == PackageInstaller.STATUS_PENDING_USER_ACTION) {
                            Intent confirm = intent.getParcelableExtra(Intent.EXTRA_INTENT);
                            if (confirm != null) {
                                confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                pending = confirm;
                                try { c.startActivity(confirm); pending = null; } catch (Throwable t) { }
                            }
                        } else if (st == PackageInstaller.STATUS_SUCCESS) {
                            status = "ok";
                        } else if (st == PackageInstaller.STATUS_FAILURE_ABORTED) {
                            status = "anulowano";
                        } else {
                            String msg = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE);
                            status = "blad " + st + (msg != null ? ": " + msg : "");
                        }
                    }
                };
                IntentFilter f = new IntentFilter(action);
                if (Build.VERSION.SDK_INT >= 33) {
                    ctx.registerReceiver(receiver, f, 4);       // RECEIVER_NOT_EXPORTED
                } else {
                    ctx.registerReceiver(receiver, f);
                }
            }
            PackageInstaller pi = ctx.getPackageManager().getPackageInstaller();
            PackageInstaller.SessionParams params =
                    new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
            if (silent && Build.VERSION.SDK_INT >= 31) {
                params.setRequireUserAction(2);     // USER_ACTION_NOT_REQUIRED
            }
            int id = pi.createSession(params);
            PackageInstaller.Session s = pi.openSession(id);
            InputStream in = new FileInputStream(apkPath);
            OutputStream out = s.openWrite("leoxplayer", 0, -1);
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            s.fsync(out);
            in.close();
            out.close();
            Intent cb = new Intent(action);
            cb.setPackage(ctx.getPackageName());
            int flags = android.app.PendingIntent.FLAG_UPDATE_CURRENT;
            if (Build.VERSION.SDK_INT >= 31) flags |= 33554432;     // FLAG_MUTABLE
            android.app.PendingIntent p = android.app.PendingIntent.getBroadcast(ctx, id, cb, flags);
            s.commit(p.getIntentSender());
            s.close();
            return "";
        } catch (Throwable t) {
            status = "blad: " + t;
            return String.valueOf(t);
        }
    }
}
