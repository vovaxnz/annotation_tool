import numpy as np


def encode_rle(mask):
    # Ensure the mask is flattened
    flat_mask = mask.flatten()
    # Find where the value changes
    diff = np.diff(flat_mask)
    # Indices where value changes
    change_indices = np.where(diff != 0)[0] + 1
    # Positions to split the flattened array and count runs
    positions = np.concatenate(([0], change_indices, [len(flat_mask)]))
    # Calculate run lengths
    run_lengths = np.diff(positions)
    # Values at the start of each run
    run_values = flat_mask[positions[:-1]]
    # Combine values and run lengths into a string
    encoded_str = ','.join([f"{val}:{count}" for val, count in zip(run_values, run_lengths)])
    return encoded_str


def decode_rle(encoded_str, shape=(1920, 1080)): # TODO: Use height, width
    # Split the encoded string into pairs of values and counts
    pairs = encoded_str.split(',')
    # Separate values and their counts
    vals_counts = [pair.split(':') for pair in pairs]
    values = np.array([int(val) for val, _ in vals_counts], dtype=np.uint8)
    counts = np.array([int(count) for _, count in vals_counts], dtype=int)
    
    # Allocate the flat mask array once based on the total length
    flat_mask = np.zeros(counts.sum(), dtype=np.uint8)
    
    # Fill the flat mask using calculated indices
    start_idx = 0
    for value, count in zip(values, counts):
        flat_mask[start_idx:start_idx + count] = value
        start_idx += count
    
    # Reshape the flat mask to the original image shape
    return flat_mask.reshape(shape)