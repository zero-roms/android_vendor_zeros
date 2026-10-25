/*
 * SPDX-License-Identifier: Apache-2.0
 */

package org.zeroroms.tools;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;

import java.io.File;
import java.io.FileNotFoundException;

/**
 * Gives the app the user picks in "Share" read access to the waiting bug report, and nothing
 * else. Not exported: access comes only from the URI permission that the share intent grants.
 * The last path segment is just the file name the receiving app shows.
 */
public class ReportFileProvider extends ContentProvider {

    static final String AUTHORITY = "org.zeroroms.tools.reports";

    static Uri uriFor(String displayName) {
        return new Uri.Builder().scheme("content").authority(AUTHORITY)
                .appendPath(displayName).build();
    }

    @Override
    public boolean onCreate() {
        return true;
    }

    private File reportFile() {
        return BugReports.get(getContext()).readyFile();
    }

    private static String displayName(Uri uri) {
        String name = uri.getLastPathSegment();
        return name != null && name.matches("[A-Za-z0-9._-]{1,100}") ? name : "bugreport.zip";
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs,
            String sortOrder) {
        String[] columns = {OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE};
        MatrixCursor cursor = new MatrixCursor(columns, 1);
        File file = reportFile();
        if (file.exists()) {
            cursor.addRow(new Object[] {displayName(uri), file.length()});
        }
        return cursor;
    }

    @Override
    public String getType(Uri uri) {
        return "application/zip";
    }

    @Override
    public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!"r".equals(mode)) {
            throw new SecurityException("read only");
        }
        File file = reportFile();
        if (!file.exists()) {
            throw new FileNotFoundException("no bug report");
        }
        return ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        throw new UnsupportedOperationException();
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        throw new UnsupportedOperationException();
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        throw new UnsupportedOperationException();
    }
}
