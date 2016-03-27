"""lsstSim-specific overrides for the processCcd task
"""
config.isr.doDark = False
config.isr.doFringe = False
# we don't have astrometry_net data (yet) so astrom and photo cal are impossible
config.calibrate.doAstrometry = False
config.calibrate.doPhotoCal = False
