clear all
inDataFolder = '/home/jlg/litrtwe/projects/dbs/data/retrospective_dataset_anonymized/';
outDataFolder = '/home/jlg/litrtwe/projects/dbs/data_preproc/retrospective_dataset_TimeDomainData';

shortGaps_systemTick = 0;

dataFolderContent = dir(fullfile(inDataFolder,'*'));
subfolders = setdiff({dataFolderContent([dataFolderContent.isdir]).name}, {'.','..'});

for ii = 1:numel(subfolders)
    
    subfolderContent = dir(fullfile(inDataFolder, subfolders{ii},'*'));
    inFileFolders = setdiff({subfolderContent([subfolderContent.isdir]).name}, {'.','..'});
    inFilePaths = fullfile(inDataFolder, subfolders{ii}, inFileFolders);
    for jj = 1:numel(inFilePaths)
        infilePath = inFilePaths{jj};
        
        TD_fileToLoad = [infilePath filesep 'RawDataTD.json'];
        if isfile(TD_fileToLoad)
            jsonobj_TD = deserializeJSON(TD_fileToLoad);
            if isfield(jsonobj_TD,'TimeDomainData') && ~isempty(jsonobj_TD.TimeDomainData)
                disp('Loading Time Domain Data')
                [outtable_TD, srates_TD] = createTimeDomainTable(jsonobj_TD);
                disp('Creating derivedTimes for time domain:')
                timeDomainData = assignTime(outtable_TD, shortGaps_systemTick);
                outFilename = ['TimeDomainData_', subfolders{ii}, '_', inFileFolders{jj}(1:end-11), '.csv'];
                outputFileName = fullfile(outDataFolder, outFilename);
                writetable(timeDomainData, outputFileName);
                %ProcessRCS(infilePath, outputFileName);
            else
                disp('problem loading time domain data')
                break
            end
        end

        
    end
end

%ProcessRCS(inFileFolder, outFile);