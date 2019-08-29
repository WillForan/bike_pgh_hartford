#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from haversine import haversine
from functools import cmp_to_key

cord = '-?[0-9.]+'
patstr = ('(OBJECTID">(?P<id>[0-9]+)<).*<coordinates>(?P<allcord>(?P<slat>%s),(?P<slon>%s)' +
          '.* (?P<elat>%s),(?P<elon>%s))</') % \
         (cord, cord, cord, cord)
PATT = re.compile(patstr)


def mean(*kargs):
    return sum(kargs)/len(kargs)


def crd_to_struct(line, metric=min):
    """ extract first and last coordinate """
    match = PATT.search(line)
    if not match:
        return None
    d = match.groupdict()
    # make numbers
    for k in ['slat', 'slon', 'elat', 'elon']:
        d[k] = float(d[k])
    # remove any multi <MultiGeometry><LineString
    # there are 3 of these on route s. end lat/long still from multiline
    #  grep '<LineString.*<LineString' PA_S.kml | wc -l
    # TODO: something more princilbed? (concat, keep the longests)?
    d['allcord'] = re.sub('<.*$', ' ', d['allcord'])
    # return with metric calculated
    return {**d,
            'mlat': metric(d['slat'], d['elat']),
            'mlon': metric(d['slon'], d['elon'])}


def rev_cord(old):
    """reverse coordinates"""
    c = old
    c['slat'] = old['elat']
    c['slon'] = old['elon']
    c['elat'] = old['slat']
    c['elon'] = old['slon']
    ac = old['allcord'].split(' ')
    ac.reverse()
    c['allcord'] = " ".join(ac)
    return(c)


def hvs_crd(c1, c2, rev=False):
    """ how far away is end of c1 from start of c2"""
    if rev:
        endcord = (c2['elat'], c2['elon'])
    else:
        endcord = (c2['slat'], c2['slon'])
    return haversine((c1['elat'], c1['elon']), endcord)

# read in and parse
fp = open('PA_S.kml', 'r')
kml_header = fp.readline()
crds = list(filter(None.__ne__, [crd_to_struct(l) for l in fp.readlines()]))
fp.close()

# hard code remove some weird paths
exclude_segs = [440, 444, 433, 383, 718, 404]
# ['404', '501']
# 383, 718 is in somerset
# 422 in champelburghsomethingorother but is the wrong one to remove
# 440, 444 and 433 are alternate in york
# '421' and '423' causes some wierdness
crds = [c for c in crds if int(c['id']) not in exclude_segs]


# # remove duplicate starts -- this just removes those that could be start=end
# # hopefuly no multisegemnt separtors
# for i in range(len(crds)):
#     for j in range(i+1, len(crds)):
#         if crds[i] and crds[j] and crds[i]['mlat'] == crds[j]['mlat']:
#             crds[j] = None
# crds = list(filter(None.__ne__, crds))

# ## sort based on lowest lat
# # bad sorts buy how close each segmant is to a pair
# each_cmp = lambda a, b: haversine((b['slat'], b['slon']), (a['elat'], a['elon']))
# sorted(crds, key=cmp_to_key(each_cmp))
#
# find min lat
# lats = [c['mlat'] for c in crds]
# base_idx = lats.index(min(lats))
# base_crd = (crds[base_idx]['slat'], crds[base_idx]['slon'])
# # bad does not gerenty continous
# base_cmp = lambda c: haversine((c['slat'], c['slon']), base_crd)
# sorted(crds, key=base_cmp)
ids = [c['id'] for c in crds]
base_idx = ids.index('362')
#crds[base_idx] = rev_cord(crds[base_idx])  # first one is going the wrong way!
crds[base_idx]['dist_from'] = 0
# # 421 is reversed and just a bit closer, caues an error
# for fix_id in [418, 421, 423]:
#     fix_i = ids.index(str(fix_id))
#     crds[fix_i] = rev_cord(crds[fix_i])
# 

# algo doesn't work but we know what should happen
hard_code_pairs = [
        (418, 421, True),
        (421, 423, True),
        (423, 424, False)]
ids = [c['id'] for c in crds]

n = len(crds)
order = [base_idx] + [0]*(n-1)
allidx = set(range(n)) - set([base_idx])
for order_i in range(1, n):
    prev = crds[order[order_i-1]]

    taken = set(order[0:order_i])
    left_idx = list(allidx - taken)
    left_val = [crds[x] for x in left_idx]
    # look at path two ways and choose the best
    hvs_fwd = [hvs_crd(prev, c) for c in left_val]
    hvs_rev = [hvs_crd(prev, c, True) for c in left_val]
    hf_min = min(hvs_fwd)
    hr_min = min(hvs_rev)
    mini_fwd = left_idx[hvs_fwd.index(hf_min)]
    mini_rev = left_idx[hvs_rev.index(hr_min)]
    if hf_min < hr_min:
        rev = False
        mini = mini_fwd
        crds[mini]['dist_from'] = hf_min
    else:
        rev = True
        mini = mini_rev
        crds[mini]['dist_from'] = hr_min



    print(f"""{order_i}: from {prev['id']} to {crds[mini]['id']} (rev: {rev}) {prev['elat']},{prev['elon']}
           fwd: {crds[mini_fwd]['id']} {hf_min} {crds[mini_fwd]['slat']},{crds[mini_rev]['slon']}
           rev: {crds[mini_rev]['id']} {hr_min} {crds[mini_rev]['slat']},{crds[mini_rev]['slon']}""")

    # hard code to fix one connection
    for (previd, nextid, isrev) in hard_code_pairs:
        if prev['id'] == str(previd):
            if crds[mini]['id'] == str(nextid):
                print("\thad hardcode but algo go it right!")
                break

            mini = ids.index(str(nextid))
            crds[mini]['dist_from'] = hvs_crd(prev, crds[mini], isrev)
            rev = isrev
            print(f"\thardcoded: {nextid} instead: {crds[mini]['dist_from']} (rev {rev})")
            break

    if rev:
        # and reverse cord
        crds[mini] = rev_cord(crds[mini])

    order[order_i] = mini

crds = [crds[i] for i in order]

# remove things that are too far away
stop_i = 0
while stop_i < len(crds):
    stop_i += 1
    if crds[stop_i]['dist_from'] > 30:
        break

# final_cords = [c for c in crds if c['dist_from'] < 10]
final_cords = crds[0:stop_i]

# what do we have
#for c in final_cords:
#    print(c['id'], c['mlat'], c['dist_from'])
#

out = open('bike_s_cont.kml', 'w')
out.write(kml_header + '\n<Placemark><LineString>\n<coordinates>\n')
out.write("\n\t".join([c['allcord'] for c in final_cords]))
out.write('\n</coordinates>\n')
out.write('\n</LineString></Placemark></Folder></Document></kml>\n')
out.close()
