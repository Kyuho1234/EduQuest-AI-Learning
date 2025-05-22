'use client';

import { useState, useEffect } from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  Button, 
  Paper, 
  RadioGroup,
  FormControlLabel,
  Radio,
  TextField,
  Card,
  CardContent,
  Divider,
  CircularProgress,
  Grid,
  Alert,
  Stepper,
  Step,
  StepLabel
} from '@mui/material';
import { Check as CheckIcon, Close as CloseIcon } from '@mui/icons-material';
import axios from 'axios';
import { useRouter } from 'next/navigation';

type Question = {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  question_type: string;
};

type AnswerResult = {
  question: string;
  user_answer: string;
  correct_answer: string;
  is_correct: boolean;
  score: number;
  feedback: string;
};

export default function QuizPage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<{[key: number]: string}>({});
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState<{
    answers: AnswerResult[];
    total_score: number;
    total_questions: number;
    percentage: number;
    overall_feedback: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // 브라우저에서만 실행
    if (typeof window !== 'undefined') {
      const storedQuestions = localStorage.getItem('generatedQuestions');
      if (!storedQuestions) {
        router.push('/generate');
      } else {
        setQuestions(JSON.parse(storedQuestions));
      }
    }
  }, [router]);

  const handleAnswer = (answer: string) => {
    setAnswers({ ...answers, [currentQuestionIndex]: answer });
  };

  const goToNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  const goToPreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  const submitQuiz = async () => {
    // 모든 문제에 답변했는지 확인
    const answeredQuestions = Object.keys(answers).length;
    if (answeredQuestions < questions.length) {
      setError(`아직 ${questions.length - answeredQuestions}개의 문제에 답변하지 않았습니다.`);
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      // 답변 데이터 준비
      const answersData = questions.map((q, index) => ({
        question: q.question,
        user_answer: answers[index] || '',
        correct_answer: q.correct_answer,
        question_type: q.question_type
      }));
      
      // API 요청
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/check-answers`, {
        answers: answersData
      });
      
      if (response.data) {
        setResults(response.data);
        setShowResults(true);
      } else {
        setError('답안 채점 중 오류가 발생했습니다.');
      }
    } catch (err) {
      console.error('Submit error:', err);
      setError('답안 제출 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    setAnswers({});
    setCurrentQuestionIndex(0);
    setShowResults(false);
    setResults(null);
  };

  const handleNewQuiz = () => {
    localStorage.removeItem('generatedQuestions');
    router.push('/upload');
  };

  if (questions.length === 0) {
    return (
      <Container maxWidth="md">
        <Box sx={{ mt: 8, textAlign: 'center' }}>
          <CircularProgress />
          <Typography variant="h6" sx={{ mt: 2 }}>문제를 불러오는 중입니다...</Typography>
        </Box>
      </Container>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 8, mb: 8 }}>
        {!showResults ? (
          <>
            <Box sx={{ mb: 4 }}>
              <Stepper 
                activeStep={currentQuestionIndex}
                alternativeLabel
                sx={{ 
                  overflowX: 'auto',
                  '& .MuiStepConnector-line': {
                    minWidth: '24px'
                  }
                }}
              >
                {questions.map((_, index) => (
                  <Step key={index} completed={answers[index] !== undefined}>
                    <StepLabel>{index + 1}</StepLabel>
                  </Step>
                ))}
              </Stepper>
            </Box>

            <Paper elevation={3} sx={{ p: 4, borderRadius: 2 }}>
              <Typography variant="h5" gutterBottom>
                문제 {currentQuestionIndex + 1} / {questions.length}
              </Typography>
              
              <Card variant="outlined" sx={{ mb: 4, bgcolor: '#f8f9fa', p: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {currentQuestion.question}
                  </Typography>
                  
                  {currentQuestion.question_type === 'multiple_choice' ? (
                    <RadioGroup
                      value={answers[currentQuestionIndex] || ''}
                      onChange={(e) => handleAnswer(e.target.value)}
                    >
                      {currentQuestion.options.map((option, index) => (
                        <FormControlLabel
                          key={index}
                          value={option}
                          control={<Radio />}
                          label={option}
                          sx={{ mb: 1 }}
                        />
                      ))}
                    </RadioGroup>
                  ) : (
                    <TextField
                      fullWidth
                      label="답변 입력"
                      variant="outlined"
                      value={answers[currentQuestionIndex] || ''}
                      onChange={(e) => handleAnswer(e.target.value)}
                      sx={{ mt: 2 }}
                    />
                  )}
                </CardContent>
              </Card>
              
              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
                <Button
                  variant="outlined"
                  onClick={goToPreviousQuestion}
                  disabled={currentQuestionIndex === 0}
                >
                  이전 문제
                </Button>
                
                <Box>
                  {currentQuestionIndex === questions.length - 1 ? (
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={submitQuiz}
                      disabled={loading}
                      sx={{ 
                        background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                        boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                      }}
                    >
                      {loading ? <CircularProgress size={24} color="inherit" /> : '제출하기'}
                    </Button>
                  ) : (
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={goToNextQuestion}
                      sx={{ 
                        background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                        boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                      }}
                    >
                      다음 문제
                    </Button>
                  )}
                </Box>
              </Box>
            </Paper>
          </>
        ) : (
          <Paper elevation={3} sx={{ p: 4, borderRadius: 2 }}>
            <Typography variant="h4" gutterBottom align="center">
              퀴즈 결과
            </Typography>
            
            <Box sx={{ my: 3, textAlign: 'center' }}>
              <Typography variant="h5" gutterBottom color="primary">
                점수: {results?.percentage.toFixed(0)}% ({results?.total_score}/{results?.total_questions})
              </Typography>
              <Typography variant="body1" paragraph>
                {results?.overall_feedback}
              </Typography>
            </Box>
            
            <Divider sx={{ my: 3 }} />
            
            <Typography variant="h5" gutterBottom>
              문제별 결과
            </Typography>
            
            {results?.answers.map((result, index) => (
              <Card 
                key={index} 
                variant="outlined" 
                sx={{ 
                  mb: 3,
                  borderColor: result.is_correct ? 'success.main' : 'error.main',
                  bgcolor: result.is_correct ? 'rgba(76, 175, 80, 0.08)' : 'rgba(239, 83, 80, 0.08)'
                }}
              >
                <CardContent>
                  <Grid container spacing={2}>
                    <Grid item xs={1}>
                      {result.is_correct ? (
                        <CheckIcon color="success" />
                      ) : (
                        <CloseIcon color="error" />
                      )}
                    </Grid>
                    <Grid item xs={11}>
                      <Typography variant="h6" gutterBottom>
                        문제 {index + 1}
                      </Typography>
                      <Typography variant="body1" paragraph>
                        {result.question}
                      </Typography>
                      
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 2 }}>
                        <Typography variant="body2">
                          <strong>내 답변:</strong> {result.user_answer}
                        </Typography>
                        <Typography variant="body2" color={result.is_correct ? 'success.main' : 'error.main'}>
                          <strong>정답:</strong> {result.correct_answer}
                        </Typography>
                      </Box>
                      
                      <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                        {result.feedback}
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            ))}
            
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4, gap: 2 }}>
              <Button 
                variant="outlined" 
                color="primary"
                onClick={handleRetry}
              >
                다시 풀기
              </Button>
              <Button 
                variant="contained" 
                color="primary"
                onClick={handleNewQuiz}
                sx={{ 
                  background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                  boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                }}
              >
                새 퀴즈 생성
              </Button>
            </Box>
          </Paper>
        )}
      </Box>
    </Container>
  );
}