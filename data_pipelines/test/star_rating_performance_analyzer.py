#!/usr/bin/env python3
"""
별점 기반 투자 성과 분석기
- data 폴더의 보고서에서 별점 추출
- 2024-01-01 ~ 2025-05-29 주가 성과 계산
- 별점별 성과 비교 분석
"""

import os
import csv
import re
import pandas as pd
import yfinance as yf
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple
import glob
from dataclasses import dataclass
import time  # API 호출 간격 조절용

@dataclass
class StockAnalysis:
    stock_code: str
    star_rating: int
    start_price: float
    end_price: float
    return_pct: float
    report_date: str

class StarRatingPerformanceAnalyzer:
    def __init__(self):
        self.start_date = "2024-01-10"
        self.end_date = "2025-05-29"  # Use valid recent date
        # Use absolute path based on script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(script_dir, "data", "historical_reports")
        print(f"데이터 디렉토리: {self.data_dir}")
        print(f"분석 기간: {self.start_date} ~ {self.end_date}")
        
    def extract_star_rating(self, report_content: str) -> int:
        """보고서 내용에서 별점 추출"""
        try:
            # 투자 매력도 패턴 찾기
            patterns = [
                r'투자 매력도[:：]\s*([⭐★✦]+)\s*\(\d+점?\)',  # 투자 매력도: ⭐⭐⭐⭐ (4점)
                r'투자 매력도[:：]\s*([⭐★✦]+)',
                r'투자 매력도[:：]\s*([⭐★✦]{1,5})',
                r'매력도[:：]\s*([⭐★✦]+)\s*\(\d+점?\)',      # 매력도: ⭐⭐⭐ (3점)
                r'매력도[:：]\s*([⭐★✦]+)',
                r'([⭐★✦]{1,5})\s*\(5점 만점\)',
                r'([⭐★✦]{1,5})\s*\(\d+점?\)',              # ⭐⭐⭐⭐ (4점)
                r'([⭐★✦]{1,5})\s*\/\s*5',
                r'([⭐★✦]{5})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, report_content)
                if match:
                    stars = match.group(1)
                    # 별 문자 개수 세기
                    star_count = len([c for c in stars if c in '⭐★✦'])
                    if 1 <= star_count <= 5:
                        print(f"별점 발견: {stars} ({star_count}개)")
                        return star_count
            
            # 숫자로 표현된 평점 찾기
            number_patterns = [
                r'투자 매력도[:：]\s*([⭐★✦]+)\s*\((\d)점?\)',  # 별 + (숫자점) 조합에서 숫자 추출
                r'매력도[:：]\s*([⭐★✦]+)\s*\((\d)점?\)',      # 매력도 + 별 + (숫자점)
                r'투자 매력도[:：]\s*(\d)\s*\/\s*5',
                r'투자 매력도[:：]\s*(\d)\s*점',
                r'매력도[:：]\s*(\d)\s*점',
                r'(\d)\s*점\s*만점',
                r'\((\d)점\)',                                  # 단순히 (4점) 형태
                r'(\d)\s*\/\s*5점?'                            # 4/5 형태
            ]
            
            for pattern in number_patterns:
                match = re.search(pattern, report_content)
                if match:
                    # 그룹이 2개면 두 번째 그룹(숫자)을 사용, 1개면 첫 번째 그룹 사용
                    if len(match.groups()) >= 2 and match.group(2):
                        rating = int(match.group(2))
                    else:
                        rating = int(match.group(1))
                    
                    if 1 <= rating <= 5:
                        print(f"숫자 평점 발견: {rating}점 (패턴: {pattern})")
                        return rating
            
            print("별점을 찾을 수 없음")
            return 0
            
        except Exception as e:
            print(f"별점 추출 실패: {e}")
            return 0
    
    def get_stock_price(self, ticker: str, date_str: str) -> float:
        """특정 날짜의 주가 가져오기"""
        try:
            # API 호출 전 잠시 대기 (과부하 방지)
            time.sleep(0.5)
            
            # yfinance로 주가 데이터 가져오기
            stock = yf.Ticker(ticker)
            
            # Method 1: 정확한 날짜 범위로 시도
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
                start_date = target_date - timedelta(days=7)  # 일주일 전부터
                end_date = target_date + timedelta(days=7)    # 일주일 후까지
                
                hist = stock.history(start=start_date.strftime("%Y-%m-%d"), 
                                   end=end_date.strftime("%Y-%m-%d"))
                
                if not hist.empty:
                    # 목표 날짜에 가장 가까운 거래일 찾기
                    hist.index = hist.index.date  # timezone 제거
                    target_date_only = target_date.date()
                    
                    # 목표 날짜 이후 첫 번째 거래일 찾기
                    valid_dates = [d for d in hist.index if d >= target_date_only]
                    if valid_dates:
                        closest_date = min(valid_dates)
                        price = hist.loc[closest_date, 'Close']
                        print(f"{ticker} {date_str}: ${price:.2f} (실제: {closest_date})")
                        return float(price)
                    else:
                        # 목표 날짜 이전 마지막 거래일 사용
                        price = hist['Close'].iloc[-1]
                        actual_date = hist.index[-1]
                        print(f"{ticker} {date_str}: ${price:.2f} (실제: {actual_date})")
                        return float(price)
            except:
                pass
            
            # Method 2: 기간 기반 조회 (fallback)
            if "2024-01" in date_str:
                hist = stock.history(period="1y")  # 1년 데이터
            else:
                hist = stock.history(period="6mo")  # 6개월 데이터
            
            if not hist.empty:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                hist.index = hist.index.date
                
                # 가장 가까운 날짜 찾기
                closest_date = min(hist.index, key=lambda x: abs((x - target_date).days))
                price = hist.loc[closest_date, 'Close']
                print(f"{ticker} {date_str}: ${price:.2f} (근사: {closest_date})")
                return float(price)
            else:
                print(f"{ticker} {date_str}: 데이터 없음")
                return 0.0
                
        except Exception as e:
            print(f"주가 조회 실패 {ticker} {date_str}: {e}")
            return 0.0
    
    def read_reports_from_csv(self) -> List[Dict]:
        """CSV 파일들에서 보고서 읽기"""
        reports = []
        
        # CSV 파일 패턴들
        csv_patterns = [
            os.path.join(self.data_dir, "historical_report_*.csv"),
            os.path.join(self.data_dir, "*.csv")
        ]
        
        csv_files = []
        for pattern in csv_patterns:
            csv_files.extend(glob.glob(pattern))
        
        # 요약 파일 제외
        csv_files = [f for f in csv_files if "summary" not in f.lower()]
        
        print(f"발견된 CSV 파일: {len(csv_files)}개")
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if 'stock_code' in row and 'report' in row:
                            reports.append({
                                'stock_code': row['stock_code'],
                                'report': row['report'],
                                'generated_at': row.get('generated_at', ''),
                                'success': row.get('success', 'True').lower() == 'true',
                                'file_path': csv_file
                            })
                            
            except Exception as e:
                print(f"CSV 파일 읽기 실패 {csv_file}: {e}")
        
        print(f"총 보고서 수: {len(reports)}개")
        
        # Remove duplicates by stock_code (keep the first one)
        seen_stocks = set()
        unique_reports = []
        for report in reports:
            stock_code = report['stock_code']
            if stock_code not in seen_stocks:
                unique_reports.append(report)
                seen_stocks.add(stock_code)
        
        print(f"중복 제거 후: {len(unique_reports)}개 (고유 종목)")
        return unique_reports
    
    def analyze_performance(self) -> List[StockAnalysis]:
        """전체 성과 분석"""
        print("=== 별점 기반 투자 성과 분석 시작 ===")
        print(f"분석 기간: {self.start_date} ~ {self.end_date}")
        print("⏰ API 호출 간격: 0.5초 + 0.3초 (과부하 방지)")
        
        # 보고서 읽기
        reports = self.read_reports_from_csv()
        
        if not reports:
            print("❌ 분석할 보고서가 없습니다!")
            return []
        
        analyses = []
        start_time = time.time()
        estimated_time = len(reports) * 1.0  # 대략 1초씩 소요 예상
        print(f"⏱️ 예상 소요 시간: {estimated_time/60:.1f}분")
        
        for i, report in enumerate(reports, 1):
            stock_code = report['stock_code']
            report_content = report['report']
            
            print(f"\n📊 {i}/{len(reports)} - {stock_code} 분석 중...")
            
            # 별점 추출
            star_rating = self.extract_star_rating(report_content)
            
            if star_rating == 0:
                print(f"⚠️ {stock_code}: 별점 없음 - 건너뜀")
                continue
            
            # 주가 데이터 가져오기
            start_price = self.get_stock_price(stock_code, self.start_date)
            
            # 두 번째 API 호출 전 추가 대기
            time.sleep(0.3)
            
            end_price = self.get_stock_price(stock_code, self.end_date)
            
            if start_price == 0 or end_price == 0:
                print(f"⚠️ {stock_code}: 주가 데이터 없음 - 건너뜀")
                continue
            
            # 수익률 계산
            return_pct = ((end_price - start_price) / start_price) * 100
            
            analysis = StockAnalysis(
                stock_code=stock_code,
                star_rating=star_rating,
                start_price=start_price,
                end_price=end_price,
                return_pct=return_pct,
                report_date=report.get('generated_at', '')
            )
            
            analyses.append(analysis)
            
            elapsed = time.time() - start_time
            remaining = len(reports) - i
            avg_time = elapsed / i
            eta = remaining * avg_time
            
            print(f"✅ {stock_code}: {star_rating}⭐ | ${start_price:.2f} → ${end_price:.2f} | {return_pct:+.2f}%")
            print(f"   📊 진행: {i}/{len(reports)} | ⏱️ 경과: {elapsed/60:.1f}분 | ⏳ 남은시간: {eta/60:.1f}분")
            
            # 중간 저장 (10개마다)
            if i % 10 == 0:
                print(f"💾 중간 진행상황: {len(analyses)}개 완료")
        
        total_time = time.time() - start_time
        print(f"\n🎯 분석 완료! 총 소요시간: {total_time/60:.1f}분")
        return analyses
    
    def generate_summary_report(self, analyses: List[StockAnalysis]) -> None:
        """요약 리포트 생성"""
        if not analyses:
            print("❌ 분석 결과가 없습니다!")
            return
        
        # DataFrame 생성
        df = pd.DataFrame([
            {
                'Stock': a.stock_code,
                'Stars': a.star_rating,
                'Start_Price': a.start_price,
                'End_Price': a.end_price,
                'Return_%': a.return_pct,
                'Report_Date': a.report_date
            }
            for a in analyses
        ])
        
        # CSV 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, "data", f"star_rating_performance_{timestamp}.csv")
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"\n📈 === 별점별 투자 성과 분석 결과 ===")
        print(f"분석 기간: {self.start_date} ~ {self.end_date}")
        print(f"총 분석 종목: {len(analyses)}개")
        
        # 별점별 그룹 분석
        star_groups = df.groupby('Stars')
        
        print(f"\n🌟 별점별 성과 요약:")
        for stars in sorted(star_groups.groups.keys()):
            group = star_groups.get_group(stars)
            count = len(group)
            avg_return = group['Return_%'].mean()
            median_return = group['Return_%'].median()
            min_return = group['Return_%'].min()
            max_return = group['Return_%'].max()
            
            print(f"\n{'⭐' * stars} ({stars}점) - {count}개 종목:")
            print(f"  평균 수익률: {avg_return:+.2f}%")
            print(f"  중간값: {median_return:+.2f}%")
            print(f"  최고: {max_return:+.2f}% | 최저: {min_return:+.2f}%")
            
            # 상위/하위 종목
            top_stock = group.loc[group['Return_%'].idxmax()]
            worst_stock = group.loc[group['Return_%'].idxmin()]
            print(f"  🥇 최고: {top_stock['Stock']} ({top_stock['Return_%']:+.2f}%)")
            print(f"  🥉 최저: {worst_stock['Stock']} ({worst_stock['Return_%']:+.2f}%)")
        
        # 전체 통계
        print(f"\n📊 전체 통계:")
        print(f"  전체 평균 수익률: {df['Return_%'].mean():+.2f}%")
        print(f"  전체 중간값: {df['Return_%'].median():+.2f}%")
        print(f"  표준편차: {df['Return_%'].std():.2f}%")
        
        # 별점과 수익률 상관관계
        correlation = df['Stars'].corr(df['Return_%'])
        print(f"  별점-수익률 상관계수: {correlation:.3f}")
        
        # 상위/하위 종목
        print(f"\n🏆 전체 최고 수익률:")
        top_3 = df.nlargest(3, 'Return_%')
        for _, row in top_3.iterrows():
            print(f"  {row['Stock']}: {'⭐' * int(row['Stars'])} | {row['Return_%']:+.2f}%")
        
        print(f"\n💸 전체 최저 수익률:")
        bottom_3 = df.nsmallest(3, 'Return_%')
        for _, row in bottom_3.iterrows():
            print(f"  {row['Stock']}: {'⭐' * int(row['Stars'])} | {row['Return_%']:+.2f}%")
        
        print(f"\n💾 상세 결과 저장: {output_file}")
        
        # 별점별 승률 계산
        print(f"\n🎯 별점별 승률 (양수 수익률 비율):")
        for stars in sorted(star_groups.groups.keys()):
            group = star_groups.get_group(stars)
            positive_count = len(group[group['Return_%'] > 0])
            total_count = len(group)
            win_rate = (positive_count / total_count) * 100
            print(f"  {'⭐' * stars}: {positive_count}/{total_count} ({win_rate:.1f}%)")

def main():
    """메인 실행 함수"""
    analyzer = StarRatingPerformanceAnalyzer()
    
    # 성과 분석 실행
    analyses = analyzer.analyze_performance()
    
    # 요약 리포트 생성
    analyzer.generate_summary_report(analyses)

if __name__ == "__main__":
    main() 