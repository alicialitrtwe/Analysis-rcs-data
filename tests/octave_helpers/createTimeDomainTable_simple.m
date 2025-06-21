function [out, srates] = createTimeDomainTable_simple(td_struct)
  data = td_struct.TimeDomainData;
  srates = getSampleRate([data.SampleRate]');
  n_packets = numel(data);
  packet_sizes = zeros(n_packets,1);
  for p = 1:n_packets
    n_chans = numel(data(p).ChannelSamples);
    packet_sizes(p) = data(p).Header.dataSize/(n_chans*2);
  end
  nrows = sum(packet_sizes);
  out = NaN(nrows,11);
  current_index = 0;
  for p = 1:n_packets
    rowidx = current_index + (1:packet_sizes(p));
    packetidx = current_index + packet_sizes(p);
    samples = data(p).ChannelSamples;
    for s = 1:numel(samples)
      out(rowidx, samples(s).Key+1) = samples(s).Value;
    end
    out(packetidx,5) = data(p).Header.systemTick;
    out(packetidx,6) = data(p).Header.timestamp.seconds;
    out(packetidx,7) = srates(p);
    out(packetidx,8) = data(p).PacketGenTime;
    out(packetidx,9) = data(p).PacketRxUnixTime;
    out(packetidx,10)= packet_sizes(p);
    out(packetidx,11)= data(p).Header.dataTypeSequence;
    current_index = current_index + packet_sizes(p);
  end
end
