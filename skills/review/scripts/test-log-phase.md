# test-log-phase.sh Contract

Regression harness for `skills/review/scripts/log-phase.sh`.

It verifies writing a registered flat review batch, rejecting an unregistered slash-containing batch with the diagnostic in the quiet log, and includes a stdout size cap assertion (≤2 KB).

Run with `bash skills/review/scripts/test-log-phase.sh` or `make test-log-phase`.
