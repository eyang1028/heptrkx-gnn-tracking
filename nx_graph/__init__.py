"""
GNN models
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from .model          import SegmentClassifier as mm
from .model_less     import SegmentClassifier as mm_less
from .model_noLayerNorm import SegmentClassifier as mm_nonorm

def get_model(model_name=None):
    """
    model_name could be used for future testing different models
    """
    if model_name == "LESS":
        return mm_less()
    elif model_name == "NOLAYERNORM":
        print("Use model", model_name)
        return mm_nonorm()
    else:
        pass

    return mm()
