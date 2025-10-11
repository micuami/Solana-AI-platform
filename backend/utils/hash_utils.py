# backend/utils/hash_utils.py
import hashlib
import torch
import numpy as np

def tensor_to_bytes(tensor: torch.Tensor) -> bytes:
    arr = tensor.detach().cpu().numpy()
    # ensure little-endian
    if arr.dtype.byteorder == '>':
        arr = arr.byteswap().newbyteorder()
    return arr.tobytes()

def canonical_state_dict_hash(model_or_state_dict) -> str:
    if hasattr(model_or_state_dict, "state_dict"):
        sd = model_or_state_dict.state_dict()
    else:
        sd = model_or_state_dict

    keys = sorted(sd.keys())
    h = hashlib.sha256()
    for k in keys:
        v = sd[k]
        h.update(k.encode('utf-8') + b'\0')
        shape_bytes = ",".join(map(str, v.shape)).encode('utf-8')
        h.update(shape_bytes + b'\0')
        dtype_bytes = str(v.dtype).encode('utf-8')
        h.update(dtype_bytes + b'\0')
        h.update(tensor_to_bytes(v))
    return h.hexdigest()

# streaming sha256 for big files
def file_sha256_stream(path, chunk_size=4*1024*1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

# build merkle root from file by chunking (returns hex)
def merkle_root_from_file(path, chunk_size=4*1024*1024):
    import math
    def sha256_bytes(b):
        return hashlib.sha256(b).digest()

    leaves = []
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            leaves.append(sha256_bytes(chunk))
    if not leaves:
        # empty file
        return hashlib.sha256(b"").hexdigest()

    # build tree
    while len(leaves) > 1:
        next_level = []
        for i in range(0, len(leaves), 2):
            left = leaves[i]
            right = leaves[i+1] if i+1 < len(leaves) else left
            next_level.append(sha256_bytes(left + right))
        leaves = next_level
    return leaves[0].hex()
