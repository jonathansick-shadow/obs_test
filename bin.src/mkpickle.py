#!/usr/bin/env python

import cPickle
import os

for raft in ["0,1", "0,2", "0,3"]:
    for sensor in ["0,1", "1,0", "1,1"]:
        for snap in [0, 1]:
            for channel in ["0,0", "0,1", "1,0", "1,1"]:
                dataId = dict(visit=85470982,
                              raft=raft, sensor=sensor, snap=snap, channel=channel)
                loc = "raw-v%(visit)d-E%(snap)03d-r%(raft)s-s%(sensor)s-c%(channel)s.pickle" % dataId
                loc = os.path.join("tests", "data", "input", loc)
                num = int(raft[0] + raft[2] + sensor[0] + sensor[2] +
                          channel[0] + channel[2]) * 10 + snap
                if raft != "0,3" or (snap != 1 and sensor != "0,1"):
                    with open(loc, "w") as f:
                        cPickle.dump(num, f)
