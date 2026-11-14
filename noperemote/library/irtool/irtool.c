/*
 * irtool: Flipper Zero's infrared encoders and decoders (lib/infrared, GPL-3.0,
 * fetched by fetch-sources.sh) as a filter for build-library.py. Runs on the
 * Mac only; nothing of it ships in ZeroS.
 *
 * One request per line on stdin, one answer per line on stdout:
 *   E <protocol> <address hex> <command hex>
 *       -> <frequency> <duty cycle> <mark> <space> <mark> ...
 *          the signal as Flipper sends it for one press (the protocol's
 *          minimum repeat count), or ERR
 *   D <mark> <space> <mark> ...
 *       -> <protocol> <address hex> <command hex> for the first message the
 *          decoders find, or NONE
 *
 * SPDX-License-Identifier: GPL-3.0-only
 */
#include <stdio.h>
#include <stdlib.h>
#include <setjmp.h>
#include <string.h>
#include "infrared.h"

/* A failed check inside lib/infrared (malformed input) jumps back here; the
   request is answered ERR or NONE and its handler is not freed. */
static jmp_buf fail;
void irtool_fail(void) { longjmp(fail, 1); }

#define MAXT 4096

static void encode(char* proto_name, char* addr, char* cmd) {
    InfraredProtocol p = infrared_get_protocol_by_name(proto_name);
    if(p == InfraredProtocolUnknown) { puts("ERR"); return; }
    InfraredMessage m = {.protocol = p, .address = (uint32_t)strtoul(addr, NULL, 16),
                         .command = (uint32_t)strtoul(cmd, NULL, 16), .repeat = false};
    if(setjmp(fail)) { puts("ERR"); return; }
    InfraredEncoderHandler* h = infrared_alloc_encoder();
    infrared_reset_encoder(h, &m);
    size_t frames = infrared_get_protocol_min_repeat_count(p);
    if(frames < 1) frames = 1;
    static uint32_t t[MAXT];
    int n = 0, last = -1; /* last level: -1 none, 0 space, 1 mark */
    size_t done = 0;
    while(done < frames && n < MAXT - 1) {
        uint32_t d; bool lv;
        InfraredStatus s = infrared_encode(h, &d, &lv);
        if(s == InfraredStatusDone) done++;
        if(d == 0) continue;
        if(n == 0 && !lv) continue;          /* leading silence */
        if(last == (int)lv) t[n - 1] += d;   /* join same-level runs */
        else { t[n++] = d; last = lv; }
    }
    infrared_free_encoder(h);
    if(n > 0 && last == 0) n--;              /* trailing space */
    printf("%lu %.2f", (unsigned long)infrared_get_protocol_frequency(p),
           (double)infrared_get_protocol_duty_cycle(p));
    for(int i = 0; i < n; i++) printf(" %u", t[i]);
    putchar('\n');
}

static void decode(char* rest) {
    if(setjmp(fail)) { puts("NONE"); return; }
    InfraredDecoderHandler* h = infrared_alloc_decoder();
    const InfraredMessage* m = NULL;
    bool lv = true;
    for(char* tok = strtok(rest, " \t\n"); tok && !m; tok = strtok(NULL, " \t\n")) {
        m = infrared_decode(h, lv, (uint32_t)strtoul(tok, NULL, 10));
        lv = !lv;
    }
    if(!m) m = infrared_decode(h, lv, 200000); /* a long gap ends the last frame */
    if(!m) m = infrared_check_decoder_ready(h);
    if(m) printf("%s %X %X\n", infrared_get_protocol_name(m->protocol), m->address, m->command);
    else puts("NONE");
    infrared_free_decoder(h);
}

int main(void) {
    static char line[65536];
    setvbuf(stdout, NULL, _IOLBF, 0);
    while(fgets(line, sizeof line, stdin)) {
        if(line[0] == 'E') {
            char p[32], a[32], c[32];
            if(sscanf(line + 1, "%31s %31s %31s", p, a, c) == 3) encode(p, a, c); else puts("ERR");
        } else if(line[0] == 'D') decode(line + 1);
        else puts("ERR");
    }
    return 0;
}
