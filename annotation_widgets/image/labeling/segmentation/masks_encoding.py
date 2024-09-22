import os
import time
import cv2
import numpy as np
from tqdm import tqdm

from utils import open_json, save_json


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


def decode_rle(encoded_str, width, height): 
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
    return flat_mask.reshape((height, width))


def get_empty_rle(height, width) -> str:
    return f"0:{height*width}"


if __name__ == "__main__":
    source_masks_dir = "/media/vova/data/workspace/kyiv/2024_03_16_debug_annotation/masks/train/crane"
    output_json_path = "/media/vova/data/workspace/kyiv/2024_03_16_debug_annotation/masks/converted.json"
    decoded_masks_dir = "/media/vova/data/workspace/kyiv/2024_03_16_debug_annotation/masks/train_decoded/crane"

    os.makedirs(decoded_masks_dir, exist_ok=True)

    # 1. Encode all masks and save to json
    # encoded_masks = dict()
    # for mask_name in tqdm(os.listdir(source_masks_dir), desc="Encoding"): # 60it/s
    #     mask = cv2.imread(os.path.join(source_masks_dir, mask_name), cv2.IMREAD_GRAYSCALE)
    #     encoded = encode_rle(mask)
    #     encoded_masks[mask_name] = encoded
    
    # save_json(value=encoded_masks, file_path=output_json_path)

    # 2. Open json and decode masks and save them to decoded dir
    data = open_json(output_json_path)

    decode_speed_total = 0
    for mask_name, encoded in tqdm(data.items(), desc="Decoding"): # 74.78it/s
        start = time.time()
        decoded = decode_rle(encoded, width=1920, height=1080)
        decode_speed_total += time.time() - start
        # decoded[decoded>0] = 100
        # output_pauth = os.path.join(decoded_masks_dir, mask_name)
        # cv2.imwrite(output_pauth, decoded)

    print(decode_speed_total / len(data)) # 0.0015846541779512787

    # 3. Check difference
    # for mask_name in os.listdir(source_masks_dir):
    #     mask = cv2.imread(os.path.join(source_masks_dir, mask_name), cv2.IMREAD_GRAYSCALE)
    #     decoded_mask = cv2.imread(os.path.join(decoded_masks_dir, mask_name), cv2.IMREAD_GRAYSCALE)
    #     mask[mask>0] = 100
    #     print("diff", np.sum(mask-decoded_mask))
