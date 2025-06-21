function out = assignTime_octave(mat, shortGaps)
  % Octave version of assignTime operating on matrices.
  if nargin < 2
    shortGaps = 0;
  end
  pkt_idx = find(~isnan(mat(:,6)));
  if isempty(pkt_idx)
    out = [NaN(size(mat,1),1), mat];
    return;
  end
  pkt = mat(pkt_idx,:);

  %% Packet rejection
  medianTs = median(pkt(:,6));
  daySecs = 24*60*60;
  badDate = find(
    pkt(:,6) > medianTs + daySecs | pkt(:,6) < medianTs - daySecs
  );
  negPG = find(pkt(:,8) <= 0);
  tempStart = min(setdiff(1:size(pkt,1), negPG));
  elapsed_ts = pkt(tempStart:end,6) - pkt(tempStart,6);
  elapsed_pg = (pkt(tempStart:end,8) - pkt(tempStart,8))/1000;
  outlier_pg = tempStart-1 + find(abs(elapsed_ts - elapsed_pg) > 2);
  dup_first = intersect(find(diff(pkt(:,11))==0), find(diff(pkt(:,5))==0));
  pg_diff = diff(pkt(:,8));
  back_idx = [];
  for di = find(pg_diff < -500)'
    if di+1 <= size(pkt,1), back_idx(end+1)=di+1; end
    if di+2 <= size(pkt,1), back_idx(end+1)=di+2; end
    ctr = 3;
    while ctr<=6 && di+ctr<=size(pkt,1) && pkt(di+ctr,8) < pkt(di,8)
      back_idx(end+1) = di+ctr;
      ctr = ctr+1;
    end
  end
  remove_idx = unique([
    badDate(:); negPG(:); dup_first(:)+1; back_idx(:); outlier_pg(:)
  ]);
  keep_idx = setdiff(1:size(pkt,1), remove_idx);
  pkt = pkt(keep_idx,:);
  pkt_idx = pkt_idx(keep_idx);

  %% Chunk detection
  changeFs = find(diff(pkt(:,7)) ~= 0) + 1;
  ts_diff = diff(pkt(:,6));
  gap_ts = find(ts_diff ~= 0 & ts_diff ~= 1) + 1;
  dts_diff = diff(pkt(:,11));
  gap_dts = find(dts_diff ~= 1 & dts_diff ~= -255) + 1;
  expectedElapsed = pkt(:,10) .* (1./pkt(:,7)) * 1e4;
  sys_diff = [NaN; mod(pkt(2:end,5) + 2^16 - pkt(1:end-1,5), 2^16)];
  cutoff = max([0.5*expectedElapsed, ones(size(expectedElapsed))*1000], [], 2);
  gap_sys = find(
    abs(expectedElapsed(2:end) - sys_diff(2:end)) > cutoff(2:end)
  ) + 1;
  flagged = unique([changeFs; gap_ts; gap_dts; gap_sys]);
  chunkIdx = {};
  start = 1;
  for k = 1:numel(flagged)
    chunkIdx{end+1} = start:flagged(k);
    start = flagged(k)+1;
  end
  chunkIdx{end+1} = start:size(pkt,1);

  %% Median error per chunk
  diff_pg = [1; diff(pkt(:,8))*10];
  medErr = zeros(1, numel(chunkIdx));
  for i = 1:numel(chunkIdx)
    ci = chunkIdx{i};
    if numel(ci) > 1
      err = expectedElapsed(ci(2:end)) - diff_pg(ci(2:end));
      medErr(i) = median(err);
    end
  end

  %% Handle short gaps using systemTick
  chunksPrev = [];
  elapsed_sys = zeros(1, numel(chunkIdx)-1);
  if shortGaps && numel(chunkIdx) > 1
    idx_first = cellfun(@(x)x(1), chunkIdx);
    idx_last = cellfun(@(x)x(end), chunkIdx);
    ts_first = pkt(idx_first,6);
    ts_last = pkt(idx_last,6);
    ts_gaps = ts_first(2:end) - ts_last(1:end-1);
    for i = 1:numel(ts_gaps)
      if ts_gaps(i) < 6 && ~ismember(idx_last(i), changeFs)
        chunksPrev(end+1) = i+1;
        elapsed_sys(i) = mod(
          pkt(idx_first(i+1),5) + 2^16 - pkt(idx_last(i),5), 2^16
        );
      end
    end
  end

  %% Corrected alignment time
  corrAlign = zeros(1, numel(chunkIdx));
  for i = 1:numel(chunkIdx)
    if shortGaps && ismember(i, chunksPrev)
      fs_prev = pkt(chunkIdx{i-1}(1),7);
      sizes_prev = pkt(chunkIdx{i-1},10);
      other_time = sum(sizes_prev(2:end)) * (1000/fs_prev);
      corrAlign(i) = corrAlign(i-1) + elapsed_sys(i-1)*0.1 + other_time;
    else
      corrAlign(i) = pkt(chunkIdx{i}(1),8) + medErr(i)*0.1;
    end
  end
  maxFs = max(pkt(:,7));
  delta = 1/maxFs*1000;
  corrShift = corrAlign(1) + ...
      floor(((corrAlign - corrAlign(1))/delta)+0.5) .* delta;

  %% Assign DerivedTime
  Derived = NaN(size(mat,1),1);
  for i = 1:numel(chunkIdx)
    ci = chunkIdx{i};
    pk_start = pkt_idx(ci(1));
    if ci(1) == 1
      samp_start = 1;
    else
      samp_start = pkt_idx(ci(1)-1)+1;
    end
    samp_end = pkt_idx(ci(end));
    fs = mat(pk_start,7);
    elapsed_before = (pk_start - samp_start) * (1000/fs);
    times = corrShift(i) - elapsed_before + ...
      (0:(samp_end - samp_start))' * (1000/fs);
    Derived(samp_start:samp_end) = times;
  end

  out = [Derived mat];
  % Remove invalid rows
  keep = ~isnan(out(:,1));
  dup = diff(out(:,1)) <= 0;
  keep(2:end) = keep(2:end) & ~dup;
  out = out(keep,:);
end
