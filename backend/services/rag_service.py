import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Tuple

class RAGService:
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        """
        RAG(Retrieval-Augmented Generation) 서비스 초기화
        
        Args:
            model_name: 사용할 임베딩 모델 이름
        """
        self.model = SentenceTransformer(model_name)
    
    def preprocess_text(self, text: str) -> str:
        """
        텍스트 전처리
        
        Args:
            text: 전처리할 텍스트
            
        Returns:
            전처리된 텍스트
        """
        # 연속된 공백을 하나로 치환
        text = ' '.join(text.split())
        # 불필요한 특수문자 제거
        text = text.replace('•', '')
        return text
    
    def compute_similarity(self, source_text: str, generated_text: str) -> float:
        """
        원본 텍스트와 생성된 텍스트 간의 의미론적 유사도 계산
        
        Args:
            source_text: 원본 텍스트
            generated_text: 생성된 텍스트
            
        Returns:
            코사인 유사도 (0~1 사이 값)
        """
        # 텍스트 전처리
        source_text = self.preprocess_text(source_text)
        generated_text = self.preprocess_text(generated_text)
        
        # 임베딩 계산
        source_embedding = self.model.encode(source_text, convert_to_tensor=True)
        generated_embedding = self.model.encode(generated_text, convert_to_tensor=True)
        
        # 코사인 유사도 계산
        similarity = torch.cosine_similarity(
            source_embedding.unsqueeze(0), 
            generated_embedding.unsqueeze(0)
        ).item()
        
        return similarity
    
    def compute_question_similarity(self, question: Dict, context: str) -> Dict:
        """
        생성된 문제와 원본 문서의 유사도 계산
        
        Args:
            question: 생성된 문제 딕셔너리 (question, options, correct_answer, explanation 포함)
            context: 원본 문서 내용
            
        Returns:
            유사도 점수를 포함한 딕셔너리
        """
        # 문서 임베딩 계산
        doc_embedding = self.model.encode(self.preprocess_text(context), convert_to_tensor=True)
        
        # 문제 구성요소 텍스트 전처리
        question_text = self.preprocess_text(question["question"])
        answer_text = self.preprocess_text(question["correct_answer"])
        explanation_text = self.preprocess_text(question.get("explanation", ""))
        
        # 각 구성요소 임베딩 계산
        q_embedding = self.model.encode(question_text, convert_to_tensor=True)
        a_embedding = self.model.encode(answer_text, convert_to_tensor=True)
        
        # 유사도 계산
        q_similarity = torch.cosine_similarity(doc_embedding.unsqueeze(0), q_embedding.unsqueeze(0)).item()
        a_similarity = torch.cosine_similarity(doc_embedding.unsqueeze(0), a_embedding.unsqueeze(0)).item()
        
        # 설명이 있는 경우에만 설명 유사도 계산
        e_similarity = 0.0
        if explanation_text:
            e_embedding = self.model.encode(explanation_text, convert_to_tensor=True)
            e_similarity = torch.cosine_similarity(doc_embedding.unsqueeze(0), e_embedding.unsqueeze(0)).item()
        
        # 평균 유사도 계산
        if explanation_text:
            avg_similarity = (q_similarity + a_similarity + e_similarity) / 3
        else:
            avg_similarity = (q_similarity + a_similarity) / 2
        
        return {
            "question_similarity": q_similarity,
            "answer_similarity": a_similarity,
            "explanation_similarity": e_similarity,
            "average_similarity": avg_similarity,
            "is_valid": avg_similarity >= 0.6  # 60% 이상 유사도면 유효한 문제로 판단
        }
    
    def extract_relevant_context(self, query: str, document: str, chunk_size: int = 500, top_k: int = 3) -> List[str]:
        """
        질의에 관련된 문서의 관련 컨텍스트 추출
        
        Args:
            query: 검색 질의
            document: 전체 문서
            chunk_size: 청크 크기
            top_k: 반환할 상위 청크 수
            
        Returns:
            관련 컨텍스트 목록
        """
        # 문서를 청크로 분할
        chunks = []
        words = document.split()
        
        for i in range(0, len(words), chunk_size//2):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        # 청크가 없으면 빈 목록 반환
        if not chunks:
            return []
        
        # 질의 임베딩 계산
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        
        # 각 청크의 임베딩 계산 및 유사도 저장
        chunk_similarities = []
        
        for chunk in chunks:
            chunk_embedding = self.model.encode(chunk, convert_to_tensor=True)
            similarity = torch.cosine_similarity(query_embedding.unsqueeze(0), chunk_embedding.unsqueeze(0)).item()
            chunk_similarities.append((chunk, similarity))
        
        # 유사도에 따라 정렬하고 상위 k개 반환
        chunk_similarities.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in chunk_similarities[:top_k]]