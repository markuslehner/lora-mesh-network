from ctypes import FormatError
from sim.simulation import simulation
from multiprocessing import Process
import math

sim_list : 'list[simulation]' = []

def thread_function(s_name, s_config, s_runtime, s_debug):
    global sim_list

    sim = simulation(s_config, s_name, debug=s_debug, runtime=s_runtime, visualize=False, print_debug=False)
    sim_list.append(sim)
    
    sim.prepare()
    sim.run()
    print("\n\n")
    print("====================== %s ======================" % sim.name)
    sim.debugger.print = True
    sim.analyze()
    sim.further_analysis(print_packets=True, more_info=False, fwd_reasons_to_print=None)
    sim.stop()

def run_multiple(s_name : str, s_config : str, n_sims, n_parallel_sims, s_runtime, s_debug=2):
    for k in range(math.ceil(n_sims/n_parallel_sims)):
        processes = []

        end_off = 0
        if(k == math.ceil(n_sims/n_parallel_sims) - 1 and n_sims%n_parallel_sims != 0):
            end_off = n_parallel_sims - n_sims%n_parallel_sims

        for i in range(n_parallel_sims - end_off):
            processes.append(Process(group=None, target=thread_function, name=("thread_%i" % i), args=( "%s_%i" % (s_name, k*n_parallel_sims + i), s_config, s_runtime, s_debug) ) )

        for t in processes:
            t.start()

        # wait for all threads to finish
        for t in processes:
            t.join()

    # for i in range(len(sim_list)):
    #     print("Simulation %i" % i)
    #     sim_list[i].debugger.print = True
    #     sim_list[i].analyze()
    #     sim_list[i].stop()

def run_multiple_different(s_names : 'list[str]', s_configs : 'list[str]', n_parallel_sims, s_runtime, s_debug=2):
    
    if(len(s_names) != len(s_configs)):
        raise Exception("configuration lengths do not match!")
    
    for k in range(math.ceil(len(s_names)/n_parallel_sims)):
        processes = []

        end_off = 0
        if(k == math.ceil(len(s_names)/n_parallel_sims) - 1 and len(s_names)%n_parallel_sims != 0):
            end_off = n_parallel_sims - n_sims%n_parallel_sims

        for i in range(n_parallel_sims - end_off):
            processes.append(Process(group=None, target=thread_function, name=("thread_%i" % i), args=( s_names[k*n_parallel_sims + i], s_configs[k*n_parallel_sims + i], s_runtime, s_debug) ) )

        for t in processes:
            t.start()

        # wait for all threads to finish
        for t in processes:
            t.join()

if __name__ == '__main__':
    # num sims to run in total
    n_sims = 10

    # max num of sims to run in parallel
    n_parallel_sims = 5

    # override the debug level from configuration file
    my_debug = 2

    # override the runtime from configuration file
    my_runtime = 1000*60*60*24 +1000*60*8

    list_names = [
        "single_SF7_flooding_15_8",
        "double_SF7_real_05_3",
        "double_SF7_flooding_05_4",
        "double_SF7_flooding_15_0",
        "double_SF7_flooding_15_7"
    ]

    list_configs = [
        "world_single_SF7_flooding_15",
        "world_double_SF7_real_05",
        "world_double_SF7_flooding_05",
        "world_double_SF7_flooding_15",
        "world_double_SF7_flooding_15"
    ]

    run_multiple_different(list_names, list_configs, 5, my_runtime)

    run_multiple("single_SF7_flooding_05", "world_single_SF7_flooding_05", n_sims, n_parallel_sims, my_runtime)
    run_multiple("single_SF7_flooding_10", "world_single_SF7_flooding_10", n_sims, n_parallel_sims, my_runtime)
    run_multiple("single_SF7_flooding_15", "world_single_SF7_flooding_15", n_sims, n_parallel_sims, my_runtime)
    run_multiple("single_SF7_flooding_20", "world_single_SF7_flooding_20", n_sims, n_parallel_sims, my_runtime)
