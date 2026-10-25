/*
 * SPDX-License-Identifier: Apache-2.0
 */

package org.zeroroms.tools;

import android.content.Context;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

/**
 * State of the bug report flow, shared by {@link BugReportService} and {@link BugReportActivity}
 * in this process. At most one report is kept: the one being collected or the one waiting to be
 * sent, saved or deleted. It lives in this app's private storage until then.
 *
 * <p>Status and listeners are used on the main thread only; the file paths may be read from any
 * thread (ReportFileProvider).
 */
final class BugReports {

    enum Status { IDLE, CAPTURING, READY, FAILED }

    interface Listener {
        void onBugReportChanged();
    }

    private static BugReports sInstance;

    private final File mDir;
    private final List<Listener> mListeners = new ArrayList<>();
    private Status mStatus;
    private int mProgress;
    private int mErrorCode;

    static synchronized BugReports get(Context context) {
        if (sInstance == null) {
            sInstance = new BugReports(context.getApplicationContext());
        }
        return sInstance;
    }

    private BugReports(Context context) {
        mDir = new File(context.getFilesDir(), "bugreports");
        // A collection cut short when this process died leaves a partial file behind
        capturingFile().delete();
        mStatus = readyFile().exists() ? Status.READY : Status.IDLE;
    }

    File readyFile() {
        return new File(mDir, "bugreport.zip");
    }

    File capturingFile() {
        return new File(mDir, "collecting.zip");
    }

    File ensureDir() {
        mDir.mkdirs();
        return mDir;
    }

    Status status() {
        return mStatus;
    }

    int progress() {
        return mProgress;
    }

    int errorCode() {
        return mErrorCode;
    }

    void setCapturing() {
        mStatus = Status.CAPTURING;
        mProgress = 0;
        notifyListeners();
    }

    void setProgress(int progress) {
        mProgress = progress;
        notifyListeners();
    }

    /** Moves the collected file into place. Returns false if that fails. */
    boolean setReady() {
        readyFile().delete();
        if (!capturingFile().renameTo(readyFile())) {
            setFailed(-1);
            return false;
        }
        mStatus = Status.READY;
        notifyListeners();
        return true;
    }

    void setFailed(int errorCode) {
        capturingFile().delete();
        mStatus = Status.FAILED;
        mErrorCode = errorCode;
        notifyListeners();
    }

    /** Deletes the waiting report (after it was sent, or when the user deletes it). */
    void discard() {
        readyFile().delete();
        mStatus = Status.IDLE;
        notifyListeners();
    }

    void addListener(Listener listener) {
        mListeners.add(listener);
    }

    void removeListener(Listener listener) {
        mListeners.remove(listener);
    }

    /** True while BugReportActivity is on screen. */
    boolean hasListeners() {
        return !mListeners.isEmpty();
    }

    private void notifyListeners() {
        for (Listener listener : new ArrayList<>(mListeners)) {
            listener.onBugReportChanged();
        }
    }
}
