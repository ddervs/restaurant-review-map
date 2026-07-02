#!/bin/bash
# Strip full article text before dumping: the Guardian Open Platform terms
# don't permit republishing article bodies, and reviews.sql is public. Text
# is only needed transiently within a pipeline run (postcode extraction and
# sentiment scoring both run before this step).
sqlite3 reviews.db "UPDATE reviews SET text = NULL;"
sqlite3 reviews.db .dump > reviews.sql
