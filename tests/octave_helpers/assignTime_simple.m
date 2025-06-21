function out = assignTime_simple(mat)
  timestamp = mat(:,6);
  idx = find(~isnan(timestamp));
  mat = mat(idx,:);
  if isempty(mat)
    out = [];
    return;
  end
  Fs = mat(1,7);
  startt = mat(1,8);
  n = size(mat,1);
  derived = startt + (0:n-1)'*(1000/Fs);
  out = [derived mat];
end
