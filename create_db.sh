#!/bin/bash
if [ -f reviews.sql ]; then
  sqlite3 reviews.db < reviews.sql
fi
