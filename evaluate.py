from postprocess.evaluate_tf import create_evaluator

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

from graph_nets import utils_np
from trackml.dataset import load_event
from nx_graph import utils_plot, utils_data, utils_train, prepare, utils_test
from postprocess import wrangler, analysis


import os
import glob

config_file = 'configs/nxgraph_test_pairs.yaml'
input_ckpt = 'trained_results/nxgraph_pairs_004'

model = create_evaluator(config_file, 99987, input_ckpt)

config = utils_train.load_config(config_file)
evtid = 1099
isec = -1
batch_size = config['train']['batch_size']

file_dir = config['data']['output_nxgraph_dir']
hits_graph_dir = config['data']['input_hitsgraph_dir']
trk_dir = '/global/homes/x/xju/atlas/heptrkx/trackml_inputs/train_all'
base_dir =  os.path.join(file_dir, "event00000{}_g{:09d}_INPUT.npz")
file_names = []
if isec < 0:
    section_patten = base_dir.format(evtid, 0).replace('_g{:09}'.format(0), '*')
    n_sections = int(len(glob.glob(section_patten)))
    file_names = [(base_dir.format(evtid, ii), ii) for ii in range(n_sections)]
else:
    file_names = [(base_dir.format(evtid, isec), isec)]

n_batches = len(file_names)//batch_size if len(file_names)%batch_size==0 else len(file_names)//batch_size + 1
split_inputs = np.array_split(file_names, n_batches)

dd = os.path.join(trk_dir, 'event{:09d}')
hits, particles, truth = load_event(dd.format(evtid), parts=['hits', 'particles', 'truth'])
hits = utils_data.merge_truth_info_to_hits(hits, truth, particles)
true_features = ['pt', 'particle_id', 'nhits', 'weight']

all_graphs = []
is_digraph = True
is_bidirection = False
# evaluate each graph
for ibatch in range(n_batches):
    ## pad batch_size
    current_files = list(split_inputs[ibatch])
    if len(current_files) < batch_size:
        last_file = current_files[-1]
        current_files += [last_file] *(batch_size-len(current_files))

#     print(current_files)
    input_graphs = []
    target_graphs = []
    for items in current_files:
        file_name = items[0]
        with np.load(file_name) as f:
            input_graphs.append(dict(f.items()))

        with np.load(file_name.replace("INPUT", "TARGET")) as f:
            target_graphs.append(dict(f.items()))

    graphs = model(utils_np.data_dicts_to_graphs_tuple(input_graphs),
                   utils_np.data_dicts_to_graphs_tuple(target_graphs),
                   use_digraph=is_digraph, bidirection=is_bidirection
                  )
    if len(graphs) != batch_size:
        raise ValueError("graph size not the same as batch-size")

     # decorate the graph with truth info
    for ii in range(batch_size):
        idx = int(current_files[ii][1])
        id_name = os.path.join(hits_graph_dir, "event{:09d}_g{:03d}_ID.npz".format(evtid, idx))
        with np.load(id_name) as f:
            hit_ids = f['ID']

        for node in graphs[ii].nodes():
            hit_id = hit_ids[node]
            graphs[ii].node[node]['hit_id'] = hit_id
            graphs[ii].node[node]['info'] = hits[hits['hit_id'] == hit_id][true_features].values
        graphs[ii].graph['info'] = [idx] ## section ID

    all_graphs += graphs



weights = []
truths = []
for G in all_graphs:
    weight = [G.edges[edge]['predict'][0] for edge in G.edges()]
    truth  = [G.edges[edge]['solution'][0] for edge in G.edges()]
    weights += weight
    truths += truth

weights = np.array(weights)
truths = np.array(truths)
utils_test.plot_metrics(weights, truths, odd_th=0.1)

# post process
# take one section as an example
"""
G = all_graphs[0]
all_true_tracks = wrangler.get_tracks(G, feature_name='solution')
all_predict_tracks = wrangler.get_tracks(G, feature_name='predict')
true_df = analysis.graphs_to_df(all_true_tracks)
pred_df = analysis.graphs_to_df(all_predict_tracks)

total_particles = np.unique(true_df.merge(truth, on='hit_id', how='left')['particle_id'])
print(len(total_particles))

th = 0.
good_pids, bad_pids = analysis.label_particles(pred_df, truth, th, ignore_noise=True)
good_trks = hits[hits['particle_id'].isin(good_pids)]
def print_info(res_pred):
    print(res_pred['n_correct'], res_pred['n_wrong'], len(res_pred['isolated_pids']), len(res_pred['broken_pids']), len(res_pred['connected_pids']))

res_pred = analysis.summary_on_prediction(G, good_trks, pred_df)
print("Prediction Info")
print_info(res_pred)
print("True Info")
res_truth = analysis.summary_on_prediction(G, good_trks, true_df)
print_info(res_truth)
"""
