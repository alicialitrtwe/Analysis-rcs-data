function [out, srates] = createAccelTable_simple(acc_struct)
  data = acc_struct.AccelData;
  srates = getSampleRateAcc([data.SampleRate]');
  n_packets = numel(data);
  packet_sizes = zeros(n_packets,1);
  for p=1:n_packets
    packet_sizes(p) = data(p).Header.dataSize/8;
  end
  nrows = sum(packet_sizes);
  out = NaN(nrows,10);
  current_index = 0;
  for p=1:n_packets
    rowidx = current_index + (1:packet_sizes(p));
    packetidx = current_index + packet_sizes(p);
    out(rowidx,1) = data(p).XSamples;
    out(rowidx,2) = data(p).YSamples;
    out(rowidx,3) = data(p).ZSamples;
    out(packetidx,4) = data(p).Header.systemTick;
    out(packetidx,5) = data(p).Header.timestamp.seconds;
    out(packetidx,6) = srates(p);
    out(packetidx,7) = data(p).PacketGenTime;
    out(packetidx,8) = data(p).PacketRxUnixTime;
    out(packetidx,9) = packet_sizes(p);
    out(packetidx,10)= data(p).Header.dataTypeSequence;
    current_index = current_index + packet_sizes(p);
  end
end
