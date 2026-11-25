package com.dd.shchitok2;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;

import java.io.File;
import java.io.FileNotFoundException;

/** Отдаёт системе или другому приложению только разрешённые файлы и только для чтения. */
public class ApkProvider extends ContentProvider {
    static final String AUTH = "com.dd.shchitok2.files";

    private File file(Uri uri) throws FileNotFoundException {
        String n = uri != null ? uri.getLastPathSegment() : null;
        if (!"Shchitok2.apk".equals(n) && !"update.apk".equals(n) && !"shchitok2-changes.json".equals(n)) {
            throw new FileNotFoundException("unknown file");
        }
        return new File(getContext().getCacheDir(), n);
    }

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!"r".equals(mode)) throw new FileNotFoundException("read only");
        return ParcelFileDescriptor.open(file(uri), 0x10000000); // MODE_READ_ONLY
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] args, String order) {
        String[] cols = projection != null ? projection : new String[]{"_display_name", "_size"};
        MatrixCursor c = new MatrixCursor(cols);
        Object[] row = new Object[cols.length];
        try {
            File f = file(uri);
            for (int i = 0; i < cols.length; i++) {
                if ("_display_name".equals(cols[i])) row[i] = f.getName();
                else if ("_size".equals(cols[i])) row[i] = Long.valueOf(f.length());
            }
            c.addRow(row);
        } catch (FileNotFoundException ignored) {}
        return c;
    }

    @Override
    public String getType(Uri uri) {
        String n = uri != null ? uri.getLastPathSegment() : null;
        return "shchitok2-changes.json".equals(n) ? "application/json" : "application/vnd.android.package-archive";
    }

    @Override
    public Uri insert(Uri uri, ContentValues v) {
        return null;
    }

    @Override
    public int delete(Uri uri, String s, String[] a) {
        return 0;
    }

    @Override
    public int update(Uri uri, ContentValues v, String s, String[] a) {
        return 0;
    }
}
