/*
 * SPDX-License-Identifier: Apache-2.0
 */

package org.zeroroms.tools;

import android.app.Activity;
import android.os.Bundle;

/**
 * Answers Google setup's Assistant opt-in request, which only the Google app (not shipped by
 * ZeroS) handles. Without an answer the Assistant step waits on a blank screen (bug B10). Result 1
 * is the "skipped" code Google setup's own skip paths use. The intent filter has a low priority,
 * so the Google app handles the request instead if it is ever installed.
 */
public class OpaSkipActivity extends Activity {

    private static final int RESULT_SKIP = RESULT_FIRST_USER;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setResult(RESULT_SKIP);
        finish();
    }
}
