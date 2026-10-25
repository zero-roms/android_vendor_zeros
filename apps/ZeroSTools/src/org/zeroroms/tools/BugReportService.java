/*
 * SPDX-License-Identifier: Apache-2.0
 */

package org.zeroroms.tools;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.BugreportManager;
import android.os.BugreportParams;
import android.os.IBinder;
import android.os.ParcelFileDescriptor;
import android.os.SystemClock;
import android.util.Log;

import java.io.IOException;

/**
 * Collects a bug report with Android's BugreportManager, which ZeroS tools may use because it
 * holds DUMP and is on the system's bug report allowlist (sysconfig_org.zeroroms.tools.xml).
 * Android asks the user for consent before it hands the report over. The report is written to
 * this app's private storage only; BugReportActivity then lets the user send, save, share or
 * delete it.
 *
 * <p>Runs as a foreground service while the report is collected (a minute or two), so leaving
 * the screen does not stop it. No screenshot is taken.
 */
public class BugReportService extends Service {

    static final String ACTION_CAPTURE = "org.zeroroms.tools.action.CAPTURE_BUG_REPORT";

    private static final String TAG = "ZeroSBugReport";
    private static final String CHANNEL_PROGRESS = "bug_report_progress";
    private static final String CHANNEL_READY = "bug_report_ready";
    private static final int NOTIFICATION_PROGRESS = 1;
    private static final int NOTIFICATION_READY = 2;

    private BugReports mReports;
    private Notification.Builder mProgressNotification;
    private long mLastProgressUpdate;

    @Override
    public void onCreate() {
        super.onCreate();
        mReports = BugReports.get(this);
        createChannels(this);
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null || !ACTION_CAPTURE.equals(intent.getAction())) {
            stopSelf();
            return START_NOT_STICKY;
        }
        mProgressNotification = new Notification.Builder(this, CHANNEL_PROGRESS)
                .setSmallIcon(R.drawable.ic_bug_report)
                .setContentTitle(getString(R.string.bug_report_collecting_notification))
                .setProgress(100, 0, true)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setContentIntent(openReportIntent(this));
        startForeground(NOTIFICATION_PROGRESS, mProgressNotification.build(),
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        if (mReports.status() != BugReports.Status.CAPTURING) {
            getSystemService(NotificationManager.class).cancel(NOTIFICATION_READY);
            startCapture();
        }
        return START_NOT_STICKY;
    }

    private void startCapture() {
        mReports.setCapturing();
        mReports.ensureDir();
        // startBugreport can block for several seconds, so it is called off the main thread;
        // its callbacks arrive on the main thread
        new Thread(() -> {
            try {
                ParcelFileDescriptor fd = ParcelFileDescriptor.open(mReports.capturingFile(),
                        ParcelFileDescriptor.MODE_WRITE_ONLY | ParcelFileDescriptor.MODE_CREATE
                                | ParcelFileDescriptor.MODE_TRUNCATE
                                | ParcelFileDescriptor.MODE_APPEND);
                getSystemService(BugreportManager.class).startBugreport(fd, null,
                        new BugreportParams(BugreportParams.BUGREPORT_MODE_INTERACTIVE),
                        getMainExecutor(), mCallback);
            } catch (IOException | RuntimeException e) {
                // A SecurityException means DUMP or the bug report allowlist is missing
                Log.e(TAG, "Could not start the bug report", e);
                getMainExecutor().execute(() -> finish(false,
                        BugreportManager.BugreportCallback.BUGREPORT_ERROR_RUNTIME));
            }
        }, "BugReportStart").start();
    }

    private final BugreportManager.BugreportCallback mCallback =
            new BugreportManager.BugreportCallback() {
        @Override
        public void onProgress(float progress) {
            mReports.setProgress((int) progress);
            long now = SystemClock.elapsedRealtime();
            if (now - mLastProgressUpdate > 1000 && mProgressNotification != null) {
                mLastProgressUpdate = now;
                mProgressNotification.setProgress(100, (int) progress, false);
                getSystemService(NotificationManager.class)
                        .notify(NOTIFICATION_PROGRESS, mProgressNotification.build());
            }
        }

        @Override
        public void onError(int errorCode) {
            Log.w(TAG, "Bug report failed: " + errorCode);
            finish(false, errorCode);
        }

        @Override
        public void onFinished() {
            finish(true, 0);
        }
    };

    private void finish(boolean collected, int errorCode) {
        boolean ready = collected && mReports.setReady();
        if (!collected) {
            mReports.setFailed(errorCode);
        }
        stopForeground(STOP_FOREGROUND_REMOVE);
        // Without the screen open, a notification tells the user the report is ready
        if (ready && !mReports.hasListeners()) {
            Notification notification = new Notification.Builder(this, CHANNEL_READY)
                    .setSmallIcon(R.drawable.ic_bug_report)
                    .setContentTitle(getString(R.string.bug_report_ready_notification))
                    .setContentText(getString(R.string.bug_report_ready_notification_text))
                    .setAutoCancel(true)
                    .setContentIntent(openReportIntent(this))
                    .build();
            getSystemService(NotificationManager.class).notify(NOTIFICATION_READY, notification);
        }
        stopSelf();
    }

    static PendingIntent openReportIntent(Context context) {
        Intent intent = new Intent(context, BugReportActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        return PendingIntent.getActivity(context, 0, intent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    private static void createChannels(Context context) {
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel(CHANNEL_PROGRESS,
                context.getString(R.string.bug_report_channel_progress),
                NotificationManager.IMPORTANCE_LOW));
        manager.createNotificationChannel(new NotificationChannel(CHANNEL_READY,
                context.getString(R.string.bug_report_channel_ready),
                NotificationManager.IMPORTANCE_DEFAULT));
    }
}
