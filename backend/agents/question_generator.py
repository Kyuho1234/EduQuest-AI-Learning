import os
import json
from typing import Dict, List, Optional
import google.generativeai as genai
from ..services.rag_service import RAGService

class QuestionGenerator:
    def __init__(self, api_key: Optional[str] = None, model_name: str = 'gemini-1.5-pro'):
        """
        문제 생성 에이전트 초기화
        
        Args:
            api_key: Google Gemini API 키 (None인 경우 환경 변수에서 가져옴)
            model_name: 사용할 모델 이름
        """
        # API 키 설정
        if api_key is None:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
        
        # Gemini API 설정
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # RAG 서비스 초기화
        self.rag_service = RAGService()
    
    def generate_questions(self, content: str, num_questions: int = 5, 
                          question_types: List[str] = ["multiple_choice", "short_answer"]) -> List[Dict]:
        """
        주어진 콘텐츠를 기반으로 문제 생성
        
        Args:
            content: 문제 생성의 기반이 되는 텍스트 내용
            num_questions: 생성할 문제 수
            question_types: 생성할 문제 유형 목록
            
        Returns:
            생성된 문제 목록
        """
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
        response = self.model.generate_content(prompt)
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
                verification = self.verify_question(q, content)
                if verification["verification"]["is_valid"]:
                    q["verification"] = verification["verification"]
                    verified_questions.append(q)
            
            return verified_questions
        
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
            
            response = self.model.generate_content(retry_prompt)
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
                    verification = self.verify_question(q, content)
                    if verification["verification"]["is_valid"]:
                        q["verification"] = verification["verification"]
                        verified_questions.append(q)
                
                return verified_questions
                
            except json.JSONDecodeError as e:
                raise ValueError(f"문제 생성 실패: JSON 파싱 오류 - {str(e)}")
    
    def verify_question(self, question: Dict, context: str) -> Dict:
        """
        생성된 문제의 유효성 검증
        
        Args:
            question: 검증할 문제
            context: 원본 문서 내용
            
        Returns:
            검증 결과
        """
        # 1. RAG 기반 유사도 검증
        similarity_result = self.rag_service.compute_question_similarity(question, context)
        
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
        설명: {question.get("explanation", "")}

        평가 기준:
        1. 할루시네이션 검사 (2-scale): 문제가 입력 자료에 기반하고 있는지 여부 (Y/N)
        2. 품질 검사 (3-scale): 문제의 전반적인 품질 (매우적절/적절/부적절)
        3. 의미론적 일관성 (0.0-1.0): 문제의 내용 관련성, 사실적 정확성, 맥락 일치도를 0.0~1.0 사이 점수로 평가

        다음 JSON 형식으로 평가 결과를 제시해 주세요:
        {json_format}
        
        반드시 위 형식의 JSON으로만 답변하세요. 다른 텍스트는 포함하지 마세요.
        """
        
        llm_response = self.model.generate_content(combined_prompt)
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
                        "question": similarity_result["question_similarity"],
                        "answer": similarity_result["answer_similarity"],
                        "explanation": similarity_result["explanation_similarity"],
                        "average": similarity_result["average_similarity"]
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
                        "question": similarity_result["question_similarity"],
                        "answer": similarity_result["answer_similarity"],
                        "explanation": similarity_result["explanation_similarity"],
                        "average": similarity_result["average_similarity"]
                    },
                    "total_score": similarity_result["average_similarity"],
                    "is_valid": similarity_result["is_valid"],
                    "error": "LLM 응답 파싱 실패"
                }
            }