#!/usr/bin/env bash
# 둘: 기존 데이터를 모두 지우고 새로 배포 (Mac / Linux)
set -e
cd "$(dirname "$0")"
echo "기존 데이터(회원 프로필, 좋아요, 채팅, 사진, 마음 표현)를 모두 지우고 새로 배포해요."
read -r -p "계속할까요? (y/N) " ans
if [ "$ans" != "y" ] && [ "$ans" != "Y" ]; then echo "취소했어요."; exit 1; fi
echo "[1/2] 기존 데이터 지우는 중..."
firebase firestore:delete --all-collections --force || echo "  (지울 데이터가 없거나 처음 배포예요)"
echo "[2/2] 사이트와 보안 규칙 배포 중..."
firebase deploy
echo "끝! 위에 나온 Hosting URL로 들어가 보세요."
