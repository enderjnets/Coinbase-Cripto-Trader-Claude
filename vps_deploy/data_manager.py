import pandas as pd
import os
from datetime import datetime
import time

class DataManager:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _get_filename(self, product_id, granularity):
        """Standardized filename: data/BTC-USD_FIVE_MINUTE.csv"""
        safe_pid = product_id.replace("/", "-")
        return os.path.join(self.data_dir, f"{safe_pid}_{granularity}.csv")

    def save_data(self, df, product_id, granularity):
        """Saves dataframe to CSV."""
        if df is None or df.empty:
            return
        
        filepath = self._get_filename(product_id, granularity)
        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        df.to_csv(filepath, index=False)
        print(f"Data saved to {filepath}")

    def load_data(self, product_id, granularity):
        """Loads data from CSV if exists."""
        filepath = self._get_filename(product_id, granularity)
        if not os.path.exists(filepath):
            return None
        
        try:
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)
            return df
        except Exception as e:
            print(f"Error loading data: {e}")
            return None

    def smart_download(self, broker, product_id, start_date, end_date, granularity, progress_callback=None):
        """
        Smartly downloads only missing data ranges and merges with local storage.
        """
        # 1. Load existing data
        df_local = self.load_data(product_id, granularity)
        
        if df_local is None or df_local.empty:
            # Case A: No local data -> Download all
            print("No local data found. Full download.")
            return self._download_and_save(broker, product_id, start_date, end_date, granularity, df_local, progress_callback)
            
        # 2. Check coverage
        local_start = df_local['timestamp'].min()
        local_end = df_local['timestamp'].max()
        
        # Requests
        req_start = pd.Timestamp(start_date)
        req_end = pd.Timestamp(end_date)
        
        # Identify Gaps
        # Gap 1: Before local data
        gap_before_start = None
        gap_before_end = None
        
        if req_start < local_start:
            gap_before_start = req_start
            gap_before_end = local_start
            
        # Gap 2: After local data
        gap_after_start = None
        gap_after_end = None
        
        if req_end > local_end:
            gap_after_start = local_end
            gap_after_end = req_end
            
        # If request is fully inside local, return sliced local
        if not gap_before_start and not gap_after_start:
            print("Data already exists locally. Returning subset.")
            mask = (df_local['timestamp'] >= req_start) & (df_local['timestamp'] <= req_end)
            return df_local.loc[mask].reset_index(drop=True)
            
        # 3. Download Gaps
        dfs_to_merge = [df_local]
        
        if gap_before_start:
            print(f"Downloading missing history (Prepend): {gap_before_start} -> {gap_before_end}")
            df_pre = self._fetch_chunk(broker, product_id, gap_before_start, gap_before_end, granularity, progress_callback, 0.0, 0.5)
            if df_pre is not None:
                dfs_to_merge.append(df_pre)
                
        if gap_after_start:
            print(f"Downloading missing history (Append): {gap_after_start} -> {gap_after_end}")
            df_post = self._fetch_chunk(broker, product_id, gap_after_start, gap_after_end, granularity, progress_callback, 0.5, 1.0)
            if df_post is not None:
                dfs_to_merge.append(df_post)
                
        # 4. Merge
        if len(dfs_to_merge) > 1:
            df_final = pd.concat(dfs_to_merge)
            df_final = df_final.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)
        else:
            df_final = df_local
            
        # 5. Save updated master file
        self.save_data(df_final, product_id, granularity)
        
        # 6. Return requested slice
        mask = (df_final['timestamp'] >= req_start) & (df_final['timestamp'] <= req_end)
        return df_final.loc[mask].reset_index(drop=True)

    def _download_and_save(self, broker, product_id, start_date, end_date, granularity, existing_df, progress_callback):
        """Helper for full fresh download"""
        df_new = self._fetch_chunk(broker, product_id, start_date, end_date, granularity, progress_callback, 0.0, 1.0)
        self.save_data(df_new, product_id, granularity)
        return df_new

    def _fetch_chunk(self, broker, product_id, start, end, granularity, callback, p_start, p_end):
        """Uses broker client to fetch a specific range"""
        from datetime import timedelta
        
        granularity_map = {
            "ONE_MINUTE": 60,
            "FIVE_MINUTE": 300,
            "FIFTEEN_MINUTE": 900,
            "ONE_HOUR": 3600,
            "SIX_HOUR": 21600,
            "ONE_DAY": 86400
        }
        gran_seconds = granularity_map.get(granularity, 300)
        chunk_size_seconds = gran_seconds * 250
        
        all_dfs = []
        current_end = end
        
        while current_end > start:
            # Guard against infinite loops if timestamps don't move
            if (current_end - timedelta(seconds=0)) <= start:
                break

            current_start = max(start, current_end - timedelta(seconds=chunk_size_seconds))
            
            ts_start = int(current_start.timestamp())
            ts_end = int(current_end.timestamp())
            
            # CALL BROKER INTERFACE
            df_chunk = broker.get_historical_data(product_id, granularity, ts_start, ts_end)
            
            if df_chunk is not None and not df_chunk.empty:
                all_dfs.append(df_chunk)
            
            # Progress param mapping
            if callback:
                # Local progress 0 to 1 for this chunk
                total_span = (end - start).total_seconds()
                done_span = (end - current_end).total_seconds()
                local_pct = done_span / total_span
                # Map to global p_start -> p_end
                global_pct = p_start + (local_pct * (p_end - p_start))
                callback(global_pct)
                
            current_end = current_start
            time.sleep(0.15) # Rate limit
            
        if not all_dfs:
            return None
            
        full_df = pd.concat(all_dfs)
        # Ensure timestamp sorting
        if not pd.api.types.is_datetime64_any_dtype(full_df['timestamp']):
             full_df['timestamp'] = pd.to_datetime(full_df['timestamp'])
             
        full_df = full_df.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)
        return full_df
