"""
convert hitgraphs to network-x and prepare graphs for graph-nets
"""
import numpy as np
from datasets.graph import load_graph
import networkx as nx

from graph_nets import utils_np

import os
import glob
import re
import random


def graph_to_input_target(graph):
    def create_feature(attr, fields):
        return np.hstack([np.array(attr[field], dtype=float) for field in fields])

    input_node_fields = ("pos",)
    input_edge_fields = ("distance",)
    target_node_fields = ("solution",)
    target_edge_fields = ("solution",)

    input_graph = graph.copy()
    target_graph = graph.copy()

    for node_index, node_feature in graph.nodes(data=True):
        input_graph.add_node(
            node_index, features=create_feature(node_feature, input_node_fields)
        )
        target_graph.add_node(
            node_index, features=create_feature(node_feature, target_node_fields)
        )

    for receiver, sender, features in graph.edges(data=True):
        input_graph.add_edge(
            sender, receiver, features=create_feature(features, input_edge_fields)
        )
        target_graph.add_edge(
            sender, receiver, features=create_feature(features, target_edge_fields)
        )

    input_graph.graph['features'] = input_graph.graph['features'] = np.array([0.0])
    return input_graph, target_graph


def inputs_generator(base_dir_, n_train_fraction=-1):
    base_dir =  os.path.join(base_dir_, "event00000{}_g{:09d}_INPUT.npz")

    file_patten = base_dir.format(1000, 0).replace('1000', '*')
    all_files = glob.glob(file_patten)
    n_events = len(all_files)
    evt_ids = np.sort([int(re.search('event00000([0-9]*)_g000000000_INPUT.npz',
                             os.path.basename(x)).group(1))
               for x in all_files])
    print(evt_ids)

    def get_sections(xx):
        section_patten = base_dir.format(xx, 0).replace('_g000000000', '*')
        #print(section_patten)
        return int(len(glob.glob(section_patten)))

    if len(evt_ids) < 102:
        all_sections = [get_sections(xx) for xx in evt_ids]
        n_sections = max(all_sections)
    else:
        # too long to run all of them...
        n_sections = get_sections(evt_ids[0])

    n_total = n_events*n_sections


    if n_events < 5:
        split_section = True
        n_max_evt_id_tr = n_events
        n_test = n_events
        pass
    else:
        split_section = False
        n_tr_fr = n_train_fraction if n_train_fraction > 0 else 0.7
        n_max_evt_id_tr = int(n_events * n_tr_fr)
        n_test = n_events - n_max_evt_id_tr

    print("Total Events: {} with {} sections, total {} files ".format(
        n_events, n_sections, n_total))
    print("Training data: [{}, {}] events, total {} files".format(0, n_max_evt_id_tr-1, n_max_evt_id_tr*n_sections))
    if split_section:
        print("Testing data:  [{}, {}] events, total {} files".format(0, n_events-1, n_test*n_sections))
    else:
        print("Testing data:  [{}, {}] events, total {} files".format(n_max_evt_id_tr, n_events, n_test*n_sections))


    def generate_input_target(n_graphs, is_train=True):
        input_graphs = []
        target_graphs = []
        igraphs = 0
        while igraphs < n_graphs:
            # determine while file to read
            sec_id = random.randint(0, n_sections-1)
            if is_train:
                evt_id = random.randint(0, n_max_evt_id_tr-1)
            else:
                if split_section:
                    evt_id = random.randint(0, n_events-1)
                else:
                    evt_id = random.randint(n_max_evt_id_tr, n_events-1)

            file_name = base_dir.format(evt_ids[evt_id], sec_id)
            if not os.path.exists(file_name):
                continue

            with np.load(file_name) as f:
                input_graphs.append(dict(f.items()))

            with np.load(file_name.replace("INPUT", "TARGET")) as f:
                target_graphs.append(dict(f.items()))

            igraphs += 1

        return input_graphs, target_graphs

    return generate_input_target


INPUT_NAME = "INPUT"
TARGET_NAME = "TARGET"
def get_networkx_saver(output_dir_):
    """
    save networkx graph as data dict for TF
    """
    output_dir = output_dir_
    def save_networkx(evt_id, isec, graph):
        output_data_name = os.path.join(
            output_dir,
            'event{:09d}_g{:09d}_{}.npz'.format(evt_id, isec, INPUT_NAME))
        if os.path.exists(output_data_name):
            print(output_data_name, "is there")
            return

        input_graph, target_graph = graph_to_input_target(graph)
        output_data = utils_np.networkx_to_data_dict(input_graph)
        target_data = utils_np.networkx_to_data_dict(target_graph)

        np.savez( output_data_name, **output_data)
        np.savez( output_data_name.replace(INPUT_NAME, TARGET_NAME), **target_data)

    return save_networkx
