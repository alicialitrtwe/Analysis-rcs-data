import numpy as np
import pandas as pd


def get_sample_rate(srates):
    """Convert sample rate codes to Hz."""
    srates = np.array(srates, dtype=float)
    out = srates.copy()
    out[srates == 0] = 250
    out[srates == 1] = 500
    out[srates == 2] = 1000
    return out


def get_sample_rate_acc(srates):
    srates = np.array(srates, dtype=float)
    out = srates.copy()
    out[srates == 0] = 65.104
    out[srates == 1] = 32.552
    out[srates == 2] = 16.276
    out[srates == 3] = 8.138
    out[srates == 4] = 4.069
    out[srates == 255] = np.nan
    return out


def calculate_delta_system_tick(prev, nxt):
    return np.mod((nxt + (2**16) - prev), 2**16)


def create_time_domain_table(td_struct):
    td_data = td_struct["TimeDomainData"]
    srates = get_sample_rate([pkt["SampleRate"] for pkt in td_data])

    n_chans = [len(pkt["ChannelSamples"]) for pkt in td_data]
    data_sizes = [pkt["Header"]["dataSize"] for pkt in td_data]
    packet_sizes = [(ds / nc) / 2 for ds, nc in zip(data_sizes, n_chans)]

    nrows = int(sum(packet_sizes))
    cols = [
        "key0",
        "key1",
        "key2",
        "key3",
        "systemTick",
        "timestamp",
        "samplerate",
        "PacketGenTime",
        "PacketRxUnixTime",
        "packetsizes",
        "dataTypeSequence",
    ]
    out = np.full((nrows, len(cols)), np.nan)

    current_index = 0
    for p, pkt in enumerate(td_data):
        rowidx = slice(current_index, current_index + int(packet_sizes[p]))
        packetidx = current_index + int(packet_sizes[p]) - 1
        for sample in pkt["ChannelSamples"]:
            idx = sample["Key"]
            out[rowidx, idx] = sample["Value"]
        out[packetidx, 4] = pkt["Header"]["systemTick"]
        out[packetidx, 5] = pkt["Header"]["timestamp"]["seconds"]
        out[packetidx, 6] = srates[p]
        out[packetidx, 7] = pkt["PacketGenTime"]
        out[packetidx, 8] = pkt["PacketRxUnixTime"]
        out[packetidx, 9] = packet_sizes[p]
        out[packetidx, 10] = pkt["Header"]["dataTypeSequence"]
        current_index += int(packet_sizes[p])

    df = pd.DataFrame(out, columns=cols)
    return df, srates


def create_accel_table(accel_struct):
    accel_data = accel_struct["AccelData"]
    srates = get_sample_rate_acc([pkt["SampleRate"] for pkt in accel_data])

    data_sizes = [pkt["Header"]["dataSize"] for pkt in accel_data]
    packet_sizes = [ds / 8 for ds in data_sizes]
    nrows = int(sum(packet_sizes))

    cols = [
        "XSamples",
        "YSamples",
        "ZSamples",
        "systemTick",
        "timestamp",
        "samplerate",
        "PacketGenTime",
        "PacketRxUnixTime",
        "packetsizes",
        "dataTypeSequence",
    ]
    out = np.full((nrows, len(cols)), np.nan)

    current_index = 0
    for p, pkt in enumerate(accel_data):
        rowidx = slice(current_index, current_index + int(packet_sizes[p]))
        packetidx = current_index + int(packet_sizes[p]) - 1
        out[rowidx, 0] = pkt["XSamples"]
        out[rowidx, 1] = pkt["YSamples"]
        out[rowidx, 2] = pkt["ZSamples"]
        out[packetidx, 3] = pkt["Header"]["systemTick"]
        out[packetidx, 4] = pkt["Header"]["timestamp"]["seconds"]
        out[packetidx, 5] = srates[p]
        out[packetidx, 6] = pkt["PacketGenTime"]
        out[packetidx, 7] = pkt["PacketRxUnixTime"]
        out[packetidx, 8] = packet_sizes[p]
        out[packetidx, 9] = pkt["Header"]["dataTypeSequence"]
        current_index += int(packet_sizes[p])

    df = pd.DataFrame(out, columns=cols)
    return df, srates


def assign_time(dataframe, short_gaps_system_tick=0):
    """Port of ``assignTime.m`` for sample alignment.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Output from :func:`create_time_domain_table` or
        :func:`create_accel_table`.
    short_gaps_system_tick : int, optional
        Bridge gaps < 6 s with ``systemTick`` if non-zero.

    Returns
    -------
    pandas.DataFrame
        Copy with ``DerivedTime`` column and faulty samples removed.
    """
    df = dataframe.reset_index(drop=True)
    packet_idx = df.index[df["timestamp"].notna()].tolist()
    if not packet_idx:
        res = df.copy()
        res.insert(0, "DerivedTime", np.nan)
        return res

    pkt_tbl_orig = df.loc[packet_idx].reset_index(drop=True)

    # --------------------------------------------------------------
    # Packet rejection based on bad metadata
    # --------------------------------------------------------------
    median_ts = np.median(pkt_tbl_orig["timestamp"])
    day_secs = 24 * 60 * 60
    bad_date = pkt_tbl_orig.index[
        (pkt_tbl_orig["timestamp"] > median_ts + day_secs)
        | (pkt_tbl_orig["timestamp"] < median_ts - day_secs)
    ]
    neg_pg = pkt_tbl_orig.index[pkt_tbl_orig["PacketGenTime"] <= 0]
    start_idx = min(set(range(len(pkt_tbl_orig))) - set(neg_pg))
    elapsed_ts = (
        pkt_tbl_orig["timestamp"].iloc[start_idx:] -
        pkt_tbl_orig["timestamp"].iloc[start_idx]
    )
    elapsed_pg = (
        pkt_tbl_orig["PacketGenTime"].iloc[start_idx:] -
        pkt_tbl_orig["PacketGenTime"].iloc[start_idx]
    ) / 1000.0
    outlier_pg = start_idx + np.where(np.abs(elapsed_ts - elapsed_pg) > 2)[0]
    dup_first = np.intersect1d(
        np.where(np.diff(pkt_tbl_orig["dataTypeSequence"]) == 0)[0],
        np.where(np.diff(pkt_tbl_orig["systemTick"]) == 0)[0],
    )
    pg_diff = np.diff(pkt_tbl_orig["PacketGenTime"])
    back_idx = []
    for di in np.where(pg_diff < -500)[0]:
        if di + 1 < len(pkt_tbl_orig):
            back_idx.append(di + 1)
        if di + 2 < len(pkt_tbl_orig):
            back_idx.append(di + 2)
        ctr = 3
        while (
            ctr <= 6
            and di + ctr < len(pkt_tbl_orig)
            and pkt_tbl_orig["PacketGenTime"].iloc[di + ctr]
            < pkt_tbl_orig["PacketGenTime"].iloc[di]
        ):
            back_idx.append(di + ctr)
            ctr += 1
    packets_to_remove = sorted(
        set(bad_date).union(neg_pg).union(dup_first + 1)
        .union(back_idx).union(outlier_pg)
    )

    # Map packet removals to sample indices
    samples_remove = []
    if 0 in packets_to_remove:
        samples_remove.extend(range(0, packet_idx[0] + 1))
        packets_to_remove.remove(0)
    for p in packets_to_remove:
        start = packet_idx[p - 1] + 1
        stop = packet_idx[p]
        samples_remove.extend(range(start, stop + 1))

    df_clean = df.drop(samples_remove).reset_index(drop=True)
    packet_idx = df_clean.index[df_clean["timestamp"].notna()].tolist()
    pkt_tbl = df_clean.loc[packet_idx].reset_index(drop=True)

    # --------------------------------------------------------------
    # Identify data chunks based on breaks in metadata
    # --------------------------------------------------------------
    change_fs = pkt_tbl.index[1:][pkt_tbl["samplerate"].diff().iloc[1:] != 0]
    ts_diff = pkt_tbl["timestamp"].diff().iloc[1:]
    gap_ts = pkt_tbl.index[1:][(ts_diff != 0) & (ts_diff != 1)]
    dts_diff = pkt_tbl["dataTypeSequence"].diff().iloc[1:]
    gap_dts = pkt_tbl.index[1:][(dts_diff != 1) & (dts_diff != -255)]

    expected_elapsed = (
        pkt_tbl["packetsizes"] * (1 / pkt_tbl["samplerate"]) * 1e4
    )
    diff_sys = [np.nan]
    for i in range(1, len(pkt_tbl)):
        diff_sys.append(
            calculate_delta_system_tick(
                pkt_tbl["systemTick"].iloc[i - 1],
                pkt_tbl["systemTick"].iloc[i],
            )
        )
    diff_sys = np.array(diff_sys)
    cutoff = np.maximum(0.5 * expected_elapsed.values, 1000.0)
    gap_sys = np.where(
        np.abs(expected_elapsed.values[1:] - diff_sys[1:]) > cutoff[1:]
    )[0] + 1
    flagged = sorted(
        set(change_fs).union(gap_ts).union(gap_dts).union(gap_sys)
    )

    chunk_idx = []
    start = 0
    for idx in flagged:
        chunk_idx.append(list(range(start, idx + 1)))
        start = idx + 1
    chunk_idx.append(list(range(start, len(pkt_tbl))))

    # --------------------------------------------------------------
    # Determine corrected alignment time for each chunk
    # --------------------------------------------------------------
    diff_pg = np.concatenate(([1], np.diff(pkt_tbl["PacketGenTime"]) * 10))
    med_err = []
    for ci in chunk_idx:
        if len(ci) > 1:
            err = expected_elapsed.values[ci][1:] - diff_pg[ci][1:]
            med_err.append(np.median(err))
        else:
            med_err.append(0.0)

    chunks_prev = []
    elapsed_sys = np.zeros(len(chunk_idx) - 1)
    if short_gaps_system_tick and len(chunk_idx) > 1:
        idx_first = [c[0] for c in chunk_idx]
        idx_last = [c[-1] for c in chunk_idx]
        ts_first = pkt_tbl["timestamp"].iloc[idx_first]
        ts_last = pkt_tbl["timestamp"].iloc[idx_last]
        ts_gaps = ts_first.iloc[1:].values - ts_last.iloc[:-1].values
        for i, g in enumerate(ts_gaps):
            if g < 6 and idx_last[i] not in change_fs:
                chunks_prev.append(i + 1)
                elapsed_sys[i] = calculate_delta_system_tick(
                    pkt_tbl["systemTick"].iloc[idx_last[i]],
                    pkt_tbl["systemTick"].iloc[idx_first[i + 1]],
                )

    corr_align = []
    for i, ci in enumerate(chunk_idx):
        if short_gaps_system_tick and i in chunks_prev:
            fs_prev = pkt_tbl["samplerate"].iloc[chunk_idx[i - 1][0]]
            sizes_prev = pkt_tbl["packetsizes"].iloc[chunk_idx[i - 1]]
            other_time = np.sum(sizes_prev.iloc[1:]) * (1000 / fs_prev)
            corr_align.append(
                corr_align[-1] + elapsed_sys[i - 1] * 0.1 + other_time
            )
        else:
            align_time = pkt_tbl["PacketGenTime"].iloc[ci[0]]
            corr_align.append(align_time + med_err[i] * 0.1)

    max_fs = pkt_tbl["samplerate"].max()
    delta = (1 / max_fs) * 1000
    multiples = np.floor(
        ((np.array(corr_align) - corr_align[0]) / delta) + 0.5
    )
    corr_shift = corr_align[0] + multiples * delta

    # --------------------------------------------------------------
    # Generate DerivedTime for every sample in the cleaned table
    # --------------------------------------------------------------
    derived = np.full(len(df_clean), np.nan)
    sample_pkt_idx = df_clean["timestamp"].dropna().index
    for idx, ci in enumerate(chunk_idx):
        pkt_start = sample_pkt_idx[ci[0]]
        samp_start = 0 if ci[0] == 0 else sample_pkt_idx[ci[0] - 1] + 1
        samp_end = sample_pkt_idx[ci[-1]]
        fs = df_clean["samplerate"].iloc[pkt_start]
        before = (pkt_start - samp_start) * (1000 / fs)
        times = corr_shift[idx] - before + np.arange(
            samp_end - samp_start + 1
        ) * (1000 / fs)
        derived[samp_start:samp_end + 1] = times

    result = df_clean.copy()
    result.insert(0, "DerivedTime", derived)

    # Remove duplicates and NaNs
    bad_rows = np.where(np.isnan(result["DerivedTime"]))[0].tolist()
    dup = result["DerivedTime"].diff().fillna(1) <= 0
    bad_rows.extend(result.index[dup].tolist())
    result.drop(bad_rows, inplace=True)
    cols = [
        "DerivedTime",
        "timestamp",
        "systemTick",
        "PacketGenTime",
        "PacketRxUnixTime",
        "dataTypeSequence",
        "samplerate",
        "packetsizes",
    ] + [c for c in result.columns if c not in {
        "DerivedTime",
        "timestamp",
        "systemTick",
        "PacketGenTime",
        "PacketRxUnixTime",
        "dataTypeSequence",
        "samplerate",
        "packetsizes",
    }]
    result = result[cols].reset_index(drop=True)
    return result
