/*
 * SPDX-License-Identifier: Apache-2.0
 */

package org.zeroroms.tools;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * Makes ZeroS tools Android's bug report handler (config_bugReportHandlerEnabled and
 * config_defaultBugReportHandlerApp in vendor/zeros/overlay). When the user presses Bug report
 * in the power menu, the system first asks whether the handler is available, then asks it to
 * take the report; both broadcasts come from the system, which holds DUMP (enforced by the
 * receiver's permission). Without an answer the system falls back to Android's own bug report.
 */
public class BugReportHandlerReceiver extends BroadcastReceiver {

    private static final String ACTION_BUGREPORT_REQUESTED =
            "com.android.internal.intent.action.BUGREPORT_REQUESTED";
    private static final String ACTION_GET_BUGREPORT_HANDLER_RESPONSE =
            "com.android.internal.intent.action.GET_BUGREPORT_HANDLER_RESPONSE";

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        if (ACTION_GET_BUGREPORT_HANDLER_RESPONSE.equals(action)) {
            setResultCode(Activity.RESULT_OK);
        } else if (ACTION_BUGREPORT_REQUESTED.equals(action)) {
            // Allowed from the background by START_ACTIVITIES_FROM_BACKGROUND (privileged)
            context.startActivity(new Intent(context, BugReportActivity.class)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    .putExtra(BugReportActivity.EXTRA_START, true));
        }
    }
}
