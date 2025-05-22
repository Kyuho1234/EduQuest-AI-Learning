'use client';

import { useState, useEffect } from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  Button, 
  Paper, 
  TextField, 
  CircularProgress, 
  Grid,
  Card,
  CardContent,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert
} from '@mui/material';
import { Quiz as QuizIcon } from '@mui/icons-material';
import axios from 'axios';
import { useRouter } from 'next/navigation';

type Question = {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  question_type: string;
  verification?: {
    total_score: number;
  };
};

export default function GeneratePage() {
  const router = useRouter();
  const [documentContent, setDocumentContent] = useState<string>('');
  const [numQuestions, setNumQuestions] = useState<number>(5);
  const [questionTypes, setQuestionTypes] = useState<string[]>(['multiple_choice', 'short_answer']);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedQuestions, setGeneratedQuestions] = useState<Question[]>([]);
  
  useEffect(() => {
    // 브라우저에서만 실행
    if (typeof window !== 'undefined') {
      const content = localStorage.getItem('documentContent');
      if (!content) {
        router.push('/upload');
      } else {
        setDocumentContent(content);
      }
    }
  }, [router]);

  const handleNumQuestionsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    if (value > 0 && value <= 10) {
      setNumQuestions(value);
    }
  };

  const handleQuestionTypeChange = (e: any) => {
    setQuestionTypes(e.target.value);
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/generate-questions`, {
        content: documentContent,
        num_questions: numQuestions,
        question_types: questionTypes
      });
      
      if (response.data && response.data.questions) {
        setGeneratedQuestions(response.data.questions);
        // 로컬 스토리지에 문제 저장
        localStorage.setItem('generatedQuestions', JSON.stringify(response.data.questions));
      } else {
        setError('문제 생성에 실패했습니다.');
      }
    } catch (err) {
      console.error('Generation error:', err);
      setError('문제 생성 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartQuiz = () => {
    router.push('/quiz');
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 8, mb: 8 }}>
        <Typography variant="h4" component="h1" align="center" gutterBottom>
          학습 문제 생성
        </Typography>
        
        <Paper elevation={3} sx={{ p: 4, mt: 4, borderRadius: 2 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                문서 내용 미리보기
              </Typography>
              <Paper 
                variant="outlined" 
                sx={{ 
                  p: 2, 
                  maxHeight: 300, 
                  overflow: 'auto',
                  backgroundColor: '#f5f5f5',
                  borderRadius: 1
                }}
              >
                <Typography variant="body2">
                  {documentContent.slice(0, 1000)}
                  {documentContent.length > 1000 && '...'}
                </Typography>
              </Paper>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                생성 설정
              </Typography>
              <Box sx={{ mb: 3 }}>
                <TextField
                  label="문제 개수"
                  type="number"
                  fullWidth
                  value={numQuestions}
                  onChange={handleNumQuestionsChange}
                  InputProps={{ inputProps: { min: 1, max: 10 } }}
                  helperText="1-10 사이의 숫자를 입력하세요"
                  sx={{ mb: 2 }}
                />
                
                <FormControl fullWidth>
                  <InputLabel>문제 유형</InputLabel>
                  <Select
                    multiple
                    value={questionTypes}
                    onChange={handleQuestionTypeChange}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {(selected as string[]).map((value) => (
                          <Chip 
                            key={value} 
                            label={value === 'multiple_choice' ? '객관식' : '주관식'} 
                            size="small"
                          />
                        ))}
                      </Box>
                    )}
                  >
                    <MenuItem value="multiple_choice">객관식</MenuItem>
                    <MenuItem value="short_answer">주관식</MenuItem>
                  </Select>
                </FormControl>
              </Box>
              
              <Button
                variant="contained"
                color="primary"
                fullWidth
                onClick={handleGenerate}
                disabled={loading}
                startIcon={<QuizIcon />}
                sx={{ 
                  py: 1.5,
                  background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                  boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                }}
              >
                {loading ? <CircularProgress size={24} color="inherit" /> : '문제 생성하기'}
              </Button>
            </Grid>
          </Grid>
          
          {error && (
            <Alert severity="error" sx={{ mt: 3 }}>
              {error}
            </Alert>
          )}
          
          {generatedQuestions.length > 0 && (
            <Box sx={{ mt: 4 }}>
              <Divider sx={{ mb: 3 }} />
              <Typography variant="h5" gutterBottom>
                생성된 문제 ({generatedQuestions.length}개)
              </Typography>
              
              <Grid container spacing={3}>
                {generatedQuestions.map((q, index) => (
                  <Grid item xs={12} key={index}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          문제 {index + 1}. {q.question_type === 'multiple_choice' ? '[객관식]' : '[주관식]'}
                        </Typography>
                        <Typography variant="body1" paragraph>
                          {q.question}
                        </Typography>
                        
                        {q.question_type === 'multiple_choice' && (
                          <Box sx={{ ml: 2 }}>
                            {q.options.map((option, i) => (
                              <Typography 
                                key={i} 
                                variant="body2" 
                                sx={{ 
                                  mb: 0.5,
                                  color: option === q.correct_answer ? 'success.main' : 'inherit',
                                  fontWeight: option === q.correct_answer ? 'bold' : 'normal'
                                }}
                              >
                                {i + 1}. {option}
                              </Typography>
                            ))}
                          </Box>
                        )}
                        
                        <Typography variant="body2" sx={{ mt: 1, color: 'success.main', fontWeight: 'bold' }}>
                          정답: {q.correct_answer}
                        </Typography>
                        
                        <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary', fontStyle: 'italic' }}>
                          {q.explanation}
                        </Typography>
                        
                        {q.verification && (
                          <Box sx={{ mt: 2, display: 'flex', alignItems: 'center' }}>
                            <Chip
                              label={`신뢰도: ${Math.round(q.verification.total_score * 100)}%`}
                              color={q.verification.total_score > 0.7 ? 'success' : 'warning'}
                              size="small"
                            />
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
              
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                <Button 
                  variant="contained" 
                  color="secondary" 
                  size="large"
                  onClick={handleStartQuiz}
                  sx={{ 
                    py: 1.5, 
                    px: 4,
                    background: 'linear-gradient(45deg, #FF4081 30%, #FF80AB 90%)',
                    boxShadow: '0 3px 5px 2px rgba(255, 105, 135, .3)',
                  }}
                >
                  퀴즈 시작하기
                </Button>
              </Box>
            </Box>
          )}
        </Paper>
      </Box>
    </Container>
  );
}