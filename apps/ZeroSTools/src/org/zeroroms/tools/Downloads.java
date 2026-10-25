/*
 * SPDX-License-Identifier: Apache-2.0
 */

package org.zeroroms.tools;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.net.Uri;
import android.provider.MediaStore;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/** Saves a stream as a new file in the public Downloads folder. Needs no storage permission. */
final class Downloads {

    private Downloads() {
    }

    /** Blocks; call it off the main thread. */
    static Uri save(Context context, InputStream in, String displayName, String mimeType)
            throws IOException {
        ContentResolver resolver = context.getContentResolver();
        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, safeName(displayName));
        values.put(MediaStore.Downloads.MIME_TYPE, storableType(mimeType, displayName));
        values.put(MediaStore.Downloads.IS_PENDING, 1);
        Uri uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
        if (uri == null) {
            throw new IOException("could not create the file in Downloads");
        }
        try (OutputStream out = resolver.openOutputStream(uri)) {
            if (out == null) {
                throw new IOException("could not open the file in Downloads");
            }
            byte[] buffer = new byte[64 * 1024];
            int read;
            while ((read = in.read(buffer)) != -1) {
                out.write(buffer, 0, read);
            }
        } catch (IOException | RuntimeException e) {
            resolver.delete(uri, null, null);
            throw e;
        }
        values.clear();
        values.put(MediaStore.Downloads.IS_PENDING, 0);
        resolver.update(uri, values, null, null);
        return uri;
    }

    private static String safeName(String name) {
        if (name == null) {
            return "Shared file";
        }
        String cleaned = name.replaceAll("[/\\\\:*?\"<>|\\p{Cntrl}]", "_").trim();
        return cleaned.isEmpty() ? "Shared file" : cleaned;
    }

    /**
     * Android's own bug report type has no file extension mapping, which would make the media
     * store rename the file; bug reports are zip files.
     */
    private static String storableType(String mimeType, String name) {
        if (mimeType == null || mimeType.isEmpty() || mimeType.contains("*")) {
            return name != null && name.endsWith(".zip") ? "application/zip"
                    : "application/octet-stream";
        }
        if (mimeType.equals("application/vnd.android.bugreport")) {
            return "application/zip";
        }
        return mimeType;
    }
}
