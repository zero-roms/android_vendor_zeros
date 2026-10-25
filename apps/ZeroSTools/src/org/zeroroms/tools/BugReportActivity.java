/*
 * SPDX-License-Identifier: Apache-2.0
 */

package org.zeroroms.tools;

import android.Manifest;
import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.BugreportManager.BugreportCallback;
import android.os.Bundle;
import android.text.format.DateFormat;
import android.util.Log;
import android.view.View;
import android.view.WindowInsets;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Date;

/**
 * The bug report screen. Opened by the Bug report tile, by the power menu's Bug report button
 * (ZeroS tools is Android's bug report handler, see BugReportHandlerReceiver) and by the "ready"
 * notification. It starts collecting a report if none is waiting, lets the user describe the
 * problem meanwhile, and then offers Send to ZeroS, Save to Downloads, Share and Delete.
 */
public class BugReportActivity extends Activity implements BugReports.Listener {

    /** Set by the tile and the power menu: collect a new report unless one is waiting. */
    static final String EXTRA_START = "org.zeroroms.tools.extra.START";

    private static final String TAG = "ZeroSBugReport";
    private static final int REQUEST_NOTIFICATIONS = 1;

    private BugReports mReports;
    private TextView mStatus;
    private ProgressBar mProgress;
    private EditText mDescription;
    private Button mSend;
    private Button mSave;
    private Button mShare;
    private Button mDelete;
    private Button mDone;
    private TextView mResult;
    private boolean mBusy;
    private String mSentId;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.bug_report_activity);
        mReports = BugReports.get(this);

        View root = findViewById(R.id.root);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            Insets bars = insets.getInsets(
                    WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            return WindowInsets.CONSUMED;
        });

        mStatus = findViewById(R.id.status);
        mProgress = findViewById(R.id.progress);
        mDescription = findViewById(R.id.description);
        mSend = findViewById(R.id.send);
        mSave = findViewById(R.id.save);
        mShare = findViewById(R.id.share);
        mDelete = findViewById(R.id.delete);
        mDone = findViewById(R.id.done);
        mResult = findViewById(R.id.result);

        mSend.setOnClickListener(v -> send());
        mSave.setOnClickListener(v -> save());
        mShare.setOnClickListener(v -> share());
        mDelete.setOnClickListener(v -> {
            mReports.discard();
            finish();
        });
        mDone.setOnClickListener(v -> finish());
        findViewById(R.id.privacy_link).setOnClickListener(v -> openPrivacyPolicy());

        if (savedInstanceState != null) {
            mSentId = savedInstanceState.getString("sent_id");
        }
        if (savedInstanceState == null) {
            maybeStart(getIntent());
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        maybeStart(intent);
    }

    private void maybeStart(Intent intent) {
        BugReports.Status status = mReports.status();
        boolean wanted = intent.getBooleanExtra(EXTRA_START, false);
        if (wanted && (status == BugReports.Status.IDLE || status == BugReports.Status.FAILED)) {
            mSentId = null;
            startForegroundService(new Intent(this, BugReportService.class)
                    .setAction(BugReportService.ACTION_CAPTURE));
            if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                // Lets the "ready" notification appear if the user leaves this screen
                requestPermissions(new String[] {Manifest.permission.POST_NOTIFICATIONS},
                        REQUEST_NOTIFICATIONS);
            }
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        outState.putString("sent_id", mSentId);
    }

    @Override
    protected void onStart() {
        super.onStart();
        mReports.addListener(this);
        onBugReportChanged();
    }

    @Override
    protected void onStop() {
        mReports.removeListener(this);
        super.onStop();
    }

    @Override
    public void onBugReportChanged() {
        BugReports.Status status = mReports.status();
        boolean ready = status == BugReports.Status.READY;
        boolean sent = mSentId != null;

        mProgress.setVisibility(status == BugReports.Status.CAPTURING ? View.VISIBLE : View.GONE);
        mProgress.setIndeterminate(mReports.progress() == 0);
        mProgress.setProgress(mReports.progress());

        if (sent) {
            mStatus.setText(R.string.bug_report_status_sent);
        } else if (status == BugReports.Status.CAPTURING) {
            mStatus.setText(R.string.bug_report_status_collecting);
        } else if (ready) {
            mStatus.setText(R.string.bug_report_status_ready);
        } else if (status == BugReports.Status.FAILED) {
            mStatus.setText(failureMessage(mReports.errorCode()));
        } else {
            mStatus.setText(R.string.bug_report_status_none);
        }

        int actions = sent ? View.GONE : View.VISIBLE;
        mDescription.setVisibility(actions);
        findViewById(R.id.description_label).setVisibility(actions);
        findViewById(R.id.contents).setVisibility(actions);
        mSend.setVisibility(actions);
        mSave.setVisibility(actions);
        mShare.setVisibility(actions);
        mDelete.setVisibility(ready && !sent ? View.VISIBLE : View.GONE);
        mDone.setVisibility(sent ? View.VISIBLE : View.GONE);
        mResult.setVisibility(sent ? View.VISIBLE : View.GONE);
        if (sent) {
            mResult.setText(getString(R.string.bug_report_sent, mSentId));
        }

        boolean enabled = ready && !mBusy;
        mSend.setEnabled(enabled);
        mSave.setEnabled(enabled);
        mShare.setEnabled(enabled);
        mDelete.setEnabled(!mBusy);
    }

    private int failureMessage(int errorCode) {
        if (errorCode == BugreportCallback.BUGREPORT_ERROR_USER_DENIED_CONSENT
                || errorCode == BugreportCallback.BUGREPORT_ERROR_USER_CONSENT_TIMED_OUT) {
            return R.string.bug_report_status_denied;
        }
        if (errorCode == BugreportCallback.BUGREPORT_ERROR_ANOTHER_REPORT_IN_PROGRESS) {
            return R.string.bug_report_status_busy;
        }
        return R.string.bug_report_status_failed;
    }

    /** File name for saving and sharing, e.g. bugreport-ginkgo-2026-10-25-1410.zip */
    private String reportName() {
        File file = mReports.readyFile();
        CharSequence time = DateFormat.format("yyyy-MM-dd-HHmm", new Date(file.lastModified()));
        return "bugreport-" + Build.DEVICE + "-" + time + ".zip";
    }

    private void setBusy(boolean busy) {
        mBusy = busy;
        onBugReportChanged();
    }

    private void send() {
        File file = mReports.readyFile();
        if (file.length() > ReportUploader.MAX_BYTES) {
            Toast.makeText(this, R.string.bug_report_too_large, Toast.LENGTH_LONG).show();
            return;
        }
        getSystemService(InputMethodManager.class)
                .hideSoftInputFromWindow(mDescription.getWindowToken(), 0);
        String description = mDescription.getText().toString().trim();
        setBusy(true);
        mStatus.setText(R.string.bug_report_status_sending);
        new Thread(() -> {
            String id = null;
            int message = 0;
            try {
                id = ReportUploader.upload(this, file, description);
            } catch (ReportUploader.ServerException e) {
                Log.w(TAG, "Reports server answered " + e.code);
                message = e.code == 429 ? R.string.bug_report_send_busy
                        : e.code == 413 ? R.string.bug_report_too_large
                        : R.string.bug_report_send_failed;
            } catch (IOException e) {
                Log.w(TAG, "Could not send the bug report", e);
                message = R.string.bug_report_send_failed;
            }
            final String reportId = id;
            final int failure = message;
            runOnUiThread(() -> {
                if (reportId != null) {
                    // Sent: the copy on the phone is no longer needed
                    mSentId = reportId;
                    mReports.discard();
                } else {
                    Toast.makeText(this, failure, Toast.LENGTH_LONG).show();
                }
                setBusy(false);
            });
        }, "BugReportSend").start();
    }

    private void save() {
        File file = mReports.readyFile();
        String name = reportName();
        setBusy(true);
        new Thread(() -> {
            boolean saved;
            try (InputStream in = new FileInputStream(file)) {
                Downloads.save(this, in, name, "application/zip");
                saved = true;
            } catch (IOException | RuntimeException e) {
                Log.e(TAG, "Could not save the bug report", e);
                saved = false;
            }
            final boolean ok = saved;
            runOnUiThread(() -> {
                Toast.makeText(this, ok ? getResources().getQuantityString(
                        R.plurals.saved_to_downloads, 1, 1)
                        : getString(R.string.save_to_downloads_failed),
                        Toast.LENGTH_LONG).show();
                setBusy(false);
            });
        }, "BugReportSave").start();
    }

    private void share() {
        Uri uri = ReportFileProvider.uriFor(reportName());
        Intent send = new Intent(Intent.ACTION_SEND)
                .setType("application/zip")
                .putExtra(Intent.EXTRA_STREAM, uri)
                .putExtra(Intent.EXTRA_SUBJECT, reportName())
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        String description = mDescription.getText().toString().trim();
        if (!description.isEmpty()) {
            send.putExtra(Intent.EXTRA_TEXT, description);
        }
        Intent chooser = Intent.createChooser(send, getString(R.string.bug_report_share))
                .putExtra(Intent.EXTRA_EXCLUDE_COMPONENTS, new ComponentName[] {
                        new ComponentName(this, SaveToDownloadsActivity.class)});
        startActivity(chooser);
    }

    private void openPrivacyPolicy() {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW,
                    Uri.parse(getString(R.string.privacy_policy_url))));
        } catch (RuntimeException e) {
            Log.w(TAG, "No browser for the privacy policy", e);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions,
            int[] grantResults) {
        // Nothing to do either way: without the permission the "ready" notification is not shown
    }
}
