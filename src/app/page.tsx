'use client';

import { useState } from 'react';
import { Button, Container, Typography, Box, Paper } from '@mui/material';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleStartLearning = () => {
    setLoading(true);
    router.push('/upload');
  };

  return (
    <Container maxWidth="lg">
      <Box
        sx={{
          mt: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          minHeight: '80vh',
          justifyContent: 'center',
        }}
      >
        <Paper 
          elevation={3} 
          sx={{ 
            p: 5, 
            borderRadius: 2, 
            maxWidth: 800, 
            width: '100%',
            background: 'linear-gradient(145deg, #ffffff, #f0f7ff)'
          }}
        >
          <Typography 
            variant="h2" 
            component="h1" 
            align="center" 
            gutterBottom
            sx={{ 
              fontWeight: 700,
              background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}
          >
            EduQuest
          </Typography>
          
          <Typography variant="h5" align="center" color="textSecondary" paragraph sx={{ mb: 4 }}>
            인공지능 기반 맞춤형 학습 플랫폼
          </Typography>
          
          <Typography variant="body1" paragraph>
            EduQuest는 인공지능을 활용한 교육용 문제 생성 및 학습 지원 시스템입니다. 
            텍스트나 PDF 문서를 업로드하면 AI가 자동으로 문제를 생성하고, 
            학습자의 이해도를 평가하며 개인화된 피드백을 제공합니다.
          </Typography>
          
          <Typography variant="body1" paragraph sx={{ mb: 4 }}>
            RAG(Retrieval-Augmented Generation) 기술을 활용하여 생성된 문제가 
            원본 자료와 일치하는지 검증하고, 할루시네이션을 방지하여 
            정확하고 신뢰할 수 있는 학습 경험을 제공합니다.
          </Typography>
          
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <Button 
              variant="contained" 
              size="large" 
              onClick={handleStartLearning}
              disabled={loading}
              sx={{ 
                py: 1.5, 
                px: 4, 
                borderRadius: 2,
                background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                '&:hover': {
                  background: 'linear-gradient(45deg, #1e88e5 30%, #1bb8e5 90%)',
                }
              }}
            >
              {loading ? '로딩 중...' : '학습 시작하기'}
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}