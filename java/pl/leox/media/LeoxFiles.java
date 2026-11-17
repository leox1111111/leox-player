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
    /** Zdjecie -> JPEG (dluzszy bok max px, proporcje zachowane, obrot wg EXIF) - na tapete. */
    public static boolean scaledJpeg(String src, String dest, int max) {
        try {
            BitmapFactory.Options o = new BitmapFactory.Options();
            o.inJustDecodeBounds = true;
            BitmapFactory.decodeFile(src, o);
            if (o.outWidth <= 0 || o.outHeight <= 0) return false;
            int s = 1;
            while (Math.max(o.outWidth, o.outHeight) / (s * 2) >= max) s *= 2;
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
            float k = Math.min(1f, (float) max / Math.max(b.getWidth(), b.getHeight()));
            Matrix m = new Matrix();
            m.postScale(k, k);
            if (rot != 0) m.postRotate(rot);
            Bitmap out = Bitmap.createBitmap(b, 0, 0, b.getWidth(), b.getHeight(), m, true);
            FileOutputStream f = new FileOutputStream(dest);
            try {
                out.compress(Bitmap.CompressFormat.JPEG, 85, f);
            } finally {
                f.close();
            }
            return true;
        } catch (Throwable t) {
            return false;
        }
    }

    /** Najczestsze kolory zdjecia (ARGB), od najczestszego; podobne kolory sa laczone. */
    public static int[] palette(String src, int k) {
        try {
            BitmapFactory.Options o = new BitmapFactory.Options();
            o.inJustDecodeBounds = true;
            BitmapFactory.decodeFile(src, o);
            int s = 1;
            while (Math.max(o.outWidth, o.outHeight) / (s * 2) >= 96) s *= 2;
            BitmapFactory.Options o2 = new BitmapFactory.Options();
            o2.inSampleSize = s;
            Bitmap b = BitmapFactory.decodeFile(src, o2);
            if (b == null) return new int[0];
            int[] count = new int[4096];
            long[] rs = new long[4096], gs = new long[4096], bs = new long[4096];
            for (int y = 0; y < b.getHeight(); y++) {
                for (int x = 0; x < b.getWidth(); x++) {
                    int c = b.getPixel(x, y);
                    int r = (c >> 16) & 255, g = (c >> 8) & 255, bl = c & 255;
                    int key = ((r >> 4) << 8) | ((g >> 4) << 4) | (bl >> 4);
                    count[key]++;
                    rs[key] += r;
                    gs[key] += g;
                    bs[key] += bl;
                }
            }
            int[] out = new int[k];
            int n = 0;
            boolean[] used = new boolean[4096];
            while (n < k) {
                int best = -1;
                for (int i = 0; i < 4096; i++) {
                    if (!used[i] && count[i] > 0 && (best < 0 || count[i] > count[best])) best = i;
                }
                if (best < 0) break;
                used[best] = true;
                int r = (int) (rs[best] / count[best]);
                int g = (int) (gs[best] / count[best]);
                int bl = (int) (bs[best] / count[best]);
                boolean close = false;
                for (int j = 0; j < n; j++) {
                    int c = out[j];
                    int dr = ((c >> 16) & 255) - r, dg = ((c >> 8) & 255) - g, db = (c & 255) - bl;
                    if (dr * dr + dg * dg + db * db < 40 * 40) { close = true; break; }
                }
                if (!close) out[n++] = 0xff000000 | (r << 16) | (g << 8) | bl;
            }
            int[] res = new int[n];
            System.arraycopy(out, 0, res, 0, n);
            return res;
        } catch (Throwable t) {
            return new int[0];
        }
    }
}
