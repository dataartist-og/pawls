import React from 'react';
import { FileManagerComponent, Inject, NavigationPane, DetailsView, Toolbar } from '@syncfusion/ej2-react-filemanager';
import '@syncfusion/ej2-base/styles/material.css';
import '@syncfusion/ej2-react-filemanager/styles/material.css';

interface FileSystemProps {
    rootPath: string;
}

const FileSystem: React.FC<FileSystemProps> = ({ rootPath }) => {
    const hostUrl = "https://ej2-aspcore-service.azurewebsites.net/";

    const fileManagerConfig = {
        ajaxSettings: {
            url: hostUrl + "api/FileManager/FileOperations",
            getImageUrl: hostUrl + "api/FileManager/GetImage",
            uploadUrl: hostUrl + "api/FileManager/Upload",
            downloadUrl: hostUrl + "api/FileManager/Download"
        },
        view: "Details",
        allowMultiSelection: false,
        toolbarSettings: { items: ['NewFolder', 'Upload', 'Delete', 'Download', 'Refresh', 'View', 'Details'] },
        contextMenuSettings: { file: ['Open', 'Download', 'Delete'], folder: ['Open', 'Delete'] },
    };

    const onFileSelect = (args: any) => {
        if (args.fileDetails.isFile && args.fileDetails.type === '.pdf') {
            // Call your upload_pdf API method here
            console.log('PDF selected:', args.fileDetails.name);
            // Implement your API call to upload the PDF
        }
    };

    return (
        <div className="control-section">
            <FileManagerComponent 
                id="filemanager"
                {...fileManagerConfig}
                rootAliasName={rootPath}
                fileSelect={onFileSelect}
            >
                <Inject services={[NavigationPane, DetailsView, Toolbar]} />
            </FileManagerComponent>
        </div>
    );
};

export default FileSystem;
