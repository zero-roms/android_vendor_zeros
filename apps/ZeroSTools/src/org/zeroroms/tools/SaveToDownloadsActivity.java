/*
 * SPDX-License-Identifier: Apache-2.0
 */

package org.zeroroms.tools;

import android.app.Activity;
import android.content.ClipData;
import android.content.ContentResolver;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.util.Log;
import android.widget.Toast;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * "Save to Downloads" in the share sheet: copies whatever is shared (files, or text) into the
 * public Downloads folder, so it can be attached anywhere later. Used for bug reports from
 * Android's own bug report notification, and for any other file.
 *
 * <p>Only content URIs from other apps are accepted. Plain file paths and this app's own
 * provider are refused, so no app can use this screen to copy ZeroS tools' private files out.
 */
public class SaveToDownloadsActivity extends Activity {

    private static final String TAG = "ZeroSSaveToDownloads";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Intent intent = getIntent();
        List<Uri> uris = sharedUris(intent);
        CharSequence text = intent.getCharSequenceExtra(Intent.EXTRA_TEXT);
        if (uris.isEmpty() && text == null) {
            finish();
            return;
        }
        String type = intent.getType();
        new Thread(() -> {
            int saved = 0;
            int failed = 0;
            if (uris.isEmpty()) {
                String name = "Shared text "
                        + new SimpleDateFormat("yyyy-MM-dd HH.mm.ss", Locale.ROOT)
                                .format(new Date()) + ".txt";
                try (InputStream in = new ByteArrayInputStream(
                        text.toString().getBytes(StandardCharsets.UTF_8))) {
                    Downloads.save(this, in, name, "text/plain");
                    saved++;
                } catch (Exception e) {
                    Log.e(TAG, "Could not save shared text", e);
                    failed++;
                }
            }
            for (Uri uri : uris) {
                if (!isAllowed(uri)) {
                    Log.w(TAG, "Refusing to save " + uri.getScheme() + "://" + uri.getAuthority());
                    failed++;
                    continue;
                }
                ContentResolver resolver = getContentResolver();
                String name = displayName(uri);
                String uriType = resolver.getType(uri);
                try (InputStream in = resolver.openInputStream(uri)) {
                    if (in == null) {
                        throw new java.io.FileNotFoundException(String.valueOf(uri));
                    }
                    Downloads.save(this, in, name, uriType != null ? uriType : type);
                    saved++;
                } catch (Exception e) {
                    Log.e(TAG, "Could not save a shared file", e);
                    failed++;
                }
            }
            final int savedCount = saved;
            final int failedCount = failed;
            runOnUiThread(() -> {
                String message = failedCount == 0
                        ? getResources().getQuantityString(R.plurals.saved_to_downloads,
                                savedCount, savedCount)
                        : getString(R.string.save_to_downloads_failed);
                Toast.makeText(getApplicationContext(), message, Toast.LENGTH_LONG).show();
                finish();
            });
        }, "SaveToDownloads").start();
    }

    private static List<Uri> sharedUris(Intent intent) {
        Set<Uri> uris = new LinkedHashSet<>();
        if (Intent.ACTION_SEND.equals(intent.getAction())) {
            Uri uri = intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri.class);
            if (uri != null) {
                uris.add(uri);
            }
        } else if (Intent.ACTION_SEND_MULTIPLE.equals(intent.getAction())) {
            ArrayList<Uri> list = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri.class);
            if (list != null) {
                uris.addAll(list);
            }
        }
        ClipData clip = intent.getClipData();
        if (uris.isEmpty() && clip != null) {
            for (int i = 0; i < clip.getItemCount(); i++) {
                Uri uri = clip.getItemAt(i).getUri();
                if (uri != null) {
                    uris.add(uri);
                }
            }
        }
        uris.remove(null);
        return new ArrayList<>(uris);
    }

    private static boolean isAllowed(Uri uri) {
        return ContentResolver.SCHEME_CONTENT.equals(uri.getScheme())
                && !ReportFileProvider.AUTHORITY.equals(uri.getAuthority());
    }

    private String displayName(Uri uri) {
        try (Cursor cursor = getContentResolver().query(uri,
                new String[] {OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst() && !cursor.isNull(0)) {
                return cursor.getString(0);
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "No display name for a shared file", e);
        }
        String last = uri.getLastPathSegment();
        return last != null ? last : "Shared file";
    }
}
