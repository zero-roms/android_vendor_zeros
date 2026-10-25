/*
 * SPDX-License-Identifier: Apache-2.0
 */

package org.zeroroms.tools;

import android.app.PendingIntent;
import android.content.Intent;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/**
 * Quick settings tile that opens the ZeroS bug report screen, which collects a report and lets
 * the user send it to ZeroS, save it or share it. The tile asks for the phone to be unlocked
 * first, since a bug report holds personal data.
 */
public class BugReportTileService extends TileService {

    @Override
    public void onStartListening() {
        Tile tile = getQsTile();
        if (tile == null) {
            return;
        }
        tile.setState(Tile.STATE_INACTIVE);
        tile.updateTile();
    }

    @Override
    public void onClick() {
        if (isLocked()) {
            unlockAndRun(this::openBugReport);
        } else {
            openBugReport();
        }
    }

    private void openBugReport() {
        Intent intent = new Intent(this, BugReportActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                .putExtra(BugReportActivity.EXTRA_START, true);
        startActivityAndCollapse(PendingIntent.getActivity(this, 1, intent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT));
    }
}
