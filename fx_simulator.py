"""
환율 변동 시뮬레이터 (중간 버전)
구현 범위: 거래 정보 입력 -> 입력 검증 -> 환율 조회(휴일은 직전 영업일) -> 환차손익 계산 -> 결과 출력
미구현(최종 버전 예정): 환헤지 비교, 다중 통화 비교, 그래프 시각화, 결과 저장
"""
import csv
import os
import random
from datetime import datetime, timedelta

RATE_FILE = "rates.csv"      # 컬럼: date, USD, EUR, JPY, CNY (원/1단위, JPY는 원/100엔)
CURRENCIES = ["USD", "EUR", "JPY", "CNY"]


# ---------- 1. 데이터 준비 ----------
def make_sample_data(path):
    """테스트용 가상 환율 데이터 생성 (영업일만). 실제 제출 시에는 ECOS 데이터로 교체할 것."""
    random.seed(1)
    base = {"USD": 1400.0, "EUR": 1520.0, "JPY": 930.0, "CNY": 195.0}
    day = datetime(2025, 1, 1)
    end = datetime(2025, 12, 31)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date"] + CURRENCIES)
        while day <= end:
            if day.weekday() < 5:  # 월~금만 기록 (주말은 데이터 없음)
                for c in CURRENCIES:
                    base[c] *= 1 + random.uniform(-0.005, 0.005)
                writer.writerow([day.strftime("%Y-%m-%d")] +
                                [round(base[c], 2) for c in CURRENCIES])
            day += timedelta(days=1)


def load_rates(path):
    """CSV를 읽어 {통화: {날짜(date): 환율}} 형태로 반환"""
    rates = {c: {} for c in CURRENCIES}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = datetime.strptime(row["date"], "%Y-%m-%d").date()
            for c in CURRENCIES:
                if row[c]:
                    rates[c][d] = float(row[c])
    return rates


# ---------- 2. 환율 조회 ----------
def get_rate(rates, currency, date, max_back=10):
    """해당 날짜 환율 반환. 없으면(휴일 등) 직전 영업일 환율로 대체. (환율, 실제사용일) 반환"""
    for i in range(max_back + 1):
        d = date - timedelta(days=i)
        if d in rates[currency]:
            return rates[currency][d], d
    return None, None


# ---------- 3. 환차손익 계산 ----------
def calc_fx_gain(trade_type, amount, rate_contract, rate_settle):
    """수출: 외화금액 x (결제일 환율 - 계약일 환율) / 수입: 외화금액 x (계약일 환율 - 결제일 환율)"""
    if trade_type == "수출":
        gain = amount * (rate_settle - rate_contract)
    else:
        gain = amount * (rate_contract - rate_settle)
    base = amount * rate_contract                 # 계약일 기준 원화 금액
    percent = gain / base * 100
    return gain, percent


# ---------- 4. 입력 + 검증 ----------
def input_choice(prompt, choices):
    while True:
        v = input(prompt).strip().upper() if choices is CURRENCIES else input(prompt).strip()
        if v in choices:
            return v
        print(f"[오류] {', '.join(choices)} 중에서 입력해 주세요.")


def input_date(prompt):
    while True:
        s = input(prompt).strip()
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            print("[오류] 날짜 형식이 올바르지 않습니다. 예) 2025-03-03")


def input_amount(prompt):
    while True:
        s = input(prompt).replace(",", "").strip()
        try:
            v = float(s)
            if v > 0:
                return v
            print("[오류] 금액은 0보다 커야 합니다.")
        except ValueError:
            print("[오류] 숫자로 입력해 주세요.")


def input_trade():
    print("=== 거래 정보 입력 ===")
    trade_type = input_choice("거래 유형 (수출/수입): ", ["수출", "수입"])
    currency = input_choice(f"통화 ({'/'.join(CURRENCIES)}): ", CURRENCIES)
    amount = input_amount("거래 금액(외화): ")
    while True:
        contract = input_date("계약일 (YYYY-MM-DD): ")
        settle = input_date("결제일 (YYYY-MM-DD): ")
        if settle < contract:
            print("[오류] 결제일은 계약일보다 빠를 수 없습니다. 다시 입력해 주세요.")
            continue
        return trade_type, currency, amount, contract, settle


# ---------- 5. 메인 ----------
def main():
    if not os.path.exists(RATE_FILE):
        print("(rates.csv가 없어 테스트용 가상 데이터를 생성합니다)")
        make_sample_data(RATE_FILE)
    rates = load_rates(RATE_FILE)

    trade_type, cur, amount, contract, settle = input_trade()

    r_c, used_c = get_rate(rates, cur, contract)
    r_s, used_s = get_rate(rates, cur, settle)
    if r_c is None or r_s is None:
        print("[오류] 해당 기간의 환율 데이터가 없습니다.")
        return

    gain, pct = calc_fx_gain(trade_type, amount, r_c, r_s)

    print("\n=== 분석 결과 ===")
    print(f"거래: {trade_type} / {cur} {amount:,.2f}")
    print(f"계약일 환율 ({used_c}): {r_c:,.2f}원")
    print(f"결제일 환율 ({used_s}): {r_s:,.2f}원")
    if used_c != contract or used_s != settle:
        print("※ 휴일 등 환율이 없는 날은 직전 영업일 환율을 사용했습니다.")
    print(f"환차손익: {gain:+,.0f}원 ({pct:+.2f}%)")
    if gain > 0:
        print(f"-> 환율 변동으로 약 {gain:,.0f}원의 환차익이 발생했습니다.")
    elif gain < 0:
        print(f"-> 환율 변동으로 약 {-gain:,.0f}원의 환차손이 발생했습니다.")
    else:
        print("-> 환차손익이 발생하지 않았습니다.")


if __name__ == "__main__":
    main()
