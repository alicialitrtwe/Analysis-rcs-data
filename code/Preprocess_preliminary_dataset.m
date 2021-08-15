clear all
inDataFolder = '/home/jlg/litrtwe/projects/dbs/data/retrospective_dataset_anonymized/';
outDataFolder = '/home/jlg/litrtwe/projects/dbs/data_preproc';
dataFolderContent = dir(fullfile(inDataFolder,'*'));
subfolders = setdiff({dataFolderContent([dataFolderContent.isdir]).name}, {'.','..'});

for ii = 3
    
    subfolderContent = dir(fullfile(inDataFolder, subfolders{ii},'*'));
    inFileFolders = setdiff({subfolderContent([subfolderContent.isdir]).name}, {'.','..'});
    inFilePaths = fullfile(inDataFolder, subfolders{ii}, inFileFolders);
    for jj = 1:numel(inFilePaths)
        infilePath = inFilePaths{jj};
        outFilename = ['table_', subfolders{ii}, '_', inFileFolders{jj}(1:end-11)];
        outputFileName = fullfile(outDataFolder, outFilename);
        ProcessRCS(infilePath, outputFileName);
        
    end
end

%ProcessRCS(inFileFolder, outFile);