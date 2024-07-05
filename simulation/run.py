from sim.simulation import simulation
from sim.destroyed_packet import Forward_type


# configuration file to use
configuration = "world_lorawan_hybrid"

# override the debug level from configuration file
my_debug = 2

# override the runtime from configuration file
my_runtime = 1000*60*60*1 + 1000*60*8

# override visualization
visualize = True

# simulate in real-time
real_time = False

sim = simulation(configuration, 
                 "sim_%s" % configuration, 
                 debug=my_debug, 
                 runtime=my_runtime, 
                 visualize=visualize, 
                 real_time=real_time)

sim.prepare()
sim.run()
sim.analyze(dont_print_additional=False)
# reasons = [Forward_type.RELAY_BLOCK, Forward_type.RETURN_TO_LAST]
reasons = None
# sim.further_analysis(print_packets=True, more_info=True, fwd_reasons_to_print=reasons)

sim.stop()