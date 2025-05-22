import os
import json
import torch
import re
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from PyPDF2 import PdfReader

# 환경 변수 로드
load_dotenv()

# API 키 설정
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다")

# Gemini API 설정
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

# RAG 모델 로드
rag_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# FastAPI 앱 생성
app = FastAPI(title="EduQuest API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포시 특정 도메인으로 제한해야 함
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모델 클래스
class Question(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    question_type: str = "multiple_choice"

class GenerateRequest(BaseModel):
    content: str
    num_questions: int = 5
    question_types: List[str] = ["multiple_choice", "short_answer"]

class AnswerSubmission(BaseModel):
    question: str
    user_answer: str
    correct_answer: str
    question_type: Optional[str] = "multiple_choice"

# 텍스트 전처리 함수
def preprocess_text(text: str) -> str:
    # 연속된 공백을 하나로 치환
    text = ' '.join(text.split())
    # 불필요한 특수문자 제거
    text = text.replace('•', '')
    return text

# RAG 기반 검증 함수
def verify_question_with_rag(question: Dict, context: str) -> Dict:
    try:
        # 1. 기존 임베딩 기반 유사도 계산
        doc_embedding = rag_model.encode(context, convert_to_tensor=True)
        
        question_text = preprocess_text(question["question"])
        answer_text = preprocess_text(question["correct_answer"])
        explanation_text = preprocess_text(question["explanation"])
        
        q_embedding = rag_model.encode(question_text, convert_to_tensor=True)
        a_embedding = rag_model.encode(answer_text, convert_to_tensor=True)
        e_embedding = rag_model.encode(explanation_text, convert_to_tensor=True)
        
        q_similarity = torch.cosine_similarity(doc_embedding.unsqueeze(0), q_embedding.unsqueeze(0)).item()
        a_similarity = torch.cosine_similarity(doc_embedding.unsqueeze(0), a_embedding.unsqueeze(0)).item()
        e_similarity = torch.cosine_similarity(doc_embedding.unsqueeze(0), e_embedding.unsqueeze(0)).item()
        
        # 2. LLM 검증 (할루시네이션, 품질 검사)
        json_format = """
        {
          "hallucination_check": {
            "result": "Y 또는 N",
            "evidence": "판단의 근거가 되는 입력 자료의 관련 부분",
            "explanation": "판단 이유 설명"
          },
          "quality_check": {
            "rating": "매우적절/적절/부적절",
            "reasoning": "평가 이유 설명"
          },
          "semantic_consistency": {
            "content_relevance": 0.0,
            "factual_accuracy": 0.0,
            "context_alignment": 0.0,
            "average_score": 0.0
          }
        }
        """
        
        combined_prompt = f"""
        당신은 교육용 문제 검증 전문가입니다. 아래 입력 자료와 생성된 문제를 검토하여 문제의 정확성과 품질을 평가해 주세요.

        [입력 자료]
        {context}

        [생성된 문제]
        질문: {question["question"]}
        정답: {question["correct_answer"]}
        설명: {question["explanation"]}

        평가 기준:
        1. 할루시네이션 검사 (2-scale): 문제가 입력 자료에 기반하고 있는지 여부 (Y/N)
        2. 품질 검사 (3-scale): 문제의 전반적인 품질 (매우적절/적절/부적절)
        3. 의미론적 일관성 (0.0-1.0): 문제의 내용 관련성, 사실적 정확성, 맥락 일치도를 0.0~1.0 사이 점수로 평가

        다음 JSON 형식으로 평가 결과를 제시해 주세요:
        {json_format}
        
        반드시 위 형식의 JSON으로만 답변하세요. 다른 텍스트는 포함하지 마세요.
        """
        
        llm_response = model.generate_content(combined_prompt)
        llm_text = llm_response.text
        
        # JSON 추출 및 파싱
        try:
            # JSON 형식 정리 (필요한 경우)
            llm_text = llm_text.strip()
            if "```json" in llm_text:
                llm_text = llm_text.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_text:
                llm_text = llm_text.split("```")[1].strip()
            
            verification_result = json.loads(llm_text)
            
            # 할루시네이션 점수 계산
            hallucination_score = 1.0 if verification_result["hallucination_check"]["result"] == "Y" else 0.0
            
            # 품질 점수 계산
            quality_rating = verification_result["quality_check"]["rating"]
            if quality_rating == "매우적절":
                quality_score = 1.0
            elif quality_rating == "적절":
                quality_score = 0.7
            else:  # 부적절
                quality_score = 0.3
                
            # 의미론적 일관성 점수
            semantic_score = verification_result["semantic_consistency"]["average_score"]
            
            # 종합 점수 계산 (가중치 적용)
            total_score = (
                hallucination_score * 0.4 +  # 할루시네이션 없음 (40%)
                quality_score * 0.3 +        # 품질 점수 (30%)
                semantic_score * 0.3         # 의미론적 일관성 (30%)
            )
            
            # 최종 검증 결과 반환
            return {
                "question_id": question.get("id", ""),
                "verification": {
                    "embedding_similarity": {
                        "question": q_similarity,
                        "answer": a_similarity,
                        "explanation": e_similarity,
                        "average": (q_similarity + a_similarity + e_similarity) / 3
                    },
                    "hallucination_check": verification_result["hallucination_check"],
                    "quality_check": verification_result["quality_check"],
                    "semantic_consistency": verification_result["semantic_consistency"],
                    "total_score": total_score,
                    "is_valid": total_score >= 0.6  # 60% 이상이면 유효한 문제로 판단
                }
            }
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"원본 텍스트: {llm_text}")
            # 파싱 실패 시 임베딩 기반 결과만 반환
            return {
                "question_id": question.get("id", ""),
                "verification": {
                    "embedding_similarity": {
                        "question": q_similarity,
                        "answer": a_similarity,
                        "explanation": e_similarity,
                        "average": (q_similarity + a_similarity + e_similarity) / 3
                    },
                    "total_score": (q_similarity + a_similarity + e_similarity) / 3,
                    "is_valid": (q_similarity + a_similarity + e_similarity) / 3 >= 0.6,
                    "error": "LLM 응답 파싱 실패"
                }
            }
    except Exception as e:
        print(f"검증 중 오류 발생: {str(e)}")
        return {
            "question_id": question.get("id", ""),
            "verification": {
                "error": str(e),
                "is_valid": False
            }
        }

# 엔드포인트: PDF 파일 처리
@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # PDF 파일 저장
        pdf_content = await file.read()
        
        # PyPDF2로 PDF 내용 추출
        reader = PdfReader(file.file)
        text_content = ""
        
        for page in reader.pages:
            text_content += page.extract_text() + "\n"
        
        # 추출된 텍스트 반환
        return {"success": True, "text": text_content, "page_count": len(reader.pages)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 처리 오류: {str(e)}")

# 엔드포인트: 문제 생성
@app.post("/api/generate-questions")
async def generate_questions(data: GenerateRequest):
    try:
        content = data.content
        num_questions = data.num_questions
        question_types = data.question_types
        
        # 문제 생성 프롬프트
        prompt = f"""
        다음 텍스트를 기반으로 {num_questions}개의 문제를 생성해 주세요.
        
        [텍스트]
        {content}
        
        문제 유형: {', '.join(question_types)}
        
        각 문제는 다음 JSON 형식으로 반환해 주세요:
        {{
            "questions": [
                {{
                    "question": "질문 내용",
                    "options": ["보기1", "보기2", "보기3", "보기4"],
                    "correct_answer": "정답",
                    "explanation": "정답 설명",
                    "question_type": "multiple_choice 또는 short_answer"
                }},
                // ... 추가 문제들
            ]
        }}
        
        요구사항:
        1. 복잡하고 도전적인 문제를 만들어 주세요.
        2. 모든 문제는 제공된 텍스트에 명확히 기반해야 합니다.
        3. 객관식 문제는 4개의 보기가 있어야 합니다.
        4. 주관식 문제는 짧은 답변(1-3단어)으로 답할 수 있어야 합니다.
        5. 정답 설명은 상세하고 교육적이어야 합니다.
        
        반드시 위에 제시한 형식의 JSON만 반환해 주세요. 다른 설명이나 텍스트는 포함하지 마세요.
        """
        
        # Gemini API 호출
        response = model.generate_content(prompt)
        result_text = response.text
        
        # JSON 형식 추출 및 파싱
        try:
            # JSON 형식 정리 (필요한 경우)
            result_text = result_text.strip()
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].strip()
            
            generated_questions = json.loads(result_text)
            
            # 생성된 문제 검증
            verified_questions = []
            for q in generated_questions["questions"]:
                verification = verify_question_with_rag(q, content)
                if verification["verification"]["is_valid"]:
                    q["verification"] = verification["verification"]
                    verified_questions.append(q)
            
            return {"questions": verified_questions}
        
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 재시도
            retry_prompt = f"""
            이전 응답을 파싱할 수 없습니다. 다음 형식의 유효한 JSON으로만 응답해 주세요:
            
            {{
                "questions": [
                    {{
                        "question": "질문 내용",
                        "options": ["보기1", "보기2", "보기3", "보기4"],
                        "correct_answer": "정답",
                        "explanation": "정답 설명",
                        "question_type": "multiple_choice 또는 short_answer"
                    }},
                    // ... 추가 문제들
                ]
            }}
            
            반드시 위 형식을 정확히 따라주세요. 다른 텍스트나 마크다운 코드 블록(```) 없이 순수 JSON만 반환해 주세요.
            """
            
            response = model.generate_content(retry_prompt)
            result_text = response.text.strip()
            
            # 마크다운 코드 블록 제거 시도
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].strip()
            
            try:
                generated_questions = json.loads(result_text)
                
                # 생성된 문제 검증
                verified_questions = []
                for q in generated_questions["questions"]:
                    verification = verify_question_with_rag(q, content)
                    if verification["verification"]["is_valid"]:
                        q["verification"] = verification["verification"]
                        verified_questions.append(q)
                
                return {"questions": verified_questions}
                
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=500, detail=f"문제 생성 실패: JSON 파싱 오류 - {str(e)}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문제 생성 실패: {str(e)}")

# 엔드포인트: 답안 채점
@app.post("/api/check-answers")
async def check_answers(data: Dict):
    try:
        answers = data["answers"]
        total_score = 0
        total_questions = len(answers)
        
        # 정답 처리를 위한 전처리 함수
        def normalize_answer(ans: str) -> str:
            ans = ans.lower()
            ans = re.sub(r'\s*\([^)]*\)', '', ans)
            ans = ' '.join(ans.split())
            ans = re.sub(r'[.,!?;:]', '', ans)
            return ans

        # 모든 답안에 대한 정답 여부 확인
        processed_answers = []
        for answer in answers:
            question = answer["question"]
            user_answer = answer["user_answer"].strip()
            correct_answer = answer["correct_answer"].strip()
            question_type = answer.get("question_type", "unknown")
            
            normalized_user_answer = normalize_answer(user_answer)
            normalized_correct_answer = normalize_answer(correct_answer)
            
            # 정답 여부 확인
            is_correct = normalized_user_answer == normalized_correct_answer
            
            # 주관식 답안의 경우 유사도 검사 추가
            similarity = 0.0
            if question_type == "short_answer" and not is_correct:
                user_embedding = rag_model.encode(normalized_user_answer, convert_to_tensor=True)
                correct_embedding = rag_model.encode(normalized_correct_answer, convert_to_tensor=True)
                similarity = torch.cosine_similarity(user_embedding.unsqueeze(0), correct_embedding.unsqueeze(0)).item()
                
                # 유사도가 0.8 이상이면 부분 점수 부여
                if similarity >= 0.8:
                    is_correct = True
                elif similarity >= 0.6:
                    is_correct = "partial"  # 부분 점수
            
            # 점수 계산
            if is_correct == True:
                score = 1.0
                total_score += 1.0
            elif is_correct == "partial":
                score = 0.5
                total_score += 0.5
            else:
                score = 0.0
            
            # AI 피드백 생성
            feedback_prompt = f"""
            다음 문제와 답변에 대한 간단한 피드백을 제공해주세요:
            
            문제: {question}
            학생 답변: {user_answer}
            정답: {correct_answer}
            정답 여부: {"맞음" if is_correct == True else "부분 정답" if is_correct == "partial" else "틀림"}
            
            학생에게 도움이 될 만한 구체적인 피드백을 1-2문장으로 제공해주세요.
            """
            
            feedback_response = model.generate_content(feedback_prompt)
            feedback = feedback_response.text.strip()
            
            processed_answer = {
                "question": question,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "score": score,
                "feedback": feedback
            }
            
            if question_type == "short_answer" and not is_correct == True:
                processed_answer["similarity"] = similarity
                
            processed_answers.append(processed_answer)
        
        # 종합 피드백 생성
        overall_percentage = (total_score / total_questions) * 100
        
        overall_feedback_prompt = f"""
        학생이 총 {total_questions}개의 문제 중 {total_score}개를 맞혔습니다(정확도: {overall_percentage:.1f}%).
        
        학생의 전반적인 이해도와 개선점에 대한 교육적이고 격려가 담긴 피드백을 2-3문장으로 제공해주세요.
        """
        
        overall_feedback_response = model.generate_content(overall_feedback_prompt)
        overall_feedback = overall_feedback_response.text.strip()
        
        return {
            "answers": processed_answers,
            "total_score": total_score,
            "total_questions": total_questions,
            "percentage": overall_percentage,
            "overall_feedback": overall_feedback
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답안 채점 실패: {str(e)}")

# 서버 구동
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)