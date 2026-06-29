# state_rank.py
import pandas as pd
import numpy as np

class MaxHeap:
    def __init__(self):
        self.heap = []
    def insert(self, score, state):
        self.heap.append((score, state))
        self._heapify_up(len(self.heap) - 1)
    def _heapify_up(self, idx):
        while idx > 0:
            parent = (idx - 1) // 2
            if self.heap[parent][0] < self.heap[idx][0]:
                self.heap[parent], self.heap[idx] = self.heap[idx], self.heap[parent]
                idx = parent
            else:
                break
    def _heapify_down(self, idx):
        n = len(self.heap)
        while idx < n:
            left = 2*idx + 1
            right = 2*idx + 2
            largest = idx
            if left < n and self.heap[left][0] > self.heap[largest][0]:
                largest = left
            if right < n and self.heap[right][0] > self.heap[largest][0]:
                largest = right
            if largest != idx:
                self.heap[idx], self.heap[largest] = self.heap[largest], self.heap[idx]
                idx = largest
            else:
                break
    def extract_max(self):
        if not self.heap:
            return None
        max_item = self.heap[0]
        last_item = self.heap.pop()
        if self.heap:
            self.heap[0] = last_item
            self._heapify_down(0)
        return max_item
    def size(self):
        return len(self.heap)
    def heap_sort(self):
        sorted_items = []
        original = self.heap.copy()
        while self.heap:
            sorted_items.append(self.extract_max())
        self.heap = original
        return sorted_items

def binary_search_by_state(sorted_list, state):
    left, right = 0, len(sorted_list) - 1
    while left <= right:
        mid = left + ((right - left) // 2)
        mid_state = sorted_list[mid][0]
        if mid_state == state:
            return mid
        elif mid_state < state:
            left = mid + 1
        else:
            right = mid - 1
    return -1

def get_rank_data(csv_path="crop_census.csv"):
    df = pd.read_csv(csv_path)
    state_metrics = df.groupby('state').agg({
        'yield_kg_ha': 'mean',
        'irrigation_pct': 'mean',
        'farm_revenue_cr': 'mean',
        'loss_pct': 'mean'
    }).reset_index()
    state_metrics.columns = ['state', 'avg_yield', 'avg_irrigation',
                             'avg_revenue', 'avg_loss']

    for col in ['avg_yield', 'avg_irrigation', 'avg_revenue', 'avg_loss']:
        min_val = state_metrics[col].min()
        max_val = state_metrics[col].max()
        if max_val > min_val:
            state_metrics[f'norm_{col}'] = (state_metrics[col] - min_val) / (max_val - min_val)
        else:
            state_metrics[f'norm_{col}'] = 0

    state_metrics['agri_score'] = (
        0.4 * state_metrics['norm_avg_yield'] +
        0.3 * state_metrics['norm_avg_irrigation'] +
        0.2 * state_metrics['norm_avg_revenue'] -
        0.1 * state_metrics['norm_avg_loss']
    )

    # Heap sort by score descending
    heap = MaxHeap()
    for _, row in state_metrics.iterrows():
        heap.insert(row['agri_score'], row['state'])
    sorted_by_score = heap.heap_sort()  # list of (score, state) descending

    # Also get sorted alphabetically for binary search
    sorted_by_state = sorted([(state, score) for score, state in sorted_by_score], key=lambda x: x[0])

    return sorted_by_score, sorted_by_state, state_metrics

def get_state_rank(state, sorted_by_state, sorted_by_score):
    idx = binary_search_by_state(sorted_by_state, state)
    if idx == -1:
        return None
    state_name, score = sorted_by_state[idx]
    # find rank
    rank = next(i+1 for i, (s, st) in enumerate(sorted_by_score) if st == state_name)
    return rank, state_name, score

if __name__ == '__main__':
    sorted_by_score, sorted_by_state, state_metrics = get_rank_data()
    print("Ranked States:")
    for rank, (score, state) in enumerate(sorted_by_score, 1):
        print(f"{rank:>3} {state:<20} {score:.4f}")
    # test search
    test = 'Punjab'
    res = get_state_rank(test, sorted_by_state, sorted_by_score)
    if res:
        rank, state, score = res
        print(f"\n{state} rank: {rank}, score: {score:.4f}")