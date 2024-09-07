import React from 'react';
import styled from 'styled-components';
import axios from 'axios';
import { useHistory } from 'react-router-dom';

const Container = styled.div`
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
`;

const UploadButton = styled.input`
    padding: 10px 20px;
    font-size: 16px;
    cursor: pointer;
`;

const UploadLanding: React.FC = () => {
    const history = useHistory();

    const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file && file.type === 'application/pdf') {
            console.log('PDF file selected:', file);
            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await axios.post('/api/upload_pdf', formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                });
                const { sha } = response.data;
                history.push(`/pdf:${sha}`);
            } catch (error) {
                console.error('Error uploading file:', error);
                alert('Failed to upload the file. Please try again.');
            }
        } else {
            alert('Please upload a valid PDF file.');
        }
    };

    return (
        <Container>
            <h1>Upload a PDF</h1>
            <UploadButton type="file" accept="application/pdf" onChange={handleUpload} />
        </Container>
    );
};

export default UploadLanding;
