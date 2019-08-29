#!/usr/bin/env bash
set -euo pipefail

# 20190829WF - extract only bike route S
# also look at xmlstarlet and xqilla


tr '\n' ' ' < PABike.kml | `# make all one line`
   sed 's/<Place/\n<Place/g;s:</Folder>:\n</Folder>:g' | `# new line for each placemark and folder end`
   perl -lne 'print if $.==1 || m:</Folder: || m:bk_rt">S:' | `# only take first line, ending line, and mk_rt S`
  grep -v 'OBJECTID">506' `# remove gettysburgh` \
  > PA_S.kml
