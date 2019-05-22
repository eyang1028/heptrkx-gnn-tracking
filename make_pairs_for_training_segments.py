#!/usr/bin/env python3

from make_true_pairs_for_training_segments_mpi import layer_pairs

def process(input_info, selected_hits_angle, output_pairs_dir):
    layer_pair, ii = input_info
    out_name = os.path.join(output_pairs_dir, 'pair{:03d}.h5'.format(ii))
    if os.path.exists(out_name):
        return

    os.makedirs(output_pairs_dir, exist_ok=True)
    segments = list(utils_mldata.create_segments(selected_hits_angle, [layer_pair]))

    with pd.HDFStore(out_name) as store:
            store['data'] = segments[0]


if __name__ == "__main__":
    import os
    import argparse

    parser = argparse.ArgumentParser(description='make pairs for given evtid')
    add_arg = parser.add_argument
    add_arg('data_dir', type=str, help='event directory',
            default='/global/homes/x/xju/atlas/heptrkx/trackml_inputs/train_all')
    add_arg('blacklist_dir', type=str, help='blacklist directory',
           default='/global/homes/x/xju/atlas/heptrkx/trackml_inputs/blacklist')
    add_arg('evtid', type=int, help='event id')
    add_arg('output_dir', type=str, help='save created pairs')
    add_arg('--n-pids', type=int, help='how many particles should be used',
            default=-1)
    add_arg('--det-dir', type=str, help='detector description',
            default='/global/homes/x/xju/atlas/heptrkx/trackml_inputs/detectors.csv')
    args = parser.parse_args()

    data_dir = args.data_dir
    black_list_dir = args.blacklist_dir
    evtid = args.evtid
    n_pids = args.n_pids
    det_dir  = args.det_dir
    output_dir = args.output_dir

    from preprocess import utils_mldata
    hits, particles, truth, cells = utils_mldata.read(data_dir, black_list_dir, evtid)

    reco_pids = utils_mldata.reconstructable_pids(particles, truth)
    from nx_graph import utils_data
    import numpy as np
    import pandas as pd

    # noise included!
    hh = utils_data.merge_truth_info_to_hits(hits, truth, particles)
    unique_pids = np.unique(hh['particle_id'])
    print("Number of particles:", unique_pids.shape, reco_pids.shape)

    if n_pids > 0:
        selected_pids = np.random.choice(unique_pids, size=n_pids)
        selected_hits = hh[hh.particle_id.isin(selected_pids)].assign(evtid=evtid)
    else:
        selected_hits = hh.assign(evtid=evtid)

    all_layers = np.unique(selected_hits.layer)
    print("Total Number of Layers:", len(all_layers))
    print("Total Layer Pairs", len(layer_pairs))

    from nx_graph import transformation
    module_getter = utils_mldata.module_info(det_dir)

    from functools import partial

    local_angles = utils_mldata.cell_angles(selected_hits, module_getter, cells)
    selected_hits_angle = selected_hits.merge(local_angles, on='hit_id', how='left')

    pp_layers_info = [(x, ii) for ii,x in enumerate(layer_pairs)]

    try:
        n_workers = int(os.getenv('SLURM_CPUS_PER_TASK'))
    except (ValueError, TypeError):
        n_workers = 1
    print("Workers:", n_workers)

    import multiprocessing as mp
    with mp.Pool(processes=n_workers) as pool:
        pp_func=partial(process, selected_hits_angle=selected_hits_angle,
                        output_pairs_dir=os.path.join(output_dir, 'evt{}'.format(evtid)))
        pool.map(pp_func, pp_layers_info)
