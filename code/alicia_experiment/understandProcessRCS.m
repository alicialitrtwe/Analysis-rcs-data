processFlag = 1;
shortGaps_systemTick = 0;
folderPath  = '/home/jlg/litrtwe/projects/Analysis-rcs-data/testDataSets/Benchtop/Simultaneous_RCS_and_DAQ/250Hz/DeviceNPC700378H';


disp('Collecting Device Settings data')
DeviceSettings_fileToLoad = [folderPath filesep 'DeviceSettings.json'];
if isfile(DeviceSettings_fileToLoad)
    [timeDomainSettings, powerSettings, fftSettings, metaData] = createDeviceSettingsTable(folderPath);
else
    error('No DeviceSettings.json file')
end



%%
% Stimulation settings
disp('Collecting Stimulation Settings from Device Settings file')
if isfile(DeviceSettings_fileToLoad)
    [stimSettingsOut, stimMetaData] = createStimSettingsFromDeviceSettings(folderPath);
else
    warning('No DeviceSettings.json file - could not extract stimulation settings')
end

disp('Collecting Stimulation Settings from Stim Log file')
StimLog_fileToLoad = [folderPath filesep 'StimLog.json'];
if isfile(StimLog_fileToLoad)
    [stimLogSettings] = createStimSettingsTable(folderPath,stimMetaData);
else
    warning('No StimLog.json file')
end
%%
% Adaptive Settings
disp('Collecting Adaptive Settings from Device Settings file')
if isfile(DeviceSettings_fileToLoad)
    [DetectorSettings,AdaptiveStimSettings,AdaptiveEmbeddedRuns_StimSettings] = createAdaptiveSettingsfromDeviceSettings(folderPath);
else
    error('No DeviceSettings.json file - could not extract detector and adaptive stimulation settings')
end
%%
% Event Log
disp('Collecting Event Information from Event Log file')
EventLog_fileToLoad = [folderPath filesep 'EventLog.json'];
if isfile(EventLog_fileToLoad)
    [eventLogTable] = createEventLogTable(folderPath);
else
    warning('No EventLog.json file')
end
    