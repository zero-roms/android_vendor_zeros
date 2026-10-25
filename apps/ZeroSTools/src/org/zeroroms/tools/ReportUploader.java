/*
 * SPDX-License-Identifier: Apache-2.0
 */

package org.zeroroms.tools;

import android.content.Context;
import android.os.Build;
import android.os.SystemProperties;
import android.util.Base64;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * Sends a bug report to the ZeroS reports server (vendor/zeros/server/reports) over HTTPS. The
 * server stores it privately for 30 days and answers with a report ID.
 */
final class ReportUploader {

    /** The server's limit (Cloud Run accepts at most 32 MiB per request). */
    static final long MAX_BYTES = 30L * 1024 * 1024;

    /** The server answered with an error; {@link #code} is its HTTP status. */
    static final class ServerException extends IOException {
        private static final long serialVersionUID = 1L;

        final int code;

        ServerException(int code) {
            super("reports server answered " + code);
            this.code = code;
        }
    }

    private ReportUploader() {
    }

    /** Uploads the zip and returns the report ID. Blocks; call it off the main thread. */
    static String upload(Context context, File zip, String description) throws IOException {
        String server = context.getString(R.string.reports_server_url);
        if (!server.startsWith("https://")) {
            throw new IOException("the reports server address must use HTTPS");
        }
        HttpURLConnection connection =
                (HttpURLConnection) new URL(server + "/v1/bugreports").openConnection();
        try {
            connection.setConnectTimeout(15_000);
            connection.setReadTimeout(120_000);
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);
            connection.setFixedLengthStreamingMode(zip.length());
            connection.setRequestProperty("Content-Type", "application/zip");
            connection.setRequestProperty("X-ZeroS-Version",
                    SystemProperties.get("ro.zeros.version", "unknown"));
            connection.setRequestProperty("X-ZeroS-Device", Build.DEVICE);
            connection.setRequestProperty("X-ZeroS-Description", Base64.encodeToString(
                    description.getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP));
            try (InputStream in = new FileInputStream(zip);
                    OutputStream out = connection.getOutputStream()) {
                byte[] buffer = new byte[64 * 1024];
                int read;
                while ((read = in.read(buffer)) != -1) {
                    out.write(buffer, 0, read);
                }
            }
            int code = connection.getResponseCode();
            if (code != HttpURLConnection.HTTP_CREATED) {
                throw new ServerException(code);
            }
            try (InputStream in = connection.getInputStream()) {
                return new JSONObject(readAll(in)).getString("id");
            }
        } catch (JSONException e) {
            throw new IOException("unexpected answer from the reports server", e);
        } finally {
            connection.disconnect();
        }
    }

    private static String readAll(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[4096];
        int read;
        while ((read = in.read(buffer)) != -1 && out.size() < 64 * 1024) {
            out.write(buffer, 0, read);
        }
        return out.toString(StandardCharsets.UTF_8.name());
    }
}
