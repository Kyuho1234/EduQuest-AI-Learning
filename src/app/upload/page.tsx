'use client';

import { useState } from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  Button,
  Paper, 
  CircularProgress,
  Alert
} from '@mui/material';
import { CloudUpload as CloudUploadIcon } from '@mui/icons-material';
import axios from 'axios';
import { useRouter } from 'next/navigation';

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === 'application/pdf') {
        setFile(selectedFile);
        setError(null);
      } else {
        setFile(null);
        setError('PDF 파일만 업로드 가능합니다.');
      }
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('업로드할 파일을 선택해주세요.');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      // API 요청 설정
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/upload-pdf`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          }
        },
      });

      if (response.data && response.data.success) {
        // 업로드 성공 후 생성 페이지로 이동
        localStorage.setItem('documentContent', response.data.text);
        localStorage.setItem('documentPageCount', response.data.page_count.toString());
        router.push('/generate');
      } else {
        setError('파일 업로드 중 오류가 발생했습니다.');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError('파일 업로드 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 8, mb: 8 }}>
        <Typography variant="h4" component="h1" align="center" gutterBottom>
          학습 자료 업로드
        </Typography>
        <Typography variant="body1" align="center" color="textSecondary" paragraph>
          PDF 문서를 업로드하면 AI가 자동으로 학습 문제를 생성합니다.
        </Typography>

        <Paper 
          elevation={3} 
          sx={{ 
            p: 4, 
            mt: 4, 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center',
            backgroundColor: '#f8f9fa',
            borderRadius: 2
          }}
        >
          <input
            accept="application/pdf"
            style={{ display: 'none' }}
            id="raised-button-file"
            type="file"
            onChange={handleFileChange}
            disabled={loading}
          />
          <label htmlFor="raised-button-file">
            <Button
              variant="outlined"
              component="span"
              startIcon={<CloudUploadIcon />}
              disabled={loading}
              sx={{ 
                mb: 2,
                borderColor: '#2196f3',
                color: '#2196f3',
                '&:hover': {
                  borderColor: '#1976d2',
                  backgroundColor: 'rgba(33, 150, 243, 0.04)',
                }
              }}
            >
              PDF 파일 선택
            </Button>
          </label>

          {file && (
            <Typography variant="body2" sx={{ mb: 2 }}>
              선택된 파일: {file.name}
            </Typography>
          )}

          {error && (
            <Alert severity="error" sx={{ mb: 2, width: '100%' }}>
              {error}
            </Alert>
          )}

          {loading && (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mt: 2, mb: 2 }}>
              <CircularProgress variant="determinate" value={uploadProgress} />
              <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                {uploadProgress}% 업로드 중...
              </Typography>
            </Box>
          )}

          <Button
            variant="contained"
            color="primary"
            onClick={handleUpload}
            disabled={!file || loading}
            sx={{ 
              mt: 2,
              background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
              boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
              '&:hover': {
                background: 'linear-gradient(45deg, #1976d2 30%, #00a5cf 90%)',
              }
            }}
          >
            {loading ? '처리 중...' : '업로드 및 문제 생성'}
          </Button>
        </Paper>
      </Box>
    </Container>
  );
}