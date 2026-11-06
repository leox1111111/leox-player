package pl.leox.media;

import android.content.Context;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.net.Uri;
import android.provider.OpenableColumns;

import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

/** Pliki wybrane w Androidzie (galeria, menedzer plikow) - kopiowanie i zmniejszanie zdjec. */
public class LeoxFiles {

    /** Nazwa pliku wybranego przez uzytkownika (albo pusty tekst). */
    public static String displayName(Context ctx, Uri uri) {
        Cursor c = null;
        try {
            c = ctx.getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME},
                    null, null, null);
            if (c != null && c.moveToFirst()) {
                String n = c.getString(0);
                return n == null ? "" : n;
            }
        } catch (Exception e) {
        } finally {
            if (c != null) c.close();
        }
        return "";
    }

    /** Kopiuje plik z adresu content:// do zwyklego pliku; zwraca liczbe bajtow albo -1. */
    public static long copyUri(Context ctx, Uri uri, String dest) {
        InputStream in = null;
        OutputStream out = null;
        try {
            in = ctx.getContentResolver().openInputStream(uri);
            if (in == null) return -1;
            out = new FileOutputStream(dest);
            byte[] buf = new byte[65536];
            long total = 0;
            int n;
            while ((n = in.read(buf)) > 0) {
                out.write(buf, 0, n);
                total += n;
            }
            return total;
        } catch (Exception e) {
            return -1;
        } finally {
            try { if (in != null) in.close(); } catch (Exception e) { }
            try { if (out != null) out.close(); } catch (Exception e) { }
        }
    }

    /** Zdjecie -> kwadratowy JPEG max x max (obrot wg EXIF, przyciecie do srodka). */
    public static boolean squareJpeg(String src, String dest, int max) {
        try {
            BitmapFactory.Options o = new BitmapFactory.Options();
            o.inJustDecodeBounds = true;
            BitmapFactory.decodeFile(src, o);
            if (o.outWidth <= 0 || o.outHeight <= 0) return false;
            int s = 1;
            while (Math.min(o.outWidth, o.outHeight) / (s * 2) >= max) s *= 2;
            BitmapFactory.Options o2 = new BitmapFactory.Options();
            o2.inSampleSize = s;
            Bitmap b = BitmapFactory.decodeFile(src, o2);
            if (b == null) return false;
            int rot = 0;
            try {
                int or = new ExifInterface(src).getAttributeInt(ExifInterface.TAG_ORIENTATION,
                        ExifInterface.ORIENTATION_NORMAL);
                if (or == ExifInterface.ORIENTATION_ROTATE_90) rot = 90;
                else if (or == ExifInterface.ORIENTATION_ROTATE_180) rot = 180;
                else if (or == ExifInterface.ORIENTATION_ROTATE_270) rot = 270;
            } catch (Exception e) { }
            int side = Math.min(b.getWidth(), b.getHeight());
            int x = (b.getWidth() - side) / 2;
            int y = (b.getHeight() - side) / 2;
            float k = Math.min(1f, (float) max / side);
            Matrix m = new Matrix();
            m.postScale(k, k);
            if (rot != 0) m.postRotate(rot);
            Bitmap sq = Bitmap.createBitmap(b, x, y, side, side, m, true);
            FileOutputStream out = new FileOutputStream(dest);
            try {
                sq.compress(Bitmap.CompressFormat.JPEG, 85, out);
            } finally {
                out.close();
            }
            return true;
        } catch (Throwable t) {
            return false;
        }
    }
}
