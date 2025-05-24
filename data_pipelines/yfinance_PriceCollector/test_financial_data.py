import yfinance as yf
import pandas as pd
import sys
import os

# 상위 디렉토리를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from financial_data_collector import process_comprehensive_financial_data, get_comprehensive_financial_data

def test_apple_financial_data():
    """
    Apple 주식의 각 기간별 재무 데이터가 다른지 테스트
    """
    print("=== Apple (AAPL) 재무 데이터 테스트 ===")
    
    # Apple 재무 데이터 가져오기
    financial_data = get_comprehensive_financial_data("AAPL")
    
    if not financial_data:
        print("[ERROR] 재무 데이터를 가져올 수 없습니다.")
        return
    
    # 재무 데이터 처리
    financial_statements = process_comprehensive_financial_data("AAPL", financial_data)
    
    if not financial_statements:
        print("[ERROR] 재무제표 데이터 처리 결과가 없습니다.")
        return
    
    print(f"\n[INFO] 총 {len(financial_statements)}개의 재무제표 레코드가 생성되었습니다.")
    
    # 각 레코드별로 주요 지표들 출력
    print("\n=== 각 기간별 주요 재무 지표 비교 ===")
    for i, stmt in enumerate(financial_statements):
        print(f"\n{i+1}. 기간: {stmt['report_period']} ({stmt['report_type']})")
        print(f"   매출액: {stmt['revenue']:,}" if stmt['revenue'] else "   매출액: N/A")
        print(f"   총이익: {stmt['gross_profits']:,}" if stmt['gross_profits'] else "   총이익: N/A")
        print(f"   EBITDA: {stmt['ebitda']:,}" if stmt['ebitda'] else "   EBITDA: N/A")
        print(f"   영업현금흐름: {stmt['operating_cashflow']:,}" if stmt['operating_cashflow'] else "   영업현금흐름: N/A")
        print(f"   자유현금흐름: {stmt['free_cashflow']:,}" if stmt['free_cashflow'] else "   자유현금흐름: N/A")
        print(f"   총자산: {stmt['assets']:,}" if stmt['assets'] else "   총자산: N/A")
        print(f"   부채총계: {stmt['liabilities']:,}" if stmt['liabilities'] else "   부채총계: N/A")
        print(f"   자본총계: {stmt['equity']:,}" if stmt['equity'] else "   자본총계: N/A")
        if stmt['gross_margins']:
            print(f"   총이익률: {stmt['gross_margins']:.4f} ({stmt['gross_margins']*100:.2f}%)")
    
    # 같은 값이 반복되는지 확인
    print("\n=== 중복 값 검사 ===")
    check_fields = ['gross_profits', 'ebitda', 'operating_cashflow', 'free_cashflow', 'gross_margins']
    
    for field in check_fields:
        values = [stmt[field] for stmt in financial_statements if stmt[field] is not None]
        unique_values = set(values)
        
        if len(values) > 1 and len(unique_values) == 1:
            print(f"[WARNING] {field}: 모든 기간에 동일한 값 ({values[0]})이 사용되고 있습니다!")
        elif len(unique_values) > 1:
            print(f"[OK] {field}: 기간별로 다른 값들이 사용되고 있습니다.")
            print(f"     값들: {list(unique_values)[:3]}{'...' if len(unique_values) > 3 else ''}")
        else:
            print(f"[INFO] {field}: 데이터가 부족하거나 없습니다.")

if __name__ == "__main__":
    test_apple_financial_data() 