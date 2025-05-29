#!/usr/bin/env python3
"""
과거 데이터 기반 보고서 생성기 실행 스크립트
"""
import sys
import os
import argparse
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from historical_report_generator import HistoricalReportGenerator
from config_historical import get_config, validate_config, DEFAULT_CONFIG, get_random_sp500_tickers

def parse_arguments():
    """명령줄 인수 파싱"""
    parser = argparse.ArgumentParser(
        description="2024년 이전 데이터를 사용한 주식 분석 보고서 생성기"
    )
    
    parser.add_argument(
        "--stock-codes", 
        nargs="+", 
        help="분석할 종목 코드들 (예: 005930 000660)"
    )
    
    parser.add_argument(
        "--output-dir", 
        default=DEFAULT_CONFIG["OUTPUT_DIR"],
        help="CSV 파일 출력 디렉토리"
    )
    
    parser.add_argument(
        "--single", 
        metavar="STOCK_CODE",
        help="단일 종목 분석"
    )
    
    parser.add_argument(
        "--batch", 
        action="store_true",
        help="기본 종목 리스트로 일괄 처리"
    )
    
    parser.add_argument(
        "--sample", 
        action="store_true",
        help="샘플 종목들(10개)로 빠른 테스트"
    )
    
    parser.add_argument(
        "--random", 
        type=int,
        metavar="COUNT",
        help="SP500에서 랜덤하게 선택할 종목 수 (예: --random 50)"
    )
    
    parser.add_argument(
        "--validate", 
        action="store_true",
        help="설정 유효성 검사만 실행"
    )
    
    return parser.parse_args()

def main():
    """메인 함수"""
    args = parse_arguments()
    
    # 설정 유효성 검사
    config_errors = validate_config()
    if config_errors:
        print("설정 오류:")
        for error in config_errors:
            print(f"  - {error}")
        if not args.validate:
            sys.exit(1)
    
    if args.validate:
        if config_errors:
            print("설정에 오류가 있습니다.")
            sys.exit(1)
        else:
            print("설정이 올바릅니다.")
            sys.exit(0)
    
    # 보고서 생성기 초기화
    try:
        generator = HistoricalReportGenerator()
        config = get_config()
        
        print("=== 과거 데이터 기반 보고서 생성기 시작 ===")
        print(f"분석 기준: {config['CUTOFF_DATE']} 이전 데이터")
        print(f"출력 디렉토리: {args.output_dir}")
        
    except Exception as e:
        print(f"초기화 실패: {e}")
        sys.exit(1)
    
    # 실행 모드 결정
    stock_codes = []
    
    if args.single:
        # 단일 종목 분석
        stock_codes = [args.single]
        print(f"단일 종목 분석: {args.single}")
        
    elif args.stock_codes:
        # 지정된 종목들 분석
        stock_codes = args.stock_codes
        print(f"지정 종목들 분석: {stock_codes}")
        
    elif args.batch:
        # 기본 종목 리스트로 일괄 처리
        stock_codes = config["DEFAULT_STOCK_CODES"]
        print(f"일괄 처리 모드: {len(stock_codes)}개 종목")
        
    elif args.sample:
        # 샘플 종목들로 빠른 테스트 (SP500에서 처음 10개)
        stock_codes = config["DEFAULT_STOCK_CODES"][:10]
        print(f"샘플 모드: {len(stock_codes)}개 종목 (SP500에서 처음 10개)")
        print(f"사용 종목: {stock_codes}")
        
    elif args.random:
        # 랜덤 종목 선택
        stock_codes = get_random_sp500_tickers(args.random)
        print(f"랜덤 모드: {len(stock_codes)}개 종목 선택")
        print(f"처음 5개: {stock_codes[:5]}...")
        
    else:
        # 기본값: SP500에서 처음 5개 종목 사용
        stock_codes = config["DEFAULT_STOCK_CODES"][:5]
        print(f"기본 모드: {len(stock_codes)}개 종목 (SP500에서 처음 5개)")
        print(f"사용 종목: {stock_codes}")
    
    # 보고서 생성 실행
    try:
        if len(stock_codes) == 1:
            # 단일 종목
            print(f"단일 종목 보고서 생성: {stock_codes[0]}")
            report_data = generator.generate_historical_report(stock_codes[0])
            csv_path = generator.save_report_to_csv(report_data, args.output_dir)
            
            if report_data["success"]:
                print(f"✅ 보고서 생성 완료: {csv_path}")
                print(f"   뉴스 수: {report_data['news_count']}")
                print(f"   재무 기간: {report_data['financial_periods']}")
            else:
                print(f"❌ 분석 실패: {report_data.get('error', '알 수 없는 오류')}")
                
        else:
            # 일괄 처리
            print(f"일괄 보고서 생성: {len(stock_codes)}개 종목")
            results = generator.batch_generate_reports(stock_codes, args.output_dir)
            
            # 결과 요약
            success_count = sum(1 for r in results if r["success"])
            total_news = sum(r["news_count"] for r in results)
            
            print("=== 처리 완료 ===")
            print(f"전체 종목: {len(results)}개")
            print(f"성공: {success_count}개")
            print(f"실패: {len(results) - success_count}개")
            print(f"총 뉴스 수: {total_news}개")
            
            # 실패한 종목들 로그
            failed_stocks = [r["stock_code"] for r in results if not r["success"]]
            if failed_stocks:
                print(f"실패한 종목들: {failed_stocks}")
        
        print("=== 과거 데이터 기반 보고서 생성 완료 ===")
        
    except KeyboardInterrupt:
        print("사용자에 의해 중단되었습니다.")
        sys.exit(1)
        
    except Exception as e:
        print(f"실행 중 오류 발생: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 